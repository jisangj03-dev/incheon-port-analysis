"""자동 갱신(2026-10-21 선장님 질문 「사이트 숫자는 매번 최신이어야 하지 않나?」) — 원천을 받고 지면이 읽는 파생 파일까지 한 번에 만든다.
돌리는 곳은 GitHub Actions(.github/workflows/refresh.yml · Claude 토큰 0)뿐이다. 키는 저장소 시크릿 DATA_GO_KR_KEY 로만 받는다.

순서(앞 단계가 뒤 단계의 입력):
  ① 받기 — collect.py(관세청 항구·공항별 · 국가×품목 · 시도별 품목 · 선박 인천) · v3/kr_apis.py(시도별 품목 연도 · 과세환율 주간 · 국가별 월)
            · v3/kcci.py(KCCI 주간) · v3/portwatch.py(초크포인트 통항) · v3/iiac_cargo.py(인천공항 항공화물 · 반기)
            · vessel.py --recent 3(항만별 선박입출항) · 인천해수청 컨테이너(analysis/collect_terminal_monthly.py → long 파일에 병합)
  ② 파생 — race_derive · fx_derive · vessel_derive · flows_derive · supply_derive · choke_derive · forecast_teu --issue(예측 원장 덧붙이기)
  ③ 신선도 — data/derived/freshness.json: 원천마다 「지면이 쓰는 기준기(ours)」·「원천이 낸 마지막 기준기(source_latest)」·
            마지막 확인일·다음 공표 예정. 시험(tests/freshness.spec.mjs)이 ours < source_latest 를 빨강으로 잡는다.
한 단계가 실패해도 지난 파일을 지키고 다음 단계로 간다(각 스크립트가 「덜 오면 지난 파일을 지킨다」). 실패는 freshness.json 과 요약에 남는다.
  python tools-build/refresh.py [--only id,id] [--skip-fetch] [--freshness-only] [--selftest] [--changed]
"""
import csv, datetime, json, os, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRESH = os.path.join(ROOT, "data/derived/freshness.json")
SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    if SUMMARY:
        with open(SUMMARY, "a", encoding="utf-8") as f: f.write(line + "\n")


def J(rel):
    p = os.path.join(ROOT, rel)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def last_csv(rel, col, where=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p): return None
    v = [r[col] for r in csv.DictReader(open(p, encoding="utf-8-sig")) if r.get(col) and (where is None or where(r))]
    return max(v) if v else None


def ym(s):
    """여러 꼴(202609 · 2026-09 · 2026-09-30)을 비교 가능한 「YYYY-MM」 또는 「YYYY-MM-DD」로."""
    if not s: return None
    s = str(s)
    if len(s) == 6 and s.isdigit(): return f"{s[:4]}-{s[4:]}"
    if len(s) == 8 and s.isdigit(): return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


# ① 받기·② 파생 — (id, 하는 일, 명령, 작업 폴더, 제한 초). 받기 단계는 원천 하나와 짝이다(freshness 의 id 와 같다).
STEPS = [
    ("collect", "공공데이터포털 월 원천(항구·공항별 · 국가×품목 · 시도별 품목 · 선박 인천)", [sys.executable, "tools-build/collect.py"], ".", 1500),
    ("kr-apis", "시도별 품목 연도 · 과세환율 주간 · 국가별 월", [sys.executable, "kr_apis.py"], "tools-build/v3", 900),
    ("kcci", "KCCI 주간", [sys.executable, "kcci.py"], "tools-build/v3", 600),
    ("portwatch", "PortWatch 초크포인트 통항", [sys.executable, "portwatch.py"], "tools-build/v3", 1200),
    ("iiac", "인천공항 항공화물(반기 파일)", [sys.executable, "iiac_cargo.py"], "tools-build/v3", 600),
    ("vessel", "항만별 선박입출항(최근 3달)", [sys.executable, "tools-build/vessel.py", "--recent", "3"], ".", 900),
    ("teu", "인천해수청 컨테이너(최근 3달 → long 병합)", None, ".", 900),
    # [2026-10-21 과제 1 · 홈 세 축] 수도권(서울·인천·경기) 시도별 수출입 — 13달 쌓기(이미 받은 달은 건너뜀 · 마지막 두 달만 다시)
    ("sudo-trade", "관세청 시도별 품목별(수도권 세 시도 + 전국 분모)", [sys.executable, "tools-build/sudo_trade.py"], ".", 1500),
    # 유통 축 KOSIS — 시크릿 KOSIS_KEY 가 없으면 아무것도 안 쓰고 0(키 발급 = 선장님)
    ("kosis", "통계청 KOSIS 유통·소비(키 있을 때만)", [sys.executable, "tools-build/kosis.py"], ".", 600),
    # [2026-10-21 숫자 전수 ③→①] 달마다 다시 계산하는 바탕 층 — 때가 된 날만 돈다(periodic.py · 종료 75 = 건너뜀). --only 로 부르면 때와 상관없이 돈다
    ("iso", "배송 등시선 — OSM 도로망 · 카카오 내비 대조 · 시간대 배율(월 1회)", [sys.executable, "tools-build/periodic.py", "iso"], ".", 3000),
    ("tariff", "관세율표 — 공공데이터포털 파일 15051179(월 1회 확인)", [sys.executable, "tools-build/periodic.py", "tariff"], ".", 900),
    ("derive", "파생 일곱 + 예측 원장", None, ".", 900),
]
DERIVE = [
    ([sys.executable, "race_derive.py"], "tools-build/v3"),
    ([sys.executable, "fx_derive.py"], "tools-build/v3"),
    ([sys.executable, "tools-build/vessel_derive.py"], "."),
    ([sys.executable, "tools-build/flows_derive.py"], "."),
    ([sys.executable, "tools-build/supply_derive.py"], "."),
    ([sys.executable, "choke_derive.py"], "tools-build/v3"),
    ([sys.executable, "tools-build/axes_derive.py"], "."),  # 홈 세 축(물류·무역·유통) — home_flows · 컨테이너 · 외항선 · 수도권 시도별 · KOSIS 를 읽는다
    # 수요예측 원장 — 새 실제값 달 T 가 들어오면 T+1~T+3 예측을 같은 커밋에 덧붙인다(이미 낸 기준월이면 아무것도 안 함 · 발행 창 F2 =
    # 예측이 그 달 실제값보다 먼저 main 에 — 이 커밋의 예측은 아직 안 나온 달만 겨눈다 · 검사 tools-build/check_ledger.py)
    ([sys.executable, "analysis/forecast_teu.py", "--issue"], "."),
]

PERIODIC = {"iso", "tariff"}  # periodic.py 층

LONG = "analysis/terminal_monthly_long.csv"
LONG_KEY = ("기준연월", "계층", "터미널")


def merge_long(new_rel):
    """collect_terminal_monthly.py 가 쓴 최근 달 표를 long 파일에 합친다 — 같은 (기준연월·계층·터미널)은 새 값, 나머지는 그대로."""
    old_p, new_p = os.path.join(ROOT, LONG), os.path.join(ROOT, new_rel)
    old = list(csv.DictReader(open(old_p, encoding="utf-8-sig")))
    new = list(csv.DictReader(open(new_p, encoding="utf-8-sig")))
    if not new: return 0, None
    cols = list(old[0].keys())
    if set(new[0].keys()) != set(cols): raise RuntimeError(f"열이 다르다 — 병합하지 않는다: {sorted(set(new[0]) ^ set(cols))}")
    k = lambda r: tuple(r[c] for c in LONG_KEY)
    idx = {k(r): i for i, r in enumerate(old)}
    added = 0
    for r in new:
        if k(r) in idx: old[idx[k(r)]] = r
        else: old.append(r); added += 1
    old.sort(key=lambda r: (r["기준연월"], cols.index("계층") and 0))
    # 원래 파일의 달 안 순서(합계 → 부두군 → 터미널)를 지킨다 — 달끼리만 정렬(안정 정렬)
    with open(old_p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(old)
    return added, max(r["기준연월"] for r in new)


def merge_sources(new_rel):
    """받은 달의 출처 대장(첨부 URL · 바이트 · SHA256)을 long 파일의 대장에 합친다 — 같은 기준연월은 새 줄."""
    old_p, new_p = os.path.join(ROOT, LONG.replace(".csv", "_sources.csv")), os.path.join(ROOT, new_rel)
    if not os.path.exists(new_p): return
    old = list(csv.DictReader(open(old_p, encoding="utf-8-sig")))
    new = list(csv.DictReader(open(new_p, encoding="utf-8-sig")))
    by = {r["기준연월"]: r for r in old}
    for r in new: by[r["기준연월"]] = r
    with open(old_p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, list(old[0].keys())); w.writeheader(); w.writerows(sorted(by.values(), key=lambda r: r["기준연월"]))
    os.remove(new_p)


def run(cmd, cwd, limit):
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=os.path.join(ROOT, cwd), timeout=limit, capture_output=True, text=True)
        out = (r.stdout + r.stderr)[-1500:]
        return r.returncode, out, time.time() - t0
    except subprocess.TimeoutExpired:
        return 124, f"{limit}초 넘음", time.time() - t0


# ③ 신선도 — 원천 표. ours = 지면이 쓰는 기준기 · latest = 원천이 낸 마지막 기준기(받기 결과에서 읽는다).
# 다음 공표 예정 = 원천 주기 규칙(cadence) — 관측에서 정한 규칙이라 「무렵」으로 적는다(기관이 날짜를 약속하지 않는다).
#   monthly(lag) = 다음 기준달이 끝난 뒤 lag 일 · weekly(lag) = 마지막 기준일 + 7 + lag 일 · semiannual(lag) = 다음 반기 말 + lag 일
SOURCES = [
    {"id": "kcs-porttrade", "label": "관세청 항구·공항별 수출입실적", "pages": ["홈"], "step": "collect", "cadence": ["monthly", 15],
     "ours": lambda: (J("data/derived/home_flows.json") or {}).get("last"),
     "latest": lambda: ym(last_csv("data/collected/porttrade.csv", "reqYm"))},
    {"id": "kcs-nation", "label": "관세청 국가별 수출입실적", "pages": ["홈 나라별 몫", "초크포인트"], "step": "kr-apis", "cadence": ["monthly", 15],
     "ours": lambda: ym(max(((J("data/derived/chokepoints.json") or {}).get("months") or [None]))),
     "latest": lambda: ym(max(((J("data/collected/v3/nation_months.json") or {}).get("months") or {}).keys(), default=None))},
    {"id": "kcs-sido-item", "label": "관세청 시도별 품목별 수출입실적(인천)", "pages": ["품목 트리맵"], "step": "kr-apis", "cadence": ["monthly", 15],
     "ours": lambda: ym(((J("data/derived/trade_race.json") or {}).get("years") or [{}])[-1].get("through")),
     "latest": lambda: ym(max((y.get("through") or "" for y in ((J("data/collected/v3/sido_item_years.json") or {}).get("years") or {}).values()), default=None) or None)},
    {"id": "kcs-fx", "label": "관세청 관세환율(수입 · 주간)", "pages": ["수입원가"], "step": "kr-apis", "cadence": ["weekly", 0],
     "ours": lambda: ym(((J("data/derived/import_cost.json") or {}).get("example") or {}).get("now", {}).get("week")),
     "latest": lambda: ym(max((w.get("from") for w in ((J("data/collected/v3/kcs_fx_weeks.json") or {}).get("weeks") or []) if w.get("from")), default=None))},
    {"id": "kobc-kcci", "label": "한국해양진흥공사 KCCI(주간)", "pages": ["수입원가 운임 칸"], "step": "kcci", "cadence": ["weekly", 1],
     "ours": lambda: ((J("data/derived/import_cost.json") or {}).get("kcci") or {}).get("last_week"),
     "latest": lambda: max((w.get("date") for w in ((J("data/collected/v3/kcci_weeks.json") or {}).get("weeks") or []) if w.get("date")), default=None)},
    {"id": "imf-portwatch", "label": "IMF PortWatch 길목 통항", "pages": ["초크포인트"], "step": "portwatch", "cadence": ["weekly", 3],
     "ours": lambda: max((p.get("asof") or "" for p in ((J("data/derived/chokepoints.json") or {}).get("points") or [])), default=None) or None,
     "latest": lambda: max((v[-1].get("date") or "" for v in ((J("data/collected/v3/portwatch_chokepoints.json") or {}).get("chokepoints") or {}).values() if v), default=None) or None},
    {"id": "mof-vessel", "label": "해양수산부 항만별 선박입출항실적", "pages": ["외항선 입항 추이", "노트 전년비"], "step": "vessel", "cadence": ["monthly", 20],
     "ours": lambda: ((J("data/derived/vessel_replay.json") or {}).get("latest") or {}).get("ym"),
     "latest": lambda: max(filter(None, [ym(((J("data/collected/vessel-monthly.json") or {}).get("months") or [None, None])[-1]), ym(last_csv("data/collected/vessel-harbor.csv", "useYm"))]), default=None)},
    {"id": "mof-incheon-port-stats", "label": "인천지방해양수산청 월별 항만운영통계(컨테이너)", "pages": ["홈 컨테이너", "노트 전년비", "수요예측"], "step": "teu", "cadence": ["monthly", 30],
     "ours": lambda: last_csv(LONG, "기준연월"),
     "latest": None},  # 원천 게시판의 마지막 달 = 받기 단계가 적는다(teu_latest)
    {"id": "kcs-sido-sudo", "label": "관세청 시도별 품목별 수출입실적(수도권 · 전국)", "pages": ["홈 무역·유통 축"], "step": "sudo-trade", "cadence": ["monthly", 15],
     "ours": lambda: ym((J("data/derived/home_axes.json") or {}).get("trade", {}).get("ym")),
     "latest": lambda: ym(max(((J("data/collected/v3/sudo_trade.json") or {}).get("months") or {}).keys(), default=None))},
    {"id": "kosis-retail", "label": "통계청 KOSIS 온라인쇼핑·소매판매", "pages": ["홈 유통 축"], "step": "kosis", "cadence": ["monthly", 35],
     "when": lambda: os.path.exists(os.path.join(ROOT, "data/collected/v3/kosis_retail.json")),  # 키가 들어와 한 번이라도 받은 뒤부터 잰다
     "ours": lambda: ym(((J("data/derived/home_axes.json") or {}).get("retail") or {}).get("kosis", {}).get("ym")),
     "latest": lambda: ym(max((r["ym"] for t in ((J("data/collected/v3/kosis_retail.json") or {}).get("tables") or {}).values() for r in (t.get("rows") or [])), default=None))},
    # 우리가 다시 계산하는 층 — 원천(OSM 은 매일 · 관세율표는 개정 때) 대신 우리 재계산 주기로 잰다(recompute · 다음 = 마지막 확인 + 주기)
    {"id": "osm-reach", "label": "OpenStreetMap 도로망 등시선 · 카카오 내비 대조(우리 재계산)", "pages": ["배송 등시선", "도구 목록"], "step": "iso", "cadence": ["recompute", 28],
     "ours": lambda: (J("data/derived/isochrones.json") or {}).get("made"),
     "latest": lambda: (J("data/derived/isochrones.json") or {}).get("made")},
    {"id": "kcs-tariff", "label": "관세청 품목번호별 관세율표(파일 · 우리 확인)", "pages": ["수입원가"], "step": "tariff", "cadence": ["recompute", 28],
     "ours": lambda: ym((J("data/derived/tariff_codes.json") or {}).get("asof")),
     "latest": lambda: ym((J("data/derived/tariff_codes.json") or {}).get("asof"))},
    {"id": "iiac-route-cargo", "label": "인천국제공항공사 항공사별 노선별 운송실적(반기 파일)", "pages": ["홈 지도"], "step": "iiac", "cadence": ["semiannual", 31],
     "ours": lambda: ((J("data/derived/home_flows.json") or {}).get("air_cargo") or {}).get("through"),
     "latest": lambda: (J("data/derived/air_cargo.json") or {}).get("through")},
]


def add_months(y, m, k):
    m += k
    while m > 12: y, m = y + 1, m - 12
    while m < 1: y, m = y - 1, m + 12
    return y, m


def next_expected(cad, latest):
    """원천이 다음 기준기를 낼 날(추정). latest 가 없으면 None."""
    if not latest: return None
    kind, lag = cad
    if kind == "recompute":  # 우리 재계산 — 마지막 확인일 + 주기
        return (datetime.date.fromisoformat(latest[:10]) + datetime.timedelta(days=lag)).isoformat()
    if kind == "weekly":
        d = datetime.date.fromisoformat(latest[:10]) if len(latest) >= 10 else None
        return (d + datetime.timedelta(days=7 + lag)).isoformat() if d else None
    y, m = int(latest[:4]), int(latest[5:7])
    if kind == "monthly":
        ny, nm = add_months(y, m, 2)  # 다음 기준달(m+1)이 끝난 다음 달 1일
        return (datetime.date(ny, nm, 1) + datetime.timedelta(days=lag - 1)).isoformat()
    if kind == "semiannual":
        ny, nm = add_months(y, m, 7)  # 다음 반기 말(m+6)이 끝난 다음 달 1일
        return (datetime.date(ny, nm, 1) + datetime.timedelta(days=lag - 1)).isoformat()
    return None


def max_age_days(cad):
    """마지막 확인이 이보다 오래면 갱신 사슬이 멈춘 것 — 시험이 빨강(freshness.json max_age). 재계산 층은 주기 + 10일."""
    return cad[1] + 10 if cad[0] == "recompute" else 10


def freshness(results, teu_latest, today):
    old = (J("data/derived/freshness.json") or {}).get("sources") or {}
    out = {}
    for s in SOURCES:
        if s.get("when") and not s["when"](): continue
        prev = old.get(s["id"], {})
        ran = results.get(s["step"])  # None = 이번에 안 돌림(--only · --skip-fetch)
        latest = teu_latest if s["id"] == "mof-incheon-port-stats" else (s["latest"]() if s["latest"] else None)
        if s["id"] == "mof-incheon-port-stats" and not latest: latest = prev.get("source_latest")
        ok = ran is not None and ran[0] == 0
        rec = {
            "label": s["label"], "pages": s["pages"], "cadence": s["cadence"],
            "ours": s["ours"](),
            "source_latest": latest or prev.get("source_latest"),
            "checked": today if ok else prev.get("checked"),
            "last_error": None if ok else (prev.get("last_error") if ran is None else f"{s['step']} rc={ran[0]} {ran[1][-300:]}"),
        }
        rec["next_expected"] = next_expected(s["cadence"], rec["checked"] if s["cadence"][0] == "recompute" else rec["source_latest"])
        rec["max_age"] = max_age_days(s["cadence"])
        rec["behind"] = bool(rec["ours"] and rec["source_latest"] and str(rec["ours"]) < str(rec["source_latest"]))
        out[s["id"]] = rec
    data = {"_설명": "원천별 신선도 — tools-build/refresh.py 가 쓴다. ours = 지면 기준기 · source_latest = 원천이 낸 마지막 기준기(마지막 확인 때) · next_expected = 다음 공표 예정(관측 주기 규칙 · 추정). 시험 tests/freshness.spec.mjs.",
            "made": today, "sources": out}
    json.dump(data, open(FRESH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return data


def main():
    if "--freshness-only" in sys.argv:  # 받기·파생 없이 지금 파일로 신선도만 다시 쓴다(확인일은 그대로 — 원천에 닿지 않았다)
        freshness({}, None, datetime.date.today().isoformat()); return 0
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    skip_fetch = "--skip-fetch" in sys.argv
    today = datetime.date.today().isoformat()
    results, teu_latest = {}, None
    say("## 자동 갱신", today)
    for sid, what, cmd, cwd, limit in STEPS:
        if only and sid not in only: continue
        if skip_fetch and sid not in ("derive",): continue
        if sid == "teu":
            tmp = "data/collected/terminal_recent.csv"
            rc, out, sec = run([sys.executable, "analysis/collect_terminal_monthly.py", "--limit", "3", "--out", tmp], ".", limit)
            if rc == 0 and os.path.exists(os.path.join(ROOT, tmp)):
                try:
                    added, teu_latest = merge_long(tmp)
                    out = f"long 병합 — 새 행 {added} · 원천 마지막 달 {teu_latest}"
                except Exception as ex:
                    rc, out = 1, f"병합 실패: {ex}"
                os.remove(os.path.join(ROOT, tmp))
                merge_sources(tmp.replace(".csv", "_sources.csv"))
            results[sid] = (rc, out)
        elif sid == "derive":
            bad = []
            for c, d in DERIVE:
                rc, out, sec = run(c, d, limit)
                if rc != 0: bad.append(f"{' '.join(c[1:])} rc={rc} {out[-200:]}")
            results[sid] = (1 if bad else 0, "; ".join(bad) or "파생 통과")
            rc, out = results[sid]
        else:
            rc, out, sec = run(cmd + (["--force"] if only and sid in PERIODIC else []), cwd, limit)
            if rc == 75 and sid in PERIODIC:  # 때가 아님 — 「안 돌림」으로 센다(확인일·오류를 바꾸지 않는다)
                say(f"- · {sid} — {what}: {out.strip().splitlines()[-1][:200] if out.strip() else '건너뜀'}"); continue
            results[sid] = (rc, out)
        say(f"- {'✓' if results[sid][0] == 0 else '✗'} {sid} — {what}: {results[sid][1].strip().splitlines()[-1][:200] if results[sid][1].strip() else ''}")
    data = freshness(results, teu_latest, today)
    say("", "| 원천 | 지면 기준기 | 원천 마지막 | 확인일 | 다음 공표 예정 | 뒤처짐 |", "|---|---|---|---|---|---|")
    for k, r in data["sources"].items():
        say(f"| {r['label']} | {r['ours']} | {r['source_latest']} | {r['checked']} | {r['next_expected']} | {'**뒤처짐**' if r['behind'] else '—'} |")
    # 받기가 하나라도 실패해도 종료 코드는 0 — 지난 파일을 지켰고, 무엇이 실패했는지는 freshness 와 요약에 남았다.
    # 뒤처짐(ours < source_latest)은 시험이 빨강으로 잡는다(배포 전에 막힌다).
    return 0


# 받은 시각·확인 시각만 바뀐 파일은 「원천이 새로 낸 것」이 아니다 — 그런 날은 커밋·배포하지 않는다(10-21 브랜치 실행에서 시각 줄만 바뀐 커밋이 났다).
STAMP_KEYS = {"fetched", "fetched_at", "checked", "made", "computed", "generated", "run_at"}


def strip_stamps(o):
    if isinstance(o, dict): return {k: strip_stamps(v) for k, v in o.items() if k not in STAMP_KEYS}
    if isinstance(o, list): return [strip_stamps(v) for v in o]
    return o


def substantive(old_text, new_text, name):
    """두 판이 시각 키를 빼고도 다른가. JSON 이 아니면 글 그대로 견준다."""
    if old_text == new_text: return False
    if name.endswith(".json"):
        try: return strip_stamps(json.loads(old_text)) != strip_stamps(json.loads(new_text))
        except ValueError: return True
    return True


def changed_files():
    """git 색인에 올린 파일 중 시각 밖이 바뀐 것만(새 파일은 늘 바뀐 것). refresh.yml 「바뀐 것」 단계가 부른다."""
    names = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    out = []
    for n in names:
        old = subprocess.run(["git", "show", f"HEAD:{n}"], cwd=ROOT, capture_output=True, text=True)
        new = subprocess.run(["git", "show", f":{n}"], cwd=ROOT, capture_output=True, text=True)
        if old.returncode != 0 or new.returncode != 0 or substantive(old.stdout, new.stdout, n): out.append(n)
    return out


def selftest():
    assert ym("202609") == "2026-09" and ym("20261018") == "2026-10-18" and ym("2026-09") == "2026-09"
    assert next_expected(["monthly", 15], "2026-09") == "2026-11-15"
    assert next_expected(["monthly", 30], "2026-08") == "2026-10-30"
    assert next_expected(["weekly", 0], "2026-10-18") == "2026-10-25"
    assert next_expected(["semiannual", 31], "2026-06") == "2027-01-31"
    assert next_expected(["monthly", 15], "2026-12") == "2027-02-15"
    assert not substantive('{"fetched": "2026-10-20", "a": [1, {"checked": "x"}]}', '{"fetched": "2026-10-21", "a": [1, {"checked": "y"}]}', "x.json")
    assert substantive('{"fetched": "2026-10-20", "to": "2026-10-09"}', '{"fetched": "2026-10-21", "to": "2026-10-16"}', "x.json")
    assert next_expected(["recompute", 28], "2026-10-21") == "2026-11-18" and max_age_days(["recompute", 28]) == 38 and max_age_days(["monthly", 15]) == 10
    print("selftest 9/9 ok"); return 0


if __name__ == "__main__":
    if "--changed" in sys.argv:
        print("\n".join(changed_files())); sys.exit(0)
    sys.exit(selftest() if "--selftest" in sys.argv else main())

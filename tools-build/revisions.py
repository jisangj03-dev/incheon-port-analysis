"""원천 정정 감지 · 정정 이력 · 증감 문구 재검토(2026-11-02 — 링크드인 질문 「원천에서 지난달 수치가 정정되면 자동 갱신 때 설명 문구도
함께 다시 확인하느냐」에 「정정 사실 표시·문구 재검토 단계는 없다, 보완하겠다」고 공개 답장한 것의 이행).

자동 갱신(refresh)이 원천을 다시 받을 때 **이미 갖고 있던 기준기(지난달 이전)의 값**이 원천에서 바뀌었는지 본다.
  ① 감지 — 원천 파일마다 「(지표, 기준기) → 값」을 뽑아 지난 커밋(HEAD)판과 지금판을 견준다. 두 판에 다 있는 칸만 센다 — 새 달은 정정이 아니다.
  ② 기록 — 바뀐 칸마다 data/revisions.csv 에 한 줄(감지일 KST · 원천 · 지표 · 기준기 · 옛 값 · 새 값 · 단위). 같은 줄은 두 번 쓰지 않는다.
  ③ 문구 — 숫자는 자동으로 바뀌어도 그 옆 말(「늘었다」·「작년보다」)은 그대로 남을 수 있다. 그래서 둘을 다시 잰다.
       · 지면 숫자(data/derived/facts.json)가 **같은 기준기인데** 부호가 뒤집혔으면 --check 가 종료 3 — refresh 는 main 에 쓰지 않고
         문장 확인 PR 을 연다(해석 문장 뒤집힘과 같은 길 · 머지 = 사람이 문구를 본 뒤 승인).
       · 같은 기준기인데 값만 바뀌었으면(부호 그대로) 경보 줄만 — 방향 말은 그대로 맞다.
       · 정정된 칸이 낀 증감(직전 기준기 대비 · 전년 같은 달 대비)의 방향이 뒤집혔으면 요약에 경보 줄(지면에 그 증감이 없을 수도 있다).
       해석 문장 대장(data/claims.json)의 조건은 facts.py --check 가 이미 다시 잰다 — 여기서 겹쳐 보지 않는다.
닿지 않는 곳: 날짜를 박은 발행본(노트·보고서)은 그날의 기록이라 고치지 않는다(§3-11) — 정정 이력이 그 뒤의 정정을 알린다.
  아래 SERIES 에 없는 원천은 ① 이 못 본다. 다만 ③ 의 지면 숫자 비교는 원천을 가리지 않는다(같은 기준기에서 값이 바뀌면 원천이 고친 것이다).

  python tools-build/revisions.py                 감지 · 대장에 덧붙이기(refresh.py 가 파생 뒤에 부른다)
  python tools-build/revisions.py --check         감지 + 지면 숫자 대조(쓰지 않음) · 지면 숫자 방향이 정정으로 뒤집혔으면 종료 3 · 출력 = 마크다운 줄
  python tools-build/revisions.py --base <rev>    견줄 옛판(기본 HEAD)
  python tools-build/revisions.py --backfill <rev>  소급 — <rev> 뒤 main 커밋끼리 되짚어 이력에 「소급 기록」으로 덧붙인다(2026-11-02 한 번 · 자동 갱신 첫날부터)
  python tools-build/revisions.py --selftest
"""
import csv, datetime, io, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = "data/revisions.csv"
COLS = ["감지일", "원천", "지표", "기준기", "옛 값", "새 값", "단위", "비고"]  # 비고 = 「소급 기록(git …)」 — 견주기를 넣기 전 갱신분을 git 이력에서 되짚은 줄
SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    if SUMMARY:
        with open(SUMMARY, "a", encoding="utf-8") as f: f.write(line + "\n")


def kst_today():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()


def num(v):
    try: return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError): return None


def rows(t): return list(csv.DictReader(io.StringIO(t.lstrip("﻿"))))


def put(out, ind, per, v):
    v = num(v)
    if v is not None and per: out[(ind, str(per))] = round(out.get((ind, str(per)), 0.0) + v, 6)


# ── 원천별 뽑기: 파일 글 → {(지표, 기준기): 값} ── 지면 숫자가 기대는 칸을 원천 단위 그대로 든다(파생 전 값)
def p_porttrade(t):
    o = {}
    for r in rows(t):
        put(o, f"{r['statKor']} 수입액", r["reqYm"], r["impDlr"]); put(o, f"{r['statKor']} 수출액", r["reqYm"], r["expDlr"])
    return o


def p_nitem(t):
    o = {}
    for r in rows(t):
        k = f"{r['cntyCd']} HS{r['hsCd2']}"
        put(o, f"{k} 수입액", r["reqYm"], r["impDlr"]); put(o, f"{k} 수출액", r["reqYm"], r["expDlr"])
    return o


def p_sido_incheon(t):
    o = {}
    for r in rows(t):
        k = "인천 총계" if r.get("priodTitle") == "총계" else f"인천 HS{r.get('hsSgn')}"
        put(o, f"{k} 수입액", r["reqYm"], r["impUsdAmt"]); put(o, f"{k} 수출액", r["reqYm"], r["expUsdAmt"])
    return o


def p_nation(t):
    o = {}
    for m, xs in (json.loads(t).get("months") or {}).items():
        for x in xs: put(o, f"{x.get('name') or x.get('c')} 수입액", m, x.get("imp")); put(o, f"{x.get('name') or x.get('c')} 수출액", m, x.get("exp"))
    return o


def p_sido_years(t):
    """연도 줄은 그해 누계라 다음 달이 들어오면 저절로 커진다 — 기준기를 「연도(~마지막 달)」로 잡아 같은 누계끼리만 견준다."""
    o = {}
    for y, Y in (json.loads(t).get("years") or {}).items():
        per = f"{y}(~{Y.get('through')})"
        for r in Y.get("rows") or []:
            k = "인천 총계" if r.get("priodTitle") == "총계" else f"인천 HS{r.get('hsSgn')}"
            put(o, f"{k} 수입액", per, r.get("impUsdAmt")); put(o, f"{k} 수출액", per, r.get("expUsdAmt"))
    return o


def p_fx(t):
    o = {}
    for w in json.loads(t).get("weeks") or []:
        for k, v in w.items():
            if k != "from": put(o, f"관세환율 {k}", w.get("from"), v)
    return o


def p_kcci(t):
    o = {}
    for w in json.loads(t).get("weeks") or []:
        for k, v in w.items():
            if k != "date": put(o, k, w.get("date"), v)
    return o


def p_portwatch(t):
    o = {}
    for name, xs in (json.loads(t).get("chokepoints") or {}).items():
        for x in xs: put(o, f"{name} 통항(척)", x.get("date"), x.get("n_total"))
    return o


def p_vessel(t):
    o = {}
    for r in rows(t): put(o, f"{r['port']} {r['kind']} 입항", r["ym"], r["etr_cnt"])
    return o


def p_vessel_harbor(t):
    o = {}
    for r in rows(t): put(o, f"{r['prtAgNm']} {r['nm']} 입항", r["useYm"], r["etrVsslCo"])
    return o


def p_teu(t):
    o = {}
    for r in rows(t): put(o, f"{r['터미널']}({r['계층']}) 당월", r["기준연월"], r["당월_천TEU"])
    return o


def p_sudo(t):
    D = json.loads(t)
    name = D.get("sudo") or {}
    o = {}
    for m, by in (D.get("months") or {}).items():
        for c, x in by.items():
            s = name.get(c, f"시도{c}")
            put(o, f"{s} 총계 수입액", m, (x.get("tot") or {}).get("imp")); put(o, f"{s} 총계 수출액", m, (x.get("tot") or {}).get("exp"))
            for h, y in (x.get("hs") or {}).items(): put(o, f"{s} HS{h} 수입액", m, y.get("imp")); put(o, f"{s} HS{h} 수출액", m, y.get("exp"))
    return o


def p_kosis(t):
    o = {}
    for tid, T in (json.loads(t).get("tables") or {}).items():
        for r in T.get("rows") or []: put(o, f"{T.get('want') or tid} · {r.get('c')} · {r.get('item')}", r.get("ym"), r.get("v"))
    return o


def p_air(t):
    D = json.loads(t)
    per = f"{(D.get('months') or ['?'])[0]}~{D.get('through')}"
    o = {}
    put(o, "도착 화물(톤)", per, D.get("total_in_t")); put(o, "출발 화물(톤)", per, D.get("total_out_t"))
    for k, v in (D.get("kind_t") or {}).items(): put(o, f"{k}(톤)", per, v)
    return o


# (원천 id = freshness.json 의 id · 이름 · 파일 · 뽑기 · 단위). 지면에 숫자를 싣는 원천 전부 — 새 원천을 붙이면 여기 한 줄.
SERIES = [
    ("kcs-porttrade", "관세청 항구·공항별 수출입실적", "data/collected/porttrade.csv", p_porttrade, "달러"),
    ("kcs-nitemtrade", "관세청 국가별 품목별 수출입실적", "data/collected/nitemtrade.csv", p_nitem, "달러"),
    ("kcs-sido-item", "관세청 시도별 품목별 수출입실적(인천 · 월)", "data/collected/sido-item-incheon.csv", p_sido_incheon, "천 달러"),
    ("kcs-sido-item", "관세청 시도별 품목별 수출입실적(인천 · 연 누계)", "data/collected/v3/sido_item_years.json", p_sido_years, "천 달러"),
    ("kcs-nation", "관세청 국가별 수출입실적", "data/collected/v3/nation_months.json", p_nation, "달러"),
    ("kcs-fx", "관세청 관세환율(주간)", "data/collected/v3/kcs_fx_weeks.json", p_fx, "원"),
    ("kobc-kcci", "한국해양진흥공사 KCCI(주간)", "data/collected/v3/kcci_weeks.json", p_kcci, "지수"),
    ("imf-portwatch", "IMF PortWatch 길목 통항", "data/collected/v3/portwatch_chokepoints.json", p_portwatch, "척"),
    ("mof-vessel", "해양수산부 항만별 선박입출항실적", "data/collected/vessel-monthly.csv", p_vessel, "척"),
    ("mof-vessel", "해양수산부 항만별 선박입출항실적(인천 항별)", "data/collected/vessel-harbor.csv", p_vessel_harbor, "척"),
    ("mof-incheon-port-stats", "인천지방해양수산청 월별 항만운영통계(컨테이너)", "analysis/terminal_monthly_long.csv", p_teu, "천 TEU"),
    ("kcs-sido-sudo", "관세청 시도별 품목별 수출입실적(수도권 · 전국)", "data/collected/v3/sudo_trade.json", p_sudo, "천 달러"),
    ("kosis-retail", "국가통계포털(KOSIS) 대형소매점·온라인쇼핑", "data/collected/v3/kosis_retail.json", p_kosis, "백만 원"),
    ("iiac-route-cargo", "인천국제공항공사 항공사별 노선별 운송실적(반기)", "data/derived/air_cargo.json", p_air, "톤"),
]


def read(rel, base):
    """base = None 이면 작업 폴더판, 아니면 그 커밋판. 없으면 None."""
    if base is None:
        p = os.path.join(ROOT, rel)
        return open(p, encoding="utf-8-sig").read() if os.path.exists(p) else None
    r = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=ROOT, capture_output=True)
    return r.stdout.decode("utf-8-sig") if r.returncode == 0 else None


def parse(fn, t):
    if not t: return {}
    try: return fn(t)
    except Exception as ex:  # 꼴이 바뀐 파일 — 정정 감지는 건너뛴다(형식 경보는 refresh 의 받기 단계가 낸다)
        say(f"  · 정정 감지 건너뜀 — 읽기 실패 {type(ex).__name__}: {ex}"); return {}


def fmt(v):
    return str(int(v)) if float(v).is_integer() else f"{v:.6g}"


def changes(old, new):
    """두 판에 다 있는 칸 중 값이 다른 것 — [(지표, 기준기, 옛, 새)]."""
    return sorted((k[0], k[1], old[k], new[k]) for k in old.keys() & new.keys() if old[k] != new[k])


MONTH = re.compile(r"^(\d{4})(-?)(\d{2})$")


def shift(per, k):
    m = MONTH.match(per)
    if not m: return None
    y, mo = int(m.group(1)), int(m.group(3)) + k
    y, mo = y + (mo - 1) // 12, (mo - 1) % 12 + 1
    return f"{y:04d}{m.group(2)}{mo:02d}"


def sgn(x): return "+" if x > 0 else "−" if x < 0 else "±"


def flips(old, new, revised):
    """정정된 칸이 낀 증감 — 직전 기준기 대비 · 전년 같은 달 대비 — 의 방향이 옛판과 새판에서 다른 것."""
    pers = {}
    for ind, per in new: pers.setdefault(ind, []).append(per)
    for v in pers.values(): v.sort()
    out, seen = [], set()
    for ind, per, _, _ in revised:
        P = pers.get(ind, [])
        i = P.index(per) if per in P else -1
        if MONTH.match(per):  # 달 — 바로 앞뒤 달과 작년·내년 같은 달(빠진 달을 건너뛰어 견주지 않는다)
            pairs = [("직전 기준기 대비", shift(per, -1), per), ("직전 기준기 대비", per, shift(per, 1)),
                     ("전년 같은 달 대비", shift(per, -12), per), ("전년 같은 달 대비", per, shift(per, 12))]
        else:  # 주·날·반기 — 받은 판에서 바로 앞뒤 기준기
            pairs = ([("직전 기준기 대비", P[i - 1], per)] if i > 0 else []) + ([("직전 기준기 대비", per, P[i + 1])] if 0 <= i < len(P) - 1 else [])
        for kind, a, b in pairs:
            ka, kb = (ind, a), (ind, b)
            if (ind, kind, a, b) in seen or not all(k in old and k in new for k in (ka, kb)): continue
            seen.add((ind, kind, a, b))
            o, n = old[kb] - old[ka], new[kb] - new[ka]
            if sgn(o) != sgn(n): out.append({"지표": ind, "비교": kind, "앞": a, "뒤": b, "옛": sgn(o), "새": sgn(n)})
    return out


def detect(base="HEAD", head=None, rels=None):
    """원천마다 정정된 칸과 그 때문에 뒤집힌 증감. [{id, label, unit, revised, flips}] — 정정 0 인 원천은 뺀다.
    head = None 이면 작업 폴더판과 견준다 · rels = 이 파일들만(소급 때 그 커밋이 바꾼 파일만 읽는다)."""
    out = []
    for sid, label, rel, fn, unit in SERIES:
        if rels is not None and rel not in rels: continue
        old, new = parse(fn, read(rel, base)), parse(fn, read(rel, head))
        rv = changes(old, new)
        if rv: out.append({"id": sid, "label": label, "unit": unit, "revised": rv, "flips": flips(old, new, rv)})
    return out


def append_ledger(found, today, note=""):
    p = os.path.join(ROOT, LEDGER)
    have = list(csv.DictReader(open(p, encoding="utf-8-sig"))) if os.path.exists(p) else []
    seen = {tuple(r[c] for c in COLS[1:6]) for r in have}
    add = []
    for s in found:
        for ind, per, o, n in s["revised"]:
            key = (s["label"], ind, per, fmt(o), fmt(n))
            if key in seen: continue
            seen.add(key); add.append(dict(zip(COLS, (today, *key, s["unit"], note))))
    if add or not os.path.exists(p):
        with open(p, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(have + add)
    return len(add)


SUMMARY_JSON = "data/derived/revisions.json"


# 지면 예시 줄 단위 — 원천 단위(백만 원·천 달러)는 지면의 억·조 표기와 안 이어진다(2026-11-03 화면 판정 경미). 바꾼 값은 요약 파일에 같이 적는다(지면 숫자 ⊂ 데이터 파일)
SHOW_UNIT = {"백만 원": (100, "억 원"), "천 달러": (1e5, "억 달러"), "달러": (1e8, "억 달러")}


def show(r):
    """{지표 표시, 옛·새 값 표시, 단위 표시} — 「상품군별 온라인쇼핑 거래액 · 문화 및 레저서비스 계 · 거래액」 → 「온라인쇼핑 거래액 · 문화 및 레저서비스」."""
    div, unit = SHOW_UNIT.get(r["단위"], (1, r["단위"]))
    v = lambda x: f"{num(x) / div:,.1f}" if div != 1 else f"{num(x):,.0f}"
    parts = [x.strip() for x in r["지표"].split("·")]
    if len(parts) == 3 and parts[2] in parts[0]: parts = parts[:2]  # 끝 칸이 표 이름의 되풀이(「거래액」)
    ind = " · ".join(re.sub(r"\s*계$", "", re.sub(r"^(상품군별|시도별)\s*", "", x)) for x in parts)
    return {"지표 표시": ind, "옛 값 표시": v(r["옛 값"]), "새 값 표시": v(r["새 값"]), "단위 표시": unit}


def write_summary(today, since=None):
    """지면 「방법·출처」의 정정 이력 한 줄이 읽는 요약 — 건수 · 마지막 감지일 · 감시 시작일(처음 돈 날 · 그 뒤 그대로)."""
    p = os.path.join(ROOT, SUMMARY_JSON)
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    led = list(csv.DictReader(open(os.path.join(ROOT, LEDGER), encoding="utf-8-sig")))
    by = {}
    for r in led: by[r["원천"]] = by.get(r["원천"], 0) + 1
    out = {"_설명": f"원천 정정 이력 요약 — tools-build/revisions.py 가 {LEDGER} 에서 만든다. since = 견준 기간의 시작(자동 갱신 첫 회차 · KST) · backfilled = 그중 견주기 단계를 넣기 전 회차를 git 이력에서 되짚은 소급 줄 수.",
           "since": since or old.get("since") or today, "n": len(led), "last": max((r["감지일"] for r in led), default=None), "by_source": by,
           "backfilled": sum(1 for r in led if (r.get("비고") or "").startswith("소급")),  # 자동 견주기를 넣기 전 회차를 git 이력에서 되짚은 줄
           # 지면 예시 한 줄 — 가장 최근 감지일 중 고친 폭(비율)이 가장 큰 줄(「최근: 지표 기준월 옛 값 → 새 값 단위」)
           "latest": max(({k: r[k] for k in ("원천", "지표", "기준기", "옛 값", "새 값", "단위")} for r in led if r["감지일"] == max(x["감지일"] for x in led)),
                         key=lambda r: abs(num(r["새 값"]) - num(r["옛 값"])) / (abs(num(r["옛 값"])) or 1), default=None)}
    if out["latest"]: out["latest"].update(show(out["latest"]))
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return out


def git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def backfill(start):
    """소급 — start 커밋 뒤 main 첫 부모 줄을 따라 원천 파일이 바뀐 커밋마다 바로 앞 커밋과 견준다(자동 갱신이 날마다 한 일을 그대로 되짚기).
    감지일 = 그 커밋 날(KST) · 비고 = 소급 기록 · since = start 뒤 첫 커밋 날(이때부터 견준 셈이 된다)."""
    paths = sorted({s[2] for s in SERIES})
    revs = [start] + git("rev-list", "--first-parent", "--reverse", f"{start}..HEAD", "--", *paths).split()
    kst = lambda r: datetime.datetime.fromtimestamp(int(git("show", "-s", "--format=%ct", r)), datetime.timezone(datetime.timedelta(hours=9))).date().isoformat()
    since, total = None, 0
    for a, b in zip(revs, revs[1:]):
        day = kst(b); since = since or day
        found = detect(a, b, set(git("diff", "--name-only", a, b, "--", *paths).split()))
        n = append_ledger(found, day, f"소급 기록(git {b[:7]})"); total += n
        say(f"- {day} {b[:7]}: " + (" · ".join(f"{s['label']} {len(s['revised'])}칸(증감 뒤집힘 {len(s['flips'])})" for s in found) or "정정 0") + f" → 이력 +{n}")
    write_summary(kst_today(), since)
    say(f"- 소급 끝: 커밋 {len(revs) - 1}개 · 이력 +{total}줄 · since {since}")
    return 0


# ── 지면 숫자(facts.json) — 같은 기준기에서 값이 바뀌었는가 ── 이름 앞머리 → 그 숫자의 기준기(같으면 새 달이 아니라 정정이다)
def _fact(name): return lambda F, rd: F.get(name, {}).get("v")
def _file(rel, f):
    def g(F, rd):
        t = rd(rel)
        try: return json.dumps(f(json.loads(t)), ensure_ascii=False) if t else None
        except (KeyError, IndexError, TypeError, ValueError): return None
    return g
PERIOD = [  # 위에서부터 먼저 맞는 것 — 기준기를 못 정하는 숫자(도달 시간·도구 수)는 원천 정정과 무관해 보지 않는다
    ("retail.online_", _fact("retail.online_ym")), ("retail.", _fact("retail.ym")),
    ("gate.", _fact("gate.ym")), ("vessel.", _fact("vessel.ym")), ("race.", _fact("race.year")), ("air.", _fact("air.window")),
    ("sudo.", _file("data/derived/home_axes.json", lambda d: d["trade"]["ym"])),
    ("cost.", _file("data/derived/import_cost.json", lambda d: [d["example"]["now"]["week"], d["example"]["ago"]["week"]])),
    ("choke.", _file("data/derived/chokepoints.json", lambda d: d["months"][-1])),
]
PERIOD_FACTS = {"gate.ym", "retail.ym", "retail.online_ym", "vessel.ym", "race.year", "air.window"}
SIGNED = re.compile(r"^[+−±-]")


def page_check(base="HEAD"):
    """(뒤집힘, 바뀜) — 지면 숫자 중 같은 기준기에서 부호가 뒤집힌 것 · 값만 바뀐 것."""
    t_old, t_new = read("data/derived/facts.json", base), read("data/derived/facts.json", None)
    if not t_old or not t_new: return [], []
    O, N = json.loads(t_old)["facts"], json.loads(t_new)["facts"]
    ro, rn = (lambda rel: read(rel, base)), (lambda rel: read(rel, None))
    flipped, moved = [], []
    for k in O.keys() & N.keys():
        if k in PERIOD_FACTS or O[k]["v"] == N[k]["v"]: continue
        per = next((g for p, g in PERIOD if k.startswith(p)), None)
        if not per: continue
        po, pn = per(O, ro), per(N, rn)
        if po is None or po != pn: continue  # 기준기가 바뀌었다 = 새 달 — 정정이 아니다
        rec = {"fact": k, "옛": O[k]["v"], "새": N[k]["v"], "기준기": pn, "pages": N[k].get("pages"), "src": N[k].get("src")}
        so, sn = SIGNED.match(O[k]["v"]), SIGNED.match(N[k]["v"])
        (flipped if so and sn and O[k]["v"][0] != N[k]["v"][0] else moved).append(rec)
    return sorted(flipped, key=lambda r: r["fact"]), sorted(moved, key=lambda r: r["fact"])


def report(found, flipped, moved):
    """요약·PR 본문에 그대로 싣는 마크다운 줄."""
    L = []
    for r in flipped:
        L.append(f"- **지면 숫자 방향 뒤집힘** `{r['fact']}` {r['옛']} → {r['새']}(기준기 {r['기준기']} 그대로 = 원천 정정 · 지면 {', '.join(r['pages'] or [])}) — 옆 문구(「늘었다」·「줄었다」 등)를 사람이 본다")
    for r in moved:
        L.append(f"- 지면 숫자 정정 `{r['fact']}` {r['옛']} → {r['새']}(기준기 {r['기준기']} 그대로 · 부호 그대로 — 방향 문구는 맞다)")
    for s in found:
        L.append(f"- 원천 정정 — {s['label']}: {len(s['revised'])}칸" + "".join(
            f"\n  - {ind} {per}: {fmt(o)} → {fmt(n)} {s['unit']}" for ind, per, o, n in s["revised"][:8]) + (f"\n  - … 외 {len(s['revised']) - 8}칸(전부 `{LEDGER}`)" if len(s["revised"]) > 8 else ""))
        for f in s["flips"][:8]:
            L.append(f"  - ⚠ 증감 방향 뒤집힘 — {f['지표']} {f['비교']}({f['앞']}→{f['뒤']}): {f['옛']} → {f['새']}")
        if len(s["flips"]) > 8: L.append(f"  - ⚠ … 외 {len(s['flips']) - 8}건")
    return L


def main():
    if "--selftest" in sys.argv: return selftest()
    if "--backfill" in sys.argv: return backfill(sys.argv[sys.argv.index("--backfill") + 1])
    base = sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "HEAD"
    found = detect(base)
    if "--check" in sys.argv:
        flipped, moved = page_check(base)
        for line in report(found, flipped, moved): print(line)
        return 3 if flipped else 0
    today = kst_today()
    added = append_ledger(found, today)
    write_summary(today)
    n = sum(len(s["revised"]) for s in found)
    nf = sum(len(s["flips"]) for s in found)
    say(f"- 원천 정정 {n}칸(원천 {len(found)}) · 정정 이력 +{added}줄 · 정정으로 뒤집힌 증감 {nf}" + "".join(
        f"\n  - {s['label']} {len(s['revised'])}칸" + (f" · 증감 뒤집힘 {len(s['flips'])}" if s["flips"] else "") for s in found))
    return 0


def selftest():
    """가짜 데이터 — 옛 값을 새 값으로 바꿔치기해 ① 감지 ② 이력 한 줄 ③ 방향 뒤집힘을 낸다."""
    import shutil, tempfile
    global ROOT
    keep = ROOT
    tmp = tempfile.mkdtemp(prefix="rev-")
    try:
        ROOT = tmp
        git = lambda *a: subprocess.run(["git", *a], cwd=tmp, capture_output=True, check=True)
        git("init", "-q"); git("config", "user.email", "t@t"); git("config", "user.name", "t")
        os.makedirs(os.path.join(tmp, "data/collected")); os.makedirs(os.path.join(tmp, "data/derived"))
        hdr = "ym,port,kind,etr_cnt,etr_grt,sat_cnt,sat_grt\n"
        old = hdr + "202508,인천,외국선,596,0,0,0\n202608,인천,외국선,560,0,0,0\n202609,인천,외국선,502,0,0,0\n"
        facts = lambda yoy: json.dumps({"facts": {"vessel.ym": {"v": "2026-09"}, "vessel.incheon": {"v": "502"}, "vessel.yoy": {"v": yoy, "pages": ["/map/vessels.html"]}}}, ensure_ascii=False)
        W = lambda rel, t: open(os.path.join(tmp, rel), "w", encoding="utf-8").write(t)
        W("data/collected/vessel-monthly.csv", old); W("data/derived/facts.json", facts("−6.0"))
        git("add", "-A"); git("commit", "-qm", "옛판")
        # 원천이 2025-08 을 596 → 520 으로 정정(지난해 같은 달) · 새 달 2026-10 도 들어온다(정정이 아니다)
        W("data/collected/vessel-monthly.csv", old.replace("202508,인천,외국선,596", "202508,인천,외국선,520") + "202610,인천,외국선,510,0,0,0\n")
        W("data/derived/facts.json", facts("+7.7"))
        found = detect()
        assert len(found) == 1 and found[0]["revised"] == [("인천 외국선 입항", "202508", 596.0, 520.0)], found
        assert {(f["비교"], f["앞"], f["뒤"], f["옛"], f["새"]) for f in found[0]["flips"]} == {("전년 같은 달 대비", "202508", "202608", "−", "+")}, found[0]["flips"]
        assert append_ledger(found, "2026-11-03") == 1 and append_ledger(found, "2026-11-04") == 0, "같은 정정은 한 줄만"
        led = list(csv.DictReader(open(os.path.join(tmp, LEDGER), encoding="utf-8-sig")))
        assert led == [{"감지일": "2026-11-03", "원천": "해양수산부 항만별 선박입출항실적", "지표": "인천 외국선 입항", "기준기": "202508", "옛 값": "596", "새 값": "520", "단위": "척", "비고": ""}], led
        sm = write_summary("2026-11-04")
        assert (sm["since"], sm["n"], sm["last"]) == ("2026-11-04", 1, "2026-11-03") and write_summary("2026-11-09")["since"] == "2026-11-04", sm
        fl, mv = page_check()
        assert [(r["fact"], r["옛"], r["새"]) for r in fl] == [("vessel.yoy", "−6.0", "+7.7")] and mv == [], (fl, mv)
        assert any("방향 뒤집힘" in x for x in report(found, fl, mv))
        # 새 달이 들어와 기준기가 바뀐 부호 변화는 정정이 아니다
        W("data/derived/facts.json", facts("+7.7").replace('"2026-09"', '"2026-10"'))
        assert page_check() == ([], [])
        # 정정 없이 다시 받은 날 — 감지 0
        git("add", "-A"); git("commit", "-qm", "새판")
        assert detect() == []
        # 소급 — 이력을 지우고 git 이력(옛판 → 새판)만으로 다시 만들면 같은 정정 한 줄 · 비고 = 소급 기록 · since = 새판 커밋 날
        os.remove(os.path.join(tmp, LEDGER)); os.remove(os.path.join(tmp, SUMMARY_JSON))
        backfill(git("rev-list", "--max-parents=0", "HEAD").stdout.decode().strip())
        led = list(csv.DictReader(open(os.path.join(tmp, LEDGER), encoding="utf-8-sig")))
        assert len(led) == 1 and led[0]["새 값"] == "520" and led[0]["비고"].startswith("소급 기록"), led
        assert json.load(open(os.path.join(tmp, SUMMARY_JSON), encoding="utf-8"))["since"] == led[0]["감지일"]
    finally:
        ROOT = keep
        shutil.rmtree(tmp, ignore_errors=True)
    assert shift("202601", -12) == "202501" and shift("2026-01", -1) == "2025-12" and shift("20261026", 1) is None
    assert sgn(-0.1) == "−" and fmt(596.0) == "596" and fmt(0.25) == "0.25"
    assert show({"지표": "상품군별 온라인쇼핑 거래액 · 문화 및 레저서비스 계 · 거래액", "옛 값": "398428", "새 값": "447358", "단위": "백만 원"}) == {"지표 표시": "온라인쇼핑 거래액 · 문화 및 레저서비스", "옛 값 표시": "3,984.3", "새 값 표시": "4,473.6", "단위 표시": "억 원"}
    print("revisions selftest OK (12)"); return 0


if __name__ == "__main__":
    sys.exit(main())

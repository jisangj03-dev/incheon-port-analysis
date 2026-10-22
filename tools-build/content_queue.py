"""콘텐츠 큐(B10 · 전권 위임 ④) — 도구 데이터가 갱신되면 LinkedIn · 블로그 · Threads 초안을 content-queue/<날짜>/<도구>.md 로 만든다.
선커밋 docs/측심_전권위임_단계기준_선커밋_20261015.md ④-상세:
  · 숫자는 파생 데이터 파일(data/derived/*.json)에서만 가져온다. 다 쓴 초안의 숫자가 데이터 파일 밖에 하나라도 있으면 **그 초안은 쓰지 않는다**.
  · 게시 0 — 초안 머리에 「게시 = 선장님」. 이 스크립트는 어디에도 올리지 않는다(네트워크 0).
  · 「갱신 시」 = 도구의 기준일(asof)이 content-queue/state.json 에 적힌 것과 다를 때만 새로 쓴다(--all 이면 전부).
  python tools-build/content_queue.py [--all] [--date YYYY-MM-DD] [--selftest]
"""
import datetime, glob, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Q = os.path.join(ROOT, "content-queue")
SITE = "https://jisangj03-dev.github.io/incheon-port-analysis"
J = lambda f: json.load(open(os.path.join(ROOT, "data/derived", f), encoding="utf-8"))
sign = lambda v: f"+{v}" if v > 0 else f"{v}"
won = lambda v: f"{v:,}"
ymd = lambda s: f"{s[:4]}-{s[4:6]}-{s[6:8]}" if re.fullmatch(r"\d{8}", str(s)) else str(s)


# ── 도구마다 사실 한 묶음(숫자는 전부 데이터에서) ─────────────────────────────
def pulse():
    P = J("port_pulse.json"); j = P["ports"]["Incheon"]["judge"]; r = P["rule"]
    return {"id": "port-pulse", "asof": P["asof"], "q": "지금 인천항에 배가 평소보다 많이 들어오나?",
            "hook": f"인천항 최근 {r['recent']}일 입항이 하루 {j['recent_avg']}척 — 평소({j['base_avg']}척)보다 {sign(j['pct'])}%, 「{j['word']}」입니다.",
            "body": [f"「평소」는 그 앞 {r['base']}일 하루 평균으로 정했습니다. ±{r['threshold_pct']}%를 넘어야 「많다·적다」로 씁니다.",
                     "부산·평택과 나란히 놓고 보면 인천만의 움직임인지 바로 갈립니다."],
            "how": "IMF PortWatch 일별 입항(AIS 기반 추정)을 해양수산부 월 통계와 대조해 씁니다.",
            "limit": "AIS 기반 추정이라 실제 입항 신고와 다를 수 있습니다.", "src": "IMF PortWatch · 해양수산부"}


def reach():
    # [2026-10-20 #67] 첫 숫자 = 지면 기본 시간대(「낮」 · 카카오 내비 대조 보정) — 자유 흐름 값은 실제보다 짧게 읽혔다(reach_slots.json table)
    I = J("isochrones.json"); o = I["origins"][0]
    try: S = J("reach_slots.json")
    except FileNotFoundError: S = None
    t = next((x for x in (S or {}).get("slots", []) if x["id"] == (S or {}).get("default")), None)
    tb = S["table"][0][t["id"]] if t and t["k"] != 1 else None
    c, w = (tb["car"], tb["within"]) if tb else (o["cities"], o["cities_within"])
    s, tag = c.get("서울시청"), (f"({t['id']} 시간 보정, 카카오 내비 {t.get('n', 30)}구간 대조)" if tb else "(자유 흐름 · 혼잡 미반영)")
    return {"id": "delivery-reach", "asof": I["made"], "q": "인천 창고에서 수도권 어디까지 몇 시간에 닿나?",
            "hook": f"{o['name']}에서 서울시청까지 승용차로 {s}분{tag}. 표에 든 수도권 도시 {o['n_cities']}곳 중 {w['1h']}곳이 1시간 안입니다.",
            "body": [f"2시간이면 {w['2h']}곳, 3시간이면 {w['3h']}곳. 출발지를 바꾸면 도달권이 지도 위에서 다시 번집니다.",
                     "출근·낮·자유 흐름 시간대와 화물차 판(고속도로 80km/h · 화물차 통행 금지 길 제외), 상하차 분을 직접 골라 볼 수 있습니다."],
            "how": "OpenStreetMap 도로를 도로 등급별 자유 흐름 속도로 엮어 미리 계산하고, 시간대는 카카오 내비(미래 출발시각) 30구간 대조 오차 중앙값만큼 늘렸습니다.",
            "limit": "시간대 보정은 모든 길에 같은 비율이라 길마다 다른 막힘은 반영하지 않습니다. 실측 소통 속도가 아닙니다.", "src": "OpenStreetMap 기여자(ODbL) · 카카오모빌리티(대조 통계만)"}


def race():
    T = J("trade_race.json"); y = [x for x in T["years"] if not x.get("partial")][-1]
    e = max(y["items"], key=lambda i: i["exp"]); m = max(y["items"], key=lambda i: i["imp"])
    return {"id": "trade-race", "asof": str(y["through"]), "q": "인천은 무엇을 사고파나 — 해마다 어떻게 바뀌었나?",
            "hook": f"{y['y']}년 인천 소재 기업 수출 {won(y['exp_total'])}백만 달러, 1위는 {e['name']}({e['exp_pct']}%)입니다.",
            "body": [f"수입은 {won(y['imp_total'])}백만 달러, 1위는 {m['name']}({m['imp_pct']}%).",
                     "해마다 품목 칸 넓이가 다시 배치되는 트리맵으로 구성이 어떻게 바뀌었는지 봅니다."],
            "how": "관세청 시도별·품목별(HS 2단위) 수출입에서 사업장 소재지가 인천인 기업 실적만 씁니다.",
            "limit": "사업장 소재지 기준이라 인천항·인천공항을 거친 물량과는 다릅니다.", "src": "관세청"}


def cost():
    C = J("import_cost.json"); E = C["example"]; n, a = E["now"], E["ago"]
    return {"id": "import-cost", "asof": ymd(n["week"]), "q": "환율이 바뀌면 내 수입 원가가 얼마나 바뀌나?",
            "hook": f"같은 {won(E['goods'])}달러({E['incoterm']}) 물건을 이번 주 과세환율로 들이면 원가(부가세 제외) {won(n['cost'])}원 — {E['ago_weeks']}주 전보다 {('+' if E['diff'] > 0 else '−') + won(abs(E['diff']))}원({sign(E['pct'])}%).",
            "body": [f"과세환율이 {a['fx']:,}원에서 {n['fx']:,}원으로 움직인 몫입니다(관세 {E['duty_pct']}% · 부가세 {E['vat_pct']}% 예시).",
                     "운임 칸에는 KCCI 지수 변동률로 낸 제안값을 넣어 볼 수 있습니다 — 지수는 달러 운임이 아닙니다."],
            "how": "관세청 주간 과세환율로 과세가격·관세·부가세를 주마다 다시 계산합니다.",
            "limit": "참고용 어림이며 법률·세무·관세 자문이 아닙니다.", "src": "관세청 과세환율 · 한국해양진흥공사 KCCI"}


def choke():
    K = J("chokepoints.json"); p = min((x for x in K["points"] if x["vs_base_pct"] is not None), key=lambda x: x["vs_base_pct"])
    return {"id": "chokepoint", "asof": p["asof"], "q": "바다 길목이 막히면 한국 교역의 어느 몫이 흔들리나?",
            "hook": f"{p['ko']} 통항이 2023년 같은 달보다 {sign(p['vs_base_pct'])}%.",
            "body": [f"이 길목을 지나는 나라와의 교역은 한국 수입의 {p['imp_pct']}% · 수출의 {p['exp_pct']}%(전국 · 최근 12달).",
                     f"인천 관문은 전국 수입의 {K['incheon_imp_share_pct']}%를 받습니다({K['incheon_ym']})."],
            "how": "IMF PortWatch 길목별 일별 통항과 관세청 국가별 수출입을 경유 표(선커밋)로 잇습니다.",
            "limit": "경유는 보통 항로의 가정이고, 흔들리는 액수는 단순 비례 가정이지 실제 손실이 아닙니다.", "src": "IMF PortWatch · 관세청"}


def anchorage():
    S = J("s2_anchorage.json"); f = [x for x in S["frames"] if not x["low_confidence"]][-1]
    return {"id": "anchorage", "asof": f["date"], "q": "인천 앞바다 묘박지에 배가 얼마나 기다리나?",
            "hook": f"{f['date']} 위성 사진에서 인천 먼바다 상자 안에 배로 보이는 물체 {f['ships_seen']}개.",
            "body": ["달마다 가장 맑은 Sentinel-2 장면을 골라 넘겨 보며 기다리는 배가 늘었는지 줄었는지 봅니다.",
                     "구름 많은 날은 막대에서만 흐리게 보여 주고 큰 숫자에는 쓰지 않습니다."],
            "how": "Copernicus Sentinel-2 장면에서 바다 위 밝은 점을 세는 어림입니다.",
            "limit": "작은 배·구름 그림자·파도를 가르지 못할 수 있어 개수는 어림입니다.", "src": "Contains modified Copernicus Sentinel data"}


def radar():
    R = J("bid_radar.json"); g = max(R["groups"], key=lambda k: R["group_counts"][k])
    return {"id": "bid-radar", "asof": R["snapshot"][:10], "q": "공공기관은 요즘 어떤 물류·무역 용역을 사려 하나?",
            "hook": f"나라장터 용역 공고 {won(R['scanned'])}건(지난 {R['window_days']}일) 중 물류·무역 공고로 마감 전이던 것 {R['n']}건.",
            "body": [f"가장 많은 묶음은 {g}({R['group_counts'][g]}건). {R['snapshot']} 스냅샷이라 그 뒤 마감·정정됐을 수 있습니다.",
                     "목록은 고르는 규칙(선커밋) 그대로 자동 수집했고 사람이 검수하지 않았습니다."],
            "how": "조달청 입찰공고정보서비스(용역)를 빌드 때 불러 공고명 낱말 규칙으로 고릅니다. 담당자 개인정보는 받지 않습니다.",
            "limit": "공고명 낱말로만 고릅니다. 응찰 자격·조건은 나라장터 원문이 정본입니다.", "src": "조달청 나라장터"}


TOOLS = [pulse, reach, race, cost, choke, anchorage, radar]


# ── 채널 셋 ─────────────────────────────────────────────────────────────
def render(f, made):
    url = f"{SITE}/tools/{f['id']}.html"
    li = "\n\n".join([f["hook"], *f["body"], f"어떻게 쟀나 — {f['how']}", f"한계 — {f['limit']}", f"직접 조작해 보기 → {url}", "#물류 #SCM #인천 #공공데이터"])
    blog = "\n\n".join([f"제목안 — {f['q']}", f["hook"], *f["body"], "### 어떻게 쟀나", f["how"], "### 한계", f["limit"],
                        f"### 원문 · CSV", f"출처: {f['src']}. 도구 지면의 신뢰 꼬리에서 원문 링크와 CSV 를 받을 수 있습니다 → {url}"])
    th = f"{f['hook']}\n\n{f['body'][0]}\n\n{url}"
    head = (f"---\nid: {f['id']}\nmade: {made}\nasof: {f['asof']}\nstate: 초안(게시 = 선장님 · 이 파일은 어디에도 게시되지 않았다)\n"
            f"note: AI 초안 · 검수 전 — 숫자는 data/derived 에서만(시험 tests/content-queue.spec.mjs)\n---\n")
    return head + f"\n# {f['q']}\n\n## LinkedIn\n\n{li}\n\n## 블로그\n\n{blog}\n\n## Threads\n\n{th}\n"


def numbers(t):
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", t)
    out = re.findall(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?(?!\d)|\d+(?:\.\d+)?", t)
    return [n for n in out if not re.fullmatch(r"(19|20)\d{2}", n)]


def norm(n):
    try: v = float(n.replace(",", "")); return str(int(v)) if v == int(v) else repr(v)
    except ValueError: return n


def allowed():
    texts = [open(p, encoding="utf-8").read() for p in sorted(glob.glob(os.path.join(ROOT, "data/derived/*.json")))]
    texts += [open(os.path.join(ROOT, f), encoding="utf-8").read() for f in ("data/rooms.json", "data/sources.json")]
    return {norm(n) for t in texts for n in numbers(t) + numbers(t.replace(",", " "))}


def outside(md, ok):
    body = md.split("\n---\n", 1)[-1]  # 머리(made·asof 날짜)는 빼고 본문만
    return sorted({norm(n) for n in numbers(body)} - ok)


def live():
    """[2026-10-22 갱신 무인화 ①] 도구 초안을 content-queue/live/ 에 늘 다시 쓴다(날짜 폴더·state 없이) — refresh 가 원천 갱신 때마다 부른다.
    made 줄은 날짜 대신 「자동」 — 날마다 글자가 바뀌어 커밋이 생기지 않게(숫자가 바뀔 때만 파일이 바뀐다)."""
    ok, d, n, bad = allowed(), os.path.join(Q, "live"), 0, []
    os.makedirs(d, exist_ok=True)
    rooms = json.load(open(os.path.join(ROOT, "data/rooms.json"), encoding="utf-8"))["rooms"]
    on = {os.path.basename(it["href"]).replace(".html", "") for r in rooms if r["id"] == "tools" for it in r.get("items") or []}  # 지금 공개 도구만(내린 지면 초안 0)
    for fn in TOOLS:
        try: f = fn()
        except (FileNotFoundError, KeyError, ValueError, IndexError) as e: print("건너뜀", fn.__name__, type(e).__name__, e); continue
        if f["id"] not in on: continue
        md = render(f, "자동(refresh · 숫자 = data/derived)"); b = outside(md, ok)
        if b: bad.append((f["id"], b)); print("버림(데이터 밖 숫자)", f["id"], b); continue
        open(os.path.join(d, f"{f['id']}.md"), "w", encoding="utf-8").write(md); n += 1
    print(f"live 초안 {n}편 · 버림 {len(bad)}")
    return 1 if bad else 0


def main():
    if "--live" in sys.argv: return live()
    made = sys.argv[sys.argv.index("--date") + 1] if "--date" in sys.argv else datetime.date.today().isoformat()
    st_p = os.path.join(Q, "state.json")
    st = json.load(open(st_p, encoding="utf-8")) if os.path.exists(st_p) else {}
    ok, wrote, dropped = allowed(), [], []
    for fn in TOOLS:
        try: f = fn()
        except (FileNotFoundError, KeyError, ValueError, IndexError) as e: print("건너뜀", fn.__name__, type(e).__name__, e); continue
        # 기준일만 보면 같은 날 바뀐 숫자(입찰 레이더 스냅샷 13:46 → 14:15)를 놓친다(2026-10-15 QA) → 사실 묶음의 지문으로 본다
        key = f"{f['asof']}|{hashlib.sha1(json.dumps(f, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:10]}"
        if "--all" not in sys.argv and st.get(f["id"]) == key: continue
        md = render(f, made); bad = outside(md, ok)
        if bad: dropped.append((f["id"], bad)); print("버림(데이터 밖 숫자)", f["id"], bad); continue
        d = os.path.join(Q, made); os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{f['id']}.md"), "w", encoding="utf-8").write(md)
        st[f["id"]] = key; wrote.append(f["id"])
    os.makedirs(Q, exist_ok=True)
    json.dump(dict(sorted(st.items())), open(st_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"초안 {len(wrote)}편 → content-queue/{made}/ {wrote} · 버림 {len(dropped)}")
    return 1 if dropped else 0


def selftest():
    ok = {norm(n) for n in numbers('{"a": 18.6, "b": "1,234", "c": 52}')}
    assert outside("---\nmade: 2026-10-15\n---\n하루 18.6척 · 1,234원 · 52주 · 2025년", ok) == []
    assert outside("---\n---\n하루 18.6척 · 77일", ok) == ["77"]
    f = {"id": "x", "asof": "2026-10-09", "q": "질문?", "hook": "훅 18.6", "body": ["하나", "둘"], "how": "방법", "limit": "한계", "src": "출처"}
    md = render(f, "2026-10-15")
    assert "게시 = 선장님" in md and md.count("## ") >= 3 and "/tools/x.html" in md, md
    print("selftest 3/3 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

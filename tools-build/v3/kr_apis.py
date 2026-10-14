"""공공데이터포털 v3 — ① 관세청 시도별 품목별(인천) 연도별 역사(품목 트리맵 레이스) ② 승인된 새 API 의 주소·요청 변수 찾기와 시험 호출.
키 = DATA_GO_KR_KEY(Decoding 판) — 로그·산출물에 찍지 않는다(common.scrub). 명세는 공개 화면(openapi.do)에서 읽는다.
결과: data/collected/v3/sido_item_years.json · data/collected/v3/api_probe.json
  python tools-build/v3/kr_apis.py [--probe | --probe-only]
"""
import datetime, html, json, re, sys, time, urllib.parse
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__))))
from common import KEY, get, write, say, scrub
from collect import parse  # 태그 이름 기준 해석(사고 1)

FIND = {
    "iiac-air-country": "인천국제공항공사 국가별 항공 통계",
    "iiac-freighter": "인천국제공항공사 화물기 정기운항편",
    "kcs-exchange": "관세청 관세환율",
    "kcs-customs-office": "관세청 세관별 수출입실적",
    "mof-cargo-item": "해양수산부 품목별 화물처리",
}


def portal_find(q):
    st, h = get("https://www.data.go.kr/tcs/dss/selectDataSetList.do", {"keyword": q})
    c = []
    for m in re.finditer(r'href="/data/(\d{8})/openapi\.do[^"]*"[^>]*>([\s\S]{0,300}?)</a>', h or ""):
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        if (m.group(1), t) not in c: c.append((m.group(1), t))
    return st, c[:8]


def spec(did):
    st, h = get(f"https://www.data.go.kr/data/{did}/openapi.do")
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", h or ""))))
    eps = sorted(set(re.findall(r"https?://apis\.data\.go\.kr/[A-Za-z0-9_/.-]+", h or "")))
    ops = sorted(set(re.findall(r"\b(get[A-Z][A-Za-z0-9_]+)\b", h or "")))
    i = t.find("요청변수")
    lic = re.search(r"이용허락범위\s*[:：]?\s*(.{0,40})", t)
    return {"status": st, "endpoints": eps[:10], "ops": ops[:20], "request_vars": t[i:i + 1200] if i >= 0 else None, "license_text": lic.group(1).strip() if lic else None, "title": (re.search(r"<title>([^<]*)", h or "") or [None, None])[1]}


def call(url, extra=None):
    p = {"serviceKey": KEY, "numOfRows": "10", "pageNo": "1", "type": "json", "_type": "json", **(extra or {})}
    st, b = get(url, p, timeout=30, tries=2)
    b = scrub(b)
    rc, msg, rows = parse(b)
    return {"url": url, "params": {k: v for k, v in p.items() if k != "serviceKey"}, "status": st, "resultCode": rc, "resultMsg": msg[:120], "rows": len(rows), "sample": rows[:3], "body_head": b[:600]}


def probe():
    out = {"checked": datetime.date.today().isoformat(), "key_present": bool(KEY), "apis": {}}
    ym = (datetime.date.today().replace(day=1) - datetime.timedelta(days=40)).strftime("%Y%m")
    for sid, q in FIND.items():
        st, cands = portal_find(q)
        rec = {"search": q, "search_status": st, "candidates": cands}
        if cands:
            did = cands[0][0]
            rec["data_id"] = did
            rec["spec"] = sp = spec(did)
            calls = []
            for ep in sp["endpoints"][:3]:
                targets = [ep] if re.search(r"/get[A-Z]", ep) else [ep.rstrip("/") + "/" + op for op in sp["ops"][:3]] or [ep]
                for u in targets[:3]:
                    calls.append(call(u))
                    calls.append(call(u, {"searchday": ym + "01", "qryYymmDd": ym + "01", "strtYymm": ym, "endYymm": ym, "searchMonth": ym, "imexTp": "2"}))
            rec["calls"] = calls
        out["apis"][sid] = rec
        say(sid, "후보", len(cands), "· 호출", len(rec.get("calls", [])), "· 결과", [c["resultCode"] for c in rec.get("calls", [])][:6])
    write("data/collected/v3/api_probe.json", out)


def sido_years():
    """관세청 시도별 품목별(인천 28) — 한 해(1~12월)를 한 번에 물으면 연간 합으로 답한다(priodTitle = 연도)."""
    url = "https://apis.data.go.kr/1220000/sidoitemtrade/getSidoitemtradeList"
    today = datetime.date.today()
    last = (today.replace(day=1) - datetime.timedelta(days=45))  # 공표 지연
    years = {}
    for y in range(2016, last.year + 1):
        end = f"{y}12" if y < last.year else last.strftime("%Y%m")
        for k in range(4):  # 포털이 연결을 끊는 일이 잦다(2026-10-14 실측: 11해 중 2해) — 빈 해는 쉬었다 다시
            st, b = get(url, {"serviceKey": KEY, "sidoCd": "28", "strtYymm": f"{y}01", "endYymm": end}, timeout=120)
            rc, msg, rows = parse(scrub(b))
            if rows: break
            time.sleep(5 * (k + 1))
        years[str(y)] = {"through": end, "status": st, "resultCode": rc, "rows": rows}
        say(y, end, st, rc, len(rows))
    miss = [y for y, r in years.items() if not r["rows"]]
    if miss:  # 빈 해가 하나라도 있으면 덮어쓰지 않는다(지난 온전한 파일을 지킨다)
        say("빈 해", miss, "— sido_item_years.json 을 덮어쓰지 않는다"); return
    write("data/collected/v3/sido_item_years.json", {"source": "관세청 시도별 품목별 수출입실적(공공데이터포털 15101641) · 시도 = 인천(28) · 금액 = 천 달러", "fetched": today.isoformat(), "years": years})


def fx_weeks(since="2024-01-07"):
    """관세청 관세환율(수입 · 주간) — 일요일마다 한 번. 아무 날짜를 주면 그 날이 든 주의 환율이 온다(2026-10-14 실측). USD·CNY·JPY(1엔)·EUR."""
    url = "https://apis.data.go.kr/1220000/retrieveTrifFxrtInfo/getRetrieveTrifFxrtInfo"
    d, today, weeks = datetime.date.fromisoformat(since), datetime.date.today(), []
    while d <= today:
        for k in range(4):
            st, b = get(url, {"serviceKey": KEY, "aplyBgnDt": d.strftime("%Y%m%d"), "weekFxrtTpcd": "2"}, timeout=30, tries=2)
            rc, msg, rows = parse(scrub(b))
            if rows: break
            time.sleep(3 * (k + 1))
        r = {x["currSgn"]: float(x["fxrt"]) for x in rows if x.get("currSgn") in ("USD", "CNY", "JPY", "EUR")}
        if r: weeks.append({"from": rows[0]["aplyBgnDt"], **r})
        else: say("빈 주", d)
        d += datetime.timedelta(days=7)
    exp = (today - datetime.date.fromisoformat(since)).days // 7 + 1
    if len(weeks) < 0.9 * exp:  # 빈 주가 많으면 덮어쓰지 않는다
        say("관세환율", len(weeks), "/", exp, "주만 받음 — 덮어쓰지 않는다"); return
    seen, out = set(), []
    for w in weeks:
        if w["from"] not in seen: seen.add(w["from"]); out.append(w)
    write("data/collected/v3/kcs_fx_weeks.json", {"source": "관세청 관세환율정보(공공데이터포털 15101230) · 수입(weekFxrtTpcd=2) · 원/통화 1단위(JPY 는 1엔)", "fetched": today.isoformat(), "weeks": out})
    say("관세환율", len(out), "주", out[0]["from"] if out else "", "~", out[-1]["from"] if out else "")


if __name__ == "__main__":
    # 탐색(probe)은 새 API 를 붙일 때만 — 예약 실행에서는 포털 화면을 긁지 않는다(Actions 에서 느려 40분 한도에 걸렸다 · 2026-10-14)
    if "--probe" in sys.argv or "--probe-only" in sys.argv: probe()
    if "--probe-only" not in sys.argv: sido_years(); fx_weeks()

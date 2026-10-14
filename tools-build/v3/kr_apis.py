"""공공데이터포털 v3 — ① 관세청 시도별 품목별(인천) 연도별 역사(품목 트리맵 레이스) ② 승인된 새 API 의 주소·요청 변수 찾기와 시험 호출.
키 = DATA_GO_KR_KEY(Decoding 판) — 로그·산출물에 찍지 않는다(common.scrub). 명세는 공개 화면(openapi.do)에서 읽는다.
결과: data/collected/v3/sido_item_years.json · data/collected/v3/api_probe.json
  python tools-build/v3/kr_apis.py [--probe-only]
"""
import datetime, html, json, re, sys, urllib.parse
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
    st, b = get(url, p, timeout=90)
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
        st, b = get(url, {"serviceKey": KEY, "sidoCd": "28", "strtYymm": f"{y}01", "endYymm": end}, timeout=120)
        rc, msg, rows = parse(scrub(b))
        years[str(y)] = {"through": end, "status": st, "resultCode": rc, "rows": rows}
        say(y, end, st, rc, len(rows))
    write("data/collected/v3/sido_item_years.json", {"source": "관세청 시도별 품목별 수출입실적(공공데이터포털 15101641) · 시도 = 인천(28) · 금액 = 천 달러", "fetched": today.isoformat(), "years": years})


if __name__ == "__main__":
    probe()
    if "--probe-only" not in sys.argv: sido_years()

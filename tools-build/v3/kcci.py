"""KCCI(한국형 컨테이너선 운임지수 · 한국해양진흥공사) — 공공데이터포털 15131881 은 KOBC 누리집으로 잇는 연결형 데이터다(포털에 파일 없음 · 자동변환 API 404 · 2026-10-15 실측).
그래서 KOBC 누리집 시계열 화면(gridList.do?mId=0304000000)에서 2022-11-07(최초 발표)부터 오늘까지를 내려받는다. 이 세션은 kobc.or.kr 이 막혀 Actions 에서 돈다.
화면 구조를 모르는 채로 짰다 — 먼저 탐색(폼·스크립트 조각)을 data/collected/v3/kcci_probe.json 에 남기고, 찾은 내려받기 길로 받아 본다. 덜 오면 지난 파일을 지킨다.
결과: data/collected/v3/kcci_weeks.json(주 · 종합 · 항로 13)
  python tools-build/v3/kcci.py
"""
import datetime, html, http.cookiejar, io, json, os, re, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, UA, write, say

BASE = "https://www.kobc.or.kr"
PAGE = BASE + "/ebz/shippinginfo/timeseries/gridList.do?mId=0304000000"
OUT = os.path.join(ROOT, "data/collected/v3/kcci_weeks.json")
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def fetch(url, data=None, ref=PAGE):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data is not None else None,
                                 headers={"User-Agent": UA, "Referer": ref, "Accept-Language": "ko,en"})
    try:
        with op.open(req, timeout=90) as r: return r.status, r.headers.get("Content-Type", ""), r.read()
    except Exception as e: return getattr(e, "code", str(e)[:120]), "", b""


def cells(htm):
    rows = []
    for tr in re.findall(r"<tr[\s\S]*?</tr>", htm, re.I):
        c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<t[hd][^>]*>([\s\S]*?)</t[hd]>", tr, re.I)]
        if c: rows.append(c)
    return rows


def parse_table(rows):
    """머리줄(DATE · KCCI · 항로 코드)이 있는 표 → 주 목록. 날짜 칸은 머리 이름(DATE·날짜·기준일)으로 찾는다
    (2026-10-15: 엑셀은 첫 칸이 「번호」라 첫 칸에서 날짜를 찾던 규칙이 엑셀 196주를 놓치고 화면 표 4묶음만 남겼다)."""
    head = next((r for r in rows if any("KCCI" in x or "종합" in x for x in r) and len(r) >= 5), None)
    if not head: return None
    di = next((i for i, x in enumerate(head) if re.search(r"^(DATE|날짜|기준일|발표일|일자)$", x.strip(), re.I)), 0)
    out = []
    for r in rows[rows.index(head) + 1:]:
        if len(r) <= di: continue
        d = re.search(r"(20\d{2})[-./]?(\d{1,2})[-./]?(\d{1,2})", r[di].split(".")[0] if re.fullmatch(r"\d{8}(\.0)?", r[di]) else r[di])
        if not d: continue
        vals = {}
        for j, (k, v) in enumerate(zip(head, r)):
            if j == di or not k.strip() or re.search(r"번호|No", k): continue
            try: vals[k.strip()] = float(str(v).replace(",", ""))
            except ValueError: pass
        if vals: out.append({"date": f"{d.group(1)}-{int(d.group(2)):02d}-{int(d.group(3)):02d}", **vals})
    return sorted(out, key=lambda x: x["date"]) or None


def main():
    probe = {"checked": datetime.date.today().isoformat(), "page": PAGE}
    st, ct, b = fetch(PAGE); h = b.decode("utf-8", "replace")
    probe.update(status=st, size=len(b))
    probe["forms"] = [f[:1500] for f in re.findall(r"<form[\s\S]*?</form>", h, re.I)][:4]
    probe["inputs"] = sorted(set(re.findall(r'<input[^>]*name="([^"]+)"', h)))[:60]
    probe["script_bits"] = sorted(set(m.strip()[:300] for m in re.findall(r"[^\n;]*(?:[Ee]xcel|[Dd]own|xls)[^\n;]*", h)))[:30]
    rows = parse_table(cells(h))
    probe["table_rows_on_page"] = len(rows or [])
    # 내려받기 길 후보 — 화면의 액션·스크립트에서 엑셀/내려받기 주소를 모으고, 날짜 칸 이름을 찾아 넣는다
    # 2026-10-15 탐색: 날짜 칸 = sDay · eDay(시작 칸 이름을 처음 규칙이 놓쳤다)
    dates = [n for n in probe["inputs"] if re.search(r"(^sDay$|start|from|bgn|sDate|srch.*Date)", n, re.I)] or ["sDay"]
    ends = [n for n in probe["inputs"] if re.search(r"(^eDay$|end|eDate)", n, re.I)] or ["eDay"]
    cands = [c for c in sorted(set(re.findall(r"['\"](/[^'\"]*(?:[Ee]xcel|[Dd]own)[^'\"]*\.do[^'\"]*)['\"]", h))) if "excel" in c.lower()][:3]
    probe["candidates"], probe["date_fields"] = cands, [dates, ends]
    today = datetime.date.today()
    tries = []
    for path in cands + [PAGE.replace(BASE, "")]:
        for sd, ed in [("2022-11-07", today.isoformat()), ("20221107", today.strftime("%Y%m%d"))]:
            data = {k: v for k, v in [("mId", "0304000000")]}
            for n in dates[:3]: data[n] = sd
            for n in ends[:3]: data[n] = ed
            s2, ct2, b2 = fetch(BASE + path, data)
            tries.append({"path": path, "fields": list(data), "status": s2, "type": ct2, "size": len(b2), "head": b2[:80].hex() if b2[:2] in (b"\xd0\xcf", b"PK") else b2[:120].decode("utf-8", "replace")})
            if not b2: continue
            rr = None
            if b2[:2] == b"\xd0\xcf":
                try:
                    import xlrd
                    wb = xlrd.open_workbook(file_contents=b2); sh = wb.sheet_by_index(0)
                    grid = [[str(sh.cell_value(i, j)) for j in range(sh.ncols)] for i in range(sh.nrows)]
                    tries[-1]["xls_rows"], tries[-1]["xls_head"] = sh.nrows, grid[:5]
                    rr = parse_table(grid)
                except Exception as e: tries[-1]["xls_error"] = str(e)[:120]
            else:
                rr = parse_table(cells(b2.decode("utf-8", "replace")))
            if rr and (len(rr) > len(rows or []) or len(rr[-1]) > len((rows or [{}])[-1])): rows = rr; probe["used"] = {k: tries[-1][k] for k in ("path", "fields", "size")}
            if rows and len(rows) > 100: break
        if rows and len(rows) > 100: break
    probe["tries"] = tries
    write("data/collected/v3/kcci_probe.json", probe)
    if not rows or len(rows) < 4:
        say("KCCI 표를 못 읽었다 — 탐색만 남김", st, len(b)); return 1
    if os.path.exists(OUT):
        old = json.load(open(OUT, encoding="utf-8"))
        if old.get("weeks") and old["weeks"][-1]["date"] > rows[-1]["date"]: say("지난 파일이 더 최신 — 지킨다"); return 1
    write("data/collected/v3/kcci_weeks.json", {"source": "한국해양진흥공사 KCCI(공공데이터포털 15131881 → KOBC 누리집)", "fetched": today.isoformat(), "weeks": rows})
    say("KCCI", len(rows), "주", rows[0]["date"], "~", rows[-1]["date"]); return 0





def selftest():
    g = [["KOBC CONTAINER COMPOSITE INDEX TIMESERIES", ""], ["번호", "DATE", "KCCI", "KUWI", "KCI"], ["2", "20261012", "4654.0", "8258.0", "55.0"], ["1", "20261006", "4629.0", "8194.0", "54.0"]]
    r = parse_table(g)
    assert r == [{"date": "2026-10-06", "KCCI": 4629.0, "KUWI": 8194.0, "KCI": 54.0}, {"date": "2026-10-12", "KCCI": 4654.0, "KUWI": 8258.0, "KCI": 55.0}], r
    print("selftest 1/1 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

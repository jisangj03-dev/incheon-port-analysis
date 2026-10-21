"""유통 축 KOSIS 원천(2026-10-21 과제 1) — 통계청 KOSIS OpenAPI 에서 유통·소비 월 통계를 받는다. 키 = 저장소 시크릿 KOSIS_KEY.
키가 없으면 아무것도 쓰지 않고 0 으로 끝난다(지난 파일을 지킨다) — 키 발급(회원가입·활용신청)은 선장님 손이다.
표는 이름으로 찾는다(KOSIS 통합검색 API) — 표 번호를 손으로 박지 않는다. 찾은 표 번호·이름은 산출물에 남는다(다음 실행부터 그 표를 쓴다).
  WANT[i] = (id, 찾을 표 이름, 기관, 주기, 고를 분류 항목 키워드)
결과: data/collected/v3/kosis_retail.json
  python tools-build/kosis.py
  python tools-build/kosis.py --selftest
[미확인] 이 세션은 키가 없어 응답 모양을 실측하지 못했다 — 첫 실행(Actions)의 요약이 실측이다.
"""
import datetime, json, os, sys, time, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "v3"))

OUT = "data/collected/v3/kosis_retail.json"
BASE = "https://kosis.kr/openapi"
KEY = os.environ.get("KOSIS_KEY", "")
WANT = [
    ("online", "상품군별 온라인쇼핑 거래액", "101", "M", ["합계", "계"]),
    ("retail-sido", "시도별 대형소매점 판매액", "101", "M", ["서울", "인천", "경기", "전국"]),
]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def hide(s):
    s = str(s)
    for k in {KEY, urllib.parse.quote(KEY, safe=""), urllib.parse.quote_plus(KEY)} - {""}:
        s = s.replace(k, "***")
    return s


def jcall(path, params):
    from common import get
    st, b = get(f"{BASE}/{path}", {"apiKey": KEY, "format": "json", "jsonVD": "Y", **params}, timeout=60, tries=2)
    try: return st, json.loads(b)
    except Exception: return st, {"_raw": hide(b)[:300]}


def find_table(name, org):
    st, j = jcall("statisticsSearch.do", {"method": "getList", "searchNm": name, "orgId": org, "resultCount": "20"})
    rows = j if isinstance(j, list) else []
    exact = [r for r in rows if r.get("TBL_NM", "").replace(" ", "") == name.replace(" ", "")]
    pick = (exact or [r for r in rows if name.split()[0] in r.get("TBL_NM", "")] or [None])[0]
    return st, pick, [{"tbl": r.get("TBL_ID"), "name": r.get("TBL_NM")} for r in rows[:10]]


def series(org, tbl, prd, n=25):
    st, j = jcall("Param/statisticsParameterData.do", {"method": "getList", "orgId": org, "tblId": tbl, "itmId": "ALL", "objL1": "ALL", "objL2": "ALL", "prdSe": prd, "newEstPrdCnt": str(n)})
    return st, (j if isinstance(j, list) else []), (None if isinstance(j, list) else hide(json.dumps(j, ensure_ascii=False))[:300])


def slim(rows, keys):
    """KOSIS 행(C1_NM·ITM_NM·PRD_DE·DT·UNIT_NM) → 고른 분류만 남긴 작은 표."""
    out = []
    for r in rows:
        lab = " ".join(str(r.get(k, "")) for k in ("C1_NM", "C2_NM") if r.get(k))
        if keys and not any(k in lab for k in keys): continue
        try: v = float(str(r.get("DT", "")).replace(",", ""))
        except ValueError: continue
        out.append({"ym": str(r.get("PRD_DE", "")), "c": lab, "item": r.get("ITM_NM", ""), "v": v, "unit": r.get("UNIT_NM", "")})
    return out


def run():
    from common import write, say
    if not KEY:
        say("KOSIS_KEY 없음 — 유통 축 KOSIS 원천은 건너뛴다(지난 파일 유지 · 키 발급 = 선장님)"); return 0
    p = os.path.join(ROOT, OUT)
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"tables": {}}
    res = {}
    for sid, name, org, prd, keys in WANT:
        prev = old.get("tables", {}).get(sid, {})
        tbl = prev.get("tbl")
        cands = None
        if not tbl:
            st, pick, cands = find_table(name, org)
            tbl = pick and pick.get("TBL_ID")
            say(sid, "표 찾기", st, tbl or "없음", "· 후보", [c["name"] for c in cands][:5])
        if not tbl: res[sid] = {"want": name, "found": None, "candidates": cands}; continue
        for k in range(3):
            st, rows, err = series(org, tbl, prd)
            if rows: break
            time.sleep(3 * (k + 1))
        s = slim(rows, keys)
        say(sid, tbl, "행", len(rows), "→", len(s), err or "")
        if s: res[sid] = {"want": name, "tbl": tbl, "org": org, "rows": s, "candidates": cands}
        elif prev: res[sid] = prev
    if not any(r.get("rows") for r in res.values()):
        say("받은 행 0 — 덮어쓰지 않는다"); return 1
    write(OUT, {"source": "통계청 KOSIS OpenAPI(이용지침: 출처 표시 · 수치 변경 배포 금지)", "fetched": datetime.date.today().isoformat(), "tables": res})
    return 0


def selftest():
    rows = [{"C1_NM": "합계", "ITM_NM": "거래액", "PRD_DE": "202608", "DT": "21,000,000", "UNIT_NM": "백만원"},
            {"C1_NM": "컴퓨터", "ITM_NM": "거래액", "PRD_DE": "202608", "DT": "1", "UNIT_NM": "백만원"},
            {"C1_NM": "합계", "ITM_NM": "거래액", "PRD_DE": "202607", "DT": "-", "UNIT_NM": "백만원"}]
    s = slim(rows, ["합계"])
    assert s == [{"ym": "202608", "c": "합계", "item": "거래액", "v": 21000000.0, "unit": "백만원"}], s
    assert len(slim(rows, [])) == 2
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())

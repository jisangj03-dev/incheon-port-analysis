"""HS 관세율 자동 채움(P1 ② · 2026-10-15) — 공공데이터포털에서 관세율표(기본·WTO·FTA 협정세율)를 줄 수 있는 원천을 찾는다.
이 세션은 data.go.kr 에 못 닿아 Actions(tariff-probe 워크플로)에서 돈다. 키 = DATA_GO_KR_KEY(로그·산출물에 안 찍는다 · common.scrub).
하는 일: 이름으로 검색(오픈 API·파일 데이터 둘 다) → 오픈 API 는 명세(주소·요청 변수·이용허락) + 시험 호출 1~3번 · 파일 데이터는 화면 메타(이용허락·형식·수정일)만.
결과: data/collected/tariff_probe.json — 다음 단계(스냅샷 수집기)가 이것을 보고 원천을 고른다. 쓸 원천이 없거나 활용 신청이 필요하면 그 사실을 적는다(선장님 손).
  python tools-build/tariff_probe.py
"""
import datetime, html, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "v3"), HERE]
from common import KEY, get, write, say, scrub  # noqa: E402
from kr_apis import spec, call  # noqa: E402

QUERIES = ["관세청 관세율", "관세율표", "관세청 품목번호별 관세율", "관세청 HS부호", "FTA 협정세율", "관세청 관세율 기본"]


def find(q):
    st, h = get("https://www.data.go.kr/tcs/dss/selectDataSetList.do", {"keyword": q})
    out = []
    for m in re.finditer(r'href="/data/(\d{8})/(openapi|fileData)\.do[^"]*"[^>]*>([\s\S]{0,300}?)</a>', h or ""):
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(3)))).strip()
        if not any(o["id"] == m.group(1) for o in out): out.append({"id": m.group(1), "kind": m.group(2), "title": t[:120]})
    return st, out[:10]


def file_meta(did):
    st, h = get(f"https://www.data.go.kr/data/{did}/fileData.do")
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", h or ""))))
    g = lambda k: (re.search(k + r"\s*[:：]?\s*(.{0,60})", t) or [None, None])[1]
    return {"status": st, "title": (re.search(r"<title>([^<]*)", h or "") or [None, None])[1], "license": g("이용허락범위"), "ext": g("확장자"), "updated": g("수정일"), "cycle": g("업데이트 주기"),
            "download_links": sorted(set(re.findall(r"fileDownload\.do\?[^\"'\s]+", h or "")))[:5]}


def main():
    out = {"checked": datetime.date.today().isoformat(), "key_present": bool(KEY), "queries": {}, "datasets": {}}
    for q in QUERIES:
        st, c = find(q); out["queries"][q] = {"status": st, "hits": c}; say(q, st, len(c))
        for d in c:
            if d["id"] in out["datasets"] or not re.search(r"관세|HS|세율|FTA", d["title"]): continue
            rec = {**d}
            if d["kind"] == "openapi":
                rec["spec"] = sp = spec(d["id"])
                calls = []
                for ep in sp["endpoints"][:2]:
                    targets = [ep] if re.search(r"/get[A-Z]", ep) else [ep.rstrip("/") + "/" + op for op in sp["ops"][:2]] or [ep]
                    for u in targets[:2]:
                        r = call(u, {"hsSgn": "8471300000", "hsCd": "8471300000", "hs": "8471300000"})
                        r.pop("sample", None); calls.append(r)
                rec["calls"] = calls
            else:
                rec["file"] = file_meta(d["id"])
            out["datasets"][d["id"]] = rec
    write("data/collected/tariff_probe.json", json.loads(scrub(json.dumps(out, ensure_ascii=False))))
    say("후보", len(out["datasets"]), "→ data/collected/tariff_probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

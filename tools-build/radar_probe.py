"""채용·지원사업 레이더 탐침(2026-10-22 밤 · 선커밋 docs/측심_채용·지원사업레이더_판정기준_선커밋_20261022.md §2-1).

공공데이터포털 검색 → 데이터 번호 → 명세(요청 주소·기능) → 기능마다 한 번 부른다(키 = DATA_GO_KR_KEY · Actions 에서만 · 사고 132).
**행 값은 남기지 않는다** — 응답 코드 · 결과 코드 · 행 수 · 전체 건수 · 칸 이름만(채용 공고의 담당자 연락처 같은 개인정보가 공개 브랜치에 남지 않게).

  python tools-build/radar_probe.py      # 결과 data/collected/v3/radar_probe.json
  python tools-build/radar_probe.py --selftest
"""
import datetime, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "v3"), HERE]  # v3 공용 도구(common·kr_apis)·collect 를 빌려 쓴다 — 이 파일은 v3 밖에 둔다(v3/** 를 고치면 data-v3 워크플로가 깨어난다 · 10/22 실측)

# 원천 후보 — 검색어 · 제목에 들어야 할 낱말(엉뚱한 데이터를 잡지 않게)
FIND = {
    "alio-recruit": ("공공기관 채용정보 조회서비스", ["공공기관 채용정보"]),
    "bizinfo": ("중소기업 지원사업 공고 조회", ["지원사업 공고"]),
    "kstartup": ("창업진흥원 사업공고", ["사업공고"]),
}
# 1회차(10/22) — 명세 화면에 요청 주소가 없었다(비동기로 싣는다). 2회차: 화면의 상세 기능 조각(selectApiDetailFunction)을 따로 읽고,
#   그래도 없으면 알려진 주소 후보를 부른다(후보는 세션 지식 · [미확인] — 응답 코드가 판정한다).
GUESS = {
    "alio-recruit": ["https://apis.data.go.kr/1051000/recruitment/list"],
    "bizinfo": ["https://apis.data.go.kr/1421000/mssBizService_v2/getbizList_v2"],
}


def detail_endpoints(did, get):
    """명세 화면의 비동기 조각에서 요청 주소를 찾는다 — publicDataDetailPk 를 뽑아 기능 번호 1~4 를 읽는다."""
    st, h = get(f"https://www.data.go.kr/data/{did}/openapi.do")
    pk = (re.search(r'(uddi:[0-9a-f-]{20,})', h or "") or [None, None])[1]
    eps, tried = set(), []
    for n in range(1, 5):
        if not pk: break
        s2, h2 = get("https://www.data.go.kr/tcs/dss/selectApiDetailFunction.do", {"publicDataDetailPk": pk, "oprtinSeqNo": str(n)})
        found = re.findall(r"https?://apis\.data\.go\.kr/[A-Za-z0-9_/.-]+", h2 or "")
        tried.append({"n": n, "status": s2, "found": len(found)})
        eps.update(found)
    return pk, sorted(eps), tried


def shape(body, rows):
    """행 값 없이 모양만 — 전체 건수 · 첫 행의 칸 이름."""
    m = re.search(r'"?totalCount"?\s*[:>]\s*"?(\d+)', body or "")
    return {"total": int(m.group(1)) if m else None, "rows": len(rows), "keys": sorted(rows[0].keys()) if rows else []}


def main():
    from common import KEY, get, write, say, scrub
    from collect import parse
    from kr_apis import portal_find, spec
    out = {"checked": datetime.date.today().isoformat(), "key_present": bool(KEY), "note": "행 값은 저장하지 않는다(개인정보) — 칸 이름·건수만", "sources": {}}
    for sid, (q, want) in FIND.items():
        st, cands = portal_find(q)
        pick = [c for c in cands if all(w in c[1] for w in want)][:2]
        rec = {"search": q, "search_status": st, "candidates": cands[:6], "sets": {}}
        for did, title in pick:
            sp = spec(did)
            calls = []
            pk, deps, tried = detail_endpoints(did, get)
            eps = (sp["endpoints"] + deps)[:6] or GUESS.get(sid, [])
            urls = []
            for ep in eps:
                urls.append(ep)
                for op in [o for o in sp["ops"] if not o.startswith(("getCategory", "getElement", "getMypage", "getOrCreate", "getSso", "getTemplate"))][:4]:
                    if not ep.rstrip("/").endswith(op): urls.append(ep.rstrip("/") + "/" + op)
            for u in list(dict.fromkeys(urls))[:8]:
                p = {"serviceKey": KEY, "numOfRows": "5", "pageNo": "1", "type": "json", "_type": "json", "resultType": "json", "returnType": "json"}
                s2, b = get(u, p, timeout=40, tries=2)
                b = scrub(b)
                rc, msg, rows = parse(b)
                c = {"url": u, "status": s2, "resultCode": rc, "resultMsg": (msg or "")[:120], **shape(b, rows)}
                if not rows: c["body_head"] = (b or "")[:240]  # 오류 응답만(행이 없으면 개인정보도 없다)
                calls.append(c)
                say(sid, did, u.rsplit("/", 2)[-2:], s2, rc, c["rows"], c["total"])
            rec["sets"][did] = {"pk": pk, "detail_tried": tried, "guessed": not (sp["endpoints"] + deps),
                                "title": title, "license_text": sp.get("license_text"), "endpoints": sp["endpoints"], "ops": sp["ops"], "request_vars": (sp.get("request_vars") or "")[:800], "calls": calls}
        out["sources"][sid] = rec
    write("data/collected/v3/radar_probe.json", out)
    return 0


def selftest():
    s = shape('{"response":{"body":{"totalCount":37,"items":[]}}}', [{"b": 1, "a": "개인"}])
    assert s == {"total": 37, "rows": 1, "keys": ["a", "b"]}, s
    assert "개인" not in str(s)  # 값은 안 남는다
    print("radar_probe selftest OK (2)"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

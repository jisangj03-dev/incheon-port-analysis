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
# 1회차(10/22) — 명세 화면에 요청 주소가 없었다(비동기로 싣는다). 2회차: 비동기 조각(selectApiDetailFunction)이 500 이라 후보 주소를 불렀고 403.
# 3회차(10/23) — 요청 주소는 사람이 명세 화면(로그인 없이)에서 읽어 채팅으로 넘겼다. 이 주소는 추측이 아니다 — 그대로 부르고 덧붙이지 않는다.
KNOWN = {  # 데이터 번호 기준 — 같은 검색에 걸린 다른 데이터에는 안 부른다
    "15125273": ["https://apis.data.go.kr/1051000/recruitment/list"],  # /detail 은 공고 번호가 있어야 한다 — 목록이 열린 뒤에
    "15157820": ["https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService"],
    "15125364": ["https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01",
                 "https://apis.data.go.kr/B552735/kisedKstartupService01/getBusinessInformation01"],
}

KNOWN_BY_SOURCE = {"alio-recruit": "15125273", "bizinfo": "15157820", "kstartup": "15125364"}


def fetch(url, params, timeout=40):
    """common.get 은 HTTP 오류의 본문을 버린다 — 403 이 「등록되지 않은 키」인지 「없는 주소」인지 갈라 보려고 오류 본문 머리를 받는다."""
    import urllib.error, urllib.parse, urllib.request
    from common import UA, scrub
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace"), ""
    except urllib.error.HTTPError as e:
        return e.code, "", scrub(e.read().decode("utf-8", "replace"))[:240]
    except Exception as e:
        return scrub(str(e))[:160], "", ""


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
        known = KNOWN_BY_SOURCE.get(sid)
        if known and known not in [d for d, _ in pick]: pick.append((known, None))  # 포털 검색이 끊겨도(4회차 시간 초과) 아는 주소는 부른다
        rec = {"search": q, "search_status": st, "candidates": cands[:6], "sets": {}}
        for did, title in pick:
            # 아는 주소면 비동기 조각은 안 읽는다 · 포털이 안 열리면 명세도 안 읽는다(한 번에 3분씩 걸려 잡 한도 15분을 넘긴다)
            sp = spec(did) if st == 200 else {"endpoints": [], "ops": [], "license_text": None, "request_vars": None}
            calls = []
            pk, deps, tried = (None, [], []) if did in KNOWN else detail_endpoints(did, get)
            if did in KNOWN:
                urls = KNOWN[did]
            else:
                eps = (sp["endpoints"] + deps)[:6]
                urls = []
                for ep in eps:
                    urls.append(ep)
                    for op in [o for o in sp["ops"] if not o.startswith(("getCategory", "getElement", "getMypage", "getOrCreate", "getSso", "getTemplate"))][:4]:
                        if not ep.rstrip("/").endswith(op): urls.append(ep.rstrip("/") + "/" + op)
            for u in list(dict.fromkeys(urls))[:8]:
                p = {"serviceKey": KEY, "numOfRows": "5", "pageNo": "1", "type": "json", "_type": "json", "resultType": "json", "returnType": "json"}
                s2, b, eb = fetch(u, p)
                b = scrub(b)
                rc, msg, rows = parse(b)
                c = {"url": u, "status": s2, "resultCode": rc, "resultMsg": (msg or "")[:120], **shape(b, rows)}
                if not rows: c["body_head"] = (b or eb or "")[:240]  # 오류 응답만(행이 없으면 개인정보도 없다)
                calls.append(c)
                say(sid, did, u.rsplit("/", 2)[-2:], s2, rc, c["rows"], c["total"])
            rec["sets"][did] = {"pk": pk, "detail_tried": tried, "endpoint_source": "명세 화면(사람 · 10/23 채팅)" if did in KNOWN else "명세 화면(자동)",
                                "title": title, "license_text": sp.get("license_text"), "endpoints": sp["endpoints"], "ops": sp["ops"], "request_vars": (sp.get("request_vars") or "")[:800], "calls": calls}
        out["sources"][sid] = rec
    write("data/collected/v3/radar_probe.json", out)
    return 0


def selftest():
    s = shape('{"response":{"body":{"totalCount":37,"items":[]}}}', [{"b": 1, "a": "개인"}])
    assert s == {"total": 37, "rows": 1, "keys": ["a", "b"]}, s
    assert "개인" not in str(s)  # 값은 안 남는다
    assert all(u.startswith("https://apis.data.go.kr/") for v in KNOWN.values() for u in v)
    print("radar_probe selftest OK (3)"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

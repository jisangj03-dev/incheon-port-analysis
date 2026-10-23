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
# 8회차 — 원천마다 요청 변수가 다르다(7회차: 지원사업은 perPage·page·30행을 붙이자 「HTTP_ERROR(04)」 · 5회차 5행은 정상).
#   변형마다 한 번씩 불러 전체 건수가 줄어드는지 본다 — 서버 쪽 거르기(진행 중 · 분야)가 되면 하루 호출 한도 안에서 다 받을 수 있다.
BASE_P = {"alio-recruit": {"numOfRows": "30", "pageNo": "1", "resultType": "json"},
          "bizinfo": {"numOfRows": "10", "pageNo": "1"},
          "kstartup": {"perPage": "30", "page": "1", "returnType": "json"}}
VARIANTS = {"alio-recruit": [{}, {"ongoingYn": "Y"}],
            "bizinfo": [{}, {"searchLclasId": "04"}],
            "kstartup": [{}, {"cond[rcrt_prgs_yn::EQ]": "Y"}]}


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


def json_rows(body):
    """공공데이터포털 JSON 은 원천마다 꼴이 다르다(response.body.items.item · data · result …) — 가장 긴 「사전의 목록」을 행으로 본다."""
    import json
    try: d = json.loads(body)
    except ValueError: return []
    best = []
    def walk(x):
        nonlocal best
        if isinstance(x, list):
            if len(x) > len(best) and x and all(isinstance(i, dict) for i in x): best = x
            for i in x: walk(i)
        elif isinstance(x, dict):
            for v in x.values(): walk(v)
    walk(d)
    return [{k: ("" if v is None else str(v)) for k, v in r.items()} for r in best]


def xml_rows(body):
    """XML 응답을 ElementTree 로 — <item> 의 자식 칸 이름과 글(CDATA 포함 · 안쪽 태그는 글만)."""
    import xml.etree.ElementTree as ET
    try: root = ET.fromstring(body.strip().encode("utf-8"))
    except ET.ParseError: return []
    return [{ch.tag: "".join(ch.itertext()).strip() for ch in it} for it in root.iter("item")]


def shape(body, rows):
    """행 값 없이 모양만 — 전체 건수 · 칸 이름(전 행 합집합) · 칸마다 채워진 행 수와 가장 긴 글자 수."""
    m = re.search(r'"?totalCount"?\s*[:>]\s*"?(\d+)', body or "")
    keys = sorted({k for r in rows for k in r})
    fill = {k: [sum(1 for r in rows if (r.get(k) or "").strip()), max((len(r.get(k) or "") for r in rows), default=0)] for k in keys}
    return {"total": int(m.group(1)) if m else None, "rows": len(rows), "keys": keys, "fill": fill, "classes": classes(rows, keys)}


# 고르는 칸 후보(분류·기관·지역 꼴 이름)만 값 분포를 남긴다 — 사람을 가리킬 수 있는 칸은 이름으로 먼저 뺀다(담당자·대표자·연락처·주소)
CLASS_KEY = re.compile(r"(Nm|Cd|Se|Rgn|Area|Realm|Clss|Ty|Type|Yn|Gb|Div)$|(rgn|regin|area|region|realm|lclas|clsfc|trgt|sido|instt|inst|ncs|type|kind|hashtag)", re.I)
TAG_KEY = re.compile(r"hashtag|Lst$", re.I)  # 쉼표로 여러 값을 담는 칸 — 낱값으로 쪼개 센다
PERSON_KEY = re.compile(r"chrg|charger|rprs|ceo|psn|pic|mngr|manager|tel|phone|fax|mail|addr|homepage|url|link", re.I)


def classes(rows, keys):
    """칸마다 서로 다른 값이 40 이하이고 값이 짧을 때만(분류 칸의 꼴) 상위 15 값과 행 수 — 공고명·본문 같은 긴 글은 남지 않는다."""
    out = {}
    for k in keys:
        if PERSON_KEY.search(k) or not CLASS_KEY.search(k): continue
        vals = [(r.get(k) or "").strip() for r in rows]
        if TAG_KEY.search(k): vals = [t.strip() for v in vals for t in v.split(",")]
        vals = [v for v in vals if v]
        if not vals or len(set(vals)) > 40 or max(len(v) for v in vals) > 40: continue
        cnt = {}
        for v in vals: cnt[v] = cnt.get(v, 0) + 1
        out[k] = sorted(cnt.items(), key=lambda kv: -kv[1])[:15]
    return out


def main():
    from common import KEY, get, write, say, scrub
    from collect import parse
    from kr_apis import portal_find, spec
    out = {"checked": datetime.date.today().isoformat(), "key_present": bool(KEY), "note": "행 값은 저장하지 않는다(개인정보) — 칸 이름·건수만", "sources": {}}
    for sid, (q, want) in FIND.items():
        # 아는 주소면 포털 검색을 건너뛴다 — 검색 화면이 자주 끊겨(4·6회차) 한 원천에 3분씩 먹는다 · 이용허락은 kogl_check 가 따로 잰다
        st, cands = ("생략 — 아는 주소", []) if sid in KNOWN_BY_SOURCE else portal_find(q)
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
              for var in (VARIANTS.get(sid) or [{}]):
                p = {"serviceKey": KEY, **(BASE_P.get(sid) or {"numOfRows": "10", "pageNo": "1", "type": "json"}), **var}
                s2, b, eb = fetch(u, p, timeout=90)
                if not isinstance(s2, int): s2, b, eb = fetch(u, p, timeout=90)  # 6회차: 100행 · 40초에 넷 다 시간 초과 → 30행 · 90초 · 한 번 더
                b = scrub(b)
                rc, msg, rows = parse(b)
                if (b or "").lstrip().startswith(("{", "[")) and not any(rows): rows = json_rows(b)  # parse 가 꼴을 못 알아 빈 행 하나를 낸 경우(5회차 채용·K-Startup)
                elif (b or "").lstrip().startswith("<"): rows = xml_rows(b) or rows  # 태그 정규식은 CDATA·본문 안 HTML 칸을 놓친다(5회차 지원사업 「p」 칸)
                c = {"url": u, "params": {k: v for k, v in p.items() if k != "serviceKey"}, "status": s2, "resultCode": rc, "resultMsg": (msg or "")[:120], **shape(b, rows)}
                if not rows: c["body_head"] = (b or eb or "")[:240]  # 오류 응답만(행이 없으면 개인정보도 없다)
                calls.append(c)
                say(sid, did, u.rsplit("/", 1)[-1], var, s2, rc, c["rows"], c["total"])
            rec["sets"][did] = {"pk": pk, "detail_tried": tried, "endpoint_source": "명세 화면(사람 · 10/23 채팅)" if did in KNOWN else "명세 화면(자동)",
                                "title": title, "license_text": sp.get("license_text"), "endpoints": sp["endpoints"], "ops": sp["ops"], "request_vars": (sp.get("request_vars") or "")[:800], "calls": calls}
        out["sources"][sid] = rec
    write("data/collected/v3/radar_probe.json", out)
    return 0


def selftest():
    s = shape('{"response":{"body":{"totalCount":37,"items":[]}}}', [{"b": "1", "a": "개인"}, {"c": ""}])
    assert s == {"total": 37, "rows": 2, "keys": ["a", "b", "c"], "fill": {"a": [1, 2], "b": [1, 1], "c": [0, 0]}, "classes": {}}, s
    c = classes([{"instNm": "인천항만공사", "chrgerNm": "홍길동", "telNo": "032"}, {"instNm": "인천항만공사"}], ["chrgerNm", "instNm", "telNo"])
    assert c == {"instNm": [("인천항만공사", 2)]}, c  # 담당자·전화는 이름으로 빠진다
    x = xml_rows("<response><body><items><item><pblancNm><![CDATA[수출 <b>바우처</b>]]></pblancNm><hashtags>서울,수출</hashtags></item></items></body></response>")
    assert x == [{"pblancNm": "수출 <b>바우처</b>", "hashtags": "서울,수출"}], x
    assert classes(x + [{"hashtags": "인천,수출"}], ["hashtags"]) == {"hashtags": [("수출", 2), ("서울", 1), ("인천", 1)]}
    assert json_rows('{"currentCount":2,"data":[{"x":1},{"x":null,"y":"z"}],"meta":[{"q":1}]}') == [{"x": "1"}, {"x": "", "y": "z"}]
    assert "개인" not in str(s)  # 값은 안 남는다
    assert all(u.startswith("https://apis.data.go.kr/") for v in KNOWN.values() for u in v)
    print("radar_probe selftest OK (6)"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

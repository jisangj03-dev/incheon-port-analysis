"""채용·지원사업 레이더 수집(2026-10-23 · 선커밋 docs/측심_채용·지원사업레이더_판정기준_선커밋_20261022.md §2-3 · §3-가 · §6).

refresh 의 한 단계(매일)다. 키 = DATA_GO_KR_KEY(Actions 에서만 · 사고 132). 고르는 규칙은 선커밋 §6 을 그대로 옮긴 것이다 — 여기서 바꾸지 않는다.
  · 채용(15125273) — 진행 중(ongoingYn=Y · 서버 쪽 거르기) 전부를 받아 기관명 `instNm` 이 고정 목록 열한 곳과 글자 그대로 같은 것만.
  · 지원사업(15157820) — 수출(searchLclasId=04 · 서버 쪽 거르기) 전부를 받아 분야 칸이 「수출」이고 `hashtags` 낱값에 서울·인천·경기·전국 중 하나가 있는 것만.
  · K-Startup(15125364) — 미달(§6 · 분야 칸에 물류·수출 갈래 없음). 부르지 않는다.
싣는 칸은 선커밋이 적은 칸뿐이고 글자를 바꾸지 않는다(공공누리 3유형 · §3-가). 담당자·연락처·본문 칸은 받아도 버린다.
한 쪽이라도 덜 오면 지난 파일을 지키고 종료 1(refresh 가 일시·인증을 가른다).
결과: data/collected/v3/radar.json
  python tools-build/radar.py
  python tools-build/radar.py --selftest
"""
import datetime, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "v3"), HERE]  # v3 공용 도구를 빌려 쓴다 — 이 파일은 v3 밖에 둔다(사고 139)

OUT = "data/collected/v3/radar.json"
KST = datetime.timezone(datetime.timedelta(hours=9))

ORGS = ["인천항만공사", "부산항만공사", "여수광양항만공사", "울산항만공사", "인천국제공항공사", "한국공항공사",
        "한국해양진흥공사", "대한무역투자진흥공사", "한국무역보험공사", "한국해양수산개발원", "한국해양교통안전공단"]  # 선커밋 §1 — 바꾸면 그 절에 「바꿈」
REGIONS = ["서울", "인천", "경기", "전국"]  # 선커밋 §6 — hashtags 낱값 글자 그대로
SIDO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "전국", "전남광주"]  # 분포 기록용(고르기에는 REGIONS 만)

RECRUIT = {"url": "https://apis.data.go.kr/1051000/recruitment/list", "rows": 50,
           "params": {"resultType": "json", "ongoingYn": "Y"},
           "keep": ["recrutPblntSn", "recrutPbancTtl", "instNm", "recrutSeNm", "hireTypeNmLst", "ncsCdNmLst", "workRgnNmLst", "pbancBgngYmd", "pbancEndYmd", "srcUrl"]}
SUPPORT = {"url": "https://apis.data.go.kr/1421000/bizinfo/pblancBsnsService", "rows": 10,  # 30행 · perPage 는 HTTP_ERROR(04) — 탐침 7회차
           "params": {"searchLclasId": "04"},
           "keep": ["pblancId", "pblancNm", "jrsdInsttNm", "excInsttNm", "pldirSportRealmLclasCodeNm", "trgetNm", "reqstBeginEndDe", "pblancUrl", "hashtags"]}
MAX_PAGES = 40  # 채용 473건 ÷ 50 = 10쪽 · 지원사업 187건 ÷ 10 = 19쪽(10/23) — 넘으면 원천이 바뀐 것이라 멈춘다


def fetch(url, params, timeout=90, tries=3):
    """(상태, 본문, 오류 본문 머리). common.get 은 HTTP 오류 본문을 버려서 「미등록 키」를 못 가른다 — 탐침과 같은 꼴."""
    import urllib.error, urllib.parse, urllib.request
    from common import UA, scrub
    req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    last = (None, "", "")
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace"), ""
        except urllib.error.HTTPError as e:
            last = (e.code, "", scrub(e.read().decode("utf-8", "replace"))[:240])
            if e.code in (401, 403): break  # 인증은 다시 불러도 안 풀린다
        except Exception as e:
            last = (scrub(str(e))[:160], "", "")
        time.sleep(3 * (i + 1))
    return last


def json_rows(body):
    """가장 긴 「사전의 목록」을 행으로(채용 응답은 response.body.items 꼴이 아니다 — 탐침 5회차)."""
    d = json.loads(body)
    best = []
    def walk(x):
        nonlocal best
        if isinstance(x, list):
            if x and all(isinstance(i, dict) for i in x) and len(x) > len(best): best = x
            for i in x: walk(i)
        elif isinstance(x, dict):
            for v in x.values(): walk(v)
    walk(d)
    tc = re.search(r'"totalCount"\s*:\s*"?(\d+)', body)
    return [{k: ("" if v is None else str(v)) for k, v in r.items()} for r in best], (int(tc.group(1)) if tc else None)


def xml_rows(body):
    """지원사업은 XML — <item> 자식의 글(CDATA 포함). 결과 코드가 00 이 아니면 오류."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(body.strip().encode("utf-8"))
    rc = (root.findtext(".//resultCode") or "").strip()
    if rc and rc != "00": raise RuntimeError(f"지원사업 결과 코드 {rc} {(root.findtext('.//resultMsg') or '').strip()}")
    tc = root.findtext(".//totalCount")
    return [{ch.tag: "".join(ch.itertext()).strip() for ch in it} for it in root.iter("item")], (int(tc) if tc and tc.strip().isdigit() else None)


def pull(spec, kind):
    """서버 쪽 거르기를 건 채로 끝 쪽까지. 반환 (행 목록, 원천 전체 건수). 덜 오면 예외 — 부분 목록을 싣지 않는다."""
    from common import KEY
    if not KEY: raise RuntimeError("키 없음 — DATA_GO_KR_KEY")
    rows, total, page = [], None, 1
    while page <= MAX_PAGES:
        p = {"serviceKey": KEY, "numOfRows": str(spec["rows"]), "pageNo": str(page), **spec["params"]}
        st, b, eb = fetch(spec["url"], p)
        if st != 200 or not b.strip():
            raise RuntimeError(f"{kind} {page}쪽 HTTP {st} {eb[:160]}")
        if "SERVICE_KEY_IS_NOT_REGISTERED" in b or "HTTP_ERROR" in b[:400]:
            raise RuntimeError(f"{kind} {page}쪽 오류 응답 {b[:160]}")
        got, tc = (json_rows(b) if b.lstrip().startswith("{") else xml_rows(b))
        if tc is not None: total = tc
        rows += got
        if not got or (total is not None and len(rows) >= total): break
        page += 1
    else:
        raise RuntimeError(f"{kind} 쪽 수가 {MAX_PAGES} 를 넘었다 — 원천 건수가 크게 바뀌었다(서버 쪽 거르기가 풀렸을 수 있다)")
    if total is None: raise RuntimeError(f"{kind} 전체 건수(totalCount)가 응답에 없다")
    if len(rows) < total: raise RuntimeError(f"{kind} 덜 왔다 — {len(rows)} / {total}")
    return rows, total


def end_of(text):
    """기간 글에서 끝 날짜(YYYYMMDD 또는 YYYY-MM-DD · YYYY.MM.DD) — 날짜 꼴이 둘 이상이면 마지막 것. 없으면 None(상시·예산 소진 등 — 빼지 않는다)."""
    ds = re.findall(r"(20\d\d)[-.]?([01]\d)[-.]?([0-3]\d)", text or "")
    return "".join(ds[-1]) if ds else None


def tags(s):
    return [t.strip() for t in (s or "").split(",") if t.strip()]


def pick_recruit(rows, today):
    out, drop = [], {"기관 목록 밖": 0, "마감 지남": 0, "진행 아님": 0}
    for r in rows:
        if r.get("ongoingYn", "Y") != "Y": drop["진행 아님"] += 1; continue
        if r.get("instNm") not in ORGS: drop["기관 목록 밖"] += 1; continue
        if (r.get("pbancEndYmd") or "99999999")[:8] < today: drop["마감 지남"] += 1; continue
        out.append({k: r.get(k, "") for k in RECRUIT["keep"]})
    out.sort(key=lambda x: ((x["pbancEndYmd"] or "99999999")[:8], x["instNm"]))  # 원천 날짜 칸 순서(§3-가 허용)
    return out, drop


def pick_support(rows, today):
    out, drop = [], {"분야 수출 아님": 0, "지역 낱값 없음(서울·인천·경기·전국)": 0, "마감 지남": 0}
    for r in rows:
        if r.get("pldirSportRealmLclasCodeNm") != "수출": drop["분야 수출 아님"] += 1; continue
        if not set(tags(r.get("hashtags"))) & set(REGIONS): drop["지역 낱값 없음(서울·인천·경기·전국)"] += 1; continue
        e = end_of(r.get("reqstBeginEndDe"))
        if e and e < today: drop["마감 지남"] += 1; continue
        x = {k: r.get(k, "") for k in SUPPORT["keep"]}
        x["regions"] = [t for t in tags(r.get("hashtags")) if t in REGIONS]  # 고른 근거(원천 낱값 그대로) — 지면이 「고른 까닭」으로 보인다
        x["_end"] = e or ""  # 정렬용(지면에 안 보인다)
        out.append(x)
    out.sort(key=lambda x: (x["_end"] or "99999999", x["pblancNm"]))
    return out, drop


def region_dist(rows):
    """수출 행의 hashtags 안 시도 낱값 분포 — 지역 규칙이 무엇을 거르는지 판정자가 보게(값은 시도 이름뿐)."""
    c = {}
    for r in rows:
        for t in set(tags(r.get("hashtags"))) & set(SIDO): c[t] = c.get(t, 0) + 1
    none = sum(1 for r in rows if not set(tags(r.get("hashtags"))) & set(SIDO))
    return {"by_sido": dict(sorted(c.items(), key=lambda kv: -kv[1])), "no_sido_tag": none}


def region_n(items):
    """지역 단추 숫자 — 남긴 공고 가운데 그 지역 낱값을 단 공고 수. 지면이 빌드 때 세면 그 수가 데이터 파일에 없어
    「지면 숫자 = 데이터 파일」 검사가 다른 숫자와 우연히 겹칠 때만 통과한다(사고 141) — 그래서 여기서 세어 파일에 둔다."""
    return {r: sum(1 for x in items if r in x["regions"]) for r in REGIONS}


def main():
    from common import write, say
    now = datetime.datetime.now(KST)
    today = now.strftime("%Y%m%d")
    try:
        rr, rt = pull(RECRUIT, "채용")
        sr, stt = pull(SUPPORT, "지원사업")
    except Exception as e:
        say("레이더 받기 실패 — 지난 파일을 지킨다:", e)
        print(f"레이더 받기 실패: {e}", file=sys.stderr)
        return 1
    ri, rd = pick_recruit(rr, today)
    si, sd = pick_support(sr, today)
    data = {
        "_설명": "채용·지원사업 레이더 스냅샷 — tools-build/radar.py(refresh 매일). 규칙 = 선커밋 §6. 항목 글자는 원천 응답 그대로(§3-가). 담당자·연락처·본문 칸은 받지 않는다.",
        # 받은 시각은 시각 키(fetched)다 — 목록이 그대로인 날은 refresh 가 커밋·배포하지 않는다(refresh.STAMP_KEYS). 목록이 바뀐 날만 지면이 새로 뜬다
        "fetched": now.strftime("%Y-%m-%d %H:%M"),
        "recruit": {"source": "15125273", "scanned": rt, "got": len(rr), "n": len(ri), "dropped": rd, "orgs": ORGS,
                    "by_org": {o: sum(1 for x in ri if x["instNm"] == o) for o in ORGS}, "items": ri},
        "support": {"source": "15157820", "scanned": stt, "got": len(sr), "n": len(si), "dropped": sd, "regions": REGIONS, "region_n": region_n(si),
                    "region_dist": region_dist([r for r in sr if r.get("pldirSportRealmLclasCodeNm") == "수출"]), "items": si},
        "kstartup": {"source": "15125364", "verdict": "미달 — 분야 칸(supt_biz_clsfc)에 물류·무역·수출 갈래가 없다(선커밋 §6)"},
    }
    write(OUT, data)
    say("레이더", data["fetched"], "· 채용", f"{len(ri)}/{rt}", "· 지원사업", f"{len(si)}/{stt}", "· 지역 분포", data["support"]["region_dist"])
    return 0


def selftest():
    assert end_of("20261001 ~ 20261031") == "20261031" and end_of("2026-10-01 ~ 2026.11.07") == "20261107" and end_of("예산 소진 시까지") is None
    rows = [{"instNm": "인천항만공사", "ongoingYn": "Y", "pbancEndYmd": "20261105", "recrutPbancTtl": "A", "chrgerNm": "홍길동"},
            {"instNm": "인천항만공사(본사)", "ongoingYn": "Y", "pbancEndYmd": "20261105"},
            {"instNm": "울산항만공사", "ongoingYn": "Y", "pbancEndYmd": "20261001"},
            {"instNm": "한국공항공사", "ongoingYn": "N", "pbancEndYmd": "20261201"}]
    ri, rd = pick_recruit(rows, "20261023")
    assert [x["instNm"] for x in ri] == ["인천항만공사"] and rd == {"기관 목록 밖": 1, "마감 지남": 1, "진행 아님": 1}, (ri, rd)
    assert "chrgerNm" not in ri[0] and set(ri[0]) == set(RECRUIT["keep"])  # 담당자 칸은 버린다
    srows = [{"pldirSportRealmLclasCodeNm": "수출", "hashtags": "수출,인천,중소기업", "reqstBeginEndDe": "20261001 ~ 20261130", "pblancNm": "B"},
             {"pldirSportRealmLclasCodeNm": "수출", "hashtags": "수출,부산", "reqstBeginEndDe": "20261001 ~ 20261130", "pblancNm": "C"},
             {"pldirSportRealmLclasCodeNm": "수출", "hashtags": "수출,중소기업", "reqstBeginEndDe": "상시", "pblancNm": "D"},
             {"pldirSportRealmLclasCodeNm": "수출", "hashtags": "전국,수출", "reqstBeginEndDe": "예산 소진 시까지", "pblancNm": "E"},
             {"pldirSportRealmLclasCodeNm": "수출", "hashtags": "경기도,수출", "reqstBeginEndDe": "20261001 ~ 20261130", "pblancNm": "F"},  # 「경기도」 ≠ 「경기」 — 글자 그대로
             {"pldirSportRealmLclasCodeNm": "내수", "hashtags": "서울", "reqstBeginEndDe": "20261001 ~ 20261130", "pblancNm": "G"},
             {"pldirSportRealmLclasCodeNm": "수출", "hashtags": "서울", "reqstBeginEndDe": "20260901 ~ 20261010", "pblancNm": "H"}]
    si, sd = pick_support(srows, "20261023")
    assert [x["pblancNm"] for x in si] == ["B", "E"], si
    assert sd == {"분야 수출 아님": 1, "지역 낱값 없음(서울·인천·경기·전국)": 3, "마감 지남": 1}, sd
    assert si[0]["regions"] == ["인천"] and si[0]["reqstBeginEndDe"] == "20261001 ~ 20261130"  # 글자 그대로
    assert region_n(si) == {r: (1 if r in ("인천", "전국") else 0) for r in REGIONS}, region_n(si)
    assert region_dist(srows[:3]) == {"by_sido": {"인천": 1, "부산": 1}, "no_sido_tag": 1}
    j, t = json_rows('{"resultCode":200,"totalCount":2,"result":[{"a":1},{"a":null}]}')
    assert j == [{"a": "1"}, {"a": ""}] and t == 2
    x, t = xml_rows("<response><header><resultCode>00</resultCode></header><body><items><item><pblancNm><![CDATA[수출 <b>바우처</b>]]></pblancNm></item></items><totalCount>1</totalCount></body></response>")
    assert x == [{"pblancNm": "수출 <b>바우처</b>"}] and t == 1
    print("radar selftest OK (10)"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

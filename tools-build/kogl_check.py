"""출처 대장의 「공공누리 유형 미확인」 원천을 공식 제공 페이지에서 직접 확인한다(2026-10-14 채팅 검수 · #49 ②-3).

이 세션(클라우드)은 공공데이터포털·해양수산부 화면이 막혀 있어 Actions 에서 돈다(키 없음 · 공개 화면만 읽는다).
읽는 것: 공공데이터포털 데이터 상세 화면의 「이용허락범위」 칸과 공공누리 표시(그림 alt · 글자), 해양수산부 게시판 글의 공공누리 마크.
쓰는 것: data/collected/kogl_check.json — 원천마다 확인한 주소 · 받은 날 · 응답 코드 · 「이용허락범위」 원문 · 공공누리 유형(찾은 것만) · 근거 글 조각.
판정(대장 고치기)은 사람이 읽고 한다 — 이 스크립트는 화면에 적힌 글자만 옮긴다. 못 찾은 것은 null(「미확인」 그대로).
  python tools-build/kogl_check.py [--selftest]
"""
import datetime, html, json, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/collected/kogl_check.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) sounding-kogl-check/1.0 (+https://github.com/jisangj03-dev/incheon-port-analysis) — license fields only"

# 원천 → 공공데이터포털 데이터 번호(알면) 또는 검색어(모르면 검색 결과에서 번호를 찾는다)
SOURCES = {
    "ipa-empty-container": {"q": "인천항만공사 공컨테이너"},
    "kcs-porttrade": {"q": "관세청 항구공항별 수출입실적"},
    "kcs-sido-item": {"id": "15101641"},
    "molit-warehouse": {"id": "15083282"},
    "kcs-nitemtrade": {"q": "관세청 품목별 국가별 수출입실적"},
    "mof-vessel": {"id": "15059059"},
    "mof-incheon-port-stats": {"board": "https://incheon.mof.go.kr/ko/board.do?menuIdx=1700"},
}
KOGL = re.compile(r"공공누리\s*(?:제\s*)?([1-4])\s*유형|KOGL\s*(?:Type\s*)?([1-4])|img_opentype0?([1-4])|opentype_?0?([1-4])", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:  # 막힘·시간 초과도 결과로 남긴다(통과로 세지 않는다)
        return getattr(e, "code", None) or str(e)[:120], ""


def text(h):
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", h, flags=re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def parse(h):
    """화면 원문에서 이용허락범위 · 공공누리 유형 · 근거 조각을 뽑는다."""
    t = text(h)
    lic = None
    m = re.search(r"이용허락범위\s*[:：]?\s*(.{0,40})", t)
    if m: lic = m.group(1).strip()
    kogl, ev = None, []
    for m in KOGL.finditer(h):
        kogl = kogl or next(g for g in m.groups() if g)
        ev.append(h[max(0, m.start() - 60): m.end() + 60].replace("\n", " "))
    for m in re.finditer(r"공공누리[^<]{0,60}", t):
        ev.append(m.group(0))
    return {"license_text": lic, "kogl_type": int(kogl) if kogl else None, "evidence": ev[:4]}


def find_id(q):
    st, h = get("https://www.data.go.kr/tcs/dss/selectDataSetList.do?" + urllib.parse.urlencode({"keyword": q}))
    m = re.search(r"/data/(\d{8})/(?:openapi|fileData)\.do", h)
    return (m.group(1) if m else None), st


def main():
    out = {"checked": datetime.date.today().isoformat(), "command": "python tools-build/kogl_check.py", "sources": {}}
    for sid, s in SOURCES.items():
        rec = {}
        if "board" in s:
            st, h = get(s["board"])
            rec = {"url": s["board"], "status": st}
            # 목록의 첫 글을 연다(공공누리 마크는 글 본문 아래에 붙는다)
            m = re.search(r'href="([^"]*board\.do\?[^"]*boardIdx=\d+[^"]*)"', h)
            if m:
                post = urllib.parse.urljoin(s["board"], html.unescape(m.group(1)))
                st2, h2 = get(post)
                rec.update({"post": post, "post_status": st2}, **parse(h2))
            else:
                rec.update(parse(h))
        else:
            did, st0 = (s["id"], None) if "id" in s else find_id(s["q"])
            rec = {"search": s.get("q"), "search_status": st0, "data_id": did}
            if did:
                for kind in ("openapi", "fileData"):
                    url = f"https://www.data.go.kr/data/{did}/{kind}.do"
                    st, h = get(url)
                    if st == 200 and "이용허락" in h:
                        rec.update({"url": url, "status": st}, **parse(h)); break
                    rec.update({"url": url, "status": st})
        out["sources"][sid] = rec
        print(sid, json.dumps({k: rec.get(k) for k in ("status", "data_id", "license_text", "kogl_type")}, ensure_ascii=False))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


def selftest():
    p = parse('<th>이용허락범위</th><td>제한 없음</td><img src="/img/img_opentype01.png" alt="공공누리 제1유형">')
    assert p["license_text"].startswith("제한 없음") and p["kogl_type"] == 1, p
    assert parse("<p>아무것도 없음</p>") == {"license_text": None, "kogl_type": None, "evidence": []}
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

"""채용·지원사업 레이더 탐침(2026-10-22 밤 · 선커밋 docs/측심_채용·지원사업레이더_판정기준_선커밋_20261022.md §2-1).

공공데이터포털 검색 → 데이터 번호 → 명세(요청 주소·기능) → 기능마다 한 번 부른다(키 = DATA_GO_KR_KEY · Actions 에서만 · 사고 132).
**행 값은 남기지 않는다** — 응답 코드 · 결과 코드 · 행 수 · 전체 건수 · 칸 이름만(채용 공고의 담당자 연락처 같은 개인정보가 공개 브랜치에 남지 않게).

  python tools-build/v3/radar_probe.py      # 결과 data/collected/v3/radar_probe.json
  python tools-build/v3/radar_probe.py --selftest
"""
import datetime, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 원천 후보 — 검색어 · 제목에 들어야 할 낱말(엉뚱한 데이터를 잡지 않게)
FIND = {
    "alio-recruit": ("공공기관 채용정보", ["채용"]),
    "bizinfo": ("기업마당 지원사업", ["지원사업"]),
    "kstartup": ("K-Startup 사업공고", ["사업공고"]),
}


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
            eps = sp["endpoints"][:4]
            urls = []
            for ep in eps:
                urls.append(ep)
                for op in sp["ops"][:4]:
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
            rec["sets"][did] = {"title": title, "license_text": sp.get("license_text"), "endpoints": sp["endpoints"], "ops": sp["ops"], "request_vars": (sp.get("request_vars") or "")[:800], "calls": calls}
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

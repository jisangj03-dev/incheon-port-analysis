"""경기 시·군별 물류창고 등록 개소(2026-10-20 · docs/품질기준.md Q2·Q3) — 홈 수도권 흐름의 경기 몫을 실측으로 바꾼다.

종전: 경기 2,290곳(시도 집계표 · 실측)을 밀집지 여섯(김포·부천·이천·용인·안성·광주)에 **똑같이 나눴다(가정)** —
독립 사실 대조가 「지어낸 분배」로 잡았다. 시·군별 개소는 주소가 든 행 단위 목록에만 있고, 그 파일은 공공데이터포털
파일데이터(15083282 「국토교통부_물류창고업등록정보」 · 이용허락범위 제한 없음)다. 세션 컨테이너는 *.go.kr 에 못 닿아 Actions 에서 받는다.

남기는 것 = 시·군 이름별 **개수만**(주소·상호·대표자·전화 열은 산출물에 들어갈 경로가 없다 — 세고 버린다).
포털 내려받기 경로는 화면 스크립트가 쓰는 것을 차례로 시도한다 — 못 받으면 진단만 남기고 지난 파일을 지킨다(빨강이 아니라 경고).

  python tools-build/gg_warehouse.py            # 결과 data/derived/gg_warehouse.json · 진단 data/collected/gg_warehouse_diag.json
  python tools-build/gg_warehouse.py --selftest
"""
import csv, io, json, os, re, sys, urllib.parse, urllib.request, datetime, http.cookiejar, http.client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/gg_warehouse.json")
DIAG = os.path.join(ROOT, "data/collected/gg_warehouse_diag.json")
PK = "15083282"
PAGE = f"https://www.data.go.kr/data/{PK}/fileData.do"
UA = {"User-Agent": "Mozilla/5.0 (sounding-collector; github actions)", "Referer": PAGE}  # 머리글은 latin-1 — 한글을 넣으면 요청이 안 나간다(첫 실행 10/20)
ADDR = ["소재지도로명주소", "소재지지번주소", "도로명주소", "지번주소", "소재지", "주소", "창고소재지", "소재지주소"]
diag = {"page": PAGE, "tried": []}


# 포털은 화면을 연 세션(쿠키)에서만 파일을 내준다 — 쿠키 없이 부르면 머리만 오고 끊겼다(IncompleteRead · 두 번째 실행 10/20)
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def get(url, data=None, ctype=None):
    h = dict(UA)
    if ctype: h["Content-Type"] = ctype
    req = urllib.request.Request(url, data=data, headers=h)
    with OPENER.open(req, timeout=90) as r:
        try: body = r.read()
        except http.client.IncompleteRead as e: body = e.partial
        return r.status, dict(r.headers), body


def decode(b):
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try: return b.decode(enc)
        except UnicodeDecodeError: pass
    return b.decode("utf-8", "replace")


def sigungu(addr):
    """「경기도 김포시 …」·「경기 이천시 …」 → 김포 · 이천 (시·군 이름 끝 시/군 뺀 것). 경기가 아니면 None"""
    a = " ".join(str(addr).split())
    m = re.match(r"^경기(?:도)?\s+(\S+?)(시|군)(?:\s|$)", a)
    return m.group(1) if m else None


def count(text):
    rd = csv.DictReader(io.StringIO(text))
    cols = rd.fieldnames or []
    col = next((c for c in ADDR if c in cols), None) or next((c for c in cols if "주소" in c or "소재지" in c), None)
    if not col: raise SystemExit(f"주소 열을 못 찾음 — 열 {cols[:12]}")
    n, gg, by = 0, 0, {}
    for r in rd:
        n += 1
        s = sigungu(r.get(col) or "")
        if s: gg += 1; by[s] = by.get(s, 0) + 1
    return {"rows": n, "gg": gg, "by": dict(sorted(by.items(), key=lambda kv: -kv[1])), "addr_col": col, "cols": len(cols)}


def fetch():
    st, _, html = get(PAGE)
    page = decode(html)
    ids = sorted(set(re.findall(r"FILE_\d{12,}", page)))
    pdpk = sorted(set(re.findall(r"uddi:[0-9a-f-]{36}(?:_\d+)?", page)))
    diag.update({"page_status": st, "atch": ids[:5], "uddi": pdpk[:5], "hints": re.findall(r"[a-zA-Z/]*[Dd]own[a-zA-Z]*\.do[^\"' ]{0,80}", page)[:8]})
    cands = []
    # ① 화면 스크립트의 「다운로드」 — selectFileDataDownload.do 가 atchFileId·fileDetailSn 을 돌려주면 fileDownload.do 로 받는다
    for u in pdpk[:2] or [""]:
        q = {"publicDataPk": PK, "fileDetailSn": "1"}
        if u: q["publicDataDetailPk"] = u
        cands.append(("api", "https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?" + urllib.parse.urlencode(q)))
    # ② 화면에 박힌 파일 id 로 바로
    for a in ids[:3]:
        cands.append(("file", f"https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={a}&fileDetailSn=1"))
    for kind, url in cands:
        try:
            st, hd, body = get(url)
            ct = hd.get("Content-Type", "")
            diag["tried"].append({"url": url[:160], "status": st, "type": ct, "bytes": len(body)})
            if kind == "api" and ("json" in ct or body[:1] in (b"{", b"[")):
                j = json.loads(decode(body))
                diag["tried"][-1]["json_keys"] = list(j.keys())[:12] if isinstance(j, dict) else None
                # 응답 구조 진단(값은 앞부분만 · 개인정보 칸 없음 — 파일 메타)
                diag["tried"][-1]["json_head"] = json.dumps(j, ensure_ascii=False)[:600]
                # 비어 있지 않은 칸만(파일 메타) — 1500자 머리에는 검색 조건 빈칸만 찼다(여섯째 실행 10/20)
                def nonempty(o, pre=""):
                    out = {}
                    if isinstance(o, dict):
                        for k, v in o.items():
                            if isinstance(v, (dict, list)): out.update(nonempty(v, f"{pre}{k}."))
                            elif v not in (None, "", 0, False): out[f"{pre}{k}"] = str(v)[:120]
                    elif isinstance(o, list):
                        for i, v in enumerate(o[:3]): out.update(nonempty(v, f"{pre}{i}."))
                    return out
                diag["tried"][-1]["json_set"] = dict(list(nonempty(j).items())[:80])
                def pick(k):
                    for box in (j, j.get("fileDataRegistVO") or {}, j.get("dataSetFileDetailInfo") or {}):
                        if isinstance(box, dict) and box.get(k): return box.get(k)
                    m = re.search(rf'"{k}"\s*:\s*"?([A-Za-z0-9_]+)', json.dumps(j))
                    return m.group(1) if m else None
                a, sn = pick("atchFileId"), pick("fileDetailSn") or 1
                diag["tried"][-1]["picked"] = [a, sn]
                if a:
                    st2, hd2, body = get(f"https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={a}&fileDetailSn={sn}")
                    diag["tried"].append({"url": f"fileDownload {a}/{sn}", "status": st2, "type": hd2.get("Content-Type", ""), "bytes": len(body)})
                else: continue
            text = decode(body)
            if text.count(",") < 50 or "<html" in text[:500].lower(): continue
            return text
        except Exception as e:  # 다음 길로
            diag["tried"].append({"url": url[:160], "err": str(e)[:160]})
    return None


def main():
    os.makedirs(os.path.dirname(DIAG), exist_ok=True)
    try: text = fetch()
    except Exception as e: text = None; diag["err"] = str(e)[:200]
    if not text:
        json.dump(diag, open(DIAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("::warning::포털 파일을 받지 못했다 — 진단만 남기고 지난 파일을 지킨다"); print(json.dumps(diag, ensure_ascii=False)[:1500]); return 0
    c = count(text)
    diag.update({"ok": True, "rows": c["rows"], "addr_col": c["addr_col"]})
    json.dump(diag, open(DIAG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out = {"_설명": "경기 시·군별 물류창고 등록 개소 — 국토교통부 물류창고업등록정보(공공데이터포털 15083282) 행 단위 목록의 주소 열에서 「경기(도) ○○시/군」을 세었다. 개수만 남긴다(주소·상호·대표자·연락처는 싣지 않는다).",
           "source": "국토교통부 「물류창고업등록정보」(공공데이터포털 15083282 · 이용허락범위 제한 없음)", "fetched": datetime.date.today().isoformat(),
           "rows": c["rows"], "gg_total": c["gg"], "by": c["by"]}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("경기", c["gg"], "곳 /", c["rows"], "행 ·", " · ".join(f"{k} {v}" for k, v in list(c["by"].items())[:10]))
    return 0


def selftest():
    assert sigungu("경기도 김포시 고촌읍 1") == "김포" and sigungu("경기 이천시 마장면") == "이천" and sigungu("경기도 광주시") == "광주"
    assert sigungu("경기도 양평군 양평읍") == "양평" and sigungu("인천광역시 서구") is None and sigungu("서울 강서구") is None
    t = "상호,소재지도로명주소,대표자\nA,경기도 김포시 고촌읍 1,홍\nB,경기도 김포시 양촌읍 2,김\nC,인천광역시 서구 3,이\nD,경기 이천시 마장면 4,박\n"
    c = count(t)
    assert c["rows"] == 4 and c["gg"] == 3 and c["by"] == {"김포": 2, "이천": 1} and "대표자" not in json.dumps(c["by"], ensure_ascii=False)
    print("selftest 3/3 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

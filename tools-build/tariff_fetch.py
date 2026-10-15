"""관세율표 받기(P1 ② · 2026-10-15) — 공공데이터포털 파일 데이터 15051179 「관세청_품목번호별 관세율표」(XLSX · 공공누리 제1유형 출처표시).
1단계(지금): 화면에서 내려받기 번호(atchFileId·fileDetailSn)를 찾아 받고 → 열 이름과 앞 20줄, 세율 구분 값들의 빈도만 data/collected/tariff_head.json 에 적는다.
           열을 모르고 해석기를 짜면 틀린다 — 열을 본 뒤 2단계(스냅샷 data/derived/tariff.json · 자동 채움)를 짠다.
키 불필요(파일 데이터). 세션은 data.go.kr 에 못 닿아 Actions(tariff-probe 워크플로)에서 돈다.
  python tools-build/tariff_fetch.py
"""
import collections, io, json, os, re, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DID = "15051179"
UA = {"User-Agent": "Mozilla/5.0 (sounding build; public data)"}


def fetch(url, binary=False, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        b = r.read(); return b if binary else b.decode("utf-8", "replace")


def build(blob, out):
    """2단계 — 지금 유효한 줄(적용개시일 ≤ 오늘 ≤ 적용만료일)만 HS 2단위(류)별 파일로: data/derived/tariff/<류>.json = {품목번호: {구분: 세율 | "종량"}}.
    종가세(관세율 %)만 계산기에 쓴다 — 단위당세액(종량세)·기준가격이 있는 줄은 "종량" 으로 표시만. 구분 코드별 줄 수는 tariff_codes.json."""
    import openpyxl, datetime
    today = datetime.date.today().strftime("%Y%m%d")
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True)
    ws = wb.worksheets[-1]  # 마지막 시트 = 가장 새 판(2026-10-15 실측: 시트 1.1 · 2.12 — 같은 열)
    rows = ws.iter_rows(values_only=True); head = [str(c) for c in next(rows)]
    ix = {k: head.index(k) for k in ("품목번호", "관세율구분", "관세율", "단위당세액", "기준가격", "적용국가구분", "적용개시일", "적용만료일")}
    by, codes, n_all, n_now = {}, collections.Counter(), 0, 0
    for r in rows:
        n_all += 1
        hs = str(r[ix["품목번호"]] or "").strip(); code = str(r[ix["관세율구분"]] or "").strip()
        if len(hs) != 10 or not code: continue
        a, b = str(r[ix["적용개시일"]] or "0"), str(r[ix["적용만료일"]] or "99999999")
        if not (a <= today <= b): continue
        n_now += 1; codes[code] += 1
        rate = r[ix["관세율"]]
        val = "종량" if (r[ix["단위당세액"]] not in (None, "", 0) or r[ix["기준가격"]] not in (None, "")) else (float(rate) if rate not in (None, "") else None)
        if val is None: continue
        d = by.setdefault(hs[:2], {}).setdefault(hs, {})
        # 같은 품목·같은 구분이 둘이면(기간 겹침 등) 낮은 세율이 아니라 먼저 나온 것을 둔다 — 겹침 수는 따로 센다
        if code in d: out.setdefault("dup", 0); out["dup"] += 1; continue
        d[code] = int(val) if isinstance(val, float) and val.is_integer() else val
    od = os.path.join(ROOT, "data/derived/tariff"); os.makedirs(od, exist_ok=True)
    for ch, m in by.items():
        json.dump(m, open(os.path.join(od, f"{ch}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"source": "관세청_품목번호별 관세율표(공공데이터포털 15051179 · 공공누리 제1유형 출처표시)", "sheet": ws.title, "asof": today,
               "rows_all": n_all, "rows_now": n_now, "hs10": sum(len(m) for m in by.values()), "chapters": sorted(by), "codes": dict(codes.most_common())},
              open(os.path.join(ROOT, "data/derived/tariff_codes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    out["build"] = {"chapters": len(by), "hs10": sum(len(m) for m in by.values()), "codes": len(codes)}
    print("관세율표 스냅샷", out["build"])


def main():
    out = {"data_id": DID, "steps": []}
    h = fetch(f"https://www.data.go.kr/data/{DID}/fileData.do")
    ids = sorted(set(re.findall(r"FILE_\d{12,}", h)))
    sns = sorted(set(re.findall(r"fileDetailSn['\"]?\s*[:=]\s*['\"]?(\d+)", h))) or ["1"]
    uddi = sorted(set(re.findall(r"uddi:[0-9a-f-]{20,}", h)))
    out["uddi"] = uddi
    # 화면에 번호가 없으면(스크립트가 받아 온다) 포털 내려받기 조회를 거친다 — 2026-10-15 1차: 화면에 FILE_ 번호 0
    out["hints"] = sorted(set(re.findall(r"(fn_\w*[Dd]own\w*|selectFileData\w*|fileDownload\.do|downloadFile\w*)", h)))[:12]
    if not ids:
        for ud in uddi[:2]:
            for u in (f"https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?publicDataPk={DID}&publicDataDetailPk={ud}&fileDetailSn=1",
                      f"https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?publicDataDetailPk={ud}"):
                try:
                    t = fetch(u, timeout=40); out["steps"].append({"url": u, "head": t[:300]})
                    ids += re.findall(r"FILE_\d{12,}", t)
                    sns += re.findall(r"fileDetailSn['\"]?\s*[:=]\s*['\"]?(\d+)", t)
                except Exception as e:
                    out["steps"].append({"url": u, "error": str(e)[:160]})
        ids = sorted(set(ids)); sns = sorted(set(sns)) or ["1"]
    out["atchFileId"], out["fileDetailSn"] = ids, sns
    out["title"] = (re.search(r"<title>([^<]*)", h) or [None, None])[1]
    blob = None
    for fid in ids[:3]:
        for sn in sns[:2]:
            u = f"https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={fid}&fileDetailSn={sn}"
            try:
                b = fetch(u, binary=True, timeout=180); out["steps"].append({"url": u, "bytes": len(b), "head": b[:4].hex()})
                if b[:2] == b"PK": blob = b; break
            except Exception as e:
                out["steps"].append({"url": u, "error": str(e)[:160]})
        if blob: break
    if blob and "--build" in sys.argv:
        build(blob, out)
    if blob:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True)
        out["sheets"] = []
        for ws in wb.worksheets[:3]:
            rows = ws.iter_rows(values_only=True)
            head = [str(c) for c in next(rows, [])]
            sample, cnt, n = [], {i: collections.Counter() for i in range(len(head))}, 0
            for r in rows:
                n += 1
                if n <= 20: sample.append([None if c is None else str(c) for c in r])
                for i, c in enumerate(r[:len(head)]):
                    if c is not None and len(cnt[i]) < 400: cnt[i][str(c)[:40]] += 1
            # 값 종류가 적은 열(세율 구분 같은 것)만 빈도를 남긴다
            small = {head[i]: dict(c.most_common(40)) for i, c in cnt.items() if 0 < len(c) <= 60}
            out["sheets"].append({"name": ws.title, "rows": n, "head": head, "sample": sample, "small_columns": small})
        os.makedirs(os.path.join(ROOT, "data/collected"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data/collected/tariff_head.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"ids": ids, "ok": bool(blob), "sheets": [(s["name"], s["rows"], s["head"]) for s in out.get("sheets", [])]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

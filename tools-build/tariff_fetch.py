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

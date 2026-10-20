"""세계은행 Global Shipping Traffic Density(CC BY 4.0) — 서해·동중국해만 잘라 홈 「인천 관문 라이브」의 밀도 빛줄기 격자로.
카탈로그 0037580 의 자원 목록에서 「commercial」·「global」 밀도 zip 을 찾아 받는다(이름을 추측하지 않고 목록에서 고른다).
rasterio 로 zip 안 GeoTIFF 의 창만 읽고(전 세계를 펴지 않는다) 0.025° 로 줄여 로그 눈금 0~255 로 담는다.
결과: data/derived/ship_density.json — {bbox, w, h, step, layer, b64(uint8 행 우선 · 0 = 배 없음), stats, source, period}
  python tools-build/v3/ship_density.py [--local <zip>]
"""
import base64, datetime, json, math, os, sys, tempfile
import numpy as np
from common import ROOT, get, jget, write, say

BBOX = (117.0, 29.0, 131.5, 41.0)  # 서·남·동·북 — 서해·발해·대한해협·동중국해 북부
STEP = 0.025


def find_zip():
    """카탈로그 자원 목록 → 내려받을 주소(상업 선박 우선 · 없으면 전체)."""
    tried = []
    for url in ["https://datacatalogapi.worldbank.org/ddhxext/DatasetView?dataset_unique_id=0037580",
                "https://datacatalogapi.worldbank.org/ddhxext/ResourceView?dataset_unique_id=0037580"]:
        st, d = jget(url, timeout=60)
        tried.append({"url": url, "status": st})
        if not d: continue
        txt = json.dumps(d)
        import re
        urls = sorted(set(re.findall(r'https://[^"\s]+?\.zip', txt)))
        tried[-1]["zips"] = urls[:12]
        for want in ("commercial", "global"):
            for u in urls:
                if want in u.lower(): return u, tried, d
    # 보조 후보 — 공개 재현 코드(PyPSA-Eur)가 쓰는 주소
    for u in ["https://datacatalogfiles.worldbank.org/ddh-published/0037580/DR0045406/shipdensity_global.zip"]:
        st, _ = get(u, timeout=60, binary=True, headers={"Range": "bytes=0-1023"})
        tried.append({"url": u, "status": st})
        if st in (200, 206): return u, tried, None
    return None, tried, None


def main():
    local = sys.argv[sys.argv.index("--local") + 1] if "--local" in sys.argv else None
    meta = {"fetched": datetime.date.today().isoformat()}
    if local: zp, url = local, "local"
    else:
        url, tried, d = find_zip()
        meta["catalog"] = tried
        if d:
            lic = json.dumps(d, ensure_ascii=False)
            import re
            m = re.search(r'"(?:license|License)[^"]*"\s*:\s*"([^"]{0,120})"', lic)
            meta["license_field"] = m.group(1) if m else None
        if not url:
            write("data/collected/v3/ship_density_probe.json", {**meta, "error": "zip 을 못 찾았다"}); return 1
        say("받는다", url)
        # 큰 파일 — 메모리에 올리지 않고 디스크로 바로(curl · 재시도)
        import subprocess
        zp = os.path.join(tempfile.mkdtemp(), "d.zip")
        r = subprocess.run(["curl", "-sSL", "--retry", "3", "-m", "1800", "-o", zp, "-w", "%{http_code} %{size_download}", url], capture_output=True, text=True)
        meta["download"] = r.stdout.strip()
        say("받음", r.stdout.strip(), r.stderr.strip()[:200])
        if not r.stdout.startswith("200"): write("data/collected/v3/ship_density_probe.json", {**meta, "url": url}); return 1
    import zipfile, rasterio
    from rasterio.windows import from_bounds
    names = [n for n in zipfile.ZipFile(zp).namelist() if n.lower().endswith(".tif")]
    say("zip 안", names)
    tif = names[0]
    with rasterio.open(f"/vsizip/{zp}/{tif}") as r:
        win = from_bounds(*BBOX, transform=r.transform).round_offsets().round_lengths()
        a = r.read(1, window=win, masked=True).filled(0).astype("float64")
        res = abs(r.transform.a)
        meta.update({"tif": tif, "crs": str(r.crs), "res_deg": res, "nodata": r.nodata})
    k = max(1, round(STEP / res))
    H, W = a.shape[0] // k, a.shape[1] // k
    a = a[: H * k, : W * k].reshape(H, k, W, k).sum(axis=(1, 3))  # 칸 안 합(밀도는 칸 크기에 비례)
    nz = a[a > 0]
    lo, hi = (np.percentile(nz, 5), np.percentile(nz, 99.7)) if nz.size else (1, 1)
    q = np.where(a > 0, np.clip(1 + 254 * (np.log1p(a) - math.log1p(lo)) / max(1e-9, math.log1p(hi) - math.log1p(lo)), 1, 255), 0).astype("uint8")
    out = {"_설명": "세계은행 Global Shipping Traffic Density 를 서해 범위로 잘라 0.025° 칸 합 → 로그 눈금 0~255(0 = 배 없음). 2015-01~2021-02 누적 — 「지금」의 배가 아니다.",
           "source": "World Bank — Global Shipping Traffic Density(datacatalog.worldbank.org 0037580) · CC BY 4.0", "url": url,
           "period": "2015-01~2021-02(AIS 누적)", "layer": tif, "bbox": BBOX, "step": STEP, "w": W, "h": H,
           "stats": {"cells_nonzero": int((q > 0).sum()), "p5": float(lo), "p99_7": float(hi)},
           "b64": base64.b64encode(q.tobytes()).decode()}
    # 사고 127 교훈: 배가 있는 칸이 지난 파일의 절반 아래로 줄면(덜 받은 래스터) 덮어쓰지 않는다
    prev = os.path.join(ROOT, "data/derived/ship_density.json")
    if os.path.exists(prev) and out["stats"]["cells_nonzero"] < 0.5 * json.load(open(prev, encoding="utf-8"))["stats"]["cells_nonzero"]:
        say("배 있는 칸이 지난 파일의 절반 아래 — 지난 파일을 지킨다", out["stats"]["cells_nonzero"]); return 1
    write("data/derived/ship_density.json", out)
    write("data/collected/v3/ship_density_probe.json", {**meta, "url": url, "shape": [H, W], "nonzero": out["stats"]["cells_nonzero"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())

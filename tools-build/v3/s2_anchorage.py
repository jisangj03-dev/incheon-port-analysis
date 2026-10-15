"""위성으로 본 인천 묘박지(2차 · 2026-10-14) — Copernicus Sentinel-2 L2A(AWS 공개 · 계정 불필요)에서 인천 앞바다 창만 읽는다.
달마다 구름이 가장 적은 장면 하나 → 실제색(TCI) JPEG 한 장 + 「위성에 보인 배」 어림 수(물 위 근적외선 밝은 덩어리 · 3~400 화소(10m)).
배 수는 그 순간 사진에 찍힌 밝은 물체 수다 — 부두에 붙은 배·작은 배·구름 아래 배는 빠지고, 부표·작은 섬이 섞일 수 있다(지면에 적는다).
결과: data/derived/s2_anchorage.json · astro/public/media/s2/<날짜>.jpg   (표기: 「Contains modified Copernicus Sentinel data <연도>」)
  python tools-build/v3/s2_anchorage.py [--months 12]
"""
import datetime, json, os, re, sys, urllib.request
import numpy as np
from common import ROOT, write, say

BUCKET = "https://sentinel-cogs.s3.us-west-2.amazonaws.com"
TILE = "52/S/BG"
AOI = (126.30, 37.20, 126.62, 37.45)  # 서·남·동·북 — 인천항 남쪽 접근 수로 · 팔미도 · 묘박지(그림 창)
COUNT = (126.30, 37.27, 126.56, 37.41)  # 배를 세는 상자 — 인천대교·항내·영흥도 갯벌 양식장을 뺀 먼바다(다리·부두·양식장이 배로 잡혔다 · 10/14 확인)
OUT_DIR = os.path.join(ROOT, "astro/public/media/s2")


def ls(prefix):
    xml = urllib.request.urlopen(f"{BUCKET}/?list-type=2&prefix={prefix}&delimiter=/", timeout=60).read().decode()
    return re.findall(r"<Prefix>([^<]*)</Prefix>", xml)[1:]


def scenes(year, month):
    return [p for p in ls(f"sentinel-s2-l2a-cogs/{TILE}/{year}/{month}/")]


def meta(prefix):
    name = prefix.rstrip("/").split("/")[-1]
    return json.loads(urllib.request.urlopen(f"{BUCKET}/{prefix}{name}.json", timeout=60).read())


def window(prefix, band, out_shape=None):
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    with rasterio.open(f"/vsicurl/{BUCKET}/{prefix}{band}.tif") as r:
        b = transform_bounds("EPSG:4326", r.crs, *AOI)
        w = from_bounds(*b, transform=r.transform).round_offsets().round_lengths()
        kw = {"out_shape": (r.count, *out_shape)} if out_shape else {}
        return r.read(window=w, boundless=False, **kw), r


def ships(prefix, shape):
    """먼바다 위 근적외선(B08) 밝은 덩어리 수 — 10m 해상도 3~300 화소.
    큰 땅(SCL 땅 덩어리 400 화소 이상)에서 250m(25 화소) 안 · 자료 없는 가장자리 100m 안 · 구름은 뺀다(해안선·부두·섬 가장자리가 배로 잡히지 않게).
    밝기 문턱 = 1500 이고 주변(15 화소 중앙값)보다 600 넘게 밝을 것."""
    from scipy import ndimage
    scl, _ = window(prefix, "SCL", shape)
    nir, _ = window(prefix, "B08", shape)
    S0, n = scl[0], nir[0].astype("float32")
    cloud = np.isin(S0, [3, 8, 9, 10])
    land = ~np.isin(S0, [0, 6, 3, 8, 9, 10])
    lab0, k0 = ndimage.label(land)
    big = np.isin(lab0, np.where(np.array(ndimage.sum(land, lab0, range(1, k0 + 1))) >= 400)[0] + 1) if k0 else land
    sea = ~ndimage.binary_dilation(big, iterations=40) & ~ndimage.binary_dilation(S0 == 0, iterations=10) & ~cloud
    # 세는 상자 밖은 뺀다(창 화소 → 경위도 선형 근사 · 창이 작아 충분)
    H, W = S0.shape
    yy, xx = np.mgrid[0:H, 0:W]
    lon = AOI[0] + (xx + 0.5) / W * (AOI[2] - AOI[0]); lat = AOI[3] - (yy + 0.5) / H * (AOI[3] - AOI[1])
    sea &= (lon >= COUNT[0]) & (lon <= COUNT[2]) & (lat >= COUNT[1]) & (lat <= COUNT[3])
    bg = ndimage.median_filter(n, size=15)
    bright = (n > 1500) & ((n - bg) > 600) & sea
    lab, k = ndimage.label(bright)
    sizes = ndimage.sum(bright, lab, range(1, k + 1)) if k else []
    objs = ndimage.find_objects(lab) if k else []
    cnt = 0
    for i, sl in enumerate(objs):
        m = lab[sl] == i + 1; sz = int(m.sum())
        if not (3 <= sz <= 300): continue
        if max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) > 45: continue  # 450m 넘게 긴 것(다리·방파제) 빼기
        if np.bincount(S0[sl][m], minlength=12)[[4, 5]].sum() > sz / 2: continue  # 대부분 식생·맨땅이면 섬·갯벌
        cnt += 1
    valid = S0 != 0
    return cnt, float((cloud & valid).sum() / max(1, valid.sum())), float(valid.mean())


def aoi_quality(prefix):
    """AOI 안 자료 있는 몫 · 그 안 구름 몫(SCL 20m 창)."""
    scl, _ = window(prefix, "SCL")
    S0 = scl[0]; valid = S0 != 0
    return float(valid.mean()), float((np.isin(S0, [3, 8, 9, 10]) & valid).sum() / max(1, valid.sum()))


def main():
    months = int(sys.argv[sys.argv.index("--months") + 1]) if "--months" in sys.argv else 12
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    today = datetime.date.today().replace(day=1)
    picks = []
    for k in range(months):
        y, m = (today.year, today.month - k) if today.month - k > 0 else (today.year - 1, today.month - k + 12)
        try: cands = scenes(y, m)
        except Exception as e: say("목록 실패", y, m, e); continue
        # 타일 구름 적은 순으로 다섯까지 AOI 를 직접 재서 — 자료 95% 이상 · 구름 10% 이하인 첫 장면(없으면 점수 가장 좋은 것)
        cc = []
        for p in cands:
            try: cc.append((meta(p)["properties"].get("eo:cloud_cover", 100), p))
            except Exception: continue
        best = None
        for c, p in sorted(cc)[:5]:
            try: v, cl = aoi_quality(p)
            except Exception: continue
            score = (1 - v) * 2 + cl
            if best is None or score < best[3]: best = (p, c, v, score, cl)
            if v >= 0.95 and cl <= 0.03: break
        if best and best[2] >= 0.6: picks.append((y, m, best[0], best[1])); say(y, m, "후보", len(cands), "고름", best[0].split("/")[-2], "자료", round(best[2], 2), "구름", round(best[4], 2))
    os.makedirs(OUT_DIR, exist_ok=True)
    out = []
    from PIL import Image
    for y, m, p, cc in sorted(picks):
        try:
            tci, r = window(p, "TCI")
            h, w = tci.shape[1:]
            img = Image.fromarray(np.transpose(tci[:3], (1, 2, 0)))
            scale = 1400 / w
            img = img.resize((1400, round(h * scale)), Image.LANCZOS)
            date = p.rstrip("/").split("_")[2]
            fn = f"{date}.jpg"; img.save(os.path.join(OUT_DIR, fn), quality=78, optimize=True, progressive=True)
            cnt, cloud, valid = ships(p, (h, w))
            out.append({"date": f"{date[:4]}-{date[4:6]}-{date[6:]}", "scene": p.rstrip("/").split("/")[-1], "tile_cloud_pct": round(cc, 1),
                        "aoi_cloud_pct": round(100 * cloud, 1), "aoi_valid_pct": round(100 * valid, 1), "ships_seen": cnt, "low_confidence": cloud > 0.03, "img": f"/media/s2/{fn}", "w": img.width, "h": img.height})
            say(date, "배", cnt, "구름", round(100 * cloud, 1), "자료", round(100 * valid, 1))
        except Exception as e:
            say("장면 실패", p, str(e)[:160])
    write("data/derived/s2_anchorage.json", {
        "_설명": "인천 앞바다 창(경위도 상자) — 달마다 가장 맑은 Sentinel-2 L2A 장면의 실제색 · 물 위 근적외선 밝은 덩어리 수(위성에 보인 배 어림).",
        "source": "Copernicus Sentinel-2 L2A(AWS Open Data · sentinel-cogs) — Contains modified Copernicus Sentinel data", "tile": TILE.replace("/", ""), "aoi": AOI,
        "made": datetime.date.today().isoformat(), "count_box": COUNT, "method": "세는 상자(먼바다 · 인천대교·항내·갯벌 양식장 제외) 안에서 큰 땅 400m · 자료 가장자리 100m · 구름을 빼고, B08 > 1500 이고 주변 중앙값보다 600 넘게 밝은 덩어리 중 3~300 화소(10m) · 450m 넘게 긴 것과 식생·맨땅이 대부분인 것은 뺀다",
        "frames": out})
    return 0


if __name__ == "__main__":
    sys.exit(main())

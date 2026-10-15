"""위성 묘박지 SAR(P1 ④ · 2026-10-15) — Copernicus Sentinel-1(레이더 · 구름·밤과 무관)로 인천 앞바다 묘박지의 배를 센다.
원천: Microsoft Planetary Computer STAC `sentinel-1-rtc`(지형 보정 후방산란 · UTM 격자) — 익명 서명(키·계정 불필요).
검출: VV 후방산란(선형) — 물은 어둡고 배(금속)는 밝다. 상자(COUNT) 안에서 국소 배경(중앙값 31화소)보다 KDB 이상 밝고 배경이 물(−15dB 미만)인
      화소를 묶어(연결 덩어리) 3~400 화소(10m 격자 기준 · 배 길이 약 20~300m)만 배 하나로 센다 — 부표·작은 섬·양식장이 섞일 수 있다(지면에 적는다).
결과: data/derived/s1_anchorage.json — 날짜별 척수 · 배 자리(경위도 · 소수 넷째 자리) · 장면 이름. 레이더 영상 자체는 싣지 않는다(바탕은 Sentinel-2 실사).
표기: 「Contains modified Copernicus Sentinel data <연도>」 · 처리 = Microsoft Planetary Computer.
  python tools-build/s1_anchorage.py [--months 12] [--selftest]
"""
import datetime, json, math, os, sys
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/s1_anchorage.json")
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
COUNT = (126.30, 37.27, 126.56, 37.41)  # 배를 세는 상자 — s2_anchorage.py 와 같은 상자(인천대교·항내·갯벌 양식장 제외)
KDB = 7.0        # 배경보다 이만큼(dB) 밝으면 후보
WATER_DB = -15.0  # 배경이 이보다 어두워야 물
MIN_PX, MAX_PX = 3, 400
ABS_DB = None    # 배 화소의 절대 밝기 하한(dB) — 진단 뒤 정한다
DIAG = os.environ.get("S1_DIAG") == "1"
GRID = [(k, a) for k in (7, 10, 13) for a in (-14, -8, -4)]  # (배경 대비 dB, 절대 dB) — 2026-10-15 첫 실행이 장면당 14~534척(얼룩 오검출 의심)이라 기준을 잰다
MAX_SCENES = 24  # 한 실행 상한(달 2장 꼴) — 2026-10-15 첫 실행이 40장을 30분 안에 못 읽었다
TIME_BUDGET = 1300  # 초 — 넘으면 거기까지 쓰고 끝낸다(중간 저장)


def detect(vv, transform_xy, kdb=KDB, water_db=WATER_DB, abs_db=None, grid=None):
    """vv = 선형 후방산란 2차원 배열(nan = 자료 없음) → 배 자리 [(x, y)](격자 좌표 → transform_xy 로 바꾼 값)."""
    from scipy import ndimage
    global grid_out
    grid_out = {}
    v = np.where(np.isfinite(vv) & (vv > 0), vv, np.nan)
    db = 10 * np.log10(np.where(np.isfinite(v), v, 1e-6))
    bg = ndimage.median_filter(np.where(np.isfinite(v), db, -30), size=31)
    if grid is not None:  # 진단 — 기준값 여러 벌로 덩어리 수만 센다(자리 없이)
        for k, a in grid:
            c = np.isfinite(v) & (db - bg >= k) & (bg < water_db) & (db >= a)
            lb, nn = ndimage.label(c)
            if nn:
                sz = ndimage.sum(c, lb, index=range(1, nn + 1)); nn = int(((sz >= MIN_PX) & (sz <= MAX_PX)).sum())
            grid_out[f"{k}|{a}"] = nn
    cand = np.isfinite(v) & (db - bg >= kdb) & (bg < water_db) & ((db >= abs_db) if abs_db is not None else True)
    lab, n = ndimage.label(cand)
    out = []
    if n:
        sizes = ndimage.sum(cand, lab, index=range(1, n + 1))
        cms = ndimage.center_of_mass(cand, lab, index=range(1, n + 1))
        for s, (r, c) in zip(sizes, cms):
            if MIN_PX <= s <= MAX_PX: out.append(transform_xy(c, r))
    return out


def save(frames, end, prev=None):
    """중간 저장 — 시간 한도에 끊겨도 읽은 데까지 남는다. 지난 파일의 장면 중 이번에 안 읽은 것도 그대로 둔다(사고 127 · 줄지 않게)."""
    have = {f["scene"] for f in frames}
    frames = frames + [f for k, f in (prev or {}).items() if k not in have]
    out = {"_설명": "Sentinel-1 레이더(VV)로 묘박지 상자 안 밝은 덩어리를 센 것 — 구름·밤과 무관. 부표·작은 섬·양식장이 섞일 수 있고, 붙어 있는 배는 하나로 셀 수 있다.",
           "source": "Copernicus Sentinel-1 RTC · Microsoft Planetary Computer(sentinel-1-rtc)", "credit": f"Contains modified Copernicus Sentinel data {end.year - 1}–{end.year}",
           "count_box": COUNT, "method": {"kdb": KDB, "water_db": WATER_DB, "min_px": MIN_PX, "max_px": MAX_PX, "median_px": 31},
           "made": end.isoformat(), "frames": sorted(frames, key=lambda f: f["date"])}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def main():
    import pystac_client, planetary_computer, rasterio
    from rasterio.warp import transform_bounds, transform as wtransform
    from rasterio.windows import from_bounds
    months = int(sys.argv[sys.argv.index("--months") + 1]) if "--months" in sys.argv else 12
    end = datetime.date.today(); start = (end.replace(day=1) - datetime.timedelta(days=31 * (months - 1))).replace(day=1)
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    items = list(cat.search(collections=["sentinel-1-rtc"], bbox=COUNT, datetime=f"{start}/{end}").items())
    items.sort(key=lambda it: it.datetime)
    print("장면", len(items), start, "~", end)
    frames, prev = [], {}
    if os.path.exists(OUT):
        for f in json.load(open(OUT, encoding="utf-8")).get("frames", []): prev[f["scene"]] = f
    import time
    t0 = time.time()
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR"); os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")
    # 달마다 고르게 — 같은 달이면 앞뒤 둘까지(날짜 그래프가 한쪽으로 몰리지 않게)
    by_m = {}
    for it in items: by_m.setdefault(it.datetime.strftime("%Y-%m"), []).append(it)
    pick = [x for m in sorted(by_m) for x in (by_m[m][:1] + by_m[m][-1:] if len(by_m[m]) > 1 else by_m[m])][-MAX_SCENES:]
    if DIAG: pick = pick[::2][:12]; prev = {}  # 진단 = 달 하나에 한 장 · 지난 결과 안 씀
    for it in pick:
        if time.time() - t0 > TIME_BUDGET: print("시간 상한 — 여기까지"); break
        if it.id in prev: frames.append(prev[it.id]); continue
        a = it.assets.get("vv")
        if not a: continue
        try:
            with rasterio.open(a.href) as r:
                b = transform_bounds("EPSG:4326", r.crs, *COUNT)
                w = from_bounds(*b, transform=r.transform).round_offsets().round_lengths()
                vv = r.read(1, window=w, boundless=True, fill_value=np.nan).astype("float32")
                T = r.window_transform(w); crs = r.crs
            valid = float(np.isfinite(vv).mean() * 100)
            if valid < 60: print(it.id, "덮인 몫", round(valid), "% — 뺀다"); continue
            def xy(c, rr):
                X, Y = T * (c + 0.5, rr + 0.5)
                lo, la = wtransform(crs, "EPSG:4326", [X], [Y]); return [round(lo[0], 4), round(la[0], 4)]
            ships = detect(vv, xy, abs_db=ABS_DB, grid=GRID if DIAG else None)
            frames.append({"date": it.datetime.date().isoformat(), "scene": it.id, "orbit": it.properties.get("sat:orbit_state"), "valid_pct": round(valid, 1), "n": len(ships), "ships": ships, **({"grid": dict(grid_out)} if DIAG else {})})
            print(it.id, it.datetime.date(), "배", len(ships), f"{time.time() - t0:.0f}초", flush=True)
            save(frames, end, prev) if not DIAG else json.dump(frames, open(os.path.join(ROOT, "data/collected/s1_diag.json"), "w", encoding="utf-8"), ensure_ascii=False)
        except Exception as e:
            print(it.id, "읽기 실패", type(e).__name__, str(e)[:120])
    if DIAG: print("진단 끝 →", "data/collected/s1_diag.json"); return 0
    save(frames, end, prev)
    frames.sort(key=lambda f: f["date"])
    print("프레임", len(frames), "→", OUT); return 0 if frames else 1


def selftest():
    rng = np.random.default_rng(0)
    vv = (rng.random((120, 120)) * 0.004 + 0.004).astype("float32")  # 물 ≈ −22 dB
    vv[30:33, 40:43] = 0.5; vv[80:84, 90:96] = 0.8  # 배 둘
    vv[0:10, 0:120] = 0.3                            # 땅(넓고 밝다) — 배경이 밝아 빠진다
    s = detect(vv, lambda c, r: (round(c), round(r)))
    assert len(s) == 2, s
    print("selftest 1/1 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

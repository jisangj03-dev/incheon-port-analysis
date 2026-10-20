"""레이더(Sentinel-1) 배 자리에서 땅 위·해안선 가까이 찍힌 것을 뺀다(2026-10-20 · docs/품질기준.md Q2).

공개 뒤 실측: 22장면 1,339점 가운데 288점(21.5%)이 OSM 땅 다각형 안 — 섬·방파제·부두의 밝은 반사를 배로 셌다.
레이더 검출(tools-build/s1_anchorage.py)은 땅을 모른다(사진 쪽 Sentinel-2 어림은 이미 큰 땅 400m 를 뺀다).

규칙: OSM 땅(data/derived/land_incheon.geojson · 단순화 0.0012° ≈ 130m) 안이거나 땅 경계에서 BUF_M 안이면 뺀다.
원래 점은 ships_raw · n_raw 로 그대로 둔다(되돌릴 수 있게) — 다시 돌려도 ships_raw 에서 다시 거른다(멱등).

  python tools-build/anchorage_landmask.py [--selftest]
"""
import json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S1 = os.path.join(ROOT, "data/derived/s1_anchorage.json")
LAND = os.path.join(ROOT, "data/derived/land_incheon.geojson")
BUF_M = 150  # 다각형 단순화(≈130m)보다 조금 넓게 — 해안에 붙은 부두·방파제 반사


def inside(x, y, ring):
    c = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def seg_dist_m(x, y, a, b):
    """점 (x,y) 와 선분 a-b 사이 거리(m) — 위도 cos 로 경도를 줄인 평면 근사(수 km 범위)."""
    k = math.cos(math.radians(y))
    px, py = x * k, y
    ax, ay, bx, by = a[0] * k, a[1], b[0] * k, b[1]
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)) * 111_320


def on_land(x, y, rings, buf=BUF_M):
    d = buf / 111_320
    for r, bb in rings:
        if x < bb[0] - d * 2 or x > bb[2] + d * 2 or y < bb[1] - d or y > bb[3] + d:
            continue
        if inside(x, y, r):
            return True
        for i in range(len(r)):
            if seg_dist_m(x, y, r[i], r[(i + 1) % len(r)]) < buf:
                return True
    return False


def load_rings():
    L = json.load(open(LAND, encoding="utf-8"))
    out = []
    for f in L["features"]:
        if f["properties"].get("kind") != "land":
            continue
        r = f["geometry"]["coordinates"][0]
        xs, ys = [p[0] for p in r], [p[1] for p in r]
        out.append((r, (min(xs), min(ys), max(xs), max(ys))))
    return out


def run():
    rings = load_rings()
    S = json.load(open(S1, encoding="utf-8"))
    for f in S["frames"]:
        raw = f.get("ships_raw", f["ships"])
        f["ships_raw"], f["n_raw"] = raw, len(raw)
        f["ships"] = [p for p in raw if not on_land(p[0], p[1], rings)]
        f["n"] = len(f["ships"])
    S["landmask"] = {"rule": f"OSM 땅 다각형 안 또는 땅 경계 {BUF_M}m 안의 점은 뺀다(섬·방파제·부두 반사)", "script": "tools-build/anchorage_landmask.py",
                     "removed": sum(f["n_raw"] - f["n"] for f in S["frames"]), "of": sum(f["n_raw"] for f in S["frames"])}
    json.dump(S, open(S1, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"레이더 점 {S['landmask']['of']} 가운데 땅·해안 {S['landmask']['removed']} 뺌")


def selftest():
    sq = [[0, 0], [1, 0], [1, 1], [0, 1]]
    rings = [(sq, (0, 0, 1, 1))]
    ok = [inside(0.5, 0.5, sq), not inside(1.5, 0.5, sq), on_land(0.5, 0.5, rings), on_land(1.0005, 0.5, rings), not on_land(1.01, 0.5, rings)]
    print(f"selftest {sum(ok)}/{len(ok)}")
    return all(ok)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    run()

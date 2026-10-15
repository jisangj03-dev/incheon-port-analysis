"""홈 해도의 육지 실루엣 — 저장소 내장 PMTiles(OpenStreetMap · Protomaps)에서 땅 면과 큰 길만 뽑아 가볍게 만든다(2026-10-14).

Actions(bathy.yml)에서 돈다(타일은 Actions 캐시에만 있다). 결과 data/derived/land_incheon.geojson:
  · kind=land  — earth 층 면(채우기 전용 · 해안선은 면의 가장자리)
  · kind=road  — roads 층 highway(고속도로) 선
OpenStreetMap 에서 나온 데이터베이스라 ODbL 1.0 — 파일 머리와 지면 캡션에 출처를 적는다.
  python tools-build/roads.py [--selftest]
"""
import gzip, json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 홈 실루엣은 서울까지 닿아야 해서 배포 타일(동경 126.85°까지)이 아니라 Actions 가 /tmp 에 따로 받는 작은 타일(z10 이하 · 배포 안 함)을 읽는다
TILES = os.environ.get("HOME_TILES") or os.path.join(ROOT, "astro/public/tiles/incheon.pmtiles")
OUT = os.path.join(ROOT, "data/derived/land_incheon.geojson")
BBOX = (126.30, 37.20, 127.10, 37.72)  # 서·남·동·북 — 홈 해도(신항~서울)
Z = 10
TOL = 0.0012  # 단순화 허용치(도 · 약 120m) — 실루엣이라 이 정도면 된다


def lon2x(lon, z): return (lon + 180) / 360 * 2 ** z
def lat2y(lat, z): r = math.radians(lat); return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2 * 2 ** z
def x2lon(x, z): return x / 2 ** z * 360 - 180
def y2lat(y, z): n = math.pi - 2 * math.pi * y / 2 ** z; return math.degrees(math.atan(math.sinh(n)))


def dp(pts, tol):
    """Douglas–Peucker(반복형)."""
    if len(pts) < 3:
        return pts
    if pts[0] == pts[-1] and len(pts) > 3:
        # 닫힌 고리는 시작점과 끝점이 같아 기준선 길이가 0 — 그대로 두면 고리 전체가 점 둘로 무너진다(2026-10-14 실측).
        # 시작점에서 가장 먼 점에서 둘로 잘라 따로 줄인다.
        k = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
        return dp(pts[:k + 1], tol) + dp(pts[k:], tol)[1:]
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-12
        best, bi = -1, -1
        for i in range(a + 1, b):
            d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
            if d > best: best, bi = d, i
        if best > tol:
            keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def to_lonlat(tx, ty, px, py, extent):
    # mapbox_vector_tile.decode 기본값은 y 가 위로(아래가 0) — 타일 좌표로 되돌린다
    return [round(x2lon(tx + px / extent, Z), 5), round(y2lat(ty + 1 - py / extent, Z), 5)]


def rings(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Polygon": return c
    if t == "MultiPolygon": return [r for p in c for r in p]
    if t == "LineString": return [c]
    if t == "MultiLineString": return c
    return []


def main():
    sys.path.insert(0, os.environ.get("PYLIB", ""))
    from pmtiles.reader import Reader, MmapSource
    import mapbox_vector_tile as mvt
    if not os.path.exists(TILES):
        print("타일 없음 — 육지 실루엣을 만들지 않는다"); return 0
    feats = []
    with open(TILES, "rb") as f:
        r = Reader(MmapSource(f))
        x0, x1 = int(lon2x(BBOX[0], Z)), int(lon2x(BBOX[2], Z))
        y0, y1 = int(lat2y(BBOX[3], Z)), int(lat2y(BBOX[1], Z))
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                raw = r.get(Z, tx, ty)
                if not raw: continue
                try: raw = gzip.decompress(raw)
                except OSError: pass
                d = mvt.decode(raw)
                for name in ("earth", "roads"):
                    lay = d.get(name)
                    if not lay: continue
                    ext = lay.get("extent", 4096)
                    for ft in lay["features"]:
                        props = ft.get("properties", {})
                        if name == "roads" and props.get("kind") != "highway": continue  # 고속도로만 — 실루엣
                        for ring in rings(ft["geometry"]):
                            pts = dp([to_lonlat(tx, ty, p[0], p[1], ext) for p in ring], TOL)
                            if len(pts) < 2: continue
                            kind = "land" if name == "earth" else "road"
                            g = {"type": "Polygon", "coordinates": [pts]} if kind == "land" else {"type": "LineString", "coordinates": pts}
                            feats.append({"type": "Feature", "properties": {"kind": kind, "class": props.get("kind", "")}, "geometry": g})
    gj = {"type": "FeatureCollection", "source": "OpenStreetMap 기여자 · Protomaps(저장소 내장 PMTiles)", "license": "ODbL 1.0 (© OpenStreetMap contributors)",
          "zoom": Z, "simplify_deg": TOL, "features": feats}
    json.dump(gj, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"land": sum(f["properties"]["kind"] == "land" for f in feats), "road": sum(f["properties"]["kind"] == "road" for f in feats), "bytes": os.path.getsize(OUT)}))
    return 0


def selftest():
    s = dp([[0, 0], [1, 0.0001], [2, 0], [3, 5], [4, 0]], 0.01)
    assert s[0] == [0, 0] and s[-1] == [4, 0] and [1, 0.0001] not in s and [3, 5] in s, s
    lon, lat = to_lonlat(int(lon2x(126.5, Z)), int(lat2y(37.4, Z)), 0, 4096, 4096)
    assert abs(lon - x2lon(int(lon2x(126.5, Z)), Z)) < 1e-5 and 37.3 < lat < 37.5, (lon, lat)
    ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    assert len(dp(ring, 0.01)) == 5, dp(ring, 0.01)
    print("selftest 3/3 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

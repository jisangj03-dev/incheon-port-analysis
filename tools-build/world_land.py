"""홈 「살아 있는 지도」의 먼 바탕 — Natural Earth 1:50m 땅 면을 동아시아·태평양 범위로 잘라 가볍게 만든다(2026-10-14).

원천: world-atlas 2.0.2(npm · ISC · Natural Earth 4.1.0 퍼블릭 도메인을 TopoJSON 으로 다시 묶은 것). 버전과 묶음 해시를 고정한다.
  python tools-build/world_land.py [<world-atlas 풀어 둔 폴더>] [--selftest]
폴더를 안 주면 npm pack 으로 고정판을 받아 푼다(받은 묶음의 SHA-256 이 아래 값과 다르면 멈춘다).
결과 data/derived/world_land.json — rings: 고리마다 [경도, 위도, 경도, 위도, …](소수 둘째 자리) · 동경 180° 너머(미주)는 +360 으로 이어 붙인다.
면만 쓴다(채우기). 잘린 가장자리는 선으로 그리지 않는다 — 잘린 자리가 해안선처럼 보이지 않게.
"""
import hashlib, json, os, subprocess, sys, tempfile, tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/world_land.json")
PKG, VER = "world-atlas", "2.0.2"
SHA = "032e7765f2ce00edaeafec23ff22bc3b77e42987c257da944cc585b452c05b97"
REGION = (-20.0, -50.0, 262.0, 82.0)  # 서·남·동·북(동은 360 넘어 미주 서해안까지)
TOL = 0.05  # 도 — 줄이기 허용 오차


def decode(topo, name="land"):
    """TopoJSON → 고리 목록(경위도). 양자화·델타 부호화를 푼다."""
    sx, sy = topo["transform"]["scale"]; tx, ty = topo["transform"]["translate"]
    arcs = []
    for a in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in a:
            x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)
    def ring(idx):
        out = []
        for i in idx:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out
    rings = []
    for g in topo["objects"][name]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for p in polys:
            rings.append(ring(p[0]))  # 바깥 고리만(호수 구멍은 이 축척에서 안 보인다)
    return rings


def shift(r):
    """미주(서경)는 +360 — 태평양 너머로 이어 보이게."""
    if max(x for x, _ in r) < -60: return [(x + 360, y) for x, y in r]
    return r


def clip(r, box):
    """사각형 자르기(서덜랜드–호지먼) — 채우기용이라 잘린 변은 그냥 사각 테두리를 따른다."""
    x0, y0, x1, y1 = box
    def cut(pts, inside, inter):
        out = []
        for i, p in enumerate(pts):
            q = pts[i - 1]
            if inside(p):
                if not inside(q): out.append(inter(q, p))
                out.append(p)
            elif inside(q): out.append(inter(q, p))
        return out
    def ix(xc):
        return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))
    def iy(yc):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (yc - a[1]) / (b[1] - a[1]), yc)
    for inside, inter in ((lambda p: p[0] >= x0, ix(x0)), (lambda p: p[0] <= x1, ix(x1)), (lambda p: p[1] >= y0, iy(y0)), (lambda p: p[1] <= y1, iy(y1))):
        r = cut(r, inside, inter)
        if not r: return []
    return r


def simplify(pts, tol):
    """더글러스–포커(반복형). 닫힌 고리는 처음 점에서 가장 먼 점으로 둘로 갈라 줄인다(처음=끝이면 기준선이 0 길이라 다 지워졌다)."""
    if len(pts) < 4: return pts
    if pts[0] == pts[-1]:
        m = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
        return simplify(pts[: m + 1], tol)[:-1] + simplify(pts[m:], tol)
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay; L = (dx * dx + dy * dy) ** 0.5 or 1e-12
        best, bi = 0, -1
        for i in range(a + 1, b):
            d = abs((pts[i][0] - ax) * dy - (pts[i][1] - ay) * dx) / L
            if d > best: best, bi = d, i
        if best > tol: keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


def build(pkgdir):
    topo = json.load(open(os.path.join(pkgdir, "land-50m.json"), encoding="utf-8"))
    rings = []
    for r in decode(topo):
        r = clip(shift(r), REGION)
        if len(r) < 4: continue
        r = simplify(r, TOL)
        xs = [p[0] for p in r]; ys = [p[1] for p in r]
        if len(r) < 4 or (max(xs) - min(xs)) * (max(ys) - min(ys)) < 0.02: continue  # 아주 작은 섬은 이 축척에서 점이다
        rings.append([v for p in r for v in (round(p[0], 2), round(p[1], 2))])
    return rings


def fetch():
    d = tempfile.mkdtemp()
    subprocess.run(["npm", "pack", f"{PKG}@{VER}", "--silent"], cwd=d, check=True, capture_output=True)
    tgz = os.path.join(d, f"{PKG}-{VER}.tgz")
    h = hashlib.sha256(open(tgz, "rb").read()).hexdigest()
    if h != SHA: sys.exit(f"묶음 해시가 다르다: {h}")
    tarfile.open(tgz).extractall(d, filter="data")
    return os.path.join(d, "package")


def main(argv):
    pkg = argv[0] if argv else fetch()
    rings = build(pkg)
    out = {"_설명": "홈 살아 있는 지도의 먼 바탕(땅 면만). tools-build/world_land.py 가 만든다.",
           "source": f"Natural Earth 4.1.0 1:50m land(퍼블릭 도메인) · {PKG} {VER}(npm · ISC · 묶음 SHA-256 {SHA})",
           "license": "Natural Earth — public domain(naturalearthdata.com/about/terms-of-use)",
           "region": REGION, "tolerance_deg": TOL, "rings": rings}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"고리 {len(rings)} · 꼭짓점 {sum(len(r) for r in rings) // 2} · {os.path.getsize(OUT) // 1024}KB → {OUT}")
    return 0


def selftest():
    topo = {"transform": {"scale": [1, 1], "translate": [0, 0]}, "arcs": [[[0, 0], [10, 0], [0, 10], [-10, 0], [0, -10]]],
            "objects": {"land": {"type": "GeometryCollection", "geometries": [{"type": "Polygon", "arcs": [[0]]}]}}}
    assert decode(topo) == [[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]]
    assert shift([(-120, 30), (-110, 40)]) == [(240, 30), (250, 40)]
    c = clip([(0, 0), (10, 0), (10, 10), (0, 10)], (5, -1, 20, 20))
    assert min(p[0] for p in c) == 5 and len(c) == 4, c
    assert simplify([(0, 0), (1, 0.001), (2, 0), (3, 0)], 0.01) == [(0, 0), (3, 0)]
    sq = simplify([(0, 0), (5, 0.001), (10, 0), (10, 10), (0, 10), (0, 0)], 0.01)
    assert len(sq) == 5 and sq[0] == sq[-1], sq  # 닫힌 고리가 살아남는다
    print("selftest 5/5 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main([a for a in sys.argv[1:] if not a.startswith("--")]))

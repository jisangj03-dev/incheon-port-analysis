"""인천 앞바다 등심선 — ERDDAP 격자 수심을 받아 라이선스를 확인하고 등심선 GeoJSON 을 만든다(2026-10-14).

Actions(bathy.yml)에서만 돈다. 순서:
  ① 후보 데이터셋(.das)을 읽어 license 속성을 그대로 적는다 — accept 문구에 안 맞으면 쓰지 않는다.
  ② 맞는 것 중 첫째의 부분 격자(.csv)를 받아 등심선(수심 m)을 만든다(matplotlib contour).
  ③ 결과 + 출처·라이선스 원문·해상도·받은 날을 data/derived/ 에 쓴다. 맞는 것이 없으면 meta 만(status=coast-only).
검색 결과(ID 목록)는 요약에 남긴다 — 더 고운 격자를 찾으면 bathy.json candidates 에 올린다.
  python tools-build/bathy.py [--selftest] [--search] [--refine]
    --search = 데이터셋 목록 검색까지(요청이 많다)
    --refine = 받지 않고, 이미 받은 등심선 파일을 bathy.json 의 levels_m·min_extent_deg·simplify_deg 로 다시 거른다(같은 자료 · 변환만)
"""
import csv, io, json, os, re, sys, urllib.request, urllib.error, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(url, timeout=60, tries=3):
    """503(서버 바쁨)은 잠깐 쉬고 다시 — 첫 실행에서 coastwatch 가 503 을 냈다(2026-10-14)."""
    import time
    req = urllib.request.Request(url, headers={"User-Agent": "sounding-bathy/1 (+github actions)"})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as ex:
            if ex.code != 503 or k == tries - 1:
                raise
            time.sleep(5 * (k + 1))


def das_attr(das, name):
    """NC_GLOBAL 의 문자열 속성 하나(여러 줄 이어진 것 포함)."""
    m = re.search(r'NC_GLOBAL\s*\{(.*?)\n  \}', das, re.S)
    body = m.group(1) if m else das
    m = re.search(r'String\s+' + re.escape(name) + r'\s+"(.*?)";', body, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def accepted(lic, accept):
    low = lic.lower()
    return any(a in low for a in accept)


def parse_grid(text, var):
    """ERDDAP griddap .csv(머리 2줄) → 위도·경도 정렬 격자."""
    rows = list(csv.reader(io.StringIO(text)))
    head = rows[0]
    ilat, ilon, iv = head.index("latitude"), head.index("longitude"), head.index(var)
    pts = [(float(r[ilat]), float(r[ilon]), float(r[iv])) for r in rows[2:] if r and r[iv] not in ("", "NaN")]
    lats, lons = sorted({p[0] for p in pts}), sorted({p[1] for p in pts})
    li, lo = {v: i for i, v in enumerate(lats)}, {v: i for i, v in enumerate(lons)}
    z = [[None] * len(lons) for _ in lats]
    for a, b, v in pts:
        z[li[a]][lo[b]] = v
    return lats, lons, z


def chaikin(coords, n=2):
    """모서리 깎기 두 번 — 격자 계단을 부드럽게(끝점 유지). 보기용이다 — 항해용 아님."""
    for _ in range(n):
        out = [coords[0]]
        for (x0, y0), (x1, y1) in zip(coords, coords[1:]):
            out += [[0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1], [0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1]]
        out.append(coords[-1])
        coords = out
    return coords


def dp(pts, tol):
    """Douglas–Peucker(반복형) — 선 무게를 줄인다."""
    import math
    if len(pts) < 3 or tol <= 0:
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


def extent(seg):
    xs, ys = [p[0] for p in seg], [p[1] for p in seg]
    return ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5


def contours(lats, lons, z, levels_m, min_extent=0.0, tol=0.0):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    Z = np.array([[np.nan if v is None else v for v in row] for row in z])
    feats = []
    # 고도(+)·수심(−) 격자 — 0 은 해안선, −d 는 수심 d m 등심선
    for d in [0] + list(levels_m):
        cs = plt.contour(lons, lats, Z, levels=[-d])
        for seg in cs.allsegs[0]:
            if len(seg) < 4:
                continue
            raw = [[float(x), float(y)] for x, y in seg]
            if extent(raw) < min_extent:  # 작은 섬·웅덩이 등선은 버린다(해도 바탕을 낙서처럼 만든다)
                continue
            coords = [[round(x, 5), round(y, 5)] for x, y in chaikin(dp(raw, tol))]
            feats.append({"type": "Feature", "properties": {"depth": d, "kind": "coast" if d == 0 else "contour"},
                          "geometry": {"type": "LineString", "coordinates": coords}})
        plt.close("all")
    return feats


def main():
    cfg = json.load(open(os.path.join(ROOT, "tools-build/bathy.json"), encoding="utf-8"))
    w, s, e, n = cfg["bbox"]
    tried, found = [], []
    for srv in (cfg["servers"] if "--search" in sys.argv else []):
        for q in cfg.get("search", []):
            try:
                j = json.loads(get(f"{srv}/search/index.json?page=1&itemsPerPage=50&searchFor={q}"))
                cols = j["table"]["columnNames"]
                for row in j["table"]["rows"]:
                    found.append(f"{srv} · {row[cols.index('Dataset ID')]} · {row[cols.index('Title')]}")
            except Exception as ex:  # 검색은 참고용 — 실패해도 진행
                found.append(f"{srv} · 검색 실패 {q}: {str(ex)[:80]}")
    pick = None
    for srv in cfg["servers"]:
        for c in cfg["candidates"]:
            url = f"{srv}/griddap/{c['id']}"
            try:
                das = get(url + ".das")
            except Exception as ex:
                tried.append({"url": url, "error": str(ex)[:120]})
                continue
            lic = das_attr(das, "license")
            ok = accepted(lic, cfg["accept"])
            tried.append({"url": url, "license": lic, "institution": das_attr(das, "institution"), "title": das_attr(das, "title"), "accepted": ok})
            if ok and not pick:
                for la in (f"({s}):1:({n})", f"({n}):1:({s})"):
                    try:
                        text = get(f"{url}.csv?{c['var']}[{la}][({w}):1:({e})]", timeout=180)
                        pick = {"url": url, "var": c["var"], "text": text, **tried[-1]}
                        break
                    except Exception as ex:
                        tried[-1]["subset_error"] = str(ex)[:120]
    today = datetime.date.today().isoformat()
    meta = {"retrieved": today, "bbox": cfg["bbox"], "tried": tried, "search": found[:60]}
    if not pick:
        # 앞서 받은 좋은 결과가 있으면 지우지 않는다 — 실패는 last_attempt 에만 적는다(2026-10-14 두 번째 실행이 403 으로 meta 를 덮어 써 지면과 어긋났다)
        mp = os.path.join(ROOT, cfg["meta"])
        prev = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
        attempt = {"retrieved": today, "tried": tried, "why": "라이선스 문구가 accept 에 맞는 격자를 받지 못했다"}
        if prev.get("status") == "contours" and os.path.exists(os.path.join(ROOT, cfg["out"])):
            prev["last_attempt"] = attempt
            json.dump(prev, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("이번 받기 실패 — 앞선 등심선을 그대로 둔다"); print(json.dumps(attempt, ensure_ascii=False)[:2000])
            return 0
        meta["status"] = "coast-only"
        meta["why"] = attempt["why"] + " — 등심선을 만들지 않는다"
        print(json.dumps(meta, ensure_ascii=False, indent=1)[:3000])
        json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 0
    lats, lons, z = parse_grid(pick["text"], pick["var"])
    feats = contours(lats, lons, z, cfg["levels_m"], cfg.get("min_extent_deg", 0.0), cfg.get("simplify_deg", 0.0))
    res = round((lats[-1] - lats[0]) / max(1, len(lats) - 1) * 3600, 1)
    meta.update({"status": "contours", "smoothing": "chaikin x2 (보기용)", "source": pick["url"], "title": pick.get("title"), "institution": pick.get("institution"),
                 "license": pick["license"], "grid": [len(lats), len(lons)], "resolution_arcsec": res,
                 "levels_m": cfg["levels_m"], "min_extent_deg": cfg.get("min_extent_deg"), "simplify_deg": cfg.get("simplify_deg"), "features": len(feats)})
    gj = {"type": "FeatureCollection", "source": pick["url"], "license": pick["license"], "retrieved": today, "features": feats}
    json.dump(gj, open(os.path.join(ROOT, cfg["out"]), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(meta, open(os.path.join(ROOT, cfg["meta"]), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in meta.items() if k not in ("tried", "search")}, ensure_ascii=False, indent=1))
    return 0


def refine():
    """이미 받은 등심선을 설정대로 다시 거른다 — 서버가 403 을 내도 정리는 할 수 있게(2026-10-14)."""
    cfg = json.load(open(os.path.join(ROOT, "tools-build/bathy.json"), encoding="utf-8"))
    gp, mp = os.path.join(ROOT, cfg["out"]), os.path.join(ROOT, cfg["meta"])
    g = json.load(open(gp, encoding="utf-8")); m = json.load(open(mp, encoding="utf-8"))
    keep_levels = set([0] + list(cfg["levels_m"]))
    me, tol = cfg.get("min_extent_deg", 0.0), cfg.get("simplify_deg", 0.0)
    out = []
    for f in g["features"]:
        d, c = f["properties"]["depth"], f["geometry"]["coordinates"]
        if d not in keep_levels or extent(c) < (me if d else me / 2):
            continue
        c = [[round(x, 5), round(y, 5)] for x, y in dp(c, tol)]
        if len(c) >= 3:
            out.append({**f, "geometry": {"type": "LineString", "coordinates": c}})
    before = len(g["features"])
    g["features"] = out
    json.dump(g, open(gp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    m.update({"levels_m": cfg["levels_m"], "min_extent_deg": me, "simplify_deg": tol, "features": len(out),
              "refined": f"{before}줄 → {len(out)}줄(같은 자료를 다시 거름 · --refine)"})
    json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(m["refined"], os.path.getsize(gp), "bytes")
    return 0


def selftest():
    das = 'Attributes {\n NC_GLOBAL {\n    String license "The data may be used and redistributed for free but is not intended\nfor legal use";\n    String title "ETOPO";\n  }\n}'
    lic = das_attr(das, "license")
    assert lic.startswith("The data may be used and redistributed for free"), lic
    assert accepted(lic, ["may be used and redistributed for free"])
    assert not accepted("All rights reserved", ["public domain"])
    lats, lons, z = parse_grid("latitude,longitude,z\ndegrees_north,degrees_east,m\n37.0,126.0,-10\n37.0,126.1,5\n37.1,126.0,-20\n37.1,126.1,1\n", "z")
    assert lats == [37.0, 37.1] and lons == [126.0, 126.1] and z[1][0] == -20
    sm = chaikin([[0, 0], [1, 0], [1, 1]], 1)
    assert sm[0] == [0, 0] and sm[-1] == [1, 1] and len(sm) == 6, sm
    assert len(dp([[0, 0], [1, 0.00001], [2, 0]], 0.001)) == 2 and extent([[0, 0], [0.03, 0.04]]) == 0.05
    ring = [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]
    assert len(dp(ring, 0.01)) == 5, dp(ring, 0.01)
    print("selftest 7/7 ok")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else refine() if "--refine" in sys.argv else main())

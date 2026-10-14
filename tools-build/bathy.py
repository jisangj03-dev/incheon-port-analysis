"""인천 앞바다 등심선 — ERDDAP 격자 수심을 받아 라이선스를 확인하고 등심선 GeoJSON 을 만든다(2026-10-14).

Actions(bathy.yml)에서만 돈다. 순서:
  ① 후보 데이터셋(.das)을 읽어 license 속성을 그대로 적는다 — accept 문구에 안 맞으면 쓰지 않는다.
  ② 맞는 것 중 첫째의 부분 격자(.csv)를 받아 등심선(수심 m)을 만든다(matplotlib contour).
  ③ 결과 + 출처·라이선스 원문·해상도·받은 날을 data/derived/ 에 쓴다. 맞는 것이 없으면 meta 만(status=coast-only).
검색 결과(ID 목록)는 요약에 남긴다 — 더 고운 격자를 찾으면 bathy.json candidates 에 올린다.
  python tools-build/bathy.py [--selftest]
"""
import csv, io, json, os, re, sys, urllib.request, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "sounding-bathy/1 (+github actions)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


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


def contours(lats, lons, z, levels_m):
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
            coords = [[round(float(x), 5), round(float(y), 5)] for x, y in seg]
            feats.append({"type": "Feature", "properties": {"depth": d, "kind": "coast" if d == 0 else "contour"},
                          "geometry": {"type": "LineString", "coordinates": coords}})
        plt.close("all")
    return feats


def main():
    cfg = json.load(open(os.path.join(ROOT, "tools-build/bathy.json"), encoding="utf-8"))
    w, s, e, n = cfg["bbox"]
    tried, found = [], []
    for srv in cfg["servers"]:
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
        meta["status"] = "coast-only"
        meta["why"] = "라이선스 문구가 accept 에 맞는 격자를 받지 못했다 — 등심선을 만들지 않는다"
        print(json.dumps(meta, ensure_ascii=False, indent=1)[:3000])
        json.dump(meta, open(os.path.join(ROOT, cfg["meta"]), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 0
    lats, lons, z = parse_grid(pick["text"], pick["var"])
    feats = contours(lats, lons, z, cfg["levels_m"])
    res = round((lats[-1] - lats[0]) / max(1, len(lats) - 1) * 3600, 1)
    meta.update({"status": "contours", "source": pick["url"], "title": pick.get("title"), "institution": pick.get("institution"),
                 "license": pick["license"], "grid": [len(lats), len(lons)], "resolution_arcsec": res,
                 "levels_m": cfg["levels_m"], "features": len(feats)})
    gj = {"type": "FeatureCollection", "source": pick["url"], "license": pick["license"], "retrieved": today, "features": feats}
    json.dump(gj, open(os.path.join(ROOT, cfg["out"]), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(meta, open(os.path.join(ROOT, cfg["meta"]), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in meta.items() if k not in ("tried", "search")}, ensure_ascii=False, indent=1))
    return 0


def selftest():
    das = 'Attributes {\n NC_GLOBAL {\n    String license "The data may be used and redistributed for free but is not intended\nfor legal use";\n    String title "ETOPO";\n  }\n}'
    lic = das_attr(das, "license")
    assert lic.startswith("The data may be used and redistributed for free"), lic
    assert accepted(lic, ["may be used and redistributed for free"])
    assert not accepted("All rights reserved", ["public domain"])
    lats, lons, z = parse_grid("latitude,longitude,z\ndegrees_north,degrees_east,m\n37.0,126.0,-10\n37.0,126.1,5\n37.1,126.0,-20\n37.1,126.1,1\n", "z")
    assert lats == [37.0, 37.1] and lons == [126.0, 126.1] and z[1][0] == -20
    print("selftest 4/4 ok")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

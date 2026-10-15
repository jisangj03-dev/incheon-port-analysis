"""판정 v3 실행 증명 — 깐 도구가 이 기계에서 실제로 도는지(외부 요청 0 · 작은 입력을 그 자리에서 만들어 돌린다).
  python tools-build/geo_proof.py
"""
import io, os, sys, tempfile
import numpy as np


def main():
    out = []
    import rasterio
    from rasterio.transform import from_origin
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.tif")
        a = (np.arange(100, dtype="float32").reshape(10, 10))
        with rasterio.open(p, "w", driver="GTiff", height=10, width=10, count=1, dtype="float32", crs="EPSG:4326", transform=from_origin(126, 38, 0.1, 0.1)) as w:
            w.write(a, 1)
        with rasterio.open(p) as r:
            assert r.read(1).sum() == a.sum() and r.crs.to_epsg() == 4326
        out.append(f"rasterio {rasterio.__version__} · GDAL {rasterio.__gdal_version__} — GeoTIFF 쓰고 읽기")
        import osmium
        x = os.path.join(d, "t.osm")
        open(x, "w").write('<osm version="0.6"><node id="1" lat="37.4" lon="126.6"/><node id="2" lat="37.5" lon="126.7"/>'
                           '<way id="9"><nd ref="1"/><nd ref="2"/><tag k="highway" v="motorway"/></way></osm>')
        class H(osmium.SimpleHandler):
            def __init__(s): super().__init__(); s.n = 0
            def way(s, w): s.n += w.tags.get("highway") == "motorway"
        h = H(); h.apply_file(x)
        assert h.n == 1
        from importlib.metadata import version
        out.append(f"osmium {version('osmium')} — OSM 길 읽기")
    import duckdb
    v = duckdb.sql("select sum(i) from range(10) t(i)").fetchone()[0]
    assert v == 45
    out.append(f"duckdb {duckdb.__version__} — SQL 집계")
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    import scipy
    g = csr_matrix(([1.0, 2.0, 1.0], ([0, 1, 0], [1, 2, 2])), shape=(3, 3))
    assert dijkstra(g, indices=0)[2] == 1.0
    out.append(f"scipy {scipy.__version__} — 최단 시간(dijkstra)")
    from PIL import Image
    import PIL
    b = io.BytesIO(); Image.fromarray(np.zeros((4, 4), "uint8")).save(b, "PNG")
    out.append(f"pillow {PIL.__version__} — PNG 쓰기")
    print("\n".join(out)); print(f"실행 증명 {len(out)}/5 ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

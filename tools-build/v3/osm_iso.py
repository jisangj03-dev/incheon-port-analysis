"""수도권 배송 등시선 — 인천 물류단지에서 1·2·3시간 도달권(빌드 때 미리 계산 · 2026-10-14).
OSM 대한민국 추출(Geofabrik · ODbL)에서 수도권 상자 안 도로만 osmium 으로 읽고, 도로 등급별 자유 흐름 속도로 그래프를 엮어
scipy 다익스트라로 출발지마다 최단 시간을 푼다 → 0.01° 칸마다 「가장 빠른 도착 분」(0~254 · 255 = 길 없음).
속도(km/h · 선커밋 §3): 고속 90 · 도시고속/간선(trunk) 70 · 주간선 60 · 보조간선 50 · 집산 40 · 일반·주거 25 · 연결로 50 · 서비스 15. 혼잡·신호·상하차는 반영하지 않는다.
출발지 = OSM 에서 이름에 「물류단지」가 든 인천 안 시설(OSM id 를 적는다) + 관문 셋(신항 · 남항 · 인천공항 화물터미널 · places.json).
  python tools-build/v3/osm_iso.py [--pbf <파일>]
"""
import base64, datetime, json, math, os, sys, tempfile
import numpy as np
from common import ROOT, get, write, say

BBOX = (126.2, 36.85, 127.75, 37.98)
STEP = 0.01
INCHEON = (126.35, 37.30, 126.80, 37.66)
SPEED = {"motorway": 90, "trunk": 70, "primary": 60, "secondary": 50, "tertiary": 40, "unclassified": 25, "residential": 25,
         "motorway_link": 50, "trunk_link": 50, "primary_link": 40, "secondary_link": 35, "tertiary_link": 30, "service": 15, "living_street": 10}
LIMIT_MIN = 200


def load(pbf):
    import osmium
    inb = lambda lon, lat: BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]
    class H(osmium.SimpleHandler):
        def __init__(s):
            super().__init__(); s.ways = []; s.named = []
        def way(s, w):
            hw = w.tags.get("highway")
            nm = w.tags.get("name", "")
            if "물류단지" in nm:
                try:
                    lo = [n.location for n in w.nodes if n.location.valid()]
                    if lo:
                        x = sum(l.lon for l in lo) / len(lo); y = sum(l.lat for l in lo) / len(lo)
                        if INCHEON[0] <= x <= INCHEON[2] and INCHEON[1] <= y <= INCHEON[3]: s.named.append({"name": nm, "lon": round(x, 5), "lat": round(y, 5), "osm": f"way/{w.id}"})
                except Exception: pass
            if hw not in SPEED: return
            try: pts = [(n.ref, n.location.lon, n.location.lat) for n in w.nodes]
            except osmium.InvalidLocationError: return
            if not any(inb(p[1], p[2]) for p in pts): return
            ow = w.tags.get("oneway", "no")
            s.ways.append((SPEED[hw], pts, 1 if ow in ("yes", "true", "1") or hw == "motorway" else -1 if ow == "-1" else 0))
        def node(s, n):
            nm = n.tags.get("name", "")
            if "물류단지" in nm and INCHEON[0] <= n.location.lon <= INCHEON[2] and INCHEON[1] <= n.location.lat <= INCHEON[3]:
                s.named.append({"name": nm, "lon": round(n.location.lon, 5), "lat": round(n.location.lat, 5), "osm": f"node/{n.id}"})
    h = H(); h.apply_file(pbf, locations=True, idx="flex_mem")
    return h.ways, h.named


def graph(ways):
    from scipy.sparse import csr_matrix
    idx, lon, lat, r, c, t = {}, [], [], [], [], []
    def nid(ref, x, y):
        if ref not in idx: idx[ref] = len(lon); lon.append(x); lat.append(y)
        return idx[ref]
    for spd, pts, ow in ways:
        for (a, x0, y0), (b, x1, y1) in zip(pts, pts[1:]):
            i, j = nid(a, x0, y0), nid(b, x1, y1)
            km = math.hypot((x1 - x0) * 111.32 * math.cos(math.radians((y0 + y1) / 2)), (y1 - y0) * 110.57)
            m = km / spd * 60
            if ow >= 0: r.append(i); c.append(j); t.append(m)
            if ow <= 0: r.append(j); c.append(i); t.append(m)
    n = len(lon)
    return csr_matrix((t, (r, c)), shape=(n, n)), np.array(lon), np.array(lat)


def main():
    pbf = sys.argv[sys.argv.index("--pbf") + 1] if "--pbf" in sys.argv else None
    if not pbf:
        url = "https://download.geofabrik.de/asia/south-korea-latest.osm.pbf"
        say("받는다", url)
        st, body = get(url, timeout=1200, binary=True)
        if st != 200: write("data/collected/v3/osm_iso_probe.json", {"url": url, "status": st}); return 1
        pbf = os.path.join(tempfile.mkdtemp(), "kr.osm.pbf"); open(pbf, "wb").write(body)
    ways, named = load(pbf)
    say("도로", len(ways), "· 이름에 물류단지", len(named))
    G, lon, lat = graph(ways)
    from scipy.sparse.csgraph import dijkstra
    W, H = round((BBOX[2] - BBOX[0]) / STEP), round((BBOX[3] - BBOX[1]) / STEP)
    cx = np.clip(((lon - BBOX[0]) / STEP).astype(int), 0, W - 1); cy = np.clip(((BBOX[3] - lat) / STEP).astype(int), 0, H - 1)
    inside = (lon >= BBOX[0]) & (lon <= BBOX[2]) & (lat >= BBOX[1]) & (lat <= BBOX[3])
    # 출발지 — 같은 이름은 한 번(OSM 면 여러 조각) · 관문 셋
    seen, origins = set(), []
    for o in sorted(named, key=lambda o: o["name"]):
        if o["name"] in seen: continue
        seen.add(o["name"]); origins.append({**o, "kind": "물류단지"})
    P = json.load(open(os.path.join(ROOT, "data/derived/places.json"), encoding="utf-8"))["places"]
    for p in P:
        if p["id"] in ("신항", "남항", "인천공항"): origins.append({"name": p["label"], "lon": p["lon"], "lat": p["lat"], "osm": p.get("coord_source", "")[:60], "kind": "관문"})
    out = []
    for o in origins:
        d2 = (lon - o["lon"]) ** 2 + (lat - o["lat"]) ** 2
        s = int(np.argmin(d2))
        snap_km = math.sqrt(d2[s]) * 100
        dist = dijkstra(G, indices=s, limit=LIMIT_MIN)
        grid = np.full((H, W), 255.0)
        ok = inside & np.isfinite(dist)
        np.minimum.at(grid, (cy[ok], cx[ok]), dist[ok])
        # 길 없는 칸은 이웃 칸 + 2분(가까운 길까지)으로 메운다 — 한 번만(바다·산을 덮지 않게)
        pad = np.pad(grid, 1, constant_values=255)
        nb = np.min([pad[1 + dy: 1 + dy + H, 1 + dx: 1 + dx + W] for dy in (-1, 0, 1) for dx in (-1, 0, 1)], axis=0) + 2
        grid = np.where(grid < 255, grid, np.minimum(nb, 255))
        g8 = np.clip(np.round(grid), 0, 255).astype("uint8")
        reach = {f"{h}h": int((g8 <= 60 * h).sum()) for h in (1, 2, 3)}
        out.append({**o, "snap_km": round(snap_km, 2), "cells": reach, "b64": base64.b64encode(g8.tobytes()).decode()})
        say(o["name"], reach, f"붙임 {snap_km:.2f}km")
    write("data/derived/isochrones.json", {
        "_설명": "인천 물류단지·관문에서 수도권 칸(0.01°)마다 가장 빠른 도착 분. 도로 등급별 자유 흐름 속도 가정 — 혼잡·신호·상하차 미반영. 255 = 길 없음/200분 넘음.",
        "source": "OpenStreetMap 기여자(ODbL 1.0) · Geofabrik south-korea 추출", "made": datetime.date.today().isoformat(),
        "bbox": BBOX, "step": STEP, "w": W, "h": H, "speeds_kmh": SPEED, "limit_min": LIMIT_MIN, "origins": out})
    return 0


if __name__ == "__main__":
    sys.exit(main())

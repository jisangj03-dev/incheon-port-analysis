# -*- coding: utf-8 -*-
"""3D 지도 자리표 후보 — Overpass API(OpenStreetMap · ODbL)에서 이름으로 찾는다(A-6 · Actions 에서만 돈다).

입력 tools-build/places-query.json · 출력 data/derived/places_osm.json(후보 전부 · OSM id · 이름 · 태그 · 중심점).
places.json 을 직접 고치지 않는다 — 이름이 비슷한 다른 시설(예: 「남항」 어시장)을 잘못 고르는 일을 막으려고 사람이 고른다.
키 0 · 외부 요청은 Actions 안에서 overpass-api.de 한 곳.
"""
import json, re, sys, time, urllib.request, urllib.parse

Q = json.load(open("tools-build/places-query.json", encoding="utf-8"))
s, w, n, e = Q["bbox"]
URL = "https://overpass-api.de/api/interpreter"
out = {"_설명": "OSM 후보(자동 생성 · places-fetch.yml). © OpenStreetMap 기여자 · ODbL. places.json 으로 옮길 때 osm_id 를 coord_source 에 적는다.",
       "queried": time.strftime("%Y-%m-%d"), "bbox": Q["bbox"], "places": []}
for p in Q["places"]:
    rx = p["name_regex"]
    s, w, n, e = p.get("bbox", Q["bbox"])
    kinds = "nw" if not p.get("require_area") else "wr"   # 면이어야 하면 길·점은 뺀다(1회: 「인천신항대로」 같은 길이 섞였다)
    q = f'[out:json][timeout:60];({kinds}["name"~"{rx}"]({s},{w},{n},{e});{kinds}["name:en"~"{rx}"]({s},{w},{n},{e}););out center tags 60;'
    body = urllib.parse.urlencode({"data": q}).encode()
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, data=body, headers={"User-Agent": "sounding-places/1 (github.com/jisangj03-dev/incheon-port-analysis)"}), timeout=90) as r:
                data = json.load(r)
            break
        except Exception as ex:
            print("재시도", p["id"], ex, file=sys.stderr); time.sleep(5 * (attempt + 1))
    else:
        out["places"].append({"id": p["id"], "error": "Overpass 응답 없음"}); continue
    cands = []
    for el in data.get("elements", []):
        c = el.get("center") or ({"lat": el.get("lat"), "lon": el.get("lon")} if "lat" in el else None)
        if not c:
            continue
        t = el.get("tags", {})
        if p.get("require_area") and not any(k in t for k in ("landuse", "industrial", "aeroway", "harbour", "building", "man_made", "amenity")):
            continue   # 시설 태그가 없는 면(길 묶음 등)은 뺀다
        if t.get("highway"):
            continue
        cands.append({"osm": f'{el["type"]}/{el["id"]}', "name": t.get("name"), "name_en": t.get("name:en"),
                      "kind": {k: t[k] for k in ("landuse", "industrial", "aeroway", "amenity", "building", "harbour", "man_made", "operator") if k in t},
                      "lat": round(c["lat"], 5), "lon": round(c["lon"], 5)})
    out["places"].append({"id": p["id"], "want": p["want"], "candidates": cands})
    time.sleep(2)
json.dump(out, open("data/derived/places_osm.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("후보:", {p["id"]: len(p.get("candidates", [])) for p in out["places"]})

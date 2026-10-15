"""수도권 물류 흐름 층(2026-10-15 공개 전 개편 P0) — 관문에서 수도권 목적지까지 고속도로를 따라가는 길과, 그 길이 겹치는 구간의 굵기(= 지나는 몫의 합).

입력: data/derived/land_incheon.geojson(OSM 고속도로 · 번호 ref · bathy 워크플로) · data/derived/home_flows.json(관문·목적지·창고 개소).
방법: 고속도로 꼭짓점을 0.002°(약 200m) 칸으로 붙여 그래프를 엮고 → 관문·목적지에서 가장 가까운 고속도로 점으로 붙여 → 최단 거리(다익스트라) 길.
몫(굵기·점 빈도의 바탕):
  · 인천 구·군 · 서울 = 물류창고 등록 개소(실측 · home_flows.json)
  · 경기 = 도 전체 창고 개소(실측)를 물류 밀집지 여섯(김포·부천·이천·용인·안성·광주)에 **똑같이 나눈 것 — 가정**
    (경기 시·군별 창고 개소는 저장소에 없다 · nlic·공공데이터포털이 이 세션에서 막혀 받지 못했다 · 받으면 이 줄을 실측으로 바꾼다)
거점 점(흐름 없이 자리만): 인천항 북항·아암 물류단지 · 인천공항 자유무역지역 · 평택·당진항 · 의왕 ICD — 개략 위치(±2km).
결과: data/derived/sudo_corridors.json
  python tools-build/corridors_derive.py [--selftest]
"""
import heapq, json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/sudo_corridors.json")
SNAP = 0.002
JOIN_KM = 1.5
# 경기 물류 밀집지(시청·대표 물류단지 부근 · 개략) — 몫은 경기 전체를 똑같이 나눈 가정
GG = {"김포": (126.716, 37.615), "부천": (126.783, 37.503), "이천": (127.443, 37.272), "용인": (127.200, 37.234), "안성": (127.280, 37.008), "광주": (127.255, 37.429)}
# 거점(자리만 · 개략)
HUBS = [
    {"id": "북항", "lon": 126.628, "lat": 37.512, "kind": "port", "note": "인천항 북항(철재·목재·곡물)"},
    {"id": "아암 물류단지", "lon": 126.622, "lat": 37.437, "kind": "park", "note": "인천항 배후 물류단지"},
    {"id": "공항 자유무역지역", "lon": 126.452, "lat": 37.466, "kind": "ftz", "note": "인천공항 자유무역지역(물류단지)"},
    {"id": "평택·당진항", "lon": 126.840, "lat": 36.968, "kind": "port", "note": "경기·충남 서해 관문"},
    {"id": "의왕 ICD", "lon": 126.965, "lat": 37.330, "kind": "icd", "note": "내륙 컨테이너 기지(철도·도로)"},
]
# 화물 고속도로 다섯(번호 → 이름) — 이름표 자리는 그 번호 선의 가운데 꼭짓점
HW = {"110": "제2경인", "100": "수도권제1순환", "50": "영동", "1": "경부", "15": "서해안"}


def km(a, b):
    x = (b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2)); y = b[1] - a[1]
    return math.hypot(x, y) * 111.2


def build(roads):
    key = lambda p: (round(p[0] / SNAP), round(p[1] / SNAP))
    pos, adj = {}, {}
    for c in roads:
        prev = None
        for p in c:
            k = key(p); pos.setdefault(k, (k[0] * SNAP, k[1] * SNAP))
            if prev is not None and prev != k:
                w = km(pos[prev], pos[k]); adj.setdefault(prev, {}); adj.setdefault(k, {})
                adj[prev][k] = min(w, adj[prev].get(k, 1e9)); adj[k][prev] = adj[prev][k]
            prev = k
    # 타일 경계에서 잘린 조각 잇기 — 끝점(이웃 하나 이하)을 JOIN_KM 안 가장 가까운 다른 점과 잇는다(2026-10-15 첫 실행: 가장 큰 덩어리가 615점뿐 · 이천·평택 쪽 길이 끊겼다)
    grid = {}
    for k in adj: grid.setdefault((k[0] // 10, k[1] // 10), []).append(k)
    for k in [k for k in adj if len(adj[k]) <= 1]:
        best_v, best_w = None, JOIN_KM
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for v in grid.get((k[0] // 10 + dx, k[1] // 10 + dy), []):
                    if v == k or v in adj[k]: continue
                    w = km(pos[k], pos[v])
                    if w < best_w: best_v, best_w = v, w
        if best_v is not None: adj[k][best_v] = best_w; adj[best_v][k] = best_w
    # 가장 큰 연결 덩어리만(고립된 짧은 조각에 붙지 않게)
    seen, best = set(), set()
    for s in adj:
        if s in seen: continue
        comp, st = {s}, [s]; seen.add(s)
        while st:
            u = st.pop()
            for v in adj[u]:
                if v not in seen: seen.add(v); comp.add(v); st.append(v)
        if len(comp) > len(best): best = comp
    adj = {k: {v: w for v, w in n.items() if v in best} for k, n in adj.items() if k in best}
    return pos, adj


def nearest(pos, adj, p):
    return min(adj, key=lambda k: (pos[k][0] - p[0]) ** 2 * math.cos(math.radians(p[1])) ** 2 + (pos[k][1] - p[1]) ** 2)


def path(adj, s, t):
    D, P, h = {s: 0.0}, {}, [(0.0, s)]
    while h:
        d, u = heapq.heappop(h)
        if u == t: break
        if d > D.get(u, 1e18): continue
        for v, w in adj[u].items():
            nd = d + w
            if nd < D.get(v, 1e18): D[v] = nd; P[v] = u; heapq.heappush(h, (nd, v))
    if t not in D: return None
    out = [t]
    while out[-1] != s: out.append(P[out[-1]])
    return out[::-1]


def main():
    L = json.load(open(os.path.join(ROOT, "data/derived/land_incheon.geojson"), encoding="utf-8"))
    F = json.load(open(os.path.join(ROOT, "data/derived/home_flows.json"), encoding="utf-8"))
    roads = [f for f in L["features"] if f["properties"]["kind"] == "road"]
    pos, adj = build([f["geometry"]["coordinates"] for f in roads])
    gates = [{"id": g["id"], "lon": g["lon"], "lat": g["lat"]} for g in F["sea_gates"]] + [{"id": F["air_gate"]["id"], "lon": F["air_gate"]["lon"], "lat": F["air_gate"]["lat"]}]
    gg = next(d for d in F["dests"] if d["id"] == "경기도")
    dests = [{**{k: d[k] for k in ("id", "lon", "lat", "n")}, "basis": "실측(창고 개소)"} for d in F["dests"] if d["id"] != "경기도"]
    for nm, (x, y) in GG.items():
        dests.append({"id": nm, "lon": x, "lat": y, "n": round(gg["n"] / len(GG), 1), "basis": f"가정(경기 {gg['n']:,}곳 ÷ {len(GG)})"})
    tot = sum(d["n"] for d in dests)
    routes, use = {}, {}
    for gi, g in enumerate(gates):
        s = nearest(pos, adj, (g["lon"], g["lat"]))
        for di, d in enumerate(dests):
            t = nearest(pos, adj, (d["lon"], d["lat"]))
            p = path(adj, s, t) if s != t else [s]
            if not p: continue
            pts = [[g["lon"], g["lat"]]] + [[round(pos[k][0], 4), round(pos[k][1], 4)] for k in p] + [[d["lon"], d["lat"]]]
            # 꼭짓점 줄이기(일정 간격 · 화면에서 매끈) — 1.5km 안 꼭짓점은 건너뛴다
            thin = [pts[0]]
            for q in pts[1:-1]:
                if km(thin[-1], q) > 1.5: thin.append(q)
            thin.append(pts[-1])
            routes[f"{gi}|{di}"] = thin
            share = d["n"] / tot / len(gates)
            for a, b in zip(p, p[1:]):
                e = (a, b) if a < b else (b, a); use[e] = use.get(e, 0) + share
    # 굵기 구간 — 같은 몫이 이어지는 간선을 한 줄로(간선마다 따로 내면 파일이 커진다)
    segs = sorted(use.items(), key=lambda kv: -kv[1])
    wmax = segs[0][1] if segs else 1
    corridors = [{"w": round(w / wmax, 3), "pts": [[round(pos[a][0], 4), round(pos[a][1], 4)], [round(pos[b][0], 4), round(pos[b][1], 4)]]} for (a, b), w in segs if w / wmax >= 0.02]
    labels = []
    for ref, nm in HW.items():
        cs = [c for f in roads if f["properties"].get("ref") == ref for c in f["geometry"]["coordinates"]]
        if not cs: continue
        cs.sort(key=lambda c: (c[0] + c[1]))
        labels.append({"id": nm, "ref": ref, "lon": cs[len(cs) // 2][0], "lat": cs[len(cs) // 2][1]})
    out = {"_설명": "수도권 물류 흐름 층 — 관문→목적지 길은 OSM 고속도로 최단 거리, 굵기 w = 그 구간을 지나는 목적지 몫의 합(최대 1). 몫: 인천 구·군·서울 = 창고 개소 실측, 경기 밀집지 여섯 = 경기 전체를 똑같이 나눈 가정.",
           "source": "OpenStreetMap 기여자(ODbL) · 국토교통부 물류창고업 등록 개소", "assume": f"경기 시·군별 창고 개소가 없어 경기 {gg['n']:,}곳을 여섯 밀집지에 똑같이 나눴다(가정) · 길은 최단 거리 가정(실제 화물 경로·교통량 아님)",
           "gates": gates, "dests": dests, "hubs": HUBS, "routes": routes, "corridors": corridors, "labels": labels}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"graph": len(adj), "routes": len(routes), "of": len(gates) * len(dests), "corridors": len(corridors), "labels": [l["id"] for l in labels], "bytes": os.path.getsize(OUT)}, ensure_ascii=False))
    return 0 if len(routes) == len(gates) * len(dests) else 1


def selftest():
    pos, adj = build([[[0, 0], [0.01, 0], [0.02, 0]], [[0.02, 0], [0.02, 0.01]], [[5, 5], [5.01, 5]]])
    assert len(adj) == 4, adj  # 떨어진 조각은 뺀다
    s, t = nearest(pos, adj, (0, 0.0005)), nearest(pos, adj, (0.02, 0.011))
    p = path(adj, s, t)
    assert p and p[0] == s and p[-1] == t and len(p) == 4, p
    assert abs(km((126.0, 37.0), (126.0, 38.0)) - 111.2) < 0.1
    print("selftest 3/3 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

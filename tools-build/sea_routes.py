"""홈 지도 바다 길 — 나라 대표 항만 → 인천의 최단 해상 경로를 계산한다(2026-10-20 · docs/품질기준.md Q3).

종전에는 손으로 찍은 경유점(「육지를 피해 긋는다」)이었다 = 개념선. 이제 searoute 1.5.0(Apache-2.0 · Eurostat MARNET 해상 경로망)이
계산한 길을 쓴다 — 누가 돌려도 같은 길이 나온다(초크포인트 도구 tools-build/choke_detour.py 와 같은 계산기).
배 한 척의 실제 항적이 아니라 「해상망 위 최단 경로」다(지면 방법 칸에 그렇게 적는다).

출발 = flows_derive.py PARTNERS 의 바다 대표 항만(첫 점) · 도착 = 인천항 신항. 끝 마디(해상망의 인천 쪽 마디)까지 저장하고,
마디 → 부두는 지면이 잇는다(가까이 보는 화면에서는 바다 위 점을 그리지 않는다 — lib/flowmap.ts).
경도는 끊기지 않게 잇는다(태평양 횡단 = 180° 를 넘으면 +360).

  pip install searoute==1.5.0 && python tools-build/sea_routes.py      # 결과 data/derived/sea_routes.json
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/sea_routes.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flows_derive import PARTNERS, SEA_GATES  # noqa: E402


def unwrap(coords):
    out = []
    for lon, lat in coords:
        if out:
            while lon - out[-1][0] > 180: lon -= 360
            while lon - out[-1][0] < -180: lon += 360
        out.append([lon, lat])
    k = round((126 - out[-1][0]) / 360) * 360  # 끝(인천 쪽)이 동경 126° 근처에 오게 통째로 민다 — 미주 출발은 +360 쪽으로
    return [[round(x + k, 3), round(y, 3)] for x, y in out]


def main():
    import searoute as sr
    to = SEA_GATES["신항"]["at"]
    routes = {}
    for c, p in PARTNERS.items():
        a = p["sea"][0][:]
        if a[0] > 180: a[0] -= 360
        r = sr.searoute(a, to, units="naut")
        routes[c] = {"from": p["at"], "naut": round(r["properties"]["length"]), "path": unwrap(r["geometry"]["coordinates"])}
    json.dump({"_설명": "나라 대표 항만 → 인천항(신항)의 해상망 최단 경로 — searoute 1.5.0(Eurostat MARNET). 실제 항적이 아니다.",
               "tool": "searoute 1.5.0 (Apache-2.0 · Eurostat MARNET)", "to": "인천항 신항", "routes": routes},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(" · ".join(f"{c} {v['naut']}해리" for c, v in routes.items()), "→", OUT)


if __name__ == "__main__":
    main()

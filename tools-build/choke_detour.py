"""초크포인트 우회 거리·일수(P1 ③ · 2026-10-15) — 길목이 막히면 대표 항로가 얼마나 길어지나.
계산: searoute 1.5.0(Apache-2.0 · Eurostat MARNET 해상 경로망)로 대표 항로의 최단 해상 거리를 길목을 열었을 때·막았을 때 두 번 잰다.
일수 = 늘어난 거리 ÷ (속력 × 24) — 속력은 가정(16노트 · 컨테이너선 감속 운항 무렵). 실제 우회 항로·기항지·혼잡은 반영하지 않는다(지면에 적는다).
  · 홍해(바브엘만데브): 부산 → 로테르담(북유럽 · KCCI 북유럽 항로와 같은 축) · 수에즈·바브엘만데브를 막으면 희망봉
  · 믈라카: 부산 → 로테르담 · 믈라카를 막으면 순다/롬복 쪽
  · 호르무즈: 걸프 안 항만(라스타누라)은 바다로 돌아갈 길이 없다 → 「우회 길 없음」 · 끝점 = 울산(원유 하역항 쪽 · 부산은 원유 항이 아니다 — 39차 사실 대조 경미 · 2026-10-23)
  · 대만해협: 경로망에 길목 표시가 없어 계산하지 않는다(대만 동쪽 우회는 거리 차가 작다 — 미계산으로 적는다)
결과: data/derived/choke_detour.json(이 스크립트를 돌린 결과를 커밋 · 경로망이 바뀌지 않으면 값도 같다)
  pip install searoute==1.5.0 && python tools-build/choke_detour.py
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOT = 16
BUSAN, RTM, RAS, ULSAN = [129.04, 35.10], [4.00, 51.95], [50.16, 26.64], [129.38, 35.50]
CASES = [
    # 홍해 — 수에즈·바브엘만데브만 막으면 경로망이 파나마로 돌린다(13,022해리 · 2026-10-15 첫 계산) → 실제 아시아–북유럽 우회인 희망봉을 재려고 파나마도 막는다
    ("redsea", "부산 → 로테르담(희망봉)", BUSAN, RTM, ["babalmandab", "suez", "panama"]),
    ("malacca", "부산 → 로테르담", BUSAN, RTM, ["malacca"]),
    ("hormuz", "라스타누라(걸프) → 울산", RAS, ULSAN, ["ormuz"]),
]


def main():
    import searoute as sr
    out = {"_설명": "대표 항로의 최단 해상 거리(해리) — 길목을 열었을 때 vs 막았을 때. 일수 = 늘어난 거리 ÷ (16노트 × 24시간) · 속력은 가정.",
           "tool": "searoute 1.5.0 (Apache-2.0 · Eurostat MARNET)", "knot": KNOT, "points": {}}
    base_r = ["northwest", "northeast"]  # 북극 항로는 늘 막는다(계절 항로)
    for pid, label, a, b, closed in CASES:
        o = sr.searoute(a, b, units="naut", restrictions=base_r)
        L0 = o.properties["length"]
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore"); c = sr.searoute(a, b, units="naut", restrictions=base_r + closed)
            L1 = c.properties["length"]
        except Exception:
            L1 = float("inf")
        rec = {"route": label, "open_nm": round(L0)}
        if L1 == float("inf") or L1 != L1 or L1 > 1e6 or L1 <= 0:  # 길이 없으면 경로망이 0 을 돌려준다
            rec.update({"closed_nm": None, "extra_nm": None, "extra_days": None, "note": "바닷길 우회는 없다 — 걸프 안 항만에서 나가는 뱃길은 이 해협 하나뿐이다. 육상 출구는 송유관 둘(사우디 동서 송유관 → 홍해 얀부 · UAE 하브샨 → 오만만 푸자이라)뿐이라 원유 일부만 돌린다"})
        else:
            rec.update({"closed_nm": round(L1), "extra_nm": round(L1 - L0), "extra_days": round((L1 - L0) / (KNOT * 24), 1)})
        out["points"][pid] = rec
    out["points"]["taiwan"] = {"route": "부산 → 싱가포르", "note": "경로망에 대만해협 길목 표시가 없어 계산하지 않았다(대만 동쪽 우회 — 거리 차가 작다)"}
    json.dump(out, open(os.path.join(ROOT, "data/derived/choke_detour.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out["points"], ensure_ascii=False)); return 0


if __name__ == "__main__":
    sys.exit(main())

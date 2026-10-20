"""등시선 시간대 배율(2026-10-15 P1 ①) — 카카오 내비 대조 통계(data/derived/navi_check.json)의 시간대별 중앙값 오차로 자유 흐름 분을 늘리는 배율.
배율 = 1 ÷ (1 + 중앙값 오차) — 예: 우리 값이 −43.6% 짧으면 ×1.77. 실측 소통 속도가 아니다(표본 30쌍의 중앙값 보정 · 지면에 적는다).
ITS 실측 속도(ITS_API_KEY)가 들어오면 이 파일 대신 그것을 쓴다(docs/신청서초안_ITS_오픈API_20261015.md).
결과: data/derived/reach_slots.json
[2026-10-20 #67] 지면 기본 시간대 = 「낮」(default) · 출발지 × 시간대마다 배율을 곱한 도착 분 표(table)도 여기서 낸다 —
  지면 숫자는 데이터 파일에만 있다(§2-1) · 반올림 = JS Math.round 와 같게(0.5 올림). isochrones.json 이 바뀌면 이 스크립트를 다시 돌린다
  (tests/tools-v3.spec.mjs 「등시선: 시간대 표 = isochrones × 배율」이 어긋나면 빨갛게 잡는다).
  python tools-build/reach_slots.py [--selftest]
"""
import json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def factor(median_pct):
    return round(1 / (1 + median_pct / 100), 2)


def jround(x):
    return int(math.floor(x + 0.5))


def scale(cities, k):
    return {c: (None if m is None else jround(m * k)) for c, m in cities.items()}


def table(iso, slots):
    out = []
    for o in iso["origins"]:
        row = {}
        for s in slots:
            car = scale(o["cities"], s["k"])
            rec = {"car": car, "within": {h: sum(1 for m in car.values() if m is not None and m <= 60 * int(h[0])) for h in ("1h", "2h", "3h")}}
            if o.get("cities_truck"): rec["truck"] = scale(o["cities_truck"], s["k"])
            row[s["id"]] = rec
        out.append(row)
    return out


def main():
    p = os.path.join(ROOT, "data/derived/navi_check.json")
    N = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    slots = [{"id": "자유 흐름", "k": 1, "basis": "OSM 도로 등급별 가정 속도"}]
    if N and N.get("status") == "ok":
        for nm, v in N["slots"].items():
            slots.append({"id": nm.split()[0], "label": nm, "k": factor(v["median_pct"]), "median_pct": v["median_pct"], "n": v["n"], "basis": f"카카오 내비 대조 중앙값 보정({N['made']} · {v['n']}쌍)"})
    iso = json.load(open(os.path.join(ROOT, "data/derived/isochrones.json"), encoding="utf-8"))
    default = "낮" if any(s["id"] == "낮" for s in slots) else slots[0]["id"]
    out = {"_설명": "등시선 시간대 배율 — 카카오 내비(미래 출발시각) 대조 중앙값 오차로 자유 흐름 분을 늘린 것. 실측 소통 속도가 아니다. table = 출발지(isochrones.json 순서) × 시간대 → 도착 분(자유 흐름 분 × 배율 · 0.5 올림).",
           "navi_made": N.get("made") if N else None, "iso_made": iso.get("made"), "default": default, "slots": slots, "table": table(iso, slots)}
    json.dump(out, open(os.path.join(ROOT, "data/derived/reach_slots.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps([(s["id"], s["k"]) for s in slots], ensure_ascii=False)); return 0


def selftest():
    assert factor(-43.6) == 1.77 and factor(-27.4) == 1.38 and factor(0) == 1
    assert jround(2.5) == 3 and jround(38 * 1.38) == 52 and scale({"a": None, "b": 10}, 1.38) == {"a": None, "b": 14}
    t = table({"origins": [{"cities": {"x": 50, "y": 100}}]}, [{"id": "낮", "k": 1.38}])
    assert t[0]["낮"]["car"] == {"x": 69, "y": 138} and t[0]["낮"]["within"] == {"1h": 0, "2h": 1, "3h": 2}
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

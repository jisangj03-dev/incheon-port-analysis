"""등시선 시간대 배율(2026-10-15 P1 ①) — 카카오 내비 대조 통계(data/derived/navi_check.json)의 시간대별 중앙값 오차로 자유 흐름 분을 늘리는 배율.
배율 = 1 ÷ (1 + 중앙값 오차) — 예: 우리 값이 −43.6% 짧으면 ×1.77. 실측 소통 속도가 아니다(표본 30쌍의 중앙값 보정 · 지면에 적는다).
ITS 실측 속도(ITS_API_KEY)가 들어오면 이 파일 대신 그것을 쓴다(docs/신청서초안_ITS_오픈API_20261015.md).
결과: data/derived/reach_slots.json
  python tools-build/reach_slots.py [--selftest]
"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def factor(median_pct):
    return round(1 / (1 + median_pct / 100), 2)


def main():
    p = os.path.join(ROOT, "data/derived/navi_check.json")
    N = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    slots = [{"id": "자유 흐름", "k": 1, "basis": "OSM 도로 등급별 가정 속도"}]
    if N and N.get("status") == "ok":
        for nm, v in N["slots"].items():
            slots.append({"id": nm.split()[0], "label": nm, "k": factor(v["median_pct"]), "median_pct": v["median_pct"], "n": v["n"], "basis": f"카카오 내비 대조 중앙값 보정({N['made']} · {v['n']}쌍)"})
    out = {"_설명": "등시선 시간대 배율 — 카카오 내비(미래 출발시각) 대조 중앙값 오차로 자유 흐름 분을 늘린 것. 실측 소통 속도가 아니다.", "navi_made": N.get("made") if N else None, "slots": slots}
    json.dump(out, open(os.path.join(ROOT, "data/derived/reach_slots.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps([(s["id"], s["k"]) for s in slots], ensure_ascii=False)); return 0


def selftest():
    assert factor(-43.6) == 1.77 and factor(-27.4) == 1.38 and factor(0) == 1
    print("selftest 1/1 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

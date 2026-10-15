"""선박 리플레이(정체성 §3-3) — 월 집계 원천(data/collected/vessel-monthly.csv)에서 지면이 쓰는 숫자를 만든다.

개별 선박이 아니다 — 항만·선종별 월 합계다. 지면은 「월 집계 — 개별 선박 아님」이라고 적는다.
외항 = 국적선 + 외국선(국제 항로) · 연안 = 연안선. 결과 data/derived/vessel_replay.json.
V1: 원천 행 수와 기간을 같이 적고, 시험이 원천 CSV 와 대조한다.
  python tools-build/vessel_derive.py [--selftest]
"""
import csv, datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data/collected/vessel-monthly.csv")
META = os.path.join(ROOT, "data/collected/vessel-monthly.json")
OUT = os.path.join(ROOT, "data/derived/vessel_replay.json")
PORTS = ["인천", "부산", "평택.당진", "경인"]
OCEAN = ("국적선", "외국선")


def derive(rows):
    months = sorted({r["ym"] for r in rows})
    ocean = {p: {m: 0 for m in months} for p in PORTS}
    coastal = {m: 0 for m in months}
    all_ocean = {m: 0 for m in months}
    for r in rows:
        n = int(r["etr_cnt"])
        if r["kind"] in OCEAN:
            all_ocean[r["ym"]] += n
            if r["port"] in ocean: ocean[r["port"]][r["ym"]] += n
        elif r["kind"] == "연안선" and r["port"] == "인천":
            coastal[r["ym"]] += n
    last = months[-1]
    # 마지막 달이 비었으면(아직 안 나온 달) 그 앞 달을 쓴다
    while all_ocean[last] == 0 and len(months) > 1:
        months = months[:-1]; last = months[-1]
    prev_y = f"{int(last[:4]) - 1}{last[4:]}"
    inc, bus = ocean["인천"][last], ocean["부산"][last]
    return {
        "months": [f"{m[:4]}-{m[4:]}" for m in months],
        "ocean_arrivals": {p: [ocean[p][m] for m in months] for p in PORTS},
        "incheon_coastal": [coastal[m] for m in months],
        "latest": {"ym": f"{last[:4]}-{last[4:]}", "incheon": inc, "busan": bus, "pyeongtaek": ocean["평택.당진"][last], "gyeongin": ocean["경인"][last],
                   "incheon_share_pct": round(100 * inc / all_ocean[last], 1) if all_ocean[last] else None,
                   "busan_to_incheon": round(bus / inc, 1) if inc else None,
                   "incheon_yoy_pct": round(100 * (inc / ocean["인천"][prev_y] - 1), 1) if ocean["인천"].get(prev_y) else None},
        "counter": "외항선 입항 척수로는 부산이 인천보다 훨씬 많다",
        "source_rows": len(rows), "source_months": [months[0], months[-1]] if months else [],
        "computed": datetime.date.today().isoformat(), "command": "python tools-build/vessel_derive.py",
        "granularity": "월 · 항만 · 선종 합계 — 개별 선박 아님",
    }


def main():
    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    d = derive(rows)
    if os.path.exists(META): d["fetched"] = json.load(open(META, encoding="utf-8")).get("fetched")
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(d["latest"], ensure_ascii=False), d["source_rows"], d["source_months"])
    return 0


def selftest():
    rows = [
        {"ym": "202508", "port": "인천", "kind": "외국선", "etr_cnt": "400"}, {"ym": "202508", "port": "인천", "kind": "국적선", "etr_cnt": "100"},
        {"ym": "202608", "port": "인천", "kind": "외국선", "etr_cnt": "447"}, {"ym": "202608", "port": "인천", "kind": "국적선", "etr_cnt": "76"},
        {"ym": "202608", "port": "인천", "kind": "연안선", "etr_cnt": "574"}, {"ym": "202608", "port": "부산", "kind": "외국선", "etr_cnt": "1354"},
        {"ym": "202608", "port": "부산", "kind": "국적선", "etr_cnt": "465"}, {"ym": "202609", "port": "인천", "kind": "외국선", "etr_cnt": "0"},
    ]
    d = derive(rows)
    L = d["latest"]
    assert L["ym"] == "2026-08" and L["incheon"] == 523 and L["busan"] == 1819 and L["busan_to_incheon"] == 3.5 and L["incheon_yoy_pct"] == 4.6, L
    assert d["incheon_coastal"][-1] == 574 and d["source_rows"] == 8
    print("selftest 1/1 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

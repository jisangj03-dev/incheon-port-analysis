# -*- coding: utf-8 -*-
"""인천항 수요예측 실험실 — 예측·채점(방법론 = docs/수요예측_방법론_선커밋_20261014.md · 정체성 전환 §3-4).

  python analysis/forecast_teu.py --issue      # 마지막 실제값 달 T 기준으로 T+1~T+3 예측(B·M1)을 원장에 덧붙인다(이미 낸 기준월이면 아무것도 안 함)
  python analysis/forecast_teu.py --score      # 익은 행 채점(MAPE · 방향 · 그 달 승패)
  python analysis/forecast_teu.py --selftest

대상 = analysis/terminal_monthly_long.csv 의 「컨테이너 합계」 당월_천TEU(공표 합계 그대로).
원장 = data/forecast/incheon_container_teu.csv — 덧붙이기만(검사 tools-build/check_ledger.py).
발행 창(F2): T+1 실제값이 main 에 들어오기 전에 main 에 들어간 예측만 인정 — 창을 놓친 기준월은 내지 않는다.
"""
import csv
import datetime as dt
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # 운영자 콘솔(cp949)에서 한글 출력이 터지지 않게(boot_check 「운영자 콘솔 안전」)
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
SERIES = ROOT / "analysis" / "terminal_monthly_long.csv"
LEDGER = ROOT / "data" / "forecast" / "incheon_container_teu.csv"
COLS = ["issued", "origin", "target", "h", "model", "yhat"]
HORIZON = 3


def add_months(ym, k):
    y, m = int(ym[:4]), int(ym[5:7])
    m += k
    while m > 12:
        y, m = y + 1, m - 12
    while m < 1:
        y, m = y - 1, m + 12
    return f"{y:04d}-{m:02d}"


def load_series(path=SERIES):
    out = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("터미널") == "컨테이너 합계" and r.get("당월_천TEU", "").strip():
                out[r["기준연월"]] = float(r["당월_천TEU"])
    return out


def baseline(y, target):
    return y.get(add_months(target, -12))


def m1(y, origin, target):
    last = [y.get(add_months(origin, -k)) for k in range(12)]
    prev = [y.get(add_months(origin, -12 - k)) for k in range(12)]
    b = baseline(y, target)
    if None in last or None in prev or b is None or sum(prev) == 0:
        return None
    return b * sum(last) / sum(prev)


def forecasts(y, origin, issued):
    rows = []
    for h in range(1, HORIZON + 1):
        t = add_months(origin, h)
        for name, v in (("B", baseline(y, t)), ("M1", m1(y, origin, t))):
            if v is not None:
                rows.append({"issued": issued, "origin": origin, "target": t, "h": str(h), "model": name, "yhat": f"{v:.1f}"})
    return rows


def read_ledger(path=LEDGER):
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def issue(series=SERIES, ledger=LEDGER, today=None):
    y = load_series(series)
    origin = max(y)
    old = read_ledger(ledger)
    if any(r["origin"] == origin for r in old):
        print(f"[예측] 기준월 {origin} 은 이미 냈다 — 덧붙일 것 없음")
        return 0
    kst = today or (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date().isoformat()
    new = forecasts(y, origin, kst)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    fresh = not ledger.exists()
    with open(ledger, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        if fresh:
            w.writeheader()
        w.writerows(new)
    for r in new:
        print(f"[예측] {r['origin']} → {r['target']} (h{r['h']}) {r['model']} {r['yhat']} 천TEU")
    return 0


def score(series=SERIES, ledger=LEDGER):
    y = load_series(series)
    rows = [r for r in read_ledger(ledger) if r["target"] in y]
    res = {}
    for r in rows:
        a, f = y[r["target"]], float(r["yhat"])
        d = res.setdefault(r["model"], {"ape": [], "hit": []})
        d["ape"].append(abs(f - a) / a)
        prev = y.get(add_months(r["target"], -12))
        if r["model"] != "B" and prev is not None and a != prev:
            d["hit"].append((f - prev > 0) == (a - prev > 0))
    out = {m: {"n": len(d["ape"]), "mape": sum(d["ape"]) / len(d["ape"]) if d["ape"] else None,
               "direction": (sum(d["hit"]) / len(d["hit"])) if d["hit"] else None} for m, d in res.items()}
    for d in out.values():  # 화면이 쓰는 꼴(소수 첫째 자리 %) — 지면 시험이 글자 그대로 대조한다
        d["mape_pct"] = None if d["mape"] is None else "%.1f" % (d["mape"] * 100)
        d["direction_pct"] = None if d["direction"] is None else "%.0f" % (d["direction"] * 100)
    return out, len(rows)


def selftest():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    s = tmp / "s.csv"
    with open(s, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["기준연월", "터미널", "당월_천TEU"])
        for i in range(24):  # 2024-01~2025-12 : 첫해 100, 둘째 해 110 (성장비 1.1)
            w.writerow([add_months("2024-01", i), "컨테이너 합계", 100 if i < 12 else 110])
            w.writerow([add_months("2024-01", i), "SNCT", 1])
    y = load_series(s)
    assert len(y) == 24 and y["2025-12"] == 110
    assert baseline(y, "2026-01") == 110
    assert abs(m1(y, "2025-12", "2026-01") - 121.0) < 1e-9
    led = tmp / "l.csv"
    issue(s, led, today="2026-01-05")
    rows = read_ledger(led)
    assert [(r["target"], r["model"], r["yhat"]) for r in rows[:2]] == [("2026-01", "B", "110.0"), ("2026-01", "M1", "121.0")]
    assert len(rows) == 6
    issue(s, led, today="2026-01-06")  # 같은 기준월 두 번 = 덧붙이지 않음
    assert len(read_ledger(led)) == 6
    with open(s, "a", encoding="utf-8-sig", newline="") as f:  # 실제값 2026-01 = 115 → 채점
        csv.writer(f).writerow(["2026-01", "컨테이너 합계", 115])
    out, n = score(s, led)
    assert n == 2 and abs(out["B"]["mape"] - 5 / 115) < 1e-9 and abs(out["M1"]["mape"] - 6 / 115) < 1e-9
    assert out["M1"]["direction"] == 1.0 and out["B"]["direction"] is None
    assert add_months("2026-11", 3) == "2027-02" and add_months("2026-01", -12) == "2025-01"
    print("forecast_teu selftest OK (8)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--issue" in sys.argv:
        sys.exit(issue())
    if "--json" in sys.argv:  # 지면 시험이 화면 수치와 대조한다
        import json
        out, n = score()
        print(json.dumps({"matured": n, "models": out}, ensure_ascii=False))
        sys.exit(0)
    if "--score" in sys.argv:
        out, n = score()
        print(f"[채점] 익은 행 {n}개")
        for m, d in sorted(out.items()):
            mape = "—" if d["mape"] is None else "%.1f%%" % (d["mape"] * 100)
            hit = "해당 없음" if d["direction"] is None else "%.0f%%" % (d["direction"] * 100)
            print(f"  {m}: n={d['n']} MAPE={mape} 방향={hit}")
        sys.exit(0)
    print(__doc__)

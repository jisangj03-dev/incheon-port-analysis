"""수입원가 계산기 파생 — data/collected/v3/kcs_fx_weeks.json(관세청 관세환율 · 수입 · 주간) → data/derived/import_cost.json.
지면 첫 화면의 예시(같은 물건 · 지금 주 vs 52주 전)를 여기서 계산해 숫자를 데이터 파일에 둔다(화면 수치 = 데이터 파일).
계산식은 astro/src/lib/import-cost.ts 와 같다(시험이 둘을 맞춘다). 참고용 · 자문 아님.
  python tools-build/v3/fx_derive.py [--selftest]
"""
import json, math, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IN, OUT = os.path.join(ROOT, "data/collected/v3/kcs_fx_weeks.json"), os.path.join(ROOT, "data/derived/import_cost.json")
CUR = ["USD", "CNY", "JPY", "EUR"]
# 예시(지면 첫 화면) — 기본세율 8% 는 많은 공산품의 관세율표 기본세율이지만 품목마다 다르다(지면에 적는다)
EX = {"goods": 10000, "freight": 0, "insurance": 0, "incoterm": "CIF", "duty_pct": 8, "vat_pct": 10, "cur": "USD"}


def jsround(x): return math.floor(x + 0.5)


def landed(goods, freight, insurance, incoterm, fx, duty_pct, vat_pct=10, inland=0):
    cif = goods + freight + insurance if incoterm == "FOB" else goods
    cv = jsround(cif * fx); duty = math.floor(cv * duty_pct / 100); vat = math.floor((cv + duty) * vat_pct / 100)
    return {"customs_value": cv, "duty": duty, "vat": vat, "landed": cv + duty + vat + inland}


def derive(src):
    W = src["weeks"]
    AGO = 52  # 견줄 주 = 52주 전(1년 전 같은 무렵)
    now, ago = W[-1], W[-1 - AGO] if len(W) > AGO else W[0]
    a = landed(EX["goods"], 0, 0, "CIF", ago["USD"], EX["duty_pct"]); b = landed(EX["goods"], 0, 0, "CIF", now["USD"], EX["duty_pct"])
    hi = max(W, key=lambda w: w["USD"]); lo = min(W, key=lambda w: w["USD"])
    return {"_설명": "관세청 관세환율(수입 · 주간 · 원/통화 1단위, JPY 는 1엔) + 첫 화면 예시 계산(1만 달러 CIF · 관세 8% · 부가세 10%). 참고용 · 자문 아님.",
            "source": src["source"], "fetched": src["fetched"], "asof": now["from"], "currencies": CUR,
            "weeks": [[w["from"]] + [w.get(c) for c in CUR] for w in W],
            "example": {**EX, "ago_weeks": AGO, "now": {"week": now["from"], "fx": now["USD"], **b}, "ago": {"week": ago["from"], "fx": ago["USD"], **a},
                        "diff": b["landed"] - a["landed"], "pct": round(100 * (b["landed"] - a["landed"]) / a["landed"], 1)},
            "usd_hi": {"week": hi["from"], "fx": hi["USD"]}, "usd_lo": {"week": lo["from"], "fx": lo["USD"]}}


def main():
    d = derive(json.load(open(IN, encoding="utf-8")))
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    e = d["example"]; print(f"{d['asof']} 기준 · 1만 달러 CIF 원가 {e['now']['landed']:,}원 · 52주 전 {e['ago']['landed']:,}원 · {e['diff']:+,}원({e['pct']:+}%) → {OUT}")
    return 0


def selftest():
    r = landed(10000, 0, 0, "CIF", 1347.03, 8)
    assert r["customs_value"] == 13470300 and r["duty"] == 1077624 and r["vat"] == 1454792 and r["landed"] == 16002716, r
    f = landed(9000, 800, 200, "FOB", 1300, 0)
    assert f["customs_value"] == 13000000 and f["vat"] == 1300000, f
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

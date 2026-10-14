"""품목 트리맵 레이스 파생 — data/collected/v3/sido_item_years.json(관세청 시도별 품목별 · 인천 · 연도별) → data/derived/trade_race.json.
금액 = 백만 달러(원천 천 달러 ÷ 1000 · 소수 1자리). 끝 해가 12월까지 안 찼으면 partial 로 표시(지면이 「1~○월」로 적는다).
  python tools-build/v3/race_derive.py [--selftest]
"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IN, OUT = os.path.join(ROOT, "data/collected/v3/sido_item_years.json"), os.path.join(ROOT, "data/derived/trade_race.json")


def num(s):
    s = str(s or "").replace(",", "").strip()
    try: return float(s)
    except ValueError: return 0.0


def derive(src):
    years = []
    for y, rec in sorted(src["years"].items()):
        rows = [r for r in rec.get("rows", []) if re.fullmatch(r"\d{2}", str(r.get("hsSgn", "")).strip())]
        if not rows: continue
        agg = {}
        for r in rows:
            hs = r["hsSgn"].strip()
            a = agg.setdefault(hs, {"hs": hs, "name": r.get("korePrlstNm", "").strip(), "exp": 0.0, "imp": 0.0})
            a["exp"] += num(r.get("expUsdAmt")); a["imp"] += num(r.get("impUsdAmt"))
        items = [{**a, "exp": round(a["exp"] / 1000, 1), "imp": round(a["imp"] / 1000, 1)} for a in agg.values()]
        thr = rec.get("through", f"{y}12")
        years.append({"y": y, "through": thr, "partial": not thr.endswith("12"),
                      "exp_total": round(sum(i["exp"] for i in items), 1), "imp_total": round(sum(i["imp"] for i in items), 1),
                      "items": sorted(items, key=lambda i: -(i["exp"] + i["imp"]))})
    return {"_설명": "인천 소재 기업의 품목별(HS 2단위) 수출입 — 연도별. 통관 항구가 아니라 사업장 주소(시도) 기준이다.",
            "source": src.get("source"), "fetched": src.get("fetched"), "unit": "백만 달러", "years": years}


def main():
    d = derive(json.load(open(IN, encoding="utf-8")))
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(d['years'])}해 · {d['years'][0]['y']}~{d['years'][-1]['y']} → {OUT}")
    return 0


def selftest():
    s = {"years": {"2020": {"through": "202012", "rows": [{"priodTitle": "총계", "hsSgn": "", "expUsdAmt": "9", "impUsdAmt": "9"},
                                                         {"priodTitle": "2020", "hsSgn": "85", "korePrlstNm": "전기기기", "expUsdAmt": "1,500", "impUsdAmt": "2,000"},
                                                         {"priodTitle": "2020", "hsSgn": "84", "korePrlstNm": "기계", "expUsdAmt": "500", "impUsdAmt": "0"}]},
                   "2021": {"through": "202108", "rows": [{"hsSgn": "85", "korePrlstNm": "전기기기", "expUsdAmt": "100", "impUsdAmt": "100"}]}}}
    d = derive(s)
    assert d["years"][0]["exp_total"] == 2.0 and d["years"][0]["items"][0]["hs"] == "85", d
    assert d["years"][1]["partial"] and not d["years"][0]["partial"]
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

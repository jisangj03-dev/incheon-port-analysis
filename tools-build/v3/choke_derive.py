"""초크포인트 충격 파생 — PortWatch 초크포인트 일별 통항 × 관세청 국가별(전국 · 최근 12달) → data/derived/chokepoints.json.
경유 표·가정은 선커밋 문서 §5 그대로(여기서 바꾸지 않는다). 인천×나라 원천이 없어 전국 기준이다(지면에 적는다).
  python tools-build/v3/choke_derive.py [--selftest]
"""
import datetime, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CK, NM = os.path.join(ROOT, "data/collected/v3/portwatch_chokepoints.json"), os.path.join(ROOT, "data/collected/v3/nation_months.json")
HF, OUT = os.path.join(ROOT, "data/derived/home_flows.json"), os.path.join(ROOT, "data/derived/chokepoints.json")
EU = "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split()
HORMUZ = "SA AE QA KW IQ IR BH".split()
REDSEA = EU + "GB NO CH IS EG IL TR MA DZ TN LY JO".split()
MALACCA = HORMUZ + REDSEA + "IN PK BD LK MM ZA KE TZ MZ NG GH CI AO BR AR UY".split()
SCS = MALACCA + "VN TH MY SG ID KH HK TW PH".split()
POINTS = [  # (id, PortWatch 이름, 한국어, 지나는 나라)
    ("hormuz", "Strait of Hormuz", "호르무즈 해협", HORMUZ),
    ("redsea", "Bab el-Mandeb Strait", "바브엘만데브(홍해)", REDSEA),
    ("malacca", "Malacca Strait", "믈라카 해협", MALACCA),
    ("taiwan", "Taiwan Strait", "대만해협(남중국해)", SCS),
]


def weekly(rows, key="n_total"):
    """일별 → 주(월요일 시작) 평균 · 날짜 오름차순"""
    by = {}
    for r in rows:
        d = datetime.date.fromisoformat(str(r["date"])[:10]); w = d - datetime.timedelta(days=d.weekday())
        by.setdefault(w.isoformat(), []).append(float(r.get(key) or 0))
    return [[w, round(sum(v) / len(v), 1)] for w, v in sorted(by.items()) if len(v) >= 5]


def derive(ck, nm, hf):
    months = sorted(nm["months"]); tot = {}
    for ym in months:
        for r in nm["months"][ym]:
            t = tot.setdefault(r["c"], {"c": r["c"], "name": r["name"], "exp": 0.0, "imp": 0.0}); t["exp"] += r["exp"]; t["imp"] += r["imp"]
    E = sum(t["exp"] for t in tot.values()) or 1; I = sum(t["imp"] for t in tot.values()) or 1
    pts = []
    for pid, pw, ko, cs in POINTS:
        rows = (ck.get("chokepoints") or {}).get(pw, [])
        wk = weekly(rows)
        # 「평소」 = 2023 년 같은 달 평균(사태 전 · §5) — 2023 자료가 없으면 비워 둔다
        base_m = {}
        for r in rows:
            d = str(r["date"])[:10]
            if d.startswith("2023-"): base_m.setdefault(d[5:7], []).append(float(r.get("n_total") or 0))
        base = {m: round(sum(v) / len(v), 1) for m, v in base_m.items()}
        last28 = [float(r.get("n_total") or 0) for r in rows[-28:]]
        now = round(sum(last28) / len(last28), 1) if last28 else None
        lm = str(rows[-1]["date"])[5:7] if rows else None
        b = base.get(lm) if lm else None
        sel = [tot[c] for c in cs if c in tot]
        se, si = sum(t["exp"] for t in sel), sum(t["imp"] for t in sel)
        top = sorted(sel, key=lambda t: -(t["exp"] + t["imp"]))[:8]
        pts.append({"id": pid, "pw": pw, "ko": ko, "asof": str(rows[-1]["date"])[:10] if rows else None, "weeks": wk,
                    "now28": now, "base_2023_same_month": b, "vs_base_pct": round(100 * (now / b - 1), 1) if (now is not None and b) else None,
                    "countries": len(sel), "exp_musd": round(se / 1e6), "imp_musd": round(si / 1e6),
                    "exp_pct": round(100 * se / E, 1), "imp_pct": round(100 * si / I, 1),
                    "monthly_musd": round((se + si) / len(months) / 1e6),
                    "top": [{"c": t["c"], "name": t["name"], "musd": round((t["exp"] + t["imp"]) / 1e6)} for t in top]})
    last = hf["months"][-1] if hf else None
    return {"_설명": "PortWatch 초크포인트 일별 통항(주 평균) × 관세청 국가별 수출입(전국 · 최근 12달). 경유 표·단순 비례 가정 = 선커밋 §5. 인천만의 몫이 아니다(인천×나라 원천 없음).",
            "source_pw": ck.get("service"), "source_kcs": nm["source"], "fetched": nm["fetched"], "months": [months[0], months[-1]],
            "total_exp_musd": round(E / 1e6), "total_imp_musd": round(I / 1e6),
            "incheon_imp_share_pct": last and last.get("imp_share_pct"), "incheon_ym": last and last.get("ym"), "points": pts}


def main():
    hf = json.load(open(HF, encoding="utf-8")) if os.path.exists(HF) else None
    d = derive(json.load(open(CK, encoding="utf-8")), json.load(open(NM, encoding="utf-8")), hf)
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    for p in d["points"]: print(p["ko"], p["asof"], "주", len(p["weeks"]), "지금", p["now28"], "2023", p["base_2023_same_month"], p["vs_base_pct"], "· 수입", p["imp_pct"], "% 수출", p["exp_pct"], "%")
    return 0


def selftest():
    ck = {"chokepoints": {"Strait of Hormuz": [{"date": f"2023-10-{d:02d}", "n_total": 100} for d in range(1, 29)] + [{"date": f"2024-10-{d:02d}", "n_total": 50} for d in range(1, 29)]}}
    nm = {"source": "t", "fetched": "x", "months": {"202401": [{"c": "SA", "name": "사우디", "exp": 1e6, "imp": 3e6}, {"c": "CN", "name": "중국", "exp": 3e6, "imp": 1e6}]}}
    d = derive(ck, nm, None); h = d["points"][0]
    assert h["vs_base_pct"] == -50.0 and h["imp_pct"] == 75.0 and h["exp_pct"] == 25.0, h
    assert d["points"][1]["weeks"] == [] and d["points"][1]["vs_base_pct"] is None
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

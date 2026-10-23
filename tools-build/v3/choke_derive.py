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
    ("taiwan", "Taiwan Strait", "대만해협", SCS),
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
        # % 는 반올림 전 값으로(5차 사실 대조: 소수 한 자리 값으로 나눠 −64.58 이 −64.5 로 나왔다) · 화면에 싣는 평균만 한 자리
        base_x = {m: sum(v) / len(v) for m, v in base_m.items()}
        base = {m: round(v, 1) for m, v in base_x.items()}
        last28 = [float(r.get("n_total") or 0) for r in rows[-28:]]
        now_x = sum(last28) / len(last28) if last28 else None
        now = round(now_x, 1) if now_x is not None else None
        lm = str(rows[-1]["date"])[5:7] if rows else None
        b = base.get(lm) if lm else None
        bx = base_x.get(lm) if lm else None
        sel = [tot[c] for c in cs if c in tot]
        se, si = sum(t["exp"] for t in sel), sum(t["imp"] for t in sel)
        top = sorted(sel, key=lambda t: -(t["exp"] + t["imp"]))[:8]
        pts.append({"id": pid, "pw": pw, "ko": ko, "asof": str(rows[-1]["date"])[:10] if rows else None, "weeks": wk,
                    "now28": now, "base_2023_same_month": b, "vs_base_pct": round(100 * (now_x / bx - 1), 1) if (now_x is not None and bx) else None,
                    "countries": len(sel), "exp_musd": round(se / 1e6), "imp_musd": round(si / 1e6),
                    "exp_pct": round(100 * se / E, 1), "imp_pct": round(100 * si / I, 1),
                    "monthly_musd": round((se + si) / len(months) / 1e6),
                    "top": [{"c": t["c"], "name": t["name"], "musd": round((t["exp"] + t["imp"]) / 1e6)} for t in top]})
    last = hf["months"][-1] if hf else None
    return {"_설명": "PortWatch 초크포인트 일별 통항(주 평균) × 관세청 국가별 수출입(전국 · 최근 12달). 경유 표·단순 비례 가정. 인천만의 몫이 아니다(인천×나라 원천 없음).",
            "source_pw": ck.get("service"), "source_kcs": nm["source"], "fetched": nm["fetched"], "months": [months[0], months[-1]],
            "total_exp_musd": round(E / 1e6), "total_imp_musd": round(I / 1e6),
            "incheon_imp_share_pct": last and last.get("imp_share_pct"), "incheon_ym": last and last.get("ym"), "points": pts}


# [2026-10-15 P1 ③] 덧붙임 — 경유 규칙 공개 · 우회 거리·일수(choke_detour.json) · 운임 충격(KCCI 실측 · 사태 창) · 품목(HS2) 상위
KC = os.path.join(ROOT, "data/collected/v3/kcci_weeks.json")
DT = os.path.join(ROOT, "data/derived/choke_detour.json")
NI = os.path.join(ROOT, "data/collected/nitemtrade.csv")
HS = os.path.join(ROOT, "data/hs2_short.json")
# 운임 충격 창 — 그 길목이 실제로 막혔던 때만(지금 원천 기간 2022-11~ 안에서는 홍해 사태 하나): 평소 = 2023-11 주 평균(공격 본격화 전) · 충격 = 2024 년 가장 높은 주
# [2026-10-20 사실 대조] 정해 둔 사건이 없는 길목도 통항 자료에서 막힘을 찾는다 — 4주 이상 이어서 2023년 평균의 30% 아래면 그 첫 주가 사건 시작.
#   (호르무즈는 2026-03 부터 하루 30척 아래인데 「막힌 적이 없어 실측이 없다」고 적었다 — 자기 자료와 모순)
AUTO_ROUTES = {"hormuz": ["KMEI"], "malacca": ["KSEI"], "taiwan": ["KCI", "KSEI"]}
def blockage(p, frac=0.3, run=4):
    w = p.get("weeks") or []
    base = [v for d_, v in w if d_.startswith("2023") and v is not None]
    if not base: return None
    lim = frac * sum(base) / len(base)
    for i in range(len(w) - run + 1):
        if all(w[j][1] is not None and w[j][1] < lim for j in range(i, i + run)): return w[i][0], w[-1][0], round(lim, 1)
    return None
SHOCK = {"redsea": {"event": "홍해 사태(2023-12~ · 후티 공격으로 수에즈 우회)", "base": ("2023-11-01", "2023-11-30"), "peak": ("2024-01-01", "2024-12-31"), "routes": ["KNEI", "KMDI"]}}
ROUTE_KO = {"KNEI": "북유럽", "KMDI": "지중해", "KMEI": "중동", "KSEI": "동남아", "KCI": "중국", "KJI": "일본"}


def extras(d):
    kc = json.load(open(KC, encoding="utf-8"))["weeks"] if os.path.exists(KC) else []
    dt = json.load(open(DT, encoding="utf-8")) if os.path.exists(DT) else None
    hsn = json.load(open(HS, encoding="utf-8"))["names"] if os.path.exists(HS) else {}
    rows = []
    if os.path.exists(NI):
        import csv
        rows = [r for r in csv.DictReader(open(NI, encoding="utf-8")) if r["hsCd2"] not in ("-", "")]
    last_ym = max((r["reqYm"] for r in rows), default=None)
    names = {}
    for nm_ in json.load(open(NM, encoding="utf-8"))["months"].values():
        for r in nm_: names[r["c"]] = r["name"]
    rules = dict((pid, cs) for pid, _, _, cs in POINTS)
    for p in d["points"]:
        cs = rules[p["id"]]
        p["rule"] = {"countries": [{"c": c, "name": names.get(c, c)} for c in cs], "basis": "그 나라와의 바닷길이 이 길목을 지난다고 본 것(대표 항로 · 나라 안 항만별 차이와 해협 밖 다른 출구는 무시)"}
        if dt and p["id"] in dt["points"]: p["detour"] = {**dt["points"][p["id"]], "knot": dt["knot"]}
        sh = SHOCK.get(p["id"])
        if not sh and p["id"] in AUTO_ROUTES:
            bl = blockage(p)
            if bl:
                import datetime as _d
                st = _d.date.fromisoformat(bl[0])
                sh = {"event": f"통항 급감({bl[0][:7]}~ · 주 평균 하루 {bl[2]}척 아래 4주 이상 — PortWatch)", "base": ((st - _d.timedelta(weeks=8)).isoformat(), (st - _d.timedelta(days=1)).isoformat()),
                      # 막힘이 원천 마지막 주까지 이어지면 운임은 KCCI 마지막 주까지 본다(통항 원천이 KCCI 보다 늦게 끝나 정점을 놓쳤다 · 2026-10-20 사실 대조)
                      "peak": (bl[0], "9999-12-31" if p.get("asof") and bl[1] >= (_d.date.fromisoformat(p["asof"]) - _d.timedelta(days=14)).isoformat() else bl[1]), "routes": AUTO_ROUTES[p["id"]]}
        if sh and kc:
            out = []
            for r in sh["routes"]:
                b = [w[r] for w in kc if sh["base"][0] <= w["date"] <= sh["base"][1] and w.get(r)]
                k = [w for w in kc if sh["peak"][0] <= w["date"] <= sh["peak"][1] and w.get(r)]
                if b and k:
                    top = max(k, key=lambda w: w[r]); bv = sum(b) / len(b)
                    # % 는 지면에 보이는 두 정수(평소 · 정점)로 잰다 — 반올림 전 값으로 재면 독자가 화면 숫자로 다시 잰 값과 0.1 갈렸다(39차 사실 대조 경미 · 2026-10-23)
                    out.append({"route": r, "ko": ROUTE_KO.get(r, r), "base": round(bv), "peak": round(top[r]), "peak_week": top["date"], "pct": round(100 * (round(top[r]) / round(bv) - 1), 1)})
            # 운임 원천(KCCI)의 마지막 공표 주 — 통항 원천 기준일(asof)보다 늦을 수 있어 지면이 따로 적는다(39차 사실 대조 경미 · 2026-10-23)
            p["shock"] = {"event": sh["event"], "base_window": list(sh["base"]), "routes": out, "kcci_last": max(w["date"] for w in kc)} if out else None
            p["shock_reason"] = None if out else "no_overlap"
        else:
            p["shock"] = None
            p["shock_reason"] = "no_kcci" if sh else "no_event"  # 지면이 칸이 빈 이유를 고른다(2026-10-21)
        if rows and last_ym:
            agg = {}
            for r in rows:
                if r["reqYm"] == last_ym and r["cntyCd"] in cs:
                    agg[r["hsCd2"]] = agg.get(r["hsCd2"], 0) + float(r["expDlr"] or 0) + float(r["impDlr"] or 0)
            tot = sum(agg.values()) or 1
            p["hs_top"] = {"ym": last_ym, "items": [{"hs": h, "name": hsn.get(h, h), "musd": round(v / 1e6), "pct": round(100 * v / tot, 1)} for h, v in sorted(agg.items(), key=lambda kv: -kv[1])[:5]]}
    d["air_note"] = "관세청 국가별 수출입은 항공·해상을 가르지 않는다 — 항공 비중이 큰 품목(반도체 등 85류)이 많은 나라는 바닷길 충격이 부풀려진다. 운송수단별 국가 통계는 아직 싣지 않았다."
    return d


def main():
    hf = json.load(open(HF, encoding="utf-8")) if os.path.exists(HF) else None
    d = extras(derive(json.load(open(CK, encoding="utf-8")), json.load(open(NM, encoding="utf-8")), hf))
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

"""홈 세 축(2026-10-21 선장님 과제 1 「수도권의 물류·무역·유통을 한 번에 아우르는 첫 화면」) — 무역·유통 축 숫자를 만든다.
물류 축(관문 몫 · 컨테이너 · 외항선 · 항공화물)은 지면이 이미 있는 파생 파일(home_flows · terminal long · vessel_replay)에서 바로 읽는다.

입력  data/collected/v3/sudo_trade.json(tools-build/sudo_trade.py · 관세청 시도별 품목별 · 천 달러)
      data/collected/v3/nation_months.json(관세청 국가별 · 달러 — 분모 대조만)
      data/collected/v3/kosis_retail.json(있으면 · 통계청 KOSIS)
출력  data/derived/home_axes.json
  무역 = 수도권(서울·인천·경기) 신고 화주의 수출입이 전국에서 차지하는 몫 · 수도권 수입 상위 품목(HS 2단위).
  유통 = 수도권 화주가 들여온 소비재(아래 CONSUMER 묶음 · 이 사이트가 고른 HS 2단위 목록 — 관세청 분류가 아니다) 금액 · 전년 같은 달 대비.
         KOSIS 키가 들어오면 온라인쇼핑 거래액(전국 · 월)을 같이 싣는다.
분모(전국) = 관세청 국가별 수출입실적의 전 국가 합(같은 달) — 없으면 시도 합. 시도 합과의 차이를 checks 에 남긴다(행정 개편으로 빠진 시도 코드를 드러낸다).
  python tools-build/axes_derive.py [--selftest]
"""
import datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUDO = ("11", "28", "41")
# 소비재 묶음 — 가계가 매장·온라인에서 사는 완제품 위주(원료·중간재 성격이 큰 곡물 10·11 · 유지 15 · 사료 23 · 담배 24 는 뺐다)
CONSUMER = {
    "식품·음료": ["02", "03", "04", "07", "08", "09", "16", "17", "18", "19", "20", "21", "22"],
    "화장품·세제": ["33", "34"],
    "의류·신발·가방": ["42", "61", "62", "63", "64", "65"],
    "가구·완구·잡화": ["94", "95", "96"],
}
CONS_HS = [h for v in CONSUMER.values() for h in v]


def J(rel):
    p = os.path.join(ROOT, rel)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def eok(thousand_usd):
    """천 달러 → 억 달러(소수 한 자리)."""
    return round(thousand_usd / 1e5, 1)


def pct(a, b):
    return round(a / b * 100, 1) if b else None


def yoy(now, before):
    return round((now / before - 1) * 100, 1) if before else None


def ym_dash(s):
    return f"{s[:4]}-{s[4:]}"


def month_view(rec, nat=None):
    """nat = 관세청 국가별 수출입실적 전국 합(천 달러 · 있으면 분모). 시도 코드가 행정 개편으로 바뀌면(2026-07 전남광주 통합 — 29·46 이 빈 응답)
    시도 합이 전국보다 작아진다 — 모든 시도가 답한 달(2025-10~2026-06)에는 두 합이 0.1% 안에서 같았다(2026-10-21 실측)."""
    sudo_imp = sum(rec[c]["tot"]["imp"] for c in SUDO)
    sudo_exp = sum(rec[c]["tot"]["exp"] for c in SUDO)
    sidos = [c for c in rec if c != "nosido" and rec[c].get("tot")]
    sido_imp = sum(rec[c]["tot"]["imp"] for c in sidos)
    sido_exp = sum(rec[c]["tot"]["exp"] for c in sidos)
    nat_imp, nat_exp = (nat if nat else (sido_imp, sido_exp))
    hs = {}
    for c in SUDO:
        for h, v in (rec[c].get("hs") or {}).items():
            x = hs.setdefault(h, {"imp": 0.0, "exp": 0.0, "name": v.get("name", "")})
            x["imp"] += v["imp"]; x["exp"] += v["exp"]
    cons = {g: sum(hs.get(h, {}).get("imp", 0.0) for h in L) for g, L in CONSUMER.items()}
    return {"sudo_imp": sudo_imp, "sudo_exp": sudo_exp, "nat_imp": nat_imp, "nat_exp": nat_exp, "n_sido": len(sidos), "hs": hs, "cons": cons,
            "sido_imp": sido_imp, "denom": "nation" if nat else "sido", "nosido_imp": (rec.get("nosido") or {}).get("tot", {}).get("imp")}


def nation_tot(nation, ym):
    """관세청 국가별 수출입실적 전 국가 합 → (수입, 수출) 천 달러."""
    rows = ((nation or {}).get("months") or {}).get(ym)
    if not rows: return None
    return (sum(r["imp"] for r in rows) / 1000, sum(r["exp"] for r in rows) / 1000)


def derive(st, nation=None, kosis=None):
    months = sorted(st["months"])
    last = months[-1]
    V = {m: month_view(st["months"][m], nation_tot(nation, m)) for m in months}
    L = V[last]
    ly = f"{int(last[:4]) - 1}{last[4:]}"
    P = V.get(ly)
    top = sorted(L["hs"].items(), key=lambda kv: -kv[1]["imp"])[:3]
    cons_now = sum(L["cons"].values())
    cons_ly = sum(P["cons"].values()) if P else None
    # 분모 대조 — 시도 합 ÷ 전국(국가별) − 1 · 모든 시도가 답한 달이면 0 근처, 개편으로 빠진 시도가 있으면 음수
    nat_check = round((L["sido_imp"] / L["nat_imp"] - 1) * 100, 2) if L["denom"] == "nation" and L["nat_imp"] else None
    out = {
        "_설명": "홈 세 축 중 무역·유통 — tools-build/axes_derive.py. 금액 = 억 달러. 시도 = 신고 화주 소재지(관세청 시도별 품목별). 전국 = 관세청 국가별 수출입실적 전 국가 합(없는 달은 시도 합) · denom 에 적는다.",
        "made": datetime.date.today().isoformat(),
        "trade": {
            "ym": ym_dash(last),
            "sudo_imp": eok(L["sudo_imp"]), "sudo_exp": eok(L["sudo_exp"]),
            "nat_imp": eok(L["nat_imp"]), "nat_exp": eok(L["nat_exp"]),
            "imp_pct": pct(L["sudo_imp"], L["nat_imp"]), "exp_pct": pct(L["sudo_exp"], L["nat_exp"]),
            "imp_yoy": yoy(L["sudo_imp"], P["sudo_imp"]) if P else None,
            "by_sido": {st["sudo"][c]: {"imp": eok(st["months"][last][c]["tot"]["imp"]), "exp": eok(st["months"][last][c]["tot"]["exp"])} for c in SUDO},
            "top_imp": [{"hs": h, "name": v["name"], "imp": eok(v["imp"]), "pct": pct(v["imp"], L["sudo_imp"])} for h, v in top],
            "n_sido": L["n_sido"], "denom": L["denom"],
        },
        "retail": {
            "ym": ym_dash(last),
            "cons_imp": eok(cons_now), "cons_imp_ly": eok(cons_ly) if cons_ly is not None else None, "cons_yoy": yoy(cons_now, cons_ly),
            "cons_pct_of_sudo_imp": pct(cons_now, L["sudo_imp"]),
            "groups": [{"name": g, "imp": eok(v), "pct": pct(v, cons_now)} for g, v in sorted(L["cons"].items(), key=lambda kv: -kv[1])],
            "basket": CONSUMER,
        },
        "months": [{"ym": ym_dash(m), "imp_pct": pct(V[m]["sudo_imp"], V[m]["nat_imp"]), "cons_imp": eok(sum(V[m]["cons"].values()))} for m in months],
        "checks": {"sido_sum_vs_nation_pct": nat_check,
                   "nat_vs_nosido_pct": round((L["nat_imp"] / L["nosido_imp"] - 1) * 100, 2) if L.get("nosido_imp") else None},
        "sources": [st.get("source", "")],
    }
    k = kosis_view(kosis)
    if k: out["retail"]["kosis"] = k; out["sources"].append((kosis or {}).get("source", ""))
    return out


def kosis_view(K):
    """KOSIS 온라인쇼핑 거래액(전국 · 월) — 마지막 달과 전년 같은 달."""
    t = ((K or {}).get("tables") or {}).get("online") or {}
    rows = [r for r in (t.get("rows") or []) if r.get("c") in ("합계", "계") or r.get("c", "").startswith("합계")]
    if not rows: return None
    by = {}
    for r in rows: by.setdefault(r["ym"], r)
    last = max(by)
    ly = f"{int(last[:4]) - 1}{last[4:]}"
    now = by[last]["v"]
    return {"ym": ym_dash(last), "online": now, "unit": by[last].get("unit"), "yoy": yoy(now, by[ly]["v"]) if ly in by else None, "tbl": t.get("tbl")}


def main():
    st = J("data/collected/v3/sudo_trade.json")
    if not st or not st.get("months"):
        print("수도권 시도별 원천 없음 — home_axes.json 을 쓰지 않는다(지난 파일 유지)"); return 0
    out = derive(st, J("data/collected/v3/nation_months.json"), J("data/collected/v3/kosis_retail.json"))
    json.dump(out, open(os.path.join(ROOT, "data/derived/home_axes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    t, r = out["trade"], out["retail"]
    print(f"→ home_axes.json {t['ym']} · 수도권 수입 몫 {t['imp_pct']}% · 수출 몫 {t['exp_pct']}% · 소비재 수입 {r['cons_imp']}억 달러({r['cons_yoy']}%) · 시도 {t['n_sido']} · 대조 {out['checks']}")
    return 0


def selftest():
    def rec(imp, exp, hs=None): return {"tot": {"imp": imp, "exp": exp}, **({"hs": hs} if hs is not None else {})}
    hs = {"33": {"imp": 100.0, "exp": 5.0, "name": "화장품"}, "85": {"imp": 900.0, "exp": 50.0, "name": "전기기기"}}
    m = lambda k: {"11": rec(600 * k, 100, hs), "28": rec(200 * k, 100, {}), "41": rec(200 * k, 100, {}), "26": rec(1000, 700)}
    st = {"sudo": {"11": "서울", "28": "인천", "41": "경기"}, "months": {"202509": m(1), "202609": m(1.1)}}
    o = derive(st)
    assert o["trade"]["imp_pct"] == round(1100 / 2100 * 100, 1) and o["trade"]["exp_pct"] == 30.0, o["trade"]
    assert o["trade"]["top_imp"][0]["hs"] == "85" and o["retail"]["cons_imp"] == eok(100) and o["retail"]["cons_yoy"] == 0.0
    assert o["trade"]["imp_yoy"] == 10.0 and o["trade"]["n_sido"] == 4
    N = {"months": {"202609": [{"imp": 1100_000.0 * 2, "exp": 100_000.0}]}}  # 달러 — 전국 수입 2,200(천 달러)
    o2 = derive(st, N)
    assert o2["trade"]["imp_pct"] == 50.0 and o2["trade"]["denom"] == "nation" and o2["checks"]["sido_sum_vs_nation_pct"] == round((2100 / 2200 - 1) * 100, 2), o2["checks"]
    K = {"tables": {"online": {"rows": [{"ym": "202608", "c": "합계", "v": 22.0, "unit": "백만원"}, {"ym": "202508", "c": "합계", "v": 20.0, "unit": "백만원"}]}}}
    assert kosis_view(K)["yoy"] == 10.0 and kosis_view(None) is None
    print("selftest 5/5 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

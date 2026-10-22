"""홈 세 축(2026-10-21 선장님 과제 1 「수도권의 물류·무역·유통을 한 번에 아우르는 첫 화면」) — 무역·유통 축 숫자를 만든다.
물류 축(관문 몫 · 컨테이너 · 외항선 · 항공화물)은 지면이 이미 있는 파생 파일(home_flows · terminal long · vessel_replay)에서 바로 읽는다.

입력  data/collected/v3/sudo_trade.json(tools-build/sudo_trade.py · 관세청 시도별 품목별 · 천 달러)
      data/collected/v3/nation_months.json(관세청 국가별 · 달러 — 분모 대조만)
      data/collected/v3/kosis_retail.json(있으면 · 통계청 KOSIS)
출력  data/derived/home_axes.json
  무역 = 수도권(서울·인천·경기) 신고 화주의 수출입이 전국에서 차지하는 몫 · 수도권 수입 상위 품목(HS 2단위).
  유통 = 수도권 화주가 들여온 소비재(아래 CONSUMER 묶음 · 이 사이트가 고른 HS 2단위 목록 — 관세청 분류가 아니다) 금액 · 전년 같은 달 대비.
         [2026-10-22] KOSIS(retail.kosis)가 있으면 지면 유통 줄은 그것 — 수도권 대형소매점 판매액 · 전국 온라인쇼핑 거래액(kosis_view).
분모(전국) = 관세청 국가별 수출입실적의 전 국가 합(같은 달) — 없으면 시도 합. 시도 합과의 차이를 checks 에 남긴다(행정 개편으로 빠진 시도 코드를 드러낸다).
  python tools-build/axes_derive.py [--selftest]
"""
import datetime, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUDO = ("11", "28", "41")
# 생활소비재 묶음 — 가계가 매장·온라인에서 사는 완제품 위주(원료·중간재 성격이 큰 곡물 10·11 · 유지 15 · 사료 23 · 담배 24 는 뺐다 ·
#   자동차 87 · 의약품 30 · 귀금속 71 · 전기기기 85(반도체·부품이 대부분) 도 뺐다 — 성질별 「소비재」와 다르다 · 지면 방법 칸에 적는다)
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


SUDO_KO = ("서울", "인천", "경기")  # KOSIS 시도 이름 앞머리(서울특별시 · 인천광역시 · 경기도)


def jo(mil):
    """백만 원 → 조 원(소수 한 자리)."""
    return round(mil / 1e6, 1)


def kosis_view(K):
    """[2026-10-22 유통 축 = KOSIS 실측] 수도권(서울·인천·경기) 대형소매점 판매액(경상금액 · 월) + 전국 온라인쇼핑 거래액(월).
    대형소매점 = 백화점 + 대형마트(서울·경기는 원천의 두 내역 합과 같다 · 인천은 내역 칸이 원천에 없다 — 2026-08 실측).
    세 시도가 다 있는 마지막 달만 쓴다(한 시도라도 빠진 달을 수도권 합으로 부르지 않는다). 둘 중 하나라도 없으면 None — 지면은 종전 줄(생활소비재 수입)로 남는다."""
    T = (K or {}).get("tables") or {}
    o = T.get("online") or {}
    orows = {}
    for r in o.get("rows") or []:
        if r.get("c") in ("합계 계", "합계", "계"):  # 판매매체 합(모바일·인터넷 각각이 아니다)
            orows.setdefault(r["ym"], r["v"])
    rs = T.get("retail-sido") or {}
    big = {}
    for r in rs.get("rows") or []:
        if r.get("item", "").startswith("대형소매점"):
            sd = next((k for k in SUDO_KO if r.get("c", "").startswith(k)), None)
            if sd: big.setdefault(r["ym"], {})[sd] = r["v"]
    full = sorted(m for m, v in big.items() if len(v) == len(SUDO_KO))
    if not orows or not full: return None
    lo, lb = max(orows), full[-1]
    ly = lambda m: f"{int(m[:4]) - 1}{m[4:]}"
    sb = sum(big[lb].values())
    sb_ly = sum(big[ly(lb)].values()) if ly(lb) in full else None
    return {
        "large": {"ym": ym_dash(lb), "sudo_mil": sb, "sudo_jo": jo(sb), "yoy": yoy(sb, sb_ly) if sb_ly else None,
                  "by_sido_jo": {k: jo(v) for k, v in big[lb].items()}, "tbl": rs.get("tbl"), "tbl_name": rs.get("tbl_name")},
        "online": {"ym": ym_dash(lo), "mil": orows[lo], "jo": jo(orows[lo]), "yoy": yoy(orows[lo], orows.get(ly(lo))) if orows.get(ly(lo)) else None,
                   "tbl": o.get("tbl"), "tbl_name": o.get("tbl_name")},
        "unit": "조 원(경상금액 · 백만 원 원값을 조 원으로)",
        # 신선도 「지면 기준」(refresh.py kosis-retail ours) — 원천 쪽 latest 가 두 표의 최댓값이라 여기도 최댓값.
        #   두 표는 공표일이 다르다(온라인쇼핑 = 달 초 · 대형소매점 = 산업활동동향 달 말) — 최솟값이면 한쪽만 새로 나온 날마다 헛 「갱신 지연」이 뜬다.
        "ym": ym_dash(max(lb, lo)),
    }


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
    big = lambda ym, a: [{"ym": ym, "c": c, "item": "대형소매점 경상금액", "v": v} for c, v in zip(("서울특별시", "인천광역시", "경기도"), a)]
    K = {"tables": {"online": {"rows": [{"ym": "202608", "c": "합계 모바일쇼핑", "v": 9.0e6}, {"ym": "202608", "c": "합계 계", "v": 22.0e6}, {"ym": "202508", "c": "합계 계", "v": 20.0e6}]},
                    "retail-sido": {"rows": big("202608", [2e6, 0.2e6, 1.5e6]) + big("202508", [1.9e6, 0.2e6, 1.4e6]) + big("202609", [2e6, 0.2e6, 0])[:2]}}}
    kv = kosis_view(K)
    assert kv["online"]["jo"] == 22.0 and kv["online"]["yoy"] == 10.0, kv  # 모바일 줄이 앞에 와도 합계 계
    assert kv["large"]["ym"] == "2026-08" and kv["large"]["sudo_jo"] == 3.7 and kv["large"]["yoy"] == round((3.7 / 3.5 - 1) * 100, 1), kv  # 경기가 빠진 2026-09 는 안 쓴다
    assert kosis_view(None) is None and kosis_view({"tables": {"online": K["tables"]["online"]}}) is None
    print("selftest 5/5 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

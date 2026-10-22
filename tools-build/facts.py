"""이름 붙은 핵심 숫자(facts)와 해석 문장 대장(claims)의 지금 상태 — 갱신 무인화 ①②③(2026-10-22 선커밋 docs/측심_갱신무인화_판정기준_선커밋_20261022.md).

  facts  = 홍보 초안·띠 그림·지면이 같이 쓰는 숫자를 **한 곳에서** 데이터 파일로부터 만든다. 초안 틀(content-queue/templates)은 숫자를 적지 않고
           {{gate.imp_share}} 처럼 이름만 부른다(tools-build/drafts.py). 시험 facts.spec 이 「그 값이 지면에 그대로 보이는가」를 댄다.
           (10/22 띠 그림 52분(화물차)·초안 51분(승용차) — 같은 숫자를 두 기준으로 따로 적은 것이 원인이었다.)
  claims = 해석 문장(반대 지표·「대부분」·「절반」·「가장 높은 달」)의 조건. data/claims.json 이 대장(조건 · 갈래별 문장 · 승인 갈래)이고,
           여기서 조건을 데이터로 다시 재 지금 갈래를 낸다. 지금 ≠ 승인이면 --check 가 3 으로 끝난다 — refresh 는 배포 대신 문장 확인 PR 을 연다.

  python tools-build/facts.py            facts.json · claims_state.json 을 쓴다
  python tools-build/facts.py --check    위와 같고, 뒤집힌 해석 문장이 있으면 종료 3(목록 출력)
  python tools-build/facts.py --approve  지금 갈래를 승인 갈래로 옮긴다(refresh 의 문장 확인 PR 만 쓴다 — 사람 결재 = 그 PR 머지)
  python tools-build/facts.py --selftest
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")
REG = os.path.join(ROOT, "data", "claims.json")


def J(rel):
    p = os.path.join(ROOT, rel)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def f1(v): return f"{v:.1f}"
def signed(v): return f"{'−' if v < 0 else '+' if v > 0 else '±'}{abs(v):.1f}"  # 지면과 같은 빼기표(U+2212)
def ym(s): s = str(s); return f"{s[:4]}-{s[-2:]}" if len(s) in (6, 7) else s


def load():
    D = {k: J(f"data/derived/{k}.json") for k in ("home_flows", "home_axes", "import_cost", "chokepoints", "vessel_replay", "trade_race", "reach_slots", "isochrones", "supply_hs85")}
    D["rooms"] = J("data/rooms.json")
    return D


def facts(D):
    """이름 → {v: 초안에 넣는 글자, pages: 그 글자가 그대로 보여야 하는 지면, src: 데이터 파일}."""
    out = {}
    def put(k, v, pages, src, ctx=None):  # ctx = 지면에서 그 값이 놓이는 꼴(「서울시청까지 {v}분」) — 짧은 값이 엉뚱한 자리의 같은 글자로 통과하지 않게(10/22 사실 대조 C4)
        out[k] = {"v": str(v), "pages": pages, "src": src, **({"ctx": ctx} if ctx else {})}
    F = D["home_flows"]; L = F["months"][-1]
    put("gate.ym", ym(L["ym"]), ["/"], "home_flows.json months[-1].ym")
    put("gate.imp_share", f1(L["imp_share_pct"]), ["/"], "home_flows.json imp_share_pct")
    put("gate.exp_share", f1(L["exp_share_pct"]), ["/"], "home_flows.json exp_share_pct")
    put("gate.port_imp", f1(L["port_imp"]), ["/"], "home_flows.json port_imp(억 달러)")
    put("gate.air_imp", f1(L["air_imp"]), ["/"], "home_flows.json air_imp(억 달러)")
    ac = F.get("air_cargo") or {}
    put("air.window", f"{ac['from']}~{ac['through'][-2:]}", ["/"], "home_flows.json air_cargo from~through")
    T = D["home_axes"]["trade"]
    put("sudo.imp_share", f1(T["imp_pct"]), ["/"], "home_axes.json trade.imp_pct")
    E = D["import_cost"]["example"]
    put("cost.goods", f"{E['goods'] // 10000}만" if E["goods"] % 10000 == 0 else f"{E['goods']:,}", ["/tools/import-cost.html"], "import_cost.json example.goods(달러)")
    put("cost.ago_weeks", E["ago_weeks"], ["/tools/import-cost.html"], "import_cost.json example.ago_weeks", "{v}주 전")
    put("cost.pct", signed(E["pct"]), ["/tools/import-cost.html"], "import_cost.json example.pct")
    H = next(p for p in D["chokepoints"]["points"] if p["id"] == "hormuz")
    put("choke.hormuz_imp", f1(H["imp_pct"]), ["/tools/chokepoint.html"], "chokepoints.json hormuz.imp_pct")
    V = D["vessel_replay"]["latest"]
    put("vessel.ym", ym(V["ym"]), ["/map/vessels.html"], "vessel_replay.json latest.ym")
    put("vessel.incheon", V["incheon"], ["/map/vessels.html"], "vessel_replay.json latest.incheon", "{v}척")
    put("vessel.yoy", signed(V["incheon_yoy_pct"]), ["/map/vessels.html"], "vessel_replay.json latest.incheon_yoy_pct")
    Y = [y for y in D["trade_race"]["years"] if not y.get("partial")][-1]
    put("race.year", Y["y"], ["/tools/trade-race.html"], "trade_race.json 마지막 온전한 해", "{v}년")
    put("race.top_name", Y["top_exp"]["name"].split("(")[0], ["/tools/trade-race.html"], "trade_race.json top_exp.name")
    put("race.top_pct", f1(Y["top_exp"]["pct"]), ["/tools/trade-race.html"], "trade_race.json top_exp.pct")
    S, I = D["reach_slots"], D["isochrones"]
    oi = max(0, next((i for i, o in enumerate(I["origins"]) if o["kind"] == "물류단지"), 0))
    put("reach.origin", I["origins"][oi]["name"], ["/tools/delivery-reach.html"], "isochrones.json origins(물류단지)")
    put("reach.slot", S["default"], ["/tools/delivery-reach.html"], "reach_slots.json default", "({v} 시간대)")
    put("reach.seoul_car", S["table"][oi][S["default"]]["car"]["서울시청"], ["/tools/delivery-reach.html"], "reach_slots.json table[물류단지][default].car.서울시청", "승용차로 출발하면 서울시청까지 {v}분")
    R = {r["id"]: len(r.get("items") or []) for r in D["rooms"]["rooms"]}
    put("site.n_tools", R["tools"], ["/"], "rooms.json tools", "실무 도구 {v}개")
    put("site.n_sims", R["sim"], ["/"], "rooms.json sim", "시뮬레이션 {v}개")
    return out


# 해석 문장의 조건 — data/claims.json 의 id 마다 지금 갈래를 고른다. 문장 자체는 대장(사람이 미리 쓴 갈래)과 파생 코드에 있다.
def variants(D):
    F = D["home_flows"]; L = F["months"][-1]
    C = (D["supply_hs85"] or {}).get("counter") or {}
    V = D["vessel_replay"]["latest"]
    SH = [m["imp_share_pct"] for m in F["months"]]
    air = L["air_imp"] / L["imp_total"] if L["imp_total"] else 0
    return {
        "home.sea_counter": "busan" if C.get("busan_pct", 0) > C.get("incheon_port_pct", 0) else ("incheon" if C.get("incheon_port_pct", 0) > C.get("busan_pct", 0) else "same"),
        "home.air_vs_port": "air" if L["air_imp"] > L["port_imp"] else "port",
        "home.top_month": "top" if L["imp_share_pct"] >= max(SH) else "not",
        "vessels.counter": "none" if not (V.get("incheon") and V.get("busan")) else ("much" if V["busan"] >= 2 * V["incheon"] else "more" if V["busan"] > V["incheon"] else "less" if V["incheon"] > V["busan"] else "same"),
        "gate.half": "over" if L["imp_share_pct"] >= 50 else ("near" if L["imp_share_pct"] >= 45 else "under"),
        "gate.air_most": "most" if air >= 0.7 else ("over_half" if air > 0.5 else "sea"),  # 「대부분」 = 70% 이상(10/22 사실 대조 D1 — 60% 는 낮은 경계)
    }


def state(D, reg):
    now = variants(D)
    out = {}
    for c in reg["claims"]:
        v = now.get(c["id"])
        if v is None: raise KeyError(f"대장에 있는 해석 문장 {c['id']} 의 조건이 facts.py 에 없다")
        if v not in c["variants"]: raise KeyError(f"{c['id']}: 지금 갈래 {v!r} 의 문장이 대장에 없다 — 갈래 문장을 먼저 쓴다")
        out[c["id"]] = {"now": v, "approved": c["approved"], "flipped": v != c["approved"]}
    return out


def main():
    if "--selftest" in sys.argv: return selftest()
    D, reg = load(), J("data/claims.json")
    fa, st = facts(D), state(D, reg)
    if "--approve" in sys.argv:
        for c in reg["claims"]:
            if st[c["id"]]["flipped"]: c["approved"] = st[c["id"]]["now"]; print("승인 갈래 →", c["id"], c["approved"])
        json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=1); open(REG, "a", encoding="utf-8").write("\n")
        st = state(D, reg)
    json.dump({"_설명": "이름 붙은 핵심 숫자 — tools-build/facts.py 가 데이터 파일에서 만든다. 초안 틀·시험이 이 값을 쓴다(손으로 적은 숫자 0).", "facts": fa}, open(os.path.join(DER, "facts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"_설명": "해석 문장 지금 갈래 vs 승인 갈래(data/claims.json) — 다르면 배포 대신 문장 확인 PR.", "claims": st}, open(os.path.join(DER, "claims_state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    flipped = [k for k, v in st.items() if v["flipped"]]
    detail = ", ".join(f"{k}: {st[k]['approved']}→{st[k]['now']}" for k in flipped)
    print(f"facts {len(fa)} · 해석 문장 {len(st)} · 뒤집힘 {len(flipped)}" + (f" — {detail}" if flipped else ""))
    return 3 if ("--check" in sys.argv and flipped) else 0


def selftest():
    D = {"home_flows": {"months": [{"ym": "2026-08", "imp_share_pct": 49.0, "air_imp": 2, "port_imp": 1, "imp_total": 3}, {"ym": "2026-09", "imp_share_pct": 50.5, "air_imp": 277.0, "port_imp": 82.0, "imp_total": 359.0}]},
         "supply_hs85": {"counter": {"busan_pct": 19.2, "incheon_port_pct": 11.5}}, "vessel_replay": {"latest": {"incheon": 502, "busan": 1602}}}
    v = variants(D)
    assert v == {"home.sea_counter": "busan", "home.air_vs_port": "air", "home.top_month": "top", "vessels.counter": "much", "gate.half": "over", "gate.air_most": "most"}, v
    D["supply_hs85"]["counter"]["incheon_port_pct"] = 30; D["home_flows"]["months"][-1]["imp_share_pct"] = 48
    v2 = variants(D)
    assert v2["home.sea_counter"] == "incheon" and v2["gate.half"] == "near" and v2["home.top_month"] == "not", v2
    reg = {"claims": [{"id": k, "variants": {x: {} for x in ("busan", "incheon", "same", "air", "port", "top", "not", "much", "more", "less", "none", "over", "near", "under", "most", "over_half", "sea")}, "approved": v[k]} for k in v]}
    st = state(D, reg)
    assert st["home.sea_counter"]["flipped"] and not st["home.air_vs_port"]["flipped"], st
    assert signed(-15.8) == "−15.8" and signed(5.9) == "+5.9" and ym("202609") == "2026-09"
    print("facts selftest OK (4)"); return 0


if __name__ == "__main__":
    sys.exit(main())

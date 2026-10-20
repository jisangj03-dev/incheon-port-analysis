"""공급망 따라가기(정체성 §3-2) — 전기기기(HS 85) 하나가 해외에서 인천을 거쳐 수도권으로 오는 길의 구간별 숫자.

지면이 쓰는 숫자를 원천 파일에서 계산해 data/derived/supply_hs85.json 에 적는다(지면 = 이 파일 · §2-1).
지어낸 값 0 — 원천이 없는 구간은 "data": null 과 이유를 적고, 지면이 「이 구간 데이터 없음」이라고 쓴다(S1).
  python tools-build/supply_derive.py [--selftest]
"""
import csv, datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/supply_hs85.json")
HS = "85"
COUNTRY = {"AU": "호주", "CN": "중국", "DE": "독일", "HK": "홍콩", "IN": "인도", "JP": "일본", "SG": "싱가포르", "TW": "대만", "US": "미국", "VN": "베트남"}


def num(s):
    s = str(s).replace(",", "").strip()
    return int(float(s)) if s not in ("", "-") else 0


def rows(rel):
    return list(csv.DictReader(open(os.path.join(ROOT, rel), encoding="utf-8-sig")))


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def derive():
    # ① 해외 출발 — 관세청 품목별·국가별 수출입(전국 · 수집한 10개국)
    nt = [r for r in rows("data/collected/nitemtrade.csv") if r["hsCd2"] == HS]
    ym = max(r["reqYm"] for r in nt if num(r["impDlr"]) > 0)
    by = sorted(((COUNTRY.get(r["cntyCd"], r["cntyCd"]), num(r["impDlr"])) for r in nt if r["reqYm"] == ym), key=lambda x: -x[1])
    tot = sum(v for _, v in by)
    origin = {"ym": ym, "unit": "백만 달러", "countries": [{"name": n, "musd": round(v / 1e6), "share_pct": pct(v, tot)} for n, v in by],
              "top": by[0][0], "top_share_pct": pct(by[0][1], tot), "n_countries": len(by),
              "scope": "전국 수입 · 수집한 10개국 안의 비중(그 밖의 나라는 이 표에 없다)"}
    # ② 해상 — 인천항 컨테이너(품목을 가르지 않는다)
    tm = [r for r in rows("analysis/terminal_monthly_long.csv") if r["계층"] == "합계" and r["당월_천TEU"]]
    last = tm[-1]
    sea = {"ym": last["기준연월"], "kteu": float(last["당월_천TEU"]), "yoy_pct": float(last["전년대비_당월_%"]) if last["전년대비_당월_%"] else None,
           "scope": "인천항 컨테이너 전체 — 품목을 가르지 않는다"}
    # ③ 통관 — 관세청 항구·공항별 수출입: 전국 수입액 중 각 관문의 비중(반대 지표: 바다로는 부산이 인천항보다 크다)
    from flows_derive import porttrade  # 일회성 파일 + 예약 수집(2026-10-20)
    _, pt = porttrade()
    pym = max(r["reqYymm"] for r in pt)
    agg = {}
    for r in pt:
        if r["reqYymm"] == pym: agg[r["statKor"]] = agg.get(r["statKor"], 0) + num(r["impDlr"])
    total = agg.get("-") or sum(v for k, v in agg.items() if k != "-")
    gate = lambda *names: sum(agg.get(n, 0) for n in names)
    customs = {"ym": pym, "gates": [
        {"name": "인천국제공항", "share_pct": pct(gate("인천국제공항"), total)},
        {"name": "인천항", "share_pct": pct(gate("인천항"), total)},
        {"name": "부산항·부산신항", "share_pct": pct(gate("부산항", "부산신항"), total)},
        {"name": "평택항", "share_pct": pct(gate("평택항"), total)},
    ], "scope": "전 품목 · 수입 신고 금액 기준(관세청 항구·공항별 = 입항지 기준 · 통관 세관 기준이 아니다)"}
    inc, bus = customs["gates"][1]["share_pct"], customs["gates"][2]["share_pct"]
    counter = {"text": f"바다로 들어오는 수입은 부산이 인천항보다 크다", "incheon_port_pct": inc, "busan_pct": bus, "ym": pym}
    # ④ 인천 소재 기업의 전기기기 수입 — 관세청 시도별 품목별(소재지 기준 · 입·출항 관문 기준이 아니다)
    si = rows("data/collected/sido-item-incheon.csv")
    sym = max(r["reqYm"] for r in si)
    hs = next(r for r in si if r["reqYm"] == sym and r["hsSgn"] == HS)
    allr = next(r for r in si if r["reqYm"] == sym and r["priodTitle"] == "총계")
    firms = {"ym": sym, "imp_kusd": num(hs["impUsdAmt"]), "share_of_incheon_imports_pct": pct(num(hs["impUsdAmt"]), num(allr["impUsdAmt"])),
             "item": hs["korePrlstNm"], "scope": "인천광역시에 사업장이 있는 수입자 기준 — 어느 항구로 들어왔는지는 이 표가 말하지 않는다"}
    # ⑤ 보세·물류창고 — 국토교통부 물류창고업 등록현황(인천 · 구별)
    wh = rows("analysis/warehouse_by_gu.csv")
    n_all, n_bond = sum(num(r["개소"]) for r in wh), sum(num(r["개소·관세법"]) for r in wh)
    top_gu = max(wh, key=lambda r: num(r["개소"]))
    warehouse = {"sites": n_all, "bonded_sites": n_bond, "bonded_pct": pct(n_bond, n_all), "top_gu": top_gu["이름"], "top_gu_sites": num(top_gu["개소"]),
                 "scope": "인천에 등록된 물류창고 — 전기기기가 어느 창고에 들어갔는지는 알 수 없다"}
    steps = [
        {"id": "origin", "title": "해외 출발", "data": origin, "source": "kcs-nitemtrade"},
        {"id": "sea", "title": "바다 — 인천항 컨테이너", "data": sea, "source": "mof-incheon-port-stats"},
        {"id": "air", "title": "하늘 — 인천공항 화물", "data": None, "why": "공항 화물을 품목·월로 잰 공개 원천을 아직 출처 대장에 올리지 못했다"},
        {"id": "customs", "title": "통관 — 어느 관문으로 들어오나", "data": customs, "source": "kcs-porttrade"},
        {"id": "firms", "title": "인천 소재 수입자", "data": firms, "source": "kcs-sido-item"},
        {"id": "warehouse", "title": "보세·물류창고", "data": warehouse, "source": "molit-warehouse"},
        {"id": "last", "title": "수도권 소비자까지", "data": None, "why": "창고에서 수도권 매장·집까지의 배송량을 품목별로 잰 공개 원천이 없다"},
    ]
    return {"item": {"hs": HS, "name": "전기기기와 그 부분품"}, "steps": steps, "counter": counter,
            "computed": datetime.date.today().isoformat(), "command": "python tools-build/supply_derive.py",
            "inputs": ["data/collected/nitemtrade.csv", "analysis/terminal_monthly_long.csv", "analysis/porttrade_202412_202607.csv",
                       "data/collected/sido-item-incheon.csv", "analysis/warehouse_by_gu.csv"]}


def main():
    d = derive()
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({s["id"]: (s["data"] is not None) for s in d["steps"]}, ensure_ascii=False), d["counter"])
    return 0


def selftest():
    assert pct(1, 4) == 25.0 and num("1,234") == 1234 and num("-") == 0
    d = derive()
    assert len(d["steps"]) >= 5 and any(s["data"] is None for s in d["steps"]), "구간 5 이상 · 데이터 없음 구간을 숨기지 않는다"
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

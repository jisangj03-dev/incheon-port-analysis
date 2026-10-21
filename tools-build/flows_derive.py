"""홈 「살아 있는 지도」(2026-10-14 선장님 판정 · 채팅 위임 A) — 월 통계를 흐름으로 그리는 데 쓰는 숫자 한 묶음.

지면은 이 파일(data/derived/home_flows.json)만 읽는다(정체성 §2-1). 숫자는 전부 원천에서 계산하고, 원천이 없는 갈래는 **가정**으로 적는다.
  · 관문별 월 수출입액 — 관세청 항구·공항별 수출입실적(analysis/porttrade_*.csv) · 인천항 / 인천국제공항 · 억 달러
  · 나라 비중 — 관세청 품목별 국가별(전국 · 수집한 10개국 · 가장 최근 석 달 합) · 수입·수출 따로
      [가정] 관문별로 나라를 가른 공개 통계가 없다 → 두 관문에 같은 나라 비중을 쓴다
  · 바다 관문 안 갈래 — 인천항 컨테이너 부두군별 처리량(신항·남항·국제여객부두 · 천TEU · 같은 달)
  · 수도권 목적지 — 국토교통부 물류창고업 등록 개소(인천은 구·군별 · 서울·경기는 시·도 합계)
      [가정] 관문을 지난 화물이 창고 개소 비례로 흩어진다 — 실제 목적지 통계가 아니다
  · 자리 — 나라 점은 대표 항만·공항, 목적지는 구청·도청 부근(개략)
  · 길 — 바다 = 해상망 최단 경로(tools-build/sea_routes.py · searoute · Eurostat MARNET) · 하늘 = 대권 · 수도권 = OSM 고속도로 최단 거리.
      계산한 길이지 실제 항적·궤적이 아니다(2026-10-20 · 종전 손으로 찍은 경유점 = 개념선을 걷었다)
  python tools-build/flows_derive.py [--selftest]
"""
import csv, datetime, glob, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/home_flows.json")

# 나라 — 바다 대표 항만(sea 의 첫 점 = 출발) · 하늘 대표 공항. 물길은 data/derived/sea_routes.json(계산) 이 있으면 그것을 쓴다 — 아래 경유점은 그 파일이 없을 때만(옛 개념선).
PARTNERS = {
    "CN": {"name": "중국", "at": "상하이", "sea": [[121.9, 30.9], [123.2, 32.3], [124.6, 34.6], [125.3, 36.2]], "air": [121.80, 31.14]},
    "JP": {"name": "일본", "at": "도쿄", "sea": [[139.8, 35.4], [139.6, 34.6], [137.0, 33.9], [134.5, 33.0], [131.9, 31.3], [130.0, 31.6], [129.4, 33.3], [128.3, 34.2], [126.6, 33.95], [125.4, 34.5], [125.2, 35.8]], "air": [140.39, 35.77]},
    "TW": {"name": "대만", "at": "가오슝", "sea": [[120.2, 22.5], [119.7, 23.6], [120.5, 25.3], [122.3, 28.0], [123.8, 31.5], [124.8, 34.6], [125.3, 36.2]], "air": [121.23, 25.08]},
    "HK": {"name": "홍콩", "at": "홍콩", "sea": [[114.2, 22.2], [115.8, 22.4], [117.6, 23.2], [119.4, 24.4], [120.6, 25.6], [122.3, 28.0], [123.8, 31.5], [124.8, 34.6], [125.3, 36.2]], "air": [113.92, 22.31]},
    "VN": {"name": "베트남", "at": "호찌민", "sea": [[107.0, 10.4], [108.0, 9.8], [109.6, 11.6], [110.6, 15.2], [113.4, 19.4], [116.2, 21.6], [118.6, 23.0], [120.0, 24.3], [120.8, 25.8], [122.3, 28.0], [123.8, 31.5], [124.8, 34.6], [125.3, 36.2]], "air": [106.66, 10.82]},
    "SG": {"name": "싱가포르", "at": "싱가포르", "sea": [[103.85, 1.22], [104.6, 1.5], [105.9, 3.6], [108.4, 8.4], [110.6, 13.0], [111.6, 16.4], [113.4, 19.4], [116.2, 21.6], [118.6, 23.0], [120.0, 24.3], [120.8, 25.8], [122.3, 28.0], [123.8, 31.5], [124.8, 34.6], [125.3, 36.2]], "air": [103.99, 1.36]},
    "IN": {"name": "인도", "at": "뭄바이", "sea": [[72.9, 18.9], [72.3, 15.0], [74.2, 10.0], [76.6, 7.0], [80.6, 5.6], [86.0, 5.6], [94.0, 6.2], [97.6, 5.3], [100.3, 3.2], [102.6, 1.6], [103.85, 1.22], [104.6, 1.5], [105.9, 3.6], [108.4, 8.4], [110.6, 13.0], [111.6, 16.4], [113.4, 19.4], [116.2, 21.6], [118.6, 23.0], [120.0, 24.3], [120.8, 25.8], [122.3, 28.0], [123.8, 31.5], [124.8, 34.6], [125.3, 36.2]], "air": [72.87, 19.09]},
    "AU": {"name": "호주", "at": "시드니", "sea": [[151.3, -33.9], [153.6, -30.0], [155.2, -22.0], [156.4, -11.0], [154.0, -4.0], [148.0, 5.0], [139.0, 16.0], [131.0, 25.0], [127.4, 30.5], [125.6, 33.6], [125.2, 35.8]], "air": [151.18, -33.94]},
    "US": {"name": "미국", "at": "로스앤젤레스", "sea": [[241.7, 33.7], [236.0, 38.0], [222.0, 45.5], [204.0, 50.0], [184.0, 51.2], [168.0, 48.0], [154.0, 42.6], [145.8, 40.6], [141.6, 41.45], [139.2, 40.9], [134.0, 38.4], [131.0, 36.2], [129.5, 34.8], [128.3, 34.2], [126.6, 33.95], [125.4, 34.5], [125.2, 35.8]], "air": [241.59, 33.94]},
    "DE": {"name": "독일", "at": "함부르크", "sea": [[9.9, 53.6], [7.5, 54.1], [3.0, 51.9], [-1.5, 50.2], [-5.6, 48.7], [-9.6, 43.2], [-9.4, 37.2], [-5.6, 35.95], [2.0, 37.4], [11.0, 37.4], [20.0, 34.6], [29.0, 32.0], [32.35, 31.3], [32.55, 29.9], [34.6, 27.4], [38.6, 21.0], [43.3, 12.7], [51.0, 12.4], [65.0, 9.6], [76.6, 7.0], [80.6, 5.6], [86.0, 5.6], [94.0, 6.2], [97.6, 5.3], [100.3, 3.2], [102.6, 1.6], [103.85, 1.22], [104.6, 1.5], [105.9, 3.6], [108.4, 8.4], [110.6, 13.0], [111.6, 16.4], [113.4, 19.4], [116.2, 21.6], [118.6, 23.0], [120.0, 24.3], [120.8, 25.8], [122.3, 28.0], [123.8, 31.5], [124.8, 34.6], [125.3, 36.2]], "air": [8.57, 50.03]},
}
# 바다 관문 마지막 물길(황해 → 부두) · 부두군 이름은 컨테이너 통계의 「부두군」
SEA_GATES = {
    "신항": {"at": [126.632, 37.344], "approach": [[125.9, 37.0], [126.35, 37.18], [126.55, 37.30]]},
    "남항": {"at": [126.607, 37.449], "approach": [[125.9, 37.0], [126.35, 37.2], [126.5, 37.36], [126.57, 37.42]]},
    "국제여객부두": {"at": [126.599, 37.423], "approach": [[125.9, 37.0], [126.35, 37.2], [126.5, 37.36], [126.57, 37.405]]},
}
AIR_GATE = {"id": "인천공항", "at": [126.4696, 37.4634]}
# 목적지 자리(개략) — 인천은 구청·군청 부근 · 서울은 시청 · 경기는 도청(도 전체를 한 점으로). 옹진군(창고 2곳)은 군청이 섬 밖이라 뺐다.
DEST_AT = {
    "제물포구": [126.622, 37.474], "서해구": [126.676, 37.546], "영종구": [126.534, 37.491], "검단구": [126.658, 37.598],
    "연수구": [126.678, 37.410], "남동구": [126.731, 37.447], "미추홀구": [126.650, 37.463], "계양구": [126.738, 37.537],
    "강화군": [126.488, 37.747], "부평구": [126.722, 37.507], "서울특별시": [126.978, 37.566], "경기도": [127.009, 37.289],
}


def num(s):
    s = str(s).replace(",", "").strip()
    return float(s) if s not in ("", "-") else 0.0


def rows(rel):
    return list(csv.DictReader(open(os.path.join(ROOT, rel), encoding="utf-8-sig")))


def eok(usd):
    return round(usd / 1e8, 1)  # 억 달러


def porttrade():
    """관세청 항구·공항별 — 일회성 파일(analysis/porttrade_*.csv) + 예약 수집(data/collected/porttrade.csv · 2026-10-20 추가). 같은 달은 수집 쪽을 쓴다."""
    pfile = sorted(glob.glob(os.path.join(ROOT, "analysis/porttrade_*.csv")))[-1]
    pt = rows(os.path.relpath(pfile, ROOT))
    cp = os.path.join(ROOT, "data/collected/porttrade.csv")
    if os.path.exists(cp):
        new = [dict(r, reqYymm=r.get("reqYm") or r.get("reqYymm")) for r in rows("data/collected/porttrade.csv")]
        got = {r["reqYymm"] for r in new}
        pt = [r for r in pt if r["reqYymm"] not in got] + new
    return pfile, pt


def derive():
    # ① 관문별 월 수출입(관세청 항구·공항별) — 전국 총계 줄(statKor "-")과 같이
    pfile, pt = porttrade()
    agg = {}
    for r in pt:
        k = (r["reqYymm"], r["statKor"])
        if k[1] not in ("인천항", "인천국제공항", "-"): continue
        a = agg.setdefault(k, [0.0, 0.0]); a[0] += num(r["impDlr"]); a[1] += num(r["expDlr"])
    months = sorted({ym for ym, _ in agg})
    # ② 부두군별 컨테이너(같은 달) — 바다 관문 안 갈래
    tm = [r for r in rows("analysis/terminal_monthly_long.csv") if r["계층"] == "부두군" or (r["계층"] == "터미널" and r["터미널"] == "IPT")]
    teu = {}
    for r in tm:
        g = r["부두군"] if r["계층"] == "부두군" else "국제여객부두"
        if r["당월_천TEU"]: teu.setdefault(r["기준연월"].replace("-", ""), {})[g] = float(r["당월_천TEU"])
    M = []
    for ym in months:
        port, air, nat = agg.get((ym, "인천항")), agg.get((ym, "인천국제공항")), agg.get((ym, "-"))
        if not (port and air and nat): continue
        t = teu.get(ym)
        M.append({"ym": f"{ym[:4]}-{ym[4:]}", "port_imp": eok(port[0]), "port_exp": eok(port[1]), "air_imp": eok(air[0]), "air_exp": eok(air[1]),
                  "nat_imp": eok(nat[0]), "nat_exp": eok(nat[1]),
                  "imp_total": eok(port[0] + air[0]), "exp_total": eok(port[1] + air[1]), "total": eok(port[0] + air[0] + port[1] + air[1]),
                  "imp_share_pct": round(100 * (port[0] + air[0]) / nat[0], 1), "exp_share_pct": round(100 * (port[1] + air[1]) / nat[1], 1),
                  "teu": {g: t.get(g) for g in SEA_GATES} if t else None})
    # ③ 나라 비중 — 전국 · 10개국 · 가장 최근 석 달 합(수입·수출 따로)
    nt = [r for r in rows("data/collected/nitemtrade.csv") if r["hsCd2"] == "-"]
    nmp = os.path.join(ROOT, "data/collected/v3/nation_months.json")
    NM = json.load(open(nmp, encoding="utf-8"))["months"] if os.path.exists(nmp) else {}
    both = sorted({r["reqYm"] for r in nt} & set(NM))  # 전국 분모가 있는 달로 맞춘다(없으면 품목 원천의 마지막 석 달)
    nym = both[-3:] if both else sorted({r["reqYm"] for r in nt})[-3:]
    imp, exp = {}, {}
    for r in nt:
        if r["reqYm"] in nym: imp[r["cntyCd"]] = imp.get(r["cntyCd"], 0) + num(r["impDlr"]); exp[r["cntyCd"]] = exp.get(r["cntyCd"], 0) + num(r["expDlr"])
    ti, te = sum(imp.values()), sum(exp.values())
    # [2026-10-20 사실 대조] imp_pct 는 10개국 합을 100 으로 본 몫(흐름 점 나누기용)이다 — 「전국」 몫이 아니다.
    #   전국 몫 = 같은 달 관세청 국가별 수출입(전 국가 · nation_months.json) 합을 분모로 따로 낸다(달이 다 있을 때만)
    nat_ok = all(m in NM for m in nym)
    ni = sum(x["imp"] for m in nym for x in NM[m]) if nat_ok else None
    ne = sum(x["exp"] for m in nym for x in NM[m]) if nat_ok else None
    srp = os.path.join(ROOT, "data/derived/sea_routes.json")
    SR = json.load(open(srp, encoding="utf-8")) if os.path.exists(srp) else None
    partners = []
    for c, p in PARTNERS.items():
        if c not in imp: continue
        sea = SR["routes"][c]["path"] if SR and c in SR.get("routes", {}) else p["sea"]
        partners.append({"id": c, "name": p["name"], "at": p["at"], "sea": sea, "air": p["air"],
                         "imp_pct": round(100 * imp[c] / ti, 1), "exp_pct": round(100 * exp[c] / te, 1),
                         "imp_eok": eok(imp[c] / len(nym)), "exp_eok": eok(exp[c] / len(nym)),
                         "imp_nat_pct": round(100 * imp[c] / ni, 1) if ni else None, "exp_nat_pct": round(100 * exp[c] / ne, 1) if ne else None})
    partners.sort(key=lambda p: -(p["imp_pct"] + p["exp_pct"]))
    # 하늘 아크의 나라 몫 = 인천공항 실측 항공화물(나라별 도착·출발 톤 · 15062056 · 2026-10-15 선장님 승인) — 없으면 관세청 전국 비중(종전 가정)
    ac_path = os.path.join(ROOT, "data/derived/air_cargo.json")
    air = json.load(open(ac_path, encoding="utf-8")) if os.path.exists(ac_path) else None
    if air:
        for p in partners:
            c = air["countries"].get(p["name"])
            if c: p["air_in_pct"], p["air_out_pct"], p["air_in_t"], p["air_out_t"] = c["in_pct"], c["out_pct"], c["in_t"], c["out_t"]
    # ④ 목적지 — 물류창고 등록 개소
    gu = {r["이름"]: int(r["개소"]) for r in rows("analysis/warehouse_by_gu.csv")}
    sido = {}
    for line in open(os.path.join(ROOT, "analysis/warehouse_stats_by_sido.csv"), encoding="utf-8-sig"):
        if line.startswith("#"): continue
        f = line.strip().split(",")
        if f[0] in ("서울특별시", "경기도"): sido[f[0]] = int(f[1])
    dests = [{"id": k, "n": (gu.get(k) if k in gu else sido.get(k)), "lon": v[0], "lat": v[1], "scope": "인천 구·군" if k in gu else "시·도 전체"} for k, v in DEST_AT.items()]
    dests = [d for d in dests if d["n"]]
    last = M[-1]
    # [2026-10-21 자동 갱신] 지면 설명 문장의 「차이」 숫자도 데이터에서 — 손으로 적은 「2억 달러 안팎」「최대 0.8%p」는 달이 바뀌면 틀린다
    #   nat_gap_eok = 같은 원천 「전국」 줄과 관세청 국가별 전 국가 합의 차이 최댓값(억 달러 · 두 원천이 다 있는 달)
    #   teu_yoy_gap_pp = 공표 전년비(%)와 공표 처리량으로 잰 전년비의 차이 최댓값(%p · 수정된 전년 기준 때문에 생긴다)
    gaps = []
    for m in M:
        k = m["ym"].replace("-", "")
        if k in NM:
            gaps += [abs(m["nat_imp"] - eok(sum(x["imp"] for x in NM[k]))), abs(m["nat_exp"] - eok(sum(x["exp"] for x in NM[k])))]
    tl = [r for r in rows("analysis/terminal_monthly_long.csv") if r["계층"] == "합계" and r["당월_천TEU"]]
    tv = {r["기준연월"]: num(r["당월_천TEU"]) for r in tl}
    tg = []
    for r in tl:
        y, mo = int(r["기준연월"][:4]), int(r["기준연월"][5:7]); pv = tv.get(f"{y - 1}-{mo:02d}")
        if pv and r["전년대비_당월_%"]: tg.append(abs(num(r["전년대비_당월_%"]) - (tv[r["기준연월"]] / pv - 1) * 100))
    checks = {"nat_gap_eok": round(max(gaps), 1) if gaps else None, "teu_yoy_gap_pp": round(max(tg), 1) if tg else None}
    return {
        "_설명": "홈 살아 있는 지도 — tools-build/flows_derive.py 가 원천에서 계산한다. 흐름은 월 통계를 그린 것이지 실시간 위치가 아니다.",
        "made": datetime.date.today().isoformat(),
        "unit": "억 달러",
        "months": M, "last": last["ym"],
        "partners": partners, "partner_months": [f"{m[:4]}-{m[4:]}" for m in nym],
        "sea_gates": [{"id": k, "lon": v["at"][0], "lat": v["at"][1], "approach": [] if SR else v["approach"]} for k, v in SEA_GATES.items()],
        "sea_route": SR["tool"] if SR else None,
        "air_gate": {"id": AIR_GATE["id"], "lon": AIR_GATE["at"][0], "lat": AIR_GATE["at"][1]},
        "air_cargo": {"through": air["through"], "from": air["months"][0], "source": air["source"], "total_t": air["total_in_t"] + air["total_out_t"],
                      "shown_pct": round(100 * sum((p.get("air_in_t") or 0) + (p.get("air_out_t") or 0) for p in partners) / (air["total_in_t"] + air["total_out_t"]), 1)} if air else None,
        "dests": dests,
        "checks": checks,
        "assume": [
            "바다 관문은 나라를 가른 공개 통계가 없어 전국 나라 비중(10개국 · 석 달 합)을 썼다. 하늘 관문은 인천공항 실측 항공화물(나라별 도착·출발 톤)로 나눴다.",
            "관문을 지난 화물이 수도권 어디로 가는지는 통계가 없어, 물류창고 등록 개소 비례로 흩었다(인천 구·군 · 서울 · 경기).",
            "나라 점은 대표 항만·공항, 목적지는 구청·도청 부근이다. 바다 길은 해상망 최단 경로(searoute), 하늘 길은 대권, 수도권 길은 OSM 고속도로 최단 거리 — 계산한 길이지 실제 항적이 아니다." if SR else "나라 점은 대표 항만·공항, 목적지는 구청·도청 부근이다. 항로·아크·육상선은 개념선이다.",
        ],
        "sources": ["kcs-porttrade", "kcs-nitemtrade", "mof-incheon-port-stats", "molit-warehouse"] + (["iiac-route-cargo"] if air else []),
        "inputs": [os.path.relpath(pfile, ROOT), "data/collected/nitemtrade.csv", "analysis/terminal_monthly_long.csv", "analysis/warehouse_by_gu.csv", "analysis/warehouse_stats_by_sido.csv"],
    }


def main():
    d = derive()
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    L = d["months"][-1]
    print(f"{d['months'][0]['ym']}~{L['ym']} {len(d['months'])}달 · 나라 {len(d['partners'])} · 목적지 {len(d['dests'])} · 마지막 달 수입 인천 비중 {L['imp_share_pct']}% → {OUT}")
    return 0


def selftest():
    d = derive()
    L = d["months"][-1]
    assert d["months"] and all(m["port_imp"] > 0 and m["air_exp"] > 0 for m in d["months"]), "관문 값이 비었다"
    assert 0 < L["imp_share_pct"] < 100 and 0 < L["exp_share_pct"] < 100
    assert abs(sum(p["imp_pct"] for p in d["partners"]) - 100) < 0.6, "나라 비중 합이 100 이 아니다"
    assert all(p["sea"][-1][0] < 126.2 and p["sea"][-1][1] > 34 for p in d["partners"]), "물길 끝이 황해 밖이다"
    assert all(d_["n"] > 0 for d_ in d["dests"]) and any(d_["id"] == "경기도" for d_ in d["dests"])
    for p in d["partners"]:
        assert all(abs(a[0] - b[0]) < 25 for a, b in zip(p["sea"], p["sea"][1:])), f"{p['id']} 물길이 경도 180° 를 뛰어넘는다"
    print("selftest 6/6 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

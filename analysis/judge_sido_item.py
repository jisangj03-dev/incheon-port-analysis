# -*- coding: utf-8 -*-
"""3번 축 첫 편 판정 — 인천 품목별 수출입(관세청 시도별 품목별) · 기준 I1·I2·I3.

기준 정본 = `docs/인천품목_판정기준_선커밋_20261003.md`(커밋 ebfc838 · 수집 0건 시점). 이 파일은 그 문면을 계산으로 옮길 뿐이다.
입력 = `analysis/incheon_sido_item.csv`(collect_sido_item.py 산출). 출력은 화면과 `analysis/incheon_sido_item_judgement.md`.

  python analysis/judge_sido_item.py
  python analysis/judge_sido_item.py --selftest
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
INP = HERE / "incheon_sido_item.csv"
OUT = HERE / "incheon_sido_item_judgement.md"
# 금액 단위 — 명세는 「달러」라 적지만 **천 달러**다(2026-10-03 검산: 2026-08 시도 총계 15곳 합 92,949,536 ↔ 국가별 수출실적 합 98,282,430,140 달러).
# 판정(I1·I2·I3)은 비율·순위라 단위와 무관하다. 표는 억 달러로 낸다: 천 달러 ÷ 100,000.
TO_EOK = 1e5


def num(s):
    s = (s or "").replace(",", "").strip()
    return float(s) if s else 0.0


def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    months = sorted({r["reqYymm"] for r in rows})
    total = {}   # 달 → (수출, 수입) — 응답의 총계 행
    chap = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))  # 류 → 달 → [수출, 수입]
    names, dropped = {}, []
    for r in rows:
        hs = r["hsSgn"].strip()
        if not hs:
            if r["priodTitle"].strip() == "총계" or r["korePrlstNm"].strip() == "":
                total[r["reqYymm"]] = (num(r["expUsdAmt"]), num(r["impUsdAmt"]))
            else:
                dropped.append(r)
            continue
        if len(hs) < 2 or not hs[:2].isdigit():
            dropped.append(r)
            continue
        c = hs[:2]
        names.setdefault(c, r["korePrlstNm"].strip())
        chap[c][r["reqYymm"]][0] += num(r["expUsdAmt"])
        chap[c][r["reqYymm"]][1] += num(r["impUsdAmt"])
    return months, total, chap, names, dropped


def rank(chap, idx):
    """12개월 합 기준 순위. 동률이면 류 번호가 작은 쪽이 위(선커밋)."""
    sums = {c: sum(v[idx] for v in m.values()) for c, m in chap.items()}
    return sorted(sums.items(), key=lambda kv: (-kv[1], kv[0])), sums


def judge(months, total, chap):
    exp_rank, exp_sum = rank(chap, 0)
    imp_rank, imp_sum = rank(chap, 1)
    E, I = sum(exp_sum.values()), sum(imp_sum.values())
    top3 = exp_rank[:3]
    i1 = sum(v for _, v in top3) / E
    i2 = "87" in [c for c, _ in top3]
    monthly = {}
    for m in months:
        e = sum(chap[c][m][0] for c in chap)
        i = sum(chap[c][m][1] for c in chap)
        monthly[m] = (e, i)
    imp_months = sum(1 for e, i in monthly.values() if i > e)
    n = len(months)
    if n == 12:
        i3 = imp_months >= 9
    elif n == 11:
        i3 = imp_months / n >= 0.75
    else:
        i3 = None  # 둘 이상 빠지면 판정 불가(선커밋)
    return dict(exp_rank=exp_rank, imp_rank=imp_rank, E=E, I=I, top3=top3, i1=i1, i2=i2,
                monthly=monthly, imp_months=imp_months, n=n, i3=i3)


def report(months, total, chap, names, dropped, j):
    pf = lambda b: "PASS" if b else ("판정 불가" if b is None else "FAIL")
    L = [f"# 판정 — 인천 품목별 수출입 I1·I2·I3 (창 {months[0]}~{months[-1]} · {len(months)}개월)", ""]
    L.append(f"- 분모: 류 {len(chap)}개 · 총계 행 {len(total)}개는 빼고 셌다 · 버린 행 {len(dropped)}")
    tot_e = sum(v[0] for v in total.values()); tot_i = sum(v[1] for v in total.values())
    L.append(f"- 검산: 류 합 수출 {j['E']:,.0f} vs 총계 {tot_e:,.0f} (차 {j['E']-tot_e:,.0f}) · 류 합 수입 {j['I']:,.0f} vs 총계 {tot_i:,.0f} (차 {j['I']-tot_i:,.0f}) 천 달러")
    L.append("")
    L.append(f"| 기준 | 값 | 문턱 | 판정 |")
    L.append("|---|---|---|---|")
    t3 = " · ".join(f"{c}류 {names.get(c,'')}" for c, _ in j["top3"])
    L.append(f"| I1 집중 | 상위 3개 류 수출 비중 {j['i1']*100:.1f}% ({t3}) | ≥ 50% | {pf(j['i1'] >= 0.5)} |")
    pos87 = [c for c, _ in j["exp_rank"]].index("87") + 1 if "87" in chap else None
    L.append(f"| I2 차량 | 87류 수출 순위 {pos87}위 | 상위 3 | {pf(j['i2'])} |")
    L.append(f"| I3 방향 | 수입 > 수출인 달 {j['imp_months']} / {j['n']} | ≥ 9 / 12 | {pf(j['i3'])} |")
    L.append("")
    L.append("## 수출 상위 10개 류 (12개월 합)")
    L.append("| 순위 | 류 | 품목 | 수출(억 달러) | 비중 |")
    L.append("|---:|---|---|---:|---:|")
    for k, (c, v) in enumerate(j["exp_rank"][:10], 1):
        L.append(f"| {k} | {c} | {names.get(c,'')} | {v/TO_EOK:,.1f} | {v/j['E']*100:.1f}% |")
    L.append("")
    L.append("## 수입 상위 10개 류 (12개월 합)")
    L.append("| 순위 | 류 | 품목 | 수입(억 달러) | 비중 |")
    L.append("|---:|---|---|---:|---:|")
    for k, (c, v) in enumerate(j["imp_rank"][:10], 1):
        L.append(f"| {k} | {c} | {names.get(c,'')} | {v/TO_EOK:,.1f} | {v/j['I']*100:.1f}% |")
    L.append("")
    L.append("## 달별 합계 (류 합)")
    L.append("| 달 | 수출(억 달러) | 수입(억 달러) | 수입 > 수출 |")
    L.append("|---|---:|---:|:-:|")
    for m in months:
        e, i = j["monthly"][m]
        L.append(f"| {m[:4]}-{m[4:]} | {e/TO_EOK:,.1f} | {i/TO_EOK:,.1f} | {'○' if i > e else ''} |")
    return "\n".join(L) + "\n"


def selftest():
    import tempfile
    p = Path(tempfile.mkdtemp()) / "t.csv"
    hdr = ["reqYymm", "priodTitle", "hsSgn", "korePrlstNm", "expLnCnt", "expUsdAmt", "impLnCnt", "impUsdAmt", "cmtrBlncAmt"]
    rows = []
    for m in [f"2025{k:02d}" for k in range(1, 13)]:
        rows.append([m, "총계", "", "", "", "100", "", "120", ""])
        rows += [[m, m, "87", "차량", "", "40", "", "10", ""], [m, m, "85", "전기", "", "30", "", "50", ""],
                 [m, m, "30", "의약", "", "30", "", "60", ""]]
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(hdr); w.writerows(rows)
    months, total, chap, names, dropped = load(p)
    j = judge(months, total, chap)
    ok = [len(chap) == 3, len(total) == 12, abs(j["i1"] - 1.0) < 1e-9, j["i2"], j["imp_months"] == 12, j["i3"] is True,
          j["exp_rank"][1][0] == "30"]  # 30류·85류 동률 → 번호 작은 30 이 위
    print("selftest", "통과" if all(ok) else f"실패 {ok}")
    return 0 if all(ok) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    months, total, chap, names, dropped = load(INP)
    j = judge(months, total, chap)
    txt = report(months, total, chap, names, dropped, j)
    OUT.write_text(txt, encoding="utf-8")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())

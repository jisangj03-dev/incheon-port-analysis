# -*- coding: utf-8 -*-
"""#10 판정 — 2005~2021 을 **월 단위**로 판정한다. 204개월.

선커밋 = `docs/10_주제검증.md` (커밋 3612443 · W4 문면 정정 3442dfa — 둘 다 값 계산 이전).
**이 스크립트는 그 문서의 기준만 집행한다. 기준을 여기서 만들지 않는다.**

왜 이 편이 있는가. #09 는 17개 연도 중 7개만 판정했다 — 정지 조건 4(Teu 항등식)가
**규격 축**을 보는데 V1~V4 는 TEU 합만 썼기 때문이다. 보수적 배제였고 #09 §3 이
그렇게 적었다. **규격 축을 안 읽으면 그 정지가 없다.** 그것이 이 편이다.

그래서 이 스크립트는 규격 세부 열을 **읽지 않는다.** 그 사실을 인수시험이
**소스(AST 문자열 상수)로 강제**한다 — 「안 쓴다」를 말이 아니라 실행으로 둔다.

이 스크립트가 하는 일: 선커밋 §3 의 W1~W4 와 게이트 6종을 월 단위로 집행하고, 판정 불가를 따로 센다.
닿지 않는 곳: **값이 옳은지는 게이트 1(#09 연도별 표 재현)로만 본다.** 원천의 진위는 안 본다.

**정지선을 집행하지 않는다** — 판정 스크립트이고 발행은 별도다. 그래서 `정지선-집행:` 표지를 안 단다.

    python analysis/judge_10_monthly.py
    python analysis/judge_10_monthly.py --selftest
"""
import csv
import os
import sys
from collections import defaultdict

# 운영자 콘솔(cp949)에서 출력이 터지지 않게 한다. **없으면 통과 문장의
# `—` 하나에 죽고, 죽은 종료코드를 다른 검사기가 판정으로 읽는다**
# (2026-09-02 실측 · `check_generated` 가 그것을 「낡았다」로 읽었다).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "container_2005_2021_direction.csv")

YEARS = tuple(range(2005, 2022))
MONTHS = tuple(range(1, 13))

# GInOut: 1=수입 · 2=수출 · 3=수입환적 · 4=수출환적  (docs/GInOut_코드규명.md [확정])
# ocCt:   1=수출입항(외항) · 2=연안항
IMPORT, EXPORT = "1", "2"
TRANSSHIP = ("3", "4")
OCEAN = "1"

# ── 선커밋 §3 의 하한. 근거 = basis_10_monthly_floor.py (근거 구간 2022~2025) ──
# **버림이다. 반올림이 아니다** — 사고 85.
W2_FLOOR = 3.88     # 근거 구간 월별 최소 3.8855 (2023-12)
W3_FLOOR = 78.3     # 근거 구간 월별 최소 78.3138% (2023-12)

# ── 게이트 1 회귀 앵커: #09 판정결과 §4 의 발행 표 (전체 · 수출 · 수입 · 환적) ──
# 전부 이미 발행된 값이다. 판정 구간의 새 정보를 안 쓴다.
ANCHOR_09 = {
    2005: (209567.0, 165413.00, 44150.00, 4.0),
    2006: (300108.0, 260307.00, 39163.00, 638.0),
    2007: (423399.0, 369203.00, 53170.00, 1026.0),
    2008: (405580.0, 356288.00, 47933.00, 1359.0),
    2009: (325659.0, 270224.00, 54741.00, 694.0),
    2010: (402019.8, 333564.75, 66859.00, 1596.0),
    2011: (394094.0, 348595.00, 44187.00, 1312.0),
    2012: (402545.0, 351110.00, 50718.00, 717.0),
    2013: (453345.0, 381200.25, 70980.75, 1164.0),
    2014: (522013.2, 471306.00, 48337.25, 2370.0),
    2015: (541502.2, 514385.75, 26462.50, 654.0),
    2016: (658586.5, 612620.75, 45816.75, 149.0),
    2017: (832244.5, 778632.00, 50940.00, 2672.5),
    2018: (835959.5, 794298.25, 36702.25, 4959.0),
    2019: (838016.5, 817591.75, 17320.75, 3104.0),
    2020: (935041.2, 912400.25, 16691.00, 5950.0),
    2021: (935085.2, 904624.00, 20296.25, 10165.0),
}


def _num(s):
    s = (s or "").strip()
    return float(s) if s else 0.0


def teu(row):
    """한 행의 TEU. 외국적 + 한국적. **규격 세부는 안 읽는다.**"""
    return _num(row.get("forEmpTeu")) + _num(row.get("korEmpTeu"))


def read_rows(path=SRC):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def aggregate(rows):
    """월별 집계와 조합 출현을 한 번에 낸다.

    반환 (monthly, combos, coastal_rows)
      monthly : {(y,m): {수출,수입,환적,전체}}  — **외항만**
      combos  : {(GInOut, ocCt): set((y,m))}    — **연안 포함** (W4 대상)
    """
    acc = defaultdict(lambda: {"수출": 0.0, "수입": 0.0, "환적": 0.0})
    combos = defaultdict(set)
    coastal = 0
    for r in rows:
        y, m = int((r.get("yyyy") or "0").strip()), int((r.get("mm") or "0").strip())
        g, oc = (r.get("GInOut") or "").strip(), (r.get("ocCt") or "").strip()
        combos[(g, oc)].add((y, m))
        if oc != OCEAN:
            coastal += 1
            continue
        if g == EXPORT:
            acc[(y, m)]["수출"] += teu(r)
        elif g == IMPORT:
            acc[(y, m)]["수입"] += teu(r)
        elif g in TRANSSHIP:
            acc[(y, m)]["환적"] += teu(r)
    monthly = {}
    for k, v in acc.items():
        v = dict(v)
        v["전체"] = v["수출"] + v["수입"] + v["환적"]
        monthly[k] = v
    return monthly, dict(combos), coastal


# ────────────────────────── 게이트 ──────────────────────────

def gate1_anchor(monthly):
    """#09 연도별 표를 월별 집계의 합으로 재현한다."""
    bad = []
    for y in YEARS:
        tot = sum(monthly[(y, m)]["전체"] for m in MONTHS if (y, m) in monthly)
        exp = sum(monthly[(y, m)]["수출"] for m in MONTHS if (y, m) in monthly)
        imp = sum(monthly[(y, m)]["수입"] for m in MONTHS if (y, m) in monthly)
        tra = sum(monthly[(y, m)]["환적"] for m in MONTHS if (y, m) in monthly)
        a_tot, a_exp, a_imp, a_tra = ANCHOR_09[y]
        # 수출·수입·환적은 #09 가 소수 2자리로 실었다 — 값끼리 곧장 댄다.
        for name, got, want in (("수출", exp, a_exp),
                                ("수입", imp, a_imp),
                                ("환적", tra, a_tra)):
            if abs(got - want) > 0.005:
                bad.append("%d %s: 우리 %.2f ≠ #09 %.2f" % (y, name, got, want))
        # **전체는 다르다.** #09 가 소수 **1자리**로 실었고, 참값이 .25 로 끝나는 해가 있다.
        # 허용 오차로 대면 경계(정확히 0.05)에 걸려 부동소수 표현에 따라 결과가 갈린다 —
        # 실제로 그렇게 걸렸다(사고 86). **같은 자리수로 렌더해서 문자열로 댄다.**
        # 「우리 값이 #09 가 인쇄한 그 글자를 내는가」가 이 대조가 묻는 것이다.
        if "%.1f" % tot != "%.1f" % a_tot:
            bad.append("%d 전체: 우리 %.1f ≠ #09 %.1f (원값 %.2f)"
                       % (y, tot, a_tot, tot))
    return bad


def gate2_months(monthly):
    missing = [(y, m) for y in YEARS for m in MONTHS if (y, m) not in monthly]
    return missing


def gate6_schema(rows):
    """태그 집합이 한 종류인가. 다르면 전수 기록한다."""
    sets = defaultdict(int)
    for r in rows:
        sets[tuple(sorted(k for k in r.keys() if k))] += 1
    return sets


# ────────────────────────── 판정 ──────────────────────────

def judge(monthly):
    keys = sorted(k for k in monthly if k[0] in YEARS)
    w1 = {"성립": [], "미성립": [], "불가": []}
    w2 = {"성립": [], "미성립": [], "불가": []}
    w3 = {"성립": [], "미성립": [], "불가": []}
    for k in keys:
        v = monthly[k]
        # W1 — 수출 > 수입. 둘 다 0 이면 비교가 뜻이 없다 → 불가.
        if v["수출"] == 0 and v["수입"] == 0:
            w1["불가"].append(k)
        else:
            (w1["성립"] if v["수출"] > v["수입"] else w1["미성립"]).append(k)
        # W2 — 배율. 분모 0 은 판정 불가 (게이트 4).
        if v["수입"] <= 0:
            w2["불가"].append(k)
        else:
            r = v["수출"] / v["수입"]
            (w2["성립"] if r >= W2_FLOOR else w2["미성립"]).append((k, r))
        # W3 — 수출 비중. 분모 0 은 판정 불가.
        if v["전체"] <= 0:
            w3["불가"].append(k)
        else:
            s = 100.0 * v["수출"] / v["전체"]
            (w3["성립"] if s >= W3_FLOOR else w3["미성립"]).append((k, s))
    return w1, w2, w3


def judge_w4(combos):
    """조합 연속성 — 첫 출현월과 마지막 출현월 사이에 빠진 달이 없는가."""
    order = [(y, m) for y in YEARS for m in MONTHS]
    idx = {k: i for i, k in enumerate(order)}
    breaks = []
    spans = {}
    for combo, months in sorted(combos.items()):
        seen = sorted(m for m in months if m in idx)
        if not seen:
            continue
        first, last = seen[0], seen[-1]
        spans[combo] = (first, last, len(seen))
        want = set(order[idx[first]:idx[last] + 1])
        gaps = sorted(want - set(seen))
        if gaps:
            # 빠진 달과, 그 뒤 처음 돌아온 달
            back = next((k for k in order[idx[gaps[-1]]:] if k in set(seen)), None)
            breaks.append((combo, gaps, back))
    return spans, breaks


def ym(k):
    return "%d-%02d" % k


def main():
    rows = read_rows()
    monthly, combos, coastal = aggregate(rows)

    print("=" * 74)
    print(" #10 판정 — 2005~2021 월 단위 · 외항(ocCt=1) · TEU")
    print(" 선커밋 docs/10_주제검증.md §3  (하한: 배율 %.2f · 비중 %.1f%%)"
          % (W2_FLOOR, W3_FLOOR))
    print("=" * 74)

    # ── 게이트 ──
    print("\n[게이트]")
    schema = gate6_schema(rows)
    missing = gate2_months(monthly)
    anchor_bad = gate1_anchor(monthly)
    stop = False

    print("  1 회귀 앵커(#09 연도별 표 재현) : %s"
          % ("**불일치 %d건 — 정지**" % len(anchor_bad) if anchor_bad
             else "일치 · 17개 연도 × 4항목 = 68칸"))
    for b in anchor_bad[:10]:
        print("      %s" % b)
    print("  2 월 완전성                     : %s"
          % ("**결손 %d개월 — 정지** %s" % (len(missing), [ym(k) for k in missing[:6]])
             if missing else "204/204 개월"))
    print("  3 모집단 분리                   : 연안(ocCt=2) %d행을 합계에서 뺐다" % coastal)
    print("  5 규격 축 미사용                 : 이 스크립트는 규격 세부 열을 안 읽는다"
          " (인수시험이 소스로 강제)")
    print("  6 스키마                        : 태그 집합 %d종 %s"
          % (len(schema), "· 16열" if all(len(s) == 16 for s in schema) else ""))
    if anchor_bad or missing:
        stop = True
        print("\n  **정지 조건 발동. 판정하지 않는다.**")
        return 1

    # ── 판정 ──
    w1, w2, w3 = judge(monthly)
    spans, breaks = judge_w4(combos)

    def verdict(d, key="성립"):
        n_ok, n_no, n_na = len(d["성립"]), len(d["미성립"]), len(d["불가"])
        return n_ok, n_no, n_na, ("PASS" if n_no == 0 else "FAIL")

    print("\n[판정]")
    print("  %-28s %-30s %s" % ("항목", "결과", "판정"))
    print("  " + "-" * 70)

    o, n, na, v = verdict(w1)
    print("  %-28s %-30s **%s**"
          % ("W1 월 방향 지속", "%d/%d 성립 (판정 불가 %d)" % (o, o + n, na), v))
    o2, n2, na2, v2 = verdict(w2)
    print("  %-28s %-30s **%s**"
          % ("W2 월 배율 ≥ %.2f" % W2_FLOOR,
             "%d/%d 성립 (판정 불가 %d)" % (o2, o2 + n2, na2), v2))
    o3, n3, na3, v3 = verdict(w3)
    print("  %-28s %-30s **%s**"
          % ("W3 월 수출비중 ≥ %.1f%%" % W3_FLOOR,
             "%d/%d 성립 (판정 불가 %d)" % (o3, o3 + n3, na3), v3))
    v4 = "PASS" if not breaks else "FAIL"
    print("  %-28s %-30s **%s**"
          % ("W4 조합 연속성", "조합 %d종 · 끊김 %d건" % (len(spans), len(breaks)), v4))

    if w1["미성립"]:
        print("\n  W1 미성립 달 (%d): %s" % (len(w1["미성립"]),
                                          ", ".join(ym(k) for k in w1["미성립"])))
    if w2["미성립"]:
        print("\n  W2 미성립 달 (%d):" % len(w2["미성립"]))
        for k, r in w2["미성립"]:
            print("      %s  배율 %.4f" % (ym(k), r))
    if w3["미성립"]:
        print("\n  W3 미성립 달 (%d):" % len(w3["미성립"]))
        for k, s in w3["미성립"]:
            print("      %s  비중 %.4f%%" % (ym(k), s))
    if w1["불가"] or w2["불가"] or w3["불가"]:
        print("\n  판정 불가 달 — 통과에도 미성립에도 안 넣는다 (사고 26):")
        for lab, d in (("W1", w1), ("W2", w2), ("W3", w3)):
            if d["불가"]:
                print("      %s: %s" % (lab, ", ".join(ym(k) for k in d["불가"])))

    # ── W4 상세 ──
    print("\n[W4 조합별 출현 구간]  (GInOut, ocCt) · 첫 ~ 마지막 · 출현 개월")
    for combo, (f, l, n_) in sorted(spans.items()):
        span = (YEARS.index(l[0]) * 12 + l[1]) - (YEARS.index(f[0]) * 12 + f[1]) + 1
        mark = "" if n_ == span else "   ← 중간 결손 %d개월" % (span - n_)
        print("      %-8s %s ~ %s   %3d개월%s" % (str(combo), ym(f), ym(l), n_, mark))
    for combo, gaps, back in breaks:
        print("      **끊김** %s: 빠진 달 %d개 %s … 돌아온 달 %s"
              % (str(combo), len(gaps), [ym(g) for g in gaps[:6]],
                 ym(back) if back else "—"))

    # ── 참고 통계 ──
    keys = sorted(k for k in monthly if k[0] in YEARS)
    ratios = {k: monthly[k]["수출"] / monthly[k]["수입"]
              for k in keys if monthly[k]["수입"] > 0}
    shares = {k: 100.0 * monthly[k]["수출"] / monthly[k]["전체"]
              for k in keys if monthly[k]["전체"] > 0}
    rmin, rmax = min(ratios, key=ratios.get), max(ratios, key=ratios.get)
    smin, smax = min(shares, key=shares.get), max(shares, key=shares.get)
    print("\n[참고 통계 — 검증 아님. 결론 자리 금지]")
    print("      월별 배율    최소 %.4f (%s)   최대 %.4f (%s)   [검사 %d개월]"
          % (ratios[rmin], ym(rmin), ratios[rmax], ym(rmax), len(ratios)))
    print("      월별 수출비중 최소 %.4f%% (%s)  최대 %.4f%% (%s)  [검사 %d개월]"
          % (shares[smin], ym(smin), shares[smax], ym(smax), len(shares)))
    print("      월별 환적 합  %.1f TEU" % sum(monthly[k]["환적"] for k in keys))

    # **선커밋에 없던 관측이다. 참고이고 판정에 안 쓴다.**
    # W4 가 FAIL 인데 그것이 W1~W3 을 오염시키는지 아닌지는 적어야 한다 —
    # 끊긴 조합 둘이 **연안**이고 W1~W3 은 연안을 뺐으므로 안 섞이지만,
    # 「뺐으니 괜찮다」는 **연안 행에 값이 있었는지 안 보고는 못 하는 말이다.**
    coastal_teu = sum(teu(r) for r in rows if (r.get("ocCt") or "").strip() != OCEAN)
    coastal_nonzero = [r for r in rows
                       if (r.get("ocCt") or "").strip() != OCEAN and teu(r) != 0]
    print("\n[참고 · 선커밋에 없던 관측] 연안(ocCt=2) %d행의 TEU 합 = %.1f · 비영 행 %d개"
          % (coastal, coastal_teu, len(coastal_nonzero)))
    # 2025년 실측(`docs/GInOut_코드규명.md` §3)에서는 연안이 **전 행 0** 이었다.
    # 이 구간은 다르다 — 그러면 **언제까지 값이 있었는지**를 적어야 한다.
    cy = defaultdict(float)
    for r in rows:
        if (r.get("ocCt") or "").strip() != OCEAN:
            cy[int((r.get("yyyy") or "0").strip())] += teu(r)
    live = [y for y in YEARS if cy[y] > 0]
    print("      연안에 값이 있는 연도: %s"
          % (", ".join("%d(%.0f)" % (y, cy[y]) for y in live) if live else "없음"))
    last_nz = max(((int(r["yyyy"]), int(r["mm"])) for r in coastal_nonzero),
                  default=None)
    print("      연안 마지막 비영 달: %s" % (ym(last_nz) if last_nz else "—"))
    print("      **W1~W3 은 연안을 뺀 값이다** — 끊긴 조합 둘도 연안이라 판정에 안 섞였다.")

    print("\n[연도별 성립 수]  (W1 방향 · W2 배율≥%.2f · W3 비중≥%.1f%%) / 12개월"
          % (W2_FLOOR, W3_FLOOR))
    no2 = {k for k, _ in w2["미성립"]}
    no3 = {k for k, _ in w3["미성립"]}
    no1 = set(w1["미성립"])
    print("      %-6s %-6s %-6s %-6s   %s" % ("연도", "W1", "W2", "W3", "그 해 월 배율 최소"))
    for y in YEARS:
        ks = [(y, m) for m in MONTHS]
        c1 = sum(1 for k in ks if k not in no1)
        c2 = sum(1 for k in ks if k not in no2)
        c3 = sum(1 for k in ks if k not in no3)
        ymin = min(ks, key=lambda k: ratios.get(k, float("inf")))
        print("      %-6d %-6s %-6s %-6s   %.4f (%s)"
              % (y, "%d/12" % c1, "%d/12" % c2, "%d/12" % c3,
                 ratios[ymin], ym(ymin)))

    print("\n" + "=" * 74)
    print(" 판정: W1 %s · W2 %s · W3 %s · W4 %s" % (v, v2, v3, v4))
    print(" **선커밋 기준 무수정. FAIL 도 그대로 발행한다**(§3-7).")
    print("=" * 74)
    return 0


# ────────────────────────── 인수시험 ──────────────────────────

def selftest():
    fails = []

    def chk(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))
        print("  %-52s %s" % (label, "OK" if got == want else "FAIL"))

    # ① 규격 축을 안 읽는다는 것을 소스로 강제한다 (선커밋 게이트 5).
    #    독스트링·주석은 그 이름을 설명해야 하므로 뺀다 —
    #    「안 읽는다」고 적는 것 자체가 실패로 잡히면 안 적게 된다.
    import ast
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                docs.add(d)
    lits = [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docs]
    #    찾는 말 자체를 조립해서 만든다 — 통째로 적으면 **이 검사가 자기를 잡는다.**
    tokens = ["Emp" + "_" + n for n in ("10", "20", "40", "99")]
    size_cols = [s for s in lits if any(t in s for t in tokens)]
    chk("규격 세부 열을 코드에서 안 부른다", size_cols, [])

    chk("TEU 는 외국적+한국적", teu({"forEmpTeu": "10.5", "korEmpTeu": "2"}), 12.5)
    chk("빈 칸은 0", teu({"forEmpTeu": "", "korEmpTeu": None}), 0.0)

    def row(y, m, g, oc, f):
        return {"yyyy": str(y), "mm": str(m), "GInOut": g, "ocCt": oc,
                "forEmpTeu": str(f), "korEmpTeu": "0"}

    rows = [row(2005, 1, "2", "1", 800), row(2005, 1, "1", "1", 100),
            row(2005, 1, "3", "1", 60), row(2005, 1, "4", "1", 40),
            row(2005, 1, "2", "2", 9999)]
    monthly, combos, coastal = aggregate(rows)
    chk("연안을 합계에서 뺀다", monthly[(2005, 1)]["수출"], 800.0)
    chk("연안 행수를 센다", coastal, 1)
    chk("환적은 3+4", monthly[(2005, 1)]["환적"], 100.0)
    chk("전체 = 수출+수입+환적", monthly[(2005, 1)]["전체"], 1000.0)
    chk("연안 조합도 W4 대상에 든다", ("2", "2") in combos, True)

    # ② 게이트 2 — 결손을 잡는가
    chk("204개월 중 결손을 센다", len(gate2_months(monthly)), 203)

    # ③ 판정 — 경계에서 어느 쪽으로 가는가
    m = {(2005, 1): {"수출": 388.0, "수입": 100.0, "환적": 0.0, "전체": 488.0},
         (2005, 2): {"수출": 387.0, "수입": 100.0, "환적": 0.0, "전체": 487.0}}
    w1, w2, w3 = judge(m)
    chk("W2 하한 정확히 3.88 은 성립", [k for k, _ in w2["성립"]], [(2005, 1)])
    chk("W2 하한 미만은 미성립", [k for k, _ in w2["미성립"]], [(2005, 2)])

    # 분모 0 — 통과로도 미성립으로도 안 센다
    m0 = {(2005, 1): {"수출": 10.0, "수입": 0.0, "환적": 0.0, "전체": 10.0}}
    w1b, w2b, w3b = judge(m0)
    chk("수입 0 인 달은 W2 판정 불가", (len(w2b["성립"]), len(w2b["미성립"]),
                                 len(w2b["불가"])), (0, 0, 1))
    chk("그 달도 W1 은 판정한다", len(w1b["성립"]), 1)
    mz = {(2005, 1): {"수출": 0.0, "수입": 0.0, "환적": 0.0, "전체": 0.0}}
    w1c, _, w3c = judge(mz)
    chk("수출·수입 다 0 이면 W1 도 판정 불가", len(w1c["불가"]), 1)
    chk("전체 0 이면 W3 판정 불가", len(w3c["불가"]), 1)

    # 방향이 뒤집힌 달을 잡는가 — 이 시험이 없으면 W1 이 늘 PASS 여도 모른다
    mrev = {(2005, 1): {"수출": 10.0, "수입": 90.0, "환적": 0.0, "전체": 100.0}}
    w1d, _, _ = judge(mrev)
    chk("수입이 더 크면 W1 미성립", w1d["미성립"], [(2005, 1)])

    # ④ W4 — 끊김을 잡는가. 안 잡으면 이 항목은 늘 PASS 다
    cont = {("2", "1"): {(2005, 1), (2005, 2), (2005, 3)}}
    _, br = judge_w4(cont)
    chk("연속이면 끊김 없음", br, [])
    gap = {("2", "2"): {(2005, 1), (2005, 3)}}
    spans, br2 = judge_w4(gap)
    chk("중간이 빠지면 끊김 1건", len(br2), 1)
    chk("빠진 달을 집는다", br2[0][1], [(2005, 2)])
    chk("돌아온 달을 집는다", br2[0][2], (2005, 3))
    # 끝에서 사라진 것은 끊김이 아니다 — 그것이 「소멸」이고 W4 대상이 아니다
    gone = {("1", "2"): {(2005, 1), (2005, 2)}}
    _, br3 = judge_w4(gone)
    chk("끝에서 사라진 것은 끊김이 아니다", br3, [])

    # ⑤ 게이트 1 — 어긋나면 잡는가
    fake = {(y, mth): {"수출": 0.0, "수입": 0.0, "환적": 0.0, "전체": 0.0}
            for y in YEARS for mth in MONTHS}
    chk("앵커가 어긋나면 게이트 1 이 발화한다", len(gate1_anchor(fake)) > 0, True)

    # ⑥ 전체는 자리수를 맞춰 대는데, **그 때문에 못 잡게 되면 안 된다**(사고 86).
    #    한 해만 참값으로 채우고 나머지는 0 으로 두어, 그 해에서 오는 지적만 본다.
    def one_year(y, tot, exp, imp, tra):
        m = {(yy, mm): {"수출": 0.0, "수입": 0.0, "환적": 0.0, "전체": 0.0}
             for yy in YEARS for mm in MONTHS}
        m[(y, 1)] = {"수출": exp, "수입": imp, "환적": tra, "전체": tot}
        return [b for b in gate1_anchor(m) if b.startswith(str(y))]

    a = ANCHOR_09[2015]
    chk("참값(.25)이 발행값(.2)과 같은 글자를 내면 통과",
        one_year(2015, 541502.25, a[1], a[2], a[3]), [])
    chk("전체가 실제로 다르면 잡는다",
        len(one_year(2015, 541502.35, a[1], a[2], a[3])), 1)
    # **전체 대조는 소수 1자리까지만 본다.** 0.05 미만의 어긋남은 못 잡는다 —
    # 그래도 되는 이유는 **전체가 파생값**이기 때문이다: 전체 = 수출+수입+환적 이고
    # 그 셋은 0.005 로 댄다. 정밀도를 지는 것은 전체가 아니라 성분 셋이다.
    # **그 문장이 참인지를 여기서 친다** — 참이 아니면 위 관대함이 구멍이 된다.
    chk("전체만 0.05 미만 어긋난 것은 못 잡는다 (파생값이라 허용)",
        len(one_year(2015, 541502.24, a[1], a[2], a[3])), 0)
    chk("대신 성분이 0.01 어긋나면 잡는다",
        len(one_year(2015, 541502.25, a[1] + 0.01, a[2], a[3])), 1)
    chk("환적이 0.01 어긋나도 잡는다",
        len(one_year(2015, 541502.25, a[1], a[2], a[3] + 0.01)), 1)

    print("\n  실패 %d" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

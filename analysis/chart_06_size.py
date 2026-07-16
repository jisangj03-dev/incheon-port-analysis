# -*- coding: utf-8 -*-
"""
#06 공컨테이너 규격×방향 비대칭 (2022~2025, 48개월)

- 진실의 원천: docs/06_주제검증.md §4 선커밋. 게이트 전부 PASS 후에만 V1-2025·V2 집계.
- 규격 구성 비중은 박스 수로만 계산한다 (TEU 금지 — 40ft=2TEU 가중 내재로 순환 논증).
- 파서는 헤더명 기준 (2025 CSV는 컬럼 순서 상이·esbCntcDt 없음).
- 저볼륨 규칙: 분모 0 월 = 미성립 보수 처리 / 월 1,000박스 미만 = 각주 / V2 제외 금지.
- 대조 게이트(X-CHECK): 챗 컨테이너 실행값(2026-07-17)과 로컬 재현 대조. 불일치 시 정지.

실행: cd analysis && python chart_06_size.py
산출물:
  - size_direction_monthly.csv (48개월 판정 표)
  - ../reports/images/size_40ft_monthly_2022_2025.png
  - ../reports/images/size_mix_direction_2022_2025.png
"""
import csv
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Patch

# 폰트: 배포본(윈도우) = Malgun Gothic 고정. 챗 컨테이너 검증 렌더 시에만 Noto 계열 폴백.
_avail = {f.name for f in font_manager.fontManager.ttflist}
for _cand in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"):
    if _cand in _avail:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

TOL = 1e-6
YEARS = (2022, 2023, 2024, 2025)
FILES = {y: f"container_{y}_direction.csv" for y in YEARS}
SIZES = ("10", "20", "40", "99")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def fail(msg):
    print(f"[게이트] FAIL — {msg}")
    print("게이트 실패로 이후 단계를 진행하지 않고 종료합니다.")
    sys.exit(1)


# ---------------------------------------------------------------- 데이터 로드
rows_by_year = {}
for y in YEARS:
    with open(FILES[y], encoding="utf-8-sig") as f:
        rows_by_year[y] = list(csv.DictReader(f))

# ---------------------------------------------------------------- G1 구조
print("== G1 구조 점검 ==")
for y in YEARS:
    rs = rows_by_year[y]
    if not set(r["GInOut"] for r in rs) <= {"1", "2", "3", "4"}:
        fail(f"{y} GInOut 코드 집합 이탈")
    if not set(r["ocCt"] for r in rs) <= {"1", "2"}:
        fail(f"{y} ocCt 코드 집합 이탈")
    oc1 = [r for r in rs if r["ocCt"] == "1"]
    if len(oc1) != 48:
        fail(f"{y} 외항 행수 {len(oc1)} != 48")
    combos = set((int(r["mm"]), r["GInOut"]) for r in oc1)
    if len(combos) != 48:
        fail(f"{y} 외항 월×GInOut 콤보 {len(combos)} != 48 (12개월×4종 미완비)")
    print(f"  {y}: 총 {len(rs)}행 / 외항 48행 / 12개월×GInOut4종 완비 — OK")

# ---------------------------------------------------------------- G2 규격식
print("== G2 규격식 검산 (외항 전 행, 외국적/한국적 각각) ==")
n_checked, max_diff = 0, 0.0
for y in YEARS:
    for r in rows_by_year[y]:
        if r["ocCt"] != "1":
            continue
        for side in ("for", "kor"):
            calc = (0.5 * num(r[f"{side}Emp_10"]) + 1.0 * num(r[f"{side}Emp_20"])
                    + 2.0 * num(r[f"{side}Emp_40"]) + 2.25 * num(r[f"{side}Emp_99"]))
            teu = num(r[f"{side}EmpTeu"])
            d = abs(calc - teu)
            max_diff = max(max_diff, d)
            n_checked += 1
            if d > TOL:
                fail(f"규격식 불일치 {y}-{r['mm']} GInOut={r['GInOut']} {side}: 계산 {calc} vs TEU {teu}")
print(f"  검산 {n_checked}건 / 최대편차 {max_diff} — OK")

# ---------------------------------------------------------------- G3 소수 앵커
print("== G3 소수 앵커 회귀 ==")
teu_dir = {}   # (y, GInOut) -> TEU
for y in YEARS:
    t = defaultdict(float)
    for r in rows_by_year[y]:
        if r["ocCt"] != "1":
            continue
        t[r["GInOut"]] += num(r["forEmpTeu"]) + num(r["korEmpTeu"])
    for g in ("1", "2", "3", "4"):
        teu_dir[(y, g)] = t[g]

year_total = {y: sum(teu_dir[(y, g)] for g in ("1", "2", "3", "4")) for y in YEARS}

# (a) 선커밋 명시 소수 앵커
if abs(year_total[2025] - 991170.0) > TOL:
    fail(f"2025 연간합 {year_total[2025]!r} != 991170.0")
if abs(year_total[2024] - 1044969.5) > TOL:
    fail(f"2024 연간합 {year_total[2024]!r} != 1044969.5")
for g, exp_v, label in (("1", 139418.25, "수입"), ("2", 843837.75, "수출")):
    if abs(teu_dir[(2025, g)] - exp_v) > TOL:
        fail(f"2025 {label} TEU {teu_dir[(2025, g)]!r} != {exp_v}")
if abs((teu_dir[(2025, "3")] + teu_dir[(2025, "4")]) - 7914.0) > TOL:
    fail("2025 환적 TEU != 7914.0")
# (b) 발행 정수 앵커 (2022·2023: 반올림 일치)
for y, pub in ((2022, 873918), (2023, 999990)):
    if round(year_total[y]) != pub:
        fail(f"{y} 연간합 반올림 {round(year_total[y])} != 발행값 {pub}")
# (c) 배율 2자리
for y, exp_r in ((2022, 27.32), (2023, 6.03), (2024, 7.70), (2025, 6.05)):
    r_ = teu_dir[(y, "2")] / teu_dir[(y, "1")]
    if f"{r_:.2f}" != f"{exp_r:.2f}":
        fail(f"{y} 배율 {r_:.4f} → 표기 {r_:.2f} != {exp_r}")
    print(f"  {y}: 연간합 {year_total[y]!r} / 배율 {r_:.2f} — OK")

# ---------------------------------------------------------------- G4 프로브 박스 앵커 (2022~2024, 실재성 근거 재현)
print("== G4 프로브 박스 앵커 재현 (06_주제검증 §3) ==")
ybox = defaultdict(lambda: defaultdict(float))   # (y, GInOut) -> size -> boxes
for y in YEARS:
    for r in rows_by_year[y]:
        if r["ocCt"] != "1":
            continue
        for sz in SIZES:
            ybox[(y, r["GInOut"])][sz] += num(r[f"forEmp_{sz}"]) + num(r[f"korEmp_{sz}"])

PROBE = {  # 06_주제검증 §3 표: (y, g) -> (_10, _20, _40, _99, 40ft% 표기)
    (2022, "1"): (0, 7739, 10932, 57, "58.4"),
    (2022, "2"): (1, 251181, 269981, 9447, "50.9"),
    (2023, "1"): (0, 11665, 64804, 79, "84.7"),
    (2023, "2"): (3, 255602, 285844, 11520, "51.7"),
    (2024, "1"): (0, 5616, 56676, 24, "90.9"),
    (2024, "2"): (0, 262673, 312630, 12908, "53.1"),
}
for (y, g), (e10, e20, e40, e99, eshare) in PROBE.items():
    d = ybox[(y, g)]
    got = tuple(round(d[s]) for s in SIZES)
    if got != (e10, e20, e40, e99):
        fail(f"프로브 박스 불일치 {y} GInOut={g}: {got} != {(e10, e20, e40, e99)}")
    share = 100 * d["40"] / sum(d.values())
    if f"{share:.1f}" != eshare:
        fail(f"프로브 40ft비중 불일치 {y} GInOut={g}: {share:.1f} != {eshare}")
for g, e_tot, e_share, label in (("1", 157592, "84.0", "수입"), ("2", 1671790, "51.9", "수출")):
    tot = sum(sum(ybox[(y, g)].values()) for y in (2022, 2023, 2024))
    t40 = sum(ybox[(y, g)]["40"] for y in (2022, 2023, 2024))
    if round(tot) != e_tot or f"{100 * t40 / tot:.1f}" != e_share:
        fail(f"3개년 {label} 앵커 불일치: {round(tot)}박스/{100 * t40 / tot:.1f}%")
    print(f"  3개년 {label}: {round(tot):,}박스 / 40ft {100 * t40 / tot:.1f}% — OK")

print("✅ 모든 검증 게이트 PASS — 집계 단계로 진행합니다.")

# ================================================================ V1-2025 판정
print()
print("== V1-2025 판정 (연도, 박스 수 기준) ==")
sh = {}
for g in ("1", "2"):
    d = ybox[(2025, g)]
    tot = sum(d.values())
    sh[g] = 100 * d["40"] / tot
    label = "수입" if g == "1" else "수출"
    print(f"  2025 {label}: _10={round(d['10'])} _20={round(d['20']):,} _40={round(d['40']):,} "
          f"_99={round(d['99']):,} / 총 {round(tot):,}박스 / 40ft {sh[g]:.4f}%")
gap25 = sh["1"] - sh["2"]
v1_pass = sh["1"] >= sh["2"] + 5.0
print(f"  격차 {gap25:+.4f}%p / 기준(수입 ≥ 수출+5%p) → {'PASS' if v1_pass else 'FAIL'}")

# ================================================================ V2 판정 (48개월)
print()
print("== V2 판정 (월 단위 48개월) ==")
mbox = defaultdict(lambda: defaultdict(float))   # (y, m, g) -> size -> boxes
for y in YEARS:
    for r in rows_by_year[y]:
        if r["ocCt"] != "1":
            continue
        key = (y, int(r["mm"]), r["GInOut"])
        for sz in SIZES:
            mbox[key][sz] += num(r[f"forEmp_{sz}"]) + num(r[f"korEmp_{sz}"])

monthly = []          # dict rows
n_pass = 0
fail_months, zero_months, low_months = [], [], []
for y in YEARS:
    for m in range(1, 13):
        di, de = mbox[(y, m, "1")], mbox[(y, m, "2")]
        bi, be = sum(di.values()), sum(de.values())
        low = bi < 1000 or be < 1000
        ym = f"{y}-{m:02d}"
        if bi == 0 or be == 0:
            ok, pi, pe, gap = False, None, None, None
            zero_months.append(ym)
        else:
            pi, pe = 100 * di["40"] / bi, 100 * de["40"] / be
            gap = pi - pe
            ok = gap > 0
        if ok:
            n_pass += 1
        else:
            fail_months.append(ym)
        if low:
            low_months.append(ym)
        monthly.append(dict(y=y, m=m, bi=bi, b40i=di["40"], pi=pi,
                            be=be, b40e=de["40"], pe=pe, gap=gap, ok=ok, low=low))

v2_pass = n_pass >= 39
print(f"  성립 {n_pass}/48 (기준 ≥39) → {'PASS' if v2_pass else 'FAIL'}")
print(f"  미성립 월: {fail_months}")
print(f"  분모0 월: {zero_months if zero_months else '없음'} / 저볼륨(<1,000박스) 월: {low_months}")

# ================================================================ X-CHECK 대조 게이트 (챗 2026-07-17 실행값)
print()
print("== X-CHECK 챗-로컬 대조 게이트 ==")
X = dict(
    imp_share_2025="91.1426", exp_share_2025="52.4408",
    imp_boxes_2025=72922, exp_boxes_2025=542456,
    v2_count=42,
    fail_months=["2022-02", "2022-03", "2022-05", "2022-07", "2022-08", "2022-09"],
    zero_months=[], low_months=["2022-08"],
    y2022_dec=873917.5, y2023_dec=999990.25,
)
checks = [
    (f"{sh['1']:.4f}" == X["imp_share_2025"], "2025 수입 40ft 비중"),
    (f"{sh['2']:.4f}" == X["exp_share_2025"], "2025 수출 40ft 비중"),
    (round(sum(ybox[(2025, '1')].values())) == X["imp_boxes_2025"], "2025 수입 총박스"),
    (round(sum(ybox[(2025, '2')].values())) == X["exp_boxes_2025"], "2025 수출 총박스"),
    (n_pass == X["v2_count"], "V2 성립 월수"),
    (fail_months == X["fail_months"], "미성립 월 목록"),
    (zero_months == X["zero_months"], "분모0 월 목록"),
    (low_months == X["low_months"], "저볼륨 월 목록"),
    (abs(year_total[2022] - X["y2022_dec"]) <= TOL, "2022 연간합 소수"),
    (abs(year_total[2023] - X["y2023_dec"]) <= TOL, "2023 연간합 소수"),
]
for ok, name in checks:
    if not ok:
        fail(f"X-CHECK 불일치: {name} — 챗-로컬 재현 실패, 정지")
print("  챗 컨테이너 실행값과 전 항목 일치 — OK")

# ================================================================ 월별 표 CSV
with open("size_direction_monthly.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["연도", "월", "수입_총박스", "수입_40ft박스", "수입_40ft비중_pct",
                "수출_총박스", "수출_40ft박스", "수출_40ft비중_pct", "격차_pp", "성립", "저볼륨"])
    for r in monthly:
        w.writerow([r["y"], r["m"], round(r["bi"]), round(r["b40i"]),
                    "" if r["pi"] is None else f"{r['pi']:.4f}",
                    round(r["be"]), round(r["b40e"]),
                    "" if r["pe"] is None else f"{r['pe']:.4f}",
                    "" if r["gap"] is None else f"{r['gap']:.4f}",
                    "O" if r["ok"] else "X", "저볼륨" if r["low"] else ""])
print("저장: size_direction_monthly.csv (48행)")

# ================================================================ 차트 1 — 월별 40ft 비중
IMG = "../reports/images"
x = list(range(48))
pi_line = [r["pi"] for r in monthly]
pe_line = [r["pe"] for r in monthly]

fig, ax = plt.subplots(figsize=(10, 6))
for i, r in enumerate(monthly):
    if not r["ok"]:
        ax.axvspan(i - 0.5, i + 0.5, color="0.88", zorder=0)
for xb in (11.5, 23.5, 35.5):
    ax.axvline(xb, color="0.6", lw=0.8, ls="--", zorder=1)
ax.plot(x, pi_line, color="#1f6fb4", lw=1.8, marker="o", ms=3, label="수입 방향", zorder=3)
ax.plot(x, pe_line, color="#c44e52", lw=1.8, marker="s", ms=3, label="수출 방향", zorder=3)
ax.set_xticks([0, 12, 24, 36])
ax.set_xticklabels(["2022-01", "2023-01", "2024-01", "2025-01"])
ax.set_ylim(0, 100)
ax.set_ylabel("40ft 비중 (박스 수 기준, %)")
ax.set_title("공컨테이너 40ft 비중 — 수입 vs 수출 방향 (인천항 외항, 2022–2025)")
ax.grid(axis="y", color="0.9", lw=0.7, zorder=0)
handles, labels = ax.get_legend_handles_labels()
handles.append(Patch(facecolor="0.88", label="격차 미성립 월"))
ax.legend(handles=handles, loc="upper left", framealpha=0.95)
fig.tight_layout()
fig.savefig(f"{IMG}/size_40ft_monthly_2022_2025.png", dpi=150)
plt.close(fig)
print(f"저장: {IMG}/size_40ft_monthly_2022_2025.png")

# ================================================================ 차트 2 — 연도×방향 규격 구성
fig, ax = plt.subplots(figsize=(10, 6))
bar_x, bar_labels = [], []
pos = 0.0
series = {"10": [], "20": [], "40": [], "99": []}
for y in YEARS:
    for g, lab in (("1", "수입"), ("2", "수출")):
        d = ybox[(y, g)]
        tot = sum(d.values())
        for sz in SIZES:
            series[sz].append(100 * d[sz] / tot)
        bar_x.append(pos)
        bar_labels.append(f"{y}\n{lab}")
        pos += 1.0
    pos += 0.6
COLORS = {"10": "#e8e8e8", "20": "#a8c6df", "40": "#1f6fb4", "99": "#f0e0b8"}
NAMES = {"10": "10ft", "20": "20ft", "40": "40ft", "99": "기타 규격(_99)"}
bottom = [0.0] * len(bar_x)
for sz in SIZES:
    vals = series[sz]
    ax.bar(bar_x, vals, 0.8, bottom=bottom, color=COLORS[sz],
           label=NAMES[sz], edgecolor="white", lw=0.5, zorder=2)
    if sz == "40":
        for xi, v, b in zip(bar_x, vals, bottom):
            ax.text(xi, b + v / 2, f"{v:.1f}%", ha="center", va="center",
                    color="white", fontsize=9, fontweight="bold")
    bottom = [b + v for b, v in zip(bottom, vals)]
ax.set_xticks(bar_x)
ax.set_xticklabels(bar_labels, fontsize=9)
ax.set_ylim(0, 100)
ax.set_ylabel("박스 구성비 (%)")
ax.set_title("공컨테이너 규격 구성 — 수입 vs 수출 방향 (인천항 외항, 박스 수 기준)")
ax.grid(axis="y", color="0.9", lw=0.7, zorder=0)
# 적층 막대가 전 구간 0~100%를 채우므로 범례는 축 바깥 하단에 배치(겹침 방지 — #05 교훈)
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=4, framealpha=0.95, fontsize=9)
fig.tight_layout()
fig.savefig(f"{IMG}/size_mix_direction_2022_2025.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print(f"저장: {IMG}/size_mix_direction_2022_2025.png")

# ================================================================ 최종 요약
print()
print("== 최종 판정 요약 ==")
print(f"V1-2025: {'PASS' if v1_pass else 'FAIL'} (수입 {sh['1']:.1f}% vs 수출 {sh['2']:.1f}%, 격차 {gap25:+.1f}%p)")
print(f"V2:      {'PASS' if v2_pass else 'FAIL'} ({n_pass}/48, 기준 ≥39)")
if v1_pass and v2_pass:
    print("→ 선커밋 판정: 완전 채택 (4개년 48개월)")
_10_total = sum(ybox[(y, g)]["10"] for y in YEARS for g in ("1", "2", "3", "4"))
print(f"(참고) _10 4개년 전 방향 합계: {round(_10_total)}박스")

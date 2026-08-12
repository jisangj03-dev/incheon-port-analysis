# -*- coding: utf-8 -*-
"""
#07 2026년 상반기 표본외 연장 — 차트 2종 렌더

- 입력: container_2026_direction.csv (2026-01~06) / container_2025_direction.csv (읽기 전용)
- 모집단: 외항(ocCt=1)만. 내항 제외. 환적(GInOut 3·4) 제외.
- 방향: GInOut 1 = 수입 / 2 = 수출
- TEU = forEmpTeu + korEmpTeu / 규격 박스 = forEmp_{n} + korEmp_{n}
- 비중·격차는 반올림 전 값으로 계산하고, 표기 단계에서만 소수 1자리로 자른다.
- 파서는 헤더명 기준. 위치 인덱스 금지.
- 독립 산출: docs/07_판정결과.md를 참조하지 않는다 (X-CHECK 성립 조건).

실행: cd analysis && python chart_07_2026.py
산출물:
  - ../reports/images/size_40ft_monthly_2026.png
  - ../reports/images/direction_yoy_2025_2026.png
"""
import csv
import hashlib
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib import font_manager

# 폰트: 배포본(윈도우) = Malgun Gothic 고정. 없으면 Noto 계열 폴백. (#06 관례)
_avail = {f.name for f in font_manager.fontManager.ttflist}
for _cand in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"):
    if _cand in _avail:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

F2026 = "container_2026_direction.csv"
F2025 = "container_2025_direction.csv"          # 읽기 전용 — 정지선
IMG = "../reports/images"
SIZES = ("10", "20", "40", "99")
MONTHS = tuple(range(1, 7))
C_IMP, C_EXP = "#1f6fb4", "#c44e52"             # 수입 / 수출 (#06 팔레트)
C_IMP_L, C_EXP_L = "#a8c6df", "#e3aeb0"         # 전년(2025) 옅은 톤

CAP_A = (
    "자료: 공공데이터포털 인천항 공컨테이너 물동량 API · 외항(ocCt=1) 기준",
    "비중은 박스 수 기준(TEU 아님). 10·20·40·기타 규격 합을 분모로 한다.",
    "2026년 수치는 잠정치이며 사후 수정될 수 있다. 수집일 2026-08-04.",
    "기타 규격(_99)의 실제 규격은 미확인.",
)
CAP_B = (
    "자료: 공공데이터포털 인천항 공컨테이너 물동량 API · 외항(ocCt=1) 기준",
    "TEU = forEmpTeu + korEmpTeu. 환적(GInOut 3·4)은 제외했다.",
    "2025년은 확정치, 2026년은 잠정치다. 두 값의 성격이 다르다. 수집일 2026-08-04.",
    "잠정치는 사후 수정될 수 있다.",
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def load(path):
    """헤더명 기준 로드 → 외항(ocCt=1) 행만."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    oc1 = [r for r in rows if r["ocCt"].strip() == "1"]
    return rows, oc1


def fmt(v):
    """TEU 표기 — 소수부가 있으면 살리고, 없으면 정수로."""
    return f"{v:,.2f}".rstrip("0").rstrip(".") if v % 1 else f"{v:,.0f}"


def caption(fig, lines, x=0.012, y0=0.105, dy=0.027):
    for i, s in enumerate(lines):
        fig.text(x, y0 - i * dy, s, fontsize=8.5, color="0.35", va="bottom")


# ---------------------------------------------------------------- 정지선 (시작)
h_start = sha256(F2025)
print("== 정지선: 2025 정본 SHA-256 (시작) ==")
print(f"  {F2025}  {h_start}")

# ---------------------------------------------------------------- 로드
rows26, oc26 = load(F2026)
rows25, oc25 = load(F2025)
print()
print("== 로드 행수 ==")
print(f"  {F2026}: 전체 {len(rows26)}행 / 외항(ocCt=1) {len(oc26)}행")
print(f"  {F2025}: 전체 {len(rows25)}행 / 외항(ocCt=1) {len(oc25)}행")

# ---------------------------------------------------------------- 집계
# box[(y, m, g)][sz] = 박스 수  /  teu[(y, m, g)] = TEU
box = defaultdict(lambda: defaultdict(float))
teu = defaultdict(float)
for year, oc in ((2026, oc26), (2025, oc25)):
    for r in oc:
        g = r["GInOut"].strip()
        if g not in ("1", "2"):          # 환적(3·4) 제외
            continue
        key = (year, int(r["mm"]), g)
        for sz in SIZES:
            box[key][sz] += num(r[f"forEmp_{sz}"]) + num(r[f"korEmp_{sz}"])
        teu[key] += num(r["forEmpTeu"]) + num(r["korEmpTeu"])

# ---------------------------------------------------------------- 차트 ⓐ 계산
monthly = []
for m in MONTHS:
    di, de = box[(2026, m, "1")], box[(2026, m, "2")]
    bi, be = sum(di.values()), sum(de.values())
    pi = 100 * di["40"] / bi if bi else None
    pe = 100 * de["40"] / be if be else None
    gap = None if (pi is None or pe is None) else pi - pe
    monthly.append(dict(m=m, b40i=di["40"], bi=bi, pi=pi,
                        b40e=de["40"], be=be, pe=pe, gap=gap,
                        ok=(gap is not None and gap > 0)))

n_ok = sum(1 for r in monthly if r["ok"])
H40I = sum(box[(2026, m, "1")]["40"] for m in MONTHS)
HBOXI = sum(sum(box[(2026, m, "1")].values()) for m in MONTHS)
H40E = sum(box[(2026, m, "2")]["40"] for m in MONTHS)
HBOXE = sum(sum(box[(2026, m, "2")].values()) for m in MONTHS)
share_i_half = 100 * H40I / HBOXI
share_e_half = 100 * H40E / HBOXE
gap_half = share_i_half - share_e_half

print()
print("== 차트 ⓐ 월별 표 (박스 수 기준, 반올림 전 계산) ==")
print(f"  {'월':<8}{'수입40ft':>10}{'수입박스계':>12}{'수입비중':>10}"
      f"{'수출40ft':>10}{'수출박스계':>12}{'수출비중':>10}{'격차':>10}")
for r in monthly:
    print(f"  2026-{r['m']:02d}{round(r['b40i']):>10,}{round(r['bi']):>12,}"
          f"{r['pi']:>9.1f}%{round(r['b40e']):>10,}{round(r['be']):>12,}"
          f"{r['pe']:>9.1f}%{r['gap']:>9.1f}p")
print(f"  반기합산{round(H40I):>10,}{round(HBOXI):>12,}{share_i_half:>9.1f}%"
      f"{round(H40E):>10,}{round(HBOXE):>12,}{share_e_half:>9.1f}%{gap_half:>9.1f}p")
print()
print(f"  합산 격차 = {gap_half:+.1f}%p (반올림 전 {gap_half:.6f}) / 성립 월 = {n_ok}/6")

# ---------------------------------------------------------------- 차트 ⓑ 계산
yoy = {}
for g in ("1", "2"):
    yoy[g] = []
    for m in MONTHS:
        prev, cur = teu[(2025, m, g)], teu[(2026, m, g)]
        yoy[g].append(None if prev == 0 else 100 * (cur - prev) / prev)

half = {(y, g): sum(teu[(y, m, g)] for m in MONTHS) for y in (2025, 2026) for g in ("1", "2")}
ratio = {y: half[(y, "2")] / half[(y, "1")] for y in (2025, 2026)}

print()
print("== 차트 ⓑ 월별 전년 동기 대비 TEU 증감률 ==")
print(f"  {'월':<10}{'수입2025':>12}{'수입2026':>12}{'증감률':>10}"
      f"{'수출2025':>12}{'수출2026':>12}{'증감률':>10}")
for i, m in enumerate(MONTHS):
    ri = "n/a" if yoy["1"][i] is None else f"{yoy['1'][i]:+.1f}%"
    re_ = "n/a" if yoy["2"][i] is None else f"{yoy['2'][i]:+.1f}%"
    print(f"  2026-{m:02d}  {fmt(teu[(2025, m, '1')]):>12}{fmt(teu[(2026, m, '1')]):>12}{ri:>10}"
          f"{fmt(teu[(2025, m, '2')]):>12}{fmt(teu[(2026, m, '2')]):>12}{re_:>10}")

print()
print("== 반기(01~06) 합산 TEU · 배율 ==")
for y in (2025, 2026):
    print(f"  {y}: 수입 {fmt(half[(y, '1')])} / 수출 {fmt(half[(y, '2')])} / 배율 {ratio[y]:.3f}")

# ================================================================ 차트 ⓐ
xs = list(range(len(MONTHS)))
pi_line = [r["pi"] for r in monthly]
pe_line = [r["pe"] for r in monthly]

fig, ax = plt.subplots(figsize=(10, 6))
ax.fill_between(xs, pi_line, pe_line, color=C_IMP, alpha=0.10, zorder=1)
ax.plot(xs, pi_line, color=C_IMP, lw=1.8, marker="o", ms=5, label="수입 40ft 비중", zorder=3)
ax.plot(xs, pe_line, color=C_EXP, lw=1.8, marker="s", ms=5, label="수출 40ft 비중", zorder=3)
for i, r in enumerate(monthly):
    ax.text(i, (r["pi"] + r["pe"]) / 2, f"{r['gap']:+.1f}%p", ha="center", va="center",
            fontsize=9, color="#111", zorder=4,
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white",
                      edgecolor="0.82", lw=0.6, alpha=0.92))
ax.set_xticks(xs)
ax.set_xticklabels([f"2026-{m:02d}" for m in MONTHS])
ax.set_ylim(0, 100)
ax.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
ax.set_ylabel("40ft 비중 (박스 수 기준)")
ax.set_title("2026년 상반기 40ft 박스 비중 — 방향별", fontsize=14, fontweight="bold")
ax.grid(axis="y", color="0.9", lw=0.7, zorder=0)
ax.set_axisbelow(True)
ax.text(0.985, 0.975,
        f"반기 합산 격차 = {gap_half:+.1f}%p\n성립 월 = {n_ok}/6",
        transform=ax.transAxes, ha="right", va="top", fontsize=9.5, color="#111",
        bbox=dict(boxstyle="round,pad=0.42", facecolor="white", edgecolor="0.7",
                  lw=0.8, alpha=0.95), zorder=5)
ax.legend(loc="lower left", framealpha=0.95, fontsize=10)
fig.tight_layout(rect=[0, 0.135, 1, 1])
caption(fig, CAP_A)
out_a = f"{IMG}/size_40ft_monthly_2026.png"
fig.savefig(out_a, dpi=150)
plt.close(fig)

# ================================================================ 차트 ⓑ
fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 6))

# 좌 — 월별 전년 동기 대비 증감률
w = 0.38
vi = [0.0 if v is None else v for v in yoy["1"]]
ve = [0.0 if v is None else v for v in yoy["2"]]
axL.bar([i - w / 2 for i in xs], vi, w, color=C_IMP, label="수입", zorder=2)
axL.bar([i + w / 2 for i in xs], ve, w, color=C_EXP, label="수출", zorder=2)
axL.axhline(0, color="#222", lw=1.8, zorder=3)
span = max([abs(v) for v in vi + ve] + [1.0])
off = span * 0.04
for i in xs:
    for xpos, v, raw in ((i - w / 2, vi[i], yoy["1"][i]), (i + w / 2, ve[i], yoy["2"][i])):
        lab = "n/a" if raw is None else f"{v:+.1f}%"
        axL.text(xpos, v + (off if v >= 0 else -off), lab, ha="center",
                 va="bottom" if v >= 0 else "top", fontsize=8.5, color="#111", zorder=4)
axL.set_xticks(xs)
axL.set_xticklabels([f"{m:02d}월" for m in MONTHS])
axL.set_ylim(min(0, min(vi + ve)) - span * 0.22, max(0, max(vi + ve)) + span * 0.22)
axL.yaxis.set_major_formatter(mtick.PercentFormatter(decimals=0))
axL.set_ylabel("전년 동월 대비 TEU 증감률")
axL.set_title("월별 전년 동기 대비 증감률", fontsize=12.5, fontweight="bold")
axL.grid(axis="y", color="0.9", lw=0.7, zorder=0)
axL.set_axisbelow(True)
axL.legend(loc="best", framealpha=0.95, fontsize=9.5)

# 우 — 반기 합산 TEU
bars = [("수입\n2025", half[(2025, "1")], C_IMP_L), ("수입\n2026", half[(2026, "1")], C_IMP),
        ("수출\n2025", half[(2025, "2")], C_EXP_L), ("수출\n2026", half[(2026, "2")], C_EXP)]
bx = list(range(len(bars)))
axR.bar(bx, [b[1] for b in bars], 0.62, color=[b[2] for b in bars], zorder=2)
top = max(b[1] for b in bars)
for i, (_, v, _c) in enumerate(bars):
    axR.text(i, v + top * 0.015, fmt(v), ha="center", va="bottom",
             fontsize=9.5, fontweight="bold", color="#111", zorder=3)
axR.set_xticks(bx)
axR.set_xticklabels([b[0] for b in bars], fontsize=10)
axR.set_ylim(0, top * 1.28)
axR.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _p: f"{v:,.0f}"))
axR.set_ylabel("TEU")
axR.set_title("반기(01~06) 합산 TEU", fontsize=12.5, fontweight="bold")
axR.grid(axis="y", color="0.9", lw=0.7, zorder=0)
axR.set_axisbelow(True)
axR.text(0.5, 0.93,
         f"수출/수입 배율: 2025 {ratio[2025]:.3f} → 2026 {ratio[2026]:.3f}",
         transform=axR.transAxes, ha="center", va="top", fontsize=10.5, color="#111",
         bbox=dict(boxstyle="round,pad=0.42", facecolor="white", edgecolor="0.7",
                   lw=0.8, alpha=0.95), zorder=4)

fig.suptitle("2026년 상반기 방향별 물동량 — 전년 동기 대비", fontsize=15, fontweight="bold")
fig.tight_layout(rect=[0, 0.135, 1, 0.945])
caption(fig, CAP_B)
out_b = f"{IMG}/direction_yoy_2025_2026.png"
fig.savefig(out_b, dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- 산출물
print()
print("== 생성 PNG ==")
for p in (out_a, out_b):
    print(f"  {os.path.abspath(p)}  {os.path.getsize(p):,} bytes")

# ---------------------------------------------------------------- 정지선 (종료)
h_end = sha256(F2025)
print()
print("== 정지선: 2025 정본 SHA-256 (종료) ==")
print(f"  {F2025}  {h_end}")
print(f"  무변경 = {h_start == h_end}")

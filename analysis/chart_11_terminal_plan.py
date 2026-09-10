# -*- coding: utf-8 -*-
"""#11 도해 — 부두 위치에 처리량을 얹은 평면 한 장. **3D 를 쓰지 않는다.**

무엇을 그리나
-------------
· 부두를 **`부두길이_m` 에 비례한 가로 막대**로 그린다. 구역(신항·남항)으로 묶는다.
· 막대의 **채움 농도 = 월평균 1m당 천TEU**(단일 색조 순차 램프 — 크기는 순차가 맡는다).
· **배치는 모식이다.** 우리에게 부두의 평면 좌표가 없다 — **길이만 실측이고 위치는 아니다.**
  그 사실을 **그림 안에** 적는다. 지도로 읽히면 안 된다(선커밋 §4).
· **두 표가 안 맞는 자리를 그림이 든다** — 부두현황에만 있는 `SICT` 는 원문이 **`- (폐쇄)`** 로
  적은 부두라 비워 그리고, 물동량에만 있는 `IPT` 는 **제원 미공표**로 축 밖에 따로 세운다.
  **조용히 빼지 않는다.** *두 표는 어긋난 것이 아니다 — 닫힌 부두가 월별 통계에 없는 것뿐이다.*

색
--
`dataviz` — **크기는 순차(단일 색조 light→dark)**. 판정이 없는 그림이라 **상태색을 안 쓴다.**
채움이 어두운 칸의 글자만 흰색으로 뒤집는다(대비).

닿지 않는 곳
------------
· **「효율」·「경쟁력」이 아니다.** 선석 수·장비·선형·운영 시간이 빠져 있다(선커밋 표기 규칙).
· **2026 구간은 잠정치다**(§4). 그림은 값을 그대로 싣고 지위는 본문이 적는다.
· 이미지 안의 글자는 린터가 못 본다. 사람이 눈으로 본다.

실행: cd analysis && python chart_11_terminal_plan.py
산출물: ../reports/images/terminal_plan_2025_10_2026_07.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle

import judge_11_terminal as J

_avail = {f.name for f in font_manager.fontManager.ttflist}
for _cand in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"):
    if _cand in _avail:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "reports", "images", "terminal_plan_2025_10_2026_07.png")

PLANE = "#f9f9f7"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
# 순차 램프(단일 색조) — dataviz `references/palette.md` 의 blue 100~700
RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
        "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
DARK_FROM = 7      # 이 단계부터 글자를 흰색으로 뒤집는다

# 구역 — 부두현황 표의 `구역` 그대로. 순서는 표에 나온 순서다.
ZONES = [("신항", ["SNCT", "HJIT"]), ("남항", ["ICT", "SICT", "E1CT"])]
DETACHED = "IPT"   # 물동량은 있고 제원이 없다


def gather():
    """반환 (달 수, {터미널: 길이}, {터미널: 10개월 합}, {터미널: 월평균 1m당})."""
    months, total, group, term, yt, yterm, berth = J.load()
    tot10 = {}
    for m in months:
        for t, v in term[m].items():
            if v is not None:
                tot10[t] = tot10.get(t, 0.0) + v
    per = {}
    for t, L in berth.items():
        if L and t in tot10:
            per[t] = tot10[t] / len(months) / L
    return len(months), dict(berth), tot10, per


def shade(v, lo, hi):
    if hi <= lo:
        return RAMP[len(RAMP) // 2], False
    i = int(round((v - lo) / (hi - lo) * (len(RAMP) - 1)))
    i = max(0, min(len(RAMP) - 1, i))
    return RAMP[i], i >= DARK_FROM


def build(path=OUT):
    nmonth, berth, tot10, per = gather()
    vals = [per[t] for t in per]
    lo, hi = min(vals), max(vals)
    maxlen = max(berth.values())

    fig = plt.figure(figsize=(11, 7.6), dpi=120, facecolor=PLANE)
    fig.text(0.055, 0.955, "인천항 컨테이너 부두 — 안벽 길이에 월평균 처리량을 얹었다",
             fontsize=19, fontweight="bold", color=INK, va="top")
    fig.text(0.055, 0.915,
             "2025-10~2026-07 · 10개월 · 안벽 길이는 실측(m) · 채움 = 월평균 1m당 천TEU",
             fontsize=11.5, color=INK2, va="top")
    fig.text(0.055, 0.888,
             "**배치는 모식이다** — 부두의 평면 좌표는 공표되지 않는다. 길이만 비례하고 위치는 아니다. 지도가 아니다.".replace("**", ""),
             fontsize=11, color=MUTED, va="top")

    ax = fig.add_axes([0.055, 0.135, 0.89, 0.72], facecolor=SURFACE)
    ax.set_xlim(-40, maxlen * 1.34)
    ax.set_axis_off()

    y = 0.0
    rows = []
    for zone, terms in ZONES:
        y -= 1.0
        ax.text(-30, y + 0.18, zone, fontsize=13.5, fontweight="bold", color=INK, va="center")
        ax.plot([-30, maxlen * 1.30], [y - 0.32, y - 0.32], color=BASE, lw=1.0)
        for t in terms:
            y -= 1.0
            L = berth.get(t, 0.0)
            has_flow = t in per
            if has_flow:
                col, dark = shade(per[t], lo, hi)
            else:
                col, dark = "none", False
            ax.add_patch(Rectangle((0, y - 0.30), L, 0.60, facecolor=col,
                                   edgecolor=(BASE if not has_flow else "white"),
                                   linewidth=(1.4 if not has_flow else 1.6),
                                   linestyle=("--" if not has_flow else "-"), zorder=3))
            ax.text(10, y, t, fontsize=12, fontweight="bold", va="center",
                    color=("white" if dark else INK), zorder=4)
            if has_flow:
                ax.text(L - 10, y, "%.4f" % per[t], fontsize=11, ha="right", va="center",
                        color=("white" if dark else INK2), zorder=4)
                ax.text(L + 24, y, "안벽 %g m · 10개월 합 %g 천TEU" % (L, tot10[t]),
                        fontsize=10.5, va="center", color=INK2)
            else:
                ax.text(L / 2, y, "폐쇄", fontsize=10.5, ha="center", va="center",
                        color=MUTED, style="italic", zorder=4)
                ax.text(L + 24, y, "안벽 %g m · 원문이 「- (폐쇄)」로 적는다 · 월별 통계에 없다" % L,
                        fontsize=10.5, va="center", color=MUTED)
            rows.append(t)

    # 축 밖 — 제원이 없는 곳
    y -= 1.35
    ax.plot([-30, maxlen * 1.30], [y + 0.42, y + 0.42], color=BASE, lw=1.0, ls=(0, (4, 3)))
    ax.text(-30, y + 0.18, "국제여객부두", fontsize=13.5, fontweight="bold", color=INK, va="center")
    y -= 1.0
    ax.add_patch(Rectangle((0, y - 0.30), maxlen * 0.30, 0.60, facecolor="none",
                           edgecolor=MUTED, linewidth=1.4, linestyle=":", zorder=3, hatch="///"))
    ax.text(10, y, DETACHED, fontsize=12, fontweight="bold", va="center", color=INK, zorder=5,
            bbox=dict(boxstyle="square,pad=0.22", facecolor=SURFACE, edgecolor="none"))
    ax.text(maxlen * 0.30 + 24, y,
            "**제원 미공표** — 부두현황 표에 이 이름이 없다 · 10개월 합 %g 천TEU".replace("**", "")
            % tot10.get(DETACHED, 0.0),
            fontsize=10.5, va="center", color=INK2)
    ax.text(maxlen * 0.15, y - 0.52, "막대 길이는 뜻이 없다(길이를 모른다)",
            fontsize=9.5, ha="center", va="center", color=MUTED, style="italic")

    ax.set_ylim(y - 1.15, 0.25)

    # 눈금 — 길이 축
    ax.plot([0, maxlen], [0.02, 0.02], color=BASE, lw=1.2)
    for x in range(0, int(maxlen) + 1, 200):
        ax.plot([x, x], [0.02, 0.10], color=BASE, lw=1.0)
        ax.text(x, 0.17, "%d m" % x, fontsize=9.5, ha="center", color=MUTED)

    # 범례 — 순차 램프
    lx, lw_ = maxlen * 1.02, maxlen * 0.26
    ly = -0.62
    for i, c in enumerate(RAMP):
        ax.add_patch(Rectangle((lx + lw_ * i / len(RAMP), ly), lw_ / len(RAMP), 0.18,
                               facecolor=c, edgecolor="none"))
    ax.text(lx, ly + 0.40, "월평균 1m당 천TEU", fontsize=10, color=INK2)
    # **숫자를 램프에 얹지 않는다** — 옅은 칸 위의 회색 글자는 안 읽힌다(2026-09-11 렌더 실측).
    ax.text(lx, ly - 0.30, "%.4f" % lo, fontsize=9.5, va="top", color=MUTED)
    ax.text(lx + lw_, ly - 0.30, "%.4f" % hi, fontsize=9.5, ha="right", va="top", color=MUTED)

    fig.text(0.055, 0.072,
             "출처 — 인천지방해양수산청 「월별 항만운영통계」(물동량) · 「부두현황」(안벽 길이, 수집일 2026-08-29). "
             "자료 기준일은 원문에 없다.",
             fontsize=10, color=INK2, va="top")
    fig.text(0.055, 0.048,
             "1m당 처리량은 효율이 아니다 — 선석 수·장비·선형·운영 시간이 빠져 있다. 2026 구간은 잠정치.",
             fontsize=10, color=MUTED, va="top")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, facecolor=PLANE)
    plt.close(fig)
    return nmonth, berth, tot10, per


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 값은 판정 코드에서 온다 (두 자리에 안 둔다 · 사고 31) ──")
    nmonth, berth, tot10, per = gather()
    chk("10개월", nmonth, 10)
    chk("안벽 다섯", sorted(berth), ["E1CT", "HJIT", "ICT", "SICT", "SNCT"])
    chk("물동량 다섯", sorted(tot10), ["E1CT", "HJIT", "ICT", "IPT", "SNCT"])
    chk("1m당은 대응 넷만", sorted(per), ["E1CT", "HJIT", "ICT", "SNCT"])
    chk("SICT 는 물동량이 없다", "SICT" in tot10, False)
    chk("SICT 가 폐쇄로 적혀 있다", "폐쇄" in (J.CARGO.get("SICT") or ""), True)
    chk("IPT 는 제원이 없다", "IPT" in berth, False)

    print("── 인수시험: 어긋남을 그림에서 안 뺀다 ──")
    drawn = [t for _, ts in ZONES for t in ts] + [DETACHED]
    chk("두 표의 이름이 전부 그려진다",
        sorted(set(drawn)), sorted(set(berth) | set(tot10)))

    print("── 인수시험: 순차 램프 ──")
    chk("단일 색조 13단", len(RAMP), 13)
    chk("가장 작은 값은 옅다", shade(0.0, 0.0, 1.0)[0], RAMP[0])
    chk("가장 큰 값은 짙다", shade(1.0, 0.0, 1.0)[0], RAMP[-1])
    chk("짙으면 글자를 뒤집는다", shade(1.0, 0.0, 1.0)[1], True)
    chk("옅으면 안 뒤집는다", shade(0.0, 0.0, 1.0)[1], False)

    print("── 인수시험: 그림이 만들어지는가 ──")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.png")
        build(p)
        chk("파일이 생겼다", os.path.exists(p), True)
        chk("빈 파일이 아니다", os.path.getsize(p) > 40000, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="#11 도해 — 부두 평면")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    nmonth, berth, tot10, per = build()
    print("만들었다: %s" % os.path.relpath(OUT, os.path.dirname(HERE)))
    print("  %d개월 · 안벽 %d곳 · 물동량 %d곳 · 1m당 판정 %d곳"
          % (nmonth, len(berth), len(tot10), len(per)))

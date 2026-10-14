# -*- coding: utf-8 -*-
"""#09 차트 — 17년 연장의 결과를 한 장으로.

**이 차트가 말하려는 것은 하나다** — 우리가 이례로 봤던 2022년(27.32배)이
어디쯤에 있는가. 그것을 보이려면 **판정한 해와 못 한 해를 눈으로 갈라야** 한다.
못 한 해를 같은 모양으로 그리면 그림이 「17년 전부 판정했다」고 말하게 된다.

  · 판정 대상 7개 연도 = 채운 점
  · 판정 불가 10개 연도 = **빈 점** — 값은 싣되 참고다
  · 기발행 구간(2022~2025) = 회색 — 이 편의 판정 대상이 아니다
  · 선커밋 기준선 두 개(V2 배율 3.9 · V4 2022의 27.32)를 같이 긋는다

**세로축은 로그가 아니다.** 3.75 와 54.66 을 한 축에 놓으면 아래쪽이 눌리지만,
로그로 펴면 **차이가 실제보다 작아 보인다.** 눌리는 쪽을 택했다 —
이 그림의 요점이 「위쪽이 얼마나 높은가」이기 때문이다.

실행: cd analysis && python chart_09_backfill.py
산출물: ../reports/images/backfill_ratio_2005_2021.png
        ../reports/images/backfill_share_2005_2021.png
"""
import csv
import io
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 운영자 콘솔(cp949)에서 출력이 터지지 않게 한다. **없으면 통과 문장의
# `—` 하나에 죽고, 죽은 종료코드를 다른 검사기가 판정으로 읽는다**
# (2026-09-02 실측 · `check_generated` 가 그것을 「낡았다」로 읽었다).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


_avail = {f.name for f in font_manager.fontManager.ttflist}
for _cand in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"):
    if _cand in _avail:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "..", "reports", "images")
SRC = os.path.join(HERE, "container_2005_2021_direction.csv")

# 판정 대상 — `docs/09_판정결과.md` §1. **여기 목록을 늘리는 것은 판정을 바꾸는 것이다.**
JUDGED = {2013, 2015, 2016, 2018, 2019, 2020, 2021}

# 기발행 구간 — 이 편의 판정 대상이 아니다(선커밋 §0-1).
# 값은 `docs/FACTS.md` 와 첫 화면 연도 구획이 든다.
PUBLISHED = {2022: (27.32, 93.0), 2023: (6.03, 85.3),
             2024: (7.70, 87.8), 2025: (6.05, 85.1)}

V2_MIN = 3.9        # 선커밋 V2
V4_REF = 27.32      # 선커밋 V4 기준 = 2022년 값

INK = "#15191C"
SEAL = "#1F4A6B"
GREY = "#8A9199"
FAILC = "#9C2F22"


def load():
    import collect_09_backfill as C
    rows = list(csv.DictReader(io.open(SRC, encoding="utf-8-sig")))
    by = defaultdict(list)
    for r in rows:
        by[int(r["yyyy"])].append(r)
    return {y: C.annual(v) for y, v in by.items()}


def _frame(ax, title, ylab):
    ax.set_title(title, fontsize=12.5, fontweight="bold", color=INK, pad=13, loc="left")
    ax.set_ylabel(ylab, fontsize=9.5, color=INK)
    ax.grid(axis="y", color="#DBDFE1", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#C3C9CC")
    ax.tick_params(colors="#5D666D", labelsize=9)


def draw_ratio(ann):
    ys = sorted(ann)
    fig, ax = plt.subplots(figsize=(10.4, 5.0), dpi=170)
    _frame(ax, "인천항 공컨테이너 연간 수출÷수입 배율 — 2005~2021 (외항)", "배율 (배)")

    # 선커밋 기준선 — **결과보다 먼저 그어진 선**이라 먼저 그린다.
    ax.axhline(V4_REF, color=FAILC, linewidth=1.2, linestyle="--", zorder=1)
    ax.text(ys[0] - 0.4, V4_REF + 1.4, "선커밋 V4 기준 = 2022년 27.32배",
            color=FAILC, fontsize=8.6, va="bottom")
    ax.axhline(V2_MIN, color=SEAL, linewidth=1.0, linestyle=":", zorder=1)
    # **오른쪽 끝에 둔다.** 왼쪽에 두면 2006~2010 점들에 가려 라벨이 안 읽힌다
    # — 그리는 것과 읽히는 것은 다르다(사고 73).
    ax.text(2025.8, V2_MIN + 1.1, "선커밋 V2 하한 3.9배",
            color=SEAL, fontsize=8.6, va="bottom", ha="right")

    line_y = [ann[y]["배율"] for y in ys]
    ax.plot(ys, line_y, color=SEAL, linewidth=1.6, zorder=2)
    for y in ys:
        v = ann[y]["배율"]
        judged = y in JUDGED
        ax.plot([y], [v], marker="o", markersize=7.5, zorder=3,
                color=SEAL if judged else "#FFFFFF",
                markeredgecolor=SEAL, markeredgewidth=1.6)
        if judged and v >= V4_REF:
            ax.annotate("%.2f" % v, (y, v), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=9,
                        fontweight="bold", color=FAILC)

    # 기발행 구간 — **회색으로 따로 둔다.** 같은 색으로 이으면 판정 대상처럼 보인다.
    py = sorted(PUBLISHED)
    ax.plot(py, [PUBLISHED[y][0] for y in py], color=GREY, linewidth=1.4,
            linestyle="-", marker="s", markersize=5.5, zorder=2)
    ax.annotate("2022  27.32", (2022, 27.32), textcoords="offset points",
                xytext=(6, 6), fontsize=9, color=GREY)
    ax.text(2023.4, 41, "기발행 구간\n(판정 대상 아님)", fontsize=8.6,
            color=GREY, ha="center", linespacing=1.4)

    ax.set_xticks(list(range(2005, 2026, 2)))
    ax.set_xlim(2004.2, 2026.0)
    ax.set_ylim(0, 62)

    hint = ("● 판정 대상 7개 연도   ○ 판정 불가 10개 연도(값은 참고)   "
            "■ 기발행 2022~2025 (판정 대상 아님)")
    ax.text(0.0, -0.155, hint, transform=ax.transAxes, fontsize=8.6, color="#5D666D")
    ax.text(0.0, -0.225,
            "판정 불가 = Teu 항등식 정지 조건. 값은 싣되 결론에 쓰지 않는다. "
            "선커밋 = docs/09_주제검증.md (커밋 2b7076b)",
            transform=ax.transAxes, fontsize=8.2, color="#79848C")

    fig.tight_layout(rect=(0, 0.055, 1, 1))
    out = os.path.join(OUTDIR, "backfill_ratio_2005_2021.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    return out


def draw_share(ann):
    ys = sorted(ann)
    fig, ax = plt.subplots(figsize=(10.4, 4.2), dpi=170)
    _frame(ax, "인천항 공컨테이너 연간 수출 방향 비중 — 2005~2021 (외항)", "비중 (%)")

    ax.axhline(85.0, color=FAILC, linewidth=1.2, linestyle="--", zorder=1)
    ax.text(ys[0] - 0.4, 85.6, "선커밋 V3 하한 85.0%", color=FAILC,
            fontsize=8.6, va="bottom")

    ax.plot(ys, [ann[y]["수출비중"] for y in ys], color=SEAL, linewidth=1.6, zorder=2)
    for y in ys:
        v = ann[y]["수출비중"]
        judged = y in JUDGED
        below = judged and v < 85.0
        ax.plot([y], [v], marker="o", markersize=7.5, zorder=3,
                color=(FAILC if below else SEAL) if judged else "#FFFFFF",
                markeredgecolor=FAILC if below else SEAL, markeredgewidth=1.6)
        if below:
            ax.annotate("%.1f%%  V3 미달" % v, (y, v), textcoords="offset points",
                        xytext=(0, -17), ha="center", fontsize=9,
                        fontweight="bold", color=FAILC)

    py = sorted(PUBLISHED)
    ax.plot(py, [PUBLISHED[y][1] for y in py], color=GREY, linewidth=1.4,
            marker="s", markersize=5.5, zorder=2)

    ax.set_xticks(list(range(2005, 2026, 2)))
    ax.set_xlim(2004.2, 2026.0)
    ax.set_ylim(74, 100)
    ax.text(0.0, -0.185,
            "● 판정 대상   ○ 판정 불가(값은 참고)   ■ 기발행 2022~2025 (판정 대상 아님)",
            transform=ax.transAxes, fontsize=8.6, color="#5D666D")

    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out = os.path.join(OUTDIR, "backfill_share_2005_2021.png")
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    return out


def selftest():
    """**그림이 판정을 바꾸지 않는지** 본다. 그림은 판정의 표현이지 판정이 아니다."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 그림이 판정 기록과 어긋나지 않는가 ──")
    doc = os.path.join(HERE, "..", "docs", "09_판정결과.md")
    t = io.open(doc, encoding="utf-8").read() if os.path.exists(doc) else ""
    chk("판정 대상이 7개다", len(JUDGED), 7)
    chk("판정 기록에 같은 연도가 적혀 있다",
        all(str(y) in t for y in JUDGED), True)
    chk("선커밋 기준선이 문서와 같다 (V2)", "3.9" in t, True)
    chk("선커밋 기준선이 문서와 같다 (V4)", "27.32" in t, True)
    ann = load()
    chk("17개 연도를 그린다", len(ann), 17)
    over = sorted(y for y in JUDGED if ann[y]["배율"] >= V4_REF)
    chk("V4 를 넘는 판정 연도가 셋이다", over, [2019, 2020, 2021])
    under = sorted(y for y in JUDGED if ann[y]["수출비중"] < 85.0)
    chk("V3 미달 판정 연도가 2013 하나다", under, [2013])
    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    os.makedirs(OUTDIR, exist_ok=True)
    ann = load()
    for p in (draw_ratio(ann), draw_share(ann)):
        print("-> %s  (%,d B)".replace(",", "") % (p, os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

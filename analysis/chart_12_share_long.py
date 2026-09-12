# -*- coding: utf-8 -*-
"""#12 도판 — 창이 41개월인데 관측이 39개월이다. 그림이 그 둘을 같이 든다.

무엇을 그리나
-------------
**위 칸** — 신항 몫 월별(39개월). x 축은 **창 41개월 전부**라서 **못 읽은 두 달이 빈칸으로 보인다.**
빈칸에 사선 띠와 「못 읽음 · 첨부가 `.hwp`」를 적는다 — **「원문에 없다」가 아니다.**
S3 의 **3~7월 정합 창** 연평균 넷을 그 다섯 달 위에 짧은 가로선으로 얹는다(값을 같이 적는다).

**아래 칸** — S2 의 쌍 10개 부호 일치율. 가로 점 도표이고 **기준선 0.50** 과 **관측 중앙값**을 같이 세운다.

형태를 고른 이유(`dataviz` · choosing-a-form)
--------------------------------------------
위는 **시간에 따른 변화** → 선. 아래는 **열 항목의 크기 비교** → 가로 점 도표(막대보다 잉크가 적다).
**둘 다 한 계열이라 범례가 없다** — 제목이 계열을 부른다(`dataviz` 비협상 항목).
**축은 하나다.** 두 칸은 단위가 다르므로 **한 그림에 두 y 축을 쓰지 않고 칸을 나눴다.**
색은 **단일 색조 두 단**과 잉크 토큰뿐이다 — 범주 팔레트가 없으므로 CVD 인접쌍 검사의 대상이 아니다.
**PASS/FAIL 을 색으로 안 가른다** — 판정은 글자가 진다(#11 과 같은 규율).

값은 **판정 코드에서만** 온다 — 같은 수를 두 자리에 두지 않는다(사고 31).

실행: cd analysis && python chart_12_share_long.py
산출물: ../reports/images/terminal_share_long_2023_2026.png
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

import judge_12_terminal_long as J

_avail = {f.name for f in font_manager.fontManager.ttflist}
for _cand in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"):
    if _cand in _avail:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "reports", "images", "terminal_share_long_2023_2026.png")

PLANE = "#f9f9f7"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
# 단일 색조 — `dataviz` references/palette.md 의 blue. 두 단만 쓴다(계열이 하나다).
LINE = "#1c5cab"
FILL = "#9ec5f4"


def build(path=OUT):
    r = J.judge()
    if r["stop"]:
        print("[중단] 게이트가 정지를 냈다:", r["stop"])
        return None
    win = J.window_months()
    months, shares = r["months"], r["shares"]
    s1, s2, s3 = r["S1"], r["S2"], r["S3"]
    x = list(range(len(win)))
    y = [shares[m]["신항"] if m in shares else None for m in win]

    fig = plt.figure(figsize=(11.4, 8.6), dpi=120, facecolor=PLANE)
    fig.text(0.055, 0.965, "인천항 신항 몫 — 창 41개월, 읽은 것은 39개월",
             fontsize=19, fontweight="bold", color=INK, va="top")
    fig.text(0.055, 0.928,
             "빈 두 달은 **원문에 없는 것이 아니다** — 그 두 글만 첨부가 `.hwp` 라 우리 파서가 못 읽는다."
             .replace("**", "").replace("`", ""),
             fontsize=11.5, fontweight="bold", color=INK2, va="top")
    fig.text(0.055, 0.903,
             "게시판에는 220개월이 있고 그중 39개월(17.7%)을 읽었다 · 몫의 분모 = 공표 합계 · 2026 구간은 잠정치",
             fontsize=10.5, color=MUTED, va="top")

    # ── 위 칸 — 신항 몫 시계열 ──
    ax = fig.add_axes([0.055, 0.475, 0.9, 0.395], facecolor=SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(BASE)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)

    # 못 읽은 달 — 사선 띠
    for m in r["missing"]:
        i = win.index(m)
        ax.add_patch(Rectangle((i - 0.5, 0), 1.0, 100, facecolor="#efeee7",
                               edgecolor=BASE, hatch="///", lw=0.0, zorder=1))
    lo = min(v for v in y if v is not None) - 1.6
    hi = max(v for v in y if v is not None) + 2.6

    # 선은 결손에서 끊는다 — 이어 그으면 없는 달을 있는 것처럼 만든다
    seg_x, seg_y = [], []
    for i, v in enumerate(y):
        if v is None:
            if len(seg_x) > 1:
                ax.plot(seg_x, seg_y, color=LINE, lw=2.0, zorder=3)
            seg_x, seg_y = [], []
        else:
            seg_x.append(i)
            seg_y.append(v)
    if len(seg_x) > 1:
        ax.plot(seg_x, seg_y, color=LINE, lw=2.0, zorder=3)
    ax.plot([i for i, v in enumerate(y) if v is not None],
            [v for v in y if v is not None], "o", ms=4.2, color=LINE,
            mec="white", mew=1.0, zorder=4)

    # S3 정합 창 — 해마다 3~7월 평균을 그 다섯 달 위에 가로선으로
    for yr, mean in sorted(s3["연평균"].items()):
        idx = [win.index("%s-%02d" % (yr, mm)) for mm in s3["정합창"]]
        ax.plot([min(idx) - 0.4, max(idx) + 0.4], [mean, mean],
                color=INK, lw=2.6, solid_capstyle="butt", zorder=5)
        # 라벨이 선 위에 앉으면 데이터선과 겹친다 — **흰 바탕을 깔아 뚫고 올린다**(렌더 실측).
        ax.text((min(idx) + max(idx)) / 2, mean + 0.55, "%s  %.2f%%" % (yr, mean),
                fontsize=10, ha="center", va="bottom", color=INK, fontweight="bold",
                zorder=7,
                bbox=dict(boxstyle="square,pad=0.18", facecolor=SURFACE, edgecolor="none"))

    ax.set_xlim(-0.8, len(win) - 0.2)
    ax.set_ylim(lo, hi)
    ax.set_ylabel("신항 몫 (%)", fontsize=10.5, color=INK2)
    ticks = [i for i, m in enumerate(win) if m.endswith(("-01", "-04", "-07", "-10"))]
    ax.set_xticks(ticks)
    ax.set_xticklabels([win[i] for i in ticks], fontsize=9, color=MUTED, rotation=45,
                       ha="right")
    ax.tick_params(axis="y", labelsize=9.5, colors=MUTED)
    # **주석이 사선 띠를 가로지르면 둘 다 안 읽힌다**(렌더 실측) — 띠 오른쪽으로 빼고 화살표로 잇는다.
    mi = win.index(r["missing"][0])
    ax.annotate("못 읽음 2개월 — 첨부가 .hwp 다",
                xy=(mi + 1.6, lo + 1.0), xytext=(mi + 4.0, lo + 0.55),
                fontsize=10, color=INK2, va="center", zorder=7,
                bbox=dict(boxstyle="square,pad=0.2", facecolor=SURFACE, edgecolor="none"),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))
    ax.text(len(win) - 0.4, hi - 0.4,
            "굵은 가로선 = 3~7월 정합 창의 해 평균 (S3 이 본 것)",
            fontsize=9.5, ha="right", va="top", color=MUTED)

    # ── 아래 칸 — S2 쌍 일치율 ──
    # **왼쪽을 넓혔다** — 쌍 이름 「E1CT ↔ HJIT」가 잘려 나갔다(렌더 실측).
    # **아래도 올렸다** — 축 라벨·눈금이 출처 문장과 겹쳤다.
    ax2 = fig.add_axes([0.135, 0.125, 0.82, 0.265], facecolor=SURFACE)
    for s in ("top", "right", "left"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_color(BASE)
    ax2.grid(axis="x", color=GRID, lw=0.8)
    ax2.set_axisbelow(True)
    pairs = sorted(s2["쌍"].items(), key=lambda kv: kv[1][2])
    for j, ((a, b), (n, d, rate)) in enumerate(pairs):
        ax2.plot([0, rate], [j, j], color=FILL, lw=2.0, solid_capstyle="butt", zorder=2)
        ax2.plot([rate], [j], "o", ms=8.5, color=LINE, mec="white", mew=1.2, zorder=4)
        # 기준선·중앙값선이 글자를 가로질러 보인다(렌더 실측) — 바탕을 깔아 글자를 지킨다.
        ax2.text(rate + 0.012, j, "%.3f  (%d/%d)" % (rate, n, d), fontsize=10,
                 va="center", color=INK2, zorder=5,
                 bbox=dict(boxstyle="square,pad=0.15", facecolor=SURFACE, edgecolor="none"))
    ax2.set_yticks(range(len(pairs)))
    ax2.set_yticklabels(["%s ↔ %s" % p for p, _ in pairs], fontsize=10, color=INK)
    ax2.axvline(s2["기준"], color=INK, lw=1.6, ls="--", zorder=3)
    ax2.text(s2["기준"], len(pairs) - 0.35, " 기준 > %.2f" % s2["기준"], fontsize=10,
             color=INK, fontweight="bold", va="top")
    ax2.axvline(s2["중앙값"], color=LINE, lw=1.6, zorder=3)
    ax2.text(s2["중앙값"], len(pairs) - 1.35, "관측 중앙값 %.3f" % s2["중앙값"], fontsize=10,
             color=LINE, fontweight="bold", ha="right", va="top")
    ax2.set_xlim(0, 0.92)
    ax2.set_ylim(-0.7, len(pairs) - 0.3)
    ax2.set_xlabel("전년대비 부호가 같은 달의 비율 — 쌍 10개 (S2)", fontsize=10.5, color=INK2)
    ax2.tick_params(axis="x", labelsize=9.5, colors=MUTED)

    fig.text(0.055, 0.048,
             "출처 — 인천지방해양수산청 「월별 항만운영통계」 첨부 39건(주소·SHA-256 = "
             "analysis/terminal_monthly_long_sources.csv).",
             fontsize=10, color=INK2, va="top")
    fig.text(0.055, 0.026,
             "선커밋 blob 89443910 · S1·S2·S3 전부 FAIL · 기준은 고치지 않았다. "
             "「계절성」·「상관」이라는 말을 쓰지 않는다 — 잰 것은 부호다.",
             fontsize=10, color=MUTED, va="top")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, facecolor=PLANE)
    plt.close(fig)
    return r


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-50s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 값은 판정 코드에서 온다 (두 자리에 안 둔다 · 사고 31) ──")
    r = J.judge()
    chk("x 축이 창 41개월", len(J.window_months()), 41)
    chk("그중 결손 2개월", len(r["missing"]), 2)
    chk("점은 39개월", len(r["shares"]), 39)
    chk("쌍은 열", len(r["S2"]["쌍"]), 10)
    chk("S3 해 넷", len(r["S3"]["연평균"]), 4)

    print("── 인수시험: 결손을 이어 긋지 않는다 ──")
    # **선이 결손에서 끊기는가** — 값 목록에 None 이 들어가야 끊긴다.
    win = J.window_months()
    y = [r["shares"][m]["신항"] if m in r["shares"] else None for m in win]
    chk("결손 자리가 None 이다", [win[i] for i, v in enumerate(y) if v is None],
        sorted(r["missing"]))

    print("── 인수시험: 상태색을 안 쓴다 ──")
    src = open(__file__, encoding="utf-8").read()
    for bad in ("#c0392b", "#d93", "red", "green"):
        chk("상태색 '%s' 가 없다" % bad, bad in src.lower().split("# ")[0], False)

    print("── 인수시험: 그림이 만들어지는가 ──")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.png")
        build(p)
        chk("파일이 생겼다", os.path.exists(p), True)
        chk("빈 파일이 아니다", os.path.getsize(p) > 60000, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="#12 도판 — 신항 몫 41/39 · 쌍 일치율")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    r = build()
    print("만들었다: %s" % os.path.relpath(OUT, os.path.dirname(HERE)))
    print("  창 %d · 관측 %d · 결손 %d · 쌍 %d · S3 해 %d"
          % (len(J.window_months()), len(r["months"]), len(r["missing"]),
             len(r["S2"]["쌍"]), len(r["S3"]["연평균"])))

# -*- coding: utf-8 -*-
"""링크드인 스페셜 한 장 — **이 장이 파는 것은 수치가 아니라 방식이다.**

무엇을 보이나
-------------
「기준을 데이터보다 먼저 커밋했고, 못 미친 것은 FAIL 로 실었다」를 **그림 하나로** 보인다.
그래서 대표 차트가 시계열 자체가 아니라 **기준선과 그 아래로 내려간 달들**이다:

  · 252개월 월별 배율(수출 TEU ÷ 수입 TEU · 외항 `ocCt=1`)
  · **근거 구간 48개월**(2022~2025) — 하한 3.88 을 여기서 뽑아 커밋했다
  · **판정 구간 204개월**(2005~2021) — 그 기준을 여기에 댔다
  · 기준선 아래로 내려간 달을 **따로 찍는다.** 그것이 #10 W2 를 FAIL 로 만든 것이다

**인과를 안 쓴다**(§3-5). 왜 내려갔는지는 이 장에 한 줄도 없다.
**낡는 값을 안 쓴다**(사고 31·83) — 편수·팔로워·「가장 최근」이 없다.

색
--
`dataviz` 기준으로 검증했다 — `#2a78d6`(계열) · `#d03b3b`(기준선·미성립) 두 색이
CVD 분리 ΔE 23.8(protan) 로 통과한다. **PASS/FAIL 은 색으로 안 가른다** —
적록 쌍(`#0ca30c`↔`#d03b3b`)이 deutan ΔE 4.1 로 떨어졌다. 대신 **채움 대 테두리 +
글리프(○/×) + 낱말**로 가른다. 색은 거들 뿐이다.
**글리프는 폰트 cmap 을 인수시험이 직접 본다** — `✓`·`✕`는 Malgun Gothic 에 없어 두부로 나온다.

닿지 않는 곳
------------
· **이 파일은 값을 안 만든다.** 원시 CSV 에서 다시 세고, `docs/FACTS.md` 등재값과
  **어긋나면 죽는다**(`--selftest`). 그림이 대장보다 앞서가지 못하게 하는 자리다.
· **이미지 안의 글자는 `check_private`·린터가 못 본다.** 사람이 눈으로 본다.
· 링크드인이 어떻게 잘라 보여 주는지는 **[미확인]** — 올려 봐야 안다.

실행: cd analysis && python build_featured_card.py
산출물: ../assets/linkedin_featured.png
"""
import argparse
import csv
import io
import os
import sys
from collections import defaultdict

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
from matplotlib.patches import FancyBboxPatch

import basis_10_monthly_floor as B

_avail = {f.name for f in font_manager.fontManager.ttflist}
for _cand in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"):
    if _cand in _avail:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "assets", "linkedin_featured.png")
LONG = os.path.join(HERE, "container_2005_2021_direction.csv")

# ── 색 (dataviz 검증분) ────────────────────────────────────────────────────
SURFACE = "#fcfcfb"
PLANE = "#f9f9f7"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
SERIES = "#2a78d6"
ALERT = "#d03b3b"

# **글리프는 폰트에 있는 것만 쓴다.** `✓`(U+2713)·`✕`(U+2715)는 Malgun Gothic 에 **없어서**
# 두부(tofu)로 나온다 — 그러면 「색 말고 모양으로 가른다」가 그 자리에서 깨진다.
# 인수시험이 폰트 cmap 을 직접 본다. **경고를 눈으로 읽는 것에 기대지 않는다**(사고 26).
GLYPH_PASS = "○"
GLYPH_FAIL = "×"

# ── 선커밋 8건 — `docs/09_판정결과.md` · `docs/10_판정결과.md` 그대로 ──────
VERDICTS = [
    ("#09 V1", "연간 수출 TEU > 수입 TEU", "판정 가능 7개 연도", "7/7 성립", True),
    ("#09 V2", "연간 배율 ≥ 3.9", "판정 가능 7개 연도", "7/7 성립", True),
    ("#09 V3", "연간 수출 비중 ≥ 85.0%", "판정 가능 7개 연도", "6/7 · 2013 미달", False),
    ("#09 V4", "2005~2021 중 27.32배 이상 없음", "판정 가능 7개 연도", "3개 연도 초과", False),
    ("#10 W1", "월간 수출 TEU > 수입 TEU", "204개월", "204/204 성립", True),
    ("#10 W2", "월간 배율 ≥ 3.88", "204개월", "187/204 · 17개월 미달", False),
    ("#10 W3", "월간 수출 비중 ≥ 78.3%", "204개월", "191/204 · 13개월 미달", False),
    ("#10 W4", "사라진 조합은 돌아오지 않는다", "조합 8종", "2종에서 끊김", False),
]

# **그림에 찍히는 문장은 전부 여기 있다** — 인수시험이 이 목록만 훑으면 된다.
TITLE = "기준을 먼저 커밋하고, 못 미친 것은 FAIL 로 실었다"
SUB1 = "인천항 공컨테이너 · 2005-01~2025-12(252개월) · 외항(ocCt=1) · TEU"
SUB2 = "판정 기준은 데이터를 받기 전에 저장소에 커밋하고 해시로 고정한다. 데이터를 본 뒤 기준을 고치지 않는다."
CHART_TITLE = "월별 수출 ÷ 수입 배율 — 세로축 로그"
NOTE_FLOOR = "선커밋 하한 3.88 — 근거 구간 48개월의 관측 최소에서 뽑아 커밋했다"
NOTE_BASIS = "근거 구간 48개월\n(2022~2025)"
NOTE_JUDGE = "판정 구간 204개월 (2005~2021) — 이 기준을 여기에 댔다"
TABLE_SUB = "FAIL 은 기준대로 판정해 떨어진 것이고, 정상 산출물로 그대로 발행했다."
# **표가 #10 을 네 줄 든다. 그런데 #10 은 보고서 편으로 안 나와 있다.**
# 이 장을 보고 사이트에 온 사람이 #10 을 찾으면 못 찾는다 — 사이트와 README 에는
# 그 안내를 붙였는데 **이 장에는 없었다.** 나침반이 가리키는 곳에 표지가 없는 자리다.
TABLE_NOTE = ("#10 은 판정만 끝났고 보고서 편으로는 아직 안 냈다 — 기준 넷과 판정, 그 근거는 "
              "저장소의 docs/10_판정결과.md 가 든다.")
FOOT1 = ("출처 — 공공데이터포털 · 인천항만공사 공컨테이너 화물 통계 API(ipaEmpConCargoInfo). "
         "모집단은 외항(ocCt=1), 단위는 TEU.")
FOOT2 = "원시 CSV · 수집·판정·차트 코드 · 선커밋 이력 — github.com/jisangj03-dev/incheon-port-analysis"
FOOT3 = "sounding.higgsfield.app"

W2_FLOOR = 3.88          # #10 W2 선커밋 하한 — 근거 구간 48개월의 관측 최소(3.8855)
JUDGE_YEARS = range(2005, 2022)   # 판정 구간 204개월
BASIS_YEARS = range(2022, 2026)   # 근거 구간 48개월


def read_long():
    """2005~2021 은 한 파일에 `yyyy` 가 들어 있다. (연,월) 로 묶는다."""
    with io.open(LONG, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    acc = defaultdict(lambda: {"수출": 0.0, "수입": 0.0, "환적": 0.0})
    for r in rows:
        if (r.get("ocCt") or "").strip() != B.OCEAN:
            continue
        key = (int((r.get("yyyy") or "0").strip()), int((r.get("mm") or "0").strip()))
        g = (r.get("GInOut") or "").strip()
        if g == B.EXPORT:
            acc[key]["수출"] += B.teu(r)
        elif g == B.IMPORT:
            acc[key]["수입"] += B.teu(r)
        elif g in B.TRANSSHIP:
            acc[key]["환적"] += B.teu(r)
    return {k: dict(v, 전체=v["수출"] + v["수입"] + v["환적"]) for k, v in acc.items()}


def series():
    """252개월. 반환 {(연,월): {수출,수입,환적,전체}} — **원시 CSV 에서 다시 센다.**"""
    per = read_long()
    for y in BASIS_YEARS:
        for m, v in B.monthly(B.read_year(y)).items():
            per[(y, m)] = v
    return per


def facts(per):
    """그림이 실을 수치. **전부 여기서 계산되고, 인수시험이 대장과 맞댄다.**"""
    keys = sorted(per)
    ratio = [(k, per[k]["수출"] / per[k]["수입"]) for k in keys if per[k]["수입"] > 0]
    judged = [(k, r) for k, r in ratio if k[0] in JUDGE_YEARS]
    lo = min(ratio, key=lambda t: t[1])
    hi = max(ratio, key=lambda t: t[1])
    return {
        "개월": len(keys),
        "W1성립": sum(1 for k in keys if per[k]["수출"] > per[k]["수입"]),
        "판정개월": len(judged),
        "W2미성립": sum(1 for _, r in judged if r < W2_FLOOR),
        "최소": (lo[1], lo[0]),
        "최대": (hi[1], hi[0]),
        "계열": ratio,
    }


def _chip(ax, x, y, ok, size=9):
    """**PASS/FAIL 을 색으로 안 가른다** — 채움/테두리 · 글리프 · 낱말 셋으로 가른다.

    적록 쌍은 deutan 에서 ΔE 4.1 로 붙는다(dataviz 검증). 색만 쓰면 못 가른다.
    """
    w, h = 0.115, 0.052
    box = FancyBboxPatch((x, y - h / 2), w, h,
                         boxstyle="round,pad=0.006,rounding_size=0.02",
                         transform=ax.transAxes, clip_on=False,
                         facecolor=(ALERT if not ok else "none"),
                         edgecolor=(ALERT if not ok else BASE), linewidth=1.4)
    ax.add_patch(box)
    ax.text(x + w / 2, y, (GLYPH_FAIL + " FAIL" if not ok else GLYPH_PASS + " PASS"),
            transform=ax.transAxes, ha="center", va="center",
            fontsize=size, fontweight="bold",
            color=("white" if not ok else INK2), clip_on=False)


def build(path=OUT):
    per = series()
    F = facts(per)
    keys = [k for k, _ in F["계열"]]
    vals = [v for _, v in F["계열"]]
    xs = [k[0] + (k[1] - 0.5) / 12.0 for k in keys]

    fig = plt.figure(figsize=(10, 12.5), dpi=120, facecolor=PLANE)

    fig.text(0.065, 0.963, TITLE, fontsize=25, fontweight="bold", color=INK, va="top")
    fig.text(0.065, 0.934, SUB1, fontsize=12.5, color=INK2, va="top")
    fig.text(0.065, 0.915, SUB2, fontsize=11.5, color=MUTED, va="top")

    ax = fig.add_axes([0.065, 0.545, 0.885, 0.335], facecolor=SURFACE)
    ax.set_yscale("log")
    ax.axvspan(2022, 2026, color=GRID, alpha=0.85, lw=0, zorder=0)
    ax.plot(xs, vals, lw=1.6, color=SERIES, zorder=3, solid_joinstyle="round")

    below = [(x, v) for x, v in zip(xs, vals) if v < W2_FLOOR and int(x) in JUDGE_YEARS]
    ax.axhline(W2_FLOOR, color=ALERT, lw=2.0, ls=(0, (5, 3)), zorder=4)
    ax.scatter([x for x, _ in below], [v for _, v in below], s=42, zorder=5,
               facecolor=ALERT, edgecolor=SURFACE, linewidth=1.4)

    ax.set_ylim(1.4, 320)
    ax.set_xlim(2004.6, 2026.4)
    ax.set_yticks([2, 3.88, 10, 30, 100, 300])
    ax.set_yticklabels(["2배", "3.88", "10배", "30배", "100배", "300배"])
    ax.set_xticks([2005, 2009, 2013, 2017, 2021, 2025])
    ax.tick_params(colors=MUTED, labelsize=10.5, length=0)
    ax.grid(axis="y", color=GRID, lw=0.9, zorder=1)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)

    ax.set_title(CHART_TITLE, fontsize=13, color=INK, fontweight="bold",
                 loc="left", pad=10)
    # **글자를 점 위에 얹지 않는다.** 미달 달들이 2005~2013 에 몰려 있어 그 구간의
    # 낮은 자리는 비워 둔다(2026-09-10 실측: 처음 배치가 점을 덮었다).
    ax.text(2013.2, 2.02, NOTE_FLOOR, fontsize=10.5, color=ALERT)
    ax.text(2023.9, 128, NOTE_BASIS, fontsize=10.5, color=INK2, ha="center")
    ax.text(2005.2, 215, NOTE_JUDGE, fontsize=10.5, color=INK2)

    lo_v, lo_k = F["최소"]
    hi_v, hi_k = F["최대"]
    ax.annotate("최소 %.4f배 · %d-%02d" % (lo_v, lo_k[0], lo_k[1]),
                xy=(lo_k[0] + lo_k[1] / 12.0, lo_v), xytext=(2005.4, 1.47),
                fontsize=10, color=INK2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))
    ax.annotate("최대 %.4f배 · %d-%02d" % (hi_v, hi_k[0], hi_k[1]),
                xy=(hi_k[0] + hi_k[1] / 12.0, hi_v), xytext=(2012.6, 258),
                fontsize=10, color=INK2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.9))

    # **한 줄에 다 넣지 않는다** — 폭을 넘으면 오른쪽이 잘리고, 잘린 것은 렌더 전에 안 보인다
    # (2026-09-10 실측: 첫 판이 「그대로 실」 에서 끊겼다). 줄을 나눠 둔다.
    fig.text(0.065, 0.527,
             "빨간 점 %d개 = 판정 구간 204개월 중 선커밋 하한 아래로 내려간 달." % F["W2미성립"],
             fontsize=11.5, color=INK, va="top", fontweight="bold")
    fig.text(0.065, 0.509,
             "그래서 #10 W2 는 FAIL 이고, 기준을 고치지 않고 그대로 실었다.",
             fontsize=11.5, color=INK, va="top", fontweight="bold")
    fig.text(0.065, 0.491,
             "같은 252개월에서 방향(수출>수입)은 %d개월 전부 성립한다 — #10 W1 · #04. "
             "PASS 는 기준 통과이지 법칙이 아니다." % F["W1성립"],
             fontsize=11.5, color=INK2, va="top")

    tb = fig.add_axes([0.065, 0.105, 0.885, 0.355])
    tb.set_axis_off()
    tb.set_xlim(0, 1)
    tb.set_ylim(0, 1)
    n_fail = sum(1 for row in VERDICTS if not row[4])
    tb.text(0, 1.0, "선커밋 기준 8건의 판정 — PASS %d · FAIL %d"
            % (len(VERDICTS) - n_fail, n_fail),
            fontsize=15, fontweight="bold", color=INK, va="top")
    tb.text(0, 0.945, TABLE_SUB, fontsize=11, color=MUTED, va="top")

    y = 0.855
    for vid, rule, win, res, ok in VERDICTS:
        tb.text(0.0, y, vid, fontsize=10.5, color=MUTED, va="center")
        tb.text(0.093, y, rule, fontsize=11.5, color=INK, va="center")
        tb.text(0.505, y, win, fontsize=10, color=INK2, va="center")
        tb.text(0.665, y, res, fontsize=10, color=INK2, va="center")
        _chip(tb, 1.0 - 0.115, y, ok)
        tb.plot([0, 1], [y - 0.052, y - 0.052], color=GRID, lw=0.8, clip_on=False)
        y -= 0.104

    tb.text(0, y + 0.046, TABLE_NOTE, fontsize=10.5, color=INK2, va="top")

    fig.text(0.065, 0.072, FOOT1, fontsize=10.5, color=INK2, va="top")
    fig.text(0.065, 0.050, FOOT2, fontsize=10.5, color=INK2, va="top")
    fig.text(0.065, 0.028, FOOT3, fontsize=10.5, color=SERIES, va="top")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, facecolor=PLANE)
    plt.close(fig)
    return F


def drawn_text():
    """**그림에 찍히는 문장 전부.** 인수시험이 이것만 훑는다."""
    out = [TITLE, SUB1, SUB2, CHART_TITLE, NOTE_FLOOR, NOTE_BASIS, NOTE_JUDGE,
           TABLE_SUB, TABLE_NOTE, FOOT1, FOOT2, FOOT3]
    for row in VERDICTS:
        out.extend([row[0], row[1], row[2], row[3]])
    return out


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 그림이 실을 수치를 원시 CSV 에서 다시 센다 (대장과 맞댄다) ──")
    F = facts(series())
    chk("252개월", F["개월"], 252)
    chk("W1 은 252개월 전부 성립 (FACTS 155)", F["W1성립"], 252)
    chk("판정 구간이 204개월 (FACTS 157)", F["판정개월"], 204)
    chk("W2 미달 17개월 (#10 W2)", F["W2미성립"], 17)
    # **근거 구간에는 미달이 없어야 한다** — 하한이 그 구간의 관측 최소에서 나왔기 때문이다.
    # 여기가 0 이 아니게 되면 그림의 「근거 구간」 음영이 거짓말을 하게 된다.
    basis = [r for k, r in F["계열"] if k[0] in BASIS_YEARS]
    chk("근거 구간 48개월에는 하한 미달이 0", sum(1 for r in basis if r < W2_FLOOR), 0)
    chk("근거 구간 48개월이 맞다", len(basis), 48)
    chk("근거 구간 최소가 하한의 출처 (3.8855)", round(min(basis), 4), 3.8855)
    chk("배율 최소 1.9435 (FACTS 158)", round(F["최소"][0], 4), 1.9435)
    chk("그 달이 2005-07", F["최소"][1], (2005, 7))
    chk("배율 최대 179.2678 (#10 §4)", round(F["최대"][0], 4), 179.2678)
    chk("그 달이 2020-05", F["최대"][1], (2020, 5))

    print("── 인수시험: 판정표가 발행된 판정과 같은가 ──")
    chk("기준 8건", len(VERDICTS), 8)
    chk("PASS 3 · FAIL 5",
        (sum(1 for r in VERDICTS if r[4]), sum(1 for r in VERDICTS if not r[4])), (3, 5))

    print("── 인수시험: 낡는 값·인과를 안 싣는다 (사고 31·83 · §3-5) ──")
    joined = " ".join(drawn_text())
    for word in ("팔로워", "가장 최근", "지금까지", "때문", "덕분", "영향으로", "원인"):
        chk("문면에 「%s」가 없다" % word, word in joined, False)
    chk("편수를 안 싣는다", "편" in joined.replace("편으로", ""), False)

    print("── 인수시험: 쓰는 글리프가 폰트에 실제로 있는가 (두부 방지) ──")
    try:
        from fontTools.ttLib import TTFont
        fam = plt.rcParams["font.family"]
        fam = fam[0] if isinstance(fam, (list, tuple)) else fam
        cand = [f.fname for f in font_manager.fontManager.ttflist if f.name == fam]
        cmap = set()
        for t in TTFont(cand[0], fontNumber=0)["cmap"].tables:
            cmap |= set(t.cmap.keys())
        for ch in (GLYPH_PASS, GLYPH_FAIL):
            chk("%s 가 %s 에 있다" % (ch, fam), ord(ch) in cmap, True)
    except ImportError:
        print("  (fontTools 가 없다 — **미실행**이지 통과가 아니다)")

    print("── 인수시험: #10 을 찾으러 갈 사람에게 표지를 준다 ──")
    joined2 = " ".join(drawn_text())
    chk("표가 #10 을 든다", any(r[0].startswith("#10") for r in VERDICTS), True)
    chk("그러면 #10 안내도 든다", "10_판정결과.md" in joined2, True)
    chk("「편으로는 아직 안 냈다」를 적는다", "아직 안 냈다" in joined2, True)

    print("── 인수시험: 그림이 실제로 만들어지는가 ──")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.png")
        build(p)
        chk("파일이 생겼다", os.path.exists(p), True)
        chk("빈 파일이 아니다", os.path.getsize(p) > 60000, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="링크드인 스페셜 한 장")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    F = build()
    print("만들었다: %s" % os.path.relpath(OUT, os.path.dirname(HERE)))
    print("  252개월 %d · W1 성립 %d · 판정 구간 %d개월 · W2 미성립 %d"
          % (F["개월"], F["W1성립"], F["판정개월"], F["W2미성립"]))

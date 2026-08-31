# -*- coding: utf-8 -*-
"""252개월 시계열 — **이 사이트가 가진 것 중 다른 데 없는 것을 첫 화면에 건다.**

왜 있는가
---------
첫 화면이 **방법만 말하고 데이터를 하나도 안 보여 준다.** 「공공 1차 데이터로 확인한다」는
문장 아래로 한참 내려가야 표가 나온다. **데이터를 내건 곳이 데이터를 안 보여 준다.**

그리고 지침 §1.3 이 브랜드의 답을 **「방법이 엄격하다」에서 「같은 대상을 오래 봤다」**로
옮겨 놨는데, **「오래」가 지면 어디에도 안 보인다.** 그 두께가 이 프로젝트의 자산이고
복제가 어려운 부분인데, 보이지 않으면 없는 것과 같다.

그래서 **252개월을 한 장에 건다.** 2005-01 ~ 2025-12, 인천항 공컨 수출÷수입 배율.

무엇을 주장하는가
-----------------
**값과 성립 여부만.** 「방향이 한 번도 안 뒤집혔다」(252/252)는 판정이고,
어느 달에 얼마였는지는 관측이다. **왜 그런지는 이 데이터가 답하지 않으므로 안 쓴다.**

세로축은 **로그**다. 1.94 와 179 를 한 축에 놓으면 선형에서는 아래쪽이 뭉갠다.
**로그는 차이를 실제보다 작아 보이게 한다** — 그 점을 지면 각주가 든다(#09 각주 2와 같은 규율).

왜 SVG 인가 — **색을 토큰에서 받아야 하기 때문이다.**
사이트는 밝은/어두운 모드가 있고 PNG 는 따라오지 못한다. 사고 68 이 그 자리였다.
그래서 `build_skyline.py` 와 같게 **색 리터럴을 하나도 안 쓴다.**

**이것은 장식이 아니다.** 스카이라인과 달리 **값을 지므로 `aria-hidden` 이 아니고**,
`role="img"` 과 이름·설명을 달고, 그림을 못 보는 독자를 위해 **표로 가는 링크**를 둔다.

값은 어디서 오는가
------------------
`judge_10_monthly.aggregate()` 와 `basis_10_monthly_floor.monthly()` 를 **그대로 부른다.**
**집계 규칙을 여기서 다시 쓰지 않는다** — 두 벌이면 갈라진다(사고 88).

닿지 않는 곳
------------
· **2026 을 안 그린다.** 잠정치이고 2026-01~05 는 강등 구간이다(§4). 창을 섞지 않는다.
· 로그축이라 **아래쪽 차이가 작아 보인다.** 각주가 그 사실을 든다.
· `--check` 는 「지금 데이터·코드로 만들면 같은 것이 나오는가」만 본다.
  **무엇으로 보이는지는 안 본다**(사고 73). 띄워 봐야 본 것이다.

  python analysis/build_series_chart.py           # 생성
  python analysis/build_series_chart.py --check   # 갈라졌는지
  python analysis/build_series_chart.py --selftest
"""

import argparse
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HUB = os.path.join(os.path.dirname(ROOT), "jisangj03-dev.github.io")
OUT = os.path.join(HUB, "_includes", "series252.html")

sys.path.insert(0, HERE)
from judge_10_monthly import read_rows, aggregate, YEARS, MONTHS   # noqa: E402
from basis_10_monthly_floor import monthly as basis_monthly, read_year, BASIS_YEARS  # noqa: E402

# 그림 좌표계. 값이 아니라 지면 치수다.
W, H = 900.0, 260.0
PAD_L, PAD_R, PAD_T, PAD_B = 46.0, 12.0, 16.0, 26.0
PLOT_W = W - PAD_L - PAD_R
PLOT_H = H - PAD_T - PAD_B

FLOOR = 3.88          # #10 W2 하한 (근거 구간 48개월 최소 3.8855 를 버림 — 사고 85)
GRID = (2, 5, 10, 30, 100)


def series():
    """252개월 (연,월,배율). 2005-01 ~ 2025-12. 외항 `ocCt=1`.

    **집계는 판정 스크립트의 것을 그대로 쓴다.** 여기서 다시 구현하지 않는다.
    """
    monthly, _combos, _coastal = aggregate(read_rows())      # 2005~2021
    pts = []
    for y in YEARS:
        for m in MONTHS:
            v = monthly[(y, m)]
            pts.append((y, m, v["수출"] / v["수입"]))
    for y in BASIS_YEARS:                                     # 2022~2025
        per = basis_monthly(read_year(y))
        for m in MONTHS:
            v = per[m]
            pts.append((y, m, v["수출"] / v["수입"]))
    return pts


def scale(pts):
    lo = min(r for _, _, r in pts)
    hi = max(r for _, _, r in pts)
    # 로그 축. 위아래로 조금 띄워 점이 테두리에 붙지 않게 한다.
    y0, y1 = math.log10(lo) - 0.06, math.log10(hi) + 0.06

    def X(i):
        return PAD_L + PLOT_W * (i / (len(pts) - 1.0))

    def Y(r):
        t = (math.log10(r) - y0) / (y1 - y0)
        return PAD_T + PLOT_H * (1.0 - t)

    return X, Y


def fmt(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def build():
    pts = series()
    X, Y = scale(pts)
    lo = min(pts, key=lambda p: p[2])
    hi = max(pts, key=lambda p: p[2])
    i_lo = pts.index(lo)
    i_hi = pts.index(hi)
    i_2022 = next(i for i, p in enumerate(pts) if p[0] == 2022 and p[1] == 1)

    o = []
    a = o.append
    name = "인천항 공컨테이너 수출÷수입 배율 · 2005-01~2025-12 · 252개월"
    desc = ("252개월 전부에서 수출 방향이 수입 방향을 앞섰다. "
            "월별 최소 %s배(%d-%02d) · 최대 %s배(%d-%02d). "
            "세로축은 로그다. 값은 아래 표와 정본 대장이 든다."
            % (fmt(lo[2]), lo[0], lo[1], fmt(hi[2]), hi[0], hi[1]))

    a('<!-- 생성됨. 손으로 고치지 마라 — analysis/build_series_chart.py -->')
    a('<figure class="series252">')
    a('<svg class="s252" viewBox="0 0 %g %g" role="img" aria-labelledby="s252t s252d" '
      'preserveAspectRatio="none">' % (W, H))
    a('<title id="s252t">%s</title>' % name)
    a('<desc id="s252d">%s</desc>' % desc)

    # 가로 눈금 — 배율 격자
    a('<g class="s252-grid">')
    for g in GRID:
        y = Y(g)
        if PAD_T <= y <= PAD_T + PLOT_H:
            a('<line x1="%g" y1="%.1f" x2="%g" y2="%.1f"/>' % (PAD_L, y, W - PAD_R, y))
            a('<text class="s252-tick" x="%g" y="%.1f">%d배</text>' % (PAD_L - 6, y + 3, g))
    a('</g>')

    # 우리가 처음 본 구간(2022~2025)을 가른다 — **이 편의 요점이 그 경계다.**
    a('<g class="s252-split">')
    a('<line x1="%.1f" y1="%g" x2="%.1f" y2="%g"/>' % (X(i_2022), PAD_T, X(i_2022), PAD_T + PLOT_H))
    # **구간 이름은 아래에 둔다.** 위에 두면 최대값 표시(2020-05)와 겹친다 —
    # 실제로 겹쳤고, 띄워 보고 알았다(사고 73: `--check` 는 무엇으로 보이는지 안 본다).
    a('<text class="s252-note" x="%.1f" y="%.1f">← 2005~2021 · 17년</text>'
      % (X(i_2022) - 8, PAD_T + PLOT_H - 7))
    a('<text class="s252-note s252-r" x="%.1f" y="%.1f">2022~2025 · 우리가 처음 본 구간 →</text>'
      % (X(i_2022) + 8, PAD_T + PLOT_H - 7))
    a('</g>')

    # #04 가 48개월에서 관측한 하한
    a('<line class="s252-floor" x1="%g" y1="%.1f" x2="%g" y2="%.1f"/>'
      % (PAD_L, Y(FLOOR), W - PAD_R, Y(FLOOR)))

    # 본선
    pth = " ".join("%s%.1f %.1f" % ("M" if i == 0 else "L", X(i), Y(r))
                   for i, (_, _, r) in enumerate(pts))
    a('<path class="s252-line" d="%s"/>' % pth)

    # 최소·최대 표시
    for i, p, cls in ((i_lo, lo, "s252-lo"), (i_hi, hi, "s252-hi")):
        a('<circle class="%s" cx="%.1f" cy="%.1f" r="3"/>' % (cls, X(i), Y(p[2])))
    a('<text class="s252-mark" x="%.1f" y="%.1f">%s배 · %d-%02d</text>'
      % (X(i_lo) + 6, Y(lo[2]) + 12, fmt(lo[2]), lo[0], lo[1]))
    a('<text class="s252-mark s252-r" x="%.1f" y="%.1f">%s배 · %d-%02d</text>'
      % (X(i_hi) - 6, Y(hi[2]) - 7, fmt(hi[2]), hi[0], hi[1]))

    # 연도 눈금 — 5년마다
    a('<g class="s252-years">')
    for i, (y, m, _) in enumerate(pts):
        if m == 1 and y % 5 == 0:
            a('<text class="s252-tick" x="%.1f" y="%g">%d</text>' % (X(i), H - 8, y))
    a('</g>')
    a('</svg>')
    a('<figcaption>')
    # **#10 을 링크하지 않는다 — 그 편은 판정만 끝났고 발행본이 없다.**
    # 없는 지면으로 보내는 링크는 「있다」고 말하는 것과 같다.
    # 대신 **어디까지 됐는지를 그대로 적는다.** 그것이 이 사이트가 파는 것에 가깝다.
    a('<strong>252개월 · 2005-01~2025-12.</strong> 인천항 공(빈)컨테이너 수출 방향 TEU ÷ 수입 방향 TEU, '
      '외항(<code>ocCt=1</code>). <strong>252개월 전부에서 수출 방향이 앞섰다.</strong> '
      '2022~2025 는 <a href="{{ \'/reports/\' | relative_url }}">#04</a> 가 발행했고, '
      '<strong>2005~2021 은 판정까지 끝났고 발행본은 아직 없다</strong>(2026-08-31 · 기준 선커밋 · '
      '판정 문서와 재현 코드는 저장소에 있다). '
      '점선은 #04 가 48개월에서 관측한 하한 3.88배다. '
      '<strong>그 하한은 그 48개월의 성질이었다</strong> — 앞 17년의 최소는 %s배(%d-%02d)로 그 절반 아래다. '
      '세로축은 로그이고, <strong>로그는 차이를 실제보다 작아 보이게 한다.</strong> '
      '왜 그런 값인지는 이 데이터로 판별할 수 없어 쓰지 않는다. '
      '<a href="{{ \'/verify/\' | relative_url }}">기준을 먼저 커밋하는 방법 →</a>'
      % (fmt(lo[2]), lo[0], lo[1]))
    a('</figcaption>')
    a('</figure>')
    return "\n".join(o) + "\n", pts, lo, hi


def selftest() -> int:
    fails = []

    def chk(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))
        print("  %-50s %s" % (label, "OK" if got == want else "FAIL"))

    pts = series()
    chk("252개월", len(pts), 252)
    chk("첫 달 2005-01", pts[0][:2], (2005, 1))
    chk("끝 달 2025-12", pts[-1][:2], (2025, 12))
    chk("2026 을 안 그린다", any(p[0] >= 2026 for p in pts), False)
    chk("전부 수출 우위 (배율 > 1)", all(r > 1 for _, _, r in pts), True)

    lo = min(pts, key=lambda p: p[2])
    chk("최소가 2005-07", lo[:2], (2005, 7))
    chk("최소값이 #10 판정과 같다", round(lo[2], 4), 1.9435)

    txt, _, _, _ = build()
    # **편 번호(`#10`)는 색이 아니다.** 처음엔 `"#" in txt` 로 봤다가 그것에 걸렸다 —
    # 넓게 잡은 검사는 오탐을 내고, **오탐을 내는 검사는 무시당한다**(§3-5).
    import re as _re
    chk("색 리터럴이 없다", _re.findall(r"#[0-9A-Fa-f]{3,8}\b", txt), [])
    chk("`rgb(`·`hsl(` 도 없다", ("rgb(" in txt or "hsl(" in txt), False)
    chk("장식이 아니다 — aria-hidden 을 안 쓴다", "aria-hidden" in txt, False)
    chk("이름과 설명을 단다", ('role="img"' in txt and "<title" in txt and "<desc" in txt), True)
    chk("로그축임을 지면이 말한다", "로그" in txt, True)
    chk("인과를 안 쓴다", ("때문에" in txt or "로 인해" in txt), False)

    print("\n  실패 %d" % len(fails))
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    text, pts, lo, hi = build()
    old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if a.check:
        if old == text:
            print("일치 — 지금 데이터·코드로 만들면 같은 것이 나온다.")
            return 0
        print("**갈라졌다** — `python analysis/build_series_chart.py` 로 다시 만든다.")
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("-> %s  (%d B)" % (OUT, len(text)))
    print("   %d개월 · 최소 %s배(%d-%02d) · 최대 %s배(%d-%02d)"
          % (len(pts), fmt(lo[2]), lo[0], lo[1], fmt(hi[2]), hi[0], hi[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

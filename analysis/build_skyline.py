# -*- coding: utf-8 -*-
"""제호 스카이라인 — **사이트가 열리는 순간 항구로 읽히게 한다.**

왜 있는가
---------
2026-08-30에 밖의 항만 지면을 여럿 열어 봤다. **전부 사진으로 항구를 낸다** —
로테르담은 전면 항공사진, 롱비치는 짙은 남색으로 덮은 항공사진을 **질감**으로 쓴다.
지면을 열면 1초 안에 「항구」가 온다.

**우리는 그 사진을 쓸 수 없다.** 남의 사진은 저작권이 있고, 자체 촬영본은 없다.
그렇다고 아무 항구 사진이나 사 오면 **그것이 인천항이라는 보장이 없다** —
인천항을 확인해 발행한다면서 어느 항구인지 모르는 사진을 거는 것은 앞뒤가 안 맞는다.

그래서 **그린다.** 롱비치가 사진에서 뽑아 쓰는 것이 결국 **질감**이라면,
질감은 사진 없이도 만들 수 있다.

무엇을 주장하는가 — **아무것도**
--------------------------------
**이것은 장식이다.** 크레인 대수·위치·높이·컨테이너 수, 어느 것도 인천항의 값이 아니다.
그래서 `aria-hidden` 이고, 숫자를 하나도 안 쓰고, **글자를 하나도 안 넣는다.**
읽을 것이 없으면 읽고 해석할 것도 없다.

**그런데 왜 크레인 모양은 단면도와 같은가.** 같은 기호를 두 자리에서 쓰면 그것이
「이 사이트의 기호」가 되기 때문이다. 단면도의 크레인도 기호이고(대수를 안 주장한다)
여기 크레인도 기호다. **둘이 다른 모양이면 하나는 실물처럼 보이기 시작한다.**

닿지 않는 곳
------------
· **배를 안 그린다.** 단면도가 「흘수를 몰라 배를 안 그린다」고 적었다.
  장식이라고 거기서 배를 그리면, 그 규율이 장식 앞에서는 접힌다는 뜻이 된다.
· 색은 전부 토큰이다. 리터럴을 쓰면 어두운 모드에서 사라지거나 튄다(사고 68).
· **`--check` 가 보는 것은 「지금 코드로 만들면 같은 것이 나오는가」뿐이다.**
  데이터에서 오지 않으므로 낡을 일은 없지만, 코드를 고치고 안 돌리면 갈라진다.

  python analysis/build_skyline.py            # 생성
  python analysis/build_skyline.py --check    # 갈라졌는지
  python analysis/build_skyline.py --selftest
"""

import argparse
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(ROOT, "..", "jisangj03-dev.github.io")
OUT = os.path.join(HUB, "_includes", "skyline.html")

# 링크 카드에도 **같은 그림**을 쓴다. 손으로 복제하면 같은 그림이 두 자리에 있고
# 한쪽만 갱신된다(사고 31). 카드는 헤드리스 크롬이 단독 렌더라 `include` 를 못 쓰므로
# 표지 사이를 갈아 끼운다 — 카드 표가 쓰는 것과 같은 수법이다.
CARD = os.path.join(HUB, "_og", "card.html")
CARD_BEGIN = "<!-- 카드하늘:시작 (생성됨. 손으로 고치지 마라 — analysis/build_skyline.py) -->"
CARD_END = "<!-- 카드하늘:끝 -->"

# **액자에 맞춰 그린다.** [2026-08-30] 첫 판은 1600×92(가로:세로 17.4)로 그려 놓고
# 660×118 자리(5.6)에 `slice` 로 넣었다 — 결과는 **그림의 32%만 보이는 것**이었다.
# 크레인 다섯 중 하나 반만 나왔다. 자리 비율에 맞춰 구성을 다시 잡고, `meet` 로 바꿔
# **자르지 않는다.** 액자를 정하고 그 안에 그리는 것이 순서다.
W, H = 900.0, 172.0
GROUND = H - 16.0        # 수평선. 그 아래는 여백 — 그림이 밴드 바닥에 붙지 않게.

# 크레인 — (x, 높이). 리듬만 있고 뜻은 없다.
CRANES = ((243, 132), (516, 110), (790, 126))
# 컨테이너 더미 — (x, 단수, 열수). 역시 뜻은 없다.
STACKS = ((44, 3, 4), (352, 2, 3), (620, 4, 3), (858, 2, 1))
BOX_W, BOX_H, BOX_G = 30.0, 12.0, 2.6


def crane(cx, h):
    """단면도와 **같은 기호**. 정면이다 — 다리 둘, 거더, A 형 탑."""
    lw = h * 0.20
    gw = lw + h * 0.13
    gird = GROUND - h * 0.70
    apex = GROUND - h
    sill = GROUND - h * 0.13
    out = []

    def L(x1, y1, x2, y2):
        out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                   % (x1, y1, x2, y2))

    L(cx - lw, GROUND, cx - lw, gird)
    L(cx + lw, GROUND, cx + lw, gird)
    L(cx - lw, sill, cx + lw, sill)
    L(cx - gw, gird, cx + gw, gird)
    L(cx - gw + gw * 0.25, gird, cx, apex)
    L(cx + gw - gw * 0.25, gird, cx, apex)
    L(cx, apex, cx, gird)
    return "".join(out)


def stack(x, rows, cols):
    """컨테이너 더미. **세지 마라** — 리듬이지 수량이 아니다."""
    out = []
    for r in range(rows):
        # 위로 갈수록 한 칸씩 좁아진다. 실제 야적이 그렇게 쌓여서가 아니라,
        # 네모난 덩어리가 그림에서 너무 무거워서다.
        n = max(1, cols - (r // 2))
        y = GROUND - (r + 1) * (BOX_H + BOX_G)
        for c in range(n):
            out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                       % (x + c * (BOX_W + BOX_G), y, BOX_W, BOX_H))
    return "".join(out)


def build_card_block():
    """카드용 — 판형을 같이 넣는다. 카드에는 CSS 토큰이 없다(단독 문서다).

    **밝은 판 하나만 쓴다.** 링크 카드는 남의 화면에서 우리 테마와 무관하게 뜨고,
    카드 배경이 `#FCFCFA` 로 고정돼 있다. 여기서 `prefers-color-scheme` 을 따라가면
    **밝은 카드 위에 어두운 테마 색이 얹힌다.**
    """
    return "\n".join([
        CARD_BEGIN,
        "<style>",
        "  .card-sky{position:absolute;top:176px;right:60px;width:470px;height:auto}",
        # 색은 사이트의 밝은 판 토큰값과 같다. 카드가 늘 밝은 배경이라 그쪽으로 고정한다.
        "  .card-sky .sky-crane line{stroke:#5D666D;opacity:.42;stroke-width:2;",
        "    stroke-linecap:round;fill:none}",
        "  .card-sky .sky-box rect{fill:#C3C9CC}",
        "  .card-sky .sky-horizon{stroke:#C3C9CC;stroke-width:1}",
        "</style>",
        build().replace('class="mast-sky"', 'class="card-sky"').strip(),
        CARD_END,
    ]) + "\n"


def splice_card(text, block):
    """표지 사이를 갈아 끼운다. **표지가 없으면 쓰지 않는다.**"""
    i, j = text.find(CARD_BEGIN), text.find(CARD_END)
    if i < 0 or j < 0:
        return None
    return text[:i] + block.rstrip("\n") + text[j + len(CARD_END):]


def build():
    p = ['<!-- 생성됨. 손으로 고치지 마라 — analysis/build_skyline.py -->',
         '<!-- 장식이다. 크레인 대수도 컨테이너 수도 인천항의 값이 아니다. -->',
         '<svg class="mast-sky" viewBox="0 0 %.0f %.0f" preserveAspectRatio="xMidYMax meet" '
         'aria-hidden="true" focusable="false">' % (W, H),
         '<g class="sky-box">%s</g>'
         % "".join(stack(x, r, c) for x, r, c in STACKS),
         '<g class="sky-crane">%s</g>'
         % "".join(crane(x, h) for x, h in CRANES),
         # 수평선 — 크레인이 무언가 위에 서 있어야 한다. 없으면 떠 보인다.
         '<line class="sky-horizon" x1="0" y1="%.1f" x2="%.0f" y2="%.1f"/>'
         % (GROUND, W, GROUND),
         '</svg>']
    return "\n".join(p) + "\n"


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-50s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    s = build()
    print("── 인수시험: 장식은 장식이어야 한다 ──")
    chk("aria-hidden 이다", 'aria-hidden="true"' in s, True)
    chk("초점을 안 받는다", 'focusable="false"' in s, True)
    # **글자가 하나도 없어야 한다.** 읽을 것이 없으면 해석할 것도 없다.
    chk("text 요소가 없다", "<text" in s, False)
    chk("배를 안 그린다", "ship" in s.lower(), False)
    # 색 리터럴 금지 — 어두운 모드에서 사라지거나 튄다(사고 68).
    chk("색 리터럴이 없다", bool(re.search(r'#[0-9A-Fa-f]{3,6}|rgb\(', s)), False)
    chk("fill/stroke 를 인라인으로 안 준다",
        bool(re.search(r'\b(fill|stroke)\s*=', s)), False)

    print("── 인수시험: 그려진 것 ──")
    # 수평선 한 줄이 더 있다.
    chk("크레인 %d대 + 수평선" % len(CRANES), s.count("<line "),
        len(CRANES) * 7 + 1)
    boxes = sum(sum(max(1, c - (r // 2)) for r in range(rw))
                for _, rw, c in STACKS)
    chk("컨테이너 %d개" % boxes, s.count("<rect x="), boxes)

    print("── 인수시험: 도형이 액자 안에 있다 ──")
    xs = [float(v) for v in re.findall(r'\bx1?="(-?[\d.]+)"', s)]
    ys = [float(v) for v in re.findall(r'\by1?="(-?[\d.]+)"', s)]
    xs += [float(a) + float(b) for a, b in
           re.findall(r'<rect x="([\d.]+)" y="[\d.]+" width="([\d.]+)"', s)]
    chk("x 가 액자를 안 넘는다", max(xs) <= W and min(xs) >= 0, True)
    chk("y 가 액자를 안 넘는다", max(ys) <= H and min(ys) >= 0, True)

    print("── 인수시험: 링크 카드용 ──")
    c = build_card_block()
    chk("카드 블록도 aria-hidden 이다", 'aria-hidden="true"' in c, True)
    chk("카드 블록에도 글자가 없다", "<text" in c, False)
    # 카드는 **늘 밝은 배경**이다. 어두운 테마를 따라가면 밝은 카드에 어두운 색이 얹힌다.
    chk("카드는 테마를 따라가지 않는다", "prefers-color-scheme" in c, False)
    chk("카드 판형이 같이 들어간다", "card-sky" in c and "<style>" in c, True)
    chk("사이트용 class 가 안 남는다", "mast-sky" in c, False)
    # 표지가 없으면 **쓰지 않는다** — 조용히 덧붙이면 문서가 깨진다.
    chk("표지가 없으면 갈아 끼우지 않는다", splice_card("<p>표지 없음</p>", c), None)
    demo = "<a>" + CARD_BEGIN + "옛것" + CARD_END + "</a>"
    chk("표지가 있으면 그 사이만 바뀐다",
        splice_card(demo, "새것").startswith("<a>새것") and
        splice_card(demo, "새것").endswith("</a>"), True)

    print("── 인수시험: 두 번 만들면 같다 ──")
    chk("멱등", build(), s)
    chk("카드도 멱등", build_card_block(), c)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    text = build()
    old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""

    card_old = io.open(CARD, encoding="utf-8").read() if os.path.exists(CARD) else ""
    card_new = splice_card(card_old, build_card_block()) if card_old else ""
    # **표지가 없으면 「모른다」다.** 조용히 통과시키면 카드가 낡은 채로 남는다(사고 26).
    card_state = ("표지 없음" if (card_old and card_new is None)
                  else "일치" if card_new == card_old else "다르다")

    if a.check:
        same = old == text and card_state == "일치"
        print("조각 " + ("일치" if old == text else "**다르다 — 다시 생성해야 한다**"))
        print("링크 카드 " + ("일치" if card_state == "일치"
                          else "**%s — 다시 생성해야 한다**" % card_state))
        return 0 if same else 1

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print("-> %s  (%d B)" % (OUT, len(text)))
    if card_new and card_new != card_old:
        io.open(CARD, "w", encoding="utf-8", newline="\n").write(card_new)
        print("-> %s  (스카이라인 구획)" % CARD)
        print("   **카드가 바뀌었다. `assets/og.png` 를 다시 찍어야 한다** — 절차는 `_og/README.md`.")
    elif card_new is None and card_old:
        print("   **카드에 표지가 없다** — `%s` 를 카드에 넣어야 갈아 끼운다." % CARD_BEGIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())

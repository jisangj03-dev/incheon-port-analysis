"""허브의 `/berths/` 지면을 생성한다 — **인천항 부두 구조.**

왜 이 지면이 생겼나
-------------------
지난 라운드에 부두 구성도를 그리며 스스로 이렇게 적었다 —

  **「지도가 아니다. 위치·거리·방위를 주장하지 않는다.」**

그 제한의 이유는 겸손이 아니라 **출처가 없어서**였다. 우리가 가진 것은 처리실적뿐이었다.
이제 인천지방해양수산청 부두현황을 받았으므로(`collect_port_facilities.py`),
**주장할 수 있는 것이 늘었다.**

  **여전히 지도는 아니다.** 위치·방위는 이 소스에도 없다.
  **그러나 길이는 있다.** 안벽 길이는 미터로 공표돼 있고, 그래서 **축척으로 그릴 수 있다.**
  이 지면의 그림 2 가 그것이다 — 인천항 컨테이너 안벽을 **같은 자로 나란히** 놓은 것.

**그리고 이 지면이 처음으로 시설과 실적을 맞댄다.** 둘 다 같은 기관(인천지방해양수산청)이
같은 단위(천TEU/년)로 낸다. 그래도 **능력과 실적은 다른 개념**이고, 그 문장을 지면이 든다.

    python analysis/build_berths_page.py
    python analysis/build_berths_page.py --check
    python analysis/build_berths_page.py --selftest

**절 제목을 「1.」「3.」으로 달지 않는다** — `lint_publish.py` 의 `conclusion_zones()` 가
그것을 보고서 §1·§3 으로 읽는다(§2.5 골격 계약). 표·그림에 번호를 단다.
"""
from __future__ import annotations
import argparse
import csv
import io
import os
import re
import sys

import htmltable

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BERTHS = os.path.join("analysis", "port_container_berths.csv")
REGIONS = os.path.join("analysis", "port_regions.csv")
SRC = os.path.join("analysis", "port_facilities_sources.csv")
TERMINALS = os.path.join("analysis", "terminal_monthly.csv")
OUT = os.path.join("..", "jisangj03-dev.github.io", "berths", "index.md")

GH = "https://github.com/jisangj03-dev/incheon-port-analysis/blob/main"
# 구역 순서와 색. `/terminals/` 의 부두군 색과 같은 계단을 쓴다 — 같은 항만의 부분이다.
ZONE_ORDER = ["신항", "남항"]


def load(path):
    return list(csv.DictReader(io.open(path, encoding="utf-8-sig")))


def num(s):
    s = (s or "").replace(",", "").strip()
    if not s or s in ("-", "–"):
        return None
    return float(s) if re.match(r"^-?\d+(\.\d+)?$", s) else None


def f(v, nd=0):
    return "–" if v is None else f"{v:,.{nd}f}"


def berth_count(cap: str):
    """`40,000×1 (3천TEU이상)` -> 1. **곱셈 기호가 두 종류다** — `×` 와 `X`.

    원문에 둘 다 나온다(`3,000X5` · `40,000×1`). 하나만 보면 **조용히 0이 된다.**
    """
    m = re.search(r"[×xX]\s*(\d+)", cap or "")
    return int(m.group(1)) if m else None


def is_closed(row) -> bool:
    return "폐쇄" in (row.get("주요취급화물") or "")


def terminals_rollup(rows):
    """안벽 구간들을 터미널 단위로 묶는다. 길이는 더하고, 선석 수도 더한다."""
    out = {}
    for r in rows:
        k = r["명칭"].strip()
        t = out.setdefault(k, {"코드": k, "구역": r["구역"], "구간": [],
                               "길이": 0.0, "선석": 0, "수심": set(), "폐쇄": False})
        ln = num(r["부두길이_m"]) or 0.0
        nb = berth_count(r["동시접안능력"])
        t["구간"].append({"길이": ln, "능력": r["동시접안능력"], "선석": nb,
                          "수심": num(r["전면수심_DL_m"])})
        t["길이"] += ln
        t["선석"] += nb or 0
        d = num(r["전면수심_DL_m"])
        if d is not None:
            t["수심"].add(d)
        t["폐쇄"] = t["폐쇄"] or is_closed(r)
    order = {c: i for i, c in enumerate(["SNCT", "HJIT", "ICT", "E1CT", "SICT"])}
    return sorted(out.values(), key=lambda t: (ZONE_ORDER.index(t["구역"])
                                               if t["구역"] in ZONE_ORDER else 9,
                                               order.get(t["코드"], 99)))


# ── 그림 ────────────────────────────────────────────────────────────────────

def quay_svg(terms):
    """그림 2 — **컨테이너 안벽을 같은 자로 나란히 놓는다.**

    가로축이 **미터**다. 이것이 이 그림의 전부이고, 이것 말고는 아무것도 주장하지 않는다 —
    부두가 어디 있는지, 어느 방향으로 뻗었는지, 서로 얼마나 떨어졌는지는
    **이 소스에 없고 그래서 그리지 않는다.**

    안벽 구간을 따로 그리는 이유: 한 터미널의 안벽이 **접안능력이 다른 구간으로 나뉘어**
    공표된다. SNCT 는 300m(4만DWT급 1척)와 500m(3만DWT급 2척)로 나뉜다.
    합쳐서 800m 한 덩어리로 그리면 **그 구조가 사라진다.**
    """
    if not terms:
        return ""
    W, LAB, ROW = 1000.0, 132.0, 62.0
    maxlen = max(t["길이"] for t in terms) or 1.0
    plot = W - LAB - 92          # 오른쪽에 수심·선석 주석 자리
    scale = plot / maxlen
    H = ROW * len(terms) + 40

    p = ['<div class="quayfig">',
         f'<svg class="quaymap" viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
         f'aria-label="인천항 컨테이너 터미널의 안벽 길이 비교 — 미터 축척">']
    # 자 (눈금) — 축척이라는 것을 눈으로 알 수 있어야 한다.
    step = 200
    for gx in range(0, int(maxlen) + step, step):
        x = LAB + gx * scale
        if x > LAB + plot + 1:
            break
        p.append(f'<line class="tick" x1="{x:.1f}" y1="16" x2="{x:.1f}" y2="{H - 22:.0f}"/>')
        p.append(f'<text class="ticklbl" x="{x:.1f}" y="12" text-anchor="middle">{gx:,}</text>')
    p.append(f'<text class="tickunit" x="{LAB - 8:.0f}" y="12" text-anchor="end">m</text>')

    for i, t in enumerate(terms):
        y = 24 + i * ROW
        cls = " closed" if t["폐쇄"] else ""
        zone_i = ZONE_ORDER.index(t["구역"]) if t["구역"] in ZONE_ORDER else 2
        p.append(f'<text class="qcode" x="0" y="{y + 22:.0f}">{t["코드"]}</text>')
        p.append(f'<text class="qzone" x="0" y="{y + 38:.0f}">{t["구역"]}</text>')
        x = LAB
        for seg in t["구간"]:
            w = seg["길이"] * scale
            p.append(f'<rect class="qseg z{zone_i}{cls}" x="{x:.1f}" y="{y:.0f}" '
                     f'width="{max(w - 2, 1):.1f}" height="30" rx="1"/>')
            if w > 54:
                p.append(f'<text class="qlen" x="{x + w / 2 - 1:.1f}" y="{y + 20:.0f}" '
                         f'text-anchor="middle">{seg["길이"]:,.0f}</text>')
            x += w
        depth = "·".join(f"{d:.1f}" for d in sorted(t["수심"]))
        note = f'{t["길이"]:,.0f} m · 수심 {depth} m · {t["선석"]}선석'
        if t["폐쇄"]:
            note += " · 폐쇄"
        p.append(f'<text class="qnote" x="{LAB:.0f}" y="{y + 47:.0f}">{note}</text>')
    p.append("</svg>")
    p.append(quay_svg_narrow(terms, maxlen))
    p.append("</div>")
    return "\n".join(p)


def quay_svg_narrow(terms, maxlen):
    """좁은 화면용 — **같은 그림을 줄이지 않고 편다.**

    viewBox 1000 을 390px 에 넣으면 배율이 0.375 라 글자가 10px 밑으로 내려간다.
    그래서 폭을 600 으로 줄이고(배율 0.625) 라벨을 막대 **위**로 올린다.
    값과 축척은 같다 — 배치만 다르다.
    """
    NW, ROW = 600.0, 100.0
    scale = NW / (maxlen or 1)
    H = ROW * len(terms) + 26
    p = [f'<svg class="quaymap narrow" viewBox="0 0 {NW:.0f} {H:.0f}" role="img" '
         f'aria-label="인천항 컨테이너 터미널의 안벽 길이 비교 — 미터 축척">']
    for gx in range(0, int(maxlen) + 200, 200):
        x = gx * scale
        if x > NW + 1:
            break
        p.append(f'<line class="tick" x1="{x:.1f}" y1="18" x2="{x:.1f}" y2="{H - 16:.0f}"/>')
        p.append(f'<text class="ticklbl" x="{x + 3:.1f}" y="13">{gx:,}</text>')
    for i, t in enumerate(terms):
        y = 26 + i * ROW
        cls = " closed" if t["폐쇄"] else ""
        zi = ZONE_ORDER.index(t["구역"]) if t["구역"] in ZONE_ORDER else 2
        p.append(f'<text class="qcode" x="0" y="{y + 18:.0f}">{t["코드"]}</text>')
        p.append(f'<text class="qzone" x="{NW:.0f}" y="{y + 18:.0f}" '
                 f'text-anchor="end">{t["구역"]}</text>')
        x = 0.0
        for seg in t["구간"]:
            w = seg["길이"] * scale
            p.append(f'<rect class="qseg z{zi}{cls}" x="{x:.1f}" y="{y + 28:.0f}" '
                     f'width="{max(w - 2, 1):.1f}" height="26" rx="1"/>')
            if w > 62:
                p.append(f'<text class="qlen" x="{x + w / 2 - 1:.1f}" y="{y + 47:.0f}" '
                         f'text-anchor="middle">{seg["길이"]:,.0f}</text>')
            x += w
        depth = "·".join(f"{d:.1f}" for d in sorted(t["수심"]))
        note = f'{t["길이"]:,.0f} m · 수심 {depth} m · {t["선석"]}선석'
        if t["폐쇄"]:
            note += " · 폐쇄"
        p.append(f'<text class="qnote" x="0" y="{y + 76:.0f}">{note}</text>')
    p.append("</svg>")
    return "\n".join(p)


SECT_ORDER = ("SNCT", "HJIT", "ICT", "E1CT", "SICT")


def section_cols(terms):
    """단면에 세울 기둥. **터미널이 아니라 「구간」이 단위다.**

    한 터미널의 안벽이 접안능력·수심이 다른 구간으로 나뉘어 공표된다.
    터미널 하나를 한 덩어리로 그리면 **수심이 구간마다 다를 때 그 사실이 사라진다.**
    지금 자료에서는 터미널마다 수심이 하나뿐이라 결과가 같지만,
    **같아 보이는 것과 같은 것은 다르다** — 다음 달 자료가 갈라지면 그림이 따라가야 한다.

    반환: [{코드, 구역, 길이, 수심, 폐쇄, 능력, 첫구간}] — `첫구간` 은 이름표를 어디에
    한 번만 찍을지 정하는 데 쓴다.
    """
    by = {t["코드"]: t for t in terms}
    cols = []
    for code in SECT_ORDER:
        t = by.get(code)
        if not t:
            continue
        for i, seg in enumerate(t["구간"]):
            d = seg.get("수심")
            if not d:
                continue          # 수심을 모르는 구간은 **그리지 않는다.** 0 으로 세우지 않는다.
            cols.append({"코드": code, "구역": t["구역"], "길이": seg["길이"],
                         "수심": d, "폐쇄": t["폐쇄"], "능력": seg.get("능력", ""),
                         "첫구간": i == 0, "구간수": len(t["구간"])})
    return cols


def section_svg(terms, narrow=False):
    """그림 3 — **안벽 앞 수심을 같은 자로 놓는다.** 가로 m · 세로 m.

    왜 이 그림인가
    --------------
    밖의 항만 지면은 항구를 **사진**으로 낸다 — 로테르담은 전면 항공사진, 롱비치는
    짙게 덮은 항공사진을 질감으로 쓴다(2026-08-30 직접 열어 확인했다).
    **우리는 그 사진을 쓸 수 없고**(저작권) 자체 촬영본도 없다.

    그런데 우리에겐 저들이 지면에 잘 안 내는 것이 있다 — **선석 단위의 안벽 길이와
    전면수심.** 둘 다 공표값이라 **축척으로 그릴 수 있다.** 사진 대신 도면으로 간다.

    무엇을 주장하는가
    -----------------
    가로 = 안벽 길이(m) · 세로 = 전면수심(m). **그 둘뿐이다.**

    **주장하지 않는 것을 먼저 적는다:**
      · **지도가 아니다.** 부두의 위치·방위·서로 간의 거리는 이 소스에 없다.
        왼쪽에서 오른쪽 순서는 **공표자료의 구역 순서**이지 지리가 아니다.
      · **해저 지형이 아니다.** 공표값은 안벽 **앞** 수심 한 숫자이고, 그 앞바다가
        어떤 모양으로 깊어지는지는 모른다. **계단으로 그린 것은 값이 계단이라서**다.
      · **크레인은 기호다.** 대수·위치·규격은 이 소스에 없다. 구간마다 같은 모양을
        하나씩 놓았다 — **세면 안 되는 그림**이라는 뜻이다.
      · **배를 그리지 않았다.** 흘수는 이 소스에 없다. 배를 그리면 그 순간
        「이 수심에 이 배가 들어온다」는, 우리가 확인하지 않은 말이 된다.

    기준면은 **DL(기본수준면)** 이다 — 공표자료가 그 기준으로 낸다. 조위에 따라 실제
    수심은 이보다 깊어지고, **그 폭은 이 소스에 없다.** 그래서 기준면 줄에 이름을 적는다.
    """
    cols = section_cols(terms)
    if not cols:
        return ""

    W = 1000.0
    LAB = 88.0
    PAD = 18.0
    VS = 13.0 if narrow else 17.0     # 세로 1 m 당 픽셀
    DECK = 28.0
    CRANE = 52.0
    # [2026-08-30 실측] 첫 판은 `Y0 = 96` 이라 **터미널 이름이 viewBox 위로 잘렸다.**
    # 화면에 그려 보기 전에는 안 보였다 — 좌표만으로는 아무 문제가 없었다.
    # 이름은 크레인 **위**에 서야 하므로 수면 높이를 그 합만큼 내린다.
    NAME_DY, ZONE_DY = CRANE + 26, CRANE + 10
    Y0 = 24 + DECK + NAME_DY
    total = sum(c["길이"] for c in cols) or 1.0
    plot = W - LAB - PAD
    hs = plot / total                  # 가로 1 m 당 픽셀
    dmax = max(c["수심"] for c in cols)
    bed_bottom = Y0 + dmax * VS + 34
    H = bed_bottom + 44

    p = ['<div class="portfig sectfig">',
         '<svg class="sectmap%s" viewBox="0 0 %.0f %.0f" role="img" '
         'aria-label="인천항 컨테이너 안벽의 길이와 전면수심 단면. '
         '가로축은 안벽 길이 미터, 세로축은 기본수준면 아래 수심 미터. '
         '신항 SNCT·HJIT 와 남항 ICT 가 14.0 m, E1CT 가 12.0 m, '
         '폐쇄된 SICT 가 11.0 m 다. 지도가 아니다.">'
         % (" narrow" if narrow else "", W, H)]

    # 물에 깊이감을 준다 — 표면이 밝고 아래가 짙다. **색은 토큰에서 온다**(사고 68).
    p.append('<defs>'
             '<linearGradient id="seaG" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" class="sea-top"/>'
             '<stop offset="1" class="sea-bot"/></linearGradient>'
             '</defs>')
    p.append('<defs><pattern id="bedH" width="8" height="8" '
             'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<line class="bedhatch" x1="0" y1="0" x2="0" y2="8"/></pattern></defs>')

    # ── 물과 해저 ───────────────────────────────────────────────────────
    # 수면은 한 줄, 바닥은 계단. 그 사이가 물이다.
    steps = []
    x = LAB
    for c in cols:
        w = c["길이"] * hs
        yb = Y0 + c["수심"] * VS
        steps.append((x, x + w, yb))
        x += w
    xend = x

    sea = ["%.1f,%.1f" % (LAB, Y0)]
    for x0, x1, yb in steps:
        sea += ["%.1f,%.1f" % (x0, yb), "%.1f,%.1f" % (x1, yb)]
    sea.append("%.1f,%.1f" % (xend, Y0))
    p.append('<polygon class="sea" points="%s"/>' % " ".join(sea))

    bedline = []
    for x0, x1, yb in steps:
        bedline += ["%.1f,%.1f" % (x0, yb), "%.1f,%.1f" % (x1, yb)]
    p.append('<polygon class="bed" points="%s %.1f,%.1f %.1f,%.1f"/>'
             % (" ".join(bedline), xend, bed_bottom, LAB, bed_bottom))
    p.append('<polyline class="bedline" points="%s"/>' % " ".join(bedline))

    # ── 세로 눈금 (수심) ────────────────────────────────────────────────
    d = 0
    while d <= int(dmax) + 1:
        y = Y0 + d * VS
        p.append('<line class="dtick" x1="%.0f" y1="%.1f" x2="%.0f" y2="%.1f"/>'
                 % (LAB - 5, y, W - PAD, y))
        p.append('<text class="dlbl" x="%.0f" y="%.1f" text-anchor="end">%s</text>'
                 % (LAB - 10, y + 4, "0" if d == 0 else "−%d" % d))
        d += 2
    p.append('<text class="dunit" x="%.0f" y="%.1f" text-anchor="end">m</text>'
             % (LAB - 10, Y0 - 13))

    # 기준면 — 이 그림에서 가장 중요한 한 줄이다. 수심은 이 선에서 잰 값이다.
    p.append('<line class="datum" x1="%.0f" y1="%.1f" x2="%.0f" y2="%.1f"/>'
             % (LAB, Y0, W - PAD, Y0))
    p.append('<text class="datumlbl" x="%.0f" y="%.1f">DL 기본수준면 0 m</text>'
             % (W - PAD - 4, Y0 - 7))

    # ── 부두 ────────────────────────────────────────────────────────────
    x = LAB
    i = 0
    while i < len(cols):
        c = cols[i]
        # 같은 터미널의 연속 구간은 이름표를 한 번만 찍는다.
        span = 1
        while i + span < len(cols) and cols[i + span]["코드"] == c["코드"]:
            span += 1
        wtot = sum(cols[i + k]["길이"] for k in range(span)) * hs
        closed = c["폐쇄"]
        cls = " closed" if closed else ""

        p.append('<rect class="deck%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f"/>'
                 % (cls, x, Y0 - DECK, wtot, DECK))
        # 안벽 벽면 — 터미널 양끝에만. 구간 경계는 벽이 아니다.
        for xx in (x, x + wtot):
            yb = Y0 + max(cols[i + k]["수심"] for k in range(span)) * VS
            p.append('<line class="quaywall%s" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                     % (cls, xx, Y0 - DECK, xx, yb))

        cx = x + wtot / 2
        p.append('<text class="sname%s" x="%.1f" y="%.1f" text-anchor="middle">%s</text>'
                 % (cls, cx, Y0 - DECK - NAME_DY, c["코드"]))
        p.append('<text class="szone" x="%.1f" y="%.1f" text-anchor="middle">%s</text>'
                 % (cx, Y0 - DECK - ZONE_DY, c["구역"] + (" 폐쇄" if closed else "")))

        # 크레인 기호 — 구간마다 하나. 폐쇄 부두에는 안 놓는다.
        xs = x
        for k in range(span):
            wk = cols[i + k]["길이"] * hs
            if not closed and wk > 40:
                p.append(crane_glyph(xs + wk / 2, Y0 - DECK))
            xs += wk

        # 수심 값 — 물속에 적는다. 해도가 수심을 적는 자리다.
        xs = x
        seen = set()
        for k in range(span):
            ck = cols[i + k]
            wk = ck["길이"] * hs
            if ck["수심"] not in seen or span == 1:
                seen.add(ck["수심"])
                yb = Y0 + ck["수심"] * VS
                p.append('<text class="sound%s" x="%.1f" y="%.1f" '
                         'text-anchor="middle">%.1f</text>'
                         % (cls, xs + wk / 2, yb - 11, ck["수심"]))
            xs += wk

        # 길이 치수선 — 바닥 아래
        yl = bed_bottom + 20
        p.append('<line class="dimline" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 % (x + 1.5, yl, x + wtot - 1.5, yl))
        for xx in (x + 1.5, x + wtot - 1.5):
            p.append('<line class="dimtick" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                     % (xx, yl - 4, xx, yl + 4))
        tot_m = sum(cols[i + k]["길이"] for k in range(span))
        p.append('<text class="dimlbl" x="%.1f" y="%.1f" text-anchor="middle">'
                 '%s m</text>' % (cx, yl + 17, "{:,}".format(int(tot_m))))

        x += wtot
        i += span

    p.append('</svg>')
    # **좁은 판을 같은 div 안에 넣는다.** kramdown 은 `svg` 를 블록 요소로 보지 않아
    # 바깥에 홀로 두면 `<p>` 에 감싸여 사라진다 — 실제로 한 번 사라졌다.
    # `quay_svg` 가 이미 같은 이유로 같은 자리에 넣고 있었는데 그 규율을 안 따랐다.
    p.append(section_svg_narrow(terms))
    p.append('</div>')
    return "\n".join(p)


def section_svg_narrow(terms):
    """좁은 화면용 단면 — **같은 그림을 줄이지 않고 편다.**

    [2026-08-30 실측] 넓은 배치를 390px 에 그대로 넣으면 **E1CT 칸이 29 px** 이 되고
    이름이 7.6 px 로 떨어진다 — 읽을 수 없다. `quay_svg_narrow` 가 같은 문제를
    같은 방법으로 풀었다: **viewBox 폭을 줄여 배율을 키우고 배치를 바꾼다.**

    **두 축의 축척은 그대로 둔다.** 가로 1 m 당 픽셀도, 세로 1 m 당 픽셀도 행마다 같다 —
    그래야 넓은 배치와 **같은 것을 말하는 그림**이 된다. 배치만 다르다.
    가로를 축척에서 풀면 편해지지만, 그 순간 두 배치가 서로 다른 주장을 하게 된다.

    각 행이 부두 하나의 작은 단면이다. 가장 깊은 수심 자리에 **점선 기준선**을 그어
    12.0 m 와 11.0 m 가 거기 못 미친다는 것이 행을 건너서도 보이게 했다.
    """
    cols = section_cols(terms)
    if not cols:
        return ""
    # 터미널 단위로 묶는다 — 행 하나가 부두 하나다.
    groups = []
    for c in cols:
        if groups and groups[-1][0]["코드"] == c["코드"]:
            groups[-1].append(c)
        else:
            groups.append([c])

    # [2026-08-30 실측] NW 560 은 390px 화면에서 배율 0.564 라 이름이 11.8 px 이었다.
    # 폭을 줄이면 배율이 커지고 글자가 커진다 — `quay_svg_narrow` 가 쓴 것과 같은 수법.
    NW = 480.0
    hs = (NW - 24.0) / max(sum(g["길이"] for g in grp) for grp in groups)
    VS = 5.4
    DECK = 11.0
    NAME, FOOT = 34.0, 27.0
    dmax = max(c["수심"] for c in cols)
    ROW = NAME + DECK + dmax * VS + FOOT
    H = ROW * len(groups) + 16

    p = ['<svg class="sectmap narrow" viewBox="0 0 %.0f %.0f" role="img" '
         'aria-label="인천항 컨테이너 안벽의 길이와 전면수심 — 부두별로 한 줄씩. '
         '가로는 안벽 길이 미터, 세로는 기본수준면 아래 수심 미터. 지도가 아니다.">'
         % (NW, H)]
    p.append('<defs><pattern id="bedHn" width="8" height="8" '
             'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             '<line class="bedhatch" x1="0" y1="0" x2="0" y2="8"/></pattern>'
             '<linearGradient id="seaGn" x1="0" y1="0" x2="0" y2="1">'
             '<stop offset="0" class="sea-top"/>'
             '<stop offset="1" class="sea-bot"/></linearGradient></defs>')

    for gi, grp in enumerate(groups):
        top = 10 + gi * ROW
        c0 = grp[0]
        closed = c0["폐쇄"]
        cls = " closed" if closed else ""
        wtot = sum(g["길이"] for g in grp) * hs
        y0 = top + NAME + DECK            # 수면
        p.append('<text class="sname%s" x="0" y="%.1f">%s</text>'
                 % (cls, top + 21, c0["코드"]))
        p.append('<text class="szone" x="%.1f" y="%.1f">%s</text>'
                 % (len(c0["코드"]) * 15 + 12, top + 21,
                    c0["구역"] + (" 폐쇄" if closed else "")))
        # 가장 깊은 수심 기준선 — 행을 건너 비교할 수 있게.
        yref = y0 + dmax * VS
        p.append('<line class="refline" x1="0" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                 % (yref, NW, yref))
        # 안벽 상부
        p.append('<rect class="deck%s" x="0" y="%.1f" width="%.1f" height="%.1f"/>'
                 % (cls, top + NAME, wtot, DECK))
        # 물과 해저 — 구간마다 수심이 다를 수 있으므로 계단으로 잇는다.
        x = 0.0
        steps = []
        for g in grp:
            w = g["길이"] * hs
            steps.append((x, x + w, y0 + g["수심"] * VS))
            x += w
        sea = ["0,%.1f" % y0]
        for x0, x1, yb in steps:
            sea += ["%.1f,%.1f" % (x0, yb), "%.1f,%.1f" % (x1, yb)]
        sea.append("%.1f,%.1f" % (wtot, y0))
        p.append('<polygon class="sea narrow" points="%s"/>' % " ".join(sea))
        bl = []
        for x0, x1, yb in steps:
            bl += ["%.1f,%.1f" % (x0, yb), "%.1f,%.1f" % (x1, yb)]
        p.append('<polygon class="bed narrow" points="%s %.1f,%.1f 0,%.1f"/>'
                 % (" ".join(bl), wtot, yref + 9, yref + 9))
        p.append('<polyline class="bedline" points="%s"/>' % " ".join(bl))
        # 값 — 왼쪽에 길이, 오른쪽에 수심.
        yv = yref + 24
        p.append('<text class="dimlbl" x="0" y="%.1f">%s m</text>'
                 % (yv, "{:,}".format(int(sum(g["길이"] for g in grp)))))
        depths = []
        for g in grp:
            if g["수심"] not in depths:
                depths.append(g["수심"])

        p.append('<text class="sound%s" x="%.1f" y="%.1f" text-anchor="end">'
                 '수심 %s m</text>'
                 % (cls, NW, yv, " · ".join("%.1f" % d for d in depths)))
    p.append('</svg>')
    return "\n".join(p)


def crane_glyph(cx, deck_y, h=56.0):
    """컨테이너 크레인 **기호** — 정면. 대수도 규격도 주장하지 않는다.

    넣은 이유는 하나다 — **이 그림이 항구라는 것이 한눈에 보여야 한다.**
    도면이 도면으로만 읽히면 숫자를 읽을 사람만 읽는다.

    **왜 정면인가.** 이 그림은 가로가 안벽 길이이고 세로가 그 앞 수심이다 —
    즉 **바다에서 안벽을 바라본 단면**이다. 그 시점에서 안벽 크레인은 정면으로 보인다.
    첫 판은 옆모습(긴 붐이 한쪽으로 뻗은 실루엣)을 그렸는데, **그림의 시점과 어긋나** 있었고
    화면에서는 그냥 「천막」으로 보였다. **좌표만 보고는 무엇으로 보이는지 알 수 없다.**

    정면에서 이 기계를 이 기계이게 하는 것은 셋이다 — **높고 좁은 두 다리** ·
    그 위에 걸친 **거더** · 거더 위의 **A 형 탑**. 거기에 트롤리를 하나 얹으면 읽힌다.

    **선 하나 굵기로만** 그린다. 채우면 실물처럼 보이고, 실물처럼 보이면 세게 된다.
    이것은 기호이지 대수가 아니다.
    """
    lw = 11.0                     # 다리 반간격 — 높이에 비해 좁아야 크레인으로 읽힌다
    gw = lw + 7.0                 # 거더는 다리보다 조금 넓다
    gird = deck_y - h * 0.70      # 거더 높이
    apex = deck_y - h             # 탑 꼭대기
    sill = deck_y - 7.0           # 하부 가로대
    seg = ['<g class="crane" aria-hidden="true">']

    def L(x1, y1, x2, y2):
        seg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                   % (x1, y1, x2, y2))

    L(cx - lw, deck_y, cx - lw, gird)      # 왼 다리
    L(cx + lw, deck_y, cx + lw, gird)      # 오른 다리
    L(cx - lw, sill, cx + lw, sill)        # 하부 가로대
    L(cx - gw, gird, cx + gw, gird)        # 거더
    L(cx - gw + 3, gird, cx, apex)         # A 형 탑
    L(cx + gw - 3, gird, cx, apex)
    L(cx, apex, cx, gird)                  # 탑 가운데 기둥
    # 트롤리 — 거더에 걸린 작은 상자와 그 아래 짧은 와이어.
    seg.append('<rect class="trolley" x="%.1f" y="%.1f" width="7" height="4.5"/>'
               % (cx - 3.5, gird - 4.5))
    L(cx, gird, cx, gird + 7)
    seg.append('</g>')
    return "".join(seg)



def zone_svg(regions):
    """그림 1 — 인천항 구역별 구성. **선석 수와 안벽 길이를 나란히.**

    두 값을 한 막대에 겹치지 않는다. 선석은 개수, 길이는 미터 — **다른 단위다.**
    겹쳐 그리면 둘 중 하나가 다른 하나의 근거처럼 읽힌다.
    """
    rows = [r for r in regions if r["항만"] == "인천항" and r["구분"] != "계"]
    rows = [r for r in rows if num(r["부두길이_m"])]
    if not rows:
        return ""
    W, LAB, ROW = 1000.0, 116.0, 44.0
    mid = (W - LAB) / 2 - 24
    maxb = max(num(r["선석_개"]) or 0 for r in rows) or 1
    maxl = max(num(r["부두길이_m"]) or 0 for r in rows) or 1
    H = ROW * len(rows) + 34

    p = ['<div class="quayfig">',
         f'<svg class="zonemap" viewBox="0 0 {W:.0f} {H:.0f}" role="img" '
         f'aria-label="인천항 구역별 선석 수와 안벽 길이">']
    p.append(f'<text class="ticklbl" x="{LAB:.0f}" y="12">선석 (개)</text>')
    p.append(f'<text class="ticklbl" x="{LAB + mid + 40:.0f}" y="12">안벽 길이 (m)</text>')
    for i, r in enumerate(rows):
        y = 22 + i * ROW
        nb, ln = num(r["선석_개"]), num(r["부두길이_m"])
        p.append(f'<text class="qcode sm" x="0" y="{y + 19:.0f}">{r["구분"]}</text>')
        if nb:
            w = nb / maxb * (mid - 46)
            p.append(f'<rect class="qseg z0" x="{LAB:.0f}" y="{y:.0f}" '
                     f'width="{max(w, 2):.1f}" height="22" rx="1"/>')
            p.append(f'<text class="qval" x="{LAB + w + 7:.1f}" y="{y + 16:.0f}">{nb:,.0f}</text>')
        x2 = LAB + mid + 40
        w2 = ln / maxl * (W - x2 - 76)
        p.append(f'<rect class="qseg z1" x="{x2:.0f}" y="{y:.0f}" '
                 f'width="{max(w2, 2):.1f}" height="22" rx="1"/>')
        p.append(f'<text class="qval" x="{x2 + w2 + 7:.1f}" y="{y + 16:.0f}">{ln:,.0f}</text>')
    p.append("</svg>")
    p.append(zone_svg_narrow(rows, maxb, maxl))
    p.append("</div>")
    return "\n".join(p)


def zone_svg_narrow(rows, maxb, maxl):
    """좁은 화면용 — 두 지표를 **가로로 나란히가 아니라 세로로** 놓는다.

    390px 에서 두 막대군을 좌우로 놓으면 각각 150px 밑으로 내려가 비교가 안 된다.
    **단위가 다른 두 값을 한 막대에 겹치지 않는다는 원칙은 그대로다** — 줄만 나눈다.
    """
    NW, ROW, BAR = 600.0, 92.0, 200.0
    H = ROW * len(rows) + 12
    p = [f'<svg class="zonemap narrow" viewBox="0 0 {NW:.0f} {H:.0f}" role="img" '
         f'aria-label="인천항 구역별 선석 수와 안벽 길이">']
    for i, r in enumerate(rows):
        y = 16 + i * ROW
        nb, ln = num(r["선석_개"]), num(r["부두길이_m"])
        p.append(f'<text class="qcode sm" x="0" y="{y + 4:.0f}">{r["구분"]}</text>')
        if nb:
            w = nb / maxb * BAR
            p.append(f'<rect class="qseg z0" x="0" y="{y + 14:.0f}" '
                     f'width="{max(w, 2):.1f}" height="18" rx="1"/>')
            p.append(f'<text class="qval" x="{w + 8:.1f}" y="{y + 28:.0f}">'
                     f'선석 {nb:,.0f}</text>')
        w2 = ln / maxl * BAR
        p.append(f'<rect class="qseg z1" x="0" y="{y + 40:.0f}" '
                 f'width="{max(w2, 2):.1f}" height="18" rx="1"/>')
        p.append(f'<text class="qval" x="{w2 + 8:.1f}" y="{y + 54:.0f}">'
                 f'안벽 {ln:,.0f} m</text>')
    p.append("</svg>")
    return "\n".join(p)


# ── 표 ──────────────────────────────────────────────────────────────────────

def berth_table(rows):
    out = ['<div class="tablewrap"><table class="data">',
           "<thead><tr><th>구역</th><th>터미널</th><th class='num'>안벽 m</th>"
           "<th class='num'>전면수심 m</th><th>동시접안능력 (DWT)</th>"
           "<th class='num'>선석</th><th>주요취급화물</th></tr></thead><tbody>"]
    for r in rows:
        nb = berth_count(r["동시접안능력"])
        out.append(
            f"<tr><td>{r['구역']}</td><td><b>{r['명칭']}</b></td>"
            f"<td class='num'>{f(num(r['부두길이_m']))}</td>"
            f"<td class='num'>{f(num(r['전면수심_DL_m']), 1)}</td>"
            f"<td>{r['동시접안능력']}</td>"
            f"<td class='num'>{'–' if nb is None else nb}</td>"
            f"<td>{r['주요취급화물']}</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def region_table(regions):
    out = ['<div class="tablewrap"><table class="data">',
           "<thead><tr><th>항만</th><th>구분</th><th class='num'>선석</th>"
           "<th class='num'>안벽 길이 m</th><th class='num'>하역능력 BULK 천RT</th>"
           "<th class='num'>하역능력 CONT 천TEU</th><th>비고</th></tr></thead><tbody>"]
    for r in regions:
        tot = (r["구분"] == "계")
        cls = " class='lv-total'" if tot else ""
        note = "원문 rowspan 부족 — 항만열 승계" if r.get("행복구") else ""
        out.append(
            f"<tr{cls}><td>{r['항만']}</td><td>{r['구분']}</td>"
            f"<td class='num'>{f(num(r['선석_개']))}</td>"
            f"<td class='num'>{f(num(r['부두길이_m']))}</td>"
            f"<td class='num'>{f(num(r['하역능력_BULK_천RT']))}</td>"
            f"<td class='num'>{f(num(r['하역능력_CONT_천TEU']))}</td>"
            f"<td class='tiny'>{note}</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def sum_gap(regions):
    """상세 행의 합과 표가 낸 「계」. **맞추지 않는다 — 재서 적는다.**"""
    tot = next((r for r in regions if r["구분"] == "계"), None)
    parts = [r for r in regions if r is not tot]
    if not tot:
        return None
    g = {}
    for key in ("선석_개", "부두길이_m"):
        s = sum(num(r.get(key) or "") or 0 for r in parts)
        t = num(tot.get(key) or "")
        g[key] = (s, t, None if t is None else s - t)
    return g


def capacity_vs_actual(regions, terms_csv):
    """시설 ↔ 실적. **같은 기관 · 같은 단위 · 같은 구역.** 그래도 다른 개념이다."""
    rows = load(terms_csv)
    latest = max(r["기준연월"] for r in rows)
    prev_year = {}
    for r in rows:
        if r["기준연월"] == latest and r["계층"] in ("부두군", "합계"):
            prev_year[r["터미널"]] = num(r["전년연간_천TEU"])
    cap = {r["구분"]: num(r["하역능력_CONT_천TEU"])
           for r in regions if r["항만"] == "인천항"}
    out = []
    for zone in ZONE_ORDER:
        c, a = cap.get(zone), prev_year.get(zone)
        if c and a:
            out.append({"구역": zone, "능력": c, "실적": a, "비율": a / c * 100})
    return latest, out


# ── 지면 ────────────────────────────────────────────────────────────────────

def build() -> str:
    berths = load(BERTHS)
    regions = load(REGIONS)
    srcs = load(SRC)
    terms = terminals_rollup(berths)
    gap = sum_gap(regions)
    latest, cva = capacity_vs_actual(regions, TERMINALS)
    collected = srcs[0]["수집일"] if srcs else ""

    live = [t for t in terms if not t["폐쇄"]]
    closed = [t for t in terms if t["폐쇄"]]
    total_q = sum(t["길이"] for t in live)
    total_b = sum(t["선석"] for t in live)
    sin_q = sum(t["길이"] for t in live if t["구역"] == "신항")
    nam_q = sum(t["길이"] for t in live if t["구역"] == "남항")
    closed_line = ""
    if closed:
        c = closed[0]
        closed_line = (f'원문이 「폐쇄」로 적은 {c["코드"]} {c["길이"]:,.0f} m 는 이 합에서 뺐다.')

    cva_rows = "\n".join(
        f"<tr><td><b>{c['구역']}</b></td><td class='num'>{f(c['능력'])}</td>"
        f"<td class='num'>{f(c['실적'])}</td>"
        f"<td class='num'>{c['비율']:.1f}</td></tr>" for c in cva)

    gap_line = ""
    if gap:
        b_s, b_t, b_d = gap["선석_개"]
        l_s, l_t, l_d = gap["부두길이_m"]
        gap_line = (
            f"상세 행을 더하면 **선석 {b_s:,.0f}개 · 안벽 {l_s:,.0f} m** 인데, "
            f"같은 표의 「계」는 **{b_t:,.0f}개 · {l_t:,.0f} m** 다. "
            f"**선석 {b_d:+,.0f} · 안벽 {l_d:+,.0f} m** 어긋난다.")

    src_rows = "\n".join(
        '<li><span class="ft">HTML</span> '
        f'<a href="https://incheon.mof.go.kr/ko/page.do?menuIdx={s["menuIdx"]}">'
        f'{s["지면제목"] or ("menuIdx " + s["menuIdx"])}</a> '
        f'<span class="meta">{int(s["바이트"]):,} B · SHA-256 {s["SHA256_앞16"]}</span></li>'
        for s in srcs)

    verify_link = "{{ '/verify/' | relative_url }}"
    terminals_link = "{{ '/terminals/' | relative_url }}"
    data_link = "{{ '/data/' | relative_url }}"

    return f"""---
layout: page
title: 인천항 부두 구조
kicker: 인천항 · 시설 현황
standfirst: 인천항 컨테이너 부두가 어느 구역에 몇 선석, 안벽 몇 미터, 수심 몇 미터로 공표돼 있는가. 처리실적과 같은 기관이 낸 시설 자료를 그대로 옮기고, 실적과 나란히 놓는다.
permalink: /berths/
collected: {collected}
status: 관측 — 판정 대상 아님
description: 인천항 컨테이너 부두(SNCT·HJIT·ICT·E1CT·SICT)의 안벽 길이·전면수심·동시접안능력과 구역별 선석 구성. 인천지방해양수산청 공표 부두현황을 원본 링크·해시와 함께 싣는다.
---

**이 지면은 「인천항이 어떻게 생겼는가」를 공표 자료로 확인한다.**
처리실적은 [터미널 지면]({terminals_link})이 든다. 여기는 **그 실적이 나오는 시설** 쪽이다.
출처는 **인천지방해양수산청** — 월별 처리실적을 내는 그 기관이다.

<div class="callout warn">
<span class="k">먼저 읽을 것 — 이 그림이 주장하지 않는 것</span>
<p><b>지도가 아니다.</b> 이 소스에는 위치·방위·부두 사이의 거리가 <b>없다.</b>
그래서 그리지 않는다. 그림 2 의 가로축은 <b>오직 안벽 길이(m)</b>이고,
같은 자로 나란히 놓은 것 말고는 아무것도 말하지 않는다.</p>
<p><b>자료 기준일이 원문에 없다.</b> 「언제 기준의 시설 현황인가」를 이 소스는 밝히지 않는다.
그래서 우리가 아는 것은 <b>우리가 받은 날({collected})</b>뿐이고, 그렇게만 적는다.</p>
</div>

## 그림 1 — 인천항은 구역이 여럿이고, 컨테이너는 그중 둘에 있다

{zone_svg(regions)}

<p class="tnote">인천항 구역별 선석 수와 안벽 길이 · 출처 인천지방해양수산청 「부두현황」 ·
수집일 {collected}. <b>두 막대는 단위가 다르다</b> — 왼쪽은 개수, 오른쪽은 미터다.
한 막대에 겹치지 않은 이유가 그것이다. 겹치면 둘 중 하나가 다른 하나의 근거처럼 읽힌다.
<b>컨테이너 하역능력이 공표된 구역은 신항과 남항 둘뿐이다</b>(표 2).</p>

## 그림 2 — 컨테이너 안벽을 같은 자로 놓으면

{quay_svg(terms)}

<p class="tnote">인천항 컨테이너 터미널의 안벽 구성 · 가로축 단위 m · 출처 동일 · 수집일 {collected}.
<b>한 터미널의 안벽이 접안능력이 다른 구간으로 나뉘어 공표된다.</b>
SNCT 와 HJIT 는 300 m 구간(4만 DWT급 1척)과 500 m 구간(3만 DWT급 2척)으로 나뉜다 —
합쳐 한 덩어리로 그리면 그 구조가 사라지므로 구간을 그대로 두었다.
빗금 친 것은 원문이 <b>「폐쇄」</b>로 적은 부두다.</p>

## 그림 3 — 물속을 같이 보면 신항과 남항이 갈린다

{section_svg(terms)}

<p class="tnote">가로축은 안벽 길이(m) · 세로축은 <b>전면수심(m)</b> · 기준면은
<b>DL(기본수준면)</b> · 출처 동일 · 수집일 {collected}.
<b>두 축 모두 공표된 값이고, 이 그림은 그 둘 말고 아무것도 주장하지 않는다.</b></p>

<div class="callout">
<span class="k">이 그림이 말하지 않는 것 — 먼저 읽을 것</span>
<p><b>지도가 아니다.</b> 부두의 위치·방위·서로 간의 거리는 이 소스에 없다.
왼쪽에서 오른쪽 순서는 <b>공표자료의 구역 순서</b>이지 지리가 아니다.</p>
<p><b>해저 지형이 아니다.</b> 공표값은 안벽 <b>앞</b> 수심 한 숫자다. 그 앞바다가 어떤
모양으로 깊어지는지는 모른다 — <b>계단으로 그린 것은 값이 계단이라서</b>이지 바닥이
계단이라서가 아니다.</p>
<p><b>크레인은 기호다.</b> 대수·위치·규격은 이 소스에 없다. 구간마다 같은 모양을 하나씩
놓았을 뿐이므로 <b>세면 안 된다.</b></p>
<p><b>배를 그리지 않았다.</b> 흘수는 이 소스에 없다. 배를 그리면 그 순간
「이 수심에 이 배가 들어온다」는, <b>우리가 확인하지 않은 말</b>이 된다.</p>
<p>그리고 <b>조위에 따라 실제 수심은 DL 보다 깊어진다.</b> 그 폭은 이 소스에 없다.</p>
</div>

**신항 두 부두와 남항 ICT 가 14.0 m 로 같고, E1CT 가 12.0 m, 폐쇄된 SICT 가 11.0 m 다.**
같은 자리에 공표된 동시접안능력은 14.0 m 구간이 3만~4만 DWT급, 12.0 m 구간이 3만 DWT급,
11.0 m 구간이 1만 8천 DWT급이다. **수심과 선박 규모가 함께 공표돼 있다는 사실만 적는다** —
어느 쪽이 어느 쪽을 정했는지는 이 데이터로 판별할 수 없다.

## 표 1 — 컨테이너 부두 상세

{berth_table(berths)}

<p class="tnote">출처 인천지방해양수산청 부두현황 지면(아래 원본 링크) · 수집일 {collected} ·
단위 m. 「선석」은 <b>동시접안능력 문자열의 척수를 우리가 읽은 값</b>이다 —
원문에 선석 수 열이 따로 없다. 운영사 상호를 쓰지 않고 <b>공표자료가 쓰는 코드</b>로만 적는다.</p>

<p class="dlrow"><span class="ft">CSV</span>
<a href="{GH}/analysis/port_container_berths.csv">이 표의 원자료</a>
<span class="meta">{len(berths)}행 · 원문 캡션 포함</span></p>

**운영 중인 컨테이너 안벽은 {total_q:,.0f} m · {total_b}선석**이다.
그중 **신항이 {sin_q:,.0f} m**, 남항이 {nam_q:,.0f} m다. {closed_line}

## 표 2 — 구역별 부두현황, 공표된 그대로

{region_table(regions)}

<p class="tnote">출처 동일 · 수집일 {collected}. <b>맨 아래 「계」는 공표자료가 낸 값</b>이고
우리가 더한 값이 아니다. 「비고」의 표시는 <b>원문 HTML 의 <code>rowspan</code> 이 모자라
항만 열이 비어 나온 행</b>이다 — 앞 행의 항만을 이어받아 채웠고, 채웠다는 사실을 적어 둔다.</p>

### 부분을 더한 값과 「계」가 다르다

{gap_line}

**맞추지 않았다.** 어느 쪽이 옳은지 이 데이터로는 판별할 수 없고,
**판별할 수 없는 것을 판별한 것처럼 고치는 것**이 이 사이트가 하지 않는 일이다.
용도별 표에서도 같은 어긋남이 나온다 — 수집 코드가 두 표를 다 검산하고 그 값을 출력한다.

## 표 3 — 하역능력과 처리실적을 나란히

<div class="tablewrap"><table class="data">
<thead><tr><th>구역</th><th class="num">하역능력 천TEU/년</th>
<th class="num">전년 실적 천TEU</th><th class="num">실적 ÷ 능력 %</th></tr></thead>
<tbody>
{cva_rows}
</tbody></table></div>

<p class="tnote">능력 = 인천지방해양수산청 「부두현황」의 CONT 하역능력 · 수집일 {collected}.
실적 = 같은 기관 「월별 항만운영통계」({latest} 호)가 든 <b>전년 연간</b> 값.
<b>같은 기관 · 같은 단위(천TEU/년) · 같은 구역 구분</b>이라 나란히 놓을 수 있다.</p>

<div class="callout">
<span class="k">이 표를 읽는 법</span>
<p><b>능력과 실적은 다른 개념이다.</b> 하역능력은 시설에 매겨진 값이고, 처리실적은
그 해에 실제로 지나간 양이다. <b>실적이 능력을 넘는 것은 그 자체로 오류가 아니다</b> —
두 값의 산정 기준이 다르기 때문이다. 이 표는 <b>두 공표값을 같은 자리에 놓을 뿐</b>이고,
넘거나 못 미치는 것이 무엇을 뜻하는지는 <b>이 데이터로 판별할 수 없어 쓰지 않는다.</b></p>
</div>

## 이 지면이 말하는 것과 말하지 않는 것

- **말하는 것** — 각 컨테이너 부두의 안벽 길이·전면수심·동시접안능력이 **공표자료에 무엇으로
  적혀 있는가.** 그리고 구역별 선석·안벽·하역능력이 무엇으로 적혀 있는가.
- **말하지 않는 것** — 부두가 **어디에** 있는지. 이 소스에 위치가 없다.
  그리고 **왜** 그런 시설 구성이 되었는지. 이 데이터로 판별할 수 없고
  [인과·전망을 쓰지 않는다]({verify_link}).
- **비교의 한계** — 수심과 접안능력이 다르면 받을 수 있는 배가 다르다. 그러나
  **안벽이 길다거나 수심이 깊다는 것을 운영 성과로 읽을 수 없다.**
  이 표는 규모를 나란히 놓을 뿐 순위를 매기지 않는다.

## 원본과 재현

받은 지면과 그 SHA-256을 함께 공개한다. **같은 주소를 받아 같은 코드를 돌리면 같은 표가 나온다.**
안 나오면 우리 잘못이거나 원문이 바뀐 것이고, 둘 다 알아야 할 일이다.

<ul class="files">
{src_rows}
</ul>

<ul class="files">
<li><span class="ft">CSV</span> <a href="{GH}/analysis/port_container_berths.csv">컨테이너 부두 상세</a> <span class="meta">{len(berths)}행</span></li>
<li><span class="ft">CSV</span> <a href="{GH}/analysis/port_regions.csv">구역별 부두현황</a> <span class="meta">{len(regions)}행</span></li>
<li><span class="ft">CSV</span> <a href="{GH}/analysis/port_usage.csv">용도별 부두현황</a> <span class="meta">교차 검산용</span></li>
<li><span class="ft">PY</span> <a href="{GH}/analysis/collect_port_facilities.py">수집·파싱 코드</a> <span class="meta">rowspan 복원 · 자체 검산 포함</span></li>
<li><span class="ft">PY</span> <a href="{GH}/analysis/build_berths_page.py">이 지면을 만든 코드</a> <span class="meta">표를 손으로 옮기지 않는다</span></li>
</ul>

<p class="tnote">소스: 인천지방해양수산청 부두현황·구역별 지면. 원시 자료의 권리는 제공 기관에 있고
재사용 조건은 그 기관의 약관을 따른다. 자세한 것은 <a href="{data_link}">데이터 지도</a>.</p>
"""


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 선석 수 읽기 ──")
    chk("`40,000×1 (3천TEU이상)`", berth_count("40,000×1 (3천TEU이상)"), 1)
    chk("`30,000×2`", berth_count("30,000×2 (2천TEU이상)"), 2)
    chk("**대문자 X 도 읽는다** (원문에 두 종류가 섞여 있다)", berth_count("3,000X5"), 5)
    chk("소문자 x", berth_count("3,000x4"), 4)
    chk("없으면 None", berth_count("-"), None)

    print("── 인수시험: 폐쇄 표시 ──")
    chk("원문이 폐쇄라 적으면 폐쇄", is_closed({"주요취급화물": "- (폐쇄)"}), True)
    chk("컨테이너는 폐쇄 아님", is_closed({"주요취급화물": "컨테이너"}), False)

    print("── 인수시험: 실물 ──")
    berths = load(BERTHS)
    terms = terminals_rollup(berths)
    codes = [t["코드"] for t in terms]
    chk("터미널 5곳", sorted(codes), ["E1CT", "HJIT", "ICT", "SICT", "SNCT"])
    chk("신항이 먼저 온다", codes[:2], ["SNCT", "HJIT"])
    snct = next(t for t in terms if t["코드"] == "SNCT")
    chk("SNCT 안벽 800 m (300+500)", snct["길이"], 800.0)
    chk("SNCT 3선석 (1+2)", snct["선석"], 3)
    chk("SNCT 구간 2개 — 합쳐서 안 그린다", len(snct["구간"]), 2)
    chk("SNCT 수심 한 종류", sorted(snct["수심"]), [14.0])
    chk("SICT 는 폐쇄로 잡힌다",
        next(t for t in terms if t["코드"] == "SICT")["폐쇄"], True)

    regions = load(REGIONS)
    g = sum_gap(regions)
    chk("검산이 돌아간다", g is not None, True)
    chk("**부분합과 계가 어긋난다 (공표자료 자체의 어긋남)**", g["선석_개"][2] != 0, True)

    latest, cva = capacity_vs_actual(regions, TERMINALS)
    chk("시설↔실적 대조가 두 구역에 선다", [c["구역"] for c in cva], ["신항", "남항"])
    chk("신항 능력이 공표값이다", cva[0]["능력"], 2162.0)

    print("── 인수시험: 생성물 ──")
    text = build()
    chk("그림 2개 · 표 3개", all(k in text for k in
        ("## 그림 1", "## 그림 2", "## 표 1", "## 표 2", "## 표 3")), True)
    chk("절 제목에 「## 1.」이 없다 (린터 오인 방지)",
        any(l.startswith("## 1.") or l.startswith("## 3.") for l in text.splitlines()), False)
    chk("SVG 가 div 로 감싸였다", text.count('<div class="quayfig">'), 2)
    # **개수를 손으로 박지 않는다.** 그림을 하나 더하자(단면도) 이 시험이 먼저 깨졌다 —
    # 사고 53·65와 같은 얼굴이다. 확인하려는 사실은 「그림이 넷이다」가 아니라
    # **「그림마다 넓은 배치와 좁은 배치가 짝을 이룬다」**이다. 그 짝을 센다.
    wide = len(re.findall(r'<svg class="(quaymap|zonemap|sectmap)"', text))
    narrow = len(re.findall(r'<svg class="(quaymap|zonemap|sectmap) narrow"', text))
    chk("그림마다 넓은/좁은 배치가 짝을 이룬다", (wide, narrow), (wide, wide))
    chk("그림이 하나 이상 있다", wide >= 1, True)
    # 열린 svg 만큼 닫히고, 그림 묶음(div)도 그만큼 닫힌다.
    chk("svg 가 전부 닫힌다", text.count("<svg "), text.count("</svg>"))
    # 그림 묶음은 **그림마다 한 번** 닫힌다 — 좁은 배치는 같은 div 안에 든다.
    # 여는 div 의 class 이름은 그림마다 다르므로(quayfig·zonefig·portfig) 이름으로 세지 않는다.
    chk("그림 묶음이 그림 수만큼 닫힌다",
        text.count("</svg>" + chr(10) + "</div>"), wide)
    chk("**「지도가 아니다」를 지면이 든다**", "지도가 아니다" in text, True)
    chk("**능력≠실적을 지면이 든다**", "능력과 실적은 다른 개념이다" in text, True)
    chk("원본 해시가 실린다", "SHA-256" in text, True)
    # **부인 목록이 아니라 허용 목록으로 검사한다.**
    # 「이 상호들이 없는가」로 쓰면 **그 상호를 검사기 자신이 공개 파일에 싣게 된다** —
    # 막으려는 것을 막는 코드가 하는 꼴이다(2026-08-29 실측: 최종 훑기에 내 가드가 잡혔다).
    # 그리고 허용 목록이 **더 강하다** — 내가 미처 못 떠올린 이름까지 걸린다.
    names = {r["명칭"].strip() for r in berths}
    chk("부두 이름이 공표 코드뿐이다 (허용 목록 · §4.1-1)",
        names <= {"SNCT", "HJIT", "ICT", "E1CT", "SICT"}, True)
    chk("지면의 부두 이름도 그 코드뿐이다",
        {n for n in names if n in text} == names, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1




# ── 접근성 후처리 ───────────────────────────────────────────────────────────
# 표에 `caption`(이름)과 `th scope`(머리 방향)를 채운다. **표마다 손으로 안 붙인다** —
# 이 파일 하나가 표를 여럿 만들고, 빠뜨린 것은 화면에서 안 보인다(사고 68과 같은 종류).
# 이름은 앞선 제목에서 가져오고 **못 찾으면 안 붙인다.** 근거 = analysis/htmltable.py
def _a11y(fn):
    def wrapped(*a, **k):
        return htmltable.annotate(fn(*a, **k))[0]
    wrapped.__name__ = fn.__name__
    wrapped.__doc__ = fn.__doc__
    return wrapped

build = _a11y(build)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    for p in (BERTHS, REGIONS, SRC):
        if not os.path.exists(p):
            print(f"[중단] {p} 가 없다. 먼저 collect_port_facilities.py 를 돌린다.")
            return 2
    if a.selftest:
        return selftest()
    text = build()
    if a.check:
        old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        same = old == text
        print("일치" if same else "**다르다 — 다시 생성해야 한다**")
        return 0 if same else 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print(f"-> {OUT}  ({len(text):,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

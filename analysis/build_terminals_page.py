"""`analysis/terminal_monthly.csv` 로 허브의 `/terminals/` 지면을 생성한다.

**손으로 표를 옮겨 적지 않는다.** 옮겨 적으면 그 순간 데이터와 지면이 갈리고,
갈린 것은 아무도 모른다. 이 스크립트가 CSV 하나에서 지면을 만든다 —
데이터가 바뀌면 지면도 한 번에 바뀐다.

**지위는 `관측`이다.** 공표자료를 그대로 옮기고 몫(share)만 계산했다.
판정 대상이 아니고, 선커밋 기준이 걸려 있지 않다.

[2026-08-29] 계층을 되살렸다 — 이 지면의 성격이 바뀐 지점이다
--------------------------------------------------------------
종전 지면은 터미널 다섯 곳을 **평평한 목록**으로 냈다. 그런데 원문을 열어 보니
(`analysis/probe/probe_11_berth_group.py`) 공표자료의 표는 **계층**이다 —

    컨테이너 합계 → 신항 소계 → SNCT · HJIT → 남항 소계 → E1CT · ICT
                  → 국제여객부두 → 그 외

**우리가 그 계층을 눌러 없앴고, 대신 우리가 더한 합계를 얹고 있었다.**
그 자체 합계는 공표 합계와 **어긋난다** — 2026-07 기준 283 대 282.
두 값 다 틀리지 않았다. 공표값이 이미 천TEU 로 반올림돼 있어서
**부분을 더한 값과 공표 합계가 ±1 벌어진다.** 실측하면 19곳 중 5곳에서 실제로 벌어졌다.

그래서 셋을 바꿨다.
① **공표자료가 낸 합계·소계를 그대로 싣는다.** 우리가 더한 값을 「합계」라 부르지 않는다.
② **몫의 분모를 공표 합계로 바꿨다.** 종전 분모는 다섯 곳의 합이었다.
③ **반올림 어긋남을 각주가 아니라 관측치로 싣는다** — 「몇 곳 중 몇 곳에서 실제로」.

**그리고 이 계층이 인천항의 구조 그 자체다.** 신항 · 남항 · 국제여객부두는
우리가 만든 분류가 아니라 **공표자료가 쓰는 구분**이고, 이 지면이 다른 항만의
지면과 달라지는 자리가 거기다. 구조도(SVG)를 그 위에 얹었다 —
**지도가 아니다.** 위치를 주장하지 않는다. 크기와 소속만 든다.

**절 제목을 「1.」「3.」으로 달지 않는다 — 의도된 제약이다.**
`lint_publish.py` 의 `conclusion_zones()` 가 `^##\\s*1[.\\s]` 와 `^##\\s*3[.\\s]` 를
**보고서의 §1 핵심 요약 · §3 해석**으로 읽는다(지침 §2.5 골격 계약).
처음에 「## 1. 최신월」로 달았더니 린터가 이 지면을 보고서로 오인해
표 안의 수치 전부를 결론 자리 미등재로 잡았다(WARN 66건).
**린터를 고치지 않고 지면을 고쳤다.** 검사기를 통과시키려고 검사기를 무르게 하는 것이
이 프로젝트가 막는 일이다. 그리고 통계 간행물은 원래 **표에 번호를 단다** — 더 맞는 형식이다.

    python analysis/build_terminals_page.py
    python analysis/build_terminals_page.py --check   # 다시 생성해 현재 파일과 대조만
    python analysis/build_terminals_page.py --selftest
"""
from __future__ import annotations
import argparse
import csv
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CSV = os.path.join("analysis", "terminal_monthly.csv")
SRC = os.path.join("analysis", "terminal_monthly_sources.csv")
OUT = os.path.join("..", "jisangj03-dev.github.io", "terminals", "index.md")
COLLECTED = "2026-08-29"

TOTAL = "컨테이너 합계"
OTHER = "그 외"
# 공표자료가 내는 순서. **이 순서가 계층이다.**
LAYOUT = [
    (TOTAL, "합계", 0),
    ("신항", "부두군", 1),
    ("SNCT", "터미널", 2),
    ("HJIT", "터미널", 2),
    ("남항", "부두군", 1),
    ("E1CT", "터미널", 2),
    ("ICT", "터미널", 2),
    ("IPT", "부두군", 1),
    (OTHER, "그 외", 1),
]
TERMS = ["SNCT", "HJIT", "E1CT", "ICT", "IPT"]
# 구조도의 세 칸. IPT 는 공표자료에서 소계 없이 그 자체로 한 칸이다.
BANDS = [("신항", "신항", ["SNCT", "HJIT"]),
         ("남항", "남항", ["E1CT", "ICT"]),
         ("IPT", "국제여객부두", [])]
LABEL = {TOTAL: "컨테이너 합계", "신항": "신항", "남항": "남항",
         "IPT": "국제여객부두 (IPT)", OTHER: "그 외"}


# ── 순수 함수 ───────────────────────────────────────────────────────────────

def load(path=CSV):
    rows = list(csv.DictReader(io.open(path, encoding="utf-8-sig")))
    months = sorted({r["기준연월"] for r in rows})
    cur = {}
    for r in rows:
        cur.setdefault(r["기준연월"], {})[r["터미널"]] = r
    return months, cur


def val(rec, key):
    if not rec:
        return None
    v = rec.get(key, "")
    if v in (None, ""):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def f(v, nd=0):
    return "–" if v is None else f"{v:,.{nd}f}"


def share(v, denom):
    """몫. **분모는 공표 합계다** — 우리가 더한 값이 아니다."""
    if v is None or not denom:
        return None
    return v / denom * 100


def rounding_gaps(months, cur):
    """부분합과 공표 합계가 **실제로** 어긋난 자리를 센다.

    「반올림 때문에 안 맞을 수 있다」는 상투구이고 독자는 그것을 면피로 읽는다.
    **「몇 곳 중 몇 곳에서 실제로 어긋났고 최대 몇이었다」는 관측이다.**
    """
    checked = hit = 0
    worst = 0.0
    for m in months:
        d = cur[m]
        for key in ("당월_천TEU", "누계_천TEU"):
            total = val(d.get(TOTAL), key)
            parts = [val(d.get(n), key) for n in ("신항", "남항", "IPT")]
            if total is None or any(p is None for p in parts):
                continue
            checked += 1
            s = sum(parts) + (val(d.get(OTHER), key) or 0.0)
            gap = abs(s - total)
            if gap > 1e-9:
                hit += 1
            worst = max(worst, gap)
    return checked, hit, worst


def delta_cell(v, extra=""):
    if v is None:
        return f"<td class='num{extra}'>–</td>"
    cls = "d-up" if v > 0 else ("d-dn" if v < 0 else "num")
    sign = "+" if v > 0 else ""
    return f"<td class='{cls}{extra}'>{sign}{v:.1f}</td>"


def hierarchy_table(d, denom):
    """표 1 — 공표자료의 계층을 그대로. 들여쓰기가 소속을 든다."""
    out = ['<div class="tablewrap"><table class="data hier">',
           "<thead><tr><th>구분</th>"
           "<th class='num'>당월</th><th class='num'>전년 동월</th><th class='num'>전년비 %</th>"
           "<th class='num'>연 누계</th><th class='num'>누계 전년비 %</th>"
           "<th class='num'>당월 몫 %</th></tr></thead><tbody>"]
    for name, level, indent in LAYOUT:
        r = d.get(name)
        if r is None and name != OTHER:
            continue
        cls = {"합계": "lv-total", "부두군": "lv-group",
               "터미널": "lv-term", "그 외": "lv-other"}[level]
        # 부두군 마커 색을 **생성기가 명시한다.** CSS 의 nth-of-type 위치로 주면
        # 원문 표 모양이 바뀔 때(그 외 행이 없는 달이 실제로 있다) 색이 조용히 밀린다.
        # 그림 1 의 칸 색과 같은 순서를 여기서 한 번만 정한다.
        band_of = {k: f" b{i}" for i, (k, _, _) in enumerate(BANDS)}
        if level == "부두군":
            cls += band_of.get(name, "")
        cur_v = val(r, "당월_천TEU")
        sh = share(cur_v, denom)
        label = LABEL.get(name, name)
        if level == "터미널":
            label = f"<b>{name}</b>"
        elif level in ("합계", "부두군"):
            label = f"<b>{label}</b>"
        out.append(
            f"<tr class='{cls}'><td class='lbl i{indent}'>{label}</td>"
            f"<td class='num'>{f(cur_v)}</td>"
            f"<td class='num'>{f(val(r, '전년당월_천TEU'))}</td>"
            f"{delta_cell(val(r, '전년대비_당월_%'))}"
            f"<td class='num'>{f(val(r, '누계_천TEU'))}</td>"
            f"{delta_cell(val(r, '전년대비_누계_%'))}"
            f"<td class='num'>{'–' if sh is None else f'{sh:.1f}'}</td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def structure_svg(d, denom):
    """인천항 컨테이너 부두의 **구조도**. 지도가 아니다 — 위치를 주장하지 않는다.

    칸의 너비는 **공표 소계**에 비례한다. 그래서 세 칸의 합이 공표 합계와 정확히 맞는다.
    터미널은 칸 안에 **글자로** 든다 — 너비로 그리지 않는다.
    그리면 반올림 때문에 칸을 넘거나 못 채우고, **그 어긋남이 그림에서는 거짓말이 된다.**
    (표에서는 숫자가 그대로 보이므로 거짓말이 안 된다. 그림과 표의 차이가 이것이다.)
    """
    W, PAD = 1000.0, 0.0
    segs = []
    x = PAD
    for key, label, kids in BANDS:
        v = val(d.get(key), "당월_천TEU")
        if v is None:
            continue
        w = v / denom * (W - PAD * 2)
        segs.append((key, label, kids, x, w, v))
        x += w
    if not segs:
        return ""

    band_y, band_h = 8, 46
    # **`<div>` 로 감싼다.** kramdown 의 블록 요소 목록에 `svg` 가 없어서, 안 감싸면
    # 마크다운이 이 덩어리를 span 으로 보고 줄마다 `<p>` 를 씌운다(2026-08-29 실측 —
    # 미리보기에서 그림이 글자 목록으로 풀렸다). 이 사이트의 표가 전부
    # `<div class="tablewrap">` 로 시작하는 이유가 같다. 미리보기 회피가 아니라
    # **kramdown 에 원시 HTML 을 넣는 올바른 방법**이다.
    parts = ['<div class="portfig">',
             f'<svg class="portmap wide" viewBox="0 0 {W:.0f} 150" role="img" '
             f'aria-label="인천항 컨테이너 부두군 구성 — 신항·남항·국제여객부두의 당월 처리량 비율">']
    for i, (key, label, kids, sx, w, v) in enumerate(segs):
        pct = v / denom * 100
        parts.append(
            f'<rect x="{sx:.1f}" y="{band_y}" width="{max(w - 3, 2):.1f}" height="{band_h}" '
            f'class="seg s{i}" rx="1"/>')
        if w > 90:
            parts.append(
                f'<text x="{sx + w / 2 - 1.5:.1f}" y="{band_y + band_h / 2 + 6:.0f}" '
                f'class="segpct" text-anchor="middle">{pct:.1f}%</text>')
    # 칸 밖 라벨 — 좁은 칸에서 글자가 넘치지 않게 마지막은 오른쪽 정렬한다.
    for i, (key, label, kids, sx, w, v) in enumerate(segs):
        last = (i == len(segs) - 1)
        tx = (sx + w - 3) if last else sx
        anchor = "end" if last else "start"
        parts.append(f'<text x="{tx:.1f}" y="{band_y + band_h + 26:.0f}" '
                     f'class="seglbl" text-anchor="{anchor}">{label}</text>')
        parts.append(f'<text x="{tx:.1f}" y="{band_y + band_h + 46:.0f}" '
                     f'class="segval" text-anchor="{anchor}">{v:,.0f} 천TEU</text>')
        kid_txt = " · ".join(
            f"{k} {f(val(d.get(k), '당월_천TEU'))}" for k in kids if d.get(k)) or "—"
        parts.append(f'<text x="{tx:.1f}" y="{band_y + band_h + 68:.0f}" '
                     f'class="segkid" text-anchor="{anchor}">{kid_txt}</text>')
    parts.append("</svg>")

    # ── 좁은 화면용 배치 ────────────────────────────────────────────────
    # **같은 그림을 줄여 쓰지 않는다.** viewBox 1000 을 390px 에 넣으면 배율이 0.375 라
    # 글자가 10px 밑으로 내려가고, 세 라벨이 가로로 겹친다(2026-08-29 실측).
    # 그래서 좁은 화면에서는 **가로 누적 막대를 세로 3행으로 편다.** 값은 그대로다 —
    # 배치만 바꾼다. CSS 로 하나를 숨긴다.
    NW, ROW = 600.0, 78.0
    n = [f'<svg class="portmap narrow" viewBox="0 0 {NW:.0f} {ROW * len(segs) + 4:.0f}" '
         f'role="img" aria-label="인천항 컨테이너 부두군 구성 — 신항·남항·국제여객부두의 '
         f'당월 처리량 비율">']
    for i, (key, label, kids, sx, w, v) in enumerate(segs):
        y = i * ROW
        pct = v / denom * 100
        bw = max(pct / 100 * NW, 2)
        n.append(f'<text x="0" y="{y + 17:.0f}" class="nlbl">{label}</text>')
        n.append(f'<text x="{NW:.0f}" y="{y + 17:.0f}" class="nval" text-anchor="end">'
                 f'{v:,.0f} 천TEU · {pct:.1f}%</text>')
        n.append(f'<rect x="0" y="{y + 27:.0f}" width="{bw:.1f}" height="17" class="seg s{i}"/>')
        kid_txt = " · ".join(
            f"{k} {f(val(d.get(k), '당월_천TEU'))}" for k in kids if d.get(k)) or "—"
        n.append(f'<text x="0" y="{y + 62:.0f}" class="nkid">{kid_txt}</text>')
    n.append("</svg>")

    parts += n
    parts.append("</div>")
    return "\n".join(parts)


def group_series(months, cur):
    """표 2 — 부두군 월별. **인천항의 구조가 시간에 따라 어떻게 움직였나.**"""
    keys = ["신항", "남항", "IPT"]
    out = ['<div class="tsw"><table>', "<thead><tr><th>기준월</th>"]
    out += ["<th class='num'>신항</th><th class='num'>남항</th>",
            "<th class='num'>국제여객부두</th><th class='num'>그 외</th>",
            "<th class='num'>공표 합계</th></tr></thead><tbody>"]
    for m in months:
        d = cur[m]
        out.append(f"<tr><th>{m}</th>")
        for k in keys:
            out.append(f"<td class='num'>{f(val(d.get(k), '당월_천TEU'))}</td>")
        out.append(f"<td class='num'>{f(val(d.get(OTHER), '당월_천TEU'))}</td>")
        out.append(f"<td class='num'><b>{f(val(d.get(TOTAL), '당월_천TEU'))}</b></td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def terminal_series(months, cur):
    """표 3 — 터미널 월별."""
    out = ['<div class="tsw"><table>', "<thead><tr><th>기준월</th>"]
    out += [f"<th class='num'>{t}</th>" for t in TERMS]
    out.append("<th class='num'>공표 합계</th></tr></thead><tbody>")
    for m in months:
        d = cur[m]
        out.append(f"<tr><th>{m}</th>")
        for t in TERMS:
            out.append(f"<td class='num'>{f(val(d.get(t), '당월_천TEU'))}</td>")
        out.append(f"<td class='num'><b>{f(val(d.get(TOTAL), '당월_천TEU'))}</b></td></tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def share_series(months, cur):
    """표 4 — 몫의 추이. 분모는 **공표 합계**다."""
    out = ['<div class="tsw"><table>', "<thead><tr><th>기준월</th>"]
    out += [f"<th class='num'>{t}</th>" for t in TERMS]
    out.append("</tr></thead><tbody>")
    for m in months:
        d = cur[m]
        denom = val(d.get(TOTAL), "당월_천TEU")
        out.append(f"<tr><th>{m}</th>")
        for t in TERMS:
            sh = share(val(d.get(t), "당월_천TEU"), denom)
            out.append(f"<td class='num'>{'–' if sh is None else f'{sh:.1f}'}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


HOME = os.path.join("..", "jisangj03-dev.github.io", "index.md")
HOME_BEGIN = "<!-- 터미널블록:시작 (생성됨. 손으로 고치지 마라 — analysis/build_terminals_page.py) -->"
HOME_END = "<!-- 터미널블록:끝 -->"

GH = "https://github.com/jisangj03-dev/incheon-port-analysis/blob/main"


def dl(label, path, note):
    """표 밑 내려받기 줄. ONS 통계 공보가 표마다 `.xlsx/.csv` 를 붙이는 자리다 —
    **데이터가 표에서 한 번의 클릭 거리에 있어야 한다.**"""
    return (f'<p class="dlrow"><span class="ft">CSV</span> '
            f'<a href="{GH}/{path}">{label}</a> <span class="meta">{note}</span></p>')


def build(csv_path=CSV, src_path=SRC) -> str:
    months, cur = load(csv_path)
    latest, first = months[-1], months[0]
    d = cur[latest]
    denom = val(d.get(TOTAL), "당월_천TEU")

    naive = sum(v for v in (val(d.get(t), "당월_천TEU") for t in TERMS) if v is not None)
    checked, hit, worst = rounding_gaps(months, cur)
    src_rows = list(csv.DictReader(io.open(src_path, encoding="utf-8-sig")))
    n_src = len(src_rows)

    # 최신월 헤드라인 — 공표 소계에서 바로 읽는다.
    sinhang = val(d.get("신항"), "당월_천TEU")
    sh_share = share(sinhang, denom)

    gap_line = (
        f"실측하면 **검산한 {checked}곳 중 {hit}곳**에서 실제로 어긋났고, "
        f"**최대 어긋남은 {worst:,.0f} 천TEU**였다."
    )
    naive_line = (
        f"이 달만 봐도 그렇다 — 터미널 다섯 곳을 그냥 더하면 **{naive:,.0f}**이 나오는데 "
        f"공표 합계는 **{f(denom)}**이다. 어긋나는 자리는 신항이다 "
        f"(SNCT {f(val(d.get('SNCT'), '당월_천TEU'))} + HJIT {f(val(d.get('HJIT'), '당월_천TEU'))} "
        f"= {f(val(d.get('SNCT'), '당월_천TEU')) and (val(d.get('SNCT'), '당월_천TEU') + val(d.get('HJIT'), '당월_천TEU')):,.0f}, "
        f"공표 소계는 {f(sinhang)})."
    )

    return f"""---
layout: page
title: 터미널별 컨테이너 처리실적
kicker: 인천항 · 월별 공표자료 정리
standfirst: 인천항 컨테이너 부두는 신항·남항·국제여객부두로 나뉜다. 그 구분과 터미널별 월별 처리실적을 공표자료의 계층 그대로 옮기고, 기계가 읽을 수 있는 한 장으로 묶었다.
permalink: /terminals/
data_through: {latest}
collected: {COLLECTED}
source_next: 익월 하순 (실측 23~30일)
status: 관측 — 판정 대상 아님
description: 인천항 컨테이너 부두(신항·남항·국제여객부두)와 터미널 SNCT·HJIT·E1CT·ICT의 월별 처리실적 시계열. 공표자료의 합계·소계를 그대로 싣고 원본 링크와 해시를 함께 공개한다.
---

**이 표는 새 계산이 아니다.** 인천지방해양수산청이 매월 내는 공표자료를 그대로 옮기고,
**월마다 흩어져 있던 것을 한 장으로 묶은 것**이다. 몫(share)만 우리가 계산했다.

이 축은 **기계가 읽을 수 있는 형태로 공개된 적이 없다.** 게시판에 HWPX 파일로 월별로 올라오고,
시계열로 보려면 사람이 {n_src}개 파일을 열어야 한다. 그 일을 코드가 한 번 하고 결과를 공개한다.

<div class="callout warn">
<span class="k">먼저 읽을 것 — 이 데이터로 할 수 없는 일</span>
<p><b>단위가 천TEU다. 공표자료가 반올림해서 낸다</b> — 우리가 반올림한 게 아니다.
그래서 <b>한 자리 차이를 근거로 무엇도 주장할 수 없다.</b> 아래 몫(%)은 그 반올림된 값에서
계산했으므로 <b>같은 오차를 그대로 물려받는다.</b></p>
<p>그리고 이 소스에는 <b>공/적 구분도, 수출입 방향 축도 없다.</b> 없는 축은 여기서 볼 수 없다.</p>
</div>

## 그림 1 — 인천항 컨테이너 부두는 신항·남항·국제여객부두로 나뉜다

{structure_svg(d, denom)}

<p class="tnote">부두군별 당월 처리량의 구성 · {latest} 단월 · 단위 천TEU ·
출처 인천지방해양수산청 「월별 항만운영통계」.
<b>지도가 아니다.</b> 칸의 너비는 공표 소계에 비례할 뿐 위치·거리·방위를 뜻하지 않는다.
신항·남항·국제여객부두는 우리가 만든 분류가 아니라 <b>공표자료의 표가 직접 쓰는 구분</b>이다 —
그 표는 부두군마다 「소 계」 행을 따로 낸다.
터미널은 칸 안에 <b>글자로</b> 들었다. 너비로 그리면 반올림 때문에 칸을 넘거나 못 채우는데,
표에서는 그냥 숫자 차이지만 <b>그림에서는 그것이 거짓말이 된다.</b></p>

## 표 1 — 최신월 {latest}, 공표자료의 계층 그대로

{hierarchy_table(d, denom)}

<p class="tnote">단위 천TEU · 자료 기준 {latest} 단월과 연 누계 · 출처 인천지방해양수산청
「월별 항만운영통계」. <b>합계와 부두군 소계는 공표자료가 낸 값을 그대로 옮긴 것이고,
우리가 더한 값이 아니다.</b> 「당월 몫」만 우리가 계산했다 — 공표자료에 없는 열이며,
<b>분모는 공표 합계 {f(denom)}</b>다.</p>

{dl("이 표의 원자료 — 터미널·부두군·합계 월별", "analysis/terminal_monthly.csv",
    f"{len(months)}개월 · 89행")}

### 부분을 더한 값과 공표 합계가 왜 다른가

**둘 다 틀리지 않았다.** 공표값이 이미 천TEU로 반올림돼 있어서, 반올림된 부분을 더한 값과
반올림된 합계는 서로 어긋날 수 있다. {gap_line}

{naive_line}

**그래서 이 지면은 우리가 더한 값을 「합계」라고 부르지 않는다.** 합계 자리에는 공표자료가
낸 합계만 놓는다. 몫의 분모도 그것이다. 다섯 곳을 더한 값이 궁금하면 위 CSV에서 직접 더하면
되고, **그 값이 공표 합계와 다르다는 사실 자체가 이 데이터의 정밀도를 말해 준다.**

## 표 2 — 부두군 월별 {first} ~ {latest}

{group_series(months, cur)}

<p class="tnote">단위 천TEU · 각 월 공표자료의 「당월」 값 · {first}~{latest} · 부두군 소계와 공표 합계는
원문 그대로. 「그 외」는 원문에 있는 항목이며 <b>{first} 이후 대부분의 달에서 0 또는 1</b>이다.
빈칸은 그 달 원문에 그 행이나 값이 없다는 뜻이다 — 0으로 채우지 않았다.</p>

## 표 3 — 터미널 월별 {first} ~ {latest}

{terminal_series(months, cur)}

<p class="tnote">단위 천TEU · 각 월 공표자료의 「당월」 값 · {first}~{latest}.
1월호는 공표자료에 누계 열이 없다(누계가 당월과 같아 원문이 열을 생략한다).
수집 코드가 그 모양을 따로 처리한다 — 처리 안 하면 1월이 시계열에서 조용히 빠진다.</p>

{dl("원본 " + str(n_src) + "건의 주소와 SHA-256", "analysis/terminal_monthly_sources.csv",
    "감사추적")}

## 표 4 — 몫의 추이 {first} ~ {latest}

{share_series(months, cur)}

<p class="tnote">단위 % · 분모는 각 월의 <b>공표 합계</b> · {first}~{latest}.
<b>반올림된 천TEU에서 계산했으므로 소수점 한 자리의 움직임은 반올림일 수 있다.</b>
그 폭 안의 변화를 추세로 읽지 않는다. 다섯 곳의 몫을 더하면 100이 안 된다 —
<b>분모인 공표 합계에는 「그 외」가 같이 들어 있다.</b></p>

## 이 수치가 무엇을 말하고 무엇을 말하지 않는가

- **말하는 것** — 각 터미널과 부두군이 그 달에 몇 천TEU를 처리했다고 **공표자료에 적혀 있는가.**
- **말하지 않는 것** — 왜 그렇게 됐는가. 이 데이터로는 원인을 판별할 수 없고,
  이 사이트는 [인과·전망을 쓰지 않는다]({{{{ '/verify/' | relative_url }}}}).
  공표자료 본문에는 기관의 해설이 붙어 있지만 **그것을 여기로 옮기지 않는다.**
- **비교의 한계** — 터미널마다 선석·수심·항로 구성이 다르다. **처리량의 크기를
  운영 성과로 바로 읽을 수 없다.** 이 표는 규모를 나란히 놓을 뿐 순위를 매기지 않는다.
- **부두군도 마찬가지다.** 신항과 남항은 시설과 개장 시기가 다르다.
  **두 칸의 크기 차이를 그 자체로 무엇의 근거로도 쓰지 않는다.**

## 원본과 재현

원본 파일 {n_src}건의 주소와 SHA-256을 함께 공개한다. **같은 파일을 받아 같은 코드를 돌리면
같은 표가 나온다.** 안 나오면 그것이 우리 잘못이거나 원본이 바뀐 것이고, 둘 다 알아야 할 일이다.

<ul class="files">
<li><span class="ft">CSV</span> <a href="{GH}/analysis/terminal_monthly.csv">터미널·부두군·합계 월별 처리실적</a> <span class="meta">{len(months)}개월 · 계층 포함</span></li>
<li><span class="ft">CSV</span> <a href="{GH}/analysis/terminal_monthly_sources.csv">원본 {n_src}건의 주소와 해시</a> <span class="meta">감사추적</span></li>
<li><span class="ft">PY</span> <a href="{GH}/analysis/collect_terminal_monthly.py">수집·파싱 코드</a> <span class="meta">인수시험 · 수집 시점 검산 포함</span></li>
<li><span class="ft">PY</span> <a href="{GH}/analysis/build_terminals_page.py">이 지면을 만든 코드</a> <span class="meta">표를 손으로 옮기지 않는다</span></li>
<li><span class="ft">PY</span> <a href="{GH}/analysis/probe/probe_11_berth_group.py">부두군이 어디서 왔는지 확인한 프로브</a> <span class="meta">원문을 다시 열어 대조</span></li>
</ul>

<p class="tnote">소스: 인천지방해양수산청 「월별 항만운영통계」. 원시 자료의 권리는 제공 기관에 있고
재사용 조건은 그 기관의 약관을 따른다. 자세한 것은 <a href="{{{{ '/data/' | relative_url }}}}">데이터 지도</a>.</p>
"""


def build_home_block(csv_path=CSV) -> str:
    """첫 화면의 터미널 구획. **손으로 적힌 표를 이 블록이 대체한다.**

    2026-08-29 실측: 첫 화면 표가 손으로 적혀 있었고, 이미 낡아 있었다 —
    합계 283(우리 합)에 몫 27.6/37.8/8.1(분모 283)이었다. `/terminals/` 는 생성되는데
    첫 화면만 손이었으니, **갈라지는 것은 시간 문제가 아니라 이미 일어난 일**이었다.
    그래서 같은 CSV 에서 같은 코드가 만든다(사고 31 — 두 자리에 손으로 적으면 반드시 갈라진다).
    """
    months, cur = load(csv_path)
    latest = months[-1]
    d = cur[latest]
    denom = val(d.get(TOTAL), "당월_천TEU")
    y, m = latest.split("-")

    rows = []
    for name, level, indent in LAYOUT:
        r = d.get(name)
        if r is None or level == "그 외":
            continue
        sh = share(val(r, "당월_천TEU"), denom)
        band = ""
        if level == "부두군":
            band = next((f" b{i}" for i, (k, _, _) in enumerate(BANDS) if k == name), "")
        cls = {"합계": "lv-total", "부두군": "lv-group", "터미널": "lv-term"}[level]
        label = LABEL.get(name, name)
        rows.append(
            f"    <tr class=\"{cls}{band}\"><th class=\"lbl i{indent}\">{label}</th>"
            f"<td class='num'>{f(val(r, '당월_천TEU'))}</td>"
            f"{delta_cell(val(r, '전년대비_당월_%'))}"
            f"<td class='num'>{'–' if sh is None else f'{sh:.1f}'}</td></tr>")

    return f"""{HOME_BEGIN}
  <h2>인천항 컨테이너 부두 — {y}년 {int(m)}월</h2>
  <p class="note">
    인천항 컨테이너 부두는 <strong>신항 · 남항 · 국제여객부두</strong>로 나뉜다.
    그 구분과 아래 값은 인천지방해양수산청 월별 공표자료를 그대로 옮긴 것이다. 단위 천TEU.
    <strong>공표자료가 반올림해 내므로 한 자리 차이를 근거로 무엇도 주장할 수 없다.</strong>
  </p>

{structure_svg(d, denom)}

  <div class="tsw">
    <table class="hier">
      <thead><tr><th>구분</th><th class="num">당월 천TEU</th><th class="num">전년비 %</th><th class="num">몫 %</th></tr></thead>
      <tbody>
{chr(10).join(rows)}
      </tbody>
    </table>
  </div>
  <p class="tnote">
    <strong>합계와 부두군 소계는 공표자료가 낸 값</strong>이고 우리가 더한 값이 아니다.
    「몫」만 우리가 계산했다 — 공표자료에 없는 열이며 분모는 공표 합계 {f(denom)}이다.
    IPT는 국제여객부두. <strong>왜 그렇게 됐는지는 이 데이터로 판별할 수 없고, 쓰지 않는다.</strong>
  </p>
  <p class="more"><a href="{{{{ '/terminals/' | relative_url }}}}">{len(months)}개월 시계열 · 원본 해시 · 수집 코드 →</a></p>
{HOME_END}"""


CARD = os.path.join("..", "jisangj03-dev.github.io", "_og", "card.html")
CARD_BEGIN = "<!-- 카드표:시작 (생성됨. 손으로 고치지 마라 — analysis/build_terminals_page.py) -->"
CARD_END = "<!-- 카드표:끝 -->"


def build_card_block(csv_path=CSV) -> str:
    """링크 카드(`_og/card.html`)의 표. **여기도 손으로 적혀 있었다.**

    `_og/README.md` 는 이미 「데이터가 갱신되면 카드도 다시 찍는다 · 카드의 수치는
    CSV 에서 그대로 온 값이어야 한다 · 손으로 안 고친다」고 적어 놓고 있었는데,
    **정작 표는 손으로 적혀 있었다.** 규칙을 문서에 적고 기전은 안 만든 자리다(§0-3).
    이제 CSV 가 원본이고, 사람이 하는 일은 **다시 찍는 것** 하나로 줄었다.

    카드는 좁으므로 계층 전체가 아니라 **부두군 3행 + 공표 합계**만 든다.
    터미널까지 넣으면 17px 로 9행이 되어 카드에서 읽히지 않는다.
    """
    months, cur = load(csv_path)
    latest = months[-1]
    d = cur[latest]
    denom = val(d.get(TOTAL), "당월_천TEU")

    rows = []
    for key, label, kids in BANDS:
        r = d.get(key)
        if r is None:
            continue
        v = val(r, "당월_천TEU")
        dv = val(r, "전년대비_당월_%")
        cls = "up" if (dv or 0) > 0 else ("dn" if (dv or 0) < 0 else "")
        sign = "+" if (dv or 0) > 0 else ""
        sub = " · ".join(kids) if kids else "IPT"
        rows.append(
            f'      <tr><th>{label} <span class="sub">{sub}</span></th>'
            f'<td>{f(v)}</td><td class="{cls}">{sign}{dv:.1f}</td>'
            f'<td>{share(v, denom):.1f}</td></tr>')
    rows.append(
        f'      <tr class="tot"><th>컨테이너 합계</th><td>{f(denom)}</td>'
        f'<td>{"+" if (val(d.get(TOTAL), "전년대비_당월_%") or 0) > 0 else ""}'
        f'{val(d.get(TOTAL), "전년대비_당월_%"):.1f}</td><td>100.0</td></tr>')

    return (f"{CARD_BEGIN}\n"
            f"    <thead><tr><th>부두군별 처리실적 · {latest}</th><th>천TEU</th>"
            f"<th>전년비 %</th><th>몫 %</th></tr></thead>\n"
            f"    <tbody>\n" + "\n".join(rows) + f"\n    </tbody>\n{CARD_END}")


def splice(text: str, block: str, begin: str, end: str, what: str) -> str:
    """생성 구획을 갈아 끼운다. 표지가 없으면 **쓰지 않는다.**"""
    i, j = text.find(begin), text.find(end)
    if i < 0 or j < 0 or j < i:
        raise ValueError(f"{what}에 생성 구획 표지가 없다 — 손으로 한 번 넣어야 한다")
    return text[:i] + block + text[j + len(end):]


def splice_home(text: str, block: str) -> str:
    """첫 화면의 생성 구획을 갈아 끼운다. 표지가 없으면 **쓰지 않는다.**"""
    i, j = text.find(HOME_BEGIN), text.find(HOME_END)
    if i < 0 or j < 0 or j < i:
        raise ValueError("첫 화면에 생성 구획 표지가 없다 — 손으로 한 번 넣어야 한다")
    return text[:i] + block + text[j + len(HOME_END):]


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 몫의 분모 ──")
    chk("분모가 공표 합계면 78/282", round(share(78, 282), 1), 27.7)
    chk("**분모가 다섯 곳 합이면 78/283 — 이 값이 종전 지면 값이다**",
        round(share(78, 283), 1), 27.6)
    chk("분모 0 이면 계산 안 한다", share(78, 0), None)
    chk("값이 없으면 계산 안 한다", share(None, 282), None)

    print("── 인수시험: 실물 CSV ──")
    months, cur = load()
    d = cur[months[-1]]
    chk("최신월에 공표 합계 행이 있다", TOTAL in d, True)
    chk("최신월에 부두군 소계가 둘 있다",
        sum(1 for k in ("신항", "남항") if k in d), 2)
    chk("공표 합계는 우리 합(283)이 아니다",
        val(d[TOTAL], "당월_천TEU") != sum(val(d[t], "당월_천TEU") for t in TERMS), True)

    denom = val(d[TOTAL], "당월_천TEU")
    band = sum(val(d[k], "당월_천TEU") for k, _, _ in BANDS)
    chk("구조도 세 칸의 합 = 공표 합계 (그림이 안 넘친다)", band, denom)

    checked, hit, worst = rounding_gaps(months, cur)
    chk("검산 자리가 있다", checked > 0, True)
    chk("어긋남은 반올림 범위 안이다 (2 이상이면 구조 이상)", worst <= 1.0, True)

    print("── 인수시험: 생성물 ──")
    text = build()
    chk("표 4개가 다 있다", all(f"## 표 {i}" in text for i in (1, 2, 3, 4)), True)
    chk("그림 1 이 있다", "## 그림 1" in text, True)
    chk("구조도 SVG 가 들어갔다", '<svg class="portmap wide"' in text, True)
    chk("좁은 화면용 배치도 같이 나간다", '<svg class="portmap narrow"' in text, True)
    chk("두 배치의 값이 같다 — 배치만 다르다",
        text.count("184 천TEU") >= 1 and "184 천TEU · 65.2%" in text, True)
    # kramdown 이 svg 를 블록으로 안 보므로 div 로 감싸야 한다. **여닫이가 짝이 맞아야 한다** —
    # 한 번은 여는 태그만 붙이고 닫는 걸 빠뜨려 열린 div 가 지면으로 나갔다(2026-08-29).
    chk("구조도가 div 로 감싸였다", text.count('<div class="portfig">'), 1)
    chk("그 div 가 닫혔다", text.count('</svg>\n</div>'), 1)
    chk("부두군 마커 색을 생성기가 명시한다 (위치 의존이 아니다)",
        all(f"lv-group b{i}" in text for i in range(3)), True)
    chk("절 제목에 「## 1.」이 없다 (린터 오인 방지)",
        any(l.startswith("## 1.") or l.startswith("## 3.") for l in text.splitlines()), False)
    chk("공표 합계를 「합계」로 부르는 열이 있다", "공표 합계" in text, True)
    chk("내려받기 줄이 있다", 'class="dlrow"' in text, True)
    chk("회사명이 안 들어갔다 (§4.1-1)",
        any(w in text for w in ("선광", "한진", "이원", "인천컨테이너터미널")), False)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    if not os.path.exists(CSV):
        print(f"[중단] {CSV} 가 없다. 먼저 collect_terminal_monthly.py 를 돌린다.")
        return 2
    if a.selftest:
        return selftest()
    text = build()
    block = build_home_block()
    home_old = io.open(HOME, encoding="utf-8").read() if os.path.exists(HOME) else ""
    home_new = splice(home_old, block, HOME_BEGIN, HOME_END, "첫 화면") if home_old else ""
    card_block = build_card_block()
    card_old = io.open(CARD, encoding="utf-8").read() if os.path.exists(CARD) else ""
    card_new = splice(card_old, card_block, CARD_BEGIN, CARD_END, "링크 카드") if card_old else ""

    if a.check:
        same = (io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else "") == text
        home_same, card_same = home_old == home_new, card_old == card_new
        print("지면 " + ("일치" if same else "**다르다 — 다시 생성해야 한다**"))
        print("첫 화면 구획 " + ("일치" if home_same else "**다르다 — 다시 생성해야 한다**"))
        print("링크 카드 구획 " + ("일치" if card_same else "**다르다 — 다시 생성해야 한다**"))
        return 0 if (same and home_same and card_same) else 1

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print(f"-> {OUT}  ({len(text):,} B)")
    io.open(HOME, "w", encoding="utf-8", newline="\n").write(home_new)
    print(f"-> {HOME}  (터미널 구획 {len(block):,} B)")
    if card_new and card_new != card_old:
        io.open(CARD, "w", encoding="utf-8", newline="\n").write(card_new)
        print(f"-> {CARD}  (카드 표 {len(card_block):,} B)")
        print("   **카드 표가 바뀌었다. `assets/og.png` 를 다시 찍어야 한다** — 절차는 `_og/README.md`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

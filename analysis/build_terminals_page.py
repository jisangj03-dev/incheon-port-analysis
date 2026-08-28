"""`analysis/terminal_monthly.csv` 로 허브의 `/terminals/` 지면을 생성한다.

**손으로 표를 옮겨 적지 않는다.** 옮겨 적으면 그 순간 데이터와 지면이 갈리고,
갈린 것은 아무도 모른다. 이 스크립트가 CSV 하나에서 지면을 만든다 —
데이터가 바뀌면 지면도 한 번에 바뀐다.

**지위는 `관측`이다.** 공표자료를 그대로 옮기고 몫(share)만 계산했다.
판정 대상이 아니고, 선커밋 기준이 걸려 있지 않다.

**절 제목을 「1.」「3.」으로 달지 않는다 — 의도된 제약이다.**
`lint_publish.py` 의 `conclusion_zones()` 가 `^##\s*1[.\s]` 와 `^##\s*3[.\s]` 를
**보고서의 §1 핵심 요약 · §3 해석**으로 읽는다(지침 §2.5 골격 계약).
처음에 「## 1. 최신월」로 달았더니 린터가 이 지면을 보고서로 오인해
표 안의 수치 전부를 결론 자리 미등재로 잡았다(WARN 66건).
**린터를 고치지 않고 지면을 고쳤다.** 검사기를 통과시키려고 검사기를 무르게 하는 것이
이 프로젝트가 막는 일이다. 그리고 통계 간행물은 원래 **표에 번호를 단다** — 더 맞는 형식이다.

**단위가 천TEU라는 것이 이 지면의 가장 큰 한계다.**
공표자료가 반올림해 낸다 — 우리가 반올림한 게 아니다. 그래서
**한 자리 차이는 반올림일 수 있고, 거기서 나온 몫도 같은 오차를 진다.**
그 문장을 지면 안에 넣는다. 각주가 아니라 본문에.

    python analysis/build_terminals_page.py
    python analysis/build_terminals_page.py --check   # 다시 생성해 현재 파일과 대조만
"""
from __future__ import annotations
import argparse
import csv
import io
import os
import sys

CSV = os.path.join("analysis", "terminal_monthly.csv")
OUT = os.path.join("..", "jisangj03-dev.github.io", "terminals", "index.md")
ORDER = ["SNCT", "HJIT", "E1CT", "ICT", "IPT"]
GROUP = {"SNCT": "신항", "HJIT": "신항", "E1CT": "남항", "ICT": "남항", "IPT": "국제여객부두"}


def load():
    rows = list(csv.DictReader(io.open(CSV, encoding="utf-8-sig")))
    months = sorted({r["기준연월"] for r in rows})
    cur = {}
    for r in rows:
        cur.setdefault(r["기준연월"], {})[r["터미널"]] = r
    return months, cur


def f(v, nd=0):
    if v in (None, ""):
        return "–"
    try:
        return f"{float(v):,.{nd}f}"
    except ValueError:
        return "–"


def delta_cell(v):
    if v in (None, ""):
        return "<td>–</td>"
    x = float(v)
    cls = "d-up" if x > 0 else ("d-dn" if x < 0 else "")
    sign = "+" if x > 0 else ""
    return f'<td class="{cls}">{sign}{x:.1f}</td>'


def build() -> str:
    months, cur = load()
    latest = months[-1]
    first = months[0]
    present = [t for t in ORDER if any(t in cur[m] for m in months)]

    # ── 최신월 표 ──────────────────────────────────────────────────────
    head = ['<div class="tablewrap"><table class="data">',
            "<thead><tr><th>터미널</th><th>부두군</th>"
            "<th style='text-align:right'>당월</th><th style='text-align:right'>전년 동월</th>"
            "<th style='text-align:right'>전년비 %</th><th style='text-align:right'>연 누계</th>"
            "<th style='text-align:right'>누계 전년비 %</th>"
            "<th style='text-align:right'>당월 몫 %</th></tr></thead><tbody>"]
    tot = sum(float(cur[latest][t]["당월_천TEU"]) for t in present if t in cur[latest])
    for t in present:
        r = cur[latest].get(t)
        if not r:
            continue
        share = float(r["당월_천TEU"]) / tot * 100 if tot else 0
        head.append(
            f"<tr><td><b>{t}</b></td><td>{GROUP[t]}</td>"
            f"<td style='text-align:right'>{f(r['당월_천TEU'])}</td>"
            f"<td style='text-align:right'>{f(r['전년당월_천TEU'])}</td>"
            f"{delta_cell(r['전년대비_당월_%'])}"
            f"<td style='text-align:right'>{f(r['누계_천TEU'])}</td>"
            f"{delta_cell(r['전년대비_누계_%'])}"
            f"<td style='text-align:right'>{share:.1f}</td></tr>"
        )
    head.append(
        f"<tr class='sum'><td colspan='2'><b>합계</b></td>"
        f"<td style='text-align:right'><b>{tot:,.0f}</b></td><td colspan='5'></td></tr>"
    )
    head.append("</tbody></table></div>")
    latest_table = "\n".join(head)

    # ── 월별 시계열 ────────────────────────────────────────────────────
    ts = ['<div class="tsw"><table>', "<thead><tr><th>기준월</th>"]
    ts += [f"<th>{t}</th>" for t in present]
    ts.append("<th>합계</th></tr></thead><tbody>")
    for m in months:
        ts.append(f"<tr><th>{m}</th>")
        s = 0.0
        for t in present:
            r = cur[m].get(t)
            if r:
                s += float(r["당월_천TEU"])
                ts.append(f"<td>{f(r['당월_천TEU'])}</td>")
            else:
                ts.append("<td>–</td>")
        ts.append(f"<td><b>{s:,.0f}</b></td></tr>")
    ts.append("</tbody></table></div>")
    series_table = "\n".join(ts)

    # ── 몫 시계열 ──────────────────────────────────────────────────────
    sh = ['<div class="tsw"><table>', "<thead><tr><th>기준월</th>"]
    sh += [f"<th>{t}</th>" for t in present]
    sh.append("</tr></thead><tbody>")
    for m in months:
        s = sum(float(cur[m][t]["당월_천TEU"]) for t in present if t in cur[m])
        sh.append(f"<tr><th>{m}</th>")
        for t in present:
            r = cur[m].get(t)
            sh.append(f"<td>{float(r['당월_천TEU'])/s*100:.1f}</td>" if r and s else "<td>–</td>")
        sh.append("</tr>")
    sh.append("</tbody></table></div>")
    share_table = "\n".join(sh)

    src_rows = list(csv.DictReader(io.open(
        os.path.join("analysis", "terminal_monthly_sources.csv"), encoding="utf-8-sig")))
    n_src = len(src_rows)

    return f"""---
layout: page
title: 터미널별 컨테이너 처리실적
kicker: 인천항 · 월별 공표자료 정리
standfirst: 인천항 컨테이너 터미널 다섯 곳의 월별 처리실적을 공표자료에서 그대로 옮기고, 기계가 읽을 수 있는 한 장으로 묶었다.
permalink: /terminals/
data_through: {latest}
collected: 2026-08-28
source_next: 익월 하순 (실측 23~30일)
status: 관측 — 판정 대상 아님
description: 인천항 컨테이너 터미널(SNCT·HJIT·E1CT·ICT·국제여객부두)의 월별 처리실적 시계열. 공표자료 원본 링크와 해시를 함께 싣는다.
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

## 표 1 — 최신월 {latest}

{latest_table}

<p class="tnote">단위 천TEU. 「당월 몫」은 위 다섯 곳의 합을 100으로 본 값이며 <b>우리가 계산했다</b> —
공표자료에 없는 열이다. 공표자료의 컨테이너 합계에는 「그 외」 항목이 따로 있어
<b>이 몫의 분모는 항만 전체가 아니라 이 다섯 곳이다.</b></p>

## 표 2 — 월별 처리실적 {first} ~ {latest}

{series_table}

<p class="tnote">단위 천TEU · 각 월 공표자료의 「당월」 값. 1월호는 공표자료에 누계 열이 없다
(누계가 당월과 같아 원문이 열을 생략한다). 수집 코드가 그 모양을 따로 처리한다.</p>

## 표 3 — 몫의 추이

{share_table}

<p class="tnote">단위 %. 다섯 곳의 합을 100으로 본 값이다. <b>반올림된 천TEU에서 계산했으므로
소수점 한 자리의 움직임은 반올림일 수 있다.</b> 그 폭 안의 변화를 추세로 읽지 않는다.</p>

## 이 수치가 무엇을 말하고 무엇을 말하지 않는가

- **말하는 것** — 각 터미널이 그 달에 몇 천TEU를 처리했다고 **공표자료에 적혀 있는가.**
- **말하지 않는 것** — 왜 그렇게 됐는가. 이 데이터로는 원인을 판별할 수 없고,
  이 사이트는 [인과·전망을 쓰지 않는다]({{{{ '/verify/' | relative_url }}}}).
  공표자료 본문에는 기관의 해설이 붙어 있지만 **그것을 여기로 옮기지 않는다.**
- **비교의 한계** — 터미널마다 선석·수심·항로 구성이 다르다. **처리량의 크기를
  운영 성과로 바로 읽을 수 없다.** 이 표는 규모를 나란히 놓을 뿐 순위를 매기지 않는다.

## 원본과 재현

원본 파일 {n_src}건의 주소와 SHA-256을 함께 공개한다. **같은 파일을 받아 같은 코드를 돌리면
같은 표가 나온다.** 안 나오면 그것이 우리 잘못이거나 원본이 바뀐 것이고, 둘 다 알아야 할 일이다.

<ul class="files">
<li><span class="ft">CSV</span> <a href="https://github.com/jisangj03-dev/incheon-port-analysis/blob/main/analysis/terminal_monthly.csv">터미널별 월별 처리실적</a> <span class="meta">{len(months)}개월 · {len(present)}터미널</span></li>
<li><span class="ft">CSV</span> <a href="https://github.com/jisangj03-dev/incheon-port-analysis/blob/main/analysis/terminal_monthly_sources.csv">원본 {n_src}건의 주소와 해시</a> <span class="meta">감사추적</span></li>
<li><span class="ft">PY</span> <a href="https://github.com/jisangj03-dev/incheon-port-analysis/blob/main/analysis/collect_terminal_monthly.py">수집·파싱 코드</a> <span class="meta">인수시험 포함</span></li>
<li><span class="ft">PY</span> <a href="https://github.com/jisangj03-dev/incheon-port-analysis/blob/main/analysis/build_terminals_page.py">이 지면을 만든 코드</a> <span class="meta">표를 손으로 옮기지 않는다</span></li>
</ul>

<p class="tnote">소스: 인천지방해양수산청 「월별 항만운영통계」. 원시 자료의 권리는 제공 기관에 있고
재사용 조건은 그 기관의 약관을 따른다. 자세한 것은 <a href="{{{{ '/data/' | relative_url }}}}">데이터 지도</a>.</p>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)
    if not os.path.exists(CSV):
        print(f"[중단] {CSV} 가 없다. 먼저 collect_terminal_monthly.py 를 돌린다.")
        return 2
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

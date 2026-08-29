# -*- coding: utf-8 -*-
"""허브의 `/datasets/` 지면을 생성한다 — **데이터 카탈로그.**

왜 이 지면이 생겼나
-------------------
2026-08-29 실측. 이 저장소에는 **CSV 20개 · 688 KB** 의 기계판독 자산이 있다.
그런데 **사이트에서 그것을 찾을 방법이 없다.** 편마다 부록에 링크가 흩어져 있고,
`/data/` 는 「어느 기관에서 받았나」를 말할 뿐 **「우리가 무엇을 만들어 뒀나」는 말하지 않는다.**

그리고 항만 사이트를 직접 훑어 보니(2026-08-29 브라우저 조사) 이 자리가 비어 있는 것이
우리만의 문제가 아니었다 — **표본의 항만 당국 대부분이 PDF·게시판으로 낸다.**
반대로 **`data.gov.sg`(싱가포르 MPA 물동량)** 가 데이터 지면의 완성형을 보여 준다:

  제공자 · **자료 창(from–to)** · 마지막 갱신 · **파일 크기와 행수** · 열 스키마 ·
  **열별 빈칸 비율** · 내려받기 · **이력(See history)**

**그 항목이 전부 우리 CSV 에서 기계로 뽑힌다.** 손으로 적을 것은 한 줄 설명뿐이다.
그래서 카탈로그를 **생성**한다 — 손으로 적으면 파일이 늘 때마다 갈라진다(사고 56).

봉인 파일 — 이 생성기가 **열지 않는 것**
------------------------------------------
지침 §4 정지선이 **열람 금지** 2건을 둔다(`_probe_dump.txt` · `probe/probe_2026_raw.csv`).
이 생성기는 그 파일들을 **열지 않는다.** 크기와 존재만 적고, **왜 안 여는지를 지면이 말한다.**

  **안 여는 것을 안 여는 채로 목록에 싣는 것**이 이 지면의 성격을 가장 잘 드러낸다 —
  카탈로그가 「우리가 가진 전부」가 아니라 **「우리가 열기로 한 것과 안 열기로 한 것」**이다.

  python analysis/build_datasets_page.py
  python analysis/build_datasets_page.py --check
  python analysis/build_datasets_page.py --selftest

닿지 않는 곳
------------
1. **한 줄 설명은 손으로 적는다.** 파일에서 뽑을 수 없다. 설명이 없는 파일은
   **목록에서 빼지 않고 「설명 없음」으로 낸다** — 빼면 새 파일이 조용히 사라진다.
2. **형식 추론은 표본 기반이다.** 열의 값을 훑어 정수·실수·연월·날짜·문자로 나눈다.
   섞여 있으면 「혼합」이라 적는다. **추론이라고 지면에 적는다.**
3. **창(from–to)은 연월·연도 열이 있을 때만** 낸다. 없으면 비운다. 지어내지 않는다.
4. **행수는 머리행을 뺀 값**이다. 빈 줄은 세지 않는다.
"""
from __future__ import annotations
import argparse
import csv
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join("..", "jisangj03-dev.github.io", "datasets", "index.md")
GH = "https://github.com/jisangj03-dev/incheon-port-analysis/blob/main"
COLLECTED = "2026-08-29"

# **§4 열람 금지.** 이 생성기는 이 경로를 열지 않는다. 크기만 적는다.
SEALED = ("_probe_dump.txt", "analysis/probe/probe_2026_raw.csv")

# **§4 수정 금지 앵커.** 읽기는 한다 — `verify_anchors.py` 가 매번 해시를 대조한다.
ANCHORED = ("analysis/container_2025_direction.csv",
            "analysis/container_2026_direction.csv",
            "analysis/probe/recheck_2025_direction_20260804.csv")

# 한 줄 설명 — **파일에서 못 뽑는 유일한 항목이라 손으로 적는다.**
# 없는 파일은 목록에서 빼지 않고 「설명 없음」으로 낸다(닿지 않는 곳 1).
DESC = {
    "analysis/terminal_monthly.csv":
        ("인천항 컨테이너 **터미널·부두군·합계** 월별 처리실적. 공표자료의 계층을 그대로 담는다",
         "/terminals/"),
    "analysis/terminal_monthly_sources.csv":
        ("위 자료의 **원본 게시물 주소와 SHA-256**. 감사추적", "/terminals/"),
    "analysis/port_container_berths.csv":
        ("인천항 **컨테이너 부두**의 안벽 길이·전면수심·동시접안능력", "/berths/"),
    "analysis/port_regions.csv":
        ("인천항·경인항 **구역별** 선석 수·안벽 길이·하역능력", "/berths/"),
    "analysis/port_usage.csv":
        ("**용도별(취급화물)** 선석 수·안벽 길이·하역능력. 구역별 표와 교차 검산용", "/berths/"),
    "analysis/port_facilities_sources.csv":
        ("위 셋의 **원본 지면 주소와 SHA-256**. 감사추적", "/berths/"),
    "analysis/container_2025.csv":
        ("2025년 인천항 **공컨테이너** 월별 — 외국적/한국적/전체", "#01"),
    "analysis/container_total_2025.csv":
        ("2025년 인천항 **전체 컨테이너** 월별. 공컨 비율의 **분모**", "#02"),
    "analysis/container_2022_direction.csv":
        ("2022년 공컨 **방향별 원시 응답**(수입/수출/환적·외항/연안·규격별)", "#04"),
    "analysis/container_2023_direction.csv":
        ("2023년 공컨 방향별 원시 응답", "#04"),
    "analysis/container_2024_direction.csv":
        ("2024년 공컨 방향별 원시 응답", "#04"),
    "analysis/container_2025_direction.csv":
        ("2025년 공컨 방향별 원시 응답", "#03·#04"),
    "analysis/container_2026_direction.csv":
        ("2026년 공컨 방향별 원시 응답 — **잠정치 구간**", "#07"),
    "analysis/total_container_direction.csv":
        ("연도별 인천항 **전체 컨테이너** 수입·수출·환적", "#05"),
    "analysis/size_direction_monthly.csv":
        ("**규격(40ft)×방향** 월별 박스 수와 비중", "#06"),
    "analysis/porttrade_202412_202607.csv":
        ("관세청 **수출입 신고** 원시 응답(항만별·월별). #08 교차 소스 대조", "#08"),
    "analysis/probe/recheck_2025_direction_20260804.csv":
        ("2025년 방향별 **회귀 앵커 재수집분**(사고 7)", "회귀 앵커"),
    "analysis/probe/probe_2024_raw.csv":
        ("2024년 프로브 원시 응답. **그 값을 어떻게 찾았나**의 감사추적", "프로브"),
    "analysis/probe/recheck_2025_raw.csv":
        ("2025년 재확인 프로브 원시 응답", "프로브"),
    "analysis/probe/probe_2026_raw.csv":
        ("2026년 프로브 원시 응답 — **열람 금지**(§4)", "프로브"),
    "_probe_dump.txt":
        ("초기 프로브 전량 덤프 — **열람 금지**(§4)", "프로브"),
}

YM = re.compile(r"^\d{4}[-./]\d{1,2}$")
YMD = re.compile(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}")
YEAR = re.compile(r"^(19|20)\d{2}$")
INT = re.compile(r"^-?\d+$")
NUM = re.compile(r"^-?\d+(\.\d+)?$")


# ── 순수 함수 ───────────────────────────────────────────────────────────────

def md_bold(text):
    """`**강조**` 를 `<b>` 로 바꾼다.

    설명을 원시 HTML(`<dd>`) 안에 넣으므로 **마크다운이 안 풀린다** — 화면에 별표가
    그대로 찍힌다(2026-08-29 실측). 소스에서는 `**` 로 쓰는 편이 읽기 좋아서
    출력 직전에만 바꾼다.
    **역참조를 문자열로 안 쓴다.** 처음엔 역참조를 문자열에 넣었는데 셸을 거치며
    제어문자 0x01 로 들어갔고, 결과가 <b></b> — 굵게 하려던 글자가 통째로 사라졌다
    (2026-08-29 실측). **렌더가 아니라 생성기에서 없어진 것이라 화면만 보면
    미리보기 탓으로 읽기 쉬운 자리였다.** 함수로 받으면 그 경로가 없다.
    """
    return re.sub(r"\*\*(.+?)\*\*", lambda m: "<b>" + m.group(1) + "</b>", text or "")


def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def is_sealed(relpath):
    return relpath in SEALED


def kind_of(values):
    """열의 형식을 표본으로 추론한다. **추론이라고 지면에 적는다.**"""
    vals = [v.strip() for v in values if v is not None and v.strip() != ""]
    if not vals:
        return "빈 열"
    tests = (("연월", YM), ("날짜", YMD), ("연도", YEAR), ("정수", INT), ("실수", NUM))
    for name, pat in tests:
        if all(pat.match(v) for v in vals):
            return name
    if all(NUM.match(v) for v in vals):
        return "실수"
    return "문자"


def window_of(header, cols):
    """연월·연도 열이 있으면 (처음, 끝). 없으면 None — **지어내지 않는다.**"""
    for i, name in enumerate(header):
        vals = sorted({v.strip() for v in cols[i] if v and v.strip()})
        if not vals:
            continue
        if all(YM.match(v) for v in vals) or all(YEAR.match(v) for v in vals):
            return vals[0], vals[-1]
    return None


def profile(path):
    """CSV 한 장의 프로필. **봉인 파일에는 절대 부르지 않는다.**"""
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f) if any((c or "").strip() for c in r)]
    if not rows:
        return {"행": 0, "열": 0, "스키마": [], "창": None}
    header, body = rows[0], rows[1:]
    cols = [[r[i] if i < len(r) else "" for r in body] for i in range(len(header))]
    schema = []
    for i, name in enumerate(header):
        vals = cols[i]
        blank = sum(1 for v in vals if not (v or "").strip())
        schema.append({
            "이름": name,
            "형식": kind_of(vals),
            "빈칸": (blank / len(vals) * 100) if vals else 0.0,
        })
    return {"행": len(body), "열": len(header), "스키마": schema,
            "창": window_of(header, cols)}


def collect(root=ROOT):
    """카탈로그 대상. **봉인은 열지 않고 목록에는 넣는다.**"""
    out = []
    paths = []
    for base in ("analysis", "analysis/probe", ""):
        d = os.path.join(root, base) if base else root
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if not os.path.isfile(p):
                continue
            r = rel(p)
            if r.endswith(".csv") or r in SEALED:
                if r not in [x["경로"] for x in out]:
                    paths.append(r)
    for r in sorted(set(paths)):
        p = os.path.join(root, r.replace("/", os.sep))
        item = {
            "경로": r, "바이트": os.path.getsize(p),
            "봉인": is_sealed(r), "앵커": r in ANCHORED,
            "설명": DESC.get(r, (None, None))[0],
            "쓴곳": DESC.get(r, (None, None))[1],
        }
        if item["봉인"]:
            item.update({"행": None, "열": None, "스키마": [], "창": None})
        else:
            item.update(profile(p))
        out.append(item)
    return out


# ── 지면 ────────────────────────────────────────────────────────────────────

def fmt_bytes(n):
    return f"{n:,} B" if n < 1024 else f"{n/1024:,.1f} KB"


def schema_table(item):
    if not item["스키마"]:
        return ""
    # 사이트의 다른 표와 같은 표기(쌍따옴표)를 쓴다 — 섞이면 검사도 사람도 헷갈린다.
    rows = "\n".join(
        '<tr><td class="lbl"><code>%s</code></td><td>%s</td>'
        '<td class="num">%.0f%%</td></tr>' % (c["이름"], c["형식"], c["빈칸"])
        for c in item["스키마"])
    return ('<div class="tablewrap"><table class="data schema">'
            '<thead><tr><th>열</th><th>형식(추론)</th><th class="num">빈칸</th></tr></thead>'
            '<tbody>\n' + rows + '\n</tbody></table></div>')


def build(root=ROOT) -> str:
    items = collect(root)
    live = [i for i in items if not i["봉인"]]
    sealed = [i for i in items if i["봉인"]]
    total_b = sum(i["바이트"] for i in items)
    total_rows = sum(i["행"] or 0 for i in live)
    n_anchor = sum(1 for i in items if i["앵커"])
    n_nodesc = sum(1 for i in items if not i["설명"])

    cards = []
    for i in live:
        win = f"{i['창'][0]} ~ {i['창'][1]}" if i["창"] else "—"
        badge = " · <span class=\"pill on\">SHA-256 앵커</span>" if i["앵커"] else ""
        desc = i["설명"] or "**설명 없음** — 이 목록은 파일을 빼지 않는다. 설명이 비면 비었다고 적는다"
        used = i["쓴곳"] or "—"
        cards.append(f"""<div class="src">
  <div class="src-head">
    <h3><code>{os.path.basename(i['경로'])}</code></h3>
    <span class="fmt machine">CSV</span>
  </div>
  <dl>
    <dt>무엇</dt><dd>{md_bold(desc)}</dd>
    <dt>창</dt><dd>{win}</dd>
    <dt>크기</dt><dd>{i['행']:,}행 · {i['열']}열 · {fmt_bytes(i['바이트'])}{badge}</dd>
    <dt>쓴 곳</dt><dd>{used}</dd>
  </dl>
{schema_table(i)}
  <div class="src-foot">
    <span><a href="{GH}/{i['경로']}">내려받기 · {i['경로']}</a></span>
  </div>
</div>""")

    sealed_rows = "\n".join(
        '<tr><td class="lbl"><code>%s</code></td>'
        '<td class="num">%s</td><td>%s</td></tr>'
        % (i["경로"], fmt_bytes(i["바이트"]), md_bold(i["설명"]) or "—") for i in sealed)

    verify_link = "{{ '/verify/' | relative_url }}"
    data_link = "{{ '/data/' | relative_url }}"

    return f"""---
layout: page
title: 데이터 카탈로그
kicker: 인천항 · 기계판독 자료
standfirst: 이 저장소가 공개하는 CSV 전부를 한 자리에 놓는다. 파일마다 창·행수·열 스키마·열별 빈칸 비율을 같이 적는다. 열지 않기로 한 파일도 목록에 있다.
permalink: /datasets/
collected: {COLLECTED}
status: 관측 — 판정 대상 아님
description: 인천항 물동량 리서치가 공개하는 기계판독 CSV {len(live)}건의 카탈로그. 파일마다 자료 창·행수·열 스키마·빈칸 비율·SHA-256 앵커 여부를 함께 싣는다.
---

**여기 있는 것은 우리가 만든 파일이다.** 어느 기관에서 무엇을 받았는지는
[데이터 지도]({data_link})가 든다. 이 지면은 **그 원본으로 우리가 무엇을 만들어 뒀는지**를 든다.

<dl class="issue">
  <div><dt>공개 파일</dt><dd>{len(live)}건</dd></div>
  <div><dt>합계 행수</dt><dd>{total_rows:,}행</dd></div>
  <div><dt>합계 크기</dt><dd>{fmt_bytes(total_b)}</dd></div>
  <div><dt>SHA-256 앵커</dt><dd>{n_anchor}건</dd></div>
  <div><dt>열람 금지</dt><dd>{len(sealed)}건</dd></div>
</dl>

<div class="callout warn">
<span class="k">이 카탈로그가 스스로에게 거는 규칙</span>
<p><b>파일을 목록에서 빼지 않는다.</b> 설명이 없으면 「설명 없음」으로 낸다 —
빼면 새로 생긴 파일이 조용히 사라지고, 그러면 이 목록이 「전부」라는 말이 거짓이 된다.
지금 설명이 빈 파일은 <b>{n_nodesc}건</b>이다.</p>
<p><b>형식은 추론이다.</b> 열의 값을 훑어 정수·실수·연월·날짜·문자로 나눈 것이지
스키마 선언을 읽은 것이 아니다. <b>창</b>도 연월·연도 열이 있을 때만 낸다 — 없으면 비운다.</p>
</div>

## 표 1 — 공개 파일 {len(live)}건

<div class="srcs">
{"".join(cards)}
</div>

## 열지 않는 파일 {len(sealed)}건

**목록에는 있고 내용은 안 읽는다.** 지침 §4 정지선이 이 둘을 **열람 금지**로 둔다.
이 지면을 만드는 코드도 그것을 지킨다 — 크기와 존재만 적고 파일을 열지 않는다.

<div class="tablewrap"><table class="data">
<thead><tr><th>경로</th><th class="num">크기</th><th>무엇</th></tr></thead>
<tbody>
{sealed_rows}
</tbody></table></div>

<p class="tnote"><b>왜 이것을 공개 목록에 적는가.</b> 안 여는 파일을 목록에서 빼면
카탈로그가 「우리가 가진 전부」로 읽힌다. 실제로는
<b>「우리가 열기로 한 것과 안 열기로 한 것」</b>이고, 후자가 있다는 사실 자체가
이 저장소가 지키는 규율의 일부다. 파일은 커밋에 남아 있으므로 누구든 직접 열 수 있다 —
<b>우리가 안 여는 것이지 감춘 것이 아니다.</b></p>

## 이 파일들을 쓸 때

- **우리 산출물은 자유롭게 쓰되 출처를 적어 달라.** 인용 형식은
  [검증 방식]({verify_link})이 든다.
- **원시 자료의 권리는 제공 기관에 있다.** 인천지방해양수산청·관세청·인천항만공사의
  약관을 따른다. 우리가 그 조건을 바꿀 수 없다.
- **SHA-256 앵커가 붙은 파일은 수정 금지다**(§4). 같은 값을 다시 받아 대조하는 것이
  이 저장소의 회귀 시험이고, 파일이 바뀌면 그 시험이 무의미해진다.
- **빈칸을 0으로 채우지 않았다.** 원문에 값이 없으면 없는 채로 뒀다 —
  위 스키마 표의 「빈칸」이 그 비율이다.

<p class="tnote">이 지면은 <code>analysis/build_datasets_page.py</code> 가
<b>파일에서 직접 생성</b>한다. 행수·크기·스키마·빈칸 비율을 손으로 옮기지 않는다 —
옮기면 파일이 늘 때마다 갈라진다.</p>
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

    print("── 인수시험: 설명의 강조 (내용이 사라지지 않는가) ──")
    chk("**강조**가 <b>로 바뀐다", md_bold("가 **나다** 라"), "가 <b>나다</b> 라")
    chk("**안쪽 글자가 남는다** (역참조가 깨지면 여기서 빈다)",
        "나다" in md_bold("가 **나다** 라"), True)
    chk("강조가 없으면 그대로", md_bold("가나다"), "가나다")
    chk("여럿도 각각", md_bold("**가** 와 **나**"), "<b>가</b> 와 <b>나</b>")
    chk("None 은 빈 문자열", md_bold(None), "")

    print("── 인수시험: 형식 추론 ──")
    chk("연월", kind_of(["2026-07", "2025-10"]), "연월")
    chk("연도", kind_of(["2022", "2025"]), "연도")
    chk("정수", kind_of(["1", "-3", "1000"]), "정수")
    chk("실수", kind_of(["1.5", "2"]), "실수")
    chk("문자", kind_of(["SNCT", "신항"]), "문자")
    chk("섞이면 문자", kind_of(["1", "SNCT"]), "문자")
    chk("전부 비면 빈 열", kind_of(["", "  "]), "빈 열")
    chk("빈칸은 형식 판정에서 빠진다", kind_of(["2026-07", "", "2025-10"]), "연월")

    print("── 인수시험: 창은 지어내지 않는다 ──")
    chk("연월 열이 있으면 처음~끝",
        window_of(["기준연월", "값"], [["2026-07", "2025-10"], ["1", "2"]]),
        ("2025-10", "2026-07"))
    chk("**연월 열이 없으면 None**",
        window_of(["터미널", "값"], [["SNCT", "HJIT"], ["1", "2"]]), None)

    print("── 인수시험: 봉인 파일은 열지 않는다 (§4) ──")
    chk("봉인 목록 2건", len(SEALED), 2)
    chk("probe_2026_raw 가 봉인이다", is_sealed("analysis/probe/probe_2026_raw.csv"), True)
    chk("_probe_dump 가 봉인이다", is_sealed("_probe_dump.txt"), True)
    chk("보통 파일은 봉인이 아니다", is_sealed("analysis/terminal_monthly.csv"), False)

    items = collect()
    sealed = [i for i in items if i["봉인"]]
    chk("카탈로그에 봉인이 실린다 (빼지 않는다)", len(sealed), 2)
    chk("**봉인은 행수를 안 읽는다**", [i["행"] for i in sealed], [None, None])
    chk("봉인도 크기는 적는다", all(i["바이트"] > 0 for i in sealed), True)

    print("── 인수시험: 실물 카탈로그 ──")
    live = [i for i in items if not i["봉인"]]
    chk("공개 파일이 여럿이다", len(live) > 10, True)
    chk("전부 행수를 읽었다", all(i["행"] is not None for i in live), True)
    chk("앵커 3건이 표시된다", sum(1 for i in items if i["앵커"]), 3)
    tm = next(i for i in live if i["경로"].endswith("terminal_monthly.csv"))
    chk("terminal_monthly 창이 잡힌다", tm["창"], ("2025-10", "2026-07"))
    chk("terminal_monthly 89행", tm["행"], 89)
    other = [c for c in tm["스키마"] if c["이름"] == "당월_천TEU"][0]
    chk("**빈칸이 있는 열은 빈칸 비율이 0이 아니다**", other["빈칸"] > 0, True)

    print("── 인수시험: 생성물 ──")
    text = build()
    chk("절 제목에 「## 1.」이 없다 (린터 오인 방지)",
        any(l.startswith("## 1.") or l.startswith("## 3.") for l in text.splitlines()), False)
    chk("봉인 절이 있다", "## 열지 않는 파일" in text, True)
    chk("**봉인 파일 경로가 지면에 있다**",
        all(s in text for s in SEALED), True)
    chk("스키마 표가 생성된다", 'class="data schema"' in text, True)
    chk("회사 상호가 없다 (§4.1-1)",
        any(w in text for w in ("선광", "한진", "동방", "대한통운")), False)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    os.chdir(ROOT)
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

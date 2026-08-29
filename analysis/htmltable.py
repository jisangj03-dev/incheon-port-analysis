# -*- coding: utf-8 -*-
"""생성된 표에 **이름과 머리 방향**을 붙인다. 사람이 표마다 손으로 안 붙이게.

왜 있는가
---------
2026-08-30에 접근성을 처음 실측했다. **이 축은 한 번도 본 적이 없었다.**
지면 전체에서 나온 것 셋 중 둘이 표에 있었다:

  · **`<caption>` 이 하나도 없다.** 화면 낭독기는 표에 들어가면서 「표, 7열 12행」이라고만
    말한다 — **어느 표인지 말하지 않는다.** 지면 하나에 표가 넷이면 넷 다 이름이 없다.
  · **`<th>` 에 `scope` 가 하나도 없다.** 열 머리인지 행 머리인지 표시가 없으면
    낭독기가 셀을 읽을 때 **어느 머리에 딸린 값인지** 못 붙여 준다.
    우리 표는 첫 열이 기준월·구역·연도인 **행 머리**라 이 손실이 특히 크다.

**생성기 셋이 표를 서른 개 만든다.** 표마다 손으로 붙이면 다음 표에서 빠뜨린다 —
그리고 빠뜨린 것은 **화면에서 안 보인다.** 인쇄 판형과 같은 종류의 결함이다(사고 68).
그래서 한 자리에서 후처리한다.

표 이름을 어디서 가져오는가
---------------------------
**지어내지 않는다.** 지면에는 이미 `<h2>표 1 — 최신월 2026-07, 공표자료의 계층 그대로</h2>`
같은 제목이 표 바로 앞에 있다. **그것이 그 표의 이름이다.** 앞쪽에서 가장 가까운
제목(`h2`·`h3`)이나 밴드 이름표를 찾아 쓴다.

**못 찾으면 안 붙이고 센다.** 그럴듯한 이름을 지어 넣으면 그것은 표기가 아니라 창작이다 —
이 저장소가 수치에 대해 지키는 규율을 표 이름에 대해서만 풀 이유가 없다.

`caption` 은 **눈에 안 보이게** 넣는다. 화면에는 이미 같은 문장이 제목으로 있어서
보이게 넣으면 같은 줄이 두 번 나온다. `.vh` 는 화면 밖으로 밀되 낭독기는 읽는 관용 수법이다 —
`display:none` 은 낭독기도 안 읽으므로 쓰면 안 된다.

닿지 않는 곳
------------
· **마크다운 표는 못 본다.** `data/`·`reports/`·`verify/`·`corrections/` 의 손 편집 표가
  그렇다. kramdown 이 그 표를 어떻게 내는지 **이쪽에서 확인할 수단이 없어**(로컬 Jekyll 없음)
  손대지 않았다. **확인 못 한 화면에 얹지 않는다**(사고 8·20).
· **표가 실제로 낭독되는지는 안 본다.** 속성이 붙었는지만 본다.
  **속성의 존재는 낭독의 확인이 아니다** — 낭독기로 들어 본 사람은 아직 없다.
"""

import re

TABLE = re.compile(r"<table\b[^>]*>", re.I)
TH = re.compile(r"<th\b([^>]*)>", re.I)
# 제목과 밴드 이름표 — 표 앞에서 이름을 찾을 때 본다.
HEADING = re.compile(r"<(h2|h3)\b[^>]*>(.*?)</\1>|<span class=\"k\"[^>]*>(.*?)</span>",
                     re.I | re.S)
TAGS = re.compile(r"<[^>]+>")


def _text(s: str) -> str:
    """태그를 걷고 공백을 하나로. `caption` 안에 태그를 넣지 않는다.

    **태그 자리에 공백을 넣지 않는다.** 제목 안 태그는 `<strong>` 같은 강조라
    낱말 가운데에 있다 — 공백으로 바꾸면 `하역능력과` 가 `하역능력 과` 로 갈라진다.
    줄바꿈 태그만 공백으로 바꾼다. 그것은 실제로 낱말 경계이기 때문이다.
    """
    s = re.sub(r"<br\s*/?>", " ", s, flags=re.I)
    s = TAGS.sub("", s)
    s = s.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", s).strip()


def name_before(html: str, pos: int):
    """`pos` 앞에서 가장 가까운 제목·이름표의 글자. 없으면 None."""
    last = None
    for m in HEADING.finditer(html, 0, pos):
        last = m
    if last is None:
        return None
    t = _text(last.group(2) or last.group(3) or "")
    return t or None


def add_scope(table: str) -> str:
    """`<thead>` 안은 열 머리, 그 밖은 행 머리. **이미 있으면 안 건드린다.**"""
    head_end = table.lower().find("</thead>")
    if head_end < 0:
        head_end = 0

    def one(m, scope):
        attrs = m.group(1)
        if re.search(r"\bscope\s*=", attrs, re.I):
            return m.group(0)
        return "<th%s scope=\"%s\">" % (attrs, scope)

    head = TH.sub(lambda m: one(m, "col"), table[:head_end])
    body = TH.sub(lambda m: one(m, "row"), table[head_end:])
    return head + body


def annotate(html: str):
    """표에 `scope` 와 `caption` 을 채운다. 반환 (새 html, 붙인 수, 이름 못 찾은 수)."""
    out = []
    i = 0
    named = unnamed = 0
    for m in TABLE.finditer(html):
        end = html.lower().find("</table>", m.end())
        if end < 0:
            continue
        end += len("</table>")
        out.append(html[i:m.start()])
        table = add_scope(html[m.start():end])
        if "<caption" not in table.lower():
            nm = name_before(html, m.start())
            if nm:
                table = table[:m.end() - m.start()] + \
                    "<caption class=\"vh\">%s</caption>" % nm + \
                    table[m.end() - m.start():]
                named += 1
            else:
                unnamed += 1
        out.append(table)
        i = end
    out.append(html[i:])
    return "".join(out), named, unnamed


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-50s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 표 이름과 머리 방향 ──")

    src = ('<h2>표 1 — 부두군 월별</h2>'
           '<div class="tsw"><table><thead><tr><th>기준월</th>'
           '<th class="num">신항</th></tr></thead>'
           '<tbody><tr><th>2026-07</th><td>184</td></tr></tbody></table></div>')
    got, named, unnamed = annotate(src)
    chk("이름을 앞선 제목에서 가져온다", '<caption class="vh">표 1 — 부두군 월별</caption>' in got, True)
    chk("이름 붙인 수", named, 1)
    chk("이름 못 찾은 수", unnamed, 0)
    chk("thead 의 th 는 열 머리", got.count('scope="col"'), 2)
    chk("tbody 의 th 는 행 머리", got.count('scope="row"'), 1)
    chk("caption 은 table 바로 뒤", '<table><caption' in got, True)

    # **이름을 지어내지 않는다.** 앞에 제목이 없으면 안 붙인다.
    got2, named2, unnamed2 = annotate('<table><tr><th>가</th></tr></table>')
    chk("제목이 없으면 이름을 안 붙인다", "<caption" in got2, False)
    chk("못 찾은 것을 센다", unnamed2, 1)

    # **이미 있는 것은 안 건드린다.** 두 번 돌려도 같아야 한다(멱등).
    twice, _, _ = annotate(got)
    chk("두 번 돌려도 같다 (멱등)", twice, got)
    chk("이미 있는 scope 를 덮지 않는다",
        annotate('<table><thead><tr><th scope="colgroup">가</th></tr></thead></table>')[0]
        .count('scope='), 1)

    # 밴드 이름표도 이름이 된다 — 첫 화면 구획에는 h2 대신 그것이 쓰인다.
    got3, n3, _ = annotate('<span class="k">연도별</span><table><tr><td>1</td></tr></table>')
    chk("밴드 이름표에서도 가져온다", '<caption class="vh">연도별</caption>' in got3, True)

    # 태그가 든 제목은 글자만 남긴다.
    got4, _, _ = annotate('<h2>표 3 — <strong>하역능력</strong>과 실적</h2><table><tr><td>1</td></tr></table>')
    chk("제목 안 태그를 걷는다", '<caption class="vh">표 3 — 하역능력과 실적</caption>' in got4, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(selftest() if "--selftest" in sys.argv else selftest())

# -*- coding: utf-8 -*-
"""프로브 — 「월별 항만운영통계」 게시판은 **어디까지 있는가.**

**질문.** #11 의 창이 10개월인 것은 **원천이 10개월이어서인가, 우리가 10개월만 읽어서인가.**

**답 (2026-09-11 실측).** **후자다.** 게시판 목록은 **23쪽**이고 마지막 쪽의 가장 이른 글은
**2006년 9월**분이다. `collect_terminal_monthly.py` 의 `list_posts()` 는 `pageindex` 를 안 붙여
**첫 쪽 10건만** 읽는다 — 그래서 CSV 가 2025-10~2026-07 열 달이 됐다.

**이것이 왜 프로브인가.** 값을 하나도 안 연다 — **쪽수와 글 제목만** 본다.
터미널별 수치는 손대지 않으므로 #11 의 선커밋 구간(2025-10~2026-07)에 영향이 없다.
창을 넓히려면 **편을 새로 열고 선커밋부터** 해야 한다(지침 §5).

**왜 남기나.** #11 이 「왜 10개월인가」를 결론 자리에서 답하는데, 그 답이 주장이 아니라
**확인 명령을 가진 관측**이어야 한다(지침 §8-3).

    python analysis/probe/probe_15_board_depth.py            # 실측
    python analysis/probe/probe_15_board_depth.py --selftest # 파서 인수시험(망 안 탄다)

닿지 않는 곳
------------
· **옛 글의 첨부에 터미널 표가 있는지는 안 본다.** 첨부를 열지 않는다 — 그건 값이다.
  **「글이 있다」와 「그 축이 있다」는 다르다**(사고 26). 창을 넓히는 편이 그것부터 확인한다.
· **제목 규칙은 수집기의 것을 그대로 쓴다.** 다른 제목으로 올라온 같은 통계가 있으면 안 잡힌다 —
  실제로 마지막 쪽에 「인천항 선박입항 및 물동량 처리 현황」이라는 다른 제목의 2006년 글이 있다.
· 게시판은 살아 있다. **이 수는 측정일의 관측이다.**
"""
from __future__ import annotations
import argparse
import html as htmllib
import os
import re
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LIST_URL = "https://incheon.mof.go.kr/ko/board.do?menuIdx=1700"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# 게시판 쪽 이동은 `fnPageMove(n)` 이 `#pageindex` 에 값을 넣고 폼을 낸다
# (`/ko/office/common/resources/js/wk_common.js`). GET 으로도 같은 목록이 온다.
END_RE = re.compile(r'fnPageMove\((\d+)\)[^>]*class="btn_end"')
LINK_RE = re.compile(
    r'<a[^>]+href="(board\.do\?[^"]*bbsIdx=\d+[^"]*)"[^>]*>(.*?)</a>', re.S
)
# **수집기와 같은 규칙을 쓴다** — 다른 규칙을 쓰면 다른 것을 세게 된다(사고 31).
YM_RE = re.compile(r"(\d{4})년\s*(\d{1,2})월")


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": LIST_URL})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def last_page(page_html: str) -> int | None:
    """목록 쪽수 — 「끝 페이지로」 단추가 드는 수."""
    m = END_RE.search(page_html)
    return int(m.group(1)) if m else None


def months_on(page_html: str) -> list[str]:
    """그 쪽의 「항만운영통계」 글에서 대상연월만. **수집기와 같은 규칙.**"""
    out = []
    for m in LINK_RE.finditer(page_html):
        title = htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        ym = YM_RE.search(title)
        if "항만운영통계" in title and ym:
            out.append("%s-%02d" % (ym.group(1), int(ym.group(2))))
    return out


def span_gaps(months):
    """구간 폭과 **글이 없는 달**. 반환 (폭, 빠진 달 목록).

    **[2026-09-13] 이 함수가 왜 생겼나.** #12 지면이 「게시판에는 220개월이 다 있고」로
    나갔는데 **220은 글이 있는 달의 수이고 구간 폭은 239개월**이다. 두 끝을 빼면 239 가
    나오므로 **읽는 사람이 220 과 맞출 수 없었다.** 그 셋(폭·글·빠진 달)을 **코드가 같이 낸다** —
    손으로 세면 또 하나가 빠진다(사고 117).
    """
    ms = sorted(months)
    y0, m0 = (int(x) for x in ms[0].split("-"))
    y1, m1 = (int(x) for x in ms[-1].split("-"))
    span = (y1 - y0) * 12 + (m1 - m0) + 1
    have, miss, y, m = set(ms), [], y0, m0
    while (y, m) <= (y1, m1):
        k = "%04d-%02d" % (y, m)
        if k not in have:
            miss.append(k)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return span, miss


def full() -> int:
    """목록 전 쪽을 읽어 **폭 · 글 수 · 빠진 달**을 낸다. 제목만 본다."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import collect_terminal_monthly as C
    posts = C.list_posts()
    ms = sorted(ym for ym, _ in posts)
    span, miss = span_gaps(ms)
    print("== 게시판 전 쪽 — 폭과 빠진 달 (제목만 본다) ==")
    print("  구간            %s ~ %s" % (ms[0], ms[-1]))
    print("  **구간 폭**       %d개월" % span)
    print("  **글이 있는 달**   %d개월  (구간 폭의 %.1f%%)" % (len(ms), len(ms) / span * 100))
    print("  **글이 없는 달**   %d개월" % len(miss))
    print("     %s" % " ".join(miss))
    print()
    print("  **셋을 같이 적는다** — 「%d개월이 다 있다」는 거짓이고," % span)
    print("  「%d개월」만 적으면 두 끝을 뺀 %d 과 안 맞는다." % (len(ms), span))
    return 0


def probe() -> int:
    first = get(LIST_URL)
    pages = last_page(first)
    head = months_on(first)
    print("== 「월별 항만운영통계」 게시판 깊이 ==")
    print("  목록 1쪽  · 항만운영통계 %d건 · %s ~ %s" % (len(head), head[-1], head[0]))
    if not pages:
        print("  **쪽수를 못 읽었다.** 목록 표시가 바뀌었다 — 단정하지 않는다.")
        return 1
    print("  목록 쪽수 · %d쪽" % pages)
    tail = months_on(get(LIST_URL + "&pageindex=%d" % pages))
    print("  목록 %d쪽 · 항만운영통계 %d건 · 가장 이른 달 %s" % (pages, len(tail), min(tail)))
    print()
    print("  **수집기는 첫 쪽만 읽는다** — `collect_terminal_monthly.py` `list_posts()` 가")
    print("  `pageindex` 를 안 붙인다. `analysis/terminal_monthly.csv` 의 %d개월이 그 결과다."
          % len(head))
    print("  **첨부에 터미널 표가 있는지는 이 프로브가 안 본다.** 글이 있는 것과 축이 있는 것은 다르다.")
    return 0


def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-46s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 쪽수 읽기 ──")
    end = ('<a href="#" title="끝 페이지로" onclick="fnPageMove(23);return false;" '
           'class="btn_end"><em class="IR">끝 페이지로</em></a>')
    chk("끝 페이지 수를 읽는다", last_page(end), 23)
    chk("없으면 None — 단정하지 않는다", last_page("<div></div>"), None)

    print("── 인수시험: 제목 규칙 ──")
    frag = (
        '<a href="board.do?menuIdx=1700&bbsIdx=1">2026년 7월 인천항 항만운영통계</a>'
        '<a href="board.do?menuIdx=1700&bbsIdx=2">2006년 9월 항만운영통계</a>'
        '<a href="board.do?menuIdx=1700&bbsIdx=3">인천항 선박입항 및 물동량 처리 현황 (2006년 8월)</a>'
        '<a href="board.do?menuIdx=1700&bbsIdx=4">항만운영통계 안내</a>'
    )
    got = months_on(frag)
    chk("항만운영통계 + 연월만 잡는다", got, ["2026-07", "2006-09"])
    chk("다른 제목은 안 잡는다 — 한계를 그대로 둔다", "2006-08" in got, False)

    print("── 인수시험: 폭·글 수·빠진 달 (망을 안 탄다) ──")
    span, miss = span_gaps(["2006-09", "2006-11", "2006-12"])
    chk("폭은 두 끝으로 센다", span, 4)
    chk("빠진 달을 든다", miss, ["2006-10"])
    span2, miss2 = span_gaps(["2024-01", "2024-02", "2024-03"])
    chk("빈 데 없으면 폭 = 글 수", (span2, miss2), (3, []))
    chk("폭은 글 수보다 작을 수 없다", span >= 3, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="게시판 깊이 프로브 — 값은 안 연다")
    ap.add_argument("--full", action="store_true", help="전 쪽을 읽어 폭·글 수·빠진 달")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else (full() if a.full else probe()))

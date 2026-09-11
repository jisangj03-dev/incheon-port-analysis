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

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="게시판 깊이 프로브 — 값은 안 연다")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else probe())

"""프로브 — 인천지방해양수산청 「월별 항만운영통계」에 어떤 축이 있는가.

**질문.** `/data/` 「확인 대기」에 올려 둔 이 소스에
**공/적(공컨·적컨) 구분과 수출입 방향 축이 있는가?**
있으면 기존 #01~#07 시리즈를 연장할 수 있고, 없으면 다른 축을 여는 소재다.

**답 (2026-08-28 실측).** **둘 다 없다.**
대신 **터미널 운영사 단위 월별 TEU**가 있다 — 그건 `/data/`가 미관측으로 적어 둔 축이다.

이 스크립트는 그 확인을 재현한다. 값을 산출하지 않는다 — **축의 존재만 본다.**
값을 쓰려면 편을 열고 선커밋부터 해야 한다(지침 §5).

    python analysis/probe/probe_08_mof_monthly.py            # 받아서 축을 훑는다
    python analysis/probe/probe_08_mof_monthly.py --keep     # 원본 hwpx 를 남긴다

**소스는 게시판이다.** 고정 API가 아니라 글마다 `file_idx`가 다르다.
그래서 목록을 먼저 긁어 대상 월의 첨부를 찾는다 — 그 경로까지가 재현 대상이다.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile

LIST_URL = "https://incheon.mof.go.kr/ko/board.do?menuIdx=1700"
BASE = "https://incheon.mof.go.kr"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# 이 프로브가 답하려는 것 — 축 키워드
AXIS_PROBE = [
    ("공컨", "공컨테이너 구분"),
    ("적컨", "적컨테이너 구분"),
    ("환적", "환적 구분"),
    ("수출", "수출 방향 축"),
    ("수입", "수입 방향 축"),
    ("TEU", "컨테이너 단위"),
    ("신항", "터미널 — 신항"),
    ("남항", "터미널 — 남항"),
    ("국제여객", "터미널 — 국제여객부두"),
    ("내항", "부두 — 내항"),
    ("북항", "부두 — 북항"),
    ("연안", "연안 구간"),
]


def get(url: str, referer: str | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if referer:
        req.add_header("Referer", referer)
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def find_latest(list_html: str):
    """목록에서 (제목, 글 URL, 첨부 file_idx) 를 최신순으로 뽑는다."""
    out = []
    for m in re.finditer(
        r'<a[^>]+href="(board\.do\?[^"]*bbsIdx=(\d+)[^"]*)"[^>]*>(.*?)</a>',
        list_html,
        re.S,
    ):
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
        if "항만운영통계" in title:
            out.append((title, BASE + "/ko/" + html.unescape(m.group(1)), m.group(2)))
    return out


def body_text(hwpx_path: str) -> str:
    """HWPX 는 XML 을 담은 ZIP 이다. 의존성 없이 본문을 뽑는다."""
    z = zipfile.ZipFile(hwpx_path)
    x = z.read("Contents/section0.xml").decode("utf-8", "replace")
    x = re.sub(r"<hp:tc\b", "\n<CELL<hp:tc", x)
    x = re.sub(r"<hp:tr\b", "\n<ROW<hp:tr", x)
    buf = []
    for m in re.finditer(r"(<CELL|<ROW|<hp:t>.*?</hp:t>)", x, re.S):
        s = m.group(0)
        if s == "<CELL":
            buf.append(" | ")
        elif s == "<ROW":
            buf.append("\n")
        else:
            buf.append(html.unescape(re.sub(r"<[^>]+>", "", s)))
    return re.sub(r"[ \t]+", " ", "".join(buf)).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="원본 hwpx 를 현재 폴더에 남긴다")
    a = ap.parse_args()

    print("== 프로브: 인천지방해양수산청 월별 항만운영통계 ==")
    print(f"  목록 {LIST_URL}")
    listing = get(LIST_URL).decode("utf-8", "replace")
    posts = find_latest(listing)
    if not posts:
        print("[중단] 목록에서 「항만운영통계」 글을 못 찾았다. 게시판 구조가 바뀌었을 수 있다.")
        return 2
    print(f"  글 {len(posts)}건 발견. 최신부터 3건:")
    for t, _u, _b in posts[:3]:
        print(f"    · {t}")

    title, url, _bbs = posts[0]
    art = get(url, referer=LIST_URL).decode("utf-8", "replace")
    fm = re.search(r'href="(/boardFileDown\.do\?file_idx=(\d+))"[^>]*>([^<]*\.hwpx)', art)
    if not fm:
        fm = re.search(r'href="(/boardFileDown\.do\?file_idx=(\d+))"', art)
        if not fm:
            print("[중단] 첨부 링크를 못 찾았다.")
            return 2
    dl = BASE + fm.group(1)
    print(f"\n  대상 «{title}»\n  첨부 {dl}")

    blob = get(dl, referer=url)
    sha = hashlib.sha256(blob).hexdigest().upper()
    print(f"  받음 {len(blob):,} B · SHA-256 {sha[:32]}")

    tmp = os.path.join(
        os.getcwd() if a.keep else tempfile.gettempdir(), "incheon_mof_monthly.hwpx"
    )
    with open(tmp, "wb") as f:
        f.write(blob)

    txt = body_text(tmp)
    print(f"  본문 {len(txt):,}자 추출\n")

    print("== 축이 있는가 ==")
    verdict = {}
    for key, label in AXIS_PROBE:
        n = txt.count(key)
        verdict[key] = n
        mark = "있음" if n else "**없음**"
        print(f"  {label:22s} {key:6s} {n:3d}회  {mark}")

    print("\n== 판정 ==")
    if verdict["공컨"] == 0 and verdict["적컨"] == 0:
        print("  공/적 구분 **없다** — 기존 #01~#07 공컨 시리즈를 이 소스로 연장할 수 없다.")
    else:
        print("  공/적 구분이 있다 — 시리즈 연장 가능성을 다시 본다.")
    if verdict["신항"] and verdict["남항"]:
        print("  터미널 축 **있다** — /data/ 가 미관측으로 적어 둔 축이다.")
    print("  ※ 수출/수입 낱말은 기관의 **인과 해설 문장**에 나온다. 축이 아니다.")
    print("     그 해설을 우리 결론 자리로 옮기지 않는다(지침 §3-5 데이터 인과 금지).")

    if not a.keep:
        try:
            os.remove(tmp)
        except OSError:
            pass
    else:
        print(f"\n  원본 남김: {tmp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

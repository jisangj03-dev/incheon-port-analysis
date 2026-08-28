"""프로브 — 국가물류통합정보센터(NLIC) 「항만별 물동량 통계」에 어떤 축이 있는가.

**질문.** `/data/` 「확인 대기」의 남은 1건이다.
인천항 축으로 무엇이 나오는가? 특히 **연안 구간 축이 있는가?**
(우리 API의 2026 상반기 `ocCt=2` 는 전 구간 0으로 관측됐고, 그 0이 실제인지 미집계인지 모른다.)

**답 (2026-08-28 실측).** 축이 있다. 그리고 **연안 값이 0이 아니다.**

    합계
    ├ 외항 ── 수출입 (소계 / 수입 / 수출)
    │      └ 환적   (소계 / 수입 / 수출)
    └ 내항 ── 연안   (소계 / 입항 / 출항)

**그러나 이것으로 우리 0 관측이 설명되지 않는다. 맞대면 안 된다.**

| | NLIC | 우리 #01~#07 |
|---|---|---|
| 단위 | **톤(R/T)** | **TEU · 박스 수** |
| 모집단 | **전체 화물** (벌크 포함) | **컨테이너만** |

**단위와 모집단이 둘 다 다르다.** 지침 §3-9(결합 게이트)가 맞대기 전에 정합 확인을 요구하고,
여기서는 정합이 **성립하지 않는다.** 그래서 이 프로브는 **값을 맞대지 않고 축의 존재만 본다.**

**다만 물음은 좁아졌다.** 연안 화물 자체는 톤 기준으로 대량 존재한다.
그러므로 우리 컨테이너 연안 0은 「연안 운항이 없어서」가 아니다.
남은 후보는 ① 연안 **컨테이너**가 실제로 거의 없다 ② 우리 소스의 `ocCt=2` 컨테이너 집계가 비어 있다.
**둘 중 어느 쪽인지는 이 프로브가 답하지 않는다.**
(인천지방해양수산청 월별 통계 각주가 「연안화물선 컨테이너는 그 외 부두로 분류」라고 밝힌 것이
①쪽 방향이지만, **분류 규칙의 진술이지 값의 확인이 아니다.**)

    python analysis/probe/probe_09_nlic_harbor.py
    python analysis/probe/probe_09_nlic_harbor.py --year 2026 --month 06
"""
from __future__ import annotations
import argparse
import html as htmllib
import re
import sys
import urllib.parse
import urllib.request

URL = "https://www.nlic.go.kr/nlic/seaHarborGtqy.action"
HARBOR_INCHEON = "030"  # 조회 폼의 S_HARBOR_CODE 값. 페이지에서 확인했다.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
# 이 프로브가 확인하려는 축 이름
AXES = ["외항", "내항", "수출입", "환적", "연안", "수입", "수출", "입항", "출항"]


def fetch(year: str, month: str, harbor: str) -> str:
    data = urllib.parse.urlencode(
        {"S_COMMAND": "LIST", "S_HARBOR_CODE": harbor, "S_YEAR": year, "S_MONTH": month}
    ).encode()
    req = urllib.request.Request(URL, data=data, headers={"User-Agent": UA, "Referer": URL})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def to_lines(page: str) -> list[str]:
    body = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", page)
    txt = htmllib.unescape(re.sub(r"<[^>]+>", "\n", body))
    return [l.strip() for l in txt.split("\n") if l.strip()]


def parse_grid(lines: list[str]):
    """단위 줄 다음의 첫 블록을 (축이름, 값 6개) 로 읽는다.

    표가 계층 표라 셀이 1개(축 이름) 또는 2개(축+소계) 뒤에 숫자 6개가 붙는다.
    **숫자 6개가 연달아 나오는 지점**을 기준으로 끊는다 — 열 이름에 의존하지 않는다.
    """
    try:
        i = next(i for i, l in enumerate(lines) if l.startswith("단위"))
    except StopIteration:
        return None, []
    unit = lines[i]
    seg = lines[i : i + 120]
    num = re.compile(r"^-?[\d,]+(\.\d+)?$")
    rows, label = [], []
    k = 0
    while k < len(seg):
        if num.match(seg[k]) and all(num.match(x) for x in seg[k : k + 6]):
            rows.append((" ".join(label[-2:]) if label else "?", seg[k : k + 6]))
            label = []
            k += 6
        else:
            label.append(seg[k])
            k += 1
    return unit, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default="2026")
    ap.add_argument("--month", default="06")
    a = ap.parse_args()

    print("== 프로브: NLIC 항만별 물동량 통계 (인천) ==")
    print(f"  {URL}  ·  S_HARBOR_CODE={HARBOR_INCHEON} {a.year}-{a.month}")
    page = fetch(a.year, a.month, HARBOR_INCHEON)
    lines = to_lines(page)

    # 메타 정보
    for key in ["자료명", "출처", "업데이트 주기", "주요 제공정보"]:
        for n, l in enumerate(lines):
            if l == key and n + 1 < len(lines):
                print(f"  {key:10s} {lines[n+1][:80]}")
                break

    unit, rows = parse_grid(lines)
    print(f"\n  {unit}")
    if not rows:
        print("[중단] 결과 표를 못 읽었다. 화면 구조가 바뀌었을 수 있다.")
        return 2

    print(f"\n== 축 구조 (앞 {min(len(rows), 12)}행) ==")
    print(f"  {'축':<14}{'당월':>14}{'누계':>14}{'전년당월':>14}{'전년누계':>14}")
    for label, vals in rows[:12]:
        print(f"  {label:<14}{vals[0]:>14}{vals[1]:>14}{vals[2]:>14}{vals[3]:>14}")

    print("\n== 축이 있는가 ==")
    joined = "\n".join(lines)
    for ax in AXES:
        print(f"  {ax:6s} {'있음' if ax in joined else '**없음**'}")

    coastal = [v for lbl, v in rows if "연안" in lbl]
    print("\n== 판정 ==")
    if coastal:
        print(f"  연안 축 **있고 값이 0이 아니다** — 당월 {coastal[0][0]} · 누계 {coastal[0][1]}")
    print("  **단위가 톤(R/T)이고 모집단이 전체 화물이다.**")
    print("  우리 #01~#07 은 TEU·컨테이너다. **단위도 모집단도 달라 맞대면 안 된다**(지침 §3-9).")
    print("  이 프로브는 축의 존재만 본다. 값 비교는 하지 않는다.")
    print("\n  좁혀진 것: 연안 화물 자체는 있다 → 우리 컨테이너 연안 0 은")
    print("  「연안 운항이 없어서」가 아니다. 남은 후보 둘은 파일 머리 주석에 있다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

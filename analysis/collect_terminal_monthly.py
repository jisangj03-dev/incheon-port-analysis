"""인천항 터미널별 월별 컨테이너 처리실적을 수집한다.

**출처.** 인천지방해양수산청 「월별 항만운영통계」 게시판(`incheon.mof.go.kr`, `menuIdx=1700`).
매월 HWPX 한 건이 올라오고, 그 안에 **터미널 운영사 단위 표**가 들어 있다.
축의 실재는 `analysis/probe/probe_08_mof_monthly.py` 가 먼저 확인했다.

**왜 만드는가.** 이 축은 **기계판독 형태로 아무도 공개하지 않는다.**
게시판에 HWPX 로만 있고, 월마다 파일이 따로다. 시계열로 보려면 사람이 10개 파일을 열어야 한다.
이 스크립트가 그것을 CSV 한 장으로 만든다. **그 자체가 우리가 내놓는 것이다.**

**터미널을 회사명으로 부르지 않는다.** 공표자료가 쓰는 코드(SNCT·HJIT·E1CT·ICT)를 그대로 쓴다.
정부가 코드로 공표하므로 우리도 코드로 싣는다. 넷을 **같은 규칙으로 동등하게** 다룬다.

**단위는 천TEU다.** 공표자료가 천TEU 로 반올림해 낸다 — 우리가 반올림하는 게 아니다.
그래서 **이 데이터로 미세한 차이를 논할 수 없다.** 그 한계를 CSV 주석과 사이트에 같이 적는다.

    python analysis/collect_terminal_monthly.py            # 전체 수집 -> CSV
    python analysis/collect_terminal_monthly.py --limit 3  # 최근 3개월만
    python analysis/collect_terminal_monthly.py --selftest # 파서 인수시험
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import html as htmllib
import io
import os
import re
import sys
import urllib.request
import zipfile

# 콘솔이 cp949 라 「—」 같은 글자에서 죽는다. 다른 스크립트는 이미 이걸 하고 있었고
# 이 파일만 빠져 있었다 — 인수시험이 그것을 드러냈다(2026-08-29).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LIST_URL = "https://incheon.mof.go.kr/ko/board.do?menuIdx=1700"
BASE = "https://incheon.mof.go.kr"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
OUT_CSV = os.path.join("analysis", "terminal_monthly.csv")

# 공표자료가 쓰는 표기 -> 우리가 싣는 코드. **회사명을 쓰지 않는다.**
#
# 부두군(신항·남항)은 **우리가 지어낸 분류가 아니다.** 공표자료의 컨테이너 표가
# 「신항 | 소 계」·「남항 | 소 계」 행을 직접 들고 그 아래에 터미널을 놓는다.
# 2026-08-29 원문 실측으로 확인했다 — `analysis/probe/probe_11_berth_group.py`.
# (확인 전에는 이 매핑의 출처가 코드 어디에도 안 적혀 있었다. 맞는 값이어도
#  출처가 안 적힌 값은 §3-6상 `미확인` 이다. 그래서 적는다.)
TERMINALS = {
    "SNCT": ("SNCT", "신항"),
    "HJIT": ("HJIT", "신항"),
    "E1CT": ("E1CT", "남항"),
    "ICT": ("ICT", "남항"),
    "국제여객부두": ("IPT", "국제여객부두"),
}

# 컨테이너 표의 계층. 공표자료가 이 순서로 낸다.
#   컨테이너 합계 → 신항 소계 → SNCT · HJIT → 남항 소계 → E1CT · ICT
#                → 국제여객부두 → 그 외
GROUP_NAMES = ("신항", "남항")


def get(url: str, referer: str | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if referer:
        req.add_header("Referer", referer)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def list_posts():
    """게시판에서 (대상연월, 글 URL) 목록을 최신순으로."""
    page = get(LIST_URL).decode("utf-8", "replace")
    out = []
    for m in re.finditer(
        r'<a[^>]+href="(board\.do\?[^"]*bbsIdx=\d+[^"]*)"[^>]*>(.*?)</a>', page, re.S
    ):
        title = htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        ym = re.search(r"(\d{4})년\s*(\d{1,2})월", title)
        if "항만운영통계" in title and ym:
            out.append(
                (f"{ym.group(1)}-{int(ym.group(2)):02d}", BASE + "/ko/" + htmllib.unescape(m.group(1)))
            )
    return out


def attachment(post_url: str) -> str | None:
    art = get(post_url, referer=LIST_URL).decode("utf-8", "replace")
    m = re.search(r'href="(/boardFileDown\.do\?file_idx=\d+)"[^>]*>[^<]*\.hwpx', art)
    if not m:
        m = re.search(r'href="(/boardFileDown\.do\?file_idx=\d+)"', art)
    return BASE + m.group(1) if m else None


def hwpx_rows(blob: bytes) -> list[list[str]]:
    """HWPX 본문을 행 단위 셀 목록으로. 표가 XML 이라 의존성 없이 읽는다."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    x = z.read("Contents/section0.xml").decode("utf-8", "replace")
    x = re.sub(r"<hp:tc\b", "\x01<hp:tc", x)
    x = re.sub(r"<hp:tr\b", "\x02<hp:tr", x)
    buf = []
    for m in re.finditer(r"(\x01|\x02|<hp:t>.*?</hp:t>)", x, re.S):
        s = m.group(0)
        if s == "\x01":
            buf.append("\x01")
        elif s == "\x02":
            buf.append("\x02")
        else:
            buf.append(htmllib.unescape(re.sub(r"<[^>]+>", "", s)))
    text = "".join(buf)
    rows = []
    for raw in text.split("\x02"):
        cells = [c.strip() for c in raw.split("\x01")]
        cells = [re.sub(r"\s+", " ", c) for c in cells if c.strip()]
        if cells:
            rows.append(cells)
    return rows


def num(s: str):
    """공표자료는 감소를 '△' 로 쓴다. '-' 는 값 없음이다."""
    s = (s or "").strip().replace(",", "").replace(" ", "")
    if s in ("", "-", "–", "—"):
        return None
    neg = s.startswith("△") or s.startswith("▲")
    s = s.lstrip("△▲")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def parse_terminals(rows: list[list[str]]) -> list[dict]:
    """터미널 행을 뽑는다. 셀 배열이 아니라 **첫 셀의 이름**으로 찾는다.

    표 구조가 달마다 조금씩 흔들려도(소계 셀 유무 등) 이름 기준이면 버틴다.
    숫자 열은 뒤에서부터 센다 — 앞쪽 라벨 셀 개수가 행마다 다르기 때문이다.
    """
    out = []
    for cells in rows:
        name = cells[0].replace(" ", "")
        if name not in TERMINALS:
            continue
        nums = [num(c) for c in cells[1:]]
        nums = [n for n in nums if n is not None]
        code, group = TERMINALS[name]

        # 표 모양이 두 가지다. **1월호는 누계 열이 없다.**
        #   평월 (7열): 전년연간 · 전년당월 · 전년누계 · 당월 · 누계 · 증감(당월) · 증감(누계)
        #   1월  (4열): 전년연간 · 전년당월 · 당월 · 증감(당월)
        # 1월은 누계가 당월과 같아서 공표자료가 열을 아예 뺀다 —
        # 본문에도 「누계 동일」이라고 적혀 있다. 추정이 아니라 원문의 진술이다.
        # **이걸 처리 안 하면 1월이 시계열에서 조용히 빠진다.** 실제로 한 번 빠졌다.
        if len(nums) >= 7:
            rec = {
                "전년연간_천TEU": nums[-7],
                "전년당월_천TEU": nums[-6],
                "전년누계_천TEU": nums[-5],
                "당월_천TEU": nums[-4],
                "누계_천TEU": nums[-3],
                "전년대비_당월_%": nums[-2],
                "전년대비_누계_%": nums[-1],
                "표모양": "평월",
            }
        elif len(nums) == 4:
            rec = {
                "전년연간_천TEU": nums[0],
                "전년당월_천TEU": nums[1],
                "전년누계_천TEU": nums[1],   # 1월이므로 누계 = 당월
                "당월_천TEU": nums[2],
                "누계_천TEU": nums[2],
                "전년대비_당월_%": nums[3],
                "전년대비_누계_%": nums[3],
                "표모양": "1월(누계열 없음)",
            }
        else:
            continue
        rec["터미널"] = code
        rec["부두군"] = group
        rec["계층"] = "터미널"
        out.append(rec)
    return out


def container_block(rows: list[list[str]]) -> list[list[str]]:
    """컨테이너 표의 행만 잘라 낸다. **여기가 이 파일에서 제일 위험한 곳이다.**

    같은 표 안에 벌크 구획이 이어지고, 거기에도 **「남 항」이 또 나온다** —
    다만 단위가 **천톤**이다(2026-07 원문: `남 항 | 3,480 | 291 | …`).
    이름만 보고 줍는 순간 **천TEU 표에 천톤 값이 섞인다.** 지침 §3-9 결합 게이트가
    정면으로 막는 사고이고, 단위 환산으로 덮을 수 있는 종류도 아니다.

    그래서 이름이 아니라 **구획**으로 자른다 — 「컨테이너 … 합계」에서 열고
    「벌크」에서 닫는다. 닫는 표지를 못 찾으면 **열지 않는다**(빈 목록을 낸다).
    추정으로 여는 것보다 아무것도 안 내는 쪽이 낫다.
    """
    start = end = None
    for i, cells in enumerate(rows):
        if not cells:
            continue
        head = re.sub(r"\s+", "", cells[0])
        if start is None and "컨테이너" in head and "합계" in head:
            start = i
        elif start is not None and "벌크" in head:
            end = i
            break
    if start is None or end is None:
        return []
    return rows[start:end]


def parse_groups(rows: list[list[str]]) -> list[dict]:
    """컨테이너 표의 **합계 · 부두군 소계 · 그 외** 행을 읽는다.

    터미널 행은 `parse_terminals()` 가 이미 읽는다. 여기서 읽는 것은
    **공표자료가 스스로 낸 집계**다 — 우리가 더한 값이 아니다. 그 구분이 이 함수의 전부다.

    값 자리를 **위치로** 센다(터미널 행처럼 뒤에서 세지 않는다). 「그 외」행이
    대부분 `-` 라서 뒤에서 세면 자리가 밀리기 때문이다 —
    실제 2026-07 「그 외」는 `- - - - 1 - -` 이고, **누계에만 1이 있다.**
    """
    out = []
    for cells in container_block(rows):
        if not cells:
            continue
        head = re.sub(r"\s+", "", cells[0])

        if "컨테이너" in head and "합계" in head:
            level, name, group, vals = "합계", "컨테이너 합계", "", cells[1:]
        elif head in GROUP_NAMES and len(cells) > 1 and "소계" in re.sub(r"\s+", "", cells[1]):
            level, name, group, vals = "부두군", head, head, cells[2:]
        elif head == "그외":
            level, name, group, vals = "그 외", "그 외", "", cells[1:]
        else:
            continue

        v = [num(c) for c in vals]
        if len(v) >= 7:
            rec = {
                "전년연간_천TEU": v[0], "전년당월_천TEU": v[1], "전년누계_천TEU": v[2],
                "당월_천TEU": v[3], "누계_천TEU": v[4],
                "전년대비_당월_%": v[5], "전년대비_누계_%": v[6], "표모양": "평월",
            }
        elif len(v) == 4:
            rec = {
                "전년연간_천TEU": v[0], "전년당월_천TEU": v[1], "전년누계_천TEU": v[1],
                "당월_천TEU": v[2], "누계_천TEU": v[2],
                "전년대비_당월_%": v[3], "전년대비_누계_%": v[3],
                "표모양": "1월(누계열 없음)",
            }
        else:
            continue
        rec["터미널"] = name
        rec["부두군"] = group
        rec["계층"] = level
        out.append(rec)
    return out


def crosscheck(terms: list[dict], groups: list[dict]) -> str:
    """공표 합계 ↔ 우리가 읽은 부분들. **공표자료가 스스로 낸 검산식이다.**

    `합계 = 신항 소계 + 남항 소계 + 국제여객부두 + 그 외` 가 원문 안에서 성립한다.
    그러니 우리가 읽은 값으로 그 식을 다시 세워 보면 **파싱이 맞았는지 원문이 답해 준다.**
    지침 §3-9-2 는 항등식을 증거로 쓰지 말라 하는데, 이건 **정의상 참인 항등식이 아니라
    서로 다른 셀에서 읽은 값들의 대조**다 — 표 구조가 밀리면 즉시 깨진다.

    맞추지 못하면 **틀렸다고 적는다.** 조용히 통과시키면 그때부터 부재가 통과로 읽힌다(사고 26).

    **어긋남을 두 종류로 가른다.** 값이 전부 천TEU 로 **반올림돼 공표되므로**,
    부분을 더한 값과 공표 합계는 **반올림만으로도 ±1 까지 벌어진다.** 그것을 「이상」이라 부르면
    이 검산은 매달 울리고 곧 무시당한다(§3-5 — 오탐을 내는 검사는 무시당한다).
    2 이상 벌어지면 그건 반올림으로 설명이 안 되고 **표 구조가 밀린 것**이다.
    """
    G = {g["터미널"]: g for g in groups}
    T = {t["터미널"]: t for t in terms}
    if "컨테이너 합계" not in G:
        return "[검산 불가 — 공표 합계 행을 못 읽었다]"
    msgs = []
    for key, label in (("당월_천TEU", "당월"), ("누계_천TEU", "누계")):
        total = G["컨테이너 합계"].get(key)
        parts = [G.get(n, {}).get(key) for n in GROUP_NAMES]
        parts.append(T.get("IPT", {}).get(key))
        parts.append(G.get("그 외", {}).get(key))
        if total is None or any(p is None for p in parts[:3]):
            msgs.append(f"{label}=자리없음")
            continue
        s = sum(p for p in parts if p is not None)
        d = s - total
        if abs(d) < 1e-9:
            msgs.append(f"{label}일치")
        elif abs(d) <= 1 + 1e-9:
            msgs.append(f"{label}반올림({d:+g})")
        else:
            msgs.append(f"{label}**이상**({s:g}≠{total:g})")
    return "검산 " + "·".join(msgs)


def rounding_report(records: list[dict]) -> tuple[int, int, float]:
    """반올림 어긋남이 **몇 달에 실제로 일어났는가.** 지면이 이 수를 들어야 한다.

    「반올림 때문에 안 맞을 수 있다」는 흔한 상투구이고, 독자는 그것을 면피로 읽는다.
    **「10개월 중 몇 달에서 실제로 어긋났고 최대 몇이었다」는 관측이다.** 그것만 싣는다.
    """
    by_ym = {}
    for r in records:
        by_ym.setdefault(r["기준연월"], []).append(r)
    months = hit = 0
    worst = 0.0
    for ym, rs in by_ym.items():
        G = {r["터미널"]: r for r in rs if r["계층"] in ("합계", "부두군", "그 외")}
        T = {r["터미널"]: r for r in rs if r["계층"] == "터미널"}
        if "컨테이너 합계" not in G:
            continue
        for key in ("당월_천TEU", "누계_천TEU"):
            total = G["컨테이너 합계"].get(key)
            parts = [G.get(n, {}).get(key) for n in GROUP_NAMES]
            parts += [T.get("IPT", {}).get(key), G.get("그 외", {}).get(key)]
            if total is None or any(p is None for p in parts[:3]):
                continue
            months += 1
            d = abs(sum(p for p in parts if p is not None) - total)
            if d > 1e-9:
                hit += 1
            worst = max(worst, d)
    return months, hit, worst


def selftest() -> int:
    print("── 인수시험: 터미널 표 파서 ──")
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f"  {'OK  ' if good else 'FAIL'} {label}")
        if not good:
            print(f"       기대={want!r}\n       실제={got!r}")

    chk("△ 는 음수", num("△12.0"), -12.0)
    chk("쉼표 제거", num("1,081"), 1081.0)
    chk("'-' 는 값 없음", num("-"), None)
    chk("빈칸은 값 없음", num("  "), None)
    chk("평범한 수", num("587"), 587.0)

    # 실제 공표 표에서 그대로 옮긴 행 (2026-07분)
    rows = [
        ["구분", "ˊ25년(연간)", "ˊ25년 7월", "ˊ26년 7월", "전년 동기대비증감률"],
        ["SNCT", "1,081", "88", "632", "78", "587", "△12.0", "△7.1"],
        ["HJIT", "1,159", "94", "660", "107", "751", "13.4", "13.8"],
        ["국제여객부두", "454", "41", "258", "32", "220", "△21.9", "△14.7"],
        ["그 외", "-", "-", "-", "-", "1", "-", "-"],
        ["내 항", "12,922", "1,179", "7,885", "1,151", "7,696", "△2.4", "△2.4"],
    ]
    got = parse_terminals(rows)
    chk("터미널 행만 골라낸다 (벌크·기타 제외)", len(got), 3)
    chk("SNCT 당월", got[0]["당월_천TEU"], 78.0)
    chk("SNCT 누계", got[0]["누계_천TEU"], 587.0)
    chk("SNCT 전년당월", got[0]["전년당월_천TEU"], 88.0)
    chk("SNCT 증감(당월) 음수", got[0]["전년대비_당월_%"], -12.0)
    chk("국제여객부두 -> IPT 코드", got[2]["터미널"], "IPT")
    chk("HJIT 부두군", got[1]["부두군"], "신항")
    chk("평월 표모양", got[0]["표모양"], "평월")

    # 회귀: 1월호는 누계 열이 없다. 처리 안 하면 1월이 시계열에서 조용히 빠진다.
    jan = [["SNCT", "1,079", "100", "95", "△5.3"],
           ["HJIT", "1,159", "99", "105", "6.3"]]
    gj = parse_terminals(jan)
    chk("1월호도 읽는다 (누계 열 없음)", len(gj), 2)
    chk("1월 당월", gj[0]["당월_천TEU"], 95.0)
    chk("1월 누계 = 당월", gj[0]["누계_천TEU"], 95.0)
    chk("1월 전년당월", gj[0]["전년당월_천TEU"], 100.0)
    chk("1월 표모양 표시", gj[0]["표모양"], "1월(누계열 없음)")

    # ── 계층 파서 ────────────────────────────────────────────────────────
    # 2026-07 원문 표#4 를 그대로 옮긴 것. **벌크 구획까지 같이 넣는다** —
    # 그 안에 「남 항」이 천톤으로 또 있고, 그것이 이 파서의 유일한 치명 오류원이다.
    print("── 인수시험: 계층 파서 (합계 · 소계 · 그 외) ──")
    full = [
        ["구분", "ˊ25년 (연간)", "ˊ 25년 7월", "ˊ 26년 7월", "전년 동기대비 증감률"],
        ["당월", "누계", "당월", "누계", "당월", "누계"],
        ["인천항 전체합계 * (천톤)", "143,820", "12,030", "83,576", "11,856", "81,022", "△1.4", "△3.1"],
        ["컨테이너 ** (천TEU) 합계", "3,446", "280", "1,967", "282", "1,995", "0.9", "1.4"],
        ["신항", "소 계", "2,240", "182", "1,292", "184", "1,338", "1.1", "3.6"],
        ["SNCT", "1,081", "88", "632", "78", "587", "△12.0", "△7.1"],
        ["HJIT", "1,159", "94", "660", "107", "751", "13.4", "13.8"],
        ["남항", "소 계", "752", "57", "417", "66", "436", "16.7", "4.4"],
        ["E1CT", "275", "21", "146", "23", "170", "12.0", "16.5"],
        ["ICT", "477", "36", "272", "43", "266", "19.3", "△2.1"],
        ["국제여객부두", "454", "41", "258", "32", "220", "△21.9", "△14.7"],
        ["그  외", "-", "-", "-", "-", "1", "-", "-"],
        ["벌크 *** (천톤) 합계", "90,194", "7,636", "52,900", "7,386", "50,183", "△3.3", "△5.1"],
        ["내  항", "12,922", "1,179", "7,885", "1,151", "7,696", "△2.4", "△2.4"],
        ["남  항", "3,480", "291", "2,045", "354", "2,475", "21.5", "21.0"],
        ["북  항", "5,642", "430", "3,165", "471", "3,091", "9.7", "△2.3"],
    ]
    g = {r["터미널"]: r for r in parse_groups(full)}
    chk("합계 · 소계2 · 그 외 = 4행", len(g), 4)
    chk("공표 합계 당월 282", g["컨테이너 합계"]["당월_천TEU"], 282.0)
    chk("공표 합계 누계 1,995", g["컨테이너 합계"]["누계_천TEU"], 1995.0)
    chk("신항 소계 당월 184", g["신항"]["당월_천TEU"], 184.0)
    chk("남항 소계 당월 66", g["남항"]["당월_천TEU"], 66.0)
    chk("남항 소계는 컨테이너 값이다 (벌크 354 가 아니다)",
        g["남항"]["당월_천TEU"] != 354.0, True)
    chk("그 외 — 당월은 값 없음", g["그 외"]["당월_천TEU"], None)
    chk("그 외 — 누계에만 1 (위치로 세야 잡힌다)", g["그 외"]["누계_천TEU"], 1.0)
    chk("소계에 계층 표시", g["신항"]["계층"], "부두군")

    # **이 셋이 §3-9 결합 게이트를 지키는 자리다.**
    blk = container_block(full)
    chk("구획이 컨테이너 합계에서 열린다", blk[0][0].startswith("컨테이너"), True)
    chk("구획이 벌크 앞에서 닫힌다", any("벌크" in r[0] for r in blk), False)
    chk("벌크의 내항·북항이 안 들어온다",
        any(re.sub(r"\s+", "", r[0]) in ("내항", "북항") for r in blk), False)
    chk("닫는 표지가 없으면 아예 안 연다",
        container_block([["컨테이너 (천TEU) 합계", "1"], ["신항", "소 계", "2"]]), [])

    # 검산 — 공표 합계가 부두군 소계의 합과 맞는가. 맞아야 우리가 옳게 읽은 것이다.
    parts = g["신항"]["당월_천TEU"] + g["남항"]["당월_천TEU"]
    ipt = [r for r in parse_terminals(full) if r["터미널"] == "IPT"][0]["당월_천TEU"]
    chk("검산: 신항+남항+IPT = 공표 합계 (당월)",
        parts + ipt, g["컨테이너 합계"]["당월_천TEU"])
    cum = (g["신항"]["누계_천TEU"] + g["남항"]["누계_천TEU"]
           + [r for r in parse_terminals(full) if r["터미널"] == "IPT"][0]["누계_천TEU"]
           + g["그 외"]["누계_천TEU"])
    chk("검산: 소계들+IPT+그외 = 공표 합계 (누계)",
        cum, g["컨테이너 합계"]["누계_천TEU"])

    # **반올림 어긋남 — 지면이 이걸 말해야 한다.**
    t = {r["터미널"]: r for r in parse_terminals(full)}
    naive = sum(t[k]["당월_천TEU"] for k in ("SNCT", "HJIT", "E1CT", "ICT", "IPT"))
    chk("다섯 곳을 더하면 283 (공표 합계 282 와 1 다르다)", naive, 283.0)
    chk("어긋남의 자리는 신항 (78+107=185 ≠ 소계 184)",
        t["SNCT"]["당월_천TEU"] + t["HJIT"]["당월_천TEU"] - g["신항"]["당월_천TEU"], 1.0)

    print("통과" if ok else "실패")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="최근 N개월만")
    ap.add_argument("--out", default=OUT_CSV)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root)

    print("== 인천항 터미널별 월별 컨테이너 처리실적 수집 ==")
    posts = list_posts()
    if a.limit:
        posts = posts[: a.limit]
    print(f"  대상 {len(posts)}개월: {posts[-1][0]} ~ {posts[0][0]}\n")

    records, sources = [], []
    for ym, url in posts:
        att = attachment(url)
        if not att:
            print(f"  [건너뜀] {ym} 첨부 없음")
            continue
        blob = get(att, referer=url)
        sha = hashlib.sha256(blob).hexdigest().upper()
        try:
            rows = hwpx_rows(blob)
        except (zipfile.BadZipFile, KeyError) as e:
            print(f"  [건너뜀] {ym} HWPX 아님 또는 구조 다름 ({e})")
            continue
        found = parse_terminals(rows)
        if not found:
            print(f"  [경고] {ym} 터미널 행을 못 찾았다 — 표 구조가 다를 수 있다")
            continue
        groups = parse_groups(rows)
        for r in found + groups:
            r["기준연월"] = ym
            records.append(r)
        sources.append((ym, att, len(blob), sha[:16]))

        # 검산을 **수집 시점에** 한다. 공표자료가 자기 합계를 같이 내므로
        # 우리가 읽은 부분들이 그 합계와 맞는지 그 자리에서 확인할 수 있다.
        # 안 맞으면 표 구조가 달라진 것이고, **조용히 지나가면 안 된다.**
        note = crosscheck(found, groups)
        print(f"  {ym}  터미널 {len(found)}건 · 집계 {len(groups)}건"
              f"  ({len(blob):,} B  {sha[:12]})  {note}")

    if not records:
        print("\n[중단] 수집된 행이 없다.")
        return 2

    cols = ["기준연월", "계층", "터미널", "부두군", "당월_천TEU", "누계_천TEU",
            "전년당월_천TEU", "전년누계_천TEU", "전년연간_천TEU",
            "전년대비_당월_%", "전년대비_누계_%", "표모양"]
    # 공표자료가 내는 순서 그대로 정렬한다 — 합계 → 신항 소계 → 그 아래 터미널 → …
    # 알파벳순으로 흩뜨리면 계층이 CSV 에서 사라진다.
    ORDER = {"컨테이너 합계": 0, "신항": 1, "SNCT": 2, "HJIT": 3,
             "남항": 4, "E1CT": 5, "ICT": 6, "IPT": 7, "그 외": 8}
    records.sort(key=lambda r: (r["기준연월"], ORDER.get(r["터미널"], 99), r["터미널"]))
    with io.open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            w.writerow({c: r.get(c, "") for c in cols})

    print(f"\n  -> {a.out}  {len(records)}행")

    n, hit, worst = rounding_report(records)
    print(f"\n== 반올림 어긋남 실측 ==")
    print(f"  검산한 자리 {n}곳 중 **{hit}곳**에서 부분합 ≠ 공표 합계. 최대 어긋남 {worst:g} 천TEU.")
    print( "  → 우리가 틀린 게 아니라 **공표값이 이미 반올림돼 있어서** 생긴다.")
    print( "     그래서 이 데이터에서 **한 자리 차이를 근거로 무엇도 주장할 수 없다.**")
    print("\n== 이 데이터의 한계 — 같이 실어야 한다 ==")
    print("  · 단위가 **천TEU**다. 공표자료가 반올림해 낸다 — 우리가 반올림한 게 아니다.")
    print("    그래서 **미세한 차이를 논할 수 없다.** 한 자리 차이는 반올림일 수 있다.")
    print("  · 공/적 구분과 수출입 방향 축이 **없다.** 이 소스에 그 축이 없다.")
    print("  · 「그 외」 항목이 있고 연안화물선 컨테이너가 거기로 분류된다(공표자료 각주).")

    idx = os.path.join("analysis", "terminal_monthly_sources.csv")
    with io.open(idx, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["기준연월", "첨부URL", "바이트", "SHA256_앞16"])
        for row in sorted(sources):
            w.writerow(row)
    print(f"  -> {idx}  (원본 {len(sources)}건의 주소와 해시)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

LIST_URL = "https://incheon.mof.go.kr/ko/board.do?menuIdx=1700"
BASE = "https://incheon.mof.go.kr"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)
OUT_CSV = os.path.join("analysis", "terminal_monthly.csv")

# 공표자료가 쓰는 표기 -> 우리가 싣는 코드. **회사명을 쓰지 않는다.**
TERMINALS = {
    "SNCT": ("SNCT", "신항"),
    "HJIT": ("HJIT", "신항"),
    "E1CT": ("E1CT", "남항"),
    "ICT": ("ICT", "남항"),
    "국제여객부두": ("IPT", "국제여객부두"),
}


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
        out.append(rec)
    return out


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
        for r in found:
            r["기준연월"] = ym
            records.append(r)
        sources.append((ym, att, len(blob), sha[:16]))
        print(f"  {ym}  터미널 {len(found)}건  ({len(blob):,} B  {sha[:12]})")

    if not records:
        print("\n[중단] 수집된 행이 없다.")
        return 2

    cols = ["기준연월", "터미널", "부두군", "당월_천TEU", "누계_천TEU",
            "전년당월_천TEU", "전년누계_천TEU", "전년연간_천TEU",
            "전년대비_당월_%", "전년대비_누계_%", "표모양"]
    records.sort(key=lambda r: (r["기준연월"], r["터미널"]))
    with io.open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in records:
            w.writerow({c: r.get(c, "") for c in cols})

    print(f"\n  -> {a.out}  {len(records)}행")
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

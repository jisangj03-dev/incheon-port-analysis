# -*- coding: utf-8 -*-
"""인천항 **부두·선석 시설 현황**을 인천지방해양수산청 공표 지면에서 수집한다.

왜 있는가
---------
2026-08-29. 지난 라운드에 부두 구성도를 그리며 스스로 이렇게 적었다 —

  **「지도가 아니다. 위치·거리·방위를 주장하지 않는다.」**

그 제한을 건 이유는 겸손이 아니라 **출처가 없어서**였다. 우리가 가진 것은 처리실적
(천TEU)뿐이었고 시설이 어떻게 생겼는지는 아무 데이터도 없었다. 그래서 **찾았다.**

인천지방해양수산청이 **우리 월별 통계와 같은 기관**으로서 부두현황을 공표한다.
기관이 같다는 것이 중요하다 — 처리실적과 시설을 맞댈 때 §3-9 결합 게이트가 요구하는
집계 축의 정합이 한 단계 쉬워진다. (그래도 **능력과 실적은 다른 개념**이다. 아래 한계 2.)

무엇을 받는가
-------------
  총괄 부두현황 (menuIdx=1779)  용도별 · **지역별** 요약 — 선석 수 · 부두길이 · 하역능력
  인천신항  (1774) · 내항 (1771) · 남항 (1773) · 북항 (1770) · 국제여객터미널 (4214)
                                 부두별 상세 — 명칭 · 부두길이 · 전면수심 · 동시접안능력

  python analysis/collect_port_facilities.py
  python analysis/collect_port_facilities.py --selftest

**`<caption>` 을 믿지 않는다 — 이것이 이 수집기의 핵심 판단이다.**
`인천신항` 지면(1774)의 부두현황 표는 `<h3>인천신항` · `<h4>부두현황(돌핀제외)` 아래
있는데 **`<caption>` 만 「남항 부두현황(돌핀제외)」**이다. 같은 지면의 다른 표도
`<caption>내항 사업` · `<caption>북항 부두현황` 으로 어긋나 있다.
**캡션이 다른 지면에서 복사되고 갱신되지 않은 것으로 보인다.**

  그래서 **문맥(`<h3>` + 표 바로 앞 `<h4>`)으로 잡고, 캡션은 버리지 않고 열로 같이 싣는다.**
  버리면 우리가 무엇을 무시했는지 아무도 모른다. 실으면 독자가 직접 갈라 볼 수 있다.

**셋이 서로를 받쳐 준다** — ① 지면 제목이 「인천신항」 ② 표 안에 **「신항관리부두」**가
있다 ③ 우리 월별 공표자료가 SNCT·HJIT 를 **신항 소계** 아래 둔다. 그래서 신항으로 읽는다.
**이건 추정이 아니라 세 근거의 일치다.** 캡션 하나가 그 셋을 못 이긴다.

닿지 않는 곳
------------
1. **지면이 바뀌면 파서가 깨질 수 있다.** 그래서 표를 못 찾으면 **조용히 넘어가지 않고**
   그 사실을 출력한다. 행 수가 0이면 CSV 를 쓰지 않는다.
2. **`하역능력`은 능력이지 실적이 아니다.** 처리실적과 나란히 놓을 수는 있으나
   **같은 것으로 더하거나 빼지 않는다.** 둘은 다른 개념이고, 실적이 능력을 넘는 일은
   흔하다 — 그 자체로 오류가 아니다. 지면이 그 문장을 같이 들어야 한다.
3. **자료 기준일이 지면에 없다.** 「언제 기준의 시설 현황인가」를 이 소스는 안 밝힌다.
   그래서 우리가 아는 것은 **수집일**뿐이고, CSV 에도 그렇게 적는다. **추정하지 않는다.**
4. **선석 수와 부두길이의 합이 상세표와 요약표에서 안 맞을 수 있다.** 요약표는 돌핀·부잔교
   등을 포함/제외하는 규칙이 상세표와 다르다. **맞추려고 손대지 않는다.** 어긋나면 어긋난 채 싣는다.
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

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://incheon.mof.go.kr/ko/page.do?menuIdx="
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

OUT_BERTH = os.path.join("analysis", "port_container_berths.csv")
OUT_REGION = os.path.join("analysis", "port_regions.csv")
OUT_USAGE = os.path.join("analysis", "port_usage.csv")
OUT_SRC = os.path.join("analysis", "port_facilities_sources.csv")

# (구역 이름, menuIdx). **구역 이름은 지면 제목에서 다시 확인한다** — 여기 적은 것은 기대값이다.
PAGES = [
    ("신항", 1774),
    ("내항", 1771),
    ("남항", 1773),
    ("북항", 1770),
    ("국제여객터미널", 4214),
]
SUMMARY_PAGE = 1779

# **공개하는 부두는 컨테이너 부두다.** 이 저장소의 축이 인천항 **컨테이너** 물동량이고
# (지침 §1.3), 나머지 화종의 부두 행은 그 축 밖이다. 원문에는 벌크 부두가 함께 있으나
# 우리가 다루지 않는 축이므로 공개 CSV 에 싣지 않는다 — **수집 코드는 그대로 공개되므로
# 누구나 같은 명령으로 전체를 다시 받을 수 있다**(§1.4 재현 100%). 감추는 것이 아니라
# 싣는 축을 정하는 것이다.
#
# 화종 문자열이 아니라 **코드 목록**으로 고른다. 원문에서 `SICT` 의 주요취급화물이
# `- (폐쇄)` 라 화종으로 거르면 **컨테이너 부두인데 빠진다.** 실제로 한 번 빠졌다.
CONTAINER_BERTHS = ("SNCT", "HJIT", "ICT", "E1CT", "SICT")

SP = re.compile(r"\s+")
TAG = re.compile(r"<[^>]+>")


# ── 순수 함수 ───────────────────────────────────────────────────────────────

def text_of(frag: str) -> str:
    """태그를 벗기고 공백을 정리한다. `<br>` 은 공백으로 — 셀 안 줄바꿈이 값을 가른다."""
    s = re.sub(r"<br\s*/?>", " ", frag, flags=re.I)
    return SP.sub(" ", htmllib.unescape(TAG.sub(" ", s))).replace("\xa0", " ").strip()


def grid(table_html: str) -> list[list[str]]:
    """rowspan·colspan 을 펴서 직사각 격자로 만든다.

    **이걸 안 하면 값이 밀린다.** 실제 markup 이 그렇다 —
    `<td rowspan="2">SNCT</td><td>300</td>…` 다음 행은 `<td>500</td>` 둘뿐이다.
    격자로 안 펴면 둘째 행의 `500` 이 「명칭」 자리에 앉는다.
    """
    rows = re.findall(r"<tr\b.*?</tr>", table_html, re.S)
    out: list[list[str]] = []
    pending: dict[int, tuple[str, int]] = {}   # 열 -> (값, 남은 행 수)
    for tr in rows:
        line: list[str] = []
        col = 0
        cells = re.findall(r"<t[hd]\b([^>]*)>(.*?)</t[hd]>", tr, re.S)
        idx = 0
        while idx < len(cells) or col in pending:
            if col in pending:
                val, left = pending[col]
                line.append(val)
                if left <= 1:
                    del pending[col]
                else:
                    pending[col] = (val, left - 1)
                col += 1
                continue
            attrs, body = cells[idx]
            idx += 1
            val = text_of(body)
            rs = int((re.search(r'rowspan\s*=\s*"?(\d+)', attrs, re.I) or [0, 1])[1]) \
                if re.search(r'rowspan\s*=\s*"?(\d+)', attrs, re.I) else 1
            cs = int((re.search(r'colspan\s*=\s*"?(\d+)', attrs, re.I) or [0, 1])[1]) \
                if re.search(r'colspan\s*=\s*"?(\d+)', attrs, re.I) else 1
            for _ in range(cs):
                line.append(val)
                if rs > 1:
                    pending[col] = (val, rs - 1)
                col += 1
        out.append(line)
    return out


def page_title(html: str) -> str:
    m = re.search(r"<h3[^>]*>(.*?)</h3>", html, re.S)
    return text_of(m.group(1)) if m else ""


def tables_with_context(html: str) -> list[dict]:
    """표마다 **바로 앞 `<h4>`** 와 `<caption>` 을 같이 든다. 둘 다 싣는다."""
    out = []
    for m in re.finditer(r"<table\b.*?</table>", html, re.S):
        before = html[:m.start()]
        h4 = re.findall(r"<h4[^>]*>(.*?)</h4>", before, re.S)
        cap = re.search(r"<caption[^>]*>(.*?)</caption>", m.group(0), re.S)
        out.append({
            "h4": text_of(h4[-1]) if h4 else "",
            "caption": text_of(cap.group(1)) if cap else "",
            "grid": grid(m.group(0)),
        })
    return out


def is_berth_table(t: dict) -> bool:
    """부두 상세표인가. **캡션이 아니라 머리행으로 판정한다.**"""
    head = " ".join(t["grid"][0]) if t["grid"] else ""
    return ("명칭" in head and "부두길이" in head)


def parse_berths(t: dict, region: str, menu: int) -> list[dict]:
    """부두 상세표 -> 행 목록. 같은 부두의 여러 안벽 구간은 각각 한 행으로 둔다."""
    rows = []
    body = t["grid"][1:]
    for r in body:
        if len(r) < 5:
            continue
        name, length, depth, cap, cargo = r[0], r[1], r[2], r[3], r[4]
        if not name or name == "명칭":
            continue
        rows.append({
            "구역": region, "명칭": name,
            "부두길이_m": length, "전면수심_DL_m": depth,
            "동시접안능력": cap, "주요취급화물": cargo,
            "표제목": t["h4"], "원문캡션": t["caption"],
            "출처_menuIdx": menu,
        })
    return rows


def parse_regions(t: dict) -> list[dict]:
    """지역별 요약표 -> 행 목록.

    **원문 `rowspan` 이 모자란다.** 「인천항」 셀의 `rowspan` 이 7행만 덮어서
    **거첨도·부잔교 행이 항만 열 없이 6칸으로 나온다**(2026-08-29 실측).
    캡션 어긋남과 같은 종류의 markup 결함이다.

    그래서 **6칸 행은 앞 행의 항만을 이어받는다.** 이건 추측이 아니라 `rowspan` 이
    제대로 걸렸다면 했을 일 그대로이고, 그 행들이 「경인항」 행보다 **위**에 있다는
    위치 증거가 받쳐 준다. 그래도 **복구했다는 사실을 열로 남긴다**(`행복구`).
    """
    rows = []
    port = ""
    for r in t["grid"]:
        if len(r) == 7:
            port_cell, rest, repaired = r[0], r[1:], ""
            if port_cell not in ("항만", ""):
                port = port_cell
        elif len(r) == 6 and port:
            port_cell, rest, repaired = port, r, "항만열 승계"
        else:
            continue
        gubun = rest[0]
        if gubun in ("구분", "") or port_cell in ("항만", ""):
            continue
        rows.append({
            "항만": port_cell, "구분": gubun, "선박규모_DWT": rest[1],
            "선석_개": rest[2], "부두길이_m": rest[3],
            "하역능력_BULK_천RT": rest[4], "하역능력_CONT_천TEU": rest[5],
            "행복구": repaired,
        })
    return rows


def parse_usage(t: dict) -> list[dict]:
    """용도별 요약표 -> 행 목록. 열이 하나 적다(항만 구분이 없다)."""
    rows = []
    for r in t["grid"]:
        if len(r) < 6:
            continue
        name = r[0]
        if name in ("취급화물 부두명", "선박 규모(DWT)", ""):
            continue
        rows.append({
            "취급화물": name, "선박규모_DWT": r[1], "선석_개": r[2],
            "부두길이_m": r[3], "하역능력_BULK_천RT": r[4],
            "하역능력_CONT_천TEU": r[5],
        })
    return rows


def sum_check(rows: list[dict], label: str) -> str:
    """**상세 행의 합과 표가 낸 「계」가 맞는가.**

    공표자료가 자기 합계를 같이 내므로 그 자리에서 대조할 수 있다. 안 맞으면
    **맞추지 않는다** — 어긋난 채로 적고, 얼마나 어긋났는지를 숫자로 낸다.
    (지침 §3-9-2: 항등식은 증거가 아니다. 이건 항등식이 아니라 **서로 다른 셀의 대조**다.)
    """
    tot = next((r for r in rows if r.get("구분") == "계" or r.get("취급화물") == "계"), None)
    if not tot:
        return f"{label}: 「계」 행이 없다"
    parts = [r for r in rows if r is not tot]
    out = []
    for key, unit in (("선석_개", "선석"), ("부두길이_m", "m")):
        s = sum(num(r.get(key) or "") or 0 for r in parts)
        t_ = num(tot.get(key) or "")
        if t_ is None:
            continue
        d = s - t_
        out.append(f"{unit} 부분합 {s:,.0f} / 계 {t_:,.0f}"
                   + ("  일치" if abs(d) < 1e-9 else f"  **어긋남 {d:+,.0f}**"))
    return f"{label}: " + " · ".join(out)


def num(s: str):
    s = (s or "").replace(",", "").strip()
    if not s or s in ("-", "–"):
        return None
    m = re.match(r"^-?\d+(\.\d+)?$", s)
    return float(s) if m else None


# ── 망 접점 ─────────────────────────────────────────────────────────────────

def fetch(menu: int) -> bytes:
    req = urllib.request.Request(BASE + str(menu), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


# ── 인수시험 ────────────────────────────────────────────────────────────────

FIX = """<h3>인천신항</h3>
<h4>부두현황(돌핀제외)</h4>
<table><caption>남항 부두현황(돌핀제외)</caption>
<thead><tr><th>명칭</th><th>부두길이</th><th>전면수심(DL(-),m)</th>
<th>동시접안능력<br>(DWT)</th><th>주요취급화물</th></tr></thead><tbody>
<tr><td rowspan="2">SNCT</td><td>300</td><td rowspan="2">14.0</td>
<td>40,000&times;1<br>(3천TEU이상)</td><td rowspan="2">컨테이너</td></tr>
<tr><td class="bor">500</td><td>30,000&times;2<br>(2천TEU이상)</td></tr>
<tr><td>신항관리부두</td><td>600</td><td>9.0</td><td>-</td><td>-</td></tr>
</tbody></table>"""

FIX_REGION = """<table><caption>지역별 부두현황 요약정보</caption>
<thead><tr><th>항만</th><th>구분</th><th>접안능력</th><th>부두길이(m)</th><th>하역능력</th></tr>
<tr><th>선박 규모(DWT)</th><th>선석(개)</th><th>BULK(천RT)</th><th>CONT(천TEU)</th></tr></thead>
<tbody>
<tr><td rowspan="2">인천항</td><td>신항</td><td>3,000 ~ 75,000</td><td>10</td><td>2,900</td><td>46,990</td><td>2,162</td></tr>
<tr><td>내항</td><td>2,000 ~ 50,000</td><td>43</td><td>9,405</td><td>38,161</td><td>&nbsp;</td></tr>
</tbody></table>"""


def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: rowspan 을 펴서 값이 안 밀린다 (이게 이 파일의 급소) ──")
    ts = tables_with_context(FIX)
    g = ts[0]["grid"]
    chk("표 1개", len(ts), 1)
    chk("머리행", g[0][:2], ["명칭", "부두길이"])
    chk("SNCT 첫 구간", g[1][:5],
        ["SNCT", "300", "14.0", "40,000×1 (3천TEU이상)", "컨테이너"])
    chk("**둘째 구간의 명칭이 SNCT 로 채워진다** (안 그러면 500 이 명칭 자리에 앉는다)",
        g[2][0], "SNCT")
    chk("둘째 구간 부두길이", g[2][1], "500")
    chk("둘째 구간 수심도 승계된다", g[2][2], "14.0")
    chk("rowspan 끝난 뒤 다음 부두는 자기 값을 쓴다", g[3][0], "신항관리부두")
    chk("`<br>` 이 값을 안 붙인다", g[1][3], "40,000×1 (3천TEU이상)")
    chk("격자가 직사각이다", sorted({len(r) for r in g}), [5])

    print("── 인수시험: 캡션을 안 믿고 문맥으로 잡는다 ──")
    chk("지면 제목", page_title(FIX), "인천신항")
    chk("표 바로 앞 h4", ts[0]["h4"], "부두현황(돌핀제외)")
    chk("**캡션은 어긋나 있다 — 버리지 않고 싣는다**", ts[0]["caption"],
        "남항 부두현황(돌핀제외)")
    chk("부두표로 알아본다 (머리행 기준)", is_berth_table(ts[0]), True)

    rows = parse_berths(ts[0], "신항", 1774)
    chk("부두 행 3건 (SNCT 2구간 + 관리부두)", len(rows), 3)
    chk("SNCT 두 구간이 각각 한 행", [r["부두길이_m"] for r in rows[:2]], ["300", "500"])
    chk("행에 구역이 붙는다", rows[0]["구역"], "신항")
    chk("행에 원문 캡션이 같이 남는다", rows[0]["원문캡션"], "남항 부두현황(돌핀제외)")
    chk("머리행은 안 들어온다", any(r["명칭"] == "명칭" for r in rows), False)

    print("── 인수시험: 지역별 요약 ──")
    rt = tables_with_context(FIX_REGION)[0]
    regs = parse_regions(rt)
    chk("2행", len(regs), 2)
    chk("항만이 rowspan 으로 채워진다", [r["항만"] for r in regs], ["인천항", "인천항"])
    chk("신항 선석", regs[0]["선석_개"], "10")
    chk("신항 CONT", regs[0]["하역능력_CONT_천TEU"], "2,162")
    chk("내항 CONT 는 빈칸", num(regs[1]["하역능력_CONT_천TEU"]), None)
    chk("머리행 2줄이 안 들어온다", any(r["구분"] == "구분" for r in regs), False)

    print("── 인수시험: 숫자 읽기 ──")
    chk("쉼표", num("46,990"), 46990.0)
    chk("소수", num("14.0"), 14.0)
    chk("빈칸", num(" "), None)
    chk("하이픈", num("-"), None)
    chk("숫자가 아닌 것은 None", num("3,000 ~ 75,000"), None)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="인천항 부두·선석 시설 현황 수집 (인천지방해양수산청).")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    os.chdir(ROOT)
    from datetime import date
    today = date.today().isoformat()

    print("== 인천항 부두·선석 시설 현황 수집 ==")
    print("  출처: 인천지방해양수산청 (월별 항만운영통계와 **같은 기관**)")
    berths, regions, sources = [], [], []

    # ① 총괄 — 지역별 요약
    blob = fetch(SUMMARY_PAGE)
    html = blob.decode("utf-8", "replace")
    sha = hashlib.sha256(blob).hexdigest().upper()
    sources.append((SUMMARY_PAGE, page_title(html), BASE + str(SUMMARY_PAGE),
                    len(blob), sha[:16], today))
    got = 0
    usage = []
    for t in tables_with_context(html):
        tag = t["caption"] + " " + t["h4"]
        if "지역별" in tag:
            regions += parse_regions(t)
            got += 1
        elif "용도별" in tag:
            usage += parse_usage(t)
            got += 1
    print(f"  {SUMMARY_PAGE:>5} {page_title(html):<12} 지역별 표 {got}개 · {len(regions)}행"
          f"  ({len(blob):,} B  {sha[:12]})")
    if not regions:
        print("  [경고] 지역별 요약표를 못 찾았다 — 지면 구조가 바뀌었을 수 있다(한계 1).")
    rep = sum(1 for r in regions if r.get("행복구"))
    if rep:
        print(f"        **원문 rowspan 이 모자라 {rep}행을 항만열 승계로 복구했다** (CSV 에 표시했다)")

    # ② 구역별 상세
    for want, menu in PAGES:
        blob = fetch(menu)
        html = blob.decode("utf-8", "replace")
        sha = hashlib.sha256(blob).hexdigest().upper()
        title = page_title(html)
        rows = []
        for t in tables_with_context(html):
            if is_berth_table(t):
                rows += parse_berths(t, want, menu)
        berths += rows
        note = "" if title else "  [지면 제목 못 읽음]"
        mism = sum(1 for r in rows if r["원문캡션"] and want not in r["원문캡션"])
        if mism:
            note += f"  **캡션 어긋남 {mism}행** (문맥으로 잡았다)"
        # **0행일 때 「왜 0인가」를 가른다.** 표가 없는 것과 표가 다른 모양인 것은 다른 사실이고,
        # 둘을 같이 「0행」으로 적으면 파서가 깨진 것을 못 알아본다(한계 1).
        if not rows:
            ntab = len(tables_with_context(html))
            note += ("  [표 자체가 없다]" if ntab == 0 else
                     f"  [표 {ntab}개 있으나 부두표 형식이 아니다 — 안 가져왔다]")
        print(f"  {menu:>5} {title:<12} 부두 {len(rows):>2}행  "
              f"({len(blob):,} B  {sha[:12]}){note}")
        sources.append((menu, title, BASE + str(menu), len(blob), sha[:16], today))

    if not berths:
        print("\n[중단] 부두 행이 하나도 없다. 아무것도 쓰지 않는다.")
        return 2

    all_n = len(berths)
    berths = [r for r in berths if r["명칭"].strip() in CONTAINER_BERTHS]
    print(f"\n  부두 행 {all_n}건 중 **컨테이너 부두 {len(berths)}건**만 싣는다"
          f"  (축 = 인천항 컨테이너 · 지침 §1.3)")
    if not berths:
        print("  [중단] 컨테이너 부두를 하나도 못 찾았다 — 코드 표기가 바뀌었을 수 있다.")
        return 2

    with io.open(OUT_BERTH, "w", encoding="utf-8-sig", newline="") as f:
        cols = ["구역", "명칭", "부두길이_m", "전면수심_DL_m", "동시접안능력",
                "주요취급화물", "표제목", "원문캡션", "출처_menuIdx"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in berths:
            w.writerow(r)
    print(f"\n  -> {OUT_BERTH}  {len(berths)}행")

    if regions:
        with io.open(OUT_REGION, "w", encoding="utf-8-sig", newline="") as f:
            cols = ["항만", "구분", "선박규모_DWT", "선석_개", "부두길이_m",
                    "하역능력_BULK_천RT", "하역능력_CONT_천TEU", "행복구"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in regions:
                w.writerow(r)
        print(f"  -> {OUT_REGION}  {len(regions)}행")

    with io.open(OUT_SRC, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["menuIdx", "지면제목", "URL", "바이트", "SHA256_앞16", "수집일"])
        for row in sources:
            w.writerow(row)
    print(f"  -> {OUT_SRC}  (지면 {len(sources)}건)")

    if usage:
        with io.open(OUT_USAGE, "w", encoding="utf-8-sig", newline="") as f:
            cols = ["취급화물", "선박규모_DWT", "선석_개", "부두길이_m",
                    "하역능력_BULK_천RT", "하역능력_CONT_천TEU"]
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in usage:
                w.writerow(r)
        print(f"  -> {OUT_USAGE}  {len(usage)}행")

    print("\n== 공표자료 자체 검산 — 상세 행의 합 ↔ 표가 낸 「계」 ==")
    print("  " + sum_check(regions, "지역별"))
    print("  " + sum_check(usage, "용도별"))
    print("  → 어긋나면 **맞추지 않는다.** 어긋난 채로 싣고 얼마나 어긋났는지를 적는다.")

    print("\n== 이 데이터의 한계 — 같이 실어야 한다 ==")
    print("  · **자료 기준일이 지면에 없다.** 우리가 아는 것은 수집일뿐이다. 추정하지 않는다.")
    print("  · **하역능력은 능력이지 실적이 아니다.** 나란히 놓을 수는 있어도 더하거나 빼지 않는다.")
    print("  · **요약표와 상세표의 합이 안 맞을 수 있다** (돌핀·부잔교 포함 규칙이 다르다).")
    print("    맞추려고 손대지 않는다. 어긋나면 어긋난 채 싣는다.")
    print("  · **`<caption>` 이 문맥과 어긋나는 표가 있다.** 원문 캡션을 CSV 에 같이 실었다 —")
    print("    우리가 무엇을 무시했는지 독자가 직접 갈라 볼 수 있어야 한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

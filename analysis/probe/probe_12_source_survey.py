# -*- coding: utf-8 -*-
"""프로브 12 — **원문에 우리가 안 본 표가 무엇이 있는가.**

왜 있는가
---------
사고 55의 교훈이 이것이었다 —

  **파서는 자기가 아는 것만 보고, 모르는 것이 있다는 사실은 안 알려 준다.**

`collect_terminal_monthly.py` 는 `TERMINALS` 사전에 있는 이름만 줍는다. 그래서
같은 표 안에 있던 **부두군 소계와 공표 합계를 10개월 내내 못 보고 있었다.**
그 교훈을 적어 놓고 **같은 문서의 나머지 표는 아직 한 번도 열거해 본 적이 없다.**

이 프로브는 판정을 하지 않는다. **문서 안의 표를 전부 세어서 「무엇이 있는가」만 낸다.**
그중 무엇을 쓸지는 사람이 정한다. 안 쓰기로 해도 **안 쓴다는 사실이 기록된다** —
`/data/` 지면이 「아직 안 본 축」을 적는 것과 같은 이유다.

  python analysis/probe/probe_12_source_survey.py            # 최신월
  python analysis/probe/probe_12_source_survey.py --all      # 10개월 전부 (표 구성 변화)
  python analysis/probe/probe_12_source_survey.py --table 7  # 한 표를 통째로

**읽기 전용이다. 아무것도 안 쓴다.** 인용한 SHA-256 과 먼저 대조한 뒤 연다 —
다른 파일을 열고 결론을 내면 그 결론이 딴 파일 것이다.
"""

import argparse
import csv
import hashlib
import io
import os
import re
import sys
import urllib.request
import zipfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC_CSV = os.path.join(ROOT, "analysis", "terminal_monthly_sources.csv")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")

# 우리가 이미 쓰고 있는 표를 알아보기 위한 표지.
KNOWN = ("SNCT", "HJIT", "E1CT", "ICT")
# 시설·구조 축의 표지 — 이번 라운드가 찾는 것.
FACILITY = ("선석", "안벽", "수심", "접안", "하역능력", "장치장", "부두", "규모", "시설", "면적")


def cell_text(tc):
    return " ".join(re.findall(r"<hp:t>(.*?)</hp:t>", tc, re.DOTALL)).strip()


def tables(xml):
    out = []
    for tbl in re.findall(r"<hp:tbl\b.*?</hp:tbl>", xml, re.DOTALL):
        rows = []
        for tr in re.findall(r"<hp:tr\b.*?</hp:tr>", tbl, re.DOTALL):
            rows.append([re.sub(r"\s+", " ", cell_text(c)).strip()
                         for c in re.findall(r"<hp:tc\b.*?</hp:tc>", tr, re.DOTALL)])
        out.append(rows)
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": "https://incheon.mof.go.kr/"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def sections(blob):
    xml = ""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for n in sorted(x for x in z.namelist()
                        if x.endswith(".xml") and "section" in x.lower()):
            xml += z.read(n).decode("utf-8", "replace")
    return xml


def label(grid):
    """표의 성격을 첫 두 행에서 짐작한다. **짐작이라고 적는다.**"""
    head = " ".join(" ".join(r) for r in grid[:2])[:110]
    return head or "(빈 표)"


def survey(ym, blob, want_table=None):
    xml = sections(blob)
    grids = tables(xml)
    print(f"\n== {ym} · 표 {len(grids)}개 ==")
    for i, g in enumerate(grids):
        flat = " ".join(" ".join(r) for r in g)
        tags = []
        if any(k in flat for k in KNOWN):
            tags.append("**우리가 쓰는 표**")
        hits = [w for w in FACILITY if w in flat]
        if hits:
            tags.append("시설어휘:" + "·".join(hits[:6]))
        ncell = sum(len(r) for r in g)
        print(f"  표#{i:<3} {len(g):>3}행 {ncell:>4}셀  {' '.join(tags)}")
        print(f"        {label(g)}")
        if want_table is not None and i == want_table:
            print("        ── 전문 ──")
            for j, r in enumerate(g):
                print(f"        {j:>2} | " + " | ".join(c if c else "·" for c in r))
    return grids


def main():
    ap = argparse.ArgumentParser(description="월별 공표자료의 표를 전부 열거한다 (판정 없음).")
    ap.add_argument("--all", action="store_true", help="10개월 전부")
    ap.add_argument("--table", type=int, default=None, help="이 번호 표를 통째로 출력")
    a = ap.parse_args()

    rows = list(csv.DictReader(io.open(SRC_CSV, encoding="utf-8-sig")))
    targets = rows if a.all else rows[-1:]

    print("== 프로브 12 — 원문 표 전수 열거 ==")
    print("  사고 55: 파서는 자기가 아는 것만 보고, 모르는 것이 있다는 사실은 안 알려 준다.")

    counts = {}
    for r in targets:
        ym, url = r["기준연월"], r["첨부URL"]
        blob = fetch(url)
        got = hashlib.sha256(blob).hexdigest().upper()[:16]
        ok = (got == r["SHA256_앞16"] and len(blob) == int(r["바이트"]))
        if not ok:
            print(f"\n[경고] {ym} 원본이 기록과 다르다 (기록 {r['SHA256_앞16']} / 지금 {got}).")
            print("       그 자체가 관측이다. 아래 내용은 인용본에 대한 것이 아니다.")
        grids = survey(ym, blob, a.table)
        counts[ym] = len(grids)

    if len(counts) > 1:
        print("\n== 달마다 표 개수가 같은가 ==")
        for ym, n in sorted(counts.items()):
            print(f"  {ym}  {n}개")
        uniq = sorted(set(counts.values()))
        print("  → " + ("전 구간 동일하다." if len(uniq) == 1
                        else f"**다르다** {uniq} — 표 구성이 달마다 흔들린다. 파서가 위치가 아니라 이름으로 찾아야 하는 이유다."))

    print("\n  ※ 이 프로브는 아무것도 쓰지 않았다. 무엇을 쓸지는 사람이 정한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

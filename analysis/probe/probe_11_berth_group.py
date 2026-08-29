# -*- coding: utf-8 -*-
"""프로브 11 — **「부두군」 열은 어디서 왔는가.**

왜 있는가
---------
`/terminals/` 지면은 터미널마다 **부두군(신항 · 남항 · 국제여객부두)**을 같이 싣는다.
그런데 `collect_terminal_monthly.py` 의 `TERMINALS` 를 읽으면 그 값은
**우리가 손으로 박은 매핑**이다. 공표자료의 표에서 읽어 온 것이 아니다.

같은 지면의 **「몫 %」열은 「우리가 계산했다 — 공표자료에 없는 열이다」라고 적혀 있다.**
**부두군에는 그 표시가 없다.** 그래서 독자는 그 열도 공표자료에서 온 것으로 읽는다.
지침 §3-6 — 「업계 통설·"일반적으로"는 출처가 아니다」. 맞는 값이어도 출처가 없으면
그 지위는 `미확인` 이고, **미확인은 결론 자리에 못 쓴다**(§3 지위 4등급).

무엇을 보는가
-------------
공표자료 원문을 **실제로 내려받아 열고**(§5 실파일 원칙), 그 안에 신항/남항 구분이
있는지 본다. 있으면 부두군은 `관측`이고, 없으면 **우리 배정이라고 지면에 적어야 한다.**

  python analysis/probe/probe_11_berth_group.py

**읽기 전용이다. 아무것도 안 쓴다.** 받은 파일은 메모리에만 둔다.
`terminal_monthly_sources.csv` 에 적힌 SHA-256 과 대조해 **우리가 인용한 그 파일이
맞는지 먼저 확인한 뒤** 연다 — 다른 파일을 열고 결론을 내면 그 결론이 딴 파일 것이다.
"""

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

TERMS = ["SNCT", "HJIT", "E1CT", "ICT", "국제여객부두"]
GROUP_WORDS = ["신항", "남항", "내항", "북항", "외항", "부두", "선석", "터미널"]


def cell_text(tc):
    return " ".join(re.findall(r"<hp:t>(.*?)</hp:t>", tc, re.DOTALL)).strip()


def tables(xml):
    out = []
    for tbl in re.findall(r"<hp:tbl\b.*?</hp:tbl>", xml, re.DOTALL):
        rows = []
        for tr in re.findall(r"<hp:tr\b.*?</hp:tr>", tbl, re.DOTALL):
            rows.append([cell_text(c) for c in
                         re.findall(r"<hp:tc\b.*?</hp:tc>", tr, re.DOTALL)])
        out.append(rows)
    return out


def plain_text(xml):
    return re.sub(r"\s+", " ", " ".join(re.findall(r"<hp:t>(.*?)</hp:t>", xml, re.DOTALL)))


def main():
    rows = list(csv.DictReader(io.open(SRC_CSV, encoding="utf-8-sig")))
    latest = rows[-1]
    ym, url = latest["기준연월"], latest["첨부URL"]
    want_head, want_bytes = latest["SHA256_앞16"], int(latest["바이트"])

    print("== 프로브 11 — 부두군 열의 출처 ==")
    print("  대상 %s · %s" % (ym, url))

    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Referer": "https://incheon.mof.go.kr/"})
    with urllib.request.urlopen(req, timeout=60) as r:
        blob = r.read()

    got_head = hashlib.sha256(blob).hexdigest().upper()[:16]
    same = (got_head == want_head and len(blob) == want_bytes)
    print("  받은 바이트 %d (기록 %d) · SHA-256 앞16 %s (기록 %s)"
          % (len(blob), want_bytes, got_head, want_head))
    print("  → %s" % ("**우리가 인용한 그 파일이 맞다**" if same else
                      "**다른 파일이다. 아래 관측은 인용본에 대한 것이 아니다.**"))
    if not same:
        print("     (원문이 교체됐을 수 있다. 그 자체가 별도 관측이다.)")

    xml = ""
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names = [n for n in z.namelist() if n.endswith(".xml") and "section" in n.lower()]
        for n in sorted(names):
            xml += z.read(n).decode("utf-8", "replace")
    print("  section XML %d개 · %d자" % (len(names), len(xml)))

    text = plain_text(xml)

    print("\n-- 1. 문서 전체에서 부두군 어휘가 나오는가 --")
    for w in GROUP_WORDS:
        n = text.count(w)
        print("  %-8s %3d회" % (w, n))

    print("\n-- 2. 터미널 코드와 같은 표 안에 신항/남항이 있는가 --")
    hit = False
    for gi, grid in enumerate(tables(xml)):
        flat = " ".join(" ".join(r) for r in grid)
        if not any(t in flat for t in TERMS):
            continue
        has_new = "신항" in flat
        has_south = "남항" in flat
        print("  표#%-3d 터미널 있음 · 신항=%s · 남항=%s · %d행"
              % (gi, has_new, has_south, len(grid)))
        if has_new or has_south:
            hit = True
        for r in grid[:14]:
            cells = [c for c in r if c]
            if cells and any(t in " ".join(cells) for t in TERMS + ["신항", "남항", "구분"]):
                print("        %s" % (" | ".join(cells))[:150])

    print("\n-- 3. 신항/남항이 나오는 문장 (표 밖 포함) --")
    for w in ("신항", "남항"):
        for m in list(re.finditer(w, text))[:6]:
            s = max(0, m.start() - 70)
            print("  [%s] …%s…" % (w, text[s:m.end() + 70]))

    print("\n== 관측 ==")
    if hit:
        print("  터미널 표 안에 신항/남항 구분이 **있다** → 부두군은 원문에서 온 값이다.")
    else:
        print("  터미널 표 안에 신항/남항 구분이 **없다**.")
        print("  → `부두군` 은 **우리가 배정한 열**이다. 지면이 그렇게 말해야 한다.")
        print("     (「몫 %」열이 이미 그렇게 표시돼 있다 — 같은 처리를 하면 된다.)")
    print("\n  ※ 이 프로브는 아무것도 쓰지 않았다. 판정은 사람이 한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

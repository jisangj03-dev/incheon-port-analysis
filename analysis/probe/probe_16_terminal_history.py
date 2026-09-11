# -*- coding: utf-8 -*-
"""프로브 — 터미널별 내역은 **언제부터** 공표자료 안에 있는가.

**질문.** `probe_15` 가 게시판에 글이 2006-09 분까지 있다는 것을 쟀다.
**그런데 글이 있는 것과 그 축이 있는 것은 다르다**(사고 26). 터미널 개장 시기가 제각각이라
글 수가 그대로 관측 개월 수가 되지 않는다. **첨부를 열어 봐야 안다.**

**값을 안 싣는다.** 각 달의 첨부에서 **터미널 행이 몇 개이고 이름이 무엇인가**만 본다 —
TEU 는 한 자리도 기록하지 않는다. 그래서 이 프로브는 **선커밋 앞에서 쳐도 된다**
(발행 SKILL §1 「값 비노출 설계」 · §2 「창을 수집기의 기본값이 정하게 두지 않는다」).

    python analysis/probe/probe_16_terminal_history.py            # 이어서 훑는다(캐시)
    python analysis/probe/probe_16_terminal_history.py --fresh    # 처음부터
    python analysis/probe/probe_16_terminal_history.py --selftest # 망을 안 탄다

산출물 `analysis/probe/terminal_axis_history.csv` — 달마다 한 줄:
기준연월 · 첨부 바이트 · SHA256 앞 16 · 터미널 행 수 · 터미널 이름 · 부두군 행 수 · 상태.
**이 표가 다음 편의 창을 정하는 근거다.** 창은 사람이 읽고 정한다 — 이 파일이 정하지 않는다.

닿지 않는 곳
------------
· **파서가 못 읽은 것과 원문에 없는 것을 이 표가 못 가른다.** 상태 칸이 그 둘을
  `표없음`(컨테이너 구획을 못 찾음) · `터미널0`(구획은 찾았으나 터미널 행이 없음) ·
  `hwpx아님` 으로 갈라 적을 뿐이고, **어느 쪽인지 단정하지 않는다.**
  옛 서식은 표 모양이 다를 수 있다 — 창을 확정하기 전에 경계 달의 원문을 사람이 한 번 본다.
· **이름이 있다고 그 달 값이 쓸 만하다는 뜻이 아니다.** 그건 편을 열고 게이트가 본다.
· 게시판은 살아 있다. **이 표는 측정일의 관측이다.**
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import collect_terminal_monthly as C  # noqa: E402

OUT = os.path.join(HERE, "terminal_axis_history.csv")
FIELDS = ["기준연월", "바이트", "SHA256_앞16", "터미널행수", "터미널이름", "부두군행수", "상태"]
PAUSE = 0.25   # 남의 서버다. 한 번에 몰아치지 않는다.


def inspect(ym: str, url: str) -> dict:
    """한 달 — **행 수와 이름만.** 값은 읽지도 적지도 않는다."""
    row = {"기준연월": ym, "바이트": "", "SHA256_앞16": "",
           "터미널행수": 0, "터미널이름": "", "부두군행수": 0, "상태": ""}
    att = C.attachment(url)
    if not att:
        row["상태"] = "첨부없음"
        return row
    blob = C.get(att, referer=url)
    row["바이트"] = len(blob)
    row["SHA256_앞16"] = hashlib.sha256(blob).hexdigest().upper()[:16]
    try:
        rows = C.hwpx_rows(blob)
    except (zipfile.BadZipFile, KeyError):
        row["상태"] = "hwpx아님"
        return row
    if not C.container_block(rows):
        row["상태"] = "표없음"
        return row
    found = C.parse_terminals(rows)
    groups = C.parse_groups(rows)
    row["터미널행수"] = len(found)
    # **이름만 가져온다.** 값이 든 칸은 건드리지 않는다.
    row["터미널이름"] = " ".join(sorted(r["터미널"] for r in found))
    row["부두군행수"] = len(groups)
    row["상태"] = "있음" if found else "터미널0"
    return row


def load_cache() -> dict:
    if not os.path.exists(OUT):
        return {}
    with io.open(OUT, encoding="utf-8-sig", newline="") as f:
        return {r["기준연월"]: r for r in csv.DictReader(f)}


def save(rows: dict) -> None:
    with io.open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for ym in sorted(rows):
            w.writerow({k: rows[ym].get(k, "") for k in FIELDS})


def summary(rows: dict) -> None:
    """연도별 한 줄. **달 목록이 아니라 모양을 본다.**"""
    years = {}
    for ym, r in sorted(rows.items()):
        years.setdefault(ym[:4], []).append(r)
    print("\n  연도  달  터미널행이 있는 달  이름 집합")
    for y in sorted(years):
        rs = years[y]
        hit = [r for r in rs if int(r["터미널행수"] or 0) > 0]
        names = sorted({r["터미널이름"] for r in hit})
        print("  %s  %2d  %2d  %s" % (y, len(rs), len(hit),
                                      " / ".join(names)[:76] or "—"))
    ok = sorted(ym for ym, r in rows.items() if int(r["터미널행수"] or 0) > 0)
    if not ok:
        print("\n  **터미널 행이 있는 달이 없다.**")
        return
    print("\n  터미널 행이 있는 달 %d개 · %s ~ %s" % (len(ok), ok[0], ok[-1]))
    # **끊김을 센다** — 판정 창은 끊기면 못 쓴다.
    span = [ym for ym in sorted(rows) if ok[0] <= ym <= ok[-1]]
    gaps = [ym for ym in span if ym not in ok]
    print("  그 구간 %d개월 중 빈 달 %d개%s"
          % (len(span), len(gaps), (" — " + " ".join(gaps)) if gaps else ""))
    # **끊기지 않고 이어지는 가장 긴 꼬리** — 지금부터 거슬러 몇 달이 성한가.
    tail = 0
    for ym in reversed(span):
        if ym in ok:
            tail += 1
        else:
            break
    print("  **최신에서 끊김 없이 이어지는 구간: %d개월 (%s ~ %s)**"
          % (tail, span[-tail], span[-1]))
    print("\n  **창은 이 표가 정하지 않는다.** 사람이 읽고 정하고, 경계 달의 원문을 한 번 본다.")


def probe(fresh: bool) -> int:
    posts = C.list_posts()
    print("== 터미널 축은 언제부터 있는가 — 값은 안 읽는다 ==")
    print("  게시판 목록 %d개월: %s ~ %s" % (len(posts), posts[-1][0], posts[0][0]))
    cache = {} if fresh else load_cache()
    print("  캐시 %d개월 · 새로 볼 달 %d개월\n"
          % (len(cache), sum(1 for ym, _ in posts if ym not in cache)))
    n = 0
    try:
        for ym, url in sorted(posts):
            if ym in cache:
                continue
            r = inspect(ym, url)
            cache[ym] = r
            n += 1
            print("  %s  터미널 %s  부두군 %s  %s  %s"
                  % (ym, r["터미널행수"], r["부두군행수"], r["상태"], r["터미널이름"]))
            if n % 20 == 0:
                save(cache)
            time.sleep(PAUSE)
    except KeyboardInterrupt:
        print("\n  [중단] 여기까지 저장한다 — 다시 치면 이어서 본다.")
    save(cache)
    print("\n  적었다: %s (%d개월)" % (os.path.relpath(OUT, os.path.dirname(HERE)), len(cache)))
    summary(cache)
    return 0


def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-46s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 값을 안 싣는다 ──")
    # **이것이 이 프로브의 정지선이다** — 열 이름에 값 칸이 없어야 한다.
    for bad in ("천TEU", "당월", "누계", "증감"):
        chk("열 이름에 '%s' 가 없다" % bad, any(bad in f for f in FIELDS), False)
    chk("열은 일곱", len(FIELDS), 7)

    print("── 인수시험: 요약이 끊김을 센다 ──")
    def row(ym, n, names=""):
        return {"기준연월": ym, "터미널행수": str(n), "터미널이름": names,
                "부두군행수": "0", "상태": "있음" if n else "터미널0",
                "바이트": "", "SHA256_앞16": ""}
    rows = {ym: row(ym, n) for ym, n in
            (("2024-01", 0), ("2024-02", 5), ("2024-03", 0), ("2024-04", 5), ("2024-05", 5))}
    buf = io.StringIO()
    keep, sys.stdout = sys.stdout, buf
    try:
        summary(rows)
    finally:
        sys.stdout = keep
    out = buf.getvalue()
    chk("빈 달을 센다", "빈 달 1개" in out, True)
    chk("끊김 없는 꼬리를 센다", "2개월 (2024-04 ~ 2024-05)" in out, True)
    chk("빈 달 이름을 적는다", "2024-03" in out, True)

    print("── 인수시험: 고친 수집기를 쓴다 ──")
    chk("list_posts 가 쪽 상한을 받는다",
        "max_pages" in C.list_posts.__code__.co_varnames, True)
    chk("끝 페이지 정규식을 든다", C.END_RE.search(
        '<a onclick="fnPageMove(23);return false;" class="btn_end">끝</a>').group(1), "23")

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="터미널 축의 시작 — 값은 안 읽는다")
    ap.add_argument("--fresh", action="store_true", help="캐시를 버리고 처음부터")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else probe(a.fresh))

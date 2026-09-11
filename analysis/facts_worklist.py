# -*- coding: utf-8 -*-
"""대장 미등재 값의 **작업 목록**을 만든다 — 창을 추정하지 않고 **찾아 오게** 한다.

왜 있는가
---------
`#01~#06` 의 결론 자리에 대장 미등재 값이 **96건** 있다(2026-08-29 실측). 오래된 부채고,
STATUS 가 이렇게 적어 놨다 — **「창을 추정해 채우면 사고 22의 재발이므로 일괄 등재하지 않는다.」**
그 판단은 옳다. 사고 22가 「값은 창과 지위 없이 이동하면 안 된다」였는데,
**창을 지어내서 채우는 것은 그 사고를 대장 안에서 재현하는 짓**이다.

**그런데 그 판단이 「그러므로 아무것도 안 한다」로 굳어 있었다.** 사고 58과 같은 자리다 —
정직한 한계 표기가 탐색 종료 신호가 됐다. 추정이 금지인 것이지 **확인이 금지는 아니다.**

이 도구가 하는 일
-----------------
미등재 값마다 **창을 지어낼 필요가 없게** 재료를 모아 온다.

  ① 그 값이 **어느 문장에 있는가** — 린터는 구역 시작 줄만 준다. 여기선 실제 줄과 문장을 찾는다.
  ② 그 문장이 **창을 이미 말하고 있는가** — 보고서 본문에는 대개 「2025년」·「연간」이 붙어 있다.
  ③ 그 값이 **우리 원시 데이터에 있는가** — 있으면 창은 추정이 아니라 **조회**다.

**등재는 안 한다.** 사람이 읽고 정하도록 재료만 낸다 — 자동 등재는 곧 자동 추정이다.

  python analysis/facts_worklist.py                     # 전체
  python analysis/facts_worklist.py --report report_01  # 한 편
  python analysis/facts_worklist.py --value 62,115      # 한 값의 출처 추적
  python analysis/facts_worklist.py --selftest

닿지 않는 곳
------------
1. **CSV 에서 값을 찾았다고 창이 확정되는 것은 아니다.** 같은 숫자가 다른 창에 또 있을 수 있다.
   그래서 **찾은 자리를 전부** 보여 주고, 하나로 좁히는 것은 사람이 한다.
2. **문장이 말하는 창이 맞는지는 안 본다.** 본문이 틀렸을 수도 있다 — 그건 원문 대조의 일이다.
3. **백분율·배율은 원시 데이터에 그대로 없다**(계산값이다). 그런 값은 ③이 비고,
   ①②만으로 판단해야 한다. **비었다는 것도 정보다.**
"""

import argparse
import csv
import io
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "analysis"))

import lint_publish as L  # noqa: E402

REPORTS = ROOT / "reports"
# 창을 조회할 원시 데이터. **우리가 만든 재현 자산만** 본다.
DATA_GLOBS = ["analysis/*.csv", "analysis/probe/*.csv"]

# 문장이 창을 말하고 있는지 알아보는 표지.
WINDOW_HINTS = re.compile(
    r"(20\d\d년?|\d{1,2}월|연간|누계|월별|분기|상반기|하반기|전년|전체|평균|"
    r"1~12월|1-12월|단월|연평균|기간)")


def sentences(text: str):
    """문장 단위로 자른다. 표 행은 통째로 한 덩어리로 둔다 — 창이 머리행에 있기 때문이다."""
    out = []
    for raw in text.splitlines():
        if raw.strip().startswith("|"):
            out.append(raw.strip())
            continue
        for s in re.split(r"(?<=[.!?])\s+|(?<=다\.)\s*", raw):
            s = s.strip()
            if s:
                out.append(s)
    return out


def ledger_rows(names):
    """이름마다 **대장 전문**에서 그 이름이 든 행을 찾는다. 반환 {이름: [(줄번호, 행)]}.

    **`load_facts()` 를 안 쓴다.** 그쪽은 `LINT-TABLE` 블록만 읽는데,
    **놓쳐서 사고가 난 행이 하필 그 블록 밖에 있었다** — `SICT`(2026-09-11 · #11 §2 정정).
    비수치 정본 절은 린터가 안 읽는 자리이고, **안 읽는다는 것이 없다는 뜻은 아니다.**
    """
    text = (ROOT / "docs" / "FACTS.md").read_text(encoding="utf-8")
    out = {n: [] for n in names}
    for i, ln in enumerate(text.splitlines(), 1):
        if not ln.startswith("|"):
            continue
        for n in names:
            if n and n.lower() in ln.lower():
                out[n].append((i, ln.strip()))
    return out


def find_lines(md: str, token: str):
    """값이 실제로 나오는 (줄번호, 문장). 린터가 안 주는 것."""
    hits = []
    for i, ln in enumerate(md.splitlines(), 1):
        if token in ln:
            for s in sentences(ln):
                if token in s:
                    hits.append((i, s.strip()))
    return hits


def load_data_files():
    files = []
    for g in DATA_GLOBS:
        files += sorted(ROOT.glob(g))
    return files


def search_data(token: str, files):
    """원시 데이터에서 이 값이 나오는 자리. **창은 조회지 추정이 아니다.**

    숫자만 비교한다 — `62,115TEU` 의 `62,115` 와 CSV 의 `62115` 가 같은 값이다.
    """
    m = re.search(r"[\d,]+(?:\.\d+)?", token)
    if not m:
        return []
    plain = m.group(0).replace(",", "")
    hits = []
    for p in files:
        try:
            rows = list(csv.reader(io.open(p, encoding="utf-8-sig")))
        except Exception:
            continue
        if not rows:
            continue
        head = rows[0]
        for r in rows[1:]:
            for ci, cell in enumerate(r):
                c = (cell or "").replace(",", "").strip()
                if c == plain or (c and c.rstrip("0").rstrip(".") == plain.rstrip("0").rstrip(".")
                                  and "." in (c + plain)):
                    ctx = " · ".join(
                        f"{head[k]}={r[k]}" for k in range(min(len(head), len(r)))
                        if k != ci and r[k] and head[k])
                    hits.append((p.relative_to(ROOT).as_posix(),
                                 head[ci] if ci < len(head) else f"열{ci}", ctx[:120]))
    return hits


def unregistered(path: Path, facts):
    """이 편의 결론 자리에서 미등재인 (구역, 표기) 목록. 린터와 같은 판정을 쓴다."""
    md = path.read_text(encoding="utf-8")
    out = []
    for zone, text, _ in L.conclusion_zones(md):
        clean = L.strip_noise(text)
        for m in L.TOKEN.finditer(clean):
            val, unit = m.group(1), m.group(2) or ""
            if not L.is_claim(val, unit):
                continue
            if L.norm(val) in facts:
                continue
            out.append((zone, (val + unit).strip()))
    # 같은 구역·같은 표기의 중복은 한 번만
    seen, uniq = set(), []
    for z, t in out:
        if (z, t) in seen:
            continue
        seen.add((z, t))
        uniq.append((z, t))
    return md, uniq


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 값이 실제로 있는 줄을 찾는다 (린터는 구역 시작만 준다) ──")
    md = "# 제목\n\n## 1. 핵심 요약\n\n2025년 공컨은 62,115TEU였다. 그 뒤 문장.\n"
    hits = find_lines(md, "62,115TEU")
    chk("줄을 찾는다", [h[0] for h in hits], [5])
    chk("문장만 잘라 온다", hits[0][1], "2025년 공컨은 62,115TEU였다.")
    chk("없는 값은 빈 목록", find_lines(md, "99,999TEU"), [])

    print("── 인수시험: 문장이 창을 말하는가 ──")
    chk("연도가 있으면 표지", bool(WINDOW_HINTS.search("2025년 공컨은")), True)
    chk("연간도 표지", bool(WINDOW_HINTS.search("연간 누계")), True)
    chk("아무 창도 없으면 표지 없음", bool(WINDOW_HINTS.search("그 값은 크다")), False)

    print("── 인수시험: 표 행은 통째로 둔다 (창이 머리행에 있다) ──")
    row = "| 1월 | 90,346 | 291,000 | 31.0% |"
    chk("표 행이 안 쪼개진다", sentences(row), [row])

    print("── 인수시험: 원시 데이터 조회 ──")
    files = load_data_files()
    chk("볼 CSV 가 있다", len(files) > 0, True)
    hits = search_data("282", [ROOT / "analysis" / "terminal_monthly.csv"])
    chk("**공표 합계 282 를 CSV 에서 찾는다** (창은 조회지 추정이 아니다)",
        any("2026-07" in h[2] for h in hits), True)
    chk("없는 값은 안 찾아온다",
        search_data("999999", [ROOT / "analysis" / "terminal_monthly.csv"]), [])

    print("── 인수시험: 미등재 판정이 린터와 같은가 ──")
    # **특정 편이 더럽다고 박지 않는다.** 처음엔 「#01 은 미등재가 있다」로 썼는데,
    # #01 을 깨끗이 만들자 **내 시험이 깨졌다** — 일시적 상태를 불변식으로 박은 것이고
    # 사고 53과 같은 얼굴이다(픽스처에 절대값을 박으면 기준 변경을 시험이 막는다).
    # 그래서 **기전**을 친다: 대장에 없는 값을 지어 넣은 픽스처가 잡히는가.
    import tempfile
    facts = L.load_facts()
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "fx.md"
        f.write_text("# 제목\n\n## 1. 핵심 요약\n\n값은 123,456TEU 였다.\n",
                     encoding="utf-8")
        _, u = unregistered(f, facts)
        chk("대장에 없는 값을 잡는다", [t for _, t in u], ["123,456TEU"])
        f.write_text("# 제목\n\n## 1. 핵심 요약\n\n값은 991,170TEU 였다.\n",
                     encoding="utf-8")
        _, u2 = unregistered(f, facts)
        chk("등재된 값은 안 잡는다 (991,170 은 대장에 있다)", u2, [])
        f.write_text("# 제목\n\n## 1. 핵심 요약\n\n2025년은 12월까지다.\n", encoding="utf-8")
        _, u3 = unregistered(f, facts)
        chk("맨 정수는 주장이 아니다", u3, [])
    # 실물은 **린터와 같은 판정을 내는가**만 본다 — 몇 건인지는 안 박는다.
    for name in ("report_07_공컨테이너_표본외검증.md", "report_01_공컨테이너_물동량.md"):
        p = REPORTS / name
        if not p.exists():
            continue
        _, u = unregistered(p, facts)
        lint_warns = [w for w in L.lint(p, facts)[1] if "미등재" in w]
        chk("%s — 린터 미등재 수와 맞는다" % name[:12],
            len(u) == len({w.split("'")[1] for w in lint_warns}), True)

    print("── 인수시험: 대장 대조가 린터 블록 밖까지 본다 ──")
    # **이 시험이 곧 사고의 재현이다.** `SICT` 행은 비수치 정본 절에 있어
    # `load_facts()` 로는 안 보인다 — 안 보이는 곳을 안 보면 같은 일이 또 난다.
    rows = ledger_rows(["SICT", "SNCT", "존재하지않는이름XYZ"])
    chk("비수치 절의 SICT 를 찾는다", bool(rows["SICT"]), True)
    chk("린터 블록의 SNCT 도 찾는다", bool(rows["SNCT"]), True)
    chk("없는 이름은 빈 목록", rows["존재하지않는이름XYZ"], [])
    # `load_facts()` 는 값 칸에서 숫자를 못 찾으면 그 행을 통째로 건너뛴다(대장 「비수치 정본」 주석).
    # **`SICT` 정본 행이 바로 그런 행이다** — 그래서 이 대조는 원문 줄을 직접 읽어야 한다.
    chk("SICT 정본 행을 줄로 잡는다",
        any(r.startswith("| SICT |") for _, r in rows["SICT"]), True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="대장 미등재 값의 작업 목록 — 창을 추정하지 않고 찾아 온다.")
    ap.add_argument("--report", default=None, help="파일명 일부 (예: report_01)")
    ap.add_argument("--value", default=None, help="이 값의 출처만 추적")
    ap.add_argument("--names", nargs="+", default=None,
                    help="선커밋 전에 — 다룰 이름이 대장에 이미 행을 갖고 있는지 전수로")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    if a.names:
        rows = ledger_rows(a.names)
        have = [n for n in a.names if rows[n]]
        print("== 대장 대조 — 선커밋을 쓰기 전에 ==")
        print("  이름 %d개 · 대장에 행이 있는 이름 %d개 · 없는 이름 %d개"
              % (len(a.names), len(have), len(a.names) - len(have)))
        for n in a.names:
            if rows[n]:
                print("\n  [%s] 대장 %d행" % (n, len(rows[n])))
                for ln, row in rows[n]:
                    print("    FACTS.md:%d  %s" % (ln, row[:200]))
            else:
                print("\n  [%s] 대장에 없다 — **없다는 것도 정보다**" % n)
        print("\n  **행이 있으면 읽고 나서 선커밋을 쓴다.** 선커밋은 blob 이 증거라 한 글자도 못 고친다 —")
        print("  **안 본 채 적은 것이 그대로 굳는다**(#11 §2 정정 · 2026-09-11).")
        print("  **이 도구는 읽었는지를 검사하지 않는다.** 앞에 놓아 줄 뿐이고, 읽는 것은 사람이 한다.")
        return 0

    facts = L.load_facts()
    files = load_data_files()

    if a.value:
        print("== 값 추적: %s ==" % a.value)
        for p in sorted(REPORTS.glob("*.md")):
            md = p.read_text(encoding="utf-8")
            for ln, s in find_lines(md, a.value):
                print("  %s L%d" % (p.name, ln))
                print("      %s" % s[:170])
        hits = search_data(a.value, files)
        print("  -- 원시 데이터 --" if hits else "  -- 원시 데이터에 없다 (계산값일 수 있다) --")
        for f, col, ctx in hits[:12]:
            print("      %s  [%s]  %s" % (f, col, ctx))
        return 0

    targets = [p for p in sorted(REPORTS.glob("*.md"))
               if not a.report or a.report in p.name]
    print("== 대장 미등재 작업 목록 ==")
    print("  **등재하지 않는다. 재료만 낸다** — 자동 등재는 곧 자동 추정이다(사고 22).")
    total = 0
    for p in targets:
        md, items = unregistered(p, facts)
        if not items:
            print("\n[%s]  미등재 없음" % p.name)
            continue
        print("\n[%s]  미등재 %d건" % (p.name, len(items)))
        for zone, tok in items:
            total += 1
            lines = find_lines(md, tok)
            hits = search_data(tok, files)
            said = any(WINDOW_HINTS.search(s) for _, s in lines)
            mark = "창 문장에 있음" if said else "**문장에 창 표지 없음**"
            print("  · %-12s %-12s %s · 원시 %s"
                  % (zone, tok, mark, ("%d곳" % len(hits)) if hits else "**없음**"))
            for ln, s in lines[:2]:
                print("       L%-4d %s" % (ln, s[:140]))
            for f, col, ctx in hits[:2]:
                print("       ↳ %s [%s] %s" % (f, col, ctx[:100]))
    print("\n== 합계 미등재 %d건 ==" % total)
    print("  창이 문장에 있고 원시 데이터에도 있는 값부터 등재한다 — **그건 추정이 아니다.**")
    print("  둘 다 비면 **등재하지 않고 비운 채로 둔다.** 비어 있는 것이 사실이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

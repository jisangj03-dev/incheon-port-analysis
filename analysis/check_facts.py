# -*- coding: utf-8 -*-
"""대장 자체를 검사한다 — **린터가 읽는 표가 스스로 온전한가.**

왜 있는가
---------
`lint_publish.py` 는 대장을 **믿고** 본문을 검사한다. 그런데 **대장 자체를 검사하는 것은
아무것도 없었다.** 2026-08-29에 미등재 96건을 갚으며 50여 행을 넣었고, 그러자 두 가지가
드러났다 — 둘 다 **조용한** 결함이다.

  ① **`3.9배` 를 두 번 등재했다.** 이미 있는 행을 못 보고 새로 넣었고,
     `load_facts()` 는 나중 행으로 **덮는다.** 앞 행의 창은 사라졌는데 아무도 모른다.
  ② **값 칸에 숫자가 없는 행을 넣었다.** `load_facts()` 는 그런 행을 **통째로 건너뛴다.**
     표 안에 있으면서 **아무것도 강제되지 않는 행**이 됐다 —
     **장치의 존재는 검사의 수행이 아니다**(사고 26). 다음 사람은 「대장에 있으니
     검사된다」고 읽는다.

**둘 다 대장을 늘릴 때만 생긴다.** 부채를 안 갚는 동안에는 영원히 안 보인다.

무엇을 보는가
-------------
  · **중복** — 같은 (값, 단위)가 두 행에 있으면 뒤가 앞을 덮는다. **창이 다르면 특히 위험하다.**
  · **읽히지 않는 행** — 값 칸에서 숫자를 못 뽑는 행. 표 안에 있으나 강제되지 않는다.
  · **칸 수** — 5칸(값·창·지위·출처·비고)이 아닌 행.
  · **지위** — 4등급(검증·관측·참고·미확인) 밖의 값.
  · **창** — 비었거나 지나치게 짧은 창. §3-2 「창 없는 등재 금지」.

  python analysis/check_facts.py
  python analysis/check_facts.py --strict     # 문제가 있으면 종료 1
  python analysis/check_facts.py --selftest

**기본이 경고인 이유.** `check_review_log.py`·`check_generated.py` 와 같은 자리다 —
막히는 것은 사람의 손이고, 차단 승격은 운영자 판단이다.

**§4 정지선표에 안 넣는다.** 이 검사가 집행하는 것은 §4가 아니라 **§3-2 등재 규칙**이다.

닿지 않는 곳
------------
1. **창이 맞는지는 안 본다.** 「2025년 연간」이라 적혀 있으면 그대로 믿는다 —
   그게 진짜 그 값의 창인지는 원시 데이터 대조의 일이고, 사람이 한다.
2. **비수치 정본 절은 안 본다.** 거기는 애초에 린터가 안 읽는 자리다.
3. **값이 실제로 재현되는지는 안 본다.** 이 검사는 **대장의 형식과 일관성**만 본다.
"""

import argparse
import collections
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "analysis"))
import lint_publish as L  # noqa: E402

FACTS = os.path.join(ROOT, "docs", "FACTS.md")
GRADES = {"검증", "관측", "참고", "미확인"}
MIN_WINDOW = 6          # 창이 이보다 짧으면 창이라 보기 어렵다


def rows_of(text: str):
    """린터가 읽는 구간의 표 행만. (줄번호, 칸들)"""
    if "<!-- LINT-TABLE-START -->" not in text:
        return []
    head, _, rest = text.partition("<!-- LINT-TABLE-START -->")
    body, _, _ = rest.partition("<!-- LINT-TABLE-END -->")
    base = head.count("\n") + 1
    out = []
    for i, line in enumerate(body.splitlines()):
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if cols and cols[0] == "값":
            continue
        out.append((base + i, cols))
    return out


def audit(rows):
    """문제 목록을 낸다. 각 항목: (종류, 줄번호, 설명)."""
    problems = []
    keys = collections.defaultdict(list)
    for ln, cols in rows:
        if len(cols) < 4:
            problems.append(("칸수", ln, "칸이 %d개다 (값·창·지위·출처 최소 4)" % len(cols)))
            continue
        val, win, grade = cols[0], cols[1], cols[2].replace("**", "").strip()
        m = L.TOKEN.search(val)
        if not m:
            problems.append(("안읽힘", ln,
                             "값 칸에서 숫자를 못 뽑는다 — **린터가 이 행을 건너뛴다**: %s"
                             % val[:40]))
            continue
        keys[(L.norm(m.group(1)), m.group(2) or "")].append((ln, val, win))
        if grade not in GRADES:
            problems.append(("지위", ln, "지위가 4등급 밖이다: %r" % grade))
        if len(win) < MIN_WINDOW:
            problems.append(("창", ln, "창이 너무 짧다 (§3-2 창 없는 등재 금지): %r" % win))
    for k, hits in keys.items():
        if len(hits) > 1:
            wins = {h[2] for h in hits}
            why = "창이 다르다 — **뒤가 앞을 덮는다**" if len(wins) > 1 else "창이 같다 (그래도 한 행으로)"
            problems.append(("중복", hits[0][0],
                             "(%s%s) 가 %d행에 있다 [%s] — %s"
                             % (k[0], k[1], len(hits),
                                ", ".join("L%d" % h[0] for h in hits), why)))
    return problems, keys


# ── 인수시험 ────────────────────────────────────────────────────────────────

FIX_OK = """앞
<!-- LINT-TABLE-START -->

| 값 | 창 | 지위 | 출처 | 비고 |
|---|---|---|---|---|
| 1.5배 | 2025년 연간 · 수출÷수입 | 관측 | 재현 | |
| 1.5%p | 2025년 연간 · 비중 폭 | 관측 | 재현 | |

<!-- LINT-TABLE-END -->
"""

FIX_BAD = """앞
<!-- LINT-TABLE-START -->

| 값 | 창 | 지위 | 출처 | 비고 |
|---|---|---|---|---|
| 3.9배 | 2022~2025 월별 최소 | 관측 | #04 | |
| 3.9배 | 2023-12 단월 · 수출÷수입 | 관측 | 재계산 | |
| SICT | 폐쇄된 부두 | 관측 | 원문 | |
| 7배 | 짧음 | 이상한지위 | 재현 | |

<!-- LINT-TABLE-END -->
"""


def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 깨끗한 대장은 조용하다 ──")
    p, keys = audit(rows_of(FIX_OK))
    chk("문제 0건", p, [])
    chk("**같은 숫자의 다른 단위는 중복이 아니다** (1.5배 · 1.5%p)", len(keys), 2)

    print("── 인수시험: 더러운 대장을 잡는다 (양방향) ──")
    p, _ = audit(rows_of(FIX_BAD))
    kinds = sorted({k for k, _, _ in p})
    chk("네 종류를 다 잡는다", kinds, ["안읽힘", "중복", "지위", "창"])
    dup = [x for x in p if x[0] == "중복"][0]
    chk("**중복이 창이 다르다고 말한다**", "뒤가 앞을 덮는다" in dup[2], True)
    unread = [x for x in p if x[0] == "안읽힘"][0]
    chk("안읽힘이 이유를 말한다", "린터가 이 행을 건너뛴다" in unread[2], True)

    print("── 인수시험: 실물 대장 ──")
    text = io.open(FACTS, encoding="utf-8").read()
    rows = rows_of(text)
    chk("행을 읽는다", len(rows) > 50, True)
    chk("머리행은 안 센다", any(c[0] == "값" for _, c in rows), False)
    chk("`<!-- LINT-TABLE-END -->` 뒤(비수치 절)는 안 본다",
        any("SICT" in c[0] for _, c in rows), False)
    probs, _ = audit(rows)
    chk("**지금 대장은 깨끗하다**", probs, [])

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="정본 대장 자체의 형식·일관성을 본다 (§3-2).")
    ap.add_argument("--strict", action="store_true", help="문제가 있으면 종료 1")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    text = io.open(FACTS, encoding="utf-8").read()
    rows = rows_of(text)
    problems, keys = audit(rows)

    print("== 정본 대장 검사 ==")
    print("  린터가 읽는 행 %d · 서로 다른 (값,단위) %d종" % (len(rows), len(keys)))
    if not problems:
        print("\n대장이 깨끗하다 — 중복 없음 · 전 행이 읽힘 · 지위 4등급 안 · 창 있음.")
        return 0

    out = sys.stderr
    print("", file=out)
    print("대장에 문제 %d건." % len(problems), file=out)
    for kind, ln, why in sorted(problems, key=lambda x: (x[0], x[1])):
        print("  [%s] FACTS.md L%d — %s" % (kind, ln, why), file=out)
    print("", file=out)
    print("  **전부 대장을 늘릴 때만 생기는 종류다.** 부채를 안 갚는 동안에는 안 보인다.", file=out)
    if a.strict:
        print("  --strict 라 여기서 멈춘다.", file=out)
        return 1
    print("  경고만 하고 통과시킨다. 막으려면 --strict.", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

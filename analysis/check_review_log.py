# -*- coding: utf-8 -*-
"""검수 게이트 — **새 편이 검수 기록 없이 push 되는 것**을 push 순간에 말한다.

왜 있는가
---------
2026-08-27 실측. `docs/STATUS.md` 「다음 할 일」을 위에서부터 따르면 이렇게 된다 —

  1번  `git push`                                   ← 미push 42건을 전부 민다
  2번  `review_pick.py report_08 … --log` 후 push   ← #08 검수

**`report_08`은 그 42건 안에 있다(A · 신규).** 즉 **1번이 2번을 앞질러 #08을 검수 없이 발행한다.**
지침 §1.4 1층은 「`docs/검수기록.md` 해당 편 기록 **1행 이상**」을 편마다 요구하고,
§2.3은 `①통독 → ②수치 대조 → ③push` 순서를 정한다. 기록 없이 나가면 §2.2 표기 블록이
**일어나지 않은 검수를 증언한다** — 표기 의무가 막으려던 실패 그 자체다.

**STATUS의 순서는 고쳤다. 그런데 순서는 문서고, 문서는 또 틀린다**(§0-3: 사람이 나르는 규칙은 유실된다).
그래서 같은 판정을 push 순간에 한 번 더 친다. 사고 26의 원칙대로 **장치가 실제로 발화하는지**는
`--selftest`가 양방향으로 확인한다(사고 34).

무엇을 보는가
-------------
push 범위에서 **새로 추가된(A) `reports/*.md`** 만 본다. 그 편의 파일명이
`docs/검수기록.md` 어딘가에 있는지 문자열로 확인한다. 그뿐이다.

  python analysis/check_review_log.py                  # origin/main..HEAD. 경고(종료 0)
  python analysis/check_review_log.py --strict         # 미기록이 있으면 종료 1
  python analysis/check_review_log.py --range A..B
  python analysis/check_review_log.py --hook           # git pre-push stdin에서 범위를 읽는다
  python analysis/check_review_log.py --selftest

**기본이 경고인 이유.** 이 훅이 막는 대상은 **운영자의 손**이다. `check_status_fresh.py`가
같은 이유로 경고를 기본으로 뒀고 「차단으로 올릴지는 운영자 판단」이라 적었다 — 같은 자리에 둔다.
차단은 `--strict`.

**§4 정지선표에 안 넣는 이유.** 이 검사가 집행하는 것은 §4가 아니라 **§1.4 1층**이다.
`stopline_table.py`의 표는 「지침 §4의 조항 문면 ↔ 기전」 짝이므로, 여기에 §1.4 가드를
끼우면 그 표가 거짓이 된다. 그래서 `정지선-집행/명제/한계` 3줄을 **일부러 선언하지 않는다.**

닿지 않는 곳
------------
1. **수정된(M) 보고서는 안 본다.** 오탈자 정정까지 재검수를 요구하면 §3-11(형식 변경은 정정
   사유가 아니다)과 어긋나고 오탐이 난다. **그래서 발행본 개정에 대한 재검수는 사람이 판단한다.**
2. **기록의 내용이 맞는지는 안 본다.** 파일명이 한 줄 있으면 통과한다 —
   `check_status_fresh.py`의 한계 ①과 같은 종류다. **한 줄을 손으로 적으면 통과한다.**
3. **#01~#06은 애초에 기록이 없다**(검수기록 장치보다 먼저 발행됐다). A만 보므로 안 걸린다.
   바꿔 말하면 **이 검사는 소급하지 않는다.**
"""

import argparse
import io
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "docs", "검수기록.md")
ZERO = "0" * 40


# ── 순수 함수 셋. --selftest 는 이것들을 친다 ────────────────────────────────

def parse_name_status_z(payload):
    """`git diff --name-status -z` 출력에서 (상태, 경로) 목록을 낸다.

    `-z` 를 쓰는 이유: 파일명이 한글이라 기본 출력은 `"reports/report_08_\\352\\264\\200…"`
    처럼 **따옴표+8진 이스케이프**로 나온다. 그것을 되돌리는 코드는 그 자체가 결함원이다.
    """
    parts = [p for p in payload.split("\0") if p != ""]
    out = []
    i = 0
    while i < len(parts):
        status = parts[i]
        if status[:1] in ("R", "C"):  # 이름 변경/복사는 old·new 둘을 뒤에 붙인다
            if i + 2 >= len(parts):
                break
            out.append((status, parts[i + 2]))
            i += 3
        else:
            if i + 1 >= len(parts):
                break
            out.append((status, parts[i + 1]))
            i += 2
    return out


def added_reports(entries):
    """새로 추가된 보고서만 고른다. 수정(M)·삭제(D)는 보지 않는다(닿지 않는 곳 1)."""
    out = []
    for status, path in entries:
        if not status.startswith("A"):
            continue
        norm = path.replace("\\", "/")
        if norm.startswith("reports/") and norm.endswith(".md"):
            out.append(os.path.basename(norm))
    return sorted(set(out))


def unlogged(names, log_text):
    """검수기록에 파일명이 안 보이는 편을 낸다."""
    return [n for n in names if n not in log_text]


# ── git 접점 ────────────────────────────────────────────────────────────────

def git(args):
    return subprocess.run(
        ["git"] + args, cwd=ROOT, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
    ).stdout


def range_from_hook_stdin(payload):
    """pre-push stdin: `<local ref> <local sha> <remote ref> <remote sha>` 줄들.

    remote_sha 가 0으로 채워져 있으면 원격에 그 브랜치가 없다는 뜻이다 — 전량이 신규다.
    """
    ranges = []
    for line in payload.splitlines():
        f = line.split()
        if len(f) != 4:
            continue
        local_sha, remote_sha = f[1], f[3]
        if local_sha == ZERO:  # 삭제 push
            continue
        ranges.append(local_sha if remote_sha == ZERO else "%s..%s" % (remote_sha, local_sha))
    return ranges


def entries_for(rev_range):
    payload = git(["diff", "--name-status", "-z", rev_range, "--", "reports/"])
    return parse_name_status_z(payload)


# ── 인수시험 (사고 26·34 — 발화하는지, 그리고 안 해야 할 때 조용한지) ────────

Z_ADDED = "A\0reports/report_08_관세청_인천항_수출입신고.md\0"
Z_MIXED = ("A\0reports/report_09_새편.md\0"
           "M\0reports/report_07_공컨테이너_표본외검증.md\0"
           "R100\0reports/old.md\0reports/report_10_이름바뀜.md\0"
           "D\0reports/report_00_지워짐.md\0")
LOG_WITH_07 = "| 2026-08-26 03:21 | report_07_공컨테이너_표본외검증.md | 48/124 | 50,336 | :63 |\n"


def selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-46s %s" % ("OK  " if good else "FAIL", label, "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: -z 파싱 ──")
    check("A 1건", parse_name_status_z(Z_ADDED),
          [("A", "reports/report_08_관세청_인천항_수출입신고.md")])
    check("A·M·R·D 섞임 → 4건", len(parse_name_status_z(Z_MIXED)), 4)
    check("R은 새 이름을 든다", parse_name_status_z(Z_MIXED)[2],
          ("R100", "reports/report_10_이름바뀜.md"))
    check("잘린 입력에도 안 죽는다", parse_name_status_z("A\0"), [])

    print("── 인수시험: A만 고른다 ──")
    check("M·D는 빠진다", added_reports(parse_name_status_z(Z_MIXED)), ["report_09_새편.md"])
    check("reports/ 밖은 빠진다", added_reports([("A", "docs/STATUS.md")]), [])

    print("── 인수시험: 발화 (양방향) ──")
    # ① 걸려야 한다 — 기록에 없는 새 편
    check("기록 없음 → 1건 잡는다",
          unlogged(["report_08_관세청_인천항_수출입신고.md"], LOG_WITH_07),
          ["report_08_관세청_인천항_수출입신고.md"])
    # ② 조용해야 한다 — 기록이 있으면 아무 말도 안 한다. 이게 없으면 「항상 FAIL」도 통과한다
    check("기록 있음 → 조용하다",
          unlogged(["report_07_공컨테이너_표본외검증.md"], LOG_WITH_07), [])
    check("새 편 없음 → 조용하다", unlogged([], LOG_WITH_07), [])

    print("── 인수시험: pre-push stdin 범위 ──")
    check("정상 범위", range_from_hook_stdin("refs/heads/main aaa refs/heads/main bbb"),
          ["bbb..aaa"])
    check("원격에 브랜치 없음 → 전량", range_from_hook_stdin("refs/heads/main aaa refs/heads/main " + ZERO),
          ["aaa"])
    check("브랜치 삭제 push → 건너뛴다",
          range_from_hook_stdin("(delete) %s refs/heads/x bbb" % ZERO), [])

    print("── 인수시험: 실물 ──")
    check("검수기록.md 가 제자리에 있다", os.path.exists(LOG), True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="새 편이 검수 기록 없이 push 되는지 본다 (지침 §1.4 1층).")
    ap.add_argument("--range", dest="rev_range", default=None, help="예: origin/main..HEAD")
    ap.add_argument("--hook", action="store_true", help="git pre-push stdin에서 범위를 읽는다")
    ap.add_argument("--strict", action="store_true", help="미기록이 있으면 종료코드 1")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.hook:
        ranges = range_from_hook_stdin(sys.stdin.read())
        if not ranges:
            return 0
    elif a.rev_range:
        ranges = [a.rev_range]
    else:
        if not git(["rev-parse", "--verify", "--quiet", "origin/main"]).strip():
            print("origin/main 이 없다 — 볼 범위가 없다. 통과.")
            return 0
        ranges = ["origin/main..HEAD"]

    entries = []
    for r in ranges:
        entries += entries_for(r)
    names = added_reports(entries)

    log_text = io.open(LOG, encoding="utf-8").read() if os.path.exists(LOG) else ""
    missing = unlogged(names, log_text)

    if not names:
        print("검수 게이트: 이 범위에 새 편이 없다. 통과.")
        return 0
    if not missing:
        print("검수 게이트: 새 편 %d건 전부 `docs/검수기록.md`에 있다. 통과." % len(names))
        return 0

    out = sys.stderr
    print("", file=out)
    print("검수 게이트 — 새 편 %d건에 검수 기록이 없다 (지침 §1.4 1층 · §2.3)." % len(missing), file=out)
    for n in missing:
        print("  · %s" % n, file=out)
    print("", file=out)
    print("  기록이 없는 편은 §2.2 표기 블록을 달 수 없다 — 일어나지 않은 검수를 증언하게 된다.", file=out)
    print("  검수는 이 명령이 연다(추첨은 결정론이다 — 다시 돌려도 쉬운 값이 안 나온다):", file=out)
    for n in missing:
        print("    python analysis/review_pick.py reports/%s --log" % n, file=out)
    print("", file=out)
    if a.strict:
        print("  --strict 라 여기서 멈춘다.", file=out)
        return 1
    print("  경고만 하고 통과시킨다. 막으려면 --strict.", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""셈 검사 — **문장 속의 수가 실제와 맞는가.**

왜 있는가
---------
이 저장소의 검사기는 **값**을 잘 본다. `lint_publish.py` 가 결론 자리 수치를 대장과
맞대고, `check_facts.py` 가 그 대장을 보고, `check_generated.py` 가 생성물의 신선도를 본다.

**그런데 산문에 적힌 수는 아무도 안 본다.** 「보고서 8편」·「장치 9종」 같은 것.
그리고 그 수는 **매번 낡는다** — 늘릴 때 목록만 늘리고 세는 수를 안 고치기 때문이다.

  · 2026-08-29 — STATUS 의 「장치 9종」이 오래 그 상태였다(목록은 20개였다).
  · 2026-08-30 — 첫 화면이 「보고서 8편」인 채로 9편이 됐다.
  · 2026-08-30 — **그 둘을 고친 바로 다음 라운드에 「26종」이 24개 목록 위에 서 있었다.**

**사고 31의 얼굴이다** — 같은 사실이 두 자리에 있고 한쪽만 갱신된다. 다만 값이 아니라
**문장**이라 기존 검사기가 안 본다(사고 80).

무엇을 보는가
-------------
**「어디에 적힌 수」와 「무엇을 세면 그 수가 나오는가」를 짝으로 둔다.**
짝을 못 만드는 수는 여기서 안 본다 — 세는 방법이 애매한 수를 넣으면 오탐이 나고,
**오탐을 내는 검사는 무시당한다**(§3-5).

  python analysis/check_counts.py            # 경고. 종료 0
  python analysis/check_counts.py --strict   # 어긋나면 종료 1
  python analysis/check_counts.py --hook     # pre-push 에서 조용히
  python analysis/check_counts.py --selftest

닿지 않는 곳
------------
· **여기 등록한 넷만 본다.** 산문의 모든 수를 세는 것은 불가능하고, 시도하면 오탐만 는다.
  **새로 「N개」를 적을 때 여기 짝을 같이 넣는 것이 규율이다.**
· **세는 기준이 바뀌면 이 검사도 같이 틀린다.** 예컨대 「장치」에 무엇을 포함할지는
  판단이고, 이 파일은 **STATUS 목록에 이름이 적힌 것**만 센다 — 그것이 유일하게
  기계로 셀 수 있는 기준이기 때문이다.
· **수가 맞다고 문장이 맞는 것은 아니다.** 이 검사는 셈만 본다.
"""

import argparse
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
HUB = os.path.join(ROOT, "..", "jisangj03-dev.github.io")


def read(*parts):
    p = os.path.join(*parts)
    return io.open(p, encoding="utf-8").read() if os.path.exists(p) else None


# ── 짝 넷 ───────────────────────────────────────────────────────────────────

def c_devices():
    """STATUS 「장치 — N종」 ↔ 그 절에 이름이 적힌 `.py` 개수."""
    s = read(ROOT, "docs", "STATUS.md")
    if s is None:
        return None, None, "docs/STATUS.md 가 없다"
    m = re.search(r"장치 — (\d+)종", s)
    if not m:
        return None, None, "「장치 — N종」 문구를 못 찾았다"
    i = s.index(m.group(0))
    tail = s[i:]
    # 목록은 첫 하위 항목(`- **`) 전까지다. 그 뒤는 설명이라 이름이 또 나온다.
    seg = tail[:tail.index("\n- **")] if "\n- **" in tail else tail[:2000]
    names = set(re.findall(r"`([a-z_0-9]+\.py)", seg))
    return int(m.group(1)), len(names), "STATUS 목록의 고유 이름"


def c_devices_real():
    """STATUS 장치 목록 ↔ **실물.**

    `c_devices` 는 **STATUS 의 수**와 **STATUS 의 목록**을 맞댄다 — 양쪽이 같은 파일이라
    **순환이다.** 새 장치를 만들고 STATUS 에 안 적으면 수와 목록이 **사이좋게 함께 틀리고**
    그 검사는 통과를 낸다. 실제로 그렇게 통과했다 — 장치가 27 → 29 가 된 라운드에.

    **사고 83 의 처분(「목록을 안 들고 찾는다」)이 부트블록에는 적용됐는데
    여기에는 안 돼 있었다.** 같은 함정이 한 층 위에 남아 있었다는 뜻이다(사고 87).

    그래서 이 짝은 **디스크를 본다.** 방향은 하나다 —
    **「있는데 안 적힌 것」**을 찾는다. 반대 방향(적혔는데 없는 것)은
    `--selftest` 가 없는 도구도 STATUS 가 정당하게 들 수 있어 오탐이 된다.
    """
    s = read(ROOT, "docs", "STATUS.md")
    if s is None:
        return None, None, "docs/STATUS.md 가 없다"
    m = re.search(r"장치 — (\d+)종", s)
    if not m:
        return None, None, "「장치 — N종」 문구를 못 찾았다"
    i = s.index(m.group(0))
    tail = s[i:]
    seg = tail[:tail.index("\n- **")] if "\n- **" in tail else tail[:2000]
    listed = set(re.findall(r"`([a-z_0-9]+\.py)", seg))

    # **`analysis/` 직하만 본다. `analysis/probe/` 는 안 본다.**
    #   STATUS 목록은 「`--selftest` 를 가진 스크립트」가 아니라 **「상시 장치」**다 —
    #   `review_pick.py`·`stopline_table.py` 는 `--selftest` 가 없어도 정당하게 실려 있다.
    #   프로브는 **한 편을 위해 한 번 도는 증거 스크립트**라 상시 장치가 아니다.
    #   (실측 2026-08-31: `probe/` 의 `--selftest` 보유는 `probe_14_year_floor.py` 하나.
    #    `boot_check` 는 그것도 돌린다 — **안 도는 것이 아니라 이 목록의 대상이 아니다.**)
    d = os.path.join(ROOT, "analysis")
    found = set()
    for fn in os.listdir(d) if os.path.isdir(d) else []:
        if not fn.endswith(".py"):
            continue
        try:
            src = io.open(os.path.join(d, fn), encoding="utf-8").read()
        except Exception:
            continue
        if '"--selftest"' in src or "'--selftest'" in src:
            found.add(fn)
    # 세는 쪽 둘은 목록에 없어도 된다.
    found -= {"check_counts.py", "boot_check.py"}
    missing = sorted(found - listed)
    how = "실물 %d개 중 STATUS 미기재 %d개%s" % (
        len(found), len(missing), (" — " + ", ".join(missing)) if missing else "")
    return len(found), len(found) - len(missing), how


def c_reports_home():
    """첫 화면 「보고서 N편」 ↔ `reports/report_*.md` 개수."""
    s = read(HUB, "index.md")
    if s is None:
        return None, None, "허브 index.md 가 없다"
    m = re.search(r"보고서 (\d+)편", s)
    if not m:
        return None, None, "「보고서 N편」 문구를 못 찾았다"
    d = os.path.join(ROOT, "reports")
    n = len([f for f in os.listdir(d)
             if f.startswith("report_") and f.endswith(".md")]) if os.path.isdir(d) else 0
    return int(m.group(1)), n, "reports/report_*.md"


def c_reports_index():
    """허브 보고서 목록의 `| #NN |` 행 ↔ 발행본 개수."""
    s = read(HUB, "reports", "index.md")
    if s is None:
        return None, None, "허브 reports/index.md 가 없다"
    rows = len(re.findall(r"(?m)^\|\s*#\d+\s*\|", s))
    d = os.path.join(ROOT, "reports")
    n = len([f for f in os.listdir(d)
             if f.startswith("report_") and f.endswith(".md")]) if os.path.isdir(d) else 0
    return rows, n, "reports/report_*.md"


def c_incident_numbers():
    """사고기록의 번호가 **1부터 빠짐없이 이어지는가.**

    그 파일이 스스로 「번호는 재사용하지 않는다」고 적는다. 재사용은 물론이고
    **건너뛰기도 문제다** — 다음 사람이 「그 번호 사고가 어디 갔지」를 찾게 된다.
    """
    s = read(ROOT, "docs", "사고기록.md")
    if s is None:
        return None, None, "docs/사고기록.md 가 없다"
    nums = [int(x) for x in re.findall(r"(?m)^\*\*(\d+)\.", s)]
    if not nums:
        return None, None, "사고 번호를 못 찾았다"
    want = list(range(1, max(nums) + 1))
    return sorted(nums), want, "1..%d 연속 · 중복 없음" % max(nums)


PAIRS = (
    ("STATUS 장치 수", c_devices),
    ("STATUS 장치 목록 ↔ 실물", c_devices_real),
    ("첫 화면 보고서 편수", c_reports_home),
    ("허브 목록 행수", c_reports_index),
    ("사고 번호 연속", c_incident_numbers),
)


def run():
    out = []
    for label, fn in PAIRS:
        try:
            said, real, how = fn()
        except Exception as e:
            out.append((label, None, None, "%s: %s" % (type(e).__name__, e), None))
            continue
        if said is None:
            # **못 센 것을 통과로 세지 않는다**(사고 26).
            out.append((label, None, None, how, None))
            continue
        out.append((label, said, real, how, said == real))
    return out


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 어긋남을 잡는가 · 맞는 것을 안 잡는가 (사고 39) ──")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        global ROOT, HUB
        keep_r, keep_h = ROOT, HUB
        try:
            os.makedirs(os.path.join(d, "docs"))
            os.makedirs(os.path.join(d, "reports"))
            hub = os.path.join(d, "hub")
            os.makedirs(os.path.join(hub, "reports"))
            ROOT, HUB = d, hub

            def w(p, t):
                io.open(os.path.join(d, p), "w", encoding="utf-8").write(t)

            # 장치 — 목록 둘인데 셋이라고 적는다.
            w("docs/STATUS.md",
              "### 검사·생성 장치 — 3종\n\n`a.py` · `b.py`\n\n- **딴 얘기** `c.py`\n")
            said, real, _ = c_devices()
            chk("장치 수 어긋남을 본다", (said, real), (3, 2))
            # 설명 절의 이름을 안 센다 — 세면 목록 밖이 섞인다.
            chk("목록 밖 이름은 안 센다", real, 2)

            w("docs/STATUS.md", "### 검사·생성 장치 — 2종\n\n`a.py` · `b.py`\n\n- **끝**\n")
            said, real, _ = c_devices()
            chk("맞으면 같다", said == real, True)

            # 보고서 — 파일 둘인데 셋이라고 적는다.
            for f in ("report_01_a.md", "report_02_b.md"):
                io.open(os.path.join(d, "reports", f), "w", encoding="utf-8").write("x")
            io.open(os.path.join(hub, "index.md"), "w", encoding="utf-8").write(
                "<dd>보고서 3편 · 정정 0건</dd>")
            said, real, _ = c_reports_home()
            chk("보고서 편수 어긋남을 본다", (said, real), (3, 2))

            io.open(os.path.join(hub, "reports", "index.md"), "w",
                    encoding="utf-8").write("| #02 | a |\n| #01 | b |\n")
            said, real, _ = c_reports_index()
            chk("목록 행수가 맞으면 같다", (said, real), (2, 2))

            # 사고 번호 — 3이 빠졌다.
            w("docs/사고기록.md", "**1.** 가\n**2.** 나\n**4.** 다\n")
            got, want, _ = c_incident_numbers()
            chk("번호 건너뛰기를 본다", (got, want), ([1, 2, 4], [1, 2, 3, 4]))
            w("docs/사고기록.md", "**1.** 가\n**2.** 나\n**3.** 다\n")
            got, want, _ = c_incident_numbers()
            chk("빠짐없으면 같다", got == want, True)
            # **중복도 잡힌다** — 정렬 목록이 기대와 달라진다.
            w("docs/사고기록.md", "**1.** 가\n**2.** 나\n**2.** 또 나\n")
            got, want, _ = c_incident_numbers()
            chk("번호 중복을 본다", got != want, True)

            # **없는 파일을 통과로 세지 않는다**(사고 26).
            os.remove(os.path.join(d, "docs", "사고기록.md"))
            said, real, why = c_incident_numbers()
            chk("파일이 없으면 「모름」", (said, real), (None, None))
        finally:
            ROOT, HUB = keep_r, keep_h

    print("── 인수시험: 실물 ──")
    rows = run()
    # **수를 손으로 들지 않는다** — 짝이 늘 때마다 이 줄이 낡는다(사고 83·87).
    # 대신 **무엇을 보는지**를 묻는다. 그것은 짝이 늘어도 뜻이 안 변하고,
    # 짝이 **사라지면** 잡힌다 — 그쪽이 이 시험이 막아야 할 방향이다.
    chk("장치 목록을 실물과도 댄다", "STATUS 장치 목록 ↔ 실물" in [r[0] for r in rows], True)
    chk("첫 화면·허브·사고 번호를 본다",
        all(any(k in r[0] for r in rows)
            for k in ("첫 화면", "허브 목록", "사고 번호")), True)
    for label, said, real, how, okk in rows:
        mark = "일치" if okk else ("**모름**" if okk is None else "**어긋남**")
        print("  ·  %-22s %s" % (label, mark))
    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="문장 속의 수가 실제와 맞는지 본다.")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--hook", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    rows = run()
    bad = [r for r in rows if r[4] is False]
    unk = [r for r in rows if r[4] is None]

    if a.hook and not bad:
        return 0

    if not a.hook:
        print("== 셈 검사 ==")
        for label, said, real, how, okk in rows:
            if okk is None:
                print("  **모름**   %-22s %s" % (label, how))
            elif okk:
                print("  일치       %-22s %s" % (label, "적힌 것 = 센 것"))
            else:
                print("  **어긋남** %-22s 적힘 %s ≠ 센 것 %s  (%s)"
                      % (label, said, real, how))
        if unk:
            print("\n  **모름은 통과가 아니다**(사고 26).")

    if not bad:
        if not a.hook:
            print("\n어긋난 셈 0건.")
        return 0

    out = sys.stderr
    print("\n문장 속의 수가 실제와 어긋난다 — %d건." % len(bad), file=out)
    print("  **값이 아니라 문장이라 다른 검사기가 안 본다**(사고 80).", file=out)
    if a.strict:
        return 1
    print("  경고만 하고 통과시킨다. 막으려면 --strict.", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

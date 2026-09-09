# -*- coding: utf-8 -*-
"""세션 개시 검사 — **목록을 손으로 들고 있지 않는다.**

왜 있는가
---------
`CLAUDE.md` 3번이 「검사 장치가 실제로 발화하는지 확인한다」면서 명령 **여덟 줄**을
들고 있었다. 그런데 2026-08-31 기준 `--selftest` 를 가진 스크립트는 **26개**다.

**그 목록은 장치를 만들 때마다 낡는다.** 그리고 낡은 목록으로 「전부 쳤다」고 말하면
그것이 사고 26 이다 — **장치의 존재는 검사의 수행이 아니고, 목록의 존재는 목록의
완전함이 아니다.** 사고 81 에서 배운 것과 같다: **조심으로 안 되는 것은 장치로 막는다.**

그래서 이 파일은 **목록을 안 가진다. 찾는다.**

무엇을 하는가
-------------
1. `analysis/` 와 `analysis/probe/` 에서 `--selftest` 를 받는 스크립트를 **전부 찾아** 돌린다.
2. 상태 검사(앵커·훅·생성물·대장·접근성·셈·링크·린터)를 돌린다.
3. **한 줄로 판정**한다. 하나라도 실패하면 종료코드 1.

  python analysis/boot_check.py            # 전부
  python analysis/boot_check.py --quick    # 인수시험만 (상태 검사 생략)
  python analysis/boot_check.py --selftest # 이 파일 자신

닿지 않는 곳
------------
· **못 돌린 것을 통과로 세지 않는다**(사고 26). 시간 초과·예외는 「모름」이고,
  모름이 하나라도 있으면 판정은 「통과」가 아니다.
· **인수시험이 통과했다는 것이 그 장치가 옳다는 뜻은 아니다.** 그 시험이 무엇을
  치는지는 각 파일이 든다.
· **여기서 안 도는 것들이 있다** — 브라우저 연결(`check_browser.py` 는 전제만 본다),
  운영자 검수, push. 그건 사람의 자리다.
"""

import argparse
import io
import os
import re
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

OK, BAD, UNK = "통과", "**실패**", "**모름**"

# 소요 로그 — **일화 대신 계열**(사고 84). 추적하지 않는 로컬 파일이다.
# 스크립트마다 「시작」 줄과 「끝」 줄을 따로 적으므로, 멈춘 실행은 **시작만 있고 끝이 없는
# 마지막 줄**로 자기가 선 자리를 남긴다. 2026-09-03 한 세션에 600초 초과가 세 번 났는데
# 죽고 나면 어느 스크립트였는지 흔적이 없었다 — 그래서 붙였다.
LOG = os.path.join(HERE, "_boot_log.tsv")


def log_line(kind, name, st="", sec=0.0, note=""):
    try:
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write("%s\t%s\t%s\t%s\t%.1f\t%s\n" % (
                time.strftime("%Y-%m-%dT%H:%M:%S"), kind, name, st, sec,
                note[:80].replace("\t", " ")))
    except Exception:
        pass  # 로그가 검사를 인질로 잡지 않는다

# 상태 검사 — 인수시험이 아니라 「지금 저장소가 성립하는가」를 본다.
# (스크립트, 인수)
#
# **[2026-09-01] 셋째 칸이 있었는데 아무 데도 안 쓰였다.** 「이것이 깨지면 멈출 일인가」를
# 선언해 뒀지만 아래 루프는 그 값을 안 읽고 **실패면 전부 멈췄다.** 선언과 기전이
# 갈린 자리다(사고 46). **선언을 살리는 대신 지웠다** — 기전이 하나뿐이면 선언도 하나다.
STATE = (
    ("verify_anchors.py", ()),
    ("install_git_hooks.py", ("--check",)),
    ("stopline_table.py", ("--check",)),
    # **[2026-09-09] 「지침 §X」가 실제로 있는 조항을 가리키는가.** v7.0 이 절 하나와 소절
    # 둘을 걷고 항 번호를 밀자 스무 곳 넘는 참조가 조용히 허공을 가리켰다. 값이 아니라
    # **참조**라서 기존 검사기가 하나도 안 봤다. `check_guideline_size.py` 의 자리를 대신한다.
    ("check_refs.py", ()),
    ("check_generated.py", ()),
    ("check_facts.py", ()),
    ("check_a11y.py", ()),
    ("check_counts.py", ()),
    ("check_status_fresh.py", ()),
    ("check_links.py", ()),
    # **허브가 빌드된 적이 없다.** 첫 push 가 첫 빌드이고 Pages 는 조용히 죽는다.
    ("check_jekyll.py", ()),
    # **[2026-09-01 운영자 지시] 사이트에 운영자 실명을 싣지 않는다.** 지운 것은 그때
    # 상태일 뿐이고, 표기 블록은 기준편을 베끼면서 **퍼진다**(발행 SKILL §3).
    ("check_private.py", ()),
    ("lint_publish.py", ()),
    # **허브 지면도 친다.** 종전에는 인수 없이 불러 `reports/*.md` 만 봤다 —
    # 사고 69 가 지면 모드를 만들어 놓고 **개시 검사가 그것을 한 번도 안 돌렸다.**
    # 지면은 인수로 줘야 검사되므로 **여기서 목록을 안 들고 찾는다**(사고 83).
    ("lint_publish.py", ("--hub",)),
    # **[2026-09-08] 세 저장소의 미커밋 파일과 마지막 턴의 종료 여부.** 2026-09-07 세션이
    # 한도로 끊겨 두 저장소의 작업이 커밋 전인 채 남았고 다음 세션이 그것을 추정해야 했다(사고 96).
    # 실패가 아니라 **보고할 사실**이라 종료코드는 0 이고 마지막 줄이 판정을 든다.
    ("session_snapshot.py", ("--check",)),
    # **[2026-09-08] STATUS 이관 후보와 여유.** 상한 처리가 일주일에 13번 손 동작이었다.
    # 보고일 뿐이라 종료코드 0 · 마지막 줄이 「여유 N B · 후보 M개」를 든다.
    ("status_archive.py", ("--check",)),
)
# STATUS 는 매 세션 전문이 읽힌다. 커지면 그만큼 착수가 느려진다.
# 자기 머리말이 「41 KB였다」고 적어 둔 파일이라 그 선을 상한으로 쓴다.
STATUS_LIMIT = 42000


def scripts_with_selftest():
    """`--selftest` 를 받는 스크립트를 **찾는다.** 목록을 들고 있지 않는다."""
    out = []
    for d in (HERE, os.path.join(HERE, "probe")):
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".py") or f.startswith("_"):
                continue
            p = os.path.join(d, f)
            try:
                src = io.open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            # argparse 로 받든 sys.argv 로 받든 잡는다.
            if '"--selftest"' in src or "'--selftest'" in src:
                out.append(p)
    return out


def run(path, args=(), timeout=60, retry=1):
    """반환 (지위, 마지막 줄, 초). **못 돌린 것을 통과로 세지 않는다.**

    **시간 초과는 한 번 다시 친다.** [2026-08-31] 한 실행에서 평소 0.2초짜리 셋이
    각각 180초를 넘겼는데, 같은 셋이 그 전후 실행에서는 정상이었다.
    **원인은 [미확인]이다** — 저장소가 OneDrive 위에 있어 동기화·검사 프로그램이
    파일을 잡는 순간일 수 있으나 확인하지 못했다.

    원인을 몰라도 처분은 된다. **이 파일은 세션의 첫 명령이고, 여기서 멈추면
    그날 일이 시작을 못 한다.** 재시도가 평소 비용의 두 배라면 싸다.
    **두 번 다 넘으면 그때가 진짜 「모름」이다** — 통과로 세지 않는다.
    """
    t0 = time.time()
    # 자식의 출력 인코딩을 **우리가 정한다.** 대부분의 스크립트가 스스로
    # `sys.stdout.reconfigure(utf-8)` 을 하지만, 안 하는 것이 하나만 있어도
    # 그 줄이 깨져 읽힌다 — 그러면 「무엇이 통과했는지」가 안 보인다.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, path] + list(args), cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        if retry > 0:
            st, why, sec = run(path, args, timeout, retry - 1)
            # 재시도로 살았어도 **그 사실을 감추지 않는다.**
            if st == OK:
                return OK, "(첫 시도 %ds 초과 — 재시도 통과) %s" % (timeout, why), sec
            return st, why, sec
        return UNK, "시간 초과 %ds — 재시도도 넘었다" % timeout, time.time() - t0
    except Exception as e:
        return UNK, "%s: %s" % (type(e).__name__, e), time.time() - t0
    lines = [l for l in (p.stdout or "").splitlines() if l.strip()]
    last = lines[-1][:70] if lines else ""
    if p.returncode == 0:
        return OK, last, time.time() - t0
    if p.returncode == 1:
        return BAD, last, time.time() - t0
    # 2 이상은 「돌리지 못했다」에 가깝다 — 실패와 가른다.
    return UNK, "종료코드 %d · %s" % (p.returncode, last), time.time() - t0


def status_bytes(data):
    """STATUS 크기 — **LF 기준.** `.gitattributes` 가 md 를 LF 로 고정하는데 이 기계의 작업 트리는
    CRLF 라 디스크 크기가 줄 수만큼 크다(415줄이면 415 B). 2026-09-08 「42,009 B 넘은 채 커밋」이
    그것이었다 — git 에는 41,594 B 였다(사고 99). 그래서 디스크가 아니라 **git 이 보는 바이트**를 잰다.
    `status_archive.py` 도 이 함수로 잰다 — 자는 하나다."""
    return len(data.replace(b"\r\n", b"\n"))


def status_size():
    p = os.path.join(ROOT, "docs", "STATUS.md")
    if not os.path.exists(p):
        return UNK, "docs/STATUS.md 가 없다", 0
    n = status_bytes(io.open(p, "rb").read())
    if n <= STATUS_LIMIT:
        return OK, "%d B (LF 기준 · 상한 %d)" % (n, STATUS_LIMIT), n
    return BAD, ("%d B — 상한 %d 을 넘었다(LF 기준). **매 세션 전문이 읽히는 파일이다** — "
                 "`python analysis/status_archive.py --check` 로 후보를 보고 `--write` 로 옮긴다."
                 % (n, STATUS_LIMIT)), n


def console_safe():
    """**이 파일이 만드는 세계가 운영자의 세계와 같은가.**

    위 `run()` 은 자식에게 `PYTHONIOENCODING=utf-8` 을 심는다. 이유는 정당하다 —
    안 심으면 한 스크립트가 깨져 찍혀 「무엇이 통과했는지」가 안 보인다.
    **그런데 그 친절이 통과의 근거를 바꾼다.** 운영자 터미널(cp949)과
    `pre-push` 에는 그 변수가 없으므로, 스스로 전문을 안 둔 스크립트는
    **여기서만 통과하고 거기서는 터진다.**

    2026-09-02 실측으로 났다. `build_series_chart.py --check` 가 통과 문장의
    `\u2014` 하나에 터졌고, 종료코드 1 을 `check_generated.py` 가
    **「낡았다」로 읽어** 멀쩡한 지면에 「다시 만들어라」를 냈다.
    훑어 보니 같은 처지가 **열 개 더** 있었다.

    그래서 환경을 원래대로 되돌리는 대신 **불변조건을 여기서 본다** —
    「한글을 찍는 스크립트는 스스로 UTF-8 전문을 둔다」.
    출력 가독성은 유지하면서 그 친절에 기대는 것을 막는다.

    **닿지 않는 곳:** 전문이 **있는지**만 본다. 그 전문이 실제로 도는지,
    한글 아닌 비ASCII 만 찍는 스크립트는 안 본다.
    """
    import re as _re
    hangul = _re.compile(r"[\uac00-\ud7a3]")
    miss = []
    for base in (HERE, os.path.join(HERE, "probe")):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(base, name)
            try:
                src = io.open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            if "reconfigure" in src:
                continue
            for line in src.split("\n"):
                if ("print(" in line or "file=sys.std" in line) and hangul.search(line):
                    miss.append(os.path.relpath(path, ROOT).replace("\\", "/"))
                    break
    n = len(miss)
    if not n:
        return OK, "한글을 찍는 스크립트가 전부 전문을 갖고 있다", 0
    return BAD, ("전문 없는 스크립트 %d개 — 운영자 콘솔에서 터진다: %s"
                 % (n, " · ".join(miss[:4]) + (" …" if n > 4 else ""))), n


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 목록을 안 들고 찾는가 ──")
    found = scripts_with_selftest()
    names = {os.path.basename(p) for p in found}
    chk("여러 개를 찾는다", len(found) >= 15, True)
    # 대표 몇 개가 들어 있는지 — **개수를 박지 않는다**(사고 53·65).
    for n in ("lint_publish.py", "safe_edit.py", "check_counts.py", "boot_check.py"):
        chk("%s 를 찾는다" % n, n in names, True)
    chk("자기 자신도 찾는다", "boot_check.py" in names, True)
    chk("probe 도 훑는다",
        any(os.sep + "probe" + os.sep in p for p in found), True)

    print("── 인수시험: 못 돌린 것을 통과로 세지 않는가 (사고 26) ──")
    st, why, _ = run(os.path.join(HERE, "없는파일.py"))
    chk("없는 스크립트는 모름", st, UNK)
    chk("모름은 통과가 아니다", st == OK, False)

    import tempfile
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "b.py")
        io.open(bad, "w", encoding="utf-8").write("import sys\nsys.exit(1)\n")
        st, _, _ = run(bad)
        chk("종료코드 1 은 실패", st, BAD)
        two = os.path.join(d, "t.py")
        io.open(two, "w", encoding="utf-8").write("import sys\nsys.exit(2)\n")
        st, _, _ = run(two)
        chk("종료코드 2 는 실패가 아니라 모름", st, UNK)
        good = os.path.join(d, "g.py")
        io.open(good, "w", encoding="utf-8").write("print('통과')\n")
        st, last, _ = run(good)
        chk("종료코드 0 은 통과", st, OK)
        chk("마지막 줄을 남긴다", last, "통과")
        slow = os.path.join(d, "s.py")
        io.open(slow, "w", encoding="utf-8").write("import time\ntime.sleep(5)\n")
        st, why, _ = run(slow, timeout=1, retry=0)
        chk("시간 초과는 모름", st, UNK)
        chk("초과라고 말한다", "시간 초과" in why, True)
        # **재시도해도 계속 넘으면 모름이다** — 재시도가 통과를 만들어 내지 않는다.
        st, why, _ = run(slow, timeout=1, retry=1)
        chk("재시도해도 넘으면 여전히 모름", st, UNK)
        chk("재시도했다고 말한다", "재시도도 넘었다" in why, True)
        # **한 번만 느린 것은 살린다.** 표식 파일로 「두 번째에는 빠르게」를 흉내 낸다.
        flaky = os.path.join(d, "f.py")
        mark = os.path.join(d, "mark").replace("\\", "/")
        io.open(flaky, "w", encoding="utf-8").write(
            "import os,time\n"
            "p = r'%s'\n"
            "if not os.path.exists(p):\n"
            "    open(p,'w').write('x')\n"
            "    time.sleep(5)\n"
            "print('통과')\n" % mark)
        st, why, _ = run(flaky, timeout=1, retry=1)
        chk("첫 시도만 느리면 재시도로 통과", st, OK)
        chk("재시도로 살았다는 것을 감추지 않는다", "재시도 통과" in why, True)

    print("── 인수시험: STATUS 크기 ──")
    st, why, n = status_size()
    chk("크기를 잰다", n > 0, True)
    chk("판정이 셋 중 하나", st in (OK, BAD, UNK), True)
    print("     지금: %s — %s" % (st, why[:60]))

    print("── 인수시험: 소요 로그 ──")
    global LOG
    keep = LOG
    with tempfile.TemporaryDirectory() as d:
        LOG = os.path.join(d, "log.tsv")
        log_line("시작", "x.py")
        log_line("끝", "x.py", OK, 0.2, "통과")
        rows = io.open(LOG, encoding="utf-8").read().splitlines()
    LOG = keep
    chk("시작과 끝을 따로 적는다", len(rows), 2)
    chk("끝 줄에 지위와 초가 있다", "\t끝\tx.py\t통과\t0.2\t" in rows[1], True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="세션 개시 검사. 목록을 찾아서 전부 돌린다.")
    ap.add_argument("--quick", action="store_true", help="인수시험만")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    t0 = time.time()
    fails, unks = [], []
    log_line("세션", "boot_check", "", 0.0, "시작")

    print("=" * 74)
    print(" 세션 개시 검사 — 목록을 손으로 들지 않는다. 찾아서 전부 돌린다.")
    print("=" * 74)

    found = scripts_with_selftest()
    print("\n[인수시험] `--selftest` 를 가진 스크립트 %d개" % len(found))
    times = []
    for p in found:
        if os.path.abspath(p) == os.path.abspath(__file__):
            continue          # 자기 자신은 여기서 안 돈다 — 돌면 무한이다
        log_line("시작", os.path.basename(p) + " --selftest")
        st, last, sec = run(p, ("--selftest",))
        log_line("끝", os.path.basename(p) + " --selftest", st, sec, last)
        name = os.path.relpath(p, ROOT).replace("\\", "/")
        times.append((sec, name))
        if st != OK or "재시도" in last:
            (fails if st == BAD else unks if st == UNK else []).append((name, last))
            print("  %-9s %-44s %s" % (st, name, last))
    print("  -> 실패 %d · 모름 %d · 나머지 통과" % (len(fails), len(unks)))
    # **가장 느렸던 셋을 찍는다.** 멈춤은 갑자기 오지 않고 느려지다 온다.
    slow = sorted(times, reverse=True)[:3]
    if slow:
        print("     느린 순: " + " · ".join("%s %.1fs" % (n.split("/")[-1], t)
                                          for t, n in slow))

    if not a.quick:
        print("\n[상태 검사]")
        for f, args in STATE:
            p = os.path.join(HERE, f)
            name = f + ((" " + " ".join(args)) if args else "")
            log_line("시작", name)
            st, last, sec = run(p, args, timeout=120)
            log_line("끝", name, st, sec, last)
            if st != OK:
                (fails if st == BAD else unks).append((name, last))
            print("  %-9s %-34s %s" % (st, name, last))

        st, why, _ = console_safe()
        if st != OK:
            (fails if st == BAD else unks).append(("운영자 콘솔 안전", why))
        print("  %-9s %-34s %s" % (st, "운영자 콘솔 안전", why[:60]))

        st, why, _ = status_size()
        if st != OK:
            (fails if st == BAD else unks).append(("STATUS 크기", why))
        print("  %-9s %-34s %s" % (st, "STATUS 크기", why[:60]))

    print("\n" + "-" * 74)
    if fails:
        print(" **실패 %d건 — 여기서 멈춘다.**" % len(fails))
        for n, w in fails:
            print("   · %-34s %s" % (n, w))
    if unks:
        print(" **모름 %d건 — 통과로 세지 않는다**(사고 26)." % len(unks))
        for n, w in unks:
            print("   · %-34s %s" % (n, w))
    if not fails and not unks:
        print(" 전부 통과 · %.1f초" % (time.time() - t0))
        print(" 소요 로그: analysis/_boot_log.tsv — 다음 초과 때 마지막 「시작」 줄이 선 자리다")
        print(" **다음: `docs/STATUS.md` 전문을 읽는다.**")
        print("   맨 앞 「착수점」 절만 읽어도 시작할 수 있고,")
        print("   바로 손댈 것은 **「다음 할 일 · A」의 첫 항목**이다.")
        print("   (A = 이쪽이 지금 할 수 있는 것 · B = 운영자 손 · C = 아직 안 본 축)")
    log_line("합계", "boot_check", BAD if fails else (UNK if unks else OK), time.time() - t0,
             "실패 %d · 모름 %d" % (len(fails), len(unks)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

"""STATUS 갱신 누락 검사 — 산문을 읽지 않고 git 이력만 본다.

왜 있는가
---------
수치는 `lint_publish.py`가, 앵커는 `verify_anchors.py`가 막는데
`docs/STATUS.md`는 **손으로 갱신해서 낡는다.** 2026-08-26 하루에 세 번 낡았다
(사고 31의 「같은 날 추가 관측」). 셋 다 파생 수치였고, 1차 처분으로 파생 수치를
STATUS 문장에서 빼고 실행 명령으로 대체했다.

남은 구멍은 **값이 아니라 갱신 자체**다. 일이 진행됐는데 STATUS만 그대로면
다음 세션은 낡은 상태를 현재로 읽는다.

**내용을 검사하지 않는 이유.** 남은 STATUS 본문은 대부분 판단이고,
판단은 기계적으로 낡지 않고 **결정으로** 낡는다. 산문을 정규식으로 긁으면
STATUS에 기계 판독 표식을 요구하게 되고, 그 표식이 또 하나의 유지 대상이 된다.
그래서 이 검사는 **표식을 요구하지 않는다.** git 이력만 본다.

무엇을 보는가
-------------
  `docs/STATUS.md`를 마지막으로 건드린 커밋 이후,
  `reports/` 또는 `docs/`를 건드린 커밋이 몇 건 쌓였는가. 그뿐이다.

  작업 트리(스테이지 포함)에 `docs/STATUS.md` 변경이 있으면 **지금 갱신 중**이므로
  연속 구간을 0으로 본다 — 커밋 직전에 도는 검사이기 때문이다.

무엇을 안 보는가 — 이 처분이 닿지 않는 곳
-----------------------------------------
  * **STATUS의 내용이 맞는지는 안 본다.** 갱신 누락만 잡는다.
    STATUS를 열어 공백 한 칸만 고쳐도 이 검사는 통과한다. 그것은 자제심의 몫이다.
  * **`analysis/`만 바뀐 커밋은 안 센다.** 운영자 설계(사고 31 후속)가 `reports/`·`docs/`로
    범위를 적었고 그대로 구현했다. **도구가 늘어도 STATUS의 도구 목록이 안 따라오는
    구멍은 남는다** — 넓힐지는 운영자 판단이고, 넓히려면 WATCH에 `analysis/`를 더한다.
    (사고 32: 처분을 넣을 때 「이 처분이 닿지 않는 곳은 어디인가」를 함께 적는다.)

기본값 N=5의 근거 — 얇다. 적어 둔다
-----------------------------------
  git 이력 전수(76커밋)에서 STATUS 도입 **이후** 관측된 최대 연속 구간은 **1건**이다.
  도입 이전 16건짜리 구간이 있으나 그때는 STATUS 파일 자체가 없었다.
  즉 N을 **관측으로 정할 근거가 없다.** 5는 여유를 둔 선택이고, 자주 울리면 올린다.

사용
----
  python analysis/check_status_fresh.py
  python analysis/check_status_fresh.py --max-stale 3
  python analysis/check_status_fresh.py --strict     # 경고를 차단으로 올린다
  python analysis/check_status_fresh.py --selftest   # 내장 인수시험

종료코드 0 = 통과 또는 경고 / 1 = --strict 에서 초과 / 2 = 검사 불성립(git 아님·커밋 없음).
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
STATUS = "docs/STATUS.md"
WATCH = ("reports/", "docs/")


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None
    return r.stdout


def stale_run():
    """STATUS를 마지막으로 건드린 커밋 이후, 감시 대상을 건드린 커밋 목록."""
    out = git("log", "--pretty=format:%x01%h%x09%s", "--name-only", "-n", "200")
    if out is None:
        return None
    run = []
    for block in out.split("\x01"):
        if not block.strip():
            continue
        head, *files = block.splitlines()
        h, _, subject = head.partition("\t")
        files = [f.strip() for f in files if f.strip()]
        if STATUS in files:
            break                      # 여기서 갱신됐다. 그 이전은 볼 필요가 없다
        if any(f.startswith(w) for f in files for w in WATCH):
            run.append((h, subject))
    return run


def status_in_worktree():
    out = git("status", "--porcelain", "--", STATUS)
    return bool(out and out.strip())


def selftest():
    """양방향으로 확인한다 — 세는 경로와 멈추는 경로 둘 다 돈다.

    저장소를 건드리지 않는다. 감시 파일 경로만 바꿔 끼운다.
    """
    global STATUS
    keep = STATUS
    ok = True
    print("── 인수시험 ──")

    # ① 세는 경로 — 이력에 없는 파일을 감시 파일로 두면 break가 안 걸린다.
    STATUS = "docs/__없는파일__.md"
    counted = stale_run()
    print(f"  ① 세는 경로     감시 대상 커밋 {len(counted)}건")
    if not counted:
        print("     실패 — 한 건도 못 셌다. reports/·docs/ 커밋이 이력에 있는데 0이면 파싱이 깨진 것이다.")
        ok = False

    # ② 멈추는 경로 — 실제 STATUS는 이력에 있으므로 그 지점에서 break 해야 한다.
    STATUS = keep
    stopped = stale_run()
    print(f"  ② 멈추는 경로   {keep} 이후 {len(stopped)}건")
    if len(stopped) >= len(counted):
        print("     실패 — break가 안 걸렸다. 갱신 커밋을 만나도 계속 세고 있다.")
        ok = False

    # ③ 작업 트리 우선 — 지금 STATUS를 고치는 중이면 연속 구간은 0이어야 한다.
    print(f"  ③ 작업 트리     {keep} 변경 {'있음' if status_in_worktree() else '없음'}"
          f" → 판정 n = {0 if status_in_worktree() else len(stopped)}")

    STATUS = keep
    print()
    print("인수시험 통과 — 세는 경로·멈추는 경로 양방향 확인." if ok else "인수시험 실패.")
    return ok


def main():
    ap = argparse.ArgumentParser(description="STATUS 갱신 누락 검사")
    ap.add_argument("--max-stale", type=int, default=5,
                    help="이 건수를 넘게 쌓이면 경고한다 (기본 5)")
    ap.add_argument("--strict", action="store_true",
                    help="경고를 차단으로 올린다 (종료코드 1)")
    ap.add_argument("--selftest", action="store_true", help="내장 인수시험")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(0 if selftest() else 1)

    run = stale_run()
    if run is None:
        print("git 이력을 읽지 못했다 — 검사 불성립.")
        sys.exit(2)

    editing = status_in_worktree()
    n = 0 if editing else len(run)

    print("── STATUS 갱신 누락 검사 ──")
    print(f"  감시 대상  {' · '.join(WATCH)}")
    print(f"  기준       연속 {a.max_stale}건 초과 시 경고")
    if editing:
        print(f"  작업 트리  {STATUS} 변경 있음 — **지금 갱신 중**으로 본다")
    print(f"  연속 구간  {n}건")

    if run and not editing:
        for h, s in run[:10]:
            print(f"    {h}  {s}")
        if len(run) > 10:
            print(f"    … 외 {len(run) - 10}건")

    print()
    if n > a.max_stale:
        print(f"경고 — {STATUS} 갱신 없이 {n}건이 쌓였다.")
        print("      일이 진행됐는데 상태가 그대로면 다음 세션이 낡은 상태를 현재로 읽는다.")
        print("      **내용이 아니라 갱신 여부만 본 것이다.** 열어서 맞는지는 사람이 판단한다.")
        if a.strict:
            sys.exit(1)
        sys.exit(0)

    print(f"통과 — 연속 {n}건 (기준 {a.max_stale}).")


if __name__ == "__main__":
    main()

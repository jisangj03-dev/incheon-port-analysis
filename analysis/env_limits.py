# -*- coding: utf-8 -*-
"""환경 생략 — 「이 기계에는 그 전제가 원천적으로 없다」를 「모름」과 가른다 (2026-10-10).

왜 있는가
---------
클라우드 새 클론에서 `boot_check.py` 가 실패 4 · 모름 6 을 냈다(2026-10-10 채팅 실측).
그중 여럿은 장치가 틀려서가 아니라 **이 기계에 없는 것**(운영자 홈의 `본부` 폴더 ·
형제 저장소 `sounding` · `~/tools/watermarks-remover`)을 찾다가 멈춘 것이었다.
그것을 실패로 세면 주간 루틴이 매번 「여기서 멈춘다」를 읽고, 모름으로 세면
진짜 모름(시간 초과·예외)과 섞여 안 보인다.

그래서 셋째 지위를 둔다 — **종료코드 3 = 환경 생략.** `verify_anchors.py` 가
2026-09-28 에 봉인 파일에 대해 먼저 쓴 코드와 같은 값이다.

규칙 (verify_anchors 의 v2 판정과 같은 방향)
--------------------------------------------
· **전제가 없고, 이 기계가 클라우드임을 적극적으로 확인했을 때만** 3 이다.
· 확인이 안 되면 종전대로 2(모름)다. 운영자 기계에서 `본부` 폴더가 사라지면
  그건 환경이 아니라 사고이고, 조용히 풀리면 안 된다(첫 시도의 결함 · 사고 26).
· **환경 생략은 통과가 아니다.** `boot_check` 는 따로 세고 따로 찍는다.

닿지 않는 곳
------------
· 신호는 Claude Code 가 스스로 심는 환경변수다(`verify_anchors.is_confirmed_cloud`).
  그 값의 위조는 못 잡는다 — 다만 위조해야 풀리는 방향이라 값이 사라지는 사고로는 안 뚫린다.

  python analysis/env_limits.py --selftest
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from verify_anchors import is_confirmed_cloud  # noqa: E402 — 판정 함수는 하나만 둔다

ENV_SKIP = 3
UNKNOWN = 2


def missing_code(env=None):
    """전제가 없을 때 낼 종료코드 — 클라우드 확인이면 3, 아니면 2."""
    return ENV_SKIP if is_confirmed_cloud(env) else UNKNOWN


def say_missing(what, path, env=None, out=None):
    """전제 부재를 한 줄로 찍고 종료코드를 돌려준다. 마지막 줄이 판정이다(boot_check 가 읽는다)."""
    out = out or sys.stdout
    code = missing_code(env)
    print("[불성립] 못 찾았다 — %s: %s" % (what, path), file=out)
    if code == ENV_SKIP:
        print("  **환경 생략**(클라우드 확인됨) — 이 기계에는 원천적으로 없다. 통과로 세지 않는다.", file=out)
    else:
        print("  이 저장소만 clone한 기계에서는 잴 수 없다. 통과로 치지 않는다.", file=out)
    return code


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-44s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 클라우드 확인일 때만 환경 생략 ──")
    chk("신호 없음 → 모름(2)", missing_code({}), UNKNOWN)
    chk("CLAUDE_CODE_REMOTE=true → 환경 생략(3)", missing_code({"CLAUDE_CODE_REMOTE": "true"}), ENV_SKIP)
    chk("CLAUDE_CODE_REMOTE=false → 모름(2)", missing_code({"CLAUDE_CODE_REMOTE": "false"}), UNKNOWN)
    chk("빈 값 → 모름(2)", missing_code({"CLAUDE_CODE_REMOTE": ""}), UNKNOWN)
    import io as _io
    buf = _io.StringIO()
    code = say_missing("지침 파일", "/없는/경로", {"CLAUDE_CODE_REMOTE": "true"}, out=buf)
    chk("환경 생략 문구를 찍는다", "환경 생략" in buf.getvalue(), True)
    chk("통과라고 말하지 않는다", "통과로 세지 않는다" in buf.getvalue(), True)
    chk("종료코드 3", code, ENV_SKIP)
    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else 0)

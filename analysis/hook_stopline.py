"""커밋 전 검증 훅 — 규칙을 기억이 아니라 하네스가 집행한다.

왜 있는가
---------
지침 §0-3: **절차는 지침에 적지 않는다. 코드·스크립트·SKILL에 상주시킨다.**
「커밋 전에 `verify_anchors.py`를 돌린다」가 문서에만 있었고, 실제로 돌리는 것은 내 기억이었다.
사람이 나르는 규칙은 유실된다(사고 22). 이 훅이 그것을 집행한다.

무엇을 하지 않는가 (v6.4 · 2026-09-09)
---------------------------------------
**push 를 막지 않는다.** 2026-08-27~09-09 에는 이 훅이 「push 는 운영자만」(구 §4)을 명령 문자열로
집행했고, 09-09 위임 뒤에는 `VIDIMUS_PUSH_OK=1` env 로 통과시켰다. 그 구조는 env 가 없는 기계에서
그대로 막히는 함정이었다. 지침 v6.4 가 push·배포를 세션 몫으로 옮기면서 **금지 분기를 지웠다** —
훅은 금지가 아니라 검증에만 쓴다(2026-09-09 운영자 위임문). 되돌릴 수 없는 것(힘 push · 토큰 갱신)은
`.claude/settings.json` 의 `permissions.deny` 와 자동 모드 `hard_deny` 가 든다.
push 분류(`classify` 의 'push')는 남겨 뒀다 — 시험이 따옴표·히어독 파싱을 그 사례로 확인한다.

왜 deny 규칙이 아니라 훅인가
----------------------------
`Bash(*git commit*)` 같은 넓은 규칙은 **언급만 하는 명령까지 잡고**, 좁은 규칙은 접두만 보므로
`cd X && git commit` 을 놓친다(2026-08-27 실측). **훅은 명령을 파싱해 정확히 판정하고, 그 판정을 시험할 수 있다.**

사용 / 시험
-----------
  python analysis/hook_stopline.py --selftest

정지선-집행: §4 — 커밋 전 앵커 검사 (push 는 v6.4 로 세션이 친다 · 이 훅은 막지 않는다)
정지선-명제: Claude Code 도구 경로로 들어온 **명령 문자열** 중 commit 앞에서 앵커 검사를 돌리고, 실패하면 그 커밋을 막는다
정지선-한계: **문자열만 본다** — `subprocess.run(['git','commit'])` 같은 간접 호출은 못 본다 · **push 는 검사 대상이 아니다**(금지 분기 삭제 · 2026-09-09). 힘 push·토큰 갱신은 `permissions.deny`·`hard_deny` 가 든다
"""

import json
import os
import re
import subprocess
import sys

# Windows 콘솔(cp949)에서 죽지 않게 강제한다. 형제 스크립트 4종과 같은 관례다.
# **이 줄이 없으면 deny() 경로에서만 죽었다** — 즉 막아야 할 때만 죽는 훅이었다.
# 통과 경로는 무출력이라 시험에서 안 드러났다(2026-08-27 실측. 사고 26 계열).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 명령의 「첫 낱말」 자리에 놓인 git push만 잡는다 — 문자열 안의 언급은 안 잡는다.
# git 전역 옵션은 값을 따로 갖는 형태가 있다(`git -c core.x=1 push`).
# 그래서 「-옵션 [값]」 쌍을 0회 이상 건너뛴 뒤 push/commit을 본다.
# `git --no-pager push`는 역추적으로 풀린다 — 값 자리에 push를 먹었다가 되돌린다.
_GIT_OPTS = r"(?:-\S+(?:\s+\S+)?\s+)*"

# re.M이 필요하다. 없으면 `^`가 문자열 맨 앞에서만 맞아서 **여러 줄 명령의 둘째 줄
# `git push`를 통째로 놓친다** — 2026-08-27 인수시험이 잡았다. 줄바꿈도 명령 구분자다.
PUSH = re.compile(r"(^|[;&|\n]|\bthen\b|\bdo\b)\s*git\s+" + _GIT_OPTS + r"push\b", re.M)

COMMIT = re.compile(r"(^|[;&|\n])\s*git\s+" + _GIT_OPTS + r"commit\b", re.M)

CHECKS = [
    (["analysis/verify_anchors.py", "--selftest"], "봉인 파일 열람 시험"),
    (["analysis/verify_anchors.py"], "앵커 3건 대조"),
]

def emit_deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


_QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"", re.S)

# 히어독 본문도 데이터다. `<<EOF ... EOF` / `<<'EOF' ... EOF` / `<<-EOF` 를 지운다.
# 따옴표를 지우고 나서도 이 자리가 남아 커밋 메시지 안의 문구에 또 막혔다(2026-08-27 실측).
_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_]\w*)\1.*?^\2\s*$", re.S | re.M)


def strip_quoted(cmd):
    """따옴표와 히어독 본문을 지운다 — 거기 있는 것은 명령이 아니라 **데이터**다.

    2026-08-27에 이 훅이 실제로 오탐했다: 문서를 쓰는 `printf '...&& git push...'`가
    push로 판정돼 막혔다. 넓은 `deny` 규칙을 되돌린 것과 **같은 결함이 훅에 남아 있었다.**
    완벽한 셸 파싱은 아니다(중첩·이스케이프는 못 본다). 그러나 **오탐을 크게 줄이면서**
    실제 실행 경로는 그대로 잡는다 — 진짜 `git push`는 따옴표 밖에 있어야 실행된다.
    """
    return _QUOTED.sub(" ", _HEREDOC.sub(" ", cmd))


def classify(cmd):
    """(판정, 사유). 판정 = 'push' | 'commit' | 'pass'. 시험이 이 함수를 직접 친다."""
    cmd = strip_quoted(cmd)
    if PUSH.search(cmd):
        # 분류만 한다. 막지 않는다(v6.4). 시험이 파싱 정확도를 이 사례로 본다.
        return "push", None
    if COMMIT.search(cmd):
        return "commit", None
    return "pass", None


def run_checks():
    """실패한 검사가 있으면 (라벨, 종료코드, 꼬리출력), 없으면 None."""
    for args, label in CHECKS:
        r = subprocess.run([sys.executable] + args, cwd=ROOT,
                           capture_output=True, timeout=110)
        if r.returncode != 0:
            out = (r.stdout or b"").decode("utf-8", "replace").strip()
            return label, r.returncode, "\n".join(out.splitlines()[-6:])
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        # 입력을 못 읽으면 **통과시킨다.** 여기서 막으면 훅 자신의 결함이 작업 전체를
        # 봉쇄한다 — 작업을 죽이는 검사기는 결국 꺼진다(사고 30의 반대편 실패).
        sys.exit(0)

    cmd = (payload.get("tool_input") or {}).get("command") or ""
    verdict, _ = classify(cmd)

    # push 는 통과다(v6.4). 커밋만 검사로 간다.
    if verdict == "commit":
        bad = run_checks()
        if bad:
            emit_deny("정지선 검사 실패 — %s (종료코드 %d). 커밋을 막았다.\n%s" % bad)
    sys.exit(0)


def selftest():
    """양방향으로 친다(사고 34). 검사로 가야 할 것과 통과시켜야 할 것을 함께 본다.

    'push' 판정은 **분류**일 뿐이다(v6.4 · 막지 않는다). 사례를 남긴 이유는 따옴표·히어독 파싱이
    실제 명령과 데이터를 가르는지를 그 사례가 가장 잘 보여 주기 때문이다.
    """
    cases = [
        # (명령, 기대 판정)
        ("git push", "push"),
        ("git push -u origin main", "push"),
        ("cd /x && git push", "push"),
        ("git -c core.x=1 push", "push"),
        ("git status; git push", "push"),
        # 언급만 하는 것은 막지 않는다 — 2026-08-27에 넓은 deny 규칙이 이걸 막았다
        ("grep -n 'git push' settings.json", "pass"),
        ("python -c \"print('git push')\"", "pass"),
        ("echo git-push-notes.md", "pass"),
        # 2026-08-27 실제 오탐: 문서를 쓰는 명령의 인자 안에 push 문구가 있었다
        ("printf '%s' 'cd X && git push 를 막는다' > note.txt", "pass"),
        ("python -c \"x = 'a; git push'\"", "pass"),
        # 히어독 본문도 데이터다 — 커밋 메시지 안의 문구에 실제로 막혔다(2026-08-27)
        ("git commit -F - <<'EOF'\ncd X && git push 를 막는다\nEOF", "commit"),
        ("cat <<EOF > n.md\ngit push 설명\nEOF", "pass"),
        # 따옴표·히어독 밖의 진짜 push는 여전히 잡혀야 한다
        ("printf 'note' > f.txt && git push", "push"),
        ("cat <<'EOF' > n.md\n설명\nEOF\ngit push", "push"),
        # 커밋은 검사로 간다
        ("git commit -m x", "commit"),
        ("git add . && git commit -F -", "commit"),
        # 나머지는 통과
        ("ls -la", "pass"),
        ("git log --oneline -1", "pass"),
    ]
    print("── 인수시험: 명령 분류 ──")
    ok = True
    for cmd, want in cases:
        got, _ = classify(cmd)
        hit = got == want
        ok = ok and hit
        print("  %s %-40s -> %-6s (기대 %s)" % ("OK  " if hit else "FAIL", cmd[:40], got, want))
    # v6.4 — push 판정에 사유(deny 문구)가 붙지 않아야 한다. 붙으면 금지 분기가 되살아난 것이다.
    print("── 인수시험: push 는 막지 않는다(v6.4) ──")
    got, reason = classify("git push origin main")
    hit = got == "push" and reason is None
    ok = ok and hit
    print("  %s %-40s -> %s · 사유 %s (기대 push · None)" % ("OK  " if hit else "FAIL", "git push origin main", got, reason))
    print("통과" if ok else "실패")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    main()

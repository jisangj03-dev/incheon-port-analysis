#!/bin/sh
# 정지선 pre-push — 「push는 운영자만」을 **도구 경로가 아니라 대리 여부**로 집행한다.
#
# 왜 이게 따로 필요한가
# ---------------------
# `analysis/hook_stopline.py`(PreToolUse)는 **명령 문자열**을 본다. 그래서
#   python -c "import subprocess; subprocess.run(['git','push'])"
# 같은 간접 호출을 **못 막는다**(2026-08-27 실측: 판정 pass).
# 즉 그 훅의 기전은 「Claude Code 도구 경로 차단」이지 §4 문면의 「운영자만」이 아니다.
#
# 이 훅은 git 자신이 부르므로 **어떤 경로로 왔든** 걸린다.
# 판정 기준은 `CLAUDECODE` — Claude Code가 자기 셸에 심는 표지다(실측).
#   · 운영자가 자기 터미널에서 치면 이 변수가 없다 → 통과. **문서화된 운영자 절차는 그대로다.**
#   · Claude Code 세션에서 나온 push는 직접이든 간접이든 → 차단.
#
# 무엇을 못 하는가 (적어 두지 않으면 또 기전을 문면으로 착각한다)
# ---------------------------------------------------------------
#   1. `.git/hooks/`는 **커밋되지 않는다.** 이 기계에만 있고, 지우면 사라진다.
#      새 clone에는 없다 — `analysis/install_git_hooks.py`로 다시 깐다.
#   2. `CLAUDECODE`는 **지울 수 있다.** 작정한 에이전트는 넘는다.
#      이것은 **내 실수를 막는 난간이지 보안 경계가 아니다.**
#   3. 세션 안에서 `!` 접두로 운영자가 직접 칠 때도 이 변수가 붙어 **같이 막힌다.**
#      그때는 아래 우회 변수를 쓴다.
#
# 운영자 우회 (의도된 통로)
# -------------------------
#   VIDIMUS_PUSH_OK=1 git push

if [ -n "$CLAUDECODE" ] && [ -z "$VIDIMUS_PUSH_OK" ]; then
	echo "" >&2
	echo "정지선: push는 운영자만 한다 (지침 §4)." >&2
	echo "  이 push는 Claude Code 세션(CLAUDECODE=1)에서 나왔다 — 막았다." >&2
	echo "  공개 발행은 운영자의 서명이다. 커밋은 AI 판단, push는 사람 손이다." >&2
	echo "" >&2
	echo "  운영자가 이 세션 안에서 직접 밀어야 하면:  VIDIMUS_PUSH_OK=1 git push" >&2
	echo "  (평소처럼 자기 터미널에서 치면 이 훅은 아무것도 안 한다.)" >&2
	echo "" >&2
	exit 1
fi

exit 0

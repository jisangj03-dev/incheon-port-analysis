#!/bin/bash
# 클라우드 세션 시작 준비 — 새 클론에서 「깔려 있지 않아 못 돈다」를 없앤다(2026-10-10).
# 운영자 기계(로컬)에서는 아무것도 안 한다. 동기 실행: 끝나야 세션이 열린다(의존성 경쟁 없음).
# 실패하면 숨기지 않는다 — 마지막 줄에 무엇이 안 됐는지 찍고 종료 1(비차단 오류로 보인다).
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 1

fail=""
# PEP 668(「외부 관리 환경」) 표지가 있는 파이썬은 첫 줄을 거절한다 — 채팅의 새 컨테이너에서 실제로 났다(PR #19 댓글).
# 이 컨테이너는 세션이 끝나면 버려지는 것이라 시스템 파이썬에 깔아도 남는 피해가 없다 → 그때만 --break-system-packages.
pip_in() { python -m pip install -q --disable-pip-version-check "$@" -r requirements-dev.txt >/tmp/session-start-pip.log 2>&1; }
pip_in || { grep -q "externally-managed" /tmp/session-start-pip.log && pip_in --break-system-packages; } || fail="$fail pip($(tail -1 /tmp/session-start-pip.log | cut -c1-80))"
npm install --no-audit --no-fund --silent >/dev/null 2>&1 || fail="$fail npm"
python analysis/install_git_hooks.py >/dev/null 2>&1 || fail="$fail git-hooks"

# Playwright 1.63 이 원하는 브라우저 판(1243)이 컨테이너에 없으면, 미리 깔린 크로미움을 쓴다.
# (이 환경은 `playwright install` 을 막아 둔다 — 내려받지 않는다.)
if [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -x /opt/pw-browsers/chromium ]; then
  echo 'export PW_CHROMIUM_PATH=/opt/pw-browsers/chromium' >> "$CLAUDE_ENV_FILE"
fi

if [ -n "$fail" ]; then
  echo "[세션 준비] 실패:$fail — boot_check 에서 해당 장치가 「모듈 없음」으로 나온다" >&2
  exit 1
fi
echo "[세션 준비] pip·npm·git 훅 준비됨"

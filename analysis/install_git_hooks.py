"""git 훅 설치 — `.git/hooks/`는 커밋되지 않으므로 설치본을 코드로 든다.

`analysis/git_pre_push.sh`가 정본이고(추적된다), 이 스크립트가 그것을
`.git/hooks/pre-push`로 복사한다. 새 clone이나 훅을 지운 뒤에는 다시 돌린다.

  python analysis/install_git_hooks.py            # 설치
  python analysis/install_git_hooks.py --check    # 설치돼 있고 정본과 같은가 (종료코드로 답한다)
  python analysis/install_git_hooks.py --selftest # 차단·통과 두 갈래가 실제로 갈리는가

사고 28의 처분과 같은 형태다 — **정지선이 문서에만 있으면 「지켜졌는가」에 답할 수 없다.**
여기서는 한 겹 더 나쁘다: `.git/hooks/`는 **추적조차 안 되므로** 있는지 없는지도
git이 말해 주지 않는다. 그래서 `--check`가 그 답을 종료코드로 낸다.
"""

import hashlib
import os
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "analysis", "git_pre_push.sh")
DST = os.path.join(ROOT, ".git", "hooks", "pre-push")


def digest(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest().upper()


def install():
    os.makedirs(os.path.dirname(DST), exist_ok=True)
    shutil.copyfile(SRC, DST)
    try:  # POSIX에서만 의미가 있다. Windows에서는 git이 알아서 sh로 돌린다.
        os.chmod(DST, 0o755)
    except Exception:
        pass
    print("설치: %s" % DST)
    print("  정본 %s" % SRC)
    print("  SHA-256 %s" % digest(DST))
    return 0


def check():
    a, b = digest(SRC), digest(DST)
    if b is None:
        print("[없음] .git/hooks/pre-push 가 설치돼 있지 않다 — push 정지선이 비어 있다.")
        print("  -> python analysis/install_git_hooks.py")
        return 2
    if a != b:
        print("[불일치] 설치본이 정본과 다르다. 손으로 고쳤거나 낡았다.")
        print("  -> python analysis/install_git_hooks.py")
        return 1
    print("[일치] pre-push 설치됨 · 정본과 동일 (SHA-256 %s)" % a)
    return 0


def find_sh():
    """git이 훅을 돌릴 때 쓰는 sh를 찾는다.

    PowerShell의 PATH에는 sh가 없지만 **기계에는 있다**(Git for Windows 동봉).
    PATH만 보고 「없다」고 하면 시험이 조용히 꺼진다 — 그래서 git 설치 경로도 본다.
    """
    for name in ("sh", "bash"):
        p = shutil.which(name)
        if p:
            return p
    try:
        exec_path = subprocess.run(["git", "--exec-path"], capture_output=True,
                                   text=True, timeout=15).stdout.strip()
    except Exception:
        exec_path = ""
    if exec_path:
        # .../Git/mingw64/libexec/git-core  ->  .../Git
        base = exec_path
        for _ in range(3):
            base = os.path.dirname(base)
        for rel in (("bin", "sh.exe"), ("usr", "bin", "sh.exe"),
                    ("bin", "bash.exe"), ("usr", "bin", "bash.exe")):
            cand = os.path.join(base, *rel)
            if os.path.isfile(cand):
                return cand
    return None


def selftest():
    """훅 자체를 두 환경으로 직접 돌린다. 차단과 통과가 실제로 갈리는지 본다(사고 34)."""
    if not os.path.isfile(SRC):
        print("정본 없음:", SRC)
        return 1
    sh = find_sh()
    if not sh:
        # **건너뛰면 실패로 친다.** 조용히 통과하는 시험은 통과가 아니라 부재다(사고 26).
        print("[FAIL] sh/bash 를 못 찾아 시험을 못 돌렸다 — 검사되지 않았다.")
        return 1

    print("── 인수시험: pre-push 판정 ──")
    cases = [
        ("운영자 터미널 (CLAUDECODE 없음)", {}, 0),
        ("Claude Code 세션", {"CLAUDECODE": "1"}, 1),
        ("Claude Code + 운영자 우회", {"CLAUDECODE": "1", "VIDIMUS_PUSH_OK": "1"}, 0),
    ]
    ok = True
    for label, extra, want in cases:
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDECODE", "VIDIMUS_PUSH_OK")}
        env.update(extra)
        r = subprocess.run([sh, SRC], env=env, capture_output=True, timeout=30)
        hit = r.returncode == want
        ok = ok and hit
        print("  %s %-34s -> 종료코드 %d (기대 %d)"
              % ("OK  " if hit else "FAIL", label, r.returncode, want))
    print("통과" if ok else "실패")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--check" in sys.argv:
        sys.exit(check())
    sys.exit(install())

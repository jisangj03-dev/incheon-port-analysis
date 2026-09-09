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

# 관할 저장소 — **이 목록을 도구가 든다. 사람이 매 세션 나르지 않는다**(§0-3).
#
# 2026-08-28 실측으로 생겼다. 이 스크립트는 인천 저장소 하나에만 훅을 깔고 있었고,
# **브랜드 허브(`jisangj03-dev.github.io`)의 `.git/hooks/`는 비어 있었다.**
# 즉 2층(경로 무관 차단)이 없고 1층(`hook_stopline.py`, 명령 문자열)만 있는 상태였는데,
# 1층은 간접 호출을 **못 막는다**(사고 46 실측). 웹사이트 작업이 일어날 저장소가 하필 그쪽이다.
#
# 형제 경로로 찾는다. 없으면 조용히 건너뛴다 — 다른 기계에는 허브가 없을 수 있다.
# [2026-09-03] 측심(`sounding`)을 넣었다 — 9/6 에 실제로 push 되는 저장소인데 2층이 비어 있었다.
# 지난 세션에 push 를 막은 것은 1층(`hook_stopline.py` · 명령 문자열)이고, 간접 호출은 그 층이
# 못 막는다(사고 46). 웹사이트 작업이 일어나는 저장소가 하필 또 관할 밖이었다.
SIBLINGS = ("jisangj03-dev.github.io", "sounding")


def governed():
    """훅을 깔아야 하는 저장소 목록. (이름, 경로)."""
    out = [(os.path.basename(ROOT), ROOT)]
    parent = os.path.dirname(ROOT)
    for name in SIBLINGS:
        path = os.path.join(parent, name)
        if os.path.isdir(os.path.join(path, ".git")):
            out.append((name, path))
    return out


def hook_path(repo):
    return os.path.join(repo, ".git", "hooks", "pre-push")


def digest(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest().upper()


def install_one(name, repo):
    dst = hook_path(repo)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(SRC, dst)
    try:  # POSIX에서만 의미가 있다. Windows에서는 git이 알아서 sh로 돌린다.
        os.chmod(dst, 0o755)
    except Exception:
        pass
    print("설치: %-26s %s" % (name, dst))
    return 0


def install(only=None):
    repos = [(n, p) for n, p in governed() if only in (None, n, p)]
    if not repos:
        print("대상 저장소가 없다: %s" % only)
        return 2
    print("정본 %s" % SRC)
    print("  SHA-256 %s" % digest(SRC))
    for name, repo in repos:
        install_one(name, repo)
    return 0


def check(only=None):
    a = digest(SRC)
    repos = [(n, p) for n, p in governed() if only in (None, n, p)]
    if not repos:
        print("대상 저장소가 없다: %s" % only)
        return 2
    worst = 0
    for name, repo in repos:
        b = digest(hook_path(repo))
        if b is None:
            print("[없음]   %-26s pre-push 미설치 — push 정지선 2층이 비어 있다." % name)
            worst = max(worst, 2)
        elif a != b:
            print("[불일치] %-26s 설치본이 정본과 다르다. 손으로 고쳤거나 낡았다." % name)
            worst = max(worst, 1)
        else:
            print("[일치]   %-26s pre-push 설치됨 · 정본과 동일" % name)
    if worst:
        print("  -> python analysis/install_git_hooks.py")
    else:
        print("정본 SHA-256 %s · 관할 %d곳 전부 일치" % (a, len(repos)))
    return worst


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
    # v6.4(2026-09-09) — 차단 분기가 없다. 어느 환경에서든 통과해야 하고, **통과하지 않으면**
    # 지운 금지 분기가 어딘가 되살아난 것이다. 세 환경을 그대로 두고 기대값만 0 으로 맞췄다.
    cases = [
        ("운영자 터미널 (CLAUDECODE 없음)", {}, 0),
        ("Claude Code 세션 (v6.4 · 통과)", {"CLAUDECODE": "1"}, 0),
        ("옛 우회 변수가 있어도 같다", {"CLAUDECODE": "1", "VIDIMUS_PUSH_OK": "1"}, 0),
    ]
    ok = True
    for label, extra, want in cases:
        env = {k: v for k, v in os.environ.items()
               if k not in ("CLAUDECODE", "VIDIMUS_PUSH_OK")}
        env.update(extra)
        # 판정만 시험한다 — 난간들은 제 인수시험이 있고, 여기서 다 돌리면 개시 검사가 선다(작업기록 2026-09-03).
        env["VIDIMUS_HOOK_SELFTEST"] = "1"
        r = subprocess.run([sh, SRC], env=env, capture_output=True, timeout=30)
        hit = r.returncode == want
        ok = ok and hit
        print("  %s %-34s -> 종료코드 %d (기대 %d)"
              % ("OK  " if hit else "FAIL", label, r.returncode, want))
    # 사고 92 — 난간이 stderr 로 한 말이 **훅 밖으로 나오는가.** ③④⑤ 가 `2>&1` 로 두 줄기를
    # 다 버려, 설치된 날부터 push 때 한 번도 말할 수 없었다. 위 세 갈래는 판정(종료코드)만
    # 보므로 그것을 못 잡는다 — 통과 픽스처만 있으면 사고 26 이다. 가짜 난간을 두고 직접 듣는다.
    import tempfile
    # 한 겹 아래에 둔다 — 훅의 `find_guard()` 는 `../*/` 를 훑는데, %TEMP% 직하에서 돌리면
    # 그 폴더 전체(수천 개)를 다섯 번 훑는다. 형제가 하나뿐인 자리에서 돌린다.
    d = os.path.join(tempfile.mkdtemp(), "repo")
    os.makedirs(os.path.join(d, "analysis"))
    with open(os.path.join(d, "analysis", "check_facts.py"), "w", encoding="utf-8") as fh:
        fh.write('import sys\nprint("STUB-92 난간이 말한다", file=sys.stderr)\n')
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "VIDIMUS_PUSH_OK")}
    r = subprocess.run([sh, SRC], env=env, cwd=d, capture_output=True, timeout=60)
    said = "STUB-92" in r.stderr.decode("utf-8", "replace")
    hit = said and r.returncode == 0
    ok = ok and hit
    print("  %s %-34s -> %s · 종료코드 %d (기대 0)"
          % ("OK  " if hit else "FAIL", "난간의 stderr 가 밖으로 나온다(사고 92)",
             "나왔다" if said else "**삼켜졌다**", r.returncode))
    print("통과" if ok else "실패")
    return 0 if ok else 1


def only_arg(argv):
    if "--repo" in argv:
        i = argv.index("--repo")
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--check" in sys.argv:
        sys.exit(check(only_arg(sys.argv)))
    sys.exit(install(only_arg(sys.argv)))

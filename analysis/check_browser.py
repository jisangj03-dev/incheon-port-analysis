"""크롬 확장 가용성 검사 — 「연결 안 됨」을 원인별로 가른다.

MCP 연결 실패 메시지는 원인을 하나로 뭉뚱그린다("설치·로그인·재시작을 확인하라").
그래서 실제 원인이 무엇이든 같은 문장이 나오고, 조용히 죽는다.
이 검사기는 그 앞단을 본다 — 확장이 어느 프로필에 있고, 크롬이 떠 있고,
지금 쓰는 프로필에 확장이 있는가.

사고 36의 처분을 그대로 옮긴 것이다: 실패를 「도달 실패」와 「우리 쪽 이상」으로 가른다.
뭉친 판정은 원인을 바깥에만 있는 것으로 계속 읽게 만든다.

읽는 것: Local State(프로필 이름·last_used·active_time) · Extensions/<id>/ 버전 폴더명.
안 읽는 것: History · Cookies · Login Data · 방문 기록 — 정지선이 아니라 필요가 없어서다.
"""

import io
import json
import os
import subprocess
import sys

try:  # Windows 콘솔(cp949)에서 한글·기호가 깨지지 않게 강제한다. 형제 스크립트 3종과 같은 관례다.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXT_ID = "fcoeoabgfenejglbffodgkkbkcdhcgfn"  # Claude in Chrome
EXT_LABEL = "Claude"

VERDICT_OK = "전제통과"
VERDICT_ASLEEP = "잠듦"
VERDICT_PROFILE = "프로필이상"
VERDICT_MISSING = "미설치"


def user_data_dir():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        return None
    path = os.path.join(base, "Google", "Chrome", "User Data")
    return path if os.path.isdir(path) else None


def chrome_running():
    """tasklist로 본다. 못 물어보면 None — 「아니다」로 단정하지 않는다."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe", "/NH"],
            capture_output=True, text=True, timeout=15,
        ).stdout
    except Exception:
        return None
    return "chrome.exe" in out.lower()


def read_local_state(ud):
    """last_used 프로필 · 표시 이름 · active_time을 읽는다. 실패해도 3-튜플을 지킨다."""
    path = os.path.join(ud, "Local State")
    if not os.path.isfile(path):
        return None, {}, {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return None, {}, {}
    prof = data.get("profile", {})
    cache = prof.get("info_cache", {})
    names = {k: (v or {}).get("name", "") for k, v in cache.items()}
    # active_time을 같이 낸다. 프로필 「이름」으로 용도를 추정하다 틀린 적이 있다(사고 43 추가 관측).
    active = {k: (v or {}).get("active_time") for k, v in cache.items()}
    return prof.get("last_used"), names, active


def ext_versions(ud, profile):
    """해당 프로필에 확장이 있으면 버전 목록을, 없으면 빈 목록을 준다."""
    path = os.path.join(ud, profile, "Extensions", EXT_ID)
    if not os.path.isdir(path):
        return []
    return sorted(d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)))


def profiles(ud):
    out = []
    for name in sorted(os.listdir(ud)):
        if name == "Default" or name.startswith("Profile "):
            if os.path.isdir(os.path.join(ud, name)):
                out.append(name)
    return out


def inspect():
    ud = user_data_dir()
    if ud is None:
        return {"verdict": VERDICT_MISSING, "reason": "크롬 User Data 폴더를 못 찾았다", "ud": None}

    last_used, names, active = read_local_state(ud)
    found = {p: ext_versions(ud, p) for p in profiles(ud)}
    installed = {p: v for p, v in found.items() if v}
    running = chrome_running()

    info = {
        "ud": ud, "last_used": last_used, "names": names, "active": active,
        "found": found, "installed": installed, "running": running,
    }

    if not installed:
        info["verdict"] = VERDICT_MISSING
        info["reason"] = "어느 프로필에도 확장이 없다 — 설치부터 한다"
        return info

    # last_used를 못 읽었으면 프로필 판정을 하지 않는다. 추정으로 통과시키지 않는다.
    if last_used is not None and last_used not in installed:
        info["verdict"] = VERDICT_PROFILE
        label = names.get(last_used, "") or last_used
        info["reason"] = "마지막으로 쓴 프로필 「%s」에 확장이 없다" % label
        return info

    if running is False:
        info["verdict"] = VERDICT_ASLEEP
        info["reason"] = "확장은 제자리인데 크롬이 안 떠 있다"
        return info

    info["verdict"] = VERDICT_OK
    info["reason"] = "확장이 현재 프로필에 있고 크롬이 떠 있다" if running else \
                     "확장이 현재 프로필에 있다 (크롬 실행 여부는 확인 못 했다)"
    return info


def _when(epoch):
    """프로필이 실제로 언제 쓰였는지. 이름으로 용도를 추정하지 않기 위해 낸다."""
    if not epoch:
        return "[미확인]"
    import datetime
    try:
        return datetime.datetime.fromtimestamp(int(epoch)).strftime("%Y-%m-%d")
    except Exception:
        return "[미확인]"

EXIT = {VERDICT_OK: 0, VERDICT_ASLEEP: 1, VERDICT_PROFILE: 2, VERDICT_MISSING: 2}


def report(info):
    print("== 크롬 확장 가용성 ==")
    if info.get("ud"):
        for prof, vers in sorted(info.get("found", {}).items()):
            label = info.get("names", {}).get(prof, "") or prof
            mark = "  <- 마지막 사용" if prof == info.get("last_used") else ""
            state = ("%s %s" % (EXT_LABEL, ", ".join(vers))) if vers else "확장 없음"
            print("  [%s] %s — %s%s" % (prof, label, state, mark))
            print("      마지막 활동: %s" % _when(info.get("active", {}).get(prof)))
        running = info.get("running")
        print("  크롬 프로세스: %s" % {True: "실행 중", False: "실행 안 됨", None: "확인 못 함"}[running])
    print()
    print("판정: %s — %s" % (info["verdict"], info["reason"]))

    v = info["verdict"]
    if v == VERDICT_OK:
        print("  -> **아직 「연결됨」이 아니다.** 이 검사는 전제 조건만 본다 —")
        print("     확장 로그인·claude.ai 계정 일치·핸드셰이크는 **보지 못한다.**")
        print("     다음 수: `tabs_context_mcp` 를 실제로 쳐서 연결을 확인한다. 둘 다 쳐야 갈린다.")
    elif v == VERDICT_ASLEEP:
        print("  -> 크롬을 켜면 된다. 브라우저 도구를 쓰기 전에 켜라.")
    elif v == VERDICT_PROFILE:
        print("  -> 확장이 있는 프로필로 바꾸거나, 지금 프로필에 확장을 설치한다.")
        print("     설치된 프로필: %s" % ", ".join(sorted(info.get("installed", {}))))
        print("     **MCP 오류 문구는 프로필을 언급하지 않는다. 그래서 이 검사가 있다.**")
    elif v == VERDICT_MISSING:
        print("  -> https://claude.ai/chrome 에서 설치한다. 설치 후 크롬 재시작.")
    return EXIT[v]


def selftest():
    """판정 네 갈래가 실제로 갈리는지 본다. 한쪽만 시험하면 규칙을 껐는지 고쳤는지 모른다(사고 34)."""
    print("== 인수시험: 판정 분기 ==")
    cases = [
        ("미설치", {"ud": "x", "last_used": "Default", "names": {}, "found": {"Default": []},
                    "installed": {}, "running": True}, VERDICT_MISSING),
        ("프로필이상", {"ud": "x", "last_used": "Profile 1", "names": {"Profile 1": "물류로그"},
                        "found": {"Default": ["1.0.85_0"], "Profile 1": []},
                        "installed": {"Default": ["1.0.85_0"]}, "running": True}, VERDICT_PROFILE),
        ("잠듦", {"ud": "x", "last_used": "Default", "names": {},
                  "found": {"Default": ["1.0.85_0"]},
                  "installed": {"Default": ["1.0.85_0"]}, "running": False}, VERDICT_ASLEEP),
        ("전제통과", {"ud": "x", "last_used": "Default", "names": {},
                  "found": {"Default": ["1.0.85_0"]},
                  "installed": {"Default": ["1.0.85_0"]}, "running": True}, VERDICT_OK),
    ]
    ok = True
    for label, info, want in cases:
        got = _classify(info)
        mark = "OK" if got == want else "FAIL"
        if got != want:
            ok = False
        print("  %s %-8s -> %s (기대 %s)" % (mark, label, got, want))
    # 판정이 갈리는 것만으로는 모자란다. **전제통과일 때 「아직 연결 아님」이 실제로 발화하는지** 본다.
    # 이 규칙을 문장으로만 뒀더니 사람이 나르는 규칙이 됐다(§0-3). 그래서 시험으로 못 지우게 한다.
    import contextlib
    buf = io.StringIO()
    ok_info = {"ud": "x", "last_used": "Default", "names": {}, "active": {},
               "found": {"Default": ["1.0.85_0"]}, "installed": {"Default": ["1.0.85_0"]},
               "running": True, "verdict": VERDICT_OK, "reason": "r"}
    with contextlib.redirect_stdout(buf):
        report(ok_info)
    said = "이 검사는 전제 조건만 본다" in buf.getvalue() and "tabs_context_mcp" in buf.getvalue()
    print("  %s 전제통과 안내 발화 -> %s" % ("OK" if said else "FAIL", said))
    ok = ok and said

    print("통과" if ok else "실패")
    return 0 if ok else 1


def _classify(info):
    """inspect()의 판정부만 떼어낸 것. 시험이 실물 크롬에 의존하지 않게 한다."""
    if not info.get("installed"):
        return VERDICT_MISSING
    last_used = info.get("last_used")
    if last_used is not None and last_used not in info["installed"]:
        return VERDICT_PROFILE
    if info.get("running") is False:
        return VERDICT_ASLEEP
    return VERDICT_OK


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(report(inspect()))

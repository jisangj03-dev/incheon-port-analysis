# -*- coding: utf-8 -*-
"""세션 스냅샷 — 인수인계를 세션 끝의 사람 동작에서 떼어 **매 턴의 부작용**으로 만든다.

왜 있는가
---------
2026-09-07 마지막 세션이 사용 한도로 끊겼다(14:40 KST). 그 세션은 STATUS·사고기록·작업기록을
고치고 측심 저장소의 코드를 고쳤는데 **둘 다 커밋 전이었고**, 「다음 세션이 이어서 일할 수 있게
STATUS 를 닫는」 동작은 세션 **끝**에 사람이 하는 일이라 끊긴 순간 같이 사라졌다.
다음 세션은 `git status` 로 미커밋 파일을 보고 경위를 **추정**해야 했다(사고 96).

사고 22 의 얼굴이다 — **사람이 나르는 규칙은 유실된다.** 그래서 나르지 않는다.
Claude Code 훅이 턴마다 이 파일을 불러 스냅샷을 쓰고, 세션이 열릴 때 그것을 문맥에 넣는다.

무엇을 하는가
-------------
  --prompt   UserPromptSubmit 훅. 지시문·시각·저장소 셋의 상태를 적고 **턴을 연다**.
  --stop     Stop / SessionEnd 훅. 마지막 보고(대화록에서 뽑는다)·손댄 파일·저장소 상태를 적고 **턴을 닫는다**.
  --show     SessionStart 훅. 스냅샷을 찍어 낸다 — 표준 출력이 그대로 문맥에 들어간다.
             턴이 열린 채면 **「끝나지 않은 채 끊겼다」**를 첫 줄에 낸다.
  --check    개시 검사(boot_check). 저장소 셋의 미커밋 파일 수와 마지막 턴의 종료 여부를 한 줄로.
  --selftest 인수시험.

  스냅샷 = `analysis/_session_snapshot.json`(기계) · `analysis/_session_snapshot.md`(사람).
  둘 다 추적하지 않는다(.gitignore) — 이 기계의 상태이지 저장소의 상태가 아니다.

닿지 않는 곳
------------
· **턴 도중에 끊기면 그 턴의 보고는 없다.** 지시문과 시작 시점의 저장소 상태, 그리고 지금의
  `git status` 차이만 남는다 — 그것이 「어디까지 갔나」의 하한이다. 상한은 대화록이 든다.
· 대화록 형식(JSONL · `type`/`message.content`)이 바뀌면 보고 추출이 빈다. 그때도 훅은 죽지 않고
  저장소 상태만 적는다 — **훅이 죽으면 작업 전체를 죽인다**(hook_stopline 의 같은 원칙).
· 이것은 STATUS 를 대신하지 않는다. STATUS 는 **판단**이고 이것은 **관측**이다.
"""

import argparse
import io
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PARENT = os.path.dirname(ROOT)

# 작업 폴더 셋(CLAUDE.md). 없는 폴더는 「없음」으로 적고 넘어간다.
REPOS = (
    ("인천항물동량", ROOT),
    ("허브", os.path.join(PARENT, "jisangj03-dev.github.io")),
    ("측심", os.path.join(PARENT, "sounding")),
)

SNAP_JSON = os.path.join(HERE, "_session_snapshot.json")
SNAP_MD = os.path.join(HERE, "_session_snapshot.md")

PROMPT_MAX = 700      # 지시문은 앞부분만 — 전문은 대화록에 있다
REPORT_MAX = 1800     # 마지막 보고도 앞부분만
FILES_MAX = 40
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def now_local():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def iso_to_local(s):
    """대화록의 UTC ISO 시각 → 이 기계의 지역 시각. 못 읽으면 원문."""
    try:
        d = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        return d.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return s


# ── git ─────────────────────────────────────────────────────────────────────

def git(path, *args, timeout=20):
    try:
        p = subprocess.run(["git", "-c", "core.quotepath=false"] + list(args), cwd=path,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except Exception as e:
        return 99, "%s: %s" % (type(e).__name__, e)


def git_state(path):
    """한 저장소의 HEAD · 가지 · 미커밋 목록. 저장소가 아니면 None."""
    if not os.path.isdir(os.path.join(path, ".git")):
        return None
    rc, head = git(path, "rev-parse", "--short", "HEAD")
    rc2, branch = git(path, "rev-parse", "--abbrev-ref", "HEAD")
    rc3, st = git(path, "status", "--porcelain", "--untracked-files=normal")
    dirty = []
    if rc3 == 0:
        for line in st.splitlines():
            if not line.strip():
                continue
            # 미리보기·촬영 산출물은 .gitignore 가 걸러 준다. 남은 untracked 는 진짜 새 파일이다.
            dirty.append((line[:2].strip() or "?", line[3:].strip()))
    return {
        "head": head.strip() if rc == 0 else "?",
        "branch": branch.strip() if rc2 == 0 else "?",
        "dirty": dirty[:FILES_MAX],
        "dirty_n": len(dirty),
        "ok": rc == 0 and rc3 == 0,
    }


def repos_state():
    out = []
    for name, path in REPOS:
        s = git_state(path)
        out.append({"name": name, "path": path, "state": s})
    return out


# ── 대화록 ─────────────────────────────────────────────────────────────────

def _blocks(msg):
    c = (msg or {}).get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return c if isinstance(c, list) else []


def transcript_summary(path):
    """마지막 사람 지시 · 마지막 보고(assistant 텍스트) · 손댄 파일. 못 읽으면 빈 값."""
    res = {"last_prompt": "", "last_prompt_ts": "", "last_report": "", "last_report_ts": "",
           "touched": [], "rows": 0}
    if not path or not os.path.exists(path):
        return res
    touched = []
    seen = set()
    last_assistant_text = []
    last_assistant_ts = ""
    pending_text = []
    pending_ts = ""
    try:
        with io.open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                res["rows"] += 1
                t = r.get("type")
                if t == "user":
                    blocks = _blocks(r.get("message"))
                    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
                    is_tool_result = any(b.get("type") == "tool_result" for b in blocks)
                    txt = "\n".join(texts).strip()
                    # 도구 결과·시스템 알림은 지시가 아니다.
                    if txt and not is_tool_result and not txt.startswith("<"):
                        res["last_prompt"] = txt[:PROMPT_MAX]
                        res["last_prompt_ts"] = iso_to_local(r.get("timestamp", ""))
                        # 새 지시가 오면 그 앞 보고는 「마지막」이 아니다 — 다시 모은다.
                        if pending_text:
                            last_assistant_text, last_assistant_ts = pending_text, pending_ts
                        pending_text, pending_ts = [], ""
                elif t == "assistant":
                    for b in _blocks(r.get("message")):
                        if b.get("type") == "text" and b.get("text", "").strip():
                            pending_text.append(b["text"].strip())
                            pending_ts = iso_to_local(r.get("timestamp", ""))
                        elif b.get("type") == "tool_use" and b.get("name") in EDIT_TOOLS:
                            fp = (b.get("input") or {}).get("file_path") or (b.get("input") or {}).get("notebook_path")
                            if fp and fp not in seen:
                                seen.add(fp)
                                touched.append(fp)
    except Exception:
        pass
    if pending_text:
        last_assistant_text, last_assistant_ts = pending_text, pending_ts
    # 마지막 보고 = 마지막 지시 뒤 assistant 텍스트 중 **끝의 것**(중간 진행 문장은 뺀다).
    if last_assistant_text:
        res["last_report"] = last_assistant_text[-1][:REPORT_MAX]
        res["last_report_ts"] = last_assistant_ts
    res["touched"] = touched[-FILES_MAX:]
    return res


# ── 스냅샷 ─────────────────────────────────────────────────────────────────

def load():
    try:
        with io.open(SNAP_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save(snap):
    tmp = SNAP_JSON + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, SNAP_JSON)
    with io.open(SNAP_MD, "w", encoding="utf-8") as fh:
        fh.write(render(snap))


def render(snap, live=None):
    """사람이 읽는 마크다운. live 가 있으면 「지금」 절을 덧붙인다(--show)."""
    L = []
    open_turn = snap.get("turn_open")
    sid = (snap.get("session_id") or "")[:8]
    L.append("# 세션 스냅샷 — 훅이 자동으로 쓴다(`analysis/session_snapshot.py`). 기억이 아니라 관측이다.")
    if not snap:
        L.append("(아직 스냅샷이 없다 — 이 기계에서 훅이 처음 돈다.)")
        return "\n".join(L) + "\n"
    state = "**끝나지 않은 채 끊겼다 — 마지막 보고가 없다. 미커밋 파일이 그 턴의 흔적이다**" if open_turn else "끝남"
    L.append("갱신 %s · 세션 %s · 마지막 턴: %s" % (snap.get("updated", "?"), sid or "?", state))
    if snap.get("prompt"):
        L.append("")
        L.append("## 마지막 지시 (%s)" % snap.get("prompt_ts", "?"))
        L.append("> " + snap["prompt"].replace("\n", "\n> "))
    if snap.get("report"):
        L.append("")
        L.append("## 마지막 보고 (턴 끝 %s)" % snap.get("stop_ts", "?"))
        L.append(snap["report"])
    if snap.get("touched"):
        L.append("")
        L.append("## 그 세션에서 편집 도구가 연 파일 (대화록 기준 · 최근 %d개까지)" % FILES_MAX)
        for f in snap["touched"]:
            L.append("- `%s`" % f)
    L.append("")
    L.append("## 저장소 셋 — %s 시점" % ("턴 끝" if not open_turn else "턴 시작"))
    L.extend(_repo_lines(snap.get("repos") or []))
    if live is not None:
        L.append("")
        L.append("## 지금 (세션 시작 %s)" % now_local())
        L.extend(_repo_lines(live))
        L.append("")
        L.append(verdict(snap, live))
    return "\n".join(L) + "\n"


def _repo_lines(repos):
    out = []
    for r in repos:
        s = r.get("state")
        if s is None:
            out.append("- %s: 저장소 없음 (`%s`)" % (r["name"], r["path"]))
            continue
        if s["dirty_n"] == 0:
            out.append("- %s `%s` %s · 미커밋 0" % (r["name"], s["head"], s["branch"]))
        else:
            files = " · ".join("%s %s" % (k, p) for k, p in s["dirty"][:12])
            more = " …(+%d)" % (s["dirty_n"] - 12) if s["dirty_n"] > 12 else ""
            out.append("- %s `%s` %s · **미커밋 %d**: %s%s" % (r["name"], s["head"], s["branch"], s["dirty_n"], files, more))
    return out


def verdict(snap, live):
    """세션 시작 때 첫 줄로 낼 판정 하나."""
    dirty = sum((r.get("state") or {}).get("dirty_n", 0) for r in live)
    if snap.get("turn_open"):
        return ("**판정: 이전 세션이 턴 도중에 끊겼다.** 위 「마지막 지시」가 무엇을 시켰고 미커밋 %d 파일이 어디까지 갔는지를 "
                "`git diff` 로 먼저 본다. STATUS 의 「착수점」은 그 턴 **이전** 상태다." % dirty)
    if dirty:
        return ("**판정: 이전 세션은 턴을 끝냈으나 미커밋 파일이 %d 있다.** 「마지막 보고」가 그것을 설명하는지 본다 — "
                "설명하지 않으면 커밋 전에 끊긴 것이다(사고 96)." % dirty)
    return "판정: 이전 세션은 턴을 끝냈고 세 저장소가 깨끗하다. STATUS 「착수점」대로 간다."


def read_payload():
    try:
        raw = sys.stdin.buffer.read()
        if not raw.strip():
            return {}
        return json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        return {}


# ── 훅 진입점 ─────────────────────────────────────────────────────────────

def on_prompt(payload):
    snap = load()
    prompt = (payload.get("prompt") or "").strip()
    if prompt.startswith("<"):
        # 명령 출력·시스템 블록은 지시가 아니다. 앞의 것을 지키고 시각만 민다.
        prompt = snap.get("prompt", "")
    snap.update({
        "session_id": payload.get("session_id") or snap.get("session_id"),
        "transcript": payload.get("transcript_path") or snap.get("transcript"),
        "prompt": prompt[:PROMPT_MAX],
        "prompt_ts": now_local(),
        "turn_open": True,
        "report": "",           # 새 턴 — 옛 보고는 이 턴의 보고가 아니다
        "stop_ts": "",
        "updated": now_local(),
        "repos": repos_state(),
    })
    save(snap)


def on_stop(payload, reason=""):
    snap = load()
    tp = payload.get("transcript_path") or snap.get("transcript")
    ts = transcript_summary(tp)
    snap.update({
        "session_id": payload.get("session_id") or snap.get("session_id"),
        "transcript": tp,
        "turn_open": False,
        "stop_ts": now_local() + ((" · " + reason) if reason else ""),
        "report": ts["last_report"] or snap.get("report", ""),
        "touched": ts["touched"] or snap.get("touched", []),
        "updated": now_local(),
        "repos": repos_state(),
    })
    if not snap.get("prompt") and ts["last_prompt"]:
        snap["prompt"], snap["prompt_ts"] = ts["last_prompt"], ts["last_prompt_ts"]
    save(snap)


def show():
    snap = load()
    print(render(snap, live=repos_state()))


def check():
    """개시 검사 한 줄. 종료코드는 0 — 미커밋은 실패가 아니라 **보고할 사실**이다."""
    snap = load()
    live = repos_state()
    parts = []
    for r in live:
        s = r.get("state")
        if s is None:
            parts.append("%s 없음" % r["name"])
        elif s["dirty_n"]:
            parts.append("%s 미커밋 %d" % (r["name"], s["dirty_n"]))
    if not snap:
        turn = "스냅샷 없음(훅이 아직 안 돌았다)"
    elif snap.get("turn_open"):
        turn = "마지막 턴 미종료(%s 시작 · 끊김)" % snap.get("prompt_ts", "?")
    else:
        turn = "마지막 턴 끝남(%s)" % (snap.get("stop_ts", "?"))
    print("세 저장소: " + (" · ".join(parts) if parts else "전부 깨끗") + " · " + turn)
    return 0


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest():
    import tempfile
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-56s %s" % ("OK  " if good else "FAIL", label, "" if good else "-> %r (기대 %r)" % (got, want)))

    global SNAP_JSON, SNAP_MD
    keep = (SNAP_JSON, SNAP_MD)
    with tempfile.TemporaryDirectory() as d:
        SNAP_JSON = os.path.join(d, "s.json")
        SNAP_MD = os.path.join(d, "s.md")

        print("── 인수시험: 대화록에서 지시·보고·손댄 파일을 뽑는가 ──")
        tp = os.path.join(d, "t.jsonl")
        rows = [
            {"type": "user", "timestamp": "2026-09-07T05:00:00.000Z", "message": {"content": "첫 지시"}},
            {"type": "assistant", "timestamp": "2026-09-07T05:01:00.000Z", "message": {"content": [{"type": "text", "text": "진행 중"}, {"type": "tool_use", "name": "Write", "input": {"file_path": "a.md"}}]}},
            {"type": "user", "timestamp": "2026-09-07T05:01:10.000Z", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
            {"type": "assistant", "timestamp": "2026-09-07T05:02:00.000Z", "message": {"content": [{"type": "text", "text": "첫 보고"}]}},
            {"type": "user", "timestamp": "2026-09-07T05:10:00.000Z", "message": {"content": [{"type": "text", "text": "둘째 지시"}]}},
            {"type": "user", "timestamp": "2026-09-07T05:10:01.000Z", "message": {"content": "<task-notification>x</task-notification>"}},
            {"type": "assistant", "timestamp": "2026-09-07T05:11:00.000Z", "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "b.py"}}]}},
            {"type": "assistant", "timestamp": "2026-09-07T05:12:00.000Z", "message": {"content": [{"type": "text", "text": "중간 문장"}]}},
            {"type": "assistant", "timestamp": "2026-09-07T05:13:00.000Z", "message": {"content": [{"type": "text", "text": "둘째 보고 — 끝"}]}},
        ]
        with io.open(tp, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        s = transcript_summary(tp)
        chk("마지막 지시는 사람 지시다(알림·도구 결과 제외)", s["last_prompt"], "둘째 지시")
        chk("마지막 보고는 마지막 지시 뒤 끝 문장", s["last_report"], "둘째 보고 — 끝")
        chk("손댄 파일 둘(순서대로)", s["touched"], ["a.md", "b.py"])
        chk("행 수", s["rows"], 9)
        chk("UTC → 지역 시각 변환이 돈다", len(s["last_prompt_ts"]), 16)
        chk("없는 대화록은 빈 값", transcript_summary(os.path.join(d, "no.jsonl"))["rows"], 0)

        print("── 인수시험: 턴을 열고 닫는가 ──")
        on_prompt({"session_id": "abcdefgh-1", "transcript_path": tp, "prompt": "셋째 지시"})
        snap = load()
        chk("턴이 열린다", snap["turn_open"], True)
        chk("지시가 적힌다", snap["prompt"], "셋째 지시")
        chk("새 턴은 옛 보고를 비운다", snap["report"], "")
        chk("저장소 셋을 본다", len(snap["repos"]), 3)
        md = io.open(SNAP_MD, encoding="utf-8").read()
        chk("열린 채면 「끊겼다」를 쓴다", "끊겼다" in md, True)
        on_stop({"session_id": "abcdefgh-1", "transcript_path": tp})
        snap = load()
        chk("턴이 닫힌다", snap["turn_open"], False)
        chk("보고가 대화록에서 채워진다", snap["report"], "둘째 보고 — 끝")
        md = io.open(SNAP_MD, encoding="utf-8").read()
        chk("닫힌 뒤엔 「끝남」", "마지막 턴: 끝남" in md, True)
        chk("--show 판정이 셋 중 하나", verdict(snap, snap["repos"]).startswith(("**판정", "판정")), True)

        print("── 인수시험: 시스템 블록은 지시로 안 적는다 ──")
        on_prompt({"session_id": "abcdefgh-1", "transcript_path": tp, "prompt": "<command-name>/x</command-name>"})
        chk("앞의 지시를 지킨다", load()["prompt"], "셋째 지시")

        print("── 인수시험: 깨진 입력에 죽지 않는가 ──")
        on_stop({})
        chk("빈 입력도 닫힌다", load()["turn_open"], False)
        with io.open(SNAP_JSON, "w", encoding="utf-8") as fh:
            fh.write("{깨진")
        chk("깨진 스냅샷은 빈 것으로 읽는다", load(), {})

        print("── 인수시험: git 상태 읽기 ──")
        g = os.path.join(d, "g")
        os.makedirs(g)
        subprocess.run(["git", "init", "-q", g], check=True)
        io.open(os.path.join(g, "x.txt"), "w").write("x")
        st = git_state(g)
        chk("새 파일은 미커밋으로 센다", st["dirty_n"], 1)
        chk("저장소 아닌 곳은 None", git_state(d), None)

    SNAP_JSON, SNAP_MD = keep
    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="세션 스냅샷 — 훅이 턴마다 쓴다.")
    ap.add_argument("--prompt", action="store_true", help="UserPromptSubmit 훅")
    ap.add_argument("--stop", action="store_true", help="Stop 훅")
    ap.add_argument("--end", action="store_true", help="SessionEnd 훅")
    ap.add_argument("--show", action="store_true", help="SessionStart 훅 — 문맥에 넣는다")
    ap.add_argument("--check", action="store_true", help="개시 검사 한 줄")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.check:
        return check()
    if a.show:
        show()
        return 0
    # 훅 경로 — 무슨 일이 있어도 0 으로 끝난다. 훅이 죽으면 작업을 죽인다.
    try:
        payload = read_payload()
        if a.prompt:
            on_prompt(payload)
        elif a.stop:
            on_stop(payload)
        elif a.end:
            on_stop(payload, reason="세션 종료 " + str(payload.get("reason", "")))
    except Exception as e:
        try:
            print("session_snapshot: %s" % e, file=sys.stderr)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

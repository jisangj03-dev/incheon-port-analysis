# -*- coding: utf-8 -*-
"""발행 대기열 — **무엇이 어느 채널에 준비됐고 무엇이 안 올라갔는가.**

왜 있는가
---------
게시는 **세션 하나로 안 끝난다.** 문안을 쓰는 세션, 검사하는 세션, 승인을 받는 순간,
실제로 누르는 순간이 전부 다른 시각에 있고 **그 사이에 세션이 끊긴다**(사고 96).
끊기고 나면 다음 세션은 「무엇이 이미 나갔나」를 추정해야 하는데,
**추정으로 두 번 올리면 GeekNews 에서는 두 시간 뒤 못 지운다.**

그래서 상태를 **파일 하나**에 둔다. 세션이 아니라 파일이 기억한다.

  python analysis/channel_queue.py                 # 「지금 뭐 대기 중이야」 — 폰에서 읽는 그것
  python analysis/channel_queue.py --check [--net] # 대기 중인 것 전부 검사 → 검증 칸 갱신
  python analysis/channel_queue.py --before-post <id>   # 누르기 직전 점검(중복 확인용 첫 줄)
  python analysis/channel_queue.py --set <id> --state 게시됨 --url <주소>
  python analysis/channel_queue.py --selftest

상태 다섯
---------
  초안     문안이 있다. 검사 안 했다
  준비     검사 통과. **승인만 받으면 나간다**
  승인대기  운영자에게 전문을 보였다. 답을 기다린다
  게시됨    나갔다. `url` 이 있다
  보류     안 올린다. `note` 에 이유

닿지 않는 곳
------------
· **이 파일은 우리가 적는 것이다. 채널에 실제로 글이 있는지는 안 본다** —
  「게시됨」은 **우리가 눌렀다는 기록**이지 채널의 상태가 아니다. 확인은 `url` 을 여는 것이다.
  **2026-09-10 에 이 한계가 실제로 물었다** — 운영자가 파이프라인 밖에서 li-01 을 올렸는데
  대기열은 `준비` 를 들고 있었다. 대기열만 보고 눌렀으면 같은 글이 두 번 나갔다.
  **채널을 훑는 검사기는 못 만든다**(자격 증명을 안 다룬다). 대신 `--before-post` 가
  **채널에서 찾을 첫 줄**을 내놓는다 — 사람이 기억하는 대신 그것을 찾는다.
· 문안 본문은 `본부\채널문안\` 이 든다. 여기는 **상태만** 든다(사본은 갈라진다).
· 순서를 강제하지 않는다 — 무엇을 먼저 올릴지는 판단이다.
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
sys.path.insert(0, HERE)
import channels as CH  # noqa: E402

QUEUE = os.path.join(ROOT, "docs", "채널대기열.md")
HQ = os.path.join(os.path.expanduser("~"), "OneDrive", "문서", "본부")
DRAFTS = os.path.join(HQ, "채널문안")

STATES = ("초안", "준비", "승인대기", "게시됨", "보류")
COLS = ("id", "채널", "무엇", "상태", "검증", "문안", "주소", "갱신", "메모")

HEADER = """# 채널 대기열

> **무엇이 어느 채널에 준비됐고 무엇이 안 올라갔는가.** 이 파일이 든다 — 세션이 아니라.
> 읽기 `python analysis/channel_queue.py` · 검사 `--check [--net]` · 갱신 `--set <id> --state <상태>`
>
> **상태 다섯** — `초안`(검사 전) · `준비`(검사 통과 · 승인만 받으면 나간다) ·
> `승인대기`(전문을 보이고 답 대기) · `게시됨`(눌렀다 · `주소` 있음) · `보류`(안 올린다 · 사유는 메모).
>
> **「게시됨」은 우리가 눌렀다는 기록이지 채널의 상태가 아니다.** 확인은 주소를 여는 것이다.
> 문안 본문은 `본부\\채널문안\\` 이 든다 — 공개 저장소에 원고를 안 넣는다(지침 §4.1).
> **유입 수는 여기 안 든다**(§4.1-3 채널 성과 원자료는 비공개) — `channel_inflow.py` 가 본부에 쓴다.

<!-- 대기열:시작 -->
"""

FOOTER = "<!-- 대기열:끝 -->\n"


def _now():
    return time.strftime("%Y-%m-%d")


def read():
    """반환 (행 목록, 머리말, 꼬리말). 파일이 없으면 빈 대기열."""
    if not os.path.exists(QUEUE):
        return [], HEADER, FOOTER
    raw = io.open(QUEUE, encoding="utf-8").read().replace("\r\n", "\n")
    i = raw.find("<!-- 대기열:시작 -->")
    j = raw.find("<!-- 대기열:끝 -->")
    if i < 0 or j < 0:
        raise ValueError("대기열 표지(<!-- 대기열:시작/끝 -->)가 없다: %s" % QUEUE)
    head = raw[:i + len("<!-- 대기열:시작 -->")] + "\n"
    tail = raw[j:]
    rows = []
    for line in raw[i:j].split("\n"):
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < len(COLS) or c[0] in ("id", "---") or set(c[0]) <= {"-", ":"}:
            continue
        rows.append(dict(zip(COLS, c[:len(COLS)])))
    return rows, head, tail


def write(rows, head, tail):
    body = ["", "| " + " | ".join(COLS) + " |",
            "|" + "|".join(["---"] * len(COLS)) + "|"]
    for r in rows:
        body.append("| " + " | ".join((r.get(k, "") or "").replace("|", "/") for k in COLS) + " |")
    body.append("")
    io.open(QUEUE, "w", encoding="utf-8", newline="\n").write(head + "\n".join(body) + tail)


def draft_path(row):
    f = (row.get("문안") or "").strip().strip("`")
    if not f:
        return None
    p = f if os.path.isabs(f) else os.path.join(DRAFTS, f)
    return p if os.path.exists(p) else None


# ── 「지금 뭐 대기 중이야」 ─────────────────────────────────────────────────

def status():
    rows, _, _ = read()
    if not rows:
        print("대기열이 비었다. (`%s`)" % os.path.relpath(QUEUE, ROOT).replace("\\", "/"))
        return 0
    by = {s: [r for r in rows if r.get("상태") == s] for s in STATES}
    other = [r for r in rows if r.get("상태") not in STATES]

    print("== 채널 대기열 ==")
    # **가장 먼저 알아야 할 것을 먼저 찍는다** — 폰에서 첫 줄만 보고 판단한다.
    ready = by["준비"]
    waiting = by["승인대기"]
    def once(row):
        """되돌릴 수 없는 채널은 **어느 목록에 있든** 그렇게 적는다 — 승인 직전이 가장 중요한 자리다."""
        c = CH.CHANNELS.get(row.get("채널"), {})
        if c.get("되돌릴수있나", True):
            return ""
        return "  ← **되돌릴 수 없다**(삭제 유예 %s)" % c.get("삭제유예", "[미확인]")

    if waiting:
        print("\n**승인을 기다린다 %d건 — 답 한 마디면 나간다**" % len(waiting))
        for r in waiting:
            print("   %-8s %-10s %s%s" % (r["id"], r["채널"], r["무엇"], once(r)))
    if ready:
        print("\n**나갈 준비가 됐다 %d건**" % len(ready))
        for r in ready:
            print("   %-8s %-10s %s%s" % (r["id"], r["채널"], r["무엇"], once(r)))
    if by["초안"]:
        print("\n검사 안 한 초안 %d건 — `--check` 로 검사한다" % len(by["초안"]))
        for r in by["초안"]:
            print("   %-8s %-10s %s  (%s)" % (r["id"], r["채널"], r["무엇"], r.get("검증") or "미검사"))
    if by["보류"]:
        print("\n보류 %d건" % len(by["보류"]))
        for r in by["보류"]:
            print("   %-8s %-10s %s — %s" % (r["id"], r["채널"], r["무엇"], r.get("메모") or ""))
    if by["게시됨"]:
        print("\n나갔다 %d건" % len(by["게시됨"]))
        for r in by["게시됨"]:
            print("   %-8s %-10s %s  %s" % (r["id"], r["채널"], r.get("갱신") or "",
                                            (r.get("주소") or "")[:60]))
    if other:
        print("\n**모르는 상태 %d건** — 상태 다섯 중 하나여야 한다" % len(other))
        for r in other:
            print("   %-8s 상태=%r" % (r["id"], r.get("상태")))

    print("\n" + "-" * 62)
    print("전체 %d · 준비 %d · 승인대기 %d · 초안 %d · 게시됨 %d · 보류 %d"
          % (len(rows), len(ready), len(waiting), len(by["초안"]),
             len(by["게시됨"]), len(by["보류"])))
    if not ready and not waiting:
        print("**지금 나갈 것은 없다.**")
    return 0


# ── 검사 ────────────────────────────────────────────────────────────────────

def check(net=False):
    rows, head, tail = read()
    todo = [r for r in rows if r.get("상태") in ("초안", "준비", "승인대기")]
    if not todo:
        print("검사할 것이 없다 — 대기 중인 항목이 없다.")
        return 0
    print("== 대기 중인 문안 %d건을 검사한다 ==" % len(todo))
    script = os.path.join(HERE, "channel_post.py")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    bad = 0
    for r in todo:
        p = draft_path(r)
        if not p:
            r["검증"] = "문안없음"
            r["갱신"] = _now()
            print("\n── %s  **문안 파일이 없다**: %s" % (r["id"], r.get("문안")))
            bad += 1
            continue
        args = [sys.executable, script, "--check", p] + (["--net"] if net else [])
        try:
            pr = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", timeout=180, env=env)
            out = pr.stdout or ""
        except Exception as e:
            r["검증"] = "모름"
            r["갱신"] = _now()
            print("\n── %s  [미확인] 못 돌렸다: %s" % (r["id"], e))
            continue
        print(out.rstrip())
        v = "FAIL" if pr.returncode else ("PASS" if "판정: **PASS**" in out else "WARN")
        r["검증"] = "%s(%s)" % (v, "net" if net else "무망")
        r["갱신"] = _now()
        if v == "FAIL":
            bad += 1
            if r["상태"] == "준비":
                r["상태"] = "초안"      # **통과했던 것이 깨지면 준비에서 내린다**
        elif r["상태"] == "초안":
            r["상태"] = "준비"
    write(rows, head, tail)
    print("\n" + "-" * 62)
    print("검사 %d건 · FAIL %d건. 대기열 갱신함." % (len(todo), bad))
    if not net:
        print("**링크와 카드는 안 쳤다**(`--net` 이 친다). 「무망」은 그 뜻이다.")
    return 1 if bad else 0


def before_post(rid):
    """**누르기 직전에 치는 것.** 채널 규칙 · 되돌릴 수 있는가 · **중복 확인용 첫 줄**.

    2026-09-10 실측: 운영자가 파이프라인 밖에서 li-01 을 올렸는데 **대기열은 그것을 몰랐다**
    — 「게시됨」은 우리가 눌렀다는 기록이지 채널의 상태가 아니기 때문이다(이 파일의 한계 절).
    대기열만 보고 눌렀으면 같은 글이 두 번 나갔다.

    **채널을 훑는 검사기는 못 만든다**(로그인·자격 증명은 안 다룬다). 그래서 대신
    **찾을 문자열을 기계가 내놓는다** — 사람이 기억하는 대신 그것을 채널에서 찾는다.
    """
    rows, _, _ = read()
    hit = [r for r in rows if r.get("id") == rid]
    if len(hit) != 1:
        print("**일치 %d건 — 그런 id 가 없다.** id=%r" % (len(hit), rid))
        return 2
    r = hit[0]
    ch = CH.CHANNELS.get(r.get("채널"), {})
    p = draft_path(r)
    print("== 게시 직전 점검 — %s (%s) ==" % (rid, ch.get("이름", r.get("채널"))))
    print("  무엇: %s" % r.get("무엇"))
    print("  상태: %s · 검증: %s" % (r.get("상태"), r.get("검증") or "미검사"))
    if r.get("상태") == "게시됨":
        print("\n  **이미 게시됨으로 적혀 있다** — 주소 %s" % r.get("주소"))
        return 2
    if not p:
        print("\n  **문안 파일이 없다**: %s" % r.get("문안"))
        return 2

    import channel_post as CP
    meta, body = CP.parse(p)
    first = body.strip().split("\n")[0].strip()
    print("\n  ── 중복 확인 ──")
    print("  **채널에서 이 줄을 먼저 찾는다. 있으면 누르지 않는다.**")
    print("    「%s」" % first)
    print("  (대기열은 채널을 안 본다 — 밖에서 올린 것을 모른다. 2026-09-10 에 실제로 그랬다.)")

    print("\n  ── 이 채널에서 알아야 하는 것 ──")
    if not ch.get("되돌릴수있나", True):
        print("  **되돌릴 수 없다** — 삭제 유예 %s · 수정 없음. **전문을 보이고 승인받는다.**"
              % ch.get("삭제유예", "[미확인]"))
    else:
        print("  되돌릴 수 있다(수정·삭제 가능). 그래도 승인 뒤에 누른다.")
    if ch.get("선행조건"):
        print("  선행 조건: **%s**" % ch["선행조건"])
    for m in ch.get("메모", []):
        print("  · %s" % m)

    print("\n  ── 붙여넣을 것 ──")
    if meta.get("title"):
        print("  제목(%d자): %s" % (len(meta["title"]), meta["title"]))
    print("  본문 %d자 · 줄 %d · 링크 %d개" % (len(body), body.count("\n") + 1, len(CH.urls(body))))
    print("  파일: %s" % p)
    print("\n  붙여넣은 뒤 **화면의 글자를 이 파일과 대조한다** — 한글이 빠지는 일이 있다.")
    return 0


def setrow(rid, state=None, url=None, note=None, verify=None):
    rows, head, tail = read()
    hit = [r for r in rows if r.get("id") == rid]
    if len(hit) != 1:
        print("**일치 %d건 — 쓰지 않는다.** id=%r" % (len(hit), rid))
        return 2
    r = hit[0]
    if state:
        if state not in STATES:
            print("모르는 상태: %s (상태 다섯: %s)" % (state, " · ".join(STATES)))
            return 2
        ch = CH.CHANNELS.get(r.get("채널"), {})
        if state == "게시됨" and not (url or r.get("주소")):
            print("**「게시됨」에는 주소가 있어야 한다** — `--url` 을 준다.")
            return 2
        if state == "게시됨" and not ch.get("되돌릴수있나", True):
            print("  (기록) %s 는 되돌릴 수 없는 채널이다 — 삭제 유예 %s"
                  % (r.get("채널"), ch.get("삭제유예", "[미확인]")))
        r["상태"] = state
    if url:
        r["주소"] = url
    if note:
        r["메모"] = note
    if verify:
        r["검증"] = verify
    r["갱신"] = _now()
    write(rows, head, tail)
    print("갱신: %s → 상태 %s%s" % (rid, r["상태"], (" · " + url) if url else ""))
    return 0


def selftest():
    ok = True
    import tempfile

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    global QUEUE
    keep = QUEUE
    try:
        with tempfile.TemporaryDirectory() as d:
            QUEUE = os.path.join(d, "q.md")
            print("── 인수시험: 빈 대기열 ──")
            rows, head, tail = read()
            chk("없는 파일은 빈 대기열", rows, [])
            chk("판정이 0", status(), 0)

            print("── 인수시험: 쓰고 다시 읽으면 같은가 (세션이 끊겨도 남는다) ──")
            src = [
                {"id": "li-01", "채널": "linkedin", "무엇": "사이트 공개", "상태": "준비",
                 "검증": "PASS(net)", "문안": "li-01.md", "주소": "", "갱신": "2026-09-09", "메모": ""},
                {"id": "gn-01", "채널": "geeknews", "무엇": "Show GN", "상태": "승인대기",
                 "검증": "PASS(net)", "문안": "gn-01.md", "주소": "", "갱신": "2026-09-09", "메모": ""},
                {"id": "dq-01", "채널": "disquiet", "무엇": "메이커로그", "상태": "보류",
                 "검증": "", "문안": "", "주소": "", "갱신": "2026-09-09", "메모": "프로덕트 등록 전"},
            ]
            write(src, head, tail)
            back, _, _ = read()
            chk("행 수가 같다", len(back), 3)
            chk("id 가 같다", [r["id"] for r in back], ["li-01", "gn-01", "dq-01"])
            chk("상태가 같다", [r["상태"] for r in back], ["준비", "승인대기", "보류"])
            chk("메모가 살아 있다", back[2]["메모"], "프로덕트 등록 전")

            print("── 인수시험: 갱신 ──")
            chk("모르는 id 는 안 쓴다", setrow("없다", state="준비"), 2)
            chk("모르는 상태는 안 쓴다", setrow("li-01", state="올림"), 2)
            chk("게시됨은 주소를 요구한다", setrow("li-01", state="게시됨"), 2)
            chk("주소를 주면 쓴다",
                setrow("li-01", state="게시됨", url="https://x.example/p/1"), 0)
            back, _, _ = read()
            r = [x for x in back if x["id"] == "li-01"][0]
            chk("상태가 바뀌었다", r["상태"], "게시됨")
            chk("주소가 남았다", r["주소"], "https://x.example/p/1")
            chk("다른 행은 안 건드렸다",
                [x["상태"] for x in back if x["id"] != "li-01"], ["승인대기", "보류"])

            print("── 인수시험: 파이프 문자가 표를 안 깬다 ──")
            src2 = [{"id": "x", "채널": "linkedin", "무엇": "a|b", "상태": "초안",
                     "검증": "", "문안": "", "주소": "", "갱신": "", "메모": "c|d"}]
            write(src2, head, tail)
            back, _, _ = read()
            chk("한 행으로 읽힌다", len(back), 1)
            chk("파이프는 갈음된다", back[0]["무엇"], "a/b")

            print("── 인수시험: 「지금 뭐 대기 중이야」가 순서를 지키는가 ──")
            write(src, head, tail)
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                status()
            out = buf.getvalue()
            chk("승인대기를 준비보다 먼저 찍는다",
                out.index("승인을 기다린다") < out.index("나갈 준비가 됐다"), True)
            chk("되돌릴 수 없는 채널을 표시한다", "되돌릴 수 없다" in out, True)
            chk("합계를 낸다", "전체 3" in out, True)
    finally:
        QUEUE = keep

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="채널 발행 대기열")
    ap.add_argument("--check", action="store_true", help="대기 중인 문안을 전부 검사")
    ap.add_argument("--net", action="store_true", help="검사에서 링크·카드를 실제로 친다")
    ap.add_argument("--before-post", dest="pre", default=None,
                    help="누르기 직전 점검 — 중복 확인용 첫 줄과 채널 주의")
    ap.add_argument("--set", dest="rid", default=None, help="갱신할 id")
    ap.add_argument("--state", default=None, help=" · ".join(STATES))
    ap.add_argument("--url", default=None)
    ap.add_argument("--note", default=None)
    ap.add_argument("--verify", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.pre:
        sys.exit(before_post(a.pre))
    if a.rid:
        sys.exit(setrow(a.rid, a.state, a.url, a.note, a.verify))
    if a.check:
        sys.exit(check(a.net))
    sys.exit(status())

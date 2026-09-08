# -*- coding: utf-8 -*-
"""STATUS 이관 — 상한 처리의 수동 경로를 없앤다.

왜 있는가
---------
`docs/STATUS.md` 는 매 세션 전문이 읽히는 파일이라 `boot_check.py` 가 크기 상한을 잰다.
상한은 제 일을 했다 — 그런데 **넘을 때마다 사람이 같은 동작을 했다.** 블록을 고르고, 잘라내고,
`docs/작업기록.md` 에 「원문 그대로」 붙이고, 포인터를 남긴다. 2026-09-02 ~ 09-08 에 그 커밋이
**13건**이다(`git log --oneline -- docs/STATUS.md | grep 상한`). 같은 손 동작이 세 번을 넘으면
고치지 말고 **경로를 없앤다**(사고 75·81). 그 동작 중 판단이 필요한 것은 「무엇을 옮기나」 하나고,
나머지는 전부 기계적이다 — 그리고 「끝난 항목」은 판단 없이도 안다: **표제가 취소선이다.**

무엇을 하는가
-------------
  --check    (기본) 크기(LF 기준)·여유·절별 바이트·자동 이관 후보(표제가 취소선인 블록)를 낸다.
             마지막 줄 하나가 판정이다(`boot_check` 가 그 줄을 든다). 종료코드 0.
  --write    후보(그리고 --move 로 고른 블록)를 `docs/작업기록.md` 끝에 **원문 그대로** 붙이고
             STATUS 에서 뺀다. 뺀 자리에는 원장 한 줄 —
             「끝난 것(이관됨): A-4 · A-5 (→ 작업기록 날짜)」. 전후 SHA-256 과 크기를 찍는다.
             **붙인 원문이 작업기록에 그대로 있고 STATUS 에서 사라졌는지를 쓰기 전에 검산한다** —
             검산이 어긋나면 아무것도 쓰지 않는다.
  --move S   첫 줄에 S 를 포함하는 블록 **하나**를 옮긴다(반복 가능). 일치가 1건이 아니면
             **쓰지 않는다**(`safe_edit` 와 같은 원칙). 취소선이 아닌 블록(경위 등)을 판단으로
             옮길 때 쓴다. 원장은 「이관됨(경위): …」로 따로 든다.
  --selftest 인수시험.

블록이란
--------
  정지선표(`<!-- 정지선표:끝 -->`) 뒤의 절만 본다 — 착수점과 생성 블록은 손대지 않는다.
  절에 `**A-1.` 꼴 표지가 있으면 **표지 블록**(다음 표지·절 끝까지. 빈 줄·코드 펜스 포함),
  없으면 **목록 블록**(`- ` 로 시작해 들여쓴 줄이 이어지는 동안).
  후보 = 블록 첫 줄에서 `- `·`**`·`[날짜 …]`·`A-1.` 을 벗긴 표제가 `~~` 로 시작하는 것.

닿지 않는 곳
------------
· **무엇이 끝났는가는 취소선이 말한다.** 취소선 없이 끝난 항목, 취소선 안에 살아 있는 꼬리
  (「배포 뒤 한 번 더」 같은)는 못 가른다 — `--check` 가 후보 전문을 찍으니 `--write` 전에 읽는다.
  옮긴 원문은 지워지지 않고 작업기록에 그대로 있다.
· **유입은 못 줄인다.** 착수점 3)·B·미해결의 서술은 판단이라 장치가 안 건드린다. 상한을 만드는
  것은 그 서술이고, 이 장치는 그 서술이 끝난 뒤의 처분만 맡는다. 여유는 `--check` 가 낸다.
· 크기는 **LF 기준**이다(`.gitattributes` 의 md 규격 · 재는 법은 `boot_check.status_bytes`).
  디스크가 CRLF 면 줄 수만큼 더 크게 보인다 — 2026-09-08 「42,009 B 넘은 채 커밋」이
  그것이었다(git 에는 41,594 B · 사고 99).
"""

import argparse
import hashlib
import io
import os
import re
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
from boot_check import STATUS_LIMIT, status_bytes  # noqa: E402 — 상한과 재는 법은 한 곳이 든다

STATUS = os.path.join(ROOT, "docs", "STATUS.md")
LOG = os.path.join(ROOT, "docs", "작업기록.md")
END_MARK = "<!-- 정지선표:끝 -->"
HEADER = re.compile(r"^(##|###) ")
LABEL = re.compile(r"^\*\*([A-Z]-\d+)\.\s")
LEDGER_DONE = "**끝난 것(이관됨):**"
LEDGER_MOVED = "**이관됨(경위):**"
LOG_HEAD = "## STATUS 에서 옮겨 온 것 (%s · `status_archive.py`) — 원문 그대로"


# ── 파일 ────────────────────────────────────────────────────────────────────

def read_text(path):
    """(본문, 줄끝, BOM). 줄끝과 BOM 은 **있는 그대로** 돌려준다 — 쓸 때 그대로 되돌린다."""
    data = io.open(path, "rb").read()
    bom = data.startswith(b"\xef\xbb\xbf")
    if bom:
        data = data[3:]
    nl = "\r\n" if b"\r\n" in data else "\n"
    return data.decode("utf-8").replace("\r\n", "\n"), nl, bom


def write_text(path, text, nl, bom):
    data = text.replace("\n", nl).encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    tmp = path + ".tmp"
    with io.open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def sha(path):
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def size_lf(text):
    """LF 기준 바이트 — `boot_check` 와 같은 자로 잰다."""
    return status_bytes(text.encode("utf-8"))


# ── 블록 ────────────────────────────────────────────────────────────────────

def is_ledger(ln):
    t = ln[2:] if ln.startswith("- ") else ln
    return t.startswith(LEDGER_DONE) or t.startswith(LEDGER_MOVED)


def headline(first):
    """블록 첫 줄에서 `- `·`**`·`[꼬리표]`·`A-1.` 을 벗긴 표제."""
    t = first
    if t.startswith("- "):
        t = t[2:]
    t = t.lstrip()
    if t.startswith("**"):
        t = t[2:]
    t = re.sub(r"^(\[[^\]]*\]\s*)+", "", t)
    t = re.sub(r"^[A-Z]-\d+\.\s*", "", t)
    return t


def _label(first, head, done):
    m = LABEL.match(first)
    if m:
        return m.group(1)
    m2 = re.match(r"~~(.+?)~~", head) if done else re.match(r"(.+?)\*\*", head)
    raw = m2.group(1) if m2 else head
    return re.sub(r"[`*]", "", raw).strip()[:40]


def parse(text):
    """반환 (lines, sections, blocks). 인덱스는 `text.split(chr(10))` 기준."""
    lines = text.split("\n")
    start = None
    for i, ln in enumerate(lines):
        if ln.strip() == END_MARK:
            start = i + 1
            break
    if start is None:
        # 표식이 없으면 착수점 절만 빼고 본다.
        start = 0
        for i, ln in enumerate(lines):
            if HEADER.match(ln) and "착수점" not in ln:
                start = i
                break
    sections, cur = [], None
    for i in range(start, len(lines)):
        if HEADER.match(lines[i]):
            if cur:
                cur["end"] = i
            cur = {"header": lines[i], "hidx": i, "begin": i + 1, "end": len(lines)}
            sections.append(cur)
    blocks = []
    for sec in sections:
        body = range(sec["begin"], sec["end"])
        labeled = any(LABEL.match(lines[i]) for i in body)
        sec["labeled"] = labeled
        if labeled:
            starts = [i for i in body if LABEL.match(lines[i]) or is_ledger(lines[i])]
            for a, b in zip(starts, starts[1:] + [sec["end"]]):
                if is_ledger(lines[a]):
                    continue
                e = b
                while e > a + 1 and not lines[e - 1].strip():
                    e -= 1
                blocks.append(_mk(lines, a, e, sec))
        else:
            i = sec["begin"]
            while i < sec["end"]:
                ln = lines[i]
                if ln.startswith("- ") and not is_ledger(ln):
                    e = i + 1
                    while e < sec["end"] and lines[e].strip() and lines[e][:1] in (" ", "\t"):
                        e += 1
                    blocks.append(_mk(lines, i, e, sec))
                    i = e
                else:
                    i += 1
    return lines, sections, blocks


def _mk(lines, a, e, sec):
    first = lines[a]
    head = headline(first)
    done = head.startswith("~~")
    return {"start": a, "end": e, "section": sec, "label": _label(first, head, done),
            "done": done, "lines": lines[a:e]}


def block_bytes(b):
    return len("\n".join(b["lines"]).encode("utf-8")) + 1


def section_sizes(text):
    out, cur, n = [], "(머리)", 0
    for ln in text.split("\n"):
        if HEADER.match(ln):
            out.append((cur, n))
            cur, n = re.split(r" — |\(", ln.lstrip("#").strip())[0][:22], 0
        n += len(ln.encode("utf-8")) + 1
    out.append((cur, n))
    return out


def resolve_moves(blocks, subs):
    """`--move` 하나에 블록 하나. 일치가 1건이 아니면 오류 — 쓰지 않는다."""
    chosen, errs = [], []
    for s in subs:
        hits = [b for b in blocks if s in b["lines"][0]]
        if len(hits) != 1:
            shown = " / ".join(h["lines"][0][:48] for h in hits[:4])
            errs.append("--move %r: 일치 %d건%s" % (s, len(hits), (" — " + shown) if hits else ""))
        elif hits[0] not in chosen:
            chosen.append(hits[0])
    return chosen, errs


# ── 이관 ────────────────────────────────────────────────────────────────────

def apply(lines, chosen, date):
    """chosen 블록을 빼고 절마다 원장 줄을 남긴다. 반환 (새 lines, [(절 머리, [블록 줄들…])…])."""
    lines = list(lines)
    by_sec = {}
    for b in chosen:
        by_sec.setdefault(id(b["section"]), (b["section"], []))[1].append(b)
    chunks = []
    # 아래 절부터 — 위 절의 인덱스가 안 밀리게.
    for _, (sec, bl) in sorted(by_sec.items(), key=lambda kv: -kv[1][0]["hidx"]):
        bl.sort(key=lambda b: b["start"])
        chunks.append((sec["header"], [b["lines"] for b in bl]))
        for group_done in (False, True):
            grp = [b for b in bl if b["done"] == group_done]
            if not grp:
                continue
            top = grp[0]["start"]
            for b in reversed(grp):
                del lines[b["start"]:b["end"]]
                a = b["start"]
                if 0 < a < len(lines) and not lines[a - 1].strip() and not lines[a].strip():
                    del lines[a]
            # 절 안의 기존 원장 — 있으면 덧붙이고, 없으면 첫 블록 자리에 넣는다.
            mark = LEDGER_DONE if group_done else LEDGER_MOVED
            entry = " · ".join(b["label"] for b in grp) + " (→ 작업기록 %s)" % date
            existing = None
            for i in range(sec["begin"], min(len(lines), sec["end"])):
                t = lines[i][2:] if lines[i].startswith("- ") else lines[i]
                if t.startswith(mark):
                    existing = i
                    break
            if existing is not None:
                lines[existing] = lines[existing].rstrip() + " · " + entry
                continue
            led = ("- " if not sec["labeled"] else "") + mark + " " + entry
            ins = [led]
            if sec["labeled"]:
                if top < len(lines) and lines[top].strip():
                    ins.append("")
                if top > 0 and lines[top - 1].strip():
                    ins.insert(0, "")
            lines[top:top] = ins
    chunks.reverse()
    return lines, chunks


def append_log(log_text, date, chunks):
    head = LOG_HEAD % date
    out = log_text.rstrip("\n") + "\n"
    last_h2 = None
    for ln in log_text.split("\n"):
        if ln.startswith("## "):
            last_h2 = ln
    if last_h2 != head:
        out += "\n" + head + "\n"
    for sec_header, block_list in chunks:
        out += "\n### " + sec_header.lstrip("#").strip() + "\n"
        for blk in block_list:
            out += "\n" + "\n".join(blk) + "\n"
    return out


# ── 명령 ────────────────────────────────────────────────────────────────────

def check(status=STATUS, subs=()):
    text, nl, _ = read_text(status)
    lines, sections, blocks = parse(text)
    size = size_lf(text)
    free = STATUS_LIMIT - size
    done = [b for b in blocks if b["done"]]
    print("STATUS %s B (LF 기준 · 상한 %s · 여유 %s B · 디스크 줄끝 %s)"
          % (format(size, ","), format(STATUS_LIMIT, ","), format(free, ","),
             "CRLF" if nl == "\r\n" else "LF"))
    big = sorted(section_sizes(text), key=lambda kv: -kv[1])[:6]
    print("절별 큰 순: " + " · ".join("%s %s" % (n, format(b, ",")) for n, b in big))
    cand_b = sum(block_bytes(b) for b in done)
    print("자동 이관 후보 %d개 · %s B (표제가 취소선인 블록)" % (len(done), format(cand_b, ",")))
    for b in done:
        print("  %-14s %5d B  %s" % (b["label"][:14], block_bytes(b), b["lines"][0][:88]))
    if subs:
        chosen, errs = resolve_moves(blocks, subs)
        for b in chosen:
            print("  --move 매치  %5d B  %s" % (block_bytes(b), b["lines"][0][:80]))
        for e in errs:
            print("  " + e)
    tail = ("자동 이관 후보 %d개(%s B) — `python analysis/status_archive.py --write` 로 옮긴다"
            % (len(done), format(cand_b, ","))) if done else \
        "자동 이관 후보 0 — 취소선 표제가 없다. 더 필요하면 `--move` 로 고른다"
    print(("**상한 초과** " if free < 0 else "") + "여유 %s B · %s" % (format(free, ","), tail))
    return 0


def write(status=STATUS, log=LOG, subs=(), date=None):
    date = date or time.strftime("%Y-%m-%d")
    text, nl, bom = read_text(status)
    lines, sections, blocks = parse(text)
    done = [b for b in blocks if b["done"]]
    moves, errs = resolve_moves(blocks, subs)
    if errs:
        for e in errs:
            print(e)
        print("**쓰지 않았다** — --move 는 일치 1건일 때만 옮긴다.")
        return 1
    chosen = done + [b for b in moves if b not in done]
    if not chosen:
        print("옮길 것이 없다 — 취소선 표제 0 · --move 0. STATUS 는 그대로다.")
        return 0
    new_lines, chunks = apply(lines, chosen, date)
    new_text = "\n".join(new_lines)
    log_text, lnl, lbom = read_text(log)
    new_log = append_log(log_text, date, chunks)
    # 검산 — 쓰기 전에. 원문이 작업기록에 그대로 있고 STATUS 에서는 사라졌는가.
    for _, blist in chunks:
        for blk in blist:
            raw = "\n".join(blk)
            if raw not in new_log:
                print("**검산 실패 — 쓰지 않았다.** 작업기록에 원문이 없다: %s" % blk[0][:60])
                return 1
            if raw in new_text:
                print("**검산 실패 — 쓰지 않았다.** STATUS 에 원문이 남았다: %s" % blk[0][:60])
                return 1
    before = (sha(status), sha(log))
    write_text(status, new_text, nl, bom)
    write_text(log, new_log, lnl, lbom)
    after = (sha(status), sha(log))
    n = sum(len(bl) for _, bl in chunks)
    print("옮겼다 %d블록 → %s 「%s」" % (n, os.path.relpath(log, ROOT).replace("\\", "/"),
                                     (LOG_HEAD % date).lstrip("# ")))
    for _, blist in chunks:
        for blk in blist:
            print("  · %s" % blk[0][:90])
    print("STATUS %s → %s B (LF 기준 · 여유 %s B)" % (
        format(size_lf(text), ","), format(size_lf(new_text), ","),
        format(STATUS_LIMIT - size_lf(new_text), ",")))
    print("SHA-256 STATUS %s → %s" % (before[0][:12], after[0][:12]))
    print("SHA-256 작업기록 %s → %s" % (before[1][:12], after[1][:12]))
    return 0


# ── 인수시험 ────────────────────────────────────────────────────────────────

FIXTURE = """# STATUS

**갱신: 시험**

## 착수점 — 이 절만 읽어도

**3) ~~착수점의 취소선은 안 옮긴다~~.** 판단 문장이다.

<!-- 정지선표:시작 (생성됨) -->
| 표 |
<!-- 정지선표:끝 -->

## 현재 상태

### 검사·생성 장치 — 2종

`a.py` · `b.py`

- **장치 a** — 산다. ~~허브만 push 하면 건너뛴다~~(닫힘). 취소선이 꼬리에만 있다.
  이어지는 줄.

## 다음 할 일

### A. 이쪽이 바로 할 수 있는 것

> 서문은 블록이 아니다.

**A-1. ~~끝난 것~~ [끝 · 꼬리 문장].** 뒤에 붙은 말.

**A-2. 살아 있는 것.** 본문
둘째 줄.

```
코드 펜스도 블록 안이다
```

**A-3. ~~또 끝난 것~~ [끝].**
**A-4. 살아 있는 넷째.**

### B. 운영자 손이 있어야 하는 것

**B-1. 살아 있다.** ① ~~부분~~ 은 안 옮긴다.

### C. 아직 안 본 축

- **~~연안 구간~~ — [2026-08-31] 닫혔다**(관측). 값 1
  이어지는 줄.
- **살아 있는 축.** 본문.

## 미해결

- **[2026-08-29 4차 갱신] 살아 있는 미해결 — 없다는 것을 확인했다.** 본문
  이어지는 줄.
"""


def selftest():
    import tempfile
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-58s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    with tempfile.TemporaryDirectory() as d:
        st = os.path.join(d, "STATUS.md")
        lg = os.path.join(d, "작업기록.md")
        with io.open(st, "wb") as fh:
            fh.write(FIXTURE.replace("\n", "\r\n").encode("utf-8"))
        with io.open(lg, "wb") as fh:
            fh.write("# 작업기록\r\n\r\n## 2026-09-01 · 앞선 라운드\r\n\r\n본문.\r\n".encode("utf-8"))

        print("── 인수시험: 블록을 가르는가 ──")
        text, nl, bom = read_text(st)
        chk("CRLF 를 기억한다", nl, "\r\n")
        chk("BOM 없음", bom, False)
        chk("LF 기준 크기 = 원문 바이트", size_lf(text), len(FIXTURE.encode("utf-8")))
        lines, sections, blocks = parse(text)
        labels = [b["label"] for b in blocks]
        chk("표지 블록 여섯 + 목록 블록 셋", len(blocks), 9)
        chk("착수점의 취소선은 후보가 아니다", any("착수점" in b["lines"][0] for b in blocks), False)
        done = [b["label"] for b in blocks if b["done"]]
        chk("후보 = 취소선 표제 셋", done, ["A-1", "A-3", "연안 구간"])
        chk("꼬리의 취소선은 후보가 아니다", "장치 a" in done, False)
        a2 = [b for b in blocks if b["label"] == "A-2"][0]
        chk("표지 블록은 다음 표지까지(펜스 포함)", "코드 펜스도 블록 안이다" in "\n".join(a2["lines"]), True)
        chk("표지 블록 꼬리의 빈 줄은 뺀다", a2["lines"][-1].strip() != "", True)
        chk("목록 블록의 표제 이름", "살아 있는 미해결 — 없다는 것을 확인했다." in labels, True)

        print("── 인수시험: --move 는 일치 1건일 때만 ──")
        ch, errs = resolve_moves(blocks, ["살아 있는 것"])
        chk("한 건 일치", [b["label"] for b in ch], ["A-2"])
        ch, errs = resolve_moves(blocks, ["살아"])
        chk("여러 건이면 오류", len(errs) == 1 and "일치" in errs[0], True)
        ch, errs = resolve_moves(blocks, ["없는 문자열"])
        chk("0건이면 오류", len(errs), 1)
        rc = write(st, lg, subs=["살아"], date="2026-09-08")
        chk("애매하면 쓰지 않는다(종료코드 1)", rc, 1)
        chk("파일이 그대로다", read_text(st)[0], text)

        print("── 인수시험: --write 가 옮기고 원장을 남기는가 ──")
        rc = write(st, lg, date="2026-09-08")
        chk("종료코드 0", rc, 0)
        s2, nl2, _ = read_text(st)
        l2, lnl2, _ = read_text(lg)
        chk("STATUS 줄끝이 그대로다", nl2, "\r\n")
        chk("작업기록 줄끝이 그대로다", lnl2, "\r\n")
        chk("끝난 블록이 STATUS 에서 사라졌다", "~~끝난 것~~" in s2 or "~~연안 구간~~" in s2, False)
        chk("살아 있는 블록은 남았다", "**A-2. 살아 있는 것.**" in s2 and "**A-4. 살아 있는 넷째.**" in s2, True)
        chk("B 의 부분 취소선은 남았다", "① ~~부분~~ 은 안 옮긴다" in s2, True)
        chk("A 원장 한 줄", "**끝난 것(이관됨):** A-1 · A-3 (→ 작업기록 2026-09-08)" in s2, True)
        chk("C 원장은 목록 꼴", "- **끝난 것(이관됨):** 연안 구간 (→ 작업기록 2026-09-08)" in s2, True)
        chk("원장 뒤에 빈 줄(표지 절)", "(→ 작업기록 2026-09-08)\n\n**A-2." in s2, True)
        chk("작업기록 머리", LOG_HEAD % "2026-09-08" in l2, True)
        chk("절 이름을 든다", "### A. 이쪽이 바로 할 수 있는 것" in l2 and "### C. 아직 안 본 축" in l2, True)
        chk("원문 그대로(A-1)", "**A-1. ~~끝난 것~~ [끝 · 꼬리 문장].** 뒤에 붙은 말." in l2, True)
        chk("원문 그대로(연안 두 줄)", "- **~~연안 구간~~ — [2026-08-31] 닫혔다**(관측). 값 1\n  이어지는 줄." in l2, True)
        chk("작아졌다", size_lf(s2) < size_lf(text), True)
        chk("빈 줄이 겹치지 않는다", "\n\n\n" in s2, False)

        print("── 인수시험: 두 번째 실행 ──")
        h1 = (sha(st), sha(lg))
        rc = write(st, lg, date="2026-09-08")
        chk("옮길 것이 없으면 0 이고", rc, 0)
        chk("파일을 안 건드린다", (sha(st), sha(lg)), h1)
        rc = write(st, lg, subs=["살아 있는 것"], date="2026-09-08")
        s3, _, _ = read_text(st)
        l3, _, _ = read_text(lg)
        chk("--move 로 산 블록을 옮긴다", rc == 0 and "**A-2. 살아 있는 것.**" not in s3, True)
        chk("경위 원장은 따로", "**이관됨(경위):** A-2 (→ 작업기록 2026-09-08)" in s3, True)
        chk("끝난 원장은 그대로", "**끝난 것(이관됨):** A-1 · A-3 (→ 작업기록 2026-09-08)" in s3, True)
        chk("같은 날은 같은 머리 아래 붙인다", l3.count(LOG_HEAD % "2026-09-08"), 1)
        chk("펜스까지 그대로 갔다", "```\n코드 펜스도 블록 안이다\n```" in l3, True)
        # 다른 날 · 같은 원장에 덧붙는가
        with io.open(st, "ab") as fh:
            fh.write("\r\n### A. 이쪽이 바로 할 수 있는 것\r\n".encode("utf-8"))  # 절 이름 중복 방지용 아님 — 아래서 새 블록만 본다
        s4 = read_text(st)[0].replace("**A-4. 살아 있는 넷째.**", "**A-4. ~~넷째도 끝~~ [끝].**")
        write_text(st, s4, "\r\n", False)
        rc = write(st, lg, date="2026-09-12")
        s5, _, _ = read_text(st)
        chk("다음 날 것은 원장에 덧붙는다",
            "A-1 · A-3 (→ 작업기록 2026-09-08) · A-4 (→ 작업기록 2026-09-12)" in s5, True)
        chk("--check 가 돈다", check(st, subs=["살아 있는 축"]), 0)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="STATUS 이관 — 끝난 블록을 작업기록으로, 원문 그대로.")
    ap.add_argument("--check", action="store_true", help="후보와 여유만 본다(기본)")
    ap.add_argument("--write", action="store_true", help="옮긴다")
    ap.add_argument("--move", action="append", default=[], metavar="S",
                    help="첫 줄에 S 를 포함하는 블록 하나를 옮긴다(반복 가능)")
    ap.add_argument("--date", default=None, help="작업기록 머리의 날짜(기본 오늘)")
    ap.add_argument("--status", default=STATUS, help=argparse.SUPPRESS)
    ap.add_argument("--log", default=LOG, help=argparse.SUPPRESS)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.write:
        return write(a.status, a.log, subs=a.move, date=a.date)
    return check(a.status, subs=a.move)


if __name__ == "__main__":
    sys.exit(main())

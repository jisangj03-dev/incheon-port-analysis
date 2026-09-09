# -*- coding: utf-8 -*-
"""세션 지시문 자리 — **무엇이 세션에게 지시가 되고 있는가.**

왜 있는가
---------
2026-09-10, 도구 도입 G5 가 **금지 축에서 가시성 축으로** 바뀌었다(운영자 판단 ·
선커밋 `docs/도구도입_선커밋_G5개정_20260910.md`). 종전 기준은 「세션 지시문 자리에
쓰지 마라」였고, 새 기준은 **「써도 된다. 대신 무엇이 쓰였는지 상시로 확인된다」**다.

**그 개정은 이 파일을 전제로만 성립한다.** 가시성은 선언이 아니라 기전이어야 하고(사고 46),
「보이니까 괜찮다」는 **보는 장치가 있을 때만** 참이다. 장치가 없으면 G5-2 는 미달이다.

**계기는 실물이다**(사고 111). `agent-reach doctor` 가 — 상태를 보는 이름의 명령이 —
`~/.claude/skills/` 에 스킬을 심었고, 지운 뒤 다시 쳐도 또 깔렸다. **README 에 그 말이 없었고
저장소 루트에 `.claude-plugin` 도 없어 사전 표식 검사를 통과했다.**
**이름이 아니라 diff 가 답이고, 그러려면 치기 전 상태가 파일로 있어야 한다.**

  python analysis/check_session_surface.py            # 기준선과 대조. 어긋나면 종료 1
  python analysis/check_session_surface.py --list     # 지금 있는 것 전부
  python analysis/check_session_surface.py --write    # 기준선 갱신 (**사람이 보고 나서** 친다)
  python analysis/check_session_surface.py --selftest

기준선은 **저장소에 커밋된 파일**(`docs/세션지시문_기준선.md`)이다 — 그래야 변화가
`git diff` 로 남고 **세션이 아니라 이력이 기억한다**(사고 96).

무엇을 담나 — 그리고 무엇을 안 담나
-----------------------------------
· 스킬: 이름 · 자리 · **설명 문장**(모델이 실제로 읽는 것) · SKILL.md 해시
· 훅·권한·MCP·기억: 파일 · 해시 · **최상위 키 이름만**
· **값은 안 담는다.** 토큰·경로·개인 설정이 이 파일로 새면 그 자체가 유출이다(§4.1).
  `check_private.py` 가 이 파일도 훑는다.

닿지 않는 곳
------------
· **목록에 있는 자리만 본다.** 도구가 새 경로를 쓰면 이 장치는 그것을 모른다.
  자리 목록은 손으로 드는 것이라 **낡는다** — 이 장치의 상수 한계다(사고 83 의 반대 경우:
  여기서는 「무엇이 지시문 자리인가」가 판단이라 찾을 수가 없다).
· **가시성은 안전이 아니다.** 무엇이 쓰였는지 아는 것과 그것이 해롭지 않은 것은 다르다.
  **이 파일은 「알 수 있다」까지만 보장하고 「괜찮다」는 사람이 판단한다.**
· **해시는 바뀐 것을 알리지 무엇이 바뀌었는지는 안 알린다.** 내용은 사람이 읽는다.
· 심링크는 **가리키는 곳의 내용**으로 잰다. 링크가 바뀌면 해시가 바뀐다.
"""

import argparse
import hashlib
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
BASELINE = os.path.join(ROOT, "docs", "세션지시문_기준선.md")

# ── 지시문 자리 ─────────────────────────────────────────────────────────────
#
# **그 내용이 세션에게 지시가 되는 자리.** 모델이 읽거나, 모델을 대신해 실행된다.
# 목록을 손으로 든다 — 「무엇이 지시문 자리인가」는 판단이라 찾을 수가 없다.
# 새 자리를 알게 되면 여기 넣는다. **넣기 전에는 이 장치가 그것을 모른다.**
SKILL_DIRS = [
    ("사용자 스킬", os.path.join(HOME, ".claude", "skills")),
    ("에이전트 스킬", os.path.join(HOME, ".agents", "skills")),
    ("프로젝트 스킬", os.path.join(ROOT, ".claude", "skills")),
]
CMD_DIRS = [
    ("사용자 명령", os.path.join(HOME, ".claude", "commands")),
    ("프로젝트 명령", os.path.join(ROOT, ".claude", "commands")),
    ("사용자 에이전트", os.path.join(HOME, ".claude", "agents")),
    ("프로젝트 에이전트", os.path.join(ROOT, ".claude", "agents")),
    ("플러그인", os.path.join(HOME, ".claude", "plugins")),
]
CONFIG_FILES = [
    ("사용자 설정", os.path.join(HOME, ".claude", "settings.json")),
    ("프로젝트 설정", os.path.join(ROOT, ".claude", "settings.json")),
    ("프로젝트 설정(로컬)", os.path.join(ROOT, ".claude", "settings.local.json")),
    ("사용자 기억", os.path.join(HOME, ".claude", "CLAUDE.md")),
    ("프로젝트 기억", os.path.join(ROOT, "CLAUDE.md")),
    ("MCP(프로젝트)", os.path.join(ROOT, ".mcp.json")),
]
# `~/.claude.json` 은 72 KB 에 대화 이력·프로젝트 목록이 섞여 있다. **해시와 최상위 키만** 든다.
BIG_CONFIG = [("사용자 전역 설정", os.path.join(HOME, ".claude.json"))]

DESC = re.compile(r"^description:\s*(.+?)\s*$", re.M | re.I)
NAME = re.compile(r"^name:\s*(.+?)\s*$", re.M | re.I)


def sha(path):
    try:
        h = hashlib.sha256()
        with io.open(path, "rb") as fh:
            for b in iter(lambda: fh.read(65536), b""):
                h.update(b)
        return h.hexdigest()[:12]
    except Exception:
        return "?"


def dir_sha(path):
    """디렉터리 전체를 한 값으로. 파일 이름과 내용을 **정렬해** 넣는다."""
    h = hashlib.sha256()
    for base, dirs, files in os.walk(path):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(base, f)
            h.update(os.path.relpath(p, path).replace("\\", "/").encode("utf-8"))
            h.update(sha(p).encode("ascii"))
    return h.hexdigest()[:12]


def skill_desc(d):
    """스킬이 **모델에게 무엇이라고 말하는가** — 그것이 실제 지시다."""
    for cand in ("SKILL.md", "skill.md"):
        p = os.path.join(d, cand)
        if os.path.exists(p):
            try:
                t = io.open(p, encoding="utf-8", errors="replace").read(4000)
            except Exception:
                return "", "?"
            m = DESC.search(t)
            desc = (m.group(1) if m else "").strip()
            # **YAML 블록 스칼라**(`description: |` / `>`)면 첫 줄이 표지뿐이다.
            # 그대로 두면 이 장치가 「|」를 설명이라고 내놓는다 — **G5b 를 자기가 못 채운다**
            # (2026-09-10 실측: higgsfield 스킬 여덟이 전부 이 꼴이었다).
            if desc in ("|", ">", "|-", ">-", "|+", ">+"):
                tail = t[m.end():]
                body = []
                for line in tail.split("\n"):
                    if line.strip() and not line[:1].isspace():
                        break          # 들여쓰기가 끝나면 다음 키다
                    body.append(line.strip())
                desc = " ".join(x for x in body if x)
            desc = re.sub(r"\s+", " ", desc)
            return desc[:150], sha(p)
    return "", "?"


PLUGINS_DB = os.path.join(HOME, ".claude", "plugins", "installed_plugins.json")


TOML_DESC = re.compile(r'^\s*description\s*=\s*"(.*?)"\s*$', re.M)


def md_desc(path):
    """`.md`/`.toml` 한 장이 **모델에게 무엇이라고 말하는가.** 머리말 `description` 을 쓰고,
    없으면 첫 비어 있지 않은 본문 줄을 쓴다 — **빈 칸으로 두면 G5b 가 거짓이 된다.**

    **명령은 `.toml` 로도 온다** — 2026-09-10 실측에서 15개가 전부 toml 이라
    `.md` 만 보던 앞판이 **한 줄도 못 냈다.** 거기선 `description = "..."` 꼴이다.
    """
    if path.lower().endswith(".toml"):
        try:
            s = io.open(path, encoding="utf-8", errors="replace").read(4000)
        except Exception:
            return "", "?"
        m = TOML_DESC.search(s)
        d = (m.group(1) if m else "").strip()
        return re.sub(r"\s+", " ", d)[:150], sha(path)
    try:
        t = io.open(path, encoding="utf-8", errors="replace").read(4000)
    except Exception:
        return "", "?"
    m = DESC.search(t)
    d = (m.group(1) if m else "").strip()
    if not d or d in ("|", ">", "|-", ">-"):
        for line in t.split("\n"):
            s = line.strip()
            if s and not s.startswith(("---", "#", "name:", "description:", "allowed-tools:")):
                d = s
                break
    return re.sub(r"\s+", " ", d)[:150], sha(path)


# **플러그인은 스킬만 들고 오지 않는다.** 슬래시 명령과 서브에이전트도 지시문 자리다 —
# `/명령` 은 쳤을 때 그 파일 내용이 그대로 지시가 되고, 에이전트는 자기 몫의 지시를 들고 산다.
# **2026-09-10 실측: 명령 15개(포니테일 6 · 에이전트 스킬즈 9)와 에이전트 4개가
# 이 장치에 한 줄도 안 나왔다** — 스킬만 폈기 때문이다. **G5b 를 또 자기가 못 채웠다.**
PLUGIN_PARTS = [("플러그인 명령", "commands"), ("플러그인 에이전트", "agents")]


def plugin_skills():
    """**플러그인이 붙인 스킬·명령·에이전트를 편다.** 전부 세션에게 지시가 되는데
    `~/.claude/skills` · `~/.claude/commands` 밖, 플러그인 안에 있다.

    설치 대장(`installed_plugins.json`)의 `installPath` 아래를 읽는다.
    **못 읽으면 그 사실을 행으로 남긴다** — 조용히 빠지면 G5a(열거)가 거짓이 된다.
    """
    rows = []
    if not os.path.exists(PLUGINS_DB):
        return rows
    try:
        db = json.load(io.open(PLUGINS_DB, encoding="utf-8"))
    except Exception as e:
        return [("플러그인 스킬", "(대장 못 읽음)", "plugins/installed_plugins.json",
                 type(e).__name__, "?")]
    for pid, entries in sorted((db.get("plugins") or {}).items()):
        for e in entries if isinstance(entries, list) else [entries]:
            root = e.get("installPath") or ""
            ver = e.get("version") or "?"
            scope = e.get("scope") or "?"
            sd = os.path.join(root, "skills")
            if not os.path.isdir(sd):
                rows.append(("플러그인 스킬", "%s (스킬 없음)" % pid, "plugins/%s" % pid,
                             "v%s · 범위 %s" % (ver, scope), sha(root) if os.path.isfile(root) else "—"))
                continue
            for n in sorted(os.listdir(sd)):
                p = os.path.join(sd, n)
                if not os.path.isdir(p):
                    continue
                desc, h = skill_desc(p)
                rows.append(("플러그인 스킬", "%s / %s" % (pid.split("@")[0], n),
                             "plugins/%s v%s (%s)" % (pid, ver, scope),
                             desc or "(SKILL.md 없음)", h))
            for label, sub in PLUGIN_PARTS:
                d2 = os.path.join(root, sub)
                if not os.path.isdir(d2):
                    continue
                for dirpath, _, names in os.walk(d2):
                    for n in sorted(names):
                        if not n.lower().endswith((".md", ".toml")):
                            continue
                        f = os.path.join(dirpath, n)
                        rel = os.path.relpath(f, d2).replace("\\", "/")
                        desc, h = md_desc(f)
                        rows.append((label, "%s / %s" % (pid.split("@")[0], os.path.splitext(rel)[0]),
                                     "plugins/%s v%s (%s)" % (pid, ver, scope), desc, h))
    return rows


def survey():
    """지금 있는 것. 반환 [(갈래, 이름, 자리, 설명, 해시)]"""
    rows = []
    for label, d in SKILL_DIRS:
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            rel = os.path.relpath(p, HOME).replace("\\", "/")
            if os.path.isdir(p):
                desc, h = skill_desc(p)
                rows.append((label, n, rel, desc or "(SKILL.md 없음)", h))
            elif n.lower().endswith(".md"):
                rows.append((label, n, rel, "(단일 파일)", sha(p)))
    # **플러그인이 붙인 스킬은 `~/.claude/skills` 에 안 나온다** — 플러그인 안에 들어 있다.
    # 그러면 위 순회가 「plugins/ 가 바뀌었다」까지만 말하고 **무엇을 지시하는지는 못 말한다** —
    # G5b 미달이다(2026-09-10 실측: 포니테일이 스킬 여섯을 붙였는데 이름조차 안 나왔다).
    # 그래서 설치 대장을 읽어 **플러그인마다 스킬 이름과 설명을 편다.**
    rows += plugin_skills()
    for label, d in CMD_DIRS:
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            rel = os.path.relpath(p, HOME).replace("\\", "/")
            rows.append((label, n, rel, "", dir_sha(p) if os.path.isdir(p) else sha(p)))
    for label, p in CONFIG_FILES:
        if not os.path.exists(p):
            continue
        rel = os.path.relpath(p, HOME).replace("\\", "/")
        keys = ""
        if p.endswith(".json"):
            try:
                keys = " · ".join(sorted(json.load(io.open(p, encoding="utf-8")).keys()))[:110]
            except Exception:
                keys = "(JSON 아님)"
        rows.append((label, os.path.basename(p), rel, keys, sha(p)))
    for label, p in BIG_CONFIG:
        if not os.path.exists(p):
            continue
        try:
            keys = sorted(json.load(io.open(p, encoding="utf-8")).keys())
            k = "최상위 키 %d개: %s" % (len(keys), " · ".join(keys[:6]))
        except Exception:
            k = "(JSON 아님)"
        rows.append((label, os.path.basename(p), os.path.relpath(p, HOME).replace("\\", "/"),
                     k[:110], sha(p)))
    return rows


# ── 기준선 ──────────────────────────────────────────────────────────────────

HEAD = """# 세션 지시문 기준선

> **무엇이 세션에게 지시가 되고 있는가.** 생성됨 — 손으로 고치지 마라.
> `python analysis/check_session_surface.py` 가 이 파일과 실물을 대조하고,
> `--write` 가 갱신한다. **`--write` 는 사람이 무엇이 바뀌었는지 보고 나서 친다.**
>
> **왜 저장소에 두나.** 변화가 `git diff` 로 남아야 **세션이 아니라 이력이 기억한다**(사고 96).
> 도구 도입 G5-2(가시성)가 이 파일을 전제로 성립한다 —
> 선커밋 `docs/도구도입_선커밋_G5개정_20260910.md`.
>
> **값은 안 담는다** — 이름 · 자리 · 설명 · 해시뿐. 토큰·개인 설정이 여기로 새면 그 자체가 유출이다(§4.1).

<!-- 기준선:시작 -->
"""
FOOT = "<!-- 기준선:끝 -->\n"
COLS = ("갈래", "이름", "자리", "무엇을 지시하나 / 키", "해시")


def read_baseline():
    if not os.path.exists(BASELINE):
        return None
    raw = io.open(BASELINE, encoding="utf-8").read().replace("\r\n", "\n")
    i, j = raw.find("<!-- 기준선:시작 -->"), raw.find("<!-- 기준선:끝 -->")
    if i < 0 or j < 0:
        raise ValueError("기준선 표지가 없다: %s" % BASELINE)
    rows = []
    for line in raw[i:j].split("\n"):
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 5 or c[0] == COLS[0] or set(c[0]) <= {"-", ":"}:
            continue
        rows.append(tuple(c[:5]))
    return rows


def write_baseline(rows):
    body = ["", "| " + " | ".join(COLS) + " |", "|" + "|".join(["---"] * 5) + "|"]
    for r in rows:
        body.append("| " + " | ".join((x or "").replace("|", "/") for x in r) + " |")
    body.append("")
    io.open(BASELINE, "w", encoding="utf-8", newline="\n").write(HEAD + "\n".join(body) + FOOT)


def key(r):
    return (r[0], r[1], r[2])


def compare(now, base):
    nb = {key(r): r for r in base}
    nn = {key(r): r for r in now}
    added = [nn[k] for k in nn if k not in nb]
    removed = [nb[k] for k in nb if k not in nn]
    changed = [(nb[k], nn[k]) for k in nn if k in nb and nb[k][4] != nn[k][4]]
    return added, removed, changed


def main(listing=False, write=False):
    now = survey()
    if listing:
        print("== 세션 지시문 자리 — 지금 있는 것 %d건 ==" % len(now))
        for r in now:
            print("  [%s] %-30s %s" % (r[0], r[1], r[4]))
            if r[3]:
                print("      %s" % r[3][:118])
        return 0
    if write:
        write_baseline(now)
        print("기준선 갱신: %s (%d건)" % (os.path.relpath(BASELINE, ROOT).replace("\\", "/"), len(now)))
        print("**무엇이 바뀌었는지 `git diff` 로 보고 커밋한다.**")
        return 0

    base = read_baseline()
    if base is None:
        print("**기준선이 없다 — 통과가 아니다.**")
        print("  `python analysis/check_session_surface.py --write` 로 만들고 `git diff` 로 본다.")
        print("  **기준선 없이는 G5-2(가시성)가 성립하지 않는다**(선커밋 G5개정 §1).")
        return 1
    added, removed, changed = compare(now, base)
    print("== 세션 지시문 자리 ==")
    print("  기준선 %d건 · 지금 %d건" % (len(base), len(now)))
    if added:
        print("\n  **새로 생겼다 %d건 — 무엇을 지시하는지 읽는다**" % len(added))
        for r in added:
            print("    [%s] %s  (%s)" % (r[0], r[1], r[2]))
            if r[3]:
                print("        %s" % r[3][:112])
    if removed:
        print("\n  없어졌다 %d건" % len(removed))
        for r in removed:
            print("    [%s] %s" % (r[0], r[1]))
    if changed:
        print("\n  **내용이 바뀌었다 %d건 — 해시는 「바뀌었다」만 말한다. 무엇이 바뀌었는지는 읽어야 안다**"
              % len(changed))
        for b, n in changed:
            print("    [%s] %s  %s → %s" % (n[0], n[1], b[4], n[4]))
    if not (added or removed or changed):
        print("\n기준선과 같다 — 지시문 자리에 새로 쓰인 것이 없다.")
        return 0
    # **어긋남은 고장이 아니다.** 여기서 멈춘 사람이 그것부터 알아야 한다 —
    # 전역 자리는 폴더를 안 가리므로 **다른 용도로 깐 것이 여기서 걸린다**(`docs/전역과_저장소.md`).
    print()
    print("-" * 66)
    print("**이것은 고장이 아니다.** 지시문 자리가 바뀌었다는 보고다 —")
    print("도구를 깔았거나, **다른 용도로 깐 것이 전역 자리에 붙었을 때** 이렇게 나온다.")
    print("전역은 폴더를 안 가린다(`docs/전역과_저장소.md`) — 여기서 안 깐 것도 여기서 보인다.")
    print()
    print("무엇을 하나 — 셋 중 하나다:")
    print("  1) 위 목록을 읽는다. **「무엇을 지시하나」가 그 스킬이 세션에게 하는 말이다.**")
    print("  2) 받아들인다면:  python analysis/check_session_surface.py --write")
    print("     그리고  git diff docs/세션지시문_기준선.md  로 무엇이 늘었는지 보고 커밋한다.")
    print("  3) 원치 않으면 그 자리를 지운다. 자리는 위 괄호 안에 적혀 있다.")
    print("     예)  rm -rf ~/.claude/skills/<이름> ~/.agents/skills/<이름>")
    print()
    print("**`--write` 는 「봤다」는 서명이다.** 안 보고 치면 이 장치가 하는 일이 없어진다.")
    return 1


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest():
    ok = True
    import tempfile

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 스킬의 「설명」을 뽑는가 (모델이 읽는 것이 그것이다) ──")
    with tempfile.TemporaryDirectory() as d:
        s = os.path.join(d, "myskill")
        os.makedirs(s)
        io.open(os.path.join(s, "SKILL.md"), "w", encoding="utf-8").write(
            "---\nname: myskill\ndescription: MUST USE when the user asks for X.\n---\n본문\n")
        desc, h = skill_desc(s)
        chk("설명을 읽는다", desc, "MUST USE when the user asks for X.")
        chk("해시를 낸다", len(h), 12)
        empty = os.path.join(d, "noskill")
        os.makedirs(empty)
        chk("SKILL.md 없으면 빈 설명", skill_desc(empty)[0], "")
        # **블록 스칼라를 못 읽으면 이 장치가 G5b 를 스스로 못 채운다**(2026-09-10 실측).
        blk = os.path.join(d, "blockskill")
        os.makedirs(blk)
        io.open(os.path.join(blk, "SKILL.md"), "w", encoding="utf-8").write(
            "\n".join(["---", "name: blockskill", "description: |",
                       "  Create things via CLI.", "  Use when asked.",
                       "other: x", "---", ""]))
        chk("YAML 블록 스칼라를 펴서 읽는다",
            skill_desc(blk)[0], "Create things via CLI. Use when asked.")
        chk("다음 키를 안 삼킨다", "other" in skill_desc(blk)[0], False)

    print("── 인수시험: 세 갈래로 가르는가 (G5c) ──")
    base = [("사용자 스킬", "a", "p/a", "설명 A", "111111111111"),
            ("사용자 스킬", "b", "p/b", "설명 B", "222222222222")]
    now = [("사용자 스킬", "a", "p/a", "설명 A", "111111111111"),
           ("사용자 스킬", "c", "p/c", "설명 C", "333333333333")]
    add, rem, chg = compare(now, base)
    chk("추가를 잡는다", [r[1] for r in add], ["c"])
    chk("삭제를 잡는다", [r[1] for r in rem], ["b"])
    chk("변경 없음", chg, [])
    now2 = [("사용자 스킬", "a", "p/a", "설명 A", "999999999999")]
    add, rem, chg = compare(now2, base)
    chk("해시가 바뀌면 변경으로 잡는다", [n[1] for _, n in chg], ["a"])
    chk("같은 이름이 다시 깔려도 잡힌다(G5c)", len(chg), 1)

    print("── 인수시험: 기준선 왕복 ──")
    global BASELINE
    keep = BASELINE
    try:
        with tempfile.TemporaryDirectory() as d:
            BASELINE = os.path.join(d, "b.md")
            chk("기준선 없으면 통과가 아니다", main(), 1)
            write_baseline(base)
            got = read_baseline()
            chk("쓰고 읽으면 같다", got, base)
            chk("파이프가 표를 안 깬다",
                (write_baseline([("갈", "a|b", "p", "설|명", "h")]) or
                 read_baseline()[0][1]), "a/b")
    finally:
        BASELINE = keep

    print("── 인수시험: 플러그인 안의 명령·에이전트를 보는가 (G5b) ──")
    # 2026-09-10: 스킬만 폈더니 **명령 15 · 에이전트 4 가 한 줄도 안 나왔다.**
    # 「없다」와 「못 본다」는 다르다 — 실물이 있는데 0 이면 그것이 고장이다.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f1 = os.path.join(d, "a.toml")
        io.open(f1, "w", encoding="utf-8").write(
            'description = \"컨테이너 물동량을 센다\"\n' + 'prompt = \"\"\"x\"\"\"\n')
        chk("toml 명령의 설명을 읽는다", md_desc(f1)[0], "컨테이너 물동량을 센다")
        f2 = os.path.join(d, "b.md")
        io.open(f2, "w", encoding="utf-8").write("---\nname: b\ndescription: 두 번째\n---\n본문\n")
        chk("md 명령의 설명을 읽는다", md_desc(f2)[0], "두 번째")

    # **실물 대조** — 플러그인이 `commands/`·`agents/` 를 들고 있으면 행이 나와야 한다.
    have, seen = {}, {}
    if os.path.exists(PLUGINS_DB):
        try:
            db = json.load(io.open(PLUGINS_DB, encoding="utf-8"))
        except Exception:
            db = {}
        for pid, es in (db.get("plugins") or {}).items():
            for e in es if isinstance(es, list) else [es]:
                for label, sub in PLUGIN_PARTS:
                    p2 = os.path.join(e.get("installPath") or "", sub)
                    if os.path.isdir(p2):
                        have[label] = have.get(label, 0) + sum(
                            1 for _, _, ns in os.walk(p2)
                            for n in ns if n.lower().endswith((".md", ".toml")))
    for r in plugin_skills():
        seen[r[0]] = seen.get(r[0], 0) + 1
    for label, cnt in sorted(have.items()):
        chk("실물 %d개가 있는 「%s」이 행으로 나온다" % (cnt, label),
            seen.get(label, 0), cnt)
    if not have:
        print("  (플러그인이 명령·에이전트를 안 들고 있다 — **미실행**이지 통과가 아니다)")

    print("── 인수시험: 값을 안 담는가 (§4.1) ──")
    # **접두만 보면 낱말에 걸린다.** 2026-09-10 에 `task-breakdown` 의 `sk-` 가 걸렸다 —
    # 스킬 이름이다. 그래서 **키의 모양**으로 잰다: 앞이 글자가 아니고, 뒤에 무작위처럼
    # 긴 문자열이 붙는다. **느슨하게 만든 게 아니라 낱말과 키를 가르는 것이다** —
    # 아래 「심은 것을 잡는가」가 진짜 모양을 넣고 실제로 잡히는지 매번 확인한다.
    LEAK = [
        ("sk-",       re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{16,}")),
        ("ghp_",      re.compile(r"(?<![A-Za-z0-9])ghp_[A-Za-z0-9]{16,}")),
        ("Bearer ",   re.compile(r"(?<![A-Za-z0-9])Bearer\s+[A-Za-z0-9._~+/=-]{12,}")),
        ('token":"',  re.compile(r'token"\s*:\s*"[^"]{8,}')),
    ]
    rows = survey()
    joined = " ".join(" ".join(r) for r in rows)
    for name, rx in LEAK:
        chk("「%s」가 안 담긴다" % name.strip(), bool(rx.search(joined)), False)
    planted = ('x sk-' + 'A1b2C3d4E5f6G7h8i9' + ' y ghp_' + 'A1b2C3d4E5f6G7h8i9'
               + ' z Bearer ' + 'eyJhbGciOi.Zm9v' + ' w token":"' + 'abcd1234efgh')
    for name, rx in LEAK:
        chk("심은 「%s」는 잡는다" % name.strip(), bool(rx.search(planted)), True)
    chk("낱말은 안 잡는다 (task-breakdown · risk-free)",
        any(rx.search("task-breakdown risk-free") for _, rx in LEAK), False)
    chk("실물에서 여러 건을 본다", len(rows) >= 3, True)
    print("     지금: 지시문 자리 %d건" % len(rows))

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="세션 지시문 자리 — 무엇이 지시가 되고 있는가")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else main(a.list, a.write))

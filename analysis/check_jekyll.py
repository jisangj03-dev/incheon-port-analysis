# -*- coding: utf-8 -*-
"""허브·인천의 Jekyll 빌드가 깨질 자리를 정적으로 훑는다. **빌드가 아니다.**

왜 있는가
---------
**허브는 한 번도 빌드된 적이 없다.** `origin/main` 이 없고, 첫 push 가 곧 첫 빌드다.
그런데 우리에겐 **로컬 빌드 수단이 없다**(Ruby+Jekyll 미설치 · STATUS 미해결이 그렇게 적는다).
즉 지금까지 「허브가 빌드되는가」는 **안 본 것**이었고, 안 본 것을 통과로 세면 사고 26 이다.

그리고 GitHub Pages 빌드는 **조용히 죽는다.** 실패하면 새 판이 안 올라갈 뿐 옛 판이 계속
서 있고, 허브는 옛 판이 아예 없어 **사이트 전체가 404 로 남는다.** 우리 쪽 화면에는
아무 표시가 안 뜬다 — 그래서 「조심」으로 안 되고, 이것이 사고 75·81 과 같은 처분이다.

무엇을 보는가 — **빌드를 깨는 것들만** 본다
--------------------------------------------
1. `_config.yml` 이 YAML 로 읽히는가 · `plugins` 가 Pages 허용 목록 안인가(**경고**)
2. front matter 가 닫히고 YAML 로 읽히는가
3. Liquid 여는 태그와 닫는 태그의 짝
4. `{% link %}` · `{% post_url %}` 의 대상 — **대상이 없으면 Pages 빌드가 죽는다**
5. `{% include %}` 의 대상이 `_includes/` 에 있는가
6. front matter 의 `layout:` 이 `_layouts/` 에 있는가

**무엇을 훑는가:** front matter 가 있는 파일과 `_layouts/`·`_includes/` 전부.
**Jekyll 은 front matter 가 없는 파일에 Liquid 를 안 돌린다** — 그래서 안 본다.
이 경계가 오탐을 없앤다: `docs/*.md` 는 Liquid 를 설명하느라 `{% ... %}` 를 글자로 들고 있는데,
그것은 Jekyll 이 해석하지 않으므로 **여기서 잡으면 전부 오탐이다.**
**오탐을 내는 검사는 무시당하고, 무시당하는 검사는 없는 검사다**(§3-5).

닿지 않는 곳
------------
· **이것은 빌드가 아니다.** kramdown 이 실제로 무엇을 내는지 · 플러그인 버전 ·
  Pages 고유 제약(빌드 시간·용량·`github-pages` gem 이 고정한 버전)은 **하나도 안 본다.**
  **여기 통과는 「빌드가 된다」가 아니라 「이 여섯 가지로는 안 깨진다」다.**
· **YAML 파서가 다르다.** Jekyll 은 Ruby Psych 를, 이 파일은 PyYAML 을 쓴다.
  둘이 갈리는 문서가 있다. **PyYAML 이 없으면 「모름」이고 통과가 아니다.**
· **허용 플러그인 목록은 손에 들고 있다** — 그래서 낡는다. 목록 밖이면 **경고**로 내고
  실패로 안 만든다. 낡은 목록으로 FAIL 을 내면 그 FAIL 이 먼저 무시당한다.
· 링크가 **살아 있는지**는 안 본다. 그건 `check_links.py` 의 자리다.
· 허브 저장소가 이 기계에 없으면 **그 저장소는 「모름」**이다. 없는 것을 통과로 안 센다.

  python analysis/check_jekyll.py
  python analysis/check_jekyll.py --selftest
"""

import argparse
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# **[2026-09-12] 허브를 뺐다.** 그 저장소는 한 번도 push 된 적이 없다(사고 115).
# 살아 있는 Jekyll 지면은 인천 하나다 — 측심은 Jekyll 이 아니다.

# GitHub Pages 가 허용하는 플러그인. **손에 든 목록이라 낡는다** — 그래서 경고만 낸다.
PAGES_PLUGINS = {
    "jekyll-coffeescript", "jekyll-default-layout", "jekyll-gist",
    "jekyll-github-metadata", "jekyll-optional-front-matter", "jekyll-paginate",
    "jekyll-readme-index", "jekyll-titles-from-headings", "jekyll-relative-links",
    "jekyll-avatar", "jekyll-feed", "jekyll-mentions", "jekyll-redirect-from",
    "jekyll-remote-theme", "jekyll-seo-tag", "jekyll-sitemap", "jemoji",
    "jekyll-include-cache",
}

SKIP_DIRS = {".git", "_site", "_preview", "node_modules", ".jekyll-cache", "__pycache__"}

# 여는 태그 -> 닫는 태그
PAIRS = {
    "if": "endif", "for": "endfor", "unless": "endunless", "case": "endcase",
    "capture": "endcapture", "raw": "endraw", "comment": "endcomment",
    "tablerow": "endtablerow", "highlight": "endhighlight", "form": "endform",
}
CLOSERS = set(PAIRS.values())

TEXT_EXT = {".md", ".markdown", ".html", ".htm", ".xml", ".txt", ".css", ".js", ".json", ".svg"}


def _read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def front_matter(text):
    """front matter 원문을 낸다. 없으면 None, 안 닫혔으면 False."""
    if not text.startswith("---"):
        return None
    # 닫는 `---` 는 **줄 첫머리**에 있어야 한다. 이렇게 안 쓰면 빈 front matter
    # (`---\n---`)를 「안 닫힘」으로 오판한다 — 인수시험이 그것을 잡았다.
    m = re.match(r"---[ \t]*\r?\n(.*?)^---[ \t]*(\r?\n|$)", text, re.S | re.M)
    if not m:
        return False
    return m.group(1)


def targets(root):
    """**Jekyll 이 Liquid 를 돌리는 파일만** 낸다 — front matter 가 있는 것과
    `_layouts/`·`_includes/` 전부. 나머지는 정적 복사라 안 본다."""
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_base = os.path.relpath(base, root).replace("\\", "/")
        in_liquid_dir = rel_base.split("/")[0] in ("_layouts", "_includes")
        for f in sorted(files):
            if os.path.splitext(f)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(base, f)
            t = _read(p)
            fm = front_matter(t)
            if in_liquid_dir or fm is not None:
                out.append((p, t, fm))
    return out


def scan(root, name):
    """(실패목록, 경고목록, 분모dict). **분모를 같이 낸다**(사고 77)."""
    fails, warns = [], []
    d = {"파일": 0, "front matter": 0, "include": 0, "layout": 0, "link태그": 0}

    if not os.path.isdir(root):
        return None, None, None  # 「모름」

    # 1) _config.yml
    cfg_path = os.path.join(root, "_config.yml")
    if os.path.isfile(cfg_path):
        try:
            import yaml
        except ImportError:
            return None, None, None  # PyYAML 없음 -> 「모름」. 통과로 안 센다.
        try:
            cfg = yaml.safe_load(_read(cfg_path)) or {}
        except Exception as e:
            fails.append(f"{name}: _config.yml 이 YAML 로 안 읽힌다 — {e}")
            cfg = {}
        for pl in (cfg.get("plugins") or []):
            if pl not in PAGES_PLUGINS:
                warns.append(f"{name}: plugins 에 `{pl}` — 손에 든 허용 목록 밖이다(목록이 낡았을 수 있다)")
    else:
        warns.append(f"{name}: _config.yml 이 없다")

    try:
        import yaml
    except ImportError:
        return None, None, None

    for p, t, fm in targets(root):
        rel = os.path.relpath(p, root).replace("\\", "/")
        d["파일"] += 1

        # 2) front matter
        if fm is False:
            fails.append(f"{name}/{rel}: front matter 가 `---` 로 안 닫혔다")
        elif fm:
            d["front matter"] += 1
            try:
                meta = yaml.safe_load(fm) or {}
            except Exception as e:
                fails.append(f"{name}/{rel}: front matter YAML 이 안 읽힌다 — {e}")
                meta = {}
            # 6) layout
            lay = meta.get("layout") if isinstance(meta, dict) else None
            if lay:
                d["layout"] += 1
                if not os.path.isfile(os.path.join(root, "_layouts", f"{lay}.html")):
                    fails.append(f"{name}/{rel}: layout `{lay}` 이 `_layouts/` 에 없다")

        # 3) Liquid 짝
        stack = []
        for m in re.finditer(r"\{%-?\s*(\w+)", t):
            tag = m.group(1)
            if tag in PAIRS:
                stack.append(tag)
            elif tag in CLOSERS:
                want = next(k for k, v in PAIRS.items() if v == tag)
                if stack and stack[-1] == want:
                    stack.pop()
                else:
                    fails.append(f"{name}/{rel}: Liquid `{tag}` 의 짝이 없다")
                    break
        else:
            if stack:
                fails.append(f"{name}/{rel}: Liquid `{stack[-1]}` 이 안 닫혔다")

        # 4) link · post_url — 대상이 없으면 **빌드가 죽는다**
        for m in re.finditer(r"\{%-?\s*(link|post_url)\s+(.+?)\s*-?%\}", t):
            d["link태그"] += 1
            arg = m.group(2).strip().strip("'\"")
            if "{{" in arg:  # 변수라 정적으로 못 푼다
                warns.append(f"{name}/{rel}: `{m.group(1)}` 인수가 변수다 — 정적으로 못 본다")
                continue
            if not os.path.isfile(os.path.join(root, arg)):
                fails.append(f"{name}/{rel}: `{m.group(1)} {arg}` 의 대상이 없다 — Pages 빌드가 죽는다")

        # 5) include
        for m in re.finditer(r"\{%-?\s*include(?:_relative)?\s+([\w./-]+)", t):
            d["include"] += 1
            if not os.path.isfile(os.path.join(root, "_includes", m.group(1))):
                fails.append(f"{name}/{rel}: include `{m.group(1)}` 이 `_includes/` 에 없다")

    return fails, warns, d


def report(hook=False, strict=False):
    """훑고 판정한다.

    `hook` 은 pre-push 용이다 — **깨끗하면 아무것도 안 찍는다.**
    걸리면 stderr 로 찍되 **막지 않는다**(난간 다섯과 같은 이유: 여기서
    막히는 것은 운영자의 손이다). 차단은 `--strict`.
    """
    lines = []
    bad = []       # 빌드가 깨질 자리
    unknown = []   # 모름 — **통과가 아니다**(사고 26)
    for root, name in ((ROOT, "인천"),):
        fails, warns, d = scan(root, name)
        if fails is None:
            why = "저장소가 이 기계에 없다" if not os.path.isdir(root) else "PyYAML 이 없다"
            lines.append(f"  **모름**  {name} — {why}. **통과로 세지 않는다.**")
            unknown.append(name)
            continue
        denom = " · ".join(f"{k} {v}" for k, v in d.items())
        head = "실패" if fails else ("경고" if warns else "통과")
        lines.append(f"  {head:4} {name} — 발견 {len(fails)}건 / 검사 {denom}")
        for f in fails:
            lines.append(f"        FAIL  {f}")
        for w in warns:
            lines.append(f"        WARN  {w}")
        if fails:
            bad.append(name)

    rc = 1 if (bad or unknown) else 0

    if not hook:
        for ln in lines:
            print(ln)
        if rc == 0:
            print("\n빌드를 깨는 여섯 가지로는 안 깨진다. **「빌드가 된다」는 뜻이 아니다** — 이것은 빌드가 아니다.")
        return rc

    # ── pre-push 모드 ─────────────────────────────────────────────────────
    if rc == 0:
        return 0
    out = sys.stderr
    print("", file=out)
    print("Jekyll 빌드가 깨질 자리 — 실패 %d곳 · 모름 %d곳."
          % (len(bad), len(unknown)), file=out)
    print("  **허브는 첫 push 가 곧 첫 빌드다.** 빌드가 죽으면 되돌아갈 옛 판이 없어"
          " 사이트 전체가 404 로 남는다.", file=out)
    for ln in lines:
        print(ln, file=out)
    if strict:
        return 1
    print("  경고만 하고 통과시킨다. 막으려면 --strict.", file=out)
    return 0


# ----------------------------------------------------------------- 인수시험
def selftest():
    """**검사가 실제로 발화하는지**를 친다. 통과 픽스처만 두면 사고 26 이다 —
    깨진 픽스처마다 그 검사가 **실제로 잡는 것**을 확인한다."""
    try:
        import yaml  # noqa: F401
    except ImportError:
        print("  PyYAML 이 없다 — 인수시험을 못 돌린다. **모름**")
        return 1

    cases = []

    def build(files):
        d = tempfile.mkdtemp()
        for rel, body in files.items():
            p = os.path.join(d, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(body)
        return d

    CFG = "title: t\n"
    OKFM = "---\nlayout: default\n---\n"

    # 통과 — 이것이 실패하면 오탐이다
    d = build({"_config.yml": CFG, "_layouts/default.html": "{% if x %}a{% endif %}",
               "_includes/f.html": "x", "index.md": OKFM + "{% include f.html %}\n"})
    f, w, dn = scan(d, "t")
    cases.append(("온전한 저장소는 실패 0", f == [], f))

    # front matter 없는 파일은 **안 본다** — 오탐 경계
    d = build({"_config.yml": CFG, "notes.md": "{% if x %} 닫는 태그 없음 — Jekyll 이 안 돌린다\n"})
    f, w, dn = scan(d, "t")
    cases.append(("front matter 없는 파일의 Liquid 는 안 본다", f == [] and dn["파일"] == 0, (f, dn)))

    # `_includes/` 는 front matter 없어도 본다
    d = build({"_config.yml": CFG, "_includes/broken.html": "{% if x %}"})
    f, w, dn = scan(d, "t")
    cases.append(("_includes 는 front matter 없이도 본다", any("안 닫혔다" in x for x in f), f))

    # 짝 안 맞는 닫는 태그
    d = build({"_config.yml": CFG, "a.html": "---\n---\n{% for i in x %}{% endif %}"})
    f, w, dn = scan(d, "t")
    cases.append(("짝 안 맞는 닫는 태그를 잡는다", any("짝이 없다" in x for x in f), f))

    # link 대상 없음 — 빌드를 죽이는 것
    d = build({"_config.yml": CFG, "a.md": "---\n---\n{% link 없는파일.md %}"})
    f, w, dn = scan(d, "t")
    cases.append(("link 대상 없음을 잡는다", any("대상이 없다" in x for x in f), f))
    d = build({"_config.yml": CFG, "b.md": "x", "a.md": "---\n---\n{% link b.md %}"})
    f, w, dn = scan(d, "t")
    cases.append(("link 대상 있으면 안 잡는다", f == [] and dn["link태그"] == 1, (f, dn)))

    # include 대상 없음
    d = build({"_config.yml": CFG, "a.md": "---\n---\n{% include 없다.html %}"})
    f, w, dn = scan(d, "t")
    cases.append(("include 대상 없음을 잡는다", any("_includes/` 에 없다" in x for x in f), f))

    # layout 대상 없음
    d = build({"_config.yml": CFG, "a.md": "---\nlayout: 없다\n---\n"})
    f, w, dn = scan(d, "t")
    cases.append(("layout 대상 없음을 잡는다", any("`_layouts/` 에 없다" in x for x in f), f))

    # front matter 안 닫힘
    d = build({"_config.yml": CFG, "a.md": "---\nlayout: default\n"})
    f, w, dn = scan(d, "t")
    cases.append(("front matter 안 닫힘을 잡는다", any("안 닫혔다" in x for x in f), f))

    # front matter YAML 깨짐
    d = build({"_config.yml": CFG, "a.md": "---\na: [1, 2\n---\n"})
    f, w, dn = scan(d, "t")
    cases.append(("front matter YAML 깨짐을 잡는다", any("YAML 이 안 읽힌다" in x for x in f), f))

    # _config.yml YAML 깨짐
    d = build({"_config.yml": "a: [1,\nb: 2\n"})
    f, w, dn = scan(d, "t")
    cases.append(("_config.yml YAML 깨짐을 잡는다", any("_config.yml" in x for x in f), f))

    # 허용 목록 밖 플러그인은 **경고**지 실패가 아니다
    d = build({"_config.yml": "plugins:\n  - jekyll-남의것\n"})
    f, w, dn = scan(d, "t")
    cases.append(("목록 밖 플러그인은 경고지 실패가 아니다", f == [] and any("허용 목록 밖" in x for x in w), (f, w)))

    # 없는 저장소는 「모름」
    f, w, dn = scan(os.path.join(tempfile.mkdtemp(), "없다"), "t")
    cases.append(("없는 저장소는 모름을 낸다", f is None, f))

    bad = 0
    for label, ok, got in cases:
        print(f"  {label:44} {'OK' if ok else '**FAIL** ' + repr(got)[:120]}")
        if not ok:
            bad += 1
    print(f"\n  실패 {bad}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="Jekyll 빌드가 깨질 자리를 정적으로 훑는다.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--hook", action="store_true",
                    help="pre-push 용 — 깨끗하면 조용하다")
    ap.add_argument("--strict", action="store_true",
                    help="걸리면 종료코드 1 (pre-push 를 막는다)")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return report(hook=a.hook, strict=a.strict)


if __name__ == "__main__":
    sys.exit(main())

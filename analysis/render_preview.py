"""허브를 로컬에서 눈으로 보기 위한 미리보기 렌더러. 의존성 0.

이것이 무엇이 아닌가 — 먼저 읽어라.
====================================
**이 스크립트는 Jekyll이 아니다. 빌드 검증 수단이 아니다.**
GitHub Pages가 실제로 빌드에 성공하는지는 **push해 봐야만 안다.** 그건 운영자 몫이고,
이 도구는 그 자리를 대신하지 못한다. 미리보기를 실물로 착각하는 것이 사고 20이다.

**그러면 왜 있는가.** 종전에는 레이아웃·CSS를 고칠 때 **아무것도 못 보고 고쳤다.**
「확인 안 된 화면에 얹지 않는다」(사고 8·20)가 그래서 사이트 작업 전체를 막고 있었다.
이 도구는 **본문·레이아웃·CSS의 시각적 결과**를 보여 준다. 그 범위 안에서만 믿는다.

닿지 않는 곳
------------
- Jekyll의 Liquid 전체 문법 (여기 있는 것은 이 저장소가 실제로 쓰는 부분집합이다)
- 플러그인 (`jekyll-feed`의 `feed_meta`는 주석으로 치환한다)
- 마크다운 전체 명세 (kramdown과 다르게 렌더될 수 있다)
- 빌드 성패 · 배포 · 실제 URL 해석

지원하는 Liquid 부분집합
------------------------
{{ 변수 }} · {{ a | filter: arg }} · {% if %}{% elsif %}{% else %}{% endif %}
{% include x.html %} · {% assign %} · {%- feed_meta -%}(무시)
필터: relative_url absolute_url default truncate strip_newlines escape

사용
----
    python analysis/render_preview.py                 # 기본 경로(허브)를 렌더
    python analysis/render_preview.py --site <경로> --out <경로>
    python analysis/render_preview.py --selftest      # 인수시험
"""
from __future__ import annotations
import argparse
import html as htmllib
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SITE = os.path.abspath(os.path.join(HERE, "..", "..", "jisangj03-dev.github.io"))
DEFAULT_OUT = os.path.join(
    os.environ.get("TEMP", os.path.join(HERE, "..")), "vidimus_preview"
)


# ── 아주 작은 YAML 리더 (front matter · _config.yml 용) ────────────────────
def read_yaml(text: str) -> dict:
    """이 저장소가 쓰는 만큼만 읽는다: key: value · key: >- 접힘 · 리스트."""
    data: dict = {}
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(" ") or line.startswith("-"):
            continue  # 중첩·리스트 항목은 상위에서 소비한다
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">-", ">", "|", "|-"):  # 접힘 블록
            buf = []
            while i < len(lines) and (lines[i].startswith("  ") or not lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            joined = " ".join(x for x in buf if x)
            data[key] = joined
            continue
        if val == "":  # 리스트가 뒤따르는가
            items = []
            while i < len(lines) and lines[i].lstrip().startswith("- "):
                items.append(lines[i].lstrip()[2:].strip())
                i += 1
            data[key] = items if items else ""
            continue
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        data[key] = val
    return data


def split_front_matter(text: str):
    text = text.replace("\r\n", "\n")
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = read_yaml(text[3:end])
    body = text[end + 4 :].lstrip("\n")
    return fm, body


# ── Liquid 부분집합 ────────────────────────────────────────────────────────
def _lookup(expr: str, ctx: dict):
    expr = expr.strip()
    if (expr.startswith("'") and expr.endswith("'")) or (
        expr.startswith('"') and expr.endswith('"')
    ):
        return expr[1:-1]
    cur = ctx
    for part in expr.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part, "")
        else:
            return ""
    return cur


def _apply_filter(val, name: str, arg: str, ctx: dict):
    baseurl = str(_lookup("site.baseurl", ctx) or "")
    url = str(_lookup("site.url", ctx) or "")
    s = "" if val is None else str(val)
    if name == "relative_url":
        return (baseurl + s) if s.startswith("/") else s
    if name == "absolute_url":
        return (url + baseurl + s) if s.startswith("/") else s
    if name == "default":
        return s if s != "" else _lookup(arg, ctx)
    if name == "strip_newlines":
        return s.replace("\n", "")
    if name == "escape":
        return htmllib.escape(s)
    if name == "truncate":
        try:
            n = int(arg.strip())
        except (TypeError, ValueError):
            n = 50
        return s if len(s) <= n else s[: max(0, n - 3)] + "..."
    return s


_OUT_RE = re.compile(r"\{\{-?\s*(.+?)\s*-?\}\}", re.S)


def render_outputs(tpl: str, ctx: dict) -> str:
    def one(m):
        body = m.group(1)
        parts = [p.strip() for p in body.split("|")]
        val = _lookup(parts[0], ctx)
        for f in parts[1:]:
            if ":" in f:
                fname, farg = f.split(":", 1)
            else:
                fname, farg = f, ""
            val = _apply_filter(val, fname.strip(), farg.strip(), ctx)
        return "" if val is None else str(val)

    return _OUT_RE.sub(one, tpl)


def _truthy(v) -> bool:
    return not (v is None or v == "" or v is False or v == [])


def _eval_cond(cond: str, ctx: dict) -> bool:
    """**결합 순서에 주의.** `and`/`or` 를 비교 연산자보다 **먼저** 쪼개야 한다.

    처음에 `!=` 를 먼저 봤더니 `page.title and page.url != '/'` 이
    (`page.title and page.url`) != (`'/'`) 로 갈렸고, 홈에서 참이 나왔다.
    실제 Liquid 는 `and` 가 더 느슨하게 묶여 거짓이다.
    → **미리보기가 실물과 다르게 나왔고, 그 차이가 사이트 결함처럼 보였다.**
    이 도구의 고유 위험이 바로 이것이라 회귀 시험을 붙였다.
    """
    cond = cond.strip()
    if " or " in cond:
        return any(_eval_cond(p, ctx) for p in cond.split(" or "))
    if " and " in cond:
        return all(_eval_cond(p, ctx) for p in cond.split(" and "))
    for op, fn in (
        ("!=", lambda a, b: a != b),
        ("==", lambda a, b: a == b),
    ):
        if op in cond:
            left, right = cond.split(op, 1)
            return fn(str(_lookup(left, ctx)), str(_lookup(right, ctx)))
    return _truthy(_lookup(cond, ctx))


_TAG_RE = re.compile(r"\{%-?\s*(.*?)\s*-?%\}", re.S)


def render_tags(tpl: str, ctx: dict, includes_dir: str) -> str:
    """if/elsif/else/endif · include · assign · feed_meta 를 처리한다."""
    out = []
    pos = 0
    # 스택: 각 항목 = [현재 분기가 살아 있는가, 이미 참인 분기를 만났는가]
    stack: list[list[bool]] = []

    def alive() -> bool:
        return all(fr[0] for fr in stack)

    for m in _TAG_RE.finditer(tpl):
        if alive():
            out.append(tpl[pos : m.start()])
        pos = m.end()
        tag = m.group(1).strip()
        head = tag.split(" ", 1)[0]
        rest = tag[len(head) :].strip()

        if head == "if":
            parent_alive = alive()
            val = _eval_cond(rest, ctx) if parent_alive else False
            stack.append([val, val])
        elif head == "elsif":
            if not stack:
                continue
            fr = stack[-1]
            if fr[1]:
                fr[0] = False
            else:
                parent_alive = all(f[0] for f in stack[:-1])
                val = _eval_cond(rest, ctx) if parent_alive else False
                fr[0] = val
                fr[1] = fr[1] or val
        elif head == "else":
            if not stack:
                continue
            fr = stack[-1]
            fr[0] = not fr[1]
            fr[1] = True
        elif head == "endif":
            if stack:
                stack.pop()
        elif head == "include":
            if alive():
                name = rest.split()[0] if rest else ""
                path = os.path.join(includes_dir, name)
                if os.path.isfile(path):
                    with open(path, encoding="utf-8") as f:
                        inc = f.read()
                    out.append(render_template(inc, ctx, includes_dir))
                else:
                    out.append(f"<!-- include 없음: {htmllib.escape(name)} -->")
        elif head == "assign":
            if alive() and "=" in rest:
                k, v = rest.split("=", 1)
                ctx[k.strip()] = render_outputs("{{" + v.strip() + "}}", ctx)
        elif head == "feed_meta":
            if alive():
                out.append("<!-- feed_meta (플러그인. 미리보기에서는 비운다) -->")
        # 그 밖의 태그는 조용히 버린다
    if alive():
        out.append(tpl[pos:])
    return "".join(out)


def render_template(tpl: str, ctx: dict, includes_dir: str) -> str:
    return render_outputs(render_tags(tpl, ctx, includes_dir), ctx)


# ── 마크다운 부분집합 ──────────────────────────────────────────────────────
BLOCK_TAGS = (
    "div|section|article|aside|header|footer|nav|main|figure|figcaption|"
    "p|ul|ol|li|dl|dt|dd|table|thead|tbody|tr|td|th|blockquote|pre|form|h[1-6]"
)
BLOCK_OPEN_RE = re.compile(r"^<(?:%s)\b" % BLOCK_TAGS, re.I)
TAG_SCAN_RE = re.compile(r"<(/?)(%s)\b[^>]*>" % BLOCK_TAGS, re.I)
VOID_TAGS = {"br", "hr", "img", "input", "meta", "link"}


def _inline(s: str) -> str:
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img alt="\1" src="\2">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def markdown(text: str) -> str:
    """이 저장소가 실제로 쓰는 문법만: 제목·문단·강조·링크·목록·표·인용·구분선·HTML 통과."""
    lines = text.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 원시 HTML 블록 — 여는 태그부터 짝이 맞을 때까지 통째로 통과시킨다.
        #
        # **한 줄씩 통과시키면 안 된다.** 처음에 그렇게 짰다가 `<p class="hero-lede">` 안의
        # 줄바꿈이 문단 3개로 갈라졌고, 화면에서 그것이 **사이트 결함처럼 보였다.**
        # 미리보기의 인공물을 실물의 결함으로 읽는 것 — 그게 이 도구의 가장 큰 위험이다.
        # kramdown도 블록 HTML 안은 markdown="1"이 없으면 마크다운으로 안 읽는다.
        if BLOCK_OPEN_RE.match(stripped):
            depth = 0
            block = []
            while i < n:
                cur = lines[i]
                block.append(cur)
                i += 1
                for tm in TAG_SCAN_RE.finditer(cur):
                    name = tm.group(2).lower()
                    if name in VOID_TAGS or tm.group(0).rstrip().endswith("/>"):
                        continue
                    depth += -1 if tm.group(1) else 1
                if depth <= 0:
                    break
            out.append("\n".join(block))
            continue

        if re.match(r"^(-{3,}|\*{3,})$", stripped):
            out.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
            i += 1
            continue

        # 표
        if "|" in stripped and i + 1 < n and re.match(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$", lines[i + 1]):
            def cells(row: str):
                row = row.strip()
                if row.startswith("|"):
                    row = row[1:]
                if row.endswith("|"):
                    row = row[:-1]
                return [c.strip() for c in row.split("|")]

            head = cells(stripped)
            i += 2
            body = []
            while i < n and "|" in lines[i] and lines[i].strip():
                body.append(cells(lines[i]))
                i += 1
            t = ['<div class="tablewrap"><table><thead><tr>']
            t += [f"<th>{_inline(c)}</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in body:
                t.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        # 인용
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>")
            continue

        # 목록
        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            tag = "ol" if ordered else "ul"
            items = []
            while i < n and (
                re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])
            ):
                item = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", lines[i])
                i += 1
                # 이어지는 들여쓴 줄을 같은 항목으로 붙인다
                while i < n and lines[i].startswith("  ") and lines[i].strip() \
                        and not re.match(r"^\s*(?:[-*]|\d+\.)\s+", lines[i]):
                    item += " " + lines[i].strip()
                    i += 1
                items.append(f"<li>{_inline(item)}</li>")
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue

        # 문단
        buf = [stripped]
        i += 1
        while i < n and lines[i].strip() and not re.match(
            r"^\s*(#{1,6}\s|[-*]\s|\d+\.\s|>|<|\||-{3,})", lines[i]
        ):
            buf.append(lines[i].strip())
            i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


# ── 사이트 렌더 ────────────────────────────────────────────────────────────
def build(site_dir: str, out_dir: str, verbose: bool = True) -> list[str]:
    cfg_path = os.path.join(site_dir, "_config.yml")
    with open(cfg_path, encoding="utf-8") as f:
        site = read_yaml(f.read())
    # 미리보기는 로컬 파일이므로 baseurl 을 비운다 — 절대경로 링크가 깨지지 않게
    site["baseurl"] = ""
    includes_dir = os.path.join(site_dir, "_includes")
    layouts_dir = os.path.join(site_dir, "_layouts")

    pages = []
    for root, dirs, files in os.walk(site_dir):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_"))]
        for fn in files:
            if fn.endswith(".md") and fn != "README_운영자안내.md":
                pages.append(os.path.join(root, fn))

    os.makedirs(out_dir, exist_ok=True)
    # 자산은 파일 단위로 덮어쓴다. rmtree 로 지우면 미리보기 서버가 CSS를 물고 있을 때
    # WinError 5 로 죽는다(실측). 렌더가 서버 실행 여부에 의존하면 도구가 안 쓰인다.
    assets_src = os.path.join(site_dir, "assets")
    if os.path.isdir(assets_src):
        for root, _dirs, files in os.walk(assets_src):
            rel = os.path.relpath(root, assets_src)
            dst_dir = os.path.join(out_dir, "assets", rel) if rel != "." else os.path.join(out_dir, "assets")
            os.makedirs(dst_dir, exist_ok=True)
            for fn in files:
                try:
                    shutil.copyfile(os.path.join(root, fn), os.path.join(dst_dir, fn))
                except PermissionError:
                    print(f"  [건너뜀] 잠긴 파일: assets/{fn}")

    written = []
    for path in pages:
        with open(path, encoding="utf-8") as f:
            fm, body = split_front_matter(f.read())
        rel = os.path.relpath(path, site_dir).replace("\\", "/")
        permalink = fm.get("permalink") or (
            "/" if rel == "index.md" else "/" + rel[:-3].rstrip("/") + "/"
        )
        if rel.endswith("/index.md"):
            permalink = fm.get("permalink") or "/" + rel[: -len("index.md")]
        page = dict(fm)
        page["url"] = permalink
        ctx = {"site": site, "page": page}

        content = markdown(render_template(body, ctx, includes_dir))
        ctx["content"] = content

        layout = fm.get("layout", "default")
        seen = set()
        while layout and layout not in seen:
            seen.add(layout)
            lp = os.path.join(layouts_dir, layout + ".html")
            if not os.path.isfile(lp):
                break
            with open(lp, encoding="utf-8") as f:
                lfm, ltpl = split_front_matter(f.read())
            ctx["content"] = render_template(ltpl, ctx, includes_dir)
            layout = lfm.get("layout")

        # 미리보기에서 링크가 실제로 눌리도록 permalink -> 파일명 매핑
        slug = "index" if permalink == "/" else permalink.strip("/").replace("/", "_")
        target = os.path.join(out_dir, slug + ".html")
        doc = (
            "<!doctype html>\n<html lang=\"ko\">\n<head>\n"
            + "<!-- 미리보기 — Jekyll 빌드가 아니다. analysis/render_preview.py -->\n"
            + ctx["content"]
        )
        # default 레이아웃이 이미 완전한 문서를 만들면 그대로 쓴다
        full = ctx["content"]
        if full.lstrip().lower().startswith("<!doctype") or "<html" in full[:400].lower():
            doc = full
        with open(target, "w", encoding="utf-8") as f:
            f.write(doc)
        written.append(target)
        if verbose:
            print(f"  [렌더] {rel:24s} -> {os.path.basename(target)}  ({len(doc):,} B)")
    return written


def selftest() -> int:
    print("── 인수시험: 미리보기 렌더러 ──")
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print(f"  {'OK  ' if good else 'FAIL'} {label}")
        if not good:
            print(f"       기대={want!r}\n       실제={got!r}")

    ctx = {"site": {"title": "T", "baseurl": "", "url": "https://x"}, "page": {"url": "/a/"}}
    check("출력 치환", render_outputs("{{ site.title }}", ctx), "T")
    check("relative_url", render_outputs("{{ '/v/' | relative_url }}", ctx), "/v/")
    check("absolute_url", render_outputs("{{ '/v/' | absolute_url }}", ctx), "https://x/v/")
    check("default 필터", render_outputs("{{ page.zz | default: site.title }}", ctx), "T")
    check(
        "if 참",
        render_tags("{% if site.title %}Y{% else %}N{% endif %}", ctx, ""),
        "Y",
    )
    check(
        "if 거짓 -> else",
        render_tags("{% if page.none %}Y{% else %}N{% endif %}", ctx, ""),
        "N",
    )
    check(
        "== 비교 (거짓)",
        render_tags("{% if page.url == '/' %}H{% else %}P{% endif %}", ctx, ""),
        "P",
    )
    check(
        "중첩 if 안에서 바깥이 거짓이면 안쪽도 안 낸다",
        render_tags("{% if page.none %}{% if site.title %}X{% endif %}{% endif %}", ctx, ""),
        "",
    )
    # 회귀: and/or 가 비교 연산자보다 먼저 묶이면 홈의 og:title 이 뒤집힌다.
    home = {"site": {"title": "T", "baseurl": "", "url": "https://x"}, "page": {"title": "홈", "url": "/"}}
    check(
        "`A and B != C` 에서 and 가 느슨하게 묶인다 (홈)",
        render_tags("{% if page.title and page.url != '/' %}P{% else %}H{% endif %}", home, ""),
        "H",
    )
    sub = {"site": {"title": "T", "baseurl": "", "url": "https://x"}, "page": {"title": "정정", "url": "/corrections/"}}
    check(
        "같은 식이 하위 페이지에서는 참",
        render_tags("{% if page.title and page.url != '/' %}P{% else %}H{% endif %}", sub, ""),
        "P",
    )
    check("표 렌더", "<table>" in markdown("| a | b |\n|---|---|\n| 1 | 2 |"), True)
    check("제목 렌더", markdown("## 가"), "<h2>가</h2>")
    check("강조 렌더", markdown("**가**"), "<p><strong>가</strong></p>")
    check("원시 HTML 통과", markdown('<div class="band">x</div>'), '<div class="band">x</div>')
    # 회귀: 여러 줄 HTML 블록을 한 줄씩 통과시키면 안쪽 줄바꿈이 문단으로 갈라진다.
    # 그러면 화면에서 미리보기의 인공물이 사이트 결함처럼 보인다. 실제로 한 번 그랬다.
    multiline = markdown('<div class="b">\n  <p class="x">\n    가\n    나\n  </p>\n</div>\n\n밖\n')
    check("여러 줄 HTML 블록이 안 갈라진다", multiline.count("<p"), 2)
    check("블록 뒤 문단은 정상 처리", "<p>밖</p>" in multiline, True)
    fm, body = split_front_matter("---\nlayout: page\ntitle: 가\n---\n\n본문\n")
    check("front matter", (fm.get("layout"), fm.get("title"), body.strip()), ("page", "가", "본문"))

    print("통과" if ok else "실패")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=DEFAULT_SITE)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not os.path.isdir(a.site):
        print(f"[중단] 사이트 폴더가 없다: {a.site}")
        return 2
    print(f"== 미리보기 렌더 ==\n  원본 {a.site}\n  출력 {a.out}")
    written = build(a.site, a.out)
    print(f"\n{len(written)}쪽. 첫 화면: {os.path.join(a.out, 'index.html')}")
    print("**이것은 Jekyll 빌드가 아니다.** 빌드 성패는 push해야 안다(사고 20).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

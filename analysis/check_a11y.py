# -*- coding: utf-8 -*-
"""접근성 게이트 — **읽는 수단이 화면 하나가 아니다.**

왜 있는가
---------
2026-08-30에 이 축을 **처음** 실측했다. 지면 아홉 개를 만들어 놓고 한 번도 안 봤다.
나온 것 셋:

  1. **`--ink-3` 의 대비가 모자랐다** — 종이 3.72 · 카드 3.82 · 회색바탕 3.43.
     WCAG AA 본문 기준은 4.5다. **그리고 그 토큰이 칠하는 것이 사이트에서 가장 작은 글자다** —
     표 머리 10 px · 주석 · 발행 메타. **가장 읽기 어려운 글자에 가장 낮은 대비를 줬다.**
  2. **건너뛰기 링크가 없었다** — 키보드로 오는 사람은 지면마다 내비 8개를 지나야 본문에 닿았다.
  3. **표에 이름(`caption`)도 머리 방향(`th scope`)도 없었다** — 낭독기가 표에 들어가며
     「표, 7열 12행」이라고만 말한다. 지면 하나에 표가 넷이면 넷 다 이름이 없다.

**셋 다 화면에서는 안 보인다.** 인쇄 판형이 깨져 있던 것과 같은 종류다(사고 68) —
쓰는 사람이 따로 있는 경로는, 그 경로로 한 번 지나가 보기 전까지 멀쩡해 보인다.

무엇을 보는가
-------------
**정적으로 확인되는 것만 본다.** 대비는 브라우저에서 실측해 토큰에 반영했으나
**이 스크립트는 색을 계산하지 않는다** — CSS 변수의 최종 계산값은 렌더러가 있어야 안다.
여기서 세는 것은 **표기의 유무**다.

  · 표: `caption` 이 있는가 · `th` 에 `scope` 가 있는가
  · 그림: `svg` 에 `role` 과 이름이 있는가 · `img` 에 `alt` 가 있는가
  · 이동: 건너뛰기 링크가 있는가 · 그 목적지가 실재하는가
  · 링크: 글자도 이름도 없는 링크가 있는가

  python analysis/check_a11y.py             # 경고. 종료 0
  python analysis/check_a11y.py --strict    # 있으면 종료 1
  python analysis/check_a11y.py --hook      # pre-push 에서 조용히
  python analysis/check_a11y.py --selftest

닿지 않는 곳
------------
· **마크다운 표는 세지 않는다.** 따로 행 수만 센다.
  [2026-08-30] 로컬 렌더러로 그려 재 보니 **표 8개 · 이름 0 · scope 0** 이었다 —
  「안 봤다」가 아니라 **「봤고 없다」**다. 다만 **kramdown 이 같은 것을 내는지는 [미확인]**
  이고, 고치는 수단(`{: }` IAL)이 거기서 도는지도 확인할 수 없어 **손대지 않았다.**
  안 되면 그 글자가 지면에 그대로 보인다 — **확인 못 한 화면에 얹지 않는다**(사고 8·20).
· **대비를 계산하지 않는다.** 위 참조.
· **속성의 존재는 낭독의 확인이 아니다.** `caption` 이 붙었다는 것과 낭독기가 그것을
  읽어 준다는 것은 다른 사실이고, **낭독기로 들어 본 사람은 아직 없다.**
· 초점 순서·동적 상태는 안 본다. 이 사이트에 스크립트가 없어 지금은 문제가 안 되지만,
  **스크립트가 생기면 이 검사는 그만큼 낡는다.**
"""

import argparse
import io
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# **[2026-09-12] 허브에서 인천으로 돌렸다.** 이 검사가 보던 지면은 한 번도 push 된 적이
# 없는 저장소의 것이었다(사고 115). **인천 저장소가 살아 있는 Jekyll 사이트다** —
# `_includes/masthead.html` · `_layouts/default.html` · `assets/css/sounding.css` 가 여기 있다.
SITE = ROOT

TABLE = re.compile(r"<table\b.*?</table>", re.I | re.S)
TH = re.compile(r"<th\b([^>]*)>", re.I)
SVG = re.compile(r"<svg\b([^>]*)>(.*?)</svg>", re.I | re.S)
IMG = re.compile(r"<img\b([^>]*)>", re.I)
LINK = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
MDROW = re.compile(r"(?m)^\s*\|")


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def audit_html(html):
    """지면 본문 하나. 반환 (문제 목록, 셈)."""
    bad = []
    tables = TABLE.findall(html)
    for t in tables:
        if "<caption" not in t.lower():
            bad.append("표에 이름(<caption>)이 없다 — 낭독기가 「표, N열」만 말한다: %s…"
                       % strip_tags(t)[:32])
        noscope = [m for m in TH.finditer(t)
                   if not re.search(r"\bscope\s*=", m.group(1), re.I)]
        if noscope:
            bad.append("th %d개에 scope 가 없다 — 열 머리인지 행 머리인지 안 알려 준다"
                       % len(noscope))
    for attrs, inner in SVG.findall(html):
        # **장식은 이름을 안 붙이는 것이 맞다.** `aria-hidden="true"` 는
        # 「이건 읽지 마라」는 뜻이고, 거기에 `role="img"` 와 이름을 요구하면
        # **틀린 것을 시키는 검사**가 된다. [2026-08-30] 첫 화면 스카이라인과
        # 404 부표를 넣자마자 이 오탐이 났다.
        # **오탐을 내는 검사는 무시당하고, 무시당하는 검사는 없는 검사다**(§3-5).
        if re.search(r'aria-hidden\s*=\s*"true"', attrs, re.I):
            # 다만 장식에 글자가 있으면 그것은 장식이 아니다 —
            # 읽을 것이 있는데 숨긴 것이다.
            if "<text" in inner.lower():
                bad.append("aria-hidden 인 svg 안에 글자가 있다 — 읽을 것을 숨기고 있다")
            continue
        if not re.search(r"\brole\s*=", attrs, re.I):
            bad.append("svg 에 role 이 없다")
        named = (re.search(r"\baria-label\s*=", attrs, re.I)
                 or re.search(r"\baria-labelledby\s*=", attrs, re.I)
                 or "<title" in inner.lower())
        if not named:
            bad.append("svg 에 이름이 없다 — 그림이 무엇을 말하는지 글로 없다")
    for attrs in IMG.findall(html):
        if not re.search(r"\balt\s*=", attrs, re.I):
            bad.append("img 에 alt 가 없다")
    for attrs, inner in LINK.findall(html):
        if not strip_tags(inner) and not re.search(r"\baria-label\s*=", attrs, re.I):
            bad.append("글자도 이름도 없는 링크가 있다")
    return bad, {"표": len(tables), "마크다운표행": len(MDROW.findall(html))}


def audit(path):
    return audit_html(io.open(path, encoding="utf-8").read())


def audit_shell():
    """제호·레이아웃·판형 — 지면마다가 아니라 한 번만 본다."""
    mast = os.path.join(SITE, "_includes", "masthead.html")
    lay = os.path.join(SITE, "_layouts", "default.html")
    css = os.path.join(SITE, "assets", "css", "sounding.css")
    for p in (mast, lay, css):
        if not os.path.exists(p):
            return ["%s 를 못 찾았다 — **모른다**(통과가 아니다)" % os.path.basename(p)]
    m = io.open(mast, encoding="utf-8").read()
    l = io.open(lay, encoding="utf-8").read()
    c = io.open(css, encoding="utf-8").read()
    bad = []
    # **[2026-09-12] 찾는 방식을 명제에 맞췄다 — 느슨하게 한 것이 아니다.**
    # 종전 판은 `class="skiplink"` 가 **제호 조각 안에** 있어야 통과했다. 그것은
    # 옛 허브의 마크업이고, 이 검사가 거는 명제는 「키보드로 내비를 건너뛸 수 있는가」다.
    # 인천 지면은 같은 것을 `class="skip"` 으로 **레이아웃에** 두고 있었다 —
    # 명제는 참인데 검사가 FAIL 을 냈다. **구현 자리를 못 박으면 명제를 못 본다.**
    sk = re.search(r'<a[^>]*class="[^"]*\b(skip|skiplink)\b[^"]*"[^>]*href="#([\w-]+)"',
                   m + "\n" + l)
    if not sk:
        bad.append("건너뛰기 링크가 없다 — 키보드로는 지면마다 내비를 전부 지나야 한다")
    else:
        cls, dest = sk.group(1), sk.group(2)
        if ('id="%s"' % dest) not in l:
            bad.append("건너뛰기 링크가 없는 곳(#%s)을 가리킨다" % dest)
        if (".%s:focus" % cls) not in c:
            bad.append("건너뛰기 링크가 포커스에서 나타나는 규칙이 없다 — 숨은 채로 남는다")
    if "lang=" not in l:
        bad.append("html 에 lang 이 없다 — 낭독기가 어느 말인지 모른다")
    # **`.vh` 는 쓰는 지면에서만 요구한다.** 감춘 이름을 쓰지 않는 지면에 그 규칙을
    # 요구하면 **안 쓰는 패턴의 부재를 결함으로 세는 것**이고, 그것은 오탐이다.
    # 인천 지면은 표 이름을 `aria-labelledby` 로 **보이는 제목**에 잇는다 — 감추지 않는다.
    if 'class="vh"' in "".join(pages_text()) and ".vh{" not in c:
        bad.append("`.vh` 를 쓰는 지면이 있는데 `.vh` 규칙이 없다 — 감춘 이름이 화면에 보인다")
    return bad


def pages_text():
    """지면·조각의 본문 전부. `.vh` 같은 **패턴을 실제로 쓰는가**를 묻는 데 쓴다."""
    out = []
    for p in pages():
        try:
            out.append(io.open(p, encoding="utf-8").read())
        except OSError:
            pass
    return out


def pages():
    """지면과 **조각(`_includes`)** 을 함께 본다.

    [2026-08-30] 처음엔 `_` 로 시작하는 폴더를 통째로 건너뛰었다. 그런데 첫 화면
    스카이라인은 `_includes/skyline.html` 에 있다 — **지면에 보이는 그림이 검사 밖에
    있었다.** 조각은 지면의 일부이고, 지면에 나가는 것이면 검사도 나가야 한다.

    `_includes`·`_layouts` 만 본다. `_site` 같은 **산출물은 원본이 아니므로** 안 본다
    (사고 71 — 검사기가 자기 도구의 출력을 원본으로 읽으면 그 판정은 전부 잡음이다).
    """
    WATCH = ("_includes", "_layouts")
    out = []
    for dirpath, dirnames, files in os.walk(SITE):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".")
                       and (not d.startswith("_") or d in WATCH)]
        here = os.path.basename(dirpath)
        for f in files:
            if f.endswith(".md") or (f.endswith(".html") and here in WATCH):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def run():
    rows = []
    for p in pages():
        bad, n = audit(p)
        rows.append((os.path.relpath(p, SITE).replace("\\", "/"), bad, n))
    return rows, audit_shell()


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 양방향으로 친다 (사고 39) ──")

    # 잡아야 한다
    chk("이름 없는 표를 잡는다",
        any("이름" in x for x in audit_html("<table><tr><th>가</th></tr></table>")[0]), True)
    chk("scope 없는 th 를 잡는다",
        any("scope" in x for x in audit_html("<table><tr><th>가</th></tr></table>")[0]), True)
    chk("role 없는 svg 를 잡는다",
        any("role" in x for x in audit_html("<svg><rect/></svg>")[0]), True)
    chk("이름 없는 svg 를 잡는다",
        any("이름이 없다" in x for x in audit_html('<svg role="img"><rect/></svg>')[0]), True)
    chk("alt 없는 img 를 잡는다",
        any("alt" in x for x in audit_html('<img src="a.png">')[0]), True)
    chk("글자 없는 링크를 잡는다",
        any("링크" in x for x in audit_html('<a href="/x"></a>')[0]), True)

    # **안 잡아야 한다.** 한쪽만 시험하면 규칙을 껐는지 그었는지 구분이 안 된다.
    good = ('<table><caption class="vh">이름</caption>'
            '<thead><tr><th scope="col">가</th></tr></thead>'
            '<tbody><tr><th scope="row">1</th><td>2</td></tr></tbody></table>'
            '<svg role="img" aria-label="그림"><rect/></svg>'
            '<img src="a.png" alt="설명"><a href="/x">글자</a>')
    chk("갖춘 지면은 아무것도 안 잡는다", audit_html(good)[0], [])
    chk("aria-labelledby 도 이름으로 센다",
        audit_html('<svg role="img" aria-labelledby="t"><title id="t">가</title></svg>')[0], [])
    # **장식은 통과시킨다.** 여기서 오탐을 내면 이 검사 전체가 무시당한다.
    chk("aria-hidden 인 장식은 role·이름을 안 물어본다",
        audit_html('<svg aria-hidden="true"><rect/></svg>')[0], [])
    # 그러나 장식 안에 글자가 있으면 그것은 장식이 아니다.
    chk("장식 안의 글자는 잡는다",
        any("숨기고" in x for x in
            audit_html('<svg aria-hidden="true"><text>값</text></svg>')[0]), True)

    # 마크다운 표는 **모르는 것**이다 — 잡지도 통과시키지도 않고 따로 센다.
    bad_md, n_md = audit_html("| 가 | 나 |\n|---|---|\n")
    chk("마크다운 표를 문제로 세지 않는다", bad_md, [])
    chk("대신 몇 행인지는 센다", n_md["마크다운표행"], 2)

    print("── 인수시험: 제호 검사가 실제로 발화하는가 ──")
    # **저장소의 현재 상태를 안 박는다**(사고 65). 임시 골격으로 기전만 친다.
    with tempfile.TemporaryDirectory() as d:
        global SITE
        keep = SITE
        try:
            os.makedirs(os.path.join(d, "_includes"))
            os.makedirs(os.path.join(d, "_layouts"))
            os.makedirs(os.path.join(d, "assets", "css"))
            io.open(os.path.join(d, "_includes", "masthead.html"), "w",
                    encoding="utf-8").write("<header></header>")
            io.open(os.path.join(d, "_layouts", "default.html"), "w",
                    encoding="utf-8").write("<html><main></main></html>")
            css_path = os.path.join(d, "assets", "css", "sounding.css")
            io.open(css_path, "w", encoding="utf-8").write("body{}")
            SITE = d
            bad = audit_shell()
            chk("건너뛰기 링크 없음을 잡는다", any("건너뛰기 링크가 없다" in b for b in bad), True)
            chk("lang 없음을 잡는다", any("lang" in b for b in bad), True)
            # **안 쓰는 패턴의 부재를 결함으로 안 센다** — 골격에 `.vh` 가 없으므로 안 나와야 맞다.
            chk("안 쓰는 `.vh` 를 요구하지 않는다", any(".vh" in b for b in bad), False)
            io.open(os.path.join(d, "index.md"), "w", encoding="utf-8").write(
                '<table><caption class="vh">가</caption></table>')
            chk("쓰는 지면이 생기면 `.vh` 를 요구한다",
                any(".vh" in b for b in audit_shell()), True)
            os.remove(os.path.join(d, "index.md"))

            io.open(os.path.join(d, "_includes", "masthead.html"), "w",
                    encoding="utf-8").write('<a class="skiplink" href="#nowhere">가</a>')
            io.open(css_path, "w", encoding="utf-8").write(".skiplink:focus{}")
            chk("목적지가 없는 건너뛰기를 잡는다",
                any("없는 곳" in b for b in audit_shell()), True)
            # **자리를 안 박는다** — 레이아웃에 둔 건너뛰기도 같은 명제를 채운다(인천 지면이 그렇다).
            io.open(os.path.join(d, "_includes", "masthead.html"), "w",
                    encoding="utf-8").write("<header></header>")
            io.open(os.path.join(d, "_layouts", "default.html"), "w",
                    encoding="utf-8").write(
                '<html lang="ko"><a class="skip" href="#main">가</a>'
                '<main id="main"></main></html>')
            io.open(css_path, "w", encoding="utf-8").write(".skip:focus{}")
            chk("레이아웃에 둔 건너뛰기도 통과시킨다", audit_shell(), [])
            io.open(css_path, "w", encoding="utf-8").write("body{}")
            chk("포커스 규칙이 없으면 잡는다",
                any("포커스" in b for b in audit_shell()), True)
        finally:
            SITE = keep

    print("── 인수시험: 실물 ──")
    rows, shell = run()
    chk("인천 지면을 찾는다", len(rows) >= 8, True)
    for name, bad, n in rows:
        if bad:
            print("  ·  %-24s %d건" % (name, len(bad)))
    if shell:
        for b in shell:
            print("  ·  (제호) %s" % b)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="지면의 접근성 표기를 센다.")
    ap.add_argument("--strict", action="store_true", help="문제가 있으면 종료코드 1")
    ap.add_argument("--hook", action="store_true", help="pre-push 용 — 문제 있을 때만 말한다")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    rows, shell = run()
    total = sum(len(b) for _, b, _ in rows) + len(shell)
    mdrows = sum(n["마크다운표행"] for _, _, n in rows)

    if a.hook and not total:
        return 0

    if not a.hook:
        print("== 접근성 표기 ==")
        for name, bad, n in rows:
            print("  %-24s 표 %2d · %s"
                  % (name, n["표"], "**%d건**" % len(bad) if bad else "문제 없음"))
            for b in bad:
                print("      · %s" % b)
        print("  %-24s %s" % ("(제호·레이아웃·판형)",
                              "**%d건**" % len(shell) if shell else "문제 없음"))
        for b in shell:
            print("      · %s" % b)
        print("\n  마크다운 표 행 %d — **이 검사가 안 보는 자리다.**" % mdrows)
        print("  [2026-08-30 실측] 로컬 렌더러로 그려 재 봤다 — **표 8개 · 이름 0 · scope 0.**")
        print("  「안 봤다」가 아니라 **「봤고 없다」**로 남는다. 다만 그것은 우리 렌더러의")
        print("  결과이고 **kramdown 이 같은 것을 내는지는 [미확인]** 이다(로컬 Jekyll 없음).")
        print("  **고치지 않았다** — kramdown 이 `{: }` 를 어떻게 다루는지 확인할 수 없고,")
        print("  안 되면 그 글자가 지면에 그대로 보인다. **확인 못 한 화면에 얹지 않는다**(사고 8·20).")

    if not total:
        if not a.hook:
            print("\n표기 문제 0건.")
        return 0

    out = sys.stderr
    print("\n접근성 표기 문제 %d건." % total, file=out)
    print("  **화면에서는 안 보이는 종류다** — 낭독기·키보드로 오는 사람에게만 보인다.", file=out)
    if a.strict:
        return 1
    print("  경고만 하고 통과시킨다. 막으려면 --strict.", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

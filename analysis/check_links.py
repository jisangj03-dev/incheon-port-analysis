# -*- coding: utf-8 -*-
"""링크 검사 — **허브-스포크 사이트에서 링크가 무엇을 배달하는지**를 본다.

왜 있는가
---------
2026-08-29 실측. 허브 `/terminals/` 지면은 이번 라운드의 실체이고, 그 지면이 내거는 것은
**「원본의 주소·SHA-256 동봉 · 지면은 CSV 에서 생성한다」**이다. 그 약속을 지탱하는 것은
지면에 박힌 네 개의 링크(`terminal_monthly.csv` · `..._sources.csv` · 수집 코드 · 생성 코드)다.
**네 개 전부 404였다.** `report_08` 링크도 같이 404였다.

죽은 이유는 결함이 아니라 **순서**다 — 그 파일들은 아직 push 되지 않은 인천 커밋 안에 있다.
그래서 이 도구의 첫 번째 일은 「죽었다/살았다」가 아니라 **그 둘을 가르는 것**이다.

  **링크에도 지위가 있다.** 값에 창과 지위가 같이 가야 하듯(사고 22), 링크도 그렇다.
  우리 것이고 로컬에 있고 아직 안 올라간 404는 **죽은 링크가 아니라 `push대기`**다.

이 구분이 없으면 이 도구는 지금 당장 7건을 「죽음」으로 외치고, **오탐을 내는 검사는
무시당한다**(지침 §3-5가 린터에 대해 적은 그대로다). 무시당하는 검사는 없는 검사다.

**그리고 만들다가 더 큰 것이 나왔다 — `날것`.**
발행본 8편의 편간 상호 링크는 전부 `report_01_….md` 처럼 **`.md` 를 가리킨다.**
그 주소는 404 가 아니다 — 실측하면 **HTTP 200 · `Content-Type: text/markdown`** 이 온다.
크롬으로 실제로 열어 확인했다(사고 20). 독자가 보는 것은 **마크다운 원본 덤프**다 —
차트는 `![...](images/….png)` 라는 글자로 남고, 표는 `| 1월 | 90,346 |` 파이프 줄로 남고,
**§2.2 표기 블록도 렌더되지 않는다.**

  **그러므로 HTTP 200 을 「살아있음」이라 부르면 이 도구가 거짓 PASS 를 낸다.**
  사고 26이 같은 자리다 — 그때의 「FAIL 0」도 통과가 아니라 부재였다.

`날것`은 네트워크 없이 정해진다. 대상이 `.md` 인데 같은 자리에 렌더된 `.html` 이 있으면
**그 링크는 렌더된 지면 대신 소스를 배달한다.** 그것을 그렇게 부른다.

**지침 §1.4 1층은 「1차 출처 링크 100%」를 편마다 요구한다.**
404 를 내는 링크는 1차 출처가 아니라 **1차 출처가 있다는 주장**이다. 그 둘을 가르는 장치가
검사 장치 11종 중에 없었다 — `render_preview.py` 는 지면을 그리지만 링크를 따라가지 않는다.

무엇을 보는가
-------------
저장소 둘(허브 · 인천)의 `.md`·`.html` 에서 링크를 걷어 **다섯 중 하나로 판정**한다.

  살아있음   HTTP 2xx/3xx 이거나, 내부 경로가 실제로 내보내지는 자리에 있다
  날것       200 이지만 **렌더된 지면 대신 마크다운 원본을 배달한다** (`.md` ↔ `.html` 짝)
  push대기   우리 도메인·우리 저장소인데 404 이고, **그 대상이 로컬 작업본에 있으며
             `origin/main` 에는 없다** — 즉 push 하면 살아난다. 근거를 대고 부르는 이름이다
  죽음       4xx/5xx 인데 로컬 근거도 없다
  미확인     네트워크를 안 쳤거나(기본) 타임아웃·연결 실패

**「미확인」이 따로 있는 이유.** 연결이 안 된 것을 「죽음」으로 적으면 그 순간
이 도구가 §8-7이 금지하는 **근거 없는 판정**을 하게 된다. 통과 판정만 근거가 필요한 게 아니다 —
**실패 판정도 근거가 필요하다.** 네트워크 실패는 링크에 대한 관측이 아니라 우리 쪽 사정이다.

**내부 링크와 `날것`은 네트워크 없이 결정론으로 본다.** 그래서 이 검사의 **큰 쪽은 항상 돌아간다** —
비행기 모드에서도 내비게이션 죽은 링크와 원본 덤프 링크는 잡힌다.

  python analysis/check_links.py                 # 내부·날것만. 외부는 「미확인」
  python analysis/check_links.py --net           # 외부까지 실제로 친다
  python analysis/check_links.py --net --strict  # 「죽음」이 있으면 종료코드 1
  python analysis/check_links.py --site 허브
  python analysis/check_links.py --selftest

**기본이 경고인 이유.** `check_status_fresh.py`·`check_review_log.py` 가 같은 자리에서
같은 선택을 했다. 이 검사가 막는 대상은 운영자의 손이고, **차단으로 올릴지는 운영자 판단**이다.
**`날것`은 `--strict` 로도 안 막는다** — 발행본 수정은 §10-8·§2.6이 걸린 운영자 판단이다.

**§4 정지선표에 안 넣는다.** 이 검사가 집행하는 것은 §4가 아니라 **§1.4 1층**이다.
`stopline_table.py` 의 표는 「§4 조항 문면 ↔ 기전」 짝이므로 여기 끼우면 그 표가 거짓이 된다.
그래서 `정지선-집행/명제/한계` 3줄을 **일부러 선언하지 않는다**(`check_review_log.py` 와 같다).

닿지 않는 곳
------------
1. **앵커(`#조각`)는 안 본다.** 200 이 온 페이지 안에 그 조각이 있는지는 확인하지 않는다.
2. **200 은 「그 자료가 그대로 있다」는 뜻이 아니다.** 리다이렉트 종착지도, 내용이 바뀌었는지도
   안 본다. 소스 내용의 동일성은 SHA-256 이 드는 일이지 HTTP 상태코드가 드는 일이 아니다.
3. **`push대기` 는 경로가 로컬에 있다는 것만 본다.** 그 파일의 내용이 링크가 약속한 것인지는
   안 본다. 이름이 맞으면 통과한다 — `check_review_log.py` 한계 ②와 같은 종류다.
4. **공공기관 사이트는 봇을 막는다.** 세션·리퍼러를 요구해 4xx/5xx 를 내는 일이 있고,
   그것은 링크가 죽은 것이 아니다. 그래서 기본이 경고이고, 판정을 사람이 한 번 읽어야 한다.
5. **Liquid 해석은 부분집합이다.** `relative_url`·`absolute_url`·`site.baseurl`·`site.url` 만 푼다.
   **못 푸는 것은 푼 척하지 않고 따로 센다.** `render_preview.py` 와 같은 한계이고,
   같은 이유로 **이것은 Jekyll 이 아니다**(사고 20).
6. **`날것` 판정은 우리 저장소에만 건다.** 남의 사이트가 `.md` 를 어떻게 내보내는지는 모른다.
7. **JavaScript 가 만드는 링크는 안 본다.** 이 사이트에는 없지만, 없다는 것도 적어 둔다.
"""

import argparse
import io
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUB = os.path.join(os.path.dirname(ROOT), "jisangj03-dev.github.io")

# (이름, 폴더, 사이트 URL, baseurl)
SITES = [
    ("허브", HUB, "https://jisangj03-dev.github.io", ""),
    ("인천", ROOT, "https://jisangj03-dev.github.io", "/incheon-port-analysis"),
]

# 지위 5종.
LIVE, RAW, WAIT, DEAD, UNK = "살아있음", "날것", "push대기", "죽음", "미확인"
ORDER = (DEAD, RAW, WAIT, UNK, LIVE)

UA = "Mozilla/5.0 (compatible; vidimus-linkcheck/1.0; +https://jisangj03-dev.github.io)"
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:")

# 문서를 가리키지 않는 <link rel>. 여기 href 는 **탐색 대상이 아니라 힌트**다 —
# `preconnect` 는 오리진만 적으므로 그 URL 을 GET 하면 404 가 정상이다(실측: fonts.googleapis.com).
NON_DOC_REL = ("preconnect", "dns-prefetch", "preload", "prefetch", "modulepreload")


# ── 순수 함수. --selftest 는 이것들을 친다 ──────────────────────────────────

FENCE = re.compile(r"^\s*(```|~~~)", re.M)


INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)*?\1", re.S)


def strip_inline_code(text):
    """인라인 코드(`` `…` ``) 안을 지운다.

    **자기 자신에게 걸렸다**(2026-08-29). `docs/STATUS.md` 가 「발행본은 서로를
    `` `[보고서 #01](report_01_….md)` `` 처럼 가리킨다」고 **설명**하는데, 이 검사기가
    그 예시를 진짜 링크로 세서 「죽음 2건」을 냈다.

    **링크를 인용한 글은 링크가 아니다.** 펜스 블록에 대해 이미 같은 판단을 했으면서
    인라인은 안 벗기고 있었다 — 같은 결함의 절반만 고쳐 뒀던 것이다.
    """
    return INLINE_CODE.sub(lambda m: " " * len(m.group(0)), text)


def strip_fences(text):
    """마크다운 펜스 코드블록을 지운다.

    **이 함수가 없으면 안 된다는 것을 손으로 확인했다.** `verify.md` 의 `curl`·`Ctrl+Shift+R`
    같은 줄에서 URL 조각이 뜯겨 나와, 손으로 친 grep 은 `https://jisangj03-dev.github.io/\\``
    와 `무효화하고` 를 링크로 셌다. 지면에 안 그려지는 것을 링크로 세면 그 판정은 거짓이다.
    """
    out, inside = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            inside = not inside
            continue
        out.append("" if inside else line)
    return "\n".join(out)


# `](...)` — Liquid 를 통째로 먼저 잡는다. `{{ '/x/' | relative_url }}` 안에는 **공백과
# 작은따옴표가 있어서**, 공백에서 끊는 규칙으로는 `{{` 만 뜯긴다(실측: 30건이 그렇게 뜯겼다).
MD_INLINE = re.compile(r"\]\(\s*(\{\{.*?\}\}|<[^>]*>|[^)\s]+)")
MD_REFDEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\{\{.*?\}\}|[^\s>]+)", re.M)

# 여는 따옴표와 **같은** 따옴표로 닫아야 한다. `href="{{ '/x/' | relative_url }}"` 에서
# 아무 따옴표나 받으면 값이 `{{ ` 에서 끊긴다(실측: 이것이 위 30건의 나머지 원인이다).
HTML_ATTR = re.compile(r"""(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
LINK_TAG = re.compile(r"<link\b[^>]*>", re.I)
REL_ATTR = re.compile(r"""\brel\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.I)


def drop_non_doc_links(html):
    """문서를 안 가리키는 `<link rel=preconnect|preload|…>` 태그를 통째로 뺀다."""
    def _sub(m):
        rm = REL_ATTR.search(m.group(0))
        rel = " ".join(x for x in (rm.groups() if rm else ()) if x).lower()
        return "" if any(r in rel.split() for r in NON_DOC_REL) else m.group(0)
    return LINK_TAG.sub(_sub, html)


def extract(text, is_html):
    """한 파일에서 링크 원문을 걷는다. 중복은 남긴다 — 어느 파일에 몇 번인지가 정보다."""
    body = drop_non_doc_links(text) if is_html else strip_inline_code(strip_fences(text))
    raw = ["".join(g for g in t if g) for t in HTML_ATTR.findall(body)]
    if not is_html:
        raw += MD_INLINE.findall(body) + MD_REFDEF.findall(body)
    return [r for r in raw if r]


LIQ = re.compile(
    r"""\{\{-?\s*['"]([^'"]*)['"]\s*\|\s*(relative_url|absolute_url)\s*-?\}\}""")
LIQ_VAR = re.compile(r"""\{\{-?\s*site\.(baseurl|url)\s*-?\}\}""")


def resolve_liquid(raw, site_url, baseurl):
    """Liquid 필터 부분집합을 푼다. 못 푸는 것은 **푼 척하지 않고 None 을 낸다.**"""
    def _filt(m):
        path, filt = m.group(1), m.group(2)
        return (site_url + baseurl + path) if filt == "absolute_url" else (baseurl + path)

    s = LIQ.sub(_filt, raw)
    s = LIQ_VAR.sub(lambda m: baseurl if m.group(1) == "baseurl" else site_url, s)
    if "{{" in s or "{%" in s:
        return None  # 남은 Liquid — 해석 못 했다고 말한다(닿지 않는 곳 5)
    return s


def classify(url):
    """링크를 부류로 가른다: 'ext' | 'int' | 'skip'."""
    if not url or url.startswith("#"):
        return "skip"
    low = url.lower()
    if low.startswith(SKIP_SCHEMES):
        return "skip"
    if low.startswith(("http://", "https://", "//")):
        return "ext"
    return "int"


def norm_path(p):
    """내부 경로를 대조 가능한 꼴로 맞춘다. 앵커·질의는 떼고, 끝 슬래시는 통일한다."""
    if p is None:
        return None
    p = p.split("#", 1)[0].split("?", 1)[0]
    p = urllib.parse.unquote(p)
    if not p:
        return None
    if p.startswith("/"):
        p = os.path.normpath(p).replace("\\", "/")
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p or "/"


FRONT = re.compile(r"\A﻿?---\s*\n(.*?)\n---\s*\n", re.S)
PERMA = re.compile(r"^permalink:\s*['\"]?([^'\"\n]+)", re.M)


def has_front_matter(text):
    return FRONT.match(text) is not None


def permalink_of(rel_path, text):
    """front matter 의 permalink, 없으면 파일 위치에서 Jekyll 기본 규칙으로 낸다."""
    m = FRONT.match(text)
    if m:
        pm = PERMA.search(m.group(1))
        if pm:
            return norm_path("/" + pm.group(1).strip().lstrip("/"))
    rel = rel_path.replace("\\", "/")
    stem = rel.rsplit(".", 1)[0]
    if stem == "index":
        return "/"
    if stem.endswith("/index"):
        return norm_path("/" + stem[: -len("/index")])
    return norm_path("/" + stem)


# ── 사이트 실측 ─────────────────────────────────────────────────────────────

SKIP_DIRS = {".git", "_site", "node_modules", "_og", "__pycache__"}

EXCLUDE_BLOCK = re.compile(r"^exclude:\s*$\n((?:^\s*-\s*.+$\n?)+)", re.M)


def site_exclude(site_dir):
    """`_config.yml` 의 `exclude:` 를 읽는다.

    **인수시험이 이 함수를 요구했다.** `README_운영자안내.md` 를 「날것」으로 셌는데,
    그 파일은 `exclude:` 에 있어 **Jekyll 이 아예 안 내보낸다.** 내보내지 않는 것에
    지위를 매기면 그 지위가 거짓이다 — 없는 지면은 살지도 죽지도 않았다.
    """
    cfg = os.path.join(site_dir, "_config.yml")
    if not os.path.exists(cfg):
        return set()
    try:
        text = io.open(cfg, encoding="utf-8").read()
    except Exception:
        return set()
    m = EXCLUDE_BLOCK.search(text)
    if not m:
        return set()
    out = set()
    for line in m.group(1).splitlines():
        v = line.strip().lstrip("-").strip().strip("'\"")
        if v:
            out.add(v.replace("\\", "/").strip("/"))
    return out


def walk(site_dir):
    ex = site_exclude(site_dir)
    for base, dirs, files in os.walk(site_dir):
        dirs[:] = [d for d in dirs
                   if d not in SKIP_DIRS and not d.startswith(".") and d not in ex]
        for f in files:
            rel = os.path.relpath(os.path.join(base, f), site_dir).replace("\\", "/")
            if rel in ex or any(rel.startswith(e + "/") for e in ex):
                continue
            yield rel


def site_targets(site_dir, baseurl):
    """이 사이트가 실제로 내보내는 경로 집합과, 그중 **원본을 배달하는 경로** 집합.

    모델은 추정이 아니라 실측이다(2026-08-29, 인천 저장소):
      `…/report_02_….html` → 200 · `text/html`      (primer 테마 렌더)
      `…/report_02_….md`   → 200 · `text/markdown`  (**원본 그대로**)
    즉 `.md` 는 지워지지 않고 자기 주소로 같이 남는다. 그래서 두 주소를 다 등록하되,
    `.md` 쪽은 `raw` 로 따로 표시한다 — **살아 있지만 렌더된 지면이 아니다.**
    """
    known, raw = set(), set()
    if not os.path.isdir(site_dir):
        return known, raw
    for rel in walk(site_dir):
        low = rel.lower()
        self_path = norm_path(baseurl + "/" + rel)
        if low.endswith((".md", ".markdown", ".html")) and not rel.startswith("_"):
            try:
                text = io.open(os.path.join(site_dir, rel), encoding="utf-8").read()
            except Exception:
                continue
            p = permalink_of(rel, text)
            if p:
                known.add(norm_path(baseurl + p) if baseurl else p)
            if low.endswith((".md", ".markdown")):
                rendered = norm_path(baseurl + "/" + rel.rsplit(".", 1)[0] + ".html")
                known.add(rendered)
                known.add(self_path)
                if not has_front_matter(text):
                    # front matter 가 없으면 Jekyll 은 이 파일을 **그대로 복사**한다.
                    # 렌더본이 따로 있는데 이 주소를 가리키면 독자는 소스를 받는다.
                    raw.add(self_path)
            else:
                known.add(self_path)
        else:
            known.add(self_path)
    known.add(norm_path(baseurl) or "/")
    return known, raw


def git(repo, args):
    try:
        return subprocess.run(
            ["git"] + args, cwd=repo, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
        )
    except Exception:
        return None


def pushed(repo, rel_path):
    """`origin/main` 에 이 경로가 이미 있는가. 원격이 없으면 **전부 미push** 다."""
    r = git(repo, ["rev-parse", "--verify", "--quiet", "origin/main"])
    if r is None or not r.stdout.strip():
        return False
    r = git(repo, ["cat-file", "-e", "origin/main:" + rel_path])
    return bool(r) and r.returncode == 0


def our_site_of(url):
    """우리 도메인 URL을 (저장소, 사이트경로) 로 되돌린다. 우리 것이 아니면 None."""
    u = urllib.parse.urlsplit(url)
    if u.netloc.lower() != "jisangj03-dev.github.io":
        return None
    path = urllib.parse.unquote(u.path)
    if path.startswith("/incheon-port-analysis"):
        return (ROOT, norm_path(path))
    return (HUB, norm_path(path))


def local_evidence(url):
    """우리 것인 URL 을 로컬 경로로 되돌린다. 못 되돌리면 None.

    되돌린 뒤 **로컬에 있고 origin/main 에는 없을 때만** `push대기` 라 부른다.
    「파일이 있다」만으로 부르면 이미 push 된 진짜 죽은 링크까지 삼킨다.
    """
    u = urllib.parse.urlsplit(url)
    path = urllib.parse.unquote(u.path)
    host = u.netloc.lower()
    cands = []
    if host == "jisangj03-dev.github.io":
        if path.startswith("/incheon-port-analysis/"):
            rel, repo = path[len("/incheon-port-analysis/"):], ROOT
        elif path.rstrip("/") == "/incheon-port-analysis":
            rel, repo = "index.md", ROOT
        else:
            rel, repo = path.lstrip("/"), HUB
        if not rel or rel.endswith("/"):
            rel += "index.md"  # 루트·디렉터리 주소는 그 자리의 index 가 근거다
        if rel.endswith(".html"):
            cands += [(repo, rel[:-5] + ".md"), (repo, rel)]
        else:
            cands.append((repo, rel))
    elif host == "github.com":
        m = re.match(r"^/jisangj03-dev/([^/]+)/(?:blob|tree|raw)/[^/]+/(.*)$", path)
        if m:
            repo = ROOT if m.group(1) == "incheon-port-analysis" else HUB
            cands.append((repo, m.group(2)))
    for repo, rel in cands:
        if rel and os.path.exists(os.path.join(repo, rel.replace("/", os.sep))):
            if not pushed(repo, rel):
                return (repo, rel)
    return None


def encode_url(url):
    """비ASCII 가 든 URL 을 퍼센트 인코딩한다.

    **인수시험이 아니라 실물이 이 함수를 요구했다.** 인천 `about.md` 의
    `…/blob/main/docs/검수기록.md` 두 건이 `UnicodeEncodeError` 로 관측되지 않았다.
    「미확인」이 그것을 죽음으로 안 부른 것은 옳았지만, **못 보는 것을 계속 못 보게
    두는 것은 검사가 아니다** — 사고 26이 말한 「부재를 통과로 읽는 것」의 사촌이다.
    """
    u = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((
        u.scheme,
        u.netloc.encode("idna").decode("ascii") if any(ord(c) > 127 for c in u.netloc)
        else u.netloc,
        urllib.parse.quote(u.path, safe="/%:@!$&'()*+,;=~-._"),
        urllib.parse.quote(u.query, safe="/?=&%:@!$'()*+,;~-._"),
        "",  # 조각은 서버로 안 간다
    ))


def http_status(url, timeout):
    """(코드, 비고). 코드가 None 이면 관측하지 못한 것이다 — 죽었다는 뜻이 아니다."""
    req = urllib.request.Request(encode_url(url),
                                 headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, type(e).__name__


def verdict(code, url, net_ran, is_raw=False):
    """코드·로컬 근거·원본 여부에서 지위를 정한다. **판정 전부가 이 함수 안에 있다.**

    `날것` 이 200 을 이긴다. 200 은 「무언가가 왔다」이지 「지면이 왔다」가 아니다.
    """
    if is_raw:
        return RAW
    if not net_ran or code is None:
        return UNK
    if 200 <= code < 400:
        return LIVE
    if local_evidence(url):
        return WAIT
    return DEAD


# ── 수집 ────────────────────────────────────────────────────────────────────

def collect(site_dir, site_url, baseurl):
    """(파일, 원문, 해석된 링크, 부류) 목록."""
    rows = []
    if not os.path.isdir(site_dir):
        return rows
    for rel in sorted(walk(site_dir)):
        low = rel.lower()
        if not low.endswith((".md", ".markdown", ".html")):
            continue
        if os.path.basename(rel).startswith("README"):
            continue
        try:
            text = io.open(os.path.join(site_dir, rel), encoding="utf-8").read()
        except Exception:
            continue
        for raw in extract(text, low.endswith(".html")):
            resolved = resolve_liquid(raw, site_url, baseurl)
            if resolved is None:
                rows.append((rel, raw, None, "liquid"))
                continue
            rows.append((rel, raw, resolved, classify(resolved)))
    return rows


def resolve_internal(rel_file, url, baseurl):
    """내부 링크를 사이트 경로로 푼다. 상대경로는 그 파일 위치를 기준으로 삼는다."""
    t = norm_path(url)
    if t is None:
        return None
    if t.startswith("/"):
        return t
    base = os.path.dirname(rel_file).replace("\\", "/")
    return norm_path("/".join(x for x in (baseurl, base, t) if x) or "/")


# ── 인수시험 (사고 26·34 — 발화하는가, 그리고 안 해야 할 때 조용한가) ──────

MD_FIXTURE = """---
layout: page
permalink: /data/
---
[살아있는 것](https://example.org/a) 과 [내부]({{ '/verify/' | relative_url }}).

```
curl -sS "https://archive.org/wayback/available?url=x"
**`Ctrl+Shift+R`로 캐시를 무효화한다**
```

[표](/reports/) · [앵커](#조각) · [메일](mailto:a@b.c)

[ref]: https://example.org/refdef
"""

HTML_FIXTURE = (
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="/assets/css/vidimus.css">'
    """<a href="{{ '/terminals/' | relative_url }}">터미널</a>"""
    '<img src="/assets/og.png">'
)


def selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 펜스 코드블록을 링크로 안 센다 (손으로 확인한 오탐) ──")
    links = extract(MD_FIXTURE, False)
    check("펜스 안 URL 이 안 들어온다", any("archive.org" in x for x in links), False)
    check("펜스 안 한글이 안 들어온다", any("무효화" in x for x in links), False)
    check("펜스 밖 링크는 들어온다", "https://example.org/a" in links, True)
    check("참조 정의도 들어온다", "https://example.org/refdef" in links, True)

    print("── 인수시험: 인라인 코드는 링크가 아니다 (자기 자신에게 걸린 자리) ──")
    quoted = "발행본은 서로를 `[보고서 #01](report_01_x.md)` 처럼 가리킨다."
    check("인용된 링크를 안 센다", extract(quoted, False), [])
    check("인용 밖의 링크는 센다",
          extract("`코드` 와 [진짜](/real/) 링크", False), ["/real/"])
    check("이중 백틱도 닫는다",
          extract("``a `b` c`` 와 [진짜](/x/)", False), ["/x/"])
    check("닫히지 않은 백틱이 뒤를 다 먹지 않는다",
          extract("` 안 닫힘 그리고 [진짜](/y/)", False), ["/y/"])

    print("── 인수시험: 따옴표·Liquid 를 안 끊는다 (실측 30건의 원인) ──")
    hl = extract(HTML_FIXTURE, True)
    check("preconnect href 는 링크가 아니다",
          any("fonts.gstatic" in x for x in hl), False)
    check("stylesheet 는 링크다", "/assets/css/vidimus.css" in hl, True)
    check("작은따옴표 낀 Liquid 가 안 끊긴다",
          "{{ '/terminals/' | relative_url }}" in hl, True)
    check("img src 도 들어온다", "/assets/og.png" in hl, True)
    check("마크다운의 Liquid 도 안 끊긴다",
          "{{ '/verify/' | relative_url }}" in links, True)

    print("── 인수시험: Liquid 부분집합 ──")
    check("relative_url", resolve_liquid("{{ '/verify/' | relative_url }}", "https://s", "/b"),
          "/b/verify/")
    check("absolute_url", resolve_liquid("{{ '/assets/og.png' | absolute_url }}", "https://s", ""),
          "https://s/assets/og.png")
    check("site.baseurl", resolve_liquid("{{ site.baseurl }}/x", "https://s", "/b"), "/b/x")
    check("못 푸는 것은 None 이다 (푼 척하지 않는다)",
          resolve_liquid("{{ page.foo }}", "https://s", ""), None)

    print("── 인수시험: 부류·경로 ──")
    check("외부", classify("https://a/b"), "ext")
    check("내부", classify("/data/"), "int")
    check("앵커는 건너뛴다", classify("#조각"), "skip")
    check("mailto 는 건너뛴다", classify("mailto:a@b"), "skip")
    check("끝 슬래시 통일", norm_path("/data/"), "/data")
    check("질의·앵커를 뗀다", norm_path("/data/?x=1#y"), "/data")
    check("상대경로를 파일 위치로 푼다",
          resolve_internal("reports/report_01.md", "report_02.md", "/incheon-port-analysis"),
          "/incheon-port-analysis/reports/report_02.md")
    check("`..` 를 푼다",
          resolve_internal("reports/report_01.md", "../docs/x.md", "/incheon-port-analysis"),
          "/incheon-port-analysis/docs/x.md")

    print("── 인수시험: permalink · front matter ──")
    check("front matter 우선", permalink_of("data/index.md", MD_FIXTURE), "/data")
    check("index.md → /", permalink_of("index.md", "본문"), "/")
    check("x/index.md → /x", permalink_of("terminals/index.md", "본문"), "/terminals")
    check("about.md → /about", permalink_of("about.md", "본문"), "/about")
    check("front matter 있음", has_front_matter(MD_FIXTURE), True)
    check("front matter 없음", has_front_matter("# 제목\n"), False)

    print("── 인수시험: 판정 (양방향 — 이게 없으면 「항상 죽음」도 통과한다) ──")
    check("2xx → 살아있음", verdict(200, "https://example.org/", True), LIVE)
    check("3xx → 살아있음", verdict(301, "https://example.org/", True), LIVE)
    check("남의 404 → 죽음", verdict(404, "https://example.org/none", True), DEAD)
    check("네트워크 실패 → 미확인 (죽음이 아니다)",
          verdict(None, "https://example.org/none", True), UNK)
    check("--net 안 켜면 미확인", verdict(None, "https://example.org/", False), UNK)
    check("날것은 200 을 이긴다 (여기가 거짓 PASS 자리다)",
          verdict(200, "https://jisangj03-dev.github.io/x.md", True, is_raw=True), RAW)

    print("── 인수시험: URL 인코딩 (실물이 요구한 함수) ──")
    check("한글 경로를 퍼센트 인코딩한다",
          encode_url("https://github.com/x/blob/main/docs/검수기록.md"),
          "https://github.com/x/blob/main/docs/%EA%B2%80%EC%88%98%EA%B8%B0%EB%A1%9D.md")
    check("이미 인코딩된 것을 두 번 안 한다",
          encode_url("https://a/b/%EA%B2%80.md"), "https://a/b/%EA%B2%80.md")
    check("조각은 서버로 안 보낸다", encode_url("https://a/b#c"), "https://a/b")
    check("평범한 URL 은 그대로 둔다", encode_url("https://a/b?x=1"), "https://a/b?x=1")

    print("── 인수시험: push대기 (실물에 걸어 확인한다) ──")
    check("우리 저장소 · 로컬에 있음 · 미push → 근거를 찾는다",
          local_evidence("https://github.com/jisangj03-dev/incheon-port-analysis/"
                         "blob/main/analysis/check_links.py") is not None, True)
    check("없는 파일은 근거가 없다",
          local_evidence("https://github.com/jisangj03-dev/incheon-port-analysis/"
                         "blob/main/analysis/없는파일.py"), None)
    check("남의 도메인은 근거를 안 만든다",
          local_evidence("https://example.org/analysis/check_links.py"), None)
    check("이미 push 된 것은 push대기가 아니다",
          local_evidence("https://github.com/jisangj03-dev/incheon-port-analysis/"
                         "blob/main/analysis/lint_publish.py"), None)
    check("허브 루트는 index.md 가 근거다",
          local_evidence("https://jisangj03-dev.github.io/") is not None, True)

    print("── 인수시험: 실물 사이트 ──")
    hub_known, hub_raw = site_targets(HUB, "")
    inc_known, inc_raw = site_targets(ROOT, "/incheon-port-analysis")
    check("허브가 제자리에 있다", os.path.isdir(HUB), True)
    check("허브 permalink 에 /data 가 있다", "/data" in hub_known, True)
    check("허브 permalink 에 /terminals 가 있다", "/terminals" in hub_known, True)
    check("허브 정적 파일에 og.png 가 있다", "/assets/og.png" in hub_known, True)
    check("없는 지면은 없다고 나온다", "/checks" in hub_known, False)
    check("허브 지면은 날것이 아니다 (front matter 가 있다)", hub_raw, set())
    check("_config.yml 의 exclude 를 읽는다",
          "README_운영자안내.md" in site_exclude(HUB), True)
    check("exclude 된 것은 내보내는 자리에 없다",
          "/README_운영자안내.md" in hub_known, False)
    check("인천 발행본 .html 은 known 이다",
          "/incheon-port-analysis/reports/report_02_공컨테이너_비율.html" in inc_known, True)
    check("인천 발행본 .md 는 날것이다 (실측: 200 · text/markdown)",
          "/incheon-port-analysis/reports/report_02_공컨테이너_비율.md" in inc_raw, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="허브·인천의 링크를 걷어 살아있음/날것/push대기/죽음/미확인으로 판정한다 (§1.4 1층).")
    ap.add_argument("--net", action="store_true", help="외부 링크를 실제로 친다")
    ap.add_argument("--strict", action="store_true", help="「죽음」이 있으면 종료코드 1")
    ap.add_argument("--site", default=None, help="허브 | 인천")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    sites = [s for s in SITES if a.site is None or s[0] == a.site]
    if not sites:
        print("그런 사이트가 없다: %s" % a.site, file=sys.stderr)
        return 2

    tally = {k: 0 for k in ORDER}
    problems, liquid_unresolved, raw_by_file = [], [], {}
    seen_ext = {}

    for name, sdir, surl, base in sites:
        if not os.path.isdir(sdir):
            print("[없음] %s — %s" % (name, sdir))
            continue
        known, raws = site_targets(sdir, base)
        n_int = n_ext = 0

        print("\n== %s ==  %s" % (name, sdir))
        for rel, raw, url, kind in collect(sdir, surl, base):
            if kind == "skip":
                continue
            if kind == "liquid":
                liquid_unresolved.append((name, rel, raw))
                continue

            if kind == "int":
                n_int += 1
                target = resolve_internal(rel, url, base)
                if target is None:
                    continue
                if target in raws:
                    v = RAW
                elif target in known:
                    v = LIVE
                else:
                    v = DEAD
                tally[v] += 1
                if v == RAW:
                    raw_by_file.setdefault((name, rel), 0)
                    raw_by_file[(name, rel)] += 1
                elif v == DEAD:
                    problems.append((v, name, rel, url, "내부 — 이 경로를 내보내는 지면이 없다"))
                continue

            n_ext += 1
            ours = our_site_of(url)
            is_raw = bool(ours and ours[1] in
                          (raws if ours[0] == sdir else site_targets(ours[0],
                           "/incheon-port-analysis" if ours[0] == ROOT else "")[1]))
            key = (url, is_raw)
            if key in seen_ext:
                v, code = seen_ext[key]
            else:
                code = http_status(url, a.timeout)[0] if a.net else None
                v = verdict(code, url, a.net, is_raw)
                seen_ext[key] = (v, code)
            tally[v] += 1
            if v == RAW:
                raw_by_file.setdefault((name, rel), 0)
                raw_by_file[(name, rel)] += 1
            elif v in (WAIT, DEAD):
                ev = local_evidence(url)
                why = ("로컬에 있고 origin/main 에 없다 → push 하면 산다: %s"
                       % os.path.relpath(os.path.join(*ev),
                                         os.path.dirname(ROOT)).replace("\\", "/")
                       ) if ev else "HTTP %s · 로컬 근거 없음" % code
                problems.append((v, name, rel, url, why))

        print("  내부 %d건 · 외부 %d건" % (n_int, n_ext))

    print("\n== 판정 ==")
    for k in ORDER:
        print("  %-8s %d" % (k, tally[k]))
    if not a.net:
        print("  (외부는 안 쳤다. `--net` 을 붙여야 살았는지 알 수 있다 — 사고 20)")

    if liquid_unresolved:
        print("\n== Liquid 를 못 풀었다 (푼 척하지 않는다 · 닿지 않는 곳 5) ==")
        for s, rel, raw in liquid_unresolved:
            print("  %s  %s  %s" % (s, rel, raw))

    if raw_by_file:
        print("\n== 날것 — 200 이지만 렌더된 지면 대신 마크다운 원본을 배달한다 ==")
        print("  독자가 받는 것: 소스 덤프. 차트는 글자로, 표는 파이프 줄로, 표기 블록도 안 그려진다.")
        for (s, rel), n in sorted(raw_by_file.items()):
            print("  %2d건  %s  %s" % (n, s, rel))
        print("  **발행본 수정은 §10-8·§2.6 이 걸린 운영자 판단이라 --strict 로도 안 막는다.**")

    if problems:
        print("\n== 손봐야 하는 것 ==")
        for v, s, rel, url, why in sorted(problems, key=lambda r: (ORDER.index(r[0]), r[1], r[2])):
            print("  [%s] %s  %s" % (v, s, rel))
            print("        %s" % url)
            print("        %s" % why)

    dead = tally[DEAD]
    if dead and a.strict:
        print("\n죽은 링크 %d건. --strict 라 여기서 멈춘다." % dead, file=sys.stderr)
        return 1
    if dead:
        print("\n죽은 링크 %d건. 경고만 한다 — 막으려면 --strict." % dead)
    elif tally[WAIT]:
        print("\n죽은 링크 0건. push대기 %d건은 순서 문제다 — 인천을 먼저 push 하면 산다."
              % tally[WAIT])
    else:
        print("\n죽은 링크 0건.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

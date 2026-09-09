# -*- coding: utf-8 -*-
"""채널 문안 — **재료를 뽑고, 나가기 전에 검사한다.**

왜 있는가
---------
채널 헤드라인은 **결론 자리**다(지침 §3). 그런데 보고서와 달리 채널 문안은
**절 구조가 없어** 발행 린터가 겨눠도 `[구조]` WARN 만 내고 값을 하나도 안 봤다.
`lint_publish.py --channel` 이 그 자리를 메웠지만 그것이 보는 것은 **수치의 지위**뿐이다.

**게시가 터지는 자리는 그 밖에 셋 더 있다.**
① 링크가 죽어 있다(인천 push 전에 올리면 404 · 사고 49 의 이웃)
② 링크 카드가 안 뜬다 — OG 태그가 없거나 이미지가 죽었다
③ 채널 형식을 어겼다 — GeekNews 는 **두 시간 뒤 못 지운다**

**그리고 되돌릴 수 없는 채널에서는 이 검사가 유일한 방어다.**

  python analysis/channel_post.py --source reports/report_09_*.md   # 문안 재료
  python analysis/channel_post.py --check <문안파일> [--net]         # 검사
  python analysis/channel_post.py --clip <문안파일>                  # 클립보드에 넣고 정본 해시
  python analysis/channel_post.py --verify <문안파일> --got <해시>    # 붙여넣은 것과 파일을 맞댄다
  python analysis/channel_post.py --check-all [--net]                # 본부 문안 전부
  python analysis/channel_post.py --selftest

문안 파일 형식
--------------
    ---
    id: li-01
    channel: linkedin
    title: (제목이 있는 채널만)
    target: https://sounding.higgsfield.app     ← 카드가 될 주소
    report: reports/report_09_....md            ← 선택. 재료 출처
    ---
    여기부터 끝까지가 **붙여넣을 본문 그대로다.**

**밑줄로 시작하는 파일(`_*.md`)은 문안이 아니다** — 근거표·메모 자리이고 검사에서 건너뛴다.

닿지 않는 곳
------------
· **문안이 좋은지는 안 본다.** 형식 · 수치 지위 · 링크 · 카드만 본다.
· `--net` 없이는 **링크를 안 친다** — 소스 판정은 사이트에 대한 진술이 아니다(사고 91).
· **OG 카드는 태그가 있는지와 이미지가 200인지만 본다.** 채널이 실제로 어떻게 그리는지는
  **사람이 미리보기로 본다.** 「속성이 붙었다」는 「그렇게 보인다」가 아니다(사고 73).
· 수치 대조는 `lint_publish.py --channel` 에 넘긴다 — 대장을 두 번 읽지 않는다.
· **깨진 음절 검사는 겹받침 목록에 기댄다.** 「그럵」은 정상 유니코드라 인코딩으로는 못 잡고,
  낱말인지 아닌지는 사전이 있어야 안다. **목록 밖 겹받침을 의심할 뿐 판정하지 않는다** —
  다른 자리가 깨지면(받침 없는 음절끼리 바뀌면) **이 검사는 침묵한다.**
  **본체 방어는 `--clip` 과 `--verify` 다** — 전사를 없애고, 대조를 파일과 한다.
"""

import argparse
import glob
import io
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import channels as CH  # noqa: E402

HQ = os.path.join(os.path.expanduser("~"), "OneDrive", "문서", "본부")
DRAFTS = os.path.join(HQ, "채널문안")

FAIL, WARN, INFO = CH.FAIL, CH.WARN, CH.INFO
HEAD = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def parse(path):
    """머리말 + 본문. **본문은 손대지 않는다** — 붙여넣을 것 그대로여야 한다."""
    raw = io.open(path, encoding="utf-8").read().replace("\r\n", "\n")
    m = HEAD.match(raw)
    if not m:
        raise ValueError("머리말(--- ... ---)이 없다: %s" % path)
    meta = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, raw[m.end():]


# ── 재료 뽑기 ───────────────────────────────────────────────────────────────

def facts_rows():
    """FACTS 대장의 (값, 창, 지위) — 문안에 쓸 수 있는 것만."""
    p = os.path.join(ROOT, "docs", "FACTS.md")
    rows = []
    if not os.path.exists(p):
        return rows
    for line in io.open(p, encoding="utf-8"):
        if not line.startswith("|"):
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) >= 4 and c[2] in ("검증", "관측", "참고", "미확인"):
            rows.append((c[0], c[1], c[2], c[3]))
    return rows


def one_liner(report):
    """그 편의 「한 줄 결론」. 문안이 되풀이하지 않게 **보여만 준다.**"""
    if not report or not os.path.exists(os.path.join(ROOT, report)):
        return None
    for line in io.open(os.path.join(ROOT, report), encoding="utf-8"):
        if "한 줄 결론" in line:
            return re.sub(r"\*\*|^-\s*", "", line).split("**", 1)[-1].strip(" :*").strip()
    return None


def source(report):
    print("== 문안 재료 ==")
    print("**여기 있는 값만 결론 자리에 쓴다**(지침 §3). 창을 값과 같이 옮긴다(사고 22).\n")
    if report:
        matches = sorted(glob.glob(os.path.join(ROOT, report)))
        rel = os.path.relpath(matches[0], ROOT).replace("\\", "/") if matches else report
        print("── 대상 편: %s" % rel)
        ol = one_liner(rel)
        if ol:
            print("   한 줄 결론: %s" % ol)
            print("   **문안은 이것을 되풀이하지 않는다** — 링크 카드 설명이 이미 나른다.")
        print()
    rows = facts_rows()
    ok = [r for r in rows if r[2] in ("검증", "관측")]
    no = [r for r in rows if r[2] not in ("검증", "관측")]
    print("── 결론 자리에 쓸 수 있는 값 %d개 (지위 검증·관측)" % len(ok))
    for v, w, s, src in ok:
        print("   %-14s %-46s %s  %s" % (v, w[:46], s, src[:34]))
    print("\n── 쓰면 안 되는 값 %d개 (지위 참고·미확인) — 본문·표에서만" % len(no))
    for v, w, s, _ in no[:12]:
        print("   %-14s %-46s %s" % (v, w[:46], s))
    print("\n── 채널 규칙은 `python analysis/channels.py --list`")
    return 0


# ── 검사 ────────────────────────────────────────────────────────────────────

def http(url, timeout=15.0, want_body=False):
    """(상태, 본문). **못 친 것을 통과로 세지 않는다** — 실패는 None 이다."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; sounding-channel-check/1.0)",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(200000).decode("utf-8", "replace") if want_body else ""
            return r.getcode(), body
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return None, ""


def check_links(body, target, net, channel=None):
    """링크 생존과 카드 순서. **카드가 없는 채널에서는 순서를 안 본다** — 메일·GeekNews 가 그렇다."""
    out = []
    us = CH.urls(body)
    has_card = bool(CH.CHANNELS.get((channel or "").lower(), {}).get("링크카드"))
    if target and target not in us:
        out.append((WARN, "카드가 될 주소(`target`)가 본문에 없다: %s" % target))
    elif has_card and target and us and len(us) > 1 and us[-1] != target:
        # 카드는 **마지막으로 입력된** URL 에 붙는다(2026-09-10 확정 · `channels.py` 메모).
        # 우리는 전문을 한 번에 붙여넣으므로 **입력 순서 = 본문 순서**다 — 끝에 있어야 한다.
        out.append((WARN, "URL %d개 중 `target`(%s)이 **마지막이 아니다** — 한 번에 붙여넣으면 "
                          "카드는 마지막 URL(%s)에 붙는다. 순서를 바꾸거나 target 을 고친다"
                          % (len(us), target, us[-1])))
    if not net:
        out.append((INFO, "링크를 안 쳤다 — `--net` 을 줘야 친다. **소스 판정은 사이트에 대한 진술이 아니다**"))
        return out
    for u in dict.fromkeys(us):
        code, _ = http(u)
        if code is None:
            out.append((WARN, "[미확인] 못 쳤다(봇 차단과 죽음을 못 가른다): %s" % u))
        elif code >= 400:
            out.append((FAIL, "죽은 링크 %d: %s" % (code, u)))
        else:
            out.append((INFO, "산다 %d: %s" % (code, u)))
    return out


OG = re.compile(r"<meta[^>]+property=[\"']og:(title|description|image)[\"'][^>]*content=[\"']([^\"']*)[\"']", re.I)
OG2 = re.compile(r"<meta[^>]+content=[\"']([^\"']*)[\"'][^>]+property=[\"']og:(title|description|image)[\"']", re.I)


def check_card(target, net, channel=None):
    """링크 카드 — **태그가 있는가와 이미지가 200인가.** 어떻게 그려지는지는 사람이 본다.

    **카드가 없는 채널에서는 안 본다** — 메일에는 링크 미리보기가 없고, 있어도 받는 쪽 프로그램이
    정한다. 없는 것을 검사하면 경고만 늘고 **경고가 늘면 무시당한다**(§3-5).
    """
    out = []
    if channel and not CH.CHANNELS.get(channel.lower(), {}).get("링크카드"):
        out.append((INFO, "이 채널에는 링크 카드가 없다 — 카드 검사를 안 한다"))
        return out
    if not target:
        out.append((WARN, "`target` 이 없다 — 어느 주소가 카드가 되는지 안 적혀 있다"))
        return out
    if not net:
        out.append((INFO, "카드를 안 봤다 — `--net` 이 필요하다"))
        return out
    code, html = http(target, want_body=True)
    if code is None or code >= 400:
        out.append((FAIL, "카드 대상 주소가 안 열린다(%s): %s" % (code, target)))
        return out
    tags = {}
    for k, v in OG.findall(html):
        tags[k.lower()] = v
    for v, k in OG2.findall(html):
        tags.setdefault(k.lower(), v)
    for k in ("title", "description", "image"):
        if tags.get(k):
            out.append((INFO, "og:%s — %s" % (k, tags[k][:80])))
        else:
            out.append((WARN, "og:%s 가 없다 — 카드가 비거나 안 뜬다" % k))
    img = tags.get("image")
    if img:
        if img.startswith("/"):
            m = re.match(r"(https?://[^/]+)", target)
            img = (m.group(1) if m else "") + img
        icode, _ = http(img)
        if icode is None:
            out.append((WARN, "[미확인] og:image 를 못 쳤다: %s" % img))
        elif icode >= 400:
            out.append((FAIL, "og:image 가 죽었다 %d: %s" % (icode, img)))
        else:
            out.append((INFO, "og:image 산다 %d" % icode))
    out.append((INFO, "**태그가 있다는 것이 카드가 그렇게 보인다는 뜻은 아니다** — 붙여넣고 미리보기를 눈으로 본다(사고 73)"))
    return out


def check_numbers(path):
    """수치는 발행 린터에 넘긴다 — 대장을 두 번 읽지 않는다."""
    lint = os.path.join(HERE, "lint_publish.py")
    if not os.path.exists(lint):
        return [(WARN, "lint_publish.py 가 없다 — 수치를 안 봤다")]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, lint, path, "--channel"], cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=90, env=env)
    except Exception as e:
        return [(WARN, "[미확인] 린터를 못 돌렸다: %s" % e)]
    last = [l for l in (p.stdout or "").splitlines() if l.strip()]
    tail = last[-1][:100] if last else ""
    if p.returncode == 0:
        return [(INFO, "린터(수치 지위·인과) 통과 — %s" % tail)]
    hits = [l.strip() for l in (p.stdout or "").splitlines() if "FAIL" in l][:6]
    return [(FAIL, "린터 FAIL — %s" % tail)] + [(FAIL, "  " + h[:110]) for h in hits]


# ── 붙여넣기: 전사를 없앤다 ─────────────────────────────────────────────────
#
# **2026-09-10 사고.** 문안을 base64 로 만들어 브라우저 스크립트에 **손으로 옮겨 적고**
# 거기서 디코드해 넣었다. 옮겨 적을 때 base64 한 글자가 틀렸고(위치 1614 · `U`↔`A`),
# 6비트가 바뀌어 「그런」이 **「그럵」**으로 나갔다.
#
# **그런데 대조는 통과했다.** 브라우저 내용을 **같은 깨진 문자열에서 디코드한 변수**와
# 맞댔기 때문이다 — 사본을 사본과 댄 것이고, **형해화된 대조와 성공한 대조는 출력이 똑같다**
# (§3-6 · 사고 25). 「불일치 0」이 「같다」가 아니라 **「같은 것을 두 번 봤다」**였다.
#
# 처분은 둘이다.
#   ① **전사 경로를 없앤다** — 파일에서 OS 클립보드로 바로 넣고 브라우저는 Ctrl+V 로 받는다.
#      본문이 사람(또는 이 세션)의 손을 한 번도 안 거친다.
#   ② **대조를 독립시킨다** — 파일에서 낸 해시와 브라우저에서 낸 해시를 맞댄다.
#      해시를 잘못 옮겨 적으면 **불일치가 되지 통과가 되지 않는다**(닫히는 쪽으로 실패한다).

WS = re.compile(r"[\s ​‌﻿]+")


def norm_for_hash(text):
    """양쪽이 **똑같이** 지우는 공백. 편집기는 문단을 제 방식대로 나누므로 공백은 빼고 잰다."""
    return WS.sub("", text or "")


def body_hash(text):
    import hashlib
    return hashlib.sha256(norm_for_hash(text).encode("utf-8")).hexdigest()


def clip(path):
    """본문을 OS 클립보드에 넣고 **읽어서 확인한 뒤** 해시를 낸다. 브라우저는 Ctrl+V 로 받는다."""
    meta, body = parse(path)
    body = body.rstrip("\n")
    try:
        subprocess.run(["clip.exe"], input=body.encode("utf-16-le"), check=True)
    except Exception as e:
        print("[불성립] 클립보드에 못 넣었다: %s" % e)
        print("  이 경로가 없으면 **전사로 돌아가지 말고 멈춘다** — 전사가 2026-09-10 사고의 원인이다.")
        return 2
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-Clipboard -Raw"],
                           stdout=subprocess.PIPE, timeout=30)
        back = r.stdout.decode("utf-8", "replace").replace("\r\n", "\n").rstrip("\n")
    except Exception as e:
        print("[미확인] 클립보드를 되읽지 못했다: %s — **넣었다고 치지 않는다**" % e)
        return 2
    if norm_for_hash(back) != norm_for_hash(body):
        print("**클립보드 왕복이 안 맞는다 — 쓰지 않는다.**")
        for i, (a, b) in enumerate(zip(norm_for_hash(back), norm_for_hash(body))):
            if a != b:
                print("  첫 불일치 %d: 클립보드 %r · 파일 %r" % (i, a, b))
                break
        return 2
    h = body_hash(body)
    print("== 클립보드에 넣었다 — %s ==" % os.path.basename(path))
    if meta.get("title"):
        print("  제목: %s" % meta["title"])
    print("  본문 %d자 · 공백 뺀 %d자 · 줄 %d"
          % (len(body), len(norm_for_hash(body)), body.count("\n") + 1))
    print("  왕복 확인: 넣은 것과 되읽은 것이 같다")
    print("\n  **정본 해시(공백 제외 SHA-256 앞 16)**: %s" % h[:16])
    print("  브라우저에서 붙여넣은 뒤 같은 값이 나오는지 본다:")
    print("    python analysis/channel_post.py --verify %s --got <브라우저해시>"
          % os.path.relpath(path, ROOT).replace("\\", "/"))
    print("\n  **base64 로 옮겨 적지 않는다.** 그것이 2026-09-10 에 「그런」을 「그럵」으로 만들었다.")
    return 0


def verify(path, got):
    """브라우저가 낸 해시를 **파일**과 맞댄다. 사본이 아니라 정본과 대는 것이 요점이다."""
    _, body = parse(path)
    want = body_hash(body.rstrip("\n"))[:16]
    got = (got or "").strip().lower()[:16]
    ok = got == want
    print("정본(파일) %s" % want)
    print("브라우저    %s" % got)
    print("**일치**" if ok else "**불일치 — 붙여넣은 것이 파일과 다르다. 지우고 다시 넣는다.**")
    return 0 if ok else 1


# ── 깨진 음절 ───────────────────────────────────────────────────────────────
#
# 「그럵」은 **정상적인 한글 음절**이다. 유니코드로는 아무 문제가 없고, 낱말이 아닐 뿐이다.
# 그래서 인코딩 검사로는 못 잡는다. 다만 **비트가 틀어지면 겹받침이 잘 생긴다** —
# 「런」(ㄴ)이 「럵」(ㄼ)이 된 것이 그것이다. 겹받침을 쓰는 낱말은 닫힌 작은 집합이라
# **목록 밖 겹받침은 의심**할 수 있다. 실측: 우리 문안 전체의 겹받침 음절은 네 종뿐이다.

JONG = "  ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ",
        "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ",
        "ㅌ", "ㅍ", "ㅎ"]
RARE_JONG = set("ㄳㄵㄶㄺㄻㄼㄽㄾㄿㅀㅄ")
# 겹받침을 쓰는 한국어 음절 — 닫힌 집합이다. 여기 없는 겹받침 음절은 **의심**이지 오류가 아니다.
OK_SYLL = set(
    "몫삯넋"          # ㄳ
    "앉얹"            # ㄵ
    "많않끊괜찮짢뚫"   # ㄶ (찮·짢 포함)
    "읽닭흙맑밝늙굵붉긁낡묽얽칡삵읽"   # ㄺ
    "젊삶닮앎굶옮곪"   # ㄻ
    "밟넓짧얇떫엷섧"   # ㄼ
    "곬"              # ㄽ
    "핥훑"            # ㄾ
    "읊"              # ㄿ
    "싫앓옳잃끓곯닳뚫" # ㅀ
    "값없엾"          # ㅄ
)


def check_hangul(body):
    """겹받침이 목록 밖이면 **의심**한다. 깨진 음절은 정상 유니코드라 이 길밖에 없다."""
    out = []
    seen = {}
    for i, ch in enumerate(body or ""):
        o = ord(ch)
        if not (0xAC00 <= o <= 0xD7A3):
            continue
        j = JONG[(o - 0xAC00) % 28]
        if j in RARE_JONG and ch not in OK_SYLL:
            seen.setdefault(ch, body[max(0, i - 12):i + 8].replace("\n", " "))
    for ch, ctx in seen.items():
        out.append((WARN, "겹받침이 낯설다 — 「%s」 (…%s…). **깨진 음절일 수 있다.** "
                          "맞으면 `OK_SYLL` 에 넣는다" % (ch, ctx)))
    return out


def check_one(path, net=False):
    meta, body = parse(path)
    ch = meta.get("channel", "")
    name = os.path.basename(path)
    print("\n── %s  [%s · %s]" % (name, meta.get("id", "?"), ch or "채널 미지정"))
    findings = []
    if not ch:
        findings.append((FAIL, "머리말에 `channel:` 이 없다"))
    else:
        try:
            findings += CH.check_format(ch, body, meta.get("title"))
        except KeyError as e:
            findings.append((FAIL, str(e)))
    findings += check_hangul(body)
    findings += check_numbers(path)
    findings += check_links(body, meta.get("target"), net, ch)
    findings += check_card(meta.get("target"), net, ch)

    for lvl in (FAIL, WARN, INFO):
        for l, m in findings:
            if l == lvl:
                print("   %-5s %s" % (l, m))
    v = CH.worst(findings)
    print("   판정: **%s**" % v)
    return v, findings


def check_all(net=False):
    if not os.path.isdir(DRAFTS):
        print("문안 폴더가 없다: %s" % DRAFTS)
        print("  (`본부\\채널문안\\` 에 문안 파일을 둔다. 공개 저장소에 원고를 안 넣는다 — §4.1)")
        return 2
    # **밑줄로 시작하면 문안이 아니다** — 근거표·메모 같은 곁딸린 파일. `boot_check` 가
    # `analysis/_*.py` 를 건너뛰는 것과 같은 관례다.
    files = sorted(f for f in glob.glob(os.path.join(DRAFTS, "*.md"))
                   if not os.path.basename(f).startswith("_"))
    if not files:
        print("문안이 없다: %s" % DRAFTS)
        return 2
    print("== 채널 문안 검사 — 문안 %d건 ==" % len(files))
    bad = 0
    for f in files:
        try:
            v, _ = check_one(f, net)
        except Exception as e:
            print("\n── %s\n   FAIL  못 읽었다: %s" % (os.path.basename(f), e))
            v = FAIL
        if v == FAIL:
            bad += 1
    print("\n" + "-" * 70)
    print("문안 %d건 중 FAIL %d건." % (len(files), bad))
    if not net:
        print("**링크와 카드는 안 쳤다** — `--net` 을 줘야 친다.")
    return 1 if bad else 0


def selftest():
    ok = True
    import tempfile

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 문안 파일을 읽는가 ──")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.md")
        io.open(p, "w", encoding="utf-8").write(
            "---\nid: li-x\nchannel: linkedin\ntarget: https://example.org\n---\n"
            "본문 첫 줄.\n둘째 줄 https://example.org\n")
        meta, body = parse(p)
        chk("머리말을 읽는다", meta.get("id"), "li-x")
        chk("채널을 읽는다", meta.get("channel"), "linkedin")
        chk("본문이 머리말 뒤부터다", body.startswith("본문 첫 줄."), True)
        chk("본문 끝을 안 자른다", body.rstrip().endswith("https://example.org"), True)

        bad = os.path.join(d, "b.md")
        io.open(bad, "w", encoding="utf-8").write("머리말 없음\n")
        try:
            parse(bad)
            chk("머리말 없으면 막는다", True, False)
        except ValueError:
            chk("머리말 없으면 막는다", True, True)

    print("── 인수시험: 대장을 읽는가 ──")
    rows = facts_rows()
    chk("대장 행을 여럿 읽는다", len(rows) >= 20, True)
    chk("지위가 4등급 안", all(r[2] in ("검증", "관측", "참고", "미확인") for r in rows), True)
    chk("창이 비어 있지 않다", all(r[1].strip() for r in rows), True)

    print("── 인수시험: 링크를 안 칠 때 통과로 안 세는가 (사고 91) ──")
    f = check_links("글 https://example.org", "https://example.org", net=False)
    chk("--net 없으면 안 쳤다고 말한다", any("안 쳤다" in m for _, m in f), True)
    chk("안 쳤는데 FAIL 을 안 만든다", any(l == FAIL for l, _ in f), False)
    f = check_links("글 https://example.org", "https://other.example", net=False)
    chk("target 이 본문에 없으면 WARN", any(l == WARN for l, _ in f), True)

    print("── 인수시험: 카드 ──")
    f = check_card(None, net=False)
    chk("target 없으면 WARN", any(l == WARN for l, _ in f), True)
    f = check_card("https://example.org", net=False)
    chk("--net 없으면 안 봤다고 말한다", any("안 봤다" in m for _, m in f), True)
    # **카드가 없는 채널에서 카드를 검사하면 경고만 는다** — 없는 것을 검사하지 않는다.
    f = check_card("https://example.org", net=True, channel="email")
    chk("메일은 카드 검사를 건너뛴다", [l for l, _ in f], [INFO])
    f = check_links("글 https://a.example 그리고 https://b.example",
                    "https://a.example", net=False, channel="email")
    chk("메일은 카드 순서를 안 본다", any("마지막이 아니다" in m for _, m in f), False)
    f = check_links("글 https://a.example 그리고 https://b.example",
                    "https://a.example", net=False, channel="linkedin")
    chk("링크드인은 카드 순서를 본다", any("마지막이 아니다" in m for _, m in f), True)

    print("── 인수시험: 깨진 음절 (2026-09-10 사고) ──")
    chk("「그럵」을 잡는다", bool(check_hangul("왜 그럵 값이었는지는")), True)
    chk("「그런」은 안 잡는다", check_hangul("왜 그런 값이었는지는"), [])
    chk("실제로 쓰는 겹받침은 안 잡는다",
        check_hangul("값이 없다 · 많다 · 앉다 · 읽다 · 밟다 · 싫다 · 젊다 · 핥다 · 읊다 · 몫"), [])
    chk("판정이 아니라 의심이다(WARN)",
        all(l == WARN for l, _ in check_hangul("그럵")), True)
    # **이 검사가 못 보는 것을 시험이 말한다** — 받침 없는 음절끼리 바뀌면 침묵한다.
    chk("받침 없는 자리의 깨짐은 못 본다(한계)", check_hangul("왜 그러 값이었는지는"), [])

    print("── 인수시험: 해시 대조 (형해화된 대조를 막는다) ──")
    a = "가나다\n라마바"
    chk("공백을 지우면 같다", norm_for_hash(a), norm_for_hash("가나다   \n\n 라마바"))
    chk("한 글자만 달라도 해시가 갈린다",
        body_hash("왜 그런 값") == body_hash("왜 그럵 값"), False)
    chk("줄바꿈이 달라도 해시는 같다",
        body_hash("가나\n다") == body_hash("가나\n\n다"), True)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "v.md")
        io.open(p, "w", encoding="utf-8").write("---\nid: t\nchannel: linkedin\n---\n왜 그런 값\n")
        good = body_hash("왜 그런 값")[:16]
        chk("맞으면 0", verify(p, good), 0)
        chk("틀리면 1 — **닫히는 쪽으로 실패한다**", verify(p, body_hash("왜 그럵 값")[:16]), 1)
        chk("빈 해시도 1", verify(p, ""), 1)

    print("── 인수시험: OG 태그 정규식 ──")
    html = ('<meta property="og:title" content="측심">'
            '<meta content="설명" property="og:description">')
    got = {k.lower(): v for k, v in OG.findall(html)}
    for v, k in OG2.findall(html):
        got.setdefault(k.lower(), v)
    chk("property 가 앞에 와도 잡는다", got.get("title"), "측심")
    chk("content 가 앞에 와도 잡는다", got.get("description"), "설명")

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="채널 문안 재료·검사")
    ap.add_argument("--source", default=None, help="문안 재료를 뽑는다 (보고서 경로 선택)")
    ap.add_argument("--check", default=None, help="문안 파일 하나를 검사")
    ap.add_argument("--check-all", action="store_true", help="본부 문안 전부")
    ap.add_argument("--net", action="store_true", help="링크와 카드를 실제로 친다")
    ap.add_argument("--clip", default=None, help="본문을 클립보드에 넣고 정본 해시를 낸다 (전사 금지)")
    ap.add_argument("--verify", default=None, help="파일")
    ap.add_argument("--got", default=None, help="브라우저가 낸 해시")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.clip:
        sys.exit(clip(a.clip))
    if a.verify:
        sys.exit(verify(a.verify, a.got))
    if a.check:
        v, _ = check_one(a.check, a.net)
        sys.exit(1 if v == FAIL else 0)
    if a.check_all:
        sys.exit(check_all(a.net))
    sys.exit(source(a.source))

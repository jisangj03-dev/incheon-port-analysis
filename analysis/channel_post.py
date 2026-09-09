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

닿지 않는 곳
------------
· **문안이 좋은지는 안 본다.** 형식 · 수치 지위 · 링크 · 카드만 본다.
· `--net` 없이는 **링크를 안 친다** — 소스 판정은 사이트에 대한 진술이 아니다(사고 91).
· **OG 카드는 태그가 있는지와 이미지가 200인지만 본다.** 채널이 실제로 어떻게 그리는지는
  **사람이 미리보기로 본다.** 「속성이 붙었다」는 「그렇게 보인다」가 아니다(사고 73).
· 수치 대조는 `lint_publish.py --channel` 에 넘긴다 — 대장을 두 번 읽지 않는다.
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


def check_links(body, target, net):
    out = []
    us = CH.urls(body)
    if target and target not in us:
        out.append((WARN, "카드가 될 주소(`target`)가 본문에 없다: %s" % target))
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


def check_card(target, net):
    """링크 카드 — **태그가 있는가와 이미지가 200인가.** 어떻게 그려지는지는 사람이 본다."""
    out = []
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
    findings += check_numbers(path)
    findings += check_links(body, meta.get("target"), net)
    findings += check_card(meta.get("target"), net)

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
    files = sorted(glob.glob(os.path.join(DRAFTS, "*.md")))
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
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if a.check:
        v, _ = check_one(a.check, a.net)
        sys.exit(1 if v == FAIL else 0)
    if a.check_all:
        sys.exit(check_all(a.net))
    sys.exit(source(a.source))

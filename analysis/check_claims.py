# -*- coding: utf-8 -*-
"""주장 일치 검사 — **규범을 고쳤는데 그것을 되풀이하는 공개물이 안 고쳐졌는가.**

왜 있는가
---------
사고 108. 지침 §1.2·§2.3 을 실측에 맞춰 고친 뒤에도 **공개 사이트는 하루 동안 옛 문면을
걸고 있었다** — `about.md` 「검수 · 발행: 운영자 … 발행을 실행한다」 · `README.md` 표기 표 ·
채널 문안 두 곳. **안 하는 일을 한다고 독자에게 적고 있었다.**

그때 처분을 **규율**로 뒀다: 「역할 조항을 고치면 공개물을 같은 커밋에서 연다」.
**그런데 §0-3 이 정확히 그것을 금지한다** — 절차는 코드에 상주시킨다. 사람이 매 세션
나르는 규칙은 유실된다(사고 22). 규율로 둔 처분은 **다음 개정 때 아무도 기억하지 않는다.**

`check_refs.py` 는 **조항 번호**가 실재하는지 본다. 여기서 낡는 것은 번호가 아니라
**주장**이다 — 번호는 그대로인데 그 조항이 말하는 내용이 바뀐다. 그 자리를 이 파일이 맡는다.

  python analysis/check_claims.py            # 경고. 종료 0
  python analysis/check_claims.py --strict   # 어긋나면 종료 1
  python analysis/check_claims.py --list     # 등록된 주장 전문
  python analysis/check_claims.py --selftest

무엇을 보는가
-------------
주장마다 **정본**(지침에 있어야 하는 문구)과 **폐기**(공개물에 있으면 안 되는 옛 문구)를 짝으로 든다.

  · **정본이 지침에서 사라지면 FAIL** — 지침이 또 바뀌었는데 이 등록부가 안 따라온 것이다.
    **검사기가 낡는 것을 검사기가 잡는다.**
  · **폐기 문구가 독자가 읽는 자리에 있으면 FAIL** — 사고 108 그 자체다.

닿지 않는 곳
------------
· **등록한 주장만 본다.** 모든 문장의 참·거짓은 기계가 못 본다 — 그런 검사기는 없고 만들 수도 없다.
  **역할 조항을 고칠 때 여기 짝을 같이 넣는 것이 규율이고, 그 규율은 하나뿐이라 유실되기 어렵다.**
· **문자열만 본다.** 같은 뜻을 다른 말로 적으면 못 잡는다.
· **인용은 봐준다** — 「종전에 「…」로 적혀 있었다」는 정정 표기이지 위반이 아니다(§3-11).
  판별은 앞뒤의 인용 표지로 한다. **표지 없이 옛 문구를 인용하면 위반으로 잡힌다** — 보수적 오탐이다.
· 발행본·기록·아카이브는 **경고만** 낸다. 그때는 참이었고 발행본은 형식 때문에 안 고친다(§3-11).
· **이미 게시된 채널 글은 아예 안 본다.** 파일이 아니라 남의 서버에 있고, 읽으려면 로그인이
  필요하다(자격 증명은 안 다룬다). **그래서 옛 게시물의 낡은 주장은 이 검사가 영원히 못 본다** —
  2026-08 게시물의 「4편」·「검증·해석은 직접 했고」가 그 실례다. 막는 자리는 **게시 전**이고,
  그쪽은 `channel_post.py --check` 의 낡는 값 검사가 든다.
"""

import argparse
import glob
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HQ = os.path.join(os.path.expanduser("~"), "OneDrive", "문서", "본부")
GUIDE = os.path.join(HQ, "프로젝트지침.md")
SOUND = os.path.join(ROOT, "..", "sounding", "app", "src")

FAIL, WARN, INFO = "FAIL", "WARN", "INFO"

# ── 등록부 ──────────────────────────────────────────────────────────────────
#
# 「정본」은 **지침에 있어야 하는 문구**다. 사라지면 이 등록부가 낡은 것이다.
# 「폐기」는 **독자가 읽는 자리에 있으면 안 되는 옛 문구**다.

CLAIMS = [
    {
        "키": "역할 갈래",
        "왜": "누가 검수하고 누가 발행하는가. 사고 108 이 난 자리다.",
        "정본": ["하는 쪽이 한다", "검수는 발행 게이트가 아니다"],
        "폐기": [
            "검수 · 발행: 운영자",
            "검수·발행** | **운영자",
            "발행을 실행한다",
            "발행 전에는 결론 자리를 통독하고",
            "기록이 없는 편은 이 표기를 달 수 없다",
            "편마다 1행 이상",
        ],
    },
    {
        "키": "push·배포 주체",
        "왜": "v6.4 로 세션 몫이 됐다. 옛 문면은 운영자를 기다리게 만든다.",
        "정본": ["커밋 · push · 배포"],
        "폐기": ["push 는 운영자만", "공개 발행은 운영자의 서명"],
    },
    {
        "키": "생성 주체 비표기",
        "왜": "v6.2 운영자 결정. 공개물에 생성 주체를 적지 않는다.",
        "정본": ["공개물에 AI 생성 표기를 싣지 않는다"],
        "폐기": ["본문은 Claude가 생성하고", "본문 생성: AI", "본문 생성** | **AI"],
    },
    {
        "키": "축",
        "왜": "v6.0 운영자 선언으로 인천항 하나. 3산업·라인 문면은 v5.x 다.",
        "정본": ["인천항 하나만 판다"],
        "폐기": ["물류 · 무역 · 유통", "물류·무역·유통", "라인 A/B/C/D"],
    },
]

# **독자가 읽는 자리.** 사고 108 이 아팠던 이유가 이것이다 — 거기 있는 것을 독자가 읽는다.
def strict_targets():
    out = []
    for rel in ("about.md", "README.md", "404.md"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            out.append((rel, p))
    for d in ("_includes", "_layouts"):
        for p in sorted(glob.glob(os.path.join(ROOT, d, "*.html"))):
            out.append((d + "/" + os.path.basename(p), p))
    for p in sorted(glob.glob(os.path.join(HQ, "채널문안", "*.md"))):
        out.append(("본부/채널문안/" + os.path.basename(p), p))   # `_` 파일도 본다 — 주장은 어디 적히든 주장이다
    p = os.path.join(HQ, "채널문안_측심_20260902.md")
    if os.path.exists(p):
        out.append(("본부/채널문안_측심_20260902.md", p))   # 붙여넣기의 출처라 엄격히 본다
    p = os.path.join(SOUND, "landing-content.ts")
    if os.path.exists(p):
        out.append(("측심/landing-content.ts", p))
    return out


# 그때는 참이었던 자리 — 경고만.
def soft_targets():
    out = []
    for rel in ("docs/사고기록.md", "docs/작업기록.md", "docs/STATUS.md"):
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            out.append((rel, p))
    for p in sorted(glob.glob(os.path.join(ROOT, "reports", "*.md"))):
        out.append(("reports/" + os.path.basename(p), p))
    return out


# 인용 표지 — 「종전에 「…」로 적혀 있었다」는 정정이지 위반이 아니다(§3-11).
CITE = re.compile(r"종전|구 ?판|폐지|폐기|뺐다|빼|고쳤다|정정|적혀 있었다|이었다|였다|없어졌다|바뀌었다|안 넣는다|나오면")
BACK, FWD = 160, 80


def norm(text):
    """줄바꿈과 인용 부호(`> `)를 접는다 — 인용이 두 줄에 걸쳐도 한 문맥으로 읽는다."""
    t = text.replace("\r\n", "\n")
    t = re.sub(r"\n>\s?", " ", t)      # 블록 인용의 이어짐
    t = re.sub(r"\s+", " ", t)
    return t


def is_citation(flat, pos, phrase):
    """앞뒤에 인용 표지가 있으면 인용이다. **표지가 없으면 위반으로 본다**(보수적)."""
    lo = max(0, pos - BACK)
    hi = min(len(flat), pos + len(phrase) + FWD)
    return bool(CITE.search(flat[lo:pos])) or bool(CITE.search(flat[pos + len(phrase):hi]))


def scan_file(path, claims):
    """반환 [(주장키, 문구, 인용인가)]"""
    try:
        flat = norm(io.open(path, encoding="utf-8", errors="replace").read())
    except Exception:
        return []
    hits = []
    for c in claims:
        for ph in c["폐기"]:
            start = 0
            while True:
                i = flat.find(ph, start)
                if i < 0:
                    break
                hits.append((c["키"], ph, is_citation(flat, i, ph)))
                start = i + len(ph)
    return hits


def check_anchors():
    """**정본이 지침에 있는가.** 없으면 이 등록부가 낡은 것이다 — 검사기의 자기 검사."""
    if not os.path.isfile(GUIDE):
        return None
    g = norm(io.open(GUIDE, encoding="utf-8", errors="replace").read())
    missing = []
    for c in CLAIMS:
        for a in c["정본"]:
            if a not in g:
                missing.append((c["키"], a))
    return missing


def main(strict=False, listing=False):
    if listing:
        print("== 등록된 주장 %d건 ==" % len(CLAIMS))
        for c in CLAIMS:
            print("\n── %s" % c["키"])
            print("   왜: %s" % c["왜"])
            print("   정본(지침에 있어야 한다): " + " · ".join("「%s」" % a for a in c["정본"]))
            print("   폐기(공개물에 있으면 안 된다):")
            for p in c["폐기"]:
                print("     · 「%s」" % p)
        return 0

    missing = check_anchors()
    if missing is None:
        print("[불성립] 지침 파일을 못 찾았다: %s" % GUIDE)
        print("  이 저장소만 clone한 기계에서는 잴 수 없다. 통과로 치지 않는다.")
        return 2

    st, so = strict_targets(), soft_targets()
    print("== 주장 일치 검사 ==")
    print("  주장 %d건 · 독자가 읽는 파일 %d개 · 기록 %d개"
          % (len(CLAIMS), len(st), len(so)))

    bad = []
    if missing:
        print("\n  **정본이 지침에서 사라졌다 %d건 — 이 등록부가 낡았다**" % len(missing))
        for k, a in missing:
            print("    [%s] 「%s」" % (k, a))
        bad += missing

    hard, cites, softhits = [], [], []
    for rel, p in st:
        for k, ph, cite in scan_file(p, CLAIMS):
            (cites if cite else hard).append((rel, k, ph))
    for rel, p in so:
        for k, ph, cite in scan_file(p, CLAIMS):
            if not cite:
                softhits.append((rel, k, ph))

    if hard:
        print("\n  **폐기된 문구가 독자가 읽는 자리에 있다 %d건**" % len(hard))
        for rel, k, ph in hard:
            print("    %-34s [%s] 「%s」" % (rel, k, ph))
        bad += hard
    if cites:
        print("\n  인용 %d건 — 정정 표기다(§3-11). 위반이 아니다." % len(cites))
        for rel, k, ph in cites:
            print("    %-34s [%s] 「%s」" % (rel, k, ph))
    if softhits:
        print("\n  경고 %d건 — 발행본·기록이라 고치지 않는다(그때는 참이었다)" % len(softhits))
        for rel, k, ph in softhits[:10]:
            print("    %-34s [%s] 「%s」" % (rel, k, ph))

    print()
    if not bad:
        print("어긋난 주장 0건 / 주장 %d건 · 파일 %d개 검사." % (len(CLAIMS), len(st) + len(so)))
    else:
        print("**고쳐야 할 것 %d건.** 지침의 역할 조항이 바뀌었으면 **공개물을 같은 커밋에서 연다.**"
              % len(bad))
    return 1 if (bad and strict) else 0


def selftest():
    ok = True
    import tempfile

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 정본이 지침에 서 있는가 (등록부의 자기 검사) ──")
    missing = check_anchors()
    if missing is None:
        print("  (지침이 없는 기계 — **미실행**이지 통과가 아니다)")
    else:
        chk("정본이 전부 지침에 있다", missing, [])

    print("── 인수시험: 인용과 위반을 가르는가 ──")
    with tempfile.TemporaryDirectory() as d:
        # 실물에서 온 두 경우다.
        cite2 = os.path.join(d, "cite2.md")
        io.open(cite2, "w", encoding="utf-8").write(
            "> **[2026-09-09 정정]** 이 절은 종전에 **「검수 · 발행: 운영자 — 발행 전 결론 자리를 통독하고,\n"
            "> 기계가 뽑은 수치 1건을 대조하고, 발행을 실행한다」**로 적혀 있었다.\n")
        hits = scan_file(cite2, CLAIMS)
        chk("두 줄에 걸친 인용도 인용으로 읽는다",
            [h[2] for h in hits], [True] * len(hits))
        chk("그 안에서 여러 문구를 잡는다", len(hits) >= 2, True)

        cite1 = os.path.join(d, "cite1.md")
        io.open(cite1, "w", encoding="utf-8").write(
            "> 종전 판의 「본문은 Claude가 생성하고」 문장은 뺐다.\n")
        chk("한 줄 인용도 인용", [h[2] for h in scan_file(cite1, CLAIMS)], [True])

        bad = os.path.join(d, "bad.md")
        io.open(bad, "w", encoding="utf-8").write(
            "## 운영 구조\n\n**검수 · 발행: 운영자.**\n주제를 정하고, 결론 자리를 통독하고, 발행을 실행한다.\n")
        hits = scan_file(bad, CLAIMS)
        chk("표지 없는 옛 문구는 위반", any(not h[2] for h in hits), True)
        chk("위반을 여러 건 잡는다", len([h for h in hits if not h[2]]) >= 2, True)

        clean = os.path.join(d, "clean.md")
        io.open(clean, "w", encoding="utf-8").write(
            "무엇을 재고 어떤 기준으로 판정할지는 운영자가 정한다.\n"
            "수집 · 계산 · 차트 · 검사 · 발행은 코드가 한다.\n")
        chk("고친 문면은 안 걸린다", scan_file(clean, CLAIMS), [])

        axis = os.path.join(d, "axis.md")
        io.open(axis, "w", encoding="utf-8").write("우리는 물류·무역·유통 3산업을 다룬다.\n")
        chk("옛 축 문면을 잡는다", [h[0] for h in scan_file(axis, CLAIMS)], ["축"])

    print("── 인수시험: 대상 ──")
    st = [r for r, _ in strict_targets()]
    chk("about.md 를 본다", "about.md" in st, True)
    chk("README.md 를 본다", "README.md" in st, True)
    chk("채널 문안을 본다", any(r.startswith("본부/채널문안/") for r in st), True)
    so = [r for r, _ in soft_targets()]
    chk("발행본은 경고 쪽", any(r.startswith("reports/") for r in so), True)
    chk("발행본은 엄격 쪽이 아니다", any(r.startswith("reports/") for r in st), False)

    print("── 인수시험: 지금 실물 ──")
    hard = []
    for rel, p in strict_targets():
        hard += [(rel, k, ph) for k, ph, c in scan_file(p, CLAIMS) if not c]
    print("     지금: 독자가 읽는 파일 %d개 · 위반 %d건" % (len(strict_targets()), len(hard)))
    for rel, k, ph in hard[:5]:
        print("       %s [%s] 「%s」" % (rel, k, ph))

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="주장 일치 검사 (사고 108)")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else main(a.strict, a.list))

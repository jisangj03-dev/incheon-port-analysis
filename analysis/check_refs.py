# -*- coding: utf-8 -*-
"""조항 참조 검사 — **「지침 §X」가 실제로 있는 조항을 가리키는가.**

왜 있는가
---------
2026-09-09 지침 v7.0(규제 해제)에서 절 하나(§11 폐지 목록)와 소절 둘(§0.2 · §2.6)이
없어지고 §2.2 · §10 의 항 번호가 밀렸다. 그 순간 **`지침 §…` 참조 여럿이 조용히 허공을
가리켰다** — 코드 주석 · 사이트 HTML 주석 · SKILL · STATUS · 챗 운영블록에 흩어져 있었고,
**어느 검사기도 그것을 못 봤다.**

실측(사후 재현 · `git archive afb69fb` 를 새 앵커에 댄다): 저장소의 명시 참조 **60건 중 6건**
(`§11` 2 · `§5.0` 2 · `§2.6` 1 · `§10-8` 1). 본부와 지침 자기 참조를 더해 **9건 · 고칠 것 8건.**
**수를 여기 박은 이유:** 이것은 지금 상태가 아니라 **이 파일이 생긴 계기**의 크기다 —
낡지 않는다. 지금 값은 이 파일을 돌리면 나온다.

**사고 31 의 얼굴이다** — 같은 사실이 두 자리에 있고 한쪽만 갱신된다.
다만 값이 아니라 **참조**라서 `check_counts.py` 도 `lint_publish.py` 도 안 본다.

그리고 이 결함은 **조용하다.** 깨진 참조는 아무것도 안 터뜨리고, 다음 세션이
「§2.6 이 그렇게 정한다」를 읽고 **없는 조항을 근거로 판단한다.**
**조항이 판단을 대신하는 것을 지침 §0.1 이 막는데, 없는 조항이 그러는 것은 더 나쁘다.**

이 파일은 **`check_guideline_size.py` 의 자리를 대신한다.** 그쪽은 지침의 **형식**(바이트)을
쟀고, v7.0 이 그 상한을 조항째 걷어냈다. 남은 것은 **실질** — 참조가 서 있는가.

  python analysis/check_refs.py            # 경고. 종료 0
  python analysis/check_refs.py --strict   # 깨진 참조가 있으면 종료 1
  python analysis/check_refs.py --list     # 유효 앵커를 전부 찍는다
  python analysis/check_refs.py --selftest

닿지 않는 곳
------------
· **「지침 §」로 명시된 것만 본다.** 맨 `§4` 는 그 문서 자신의 4절일 수 있어 안 센다
  (`docs/NN_판정결과.md` 의 `§4` 가 실제로 그렇다). **명시하지 않은 참조는 이 검사 밖이다.**
· **번호가 맞는지만 본다. 내용이 맞는지는 안 본다** — `§3-7` 이 있기만 하면 통과다.
  「그 조항이 정말 그런 말을 하는가」는 사람이 읽는다.
· **발행본(`reports/`)과 기록은 경고만 낸다** — `사고기록`·`작업기록`·아카이브, 그리고
  **파일명에 날짜가 박힌 본부 문서**(`항만사이트조사_20260828.md` 류). 그때는 참이었고
  발행본은 형식 때문에 안 고친다(§3-11). **고칠 대상이 아니라 알아 둘 사실이다.**
  **날짜 없는 상시 문서**(지침·CLAUDE·SKILL·챗 운영블록·구성 실측)는 안 봐준다 — 지금 참이어야 한다.
· **자기 자신은 안 본다** — 인수시험 픽스처가 일부러 깨진 참조를 든다. 그러므로
  **이 파일 안의 참조는 아무도 안 본다.** 여기 새 조항 번호를 적을 때는 손으로 확인한다.
· 지침 파일이 없는 기계에서는 **불성립**이지 통과가 아니다(종료 2).
"""

import argparse
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HQ = os.path.join(os.path.expanduser("~"), "OneDrive", "문서", "본부")
GUIDE = os.path.join(HQ, "프로젝트지침.md")

# 「지침 §…」으로 **명시된** 것만 본다. 맨 §N 은 그 문서 자신의 절일 수 있다.
REF = re.compile(r"지침(?:의)?\s*(?:v[\d.]+\s*)?§\s*(\d+(?:\.\d+)?(?:-\d+)*)")
# 지침 자신 안에서는 맨 §N 도 자기 조항 참조다.
SELF_REF = re.compile(r"§\s*(\d+(?:\.\d+)?(?:-\d+)*)")

H_SEC = re.compile(r"^##\s+§(\d+)\.")                 # ## §3. 수치 규율
H_SUB = re.compile(r"^###\s+(\d+\.\d+)\s")            # ### 2.2 표기 의무
H_DASH = re.compile(r"^###\s+(\d+-\d+)\.")            # ### 3-5. 인과 …
ITEM = re.compile(r"^(\d+)\.\s")                       # 1. 절차는 …

# 참인 당시 기록이라 고치지 않는 자리 — 경고로만 낸다.
SOFT = ("reports/", "docs/사고기록.md", "docs/작업기록.md", "본부/아카이브/")
# **파일명에 날짜가 박힌 본부 문서도 기록이다** — `항만사이트조사_20260828.md` 처럼.
# 그날의 판단을 적은 것이라 조항이 없어져도 고치지 않는다. 지침·부트블록처럼 **날짜 없는**
# 상시 문서는 여기 안 걸린다 — 그쪽은 지금 참이어야 한다.
DATED = re.compile(r"_20\d{6}\.md$")


def anchors(text):
    """지침 본문에서 **실제로 존재하는** 조항 번호를 뽑는다. 목록을 손으로 안 든다."""
    valid, cur, items = set(), None, {}
    for line in text.split("\n"):
        m = H_SEC.match(line)
        if m:
            cur = m.group(1)
            valid.add(cur)
            continue
        m = H_SUB.match(line)
        if m:
            cur = m.group(1)
            valid.add(cur)
            valid.add(cur.split(".")[0])
            continue
        m = H_DASH.match(line)
        if m:
            cur = m.group(1)
            valid.add(cur)
            valid.add(cur.split("-")[0])
            continue
        m = ITEM.match(line)
        if m and cur:
            n = int(m.group(1))
            items[cur] = max(items.get(cur, 0), n)
    # 절 안의 번호 항목 — `§0-4`·`§2.2-3`·`§10-1` 이 그것이다.
    for sec, n in items.items():
        for i in range(1, n + 1):
            valid.add("%s-%d" % (sec, i))
    return valid


def targets():
    """검사 대상 — 저장소 추적 파일 + 본부 md(아카이브 제외).

    **자기 자신은 뺀다.** 이 파일의 인수시험 픽스처가 「지침 §2.6」처럼 **일부러 깨진**
    참조를 문자열로 들고 있어서, 안 빼면 자기 시험 자료를 결함으로 신고한다
    (실제로 그렇게 났다 — 커밋되어 `git ls-files` 에 들어온 순간).
    **참조를 말하는 파일은 참조처럼 생긴 문자열을 가진다.**
    """
    out = []
    try:
        r = subprocess.run(["git", "ls-files"], cwd=ROOT, stdout=subprocess.PIPE,
                           text=True, encoding="utf-8", errors="replace")
        for rel in (r.stdout or "").splitlines():
            if rel.replace("\\", "/").endswith("analysis/check_refs.py"):
                continue
            if rel.lower().endswith((".md", ".py", ".sh", ".html", ".yml", ".yaml", ".txt")):
                out.append((rel, os.path.join(ROOT, rel)))
    except Exception:
        pass
    if os.path.isdir(HQ):
        for fn in sorted(os.listdir(HQ)):
            if fn.endswith(".md"):
                out.append(("본부/" + fn, os.path.join(HQ, fn)))
    return out


def scan(valid):
    """반환 (깨진 것, 훑은 파일 수, 본 참조 수). **분모를 같이 낸다**(사고 77)."""
    bad, files, seen = [], 0, 0
    for rel, path in targets():
        try:
            text = io.open(path, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        files += 1
        pat = SELF_REF if os.path.abspath(path) == os.path.abspath(GUIDE) else REF
        for m in pat.finditer(text):
            seen += 1
            num = m.group(1)
            if num in valid:
                continue
            line = text.count("\n", 0, m.start()) + 1
            r = rel.replace("\\", "/")
            soft = any(s in r for s in SOFT) or bool(DATED.search(r))
            bad.append((rel, line, num, soft))
    return bad, files, seen


def main(strict=False, listing=False):
    if not os.path.isfile(GUIDE):
        print("[불성립] 지침 파일을 못 찾았다: %s" % GUIDE)
        print("  이 저장소만 clone한 기계에서는 잴 수 없다. 통과로 치지 않는다.")
        return 2
    valid = anchors(io.open(GUIDE, encoding="utf-8").read())
    if listing:
        print("== 지침의 유효 앵커 %d개 ==" % len(valid))
        print("  " + " · ".join("§" + a for a in sorted(valid, key=sortkey)))
        return 0
    bad, files, seen = scan(valid)
    hard = [b for b in bad if not b[3]]
    soft = [b for b in bad if b[3]]
    print("== 조항 참조 검사 ==")
    print("  파일 %d개 · 「지침 §」 참조 %d건 · 유효 앵커 %d개" % (files, seen, len(valid)))
    if hard:
        print("\n  **깨진 참조 %d건 — 없는 조항을 가리킨다**" % len(hard))
        for rel, line, num, _ in hard:
            print("    %s:%d  §%s" % (rel, line, num))
    if soft:
        print("\n  경고 %d건 — 발행본·기록이라 고치지 않는다(그때는 참이었다)" % len(soft))
        for rel, line, num, _ in soft:
            print("    %s:%d  §%s" % (rel, line, num))
    if not bad:
        print("\n깨진 참조 0건 / 참조 %d건 검사." % seen)
    elif not hard:
        print("\n고쳐야 할 깨진 참조 0건 / 참조 %d건 검사." % seen)
    else:
        print("\n**고쳐야 할 것 %d건.** 지침 조항이 없어졌거나 번호가 밀렸다 —"
              " 참조를 고치거나, 조항을 되살린다." % len(hard))
    return 1 if (hard and strict) else 0


def sortkey(a):
    return [int(x) for x in re.split(r"[.-]", a)]


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-50s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 앵커를 본문에서 뽑는가 (목록을 안 든다) ──")
    fake = "\n".join([
        "# 지침",
        "## §0. 지위",
        "1. 하나",
        "2. 둘",
        "3. 셋",
        "### 0.1 판단 우선",
        "## §2. 구조",
        "### 2.2 표기",
        "1. 가",
        "2. 나",
        "## §3. 수치",
        "### 3-5. 예외",
        "## §10. 안 하는 것",
        "1. 편수",
        "2. 인과",
    ])
    v = anchors(fake)
    chk("절 표제를 잡는다", {"0", "2", "3", "10"} <= v, True)
    chk("소절(0.1 · 2.2)을 잡는다", {"0.1", "2.2"} <= v, True)
    chk("붙임표 소절(3-5)을 잡는다", "3-5" in v, True)
    chk("절 안의 항(§0-3)을 잡는다", "0-3" in v, True)
    chk("소절 안의 항(§2.2-2)을 잡는다", "2.2-2" in v, True)
    chk("없는 항(§0-4)은 안 잡는다", "0-4" in v, False)
    chk("없는 항(§10-3)은 안 잡는다", "10-3" in v, False)
    chk("없는 절(§11)은 안 잡는다", "11" in v, False)

    print("── 인수시험: 무엇을 참조로 세는가 ──")
    chk("「지침 §2.6」을 잡는다", bool(REF.search("형식은 지침 §2.6 이 든다")), True)
    chk("「지침 v6.4 §4」도 잡는다", REF.search("지침 v6.4 §4 를 본다").group(1), "4")
    chk("맨 「§4」는 안 잡는다 — 그 문서의 4절일 수 있다",
        bool(REF.search("이 문서 §4 를 본다")), False)
    chk("지침 안에서는 맨 §4 도 참조다", bool(SELF_REF.search("§4 를 본다")), True)

    print("── 인수시험: 자기 자신을 안 보는가 (픽스처가 일부러 깨져 있다) ──")
    names = [rel.replace("\\", "/") for rel, _ in targets()]
    chk("대상에서 자기를 뺐다", any(n.endswith("analysis/check_refs.py") for n in names), False)
    chk("다른 analysis 파일은 본다",
        any(n.startswith("analysis/") and n.endswith(".py") for n in names), True)

    print("── 인수시험: 기록과 상시 문서를 가르는가 ──")
    chk("날짜 박힌 본부 문서는 기록", bool(DATED.search("본부/항만사이트조사_20260828.md")), True)
    chk("날짜 없는 상시 문서는 아니다", bool(DATED.search("본부/프로젝트지침.md")), False)
    chk("CLAUDE.md 도 아니다", bool(DATED.search("CLAUDE.md")), False)
    chk("발행본은 SOFT 목록으로 걸린다",
        any(s in "reports/report_07_x.md" for s in SOFT), True)

    print("── 인수시험: 깨진 것을 실제로 골라내는가 (사고 26) ──")
    dangling = [n for n in ("2.6", "11", "0.2", "10-9") if n not in v]
    chk("네 개 다 깨진 것으로 나온다", len(dangling), 4)
    chk("살아 있는 것은 안 걸린다", "3-5" in v and "2.2-1" in v, True)

    print("── 인수시험: 실물 지침에 대고 ──")
    if os.path.isfile(GUIDE):
        real = anchors(io.open(GUIDE, encoding="utf-8").read())
        chk("실물에서 여러 앵커를 뽑는다", len(real) >= 25, True)
        chk("§4.1-1(취업 타깃 기업명)이 산다", "4.1-1" in real, True)
        chk("§3-7(선커밋)이 산다", "3-7" in real, True)
        chk("§11(폐지 목록)은 v7.0 에서 없다", "11" in real, False)
        bad, files, seen = scan(real)
        chk("파일을 여럿 훑는다", files >= 20, True)
        chk("참조를 여럿 본다 — 분모가 0이 아니다", seen >= 10, True)
        print("     지금: 파일 %d · 참조 %d · 깨진 것 %d(그중 고칠 것 %d)"
              % (files, seen, len(bad), len([b for b in bad if not b[3]])))
    else:
        print("  (지침 파일이 없는 기계 — 실물 시험은 건너뛴다. **통과가 아니라 미실행이다**)")

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="「지침 §X」 참조가 실제 조항을 가리키는가")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else main(a.strict, a.list))

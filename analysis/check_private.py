# -*- coding: utf-8 -*-
"""공개 저장소에 나가면 안 되는 것이 들어갔는지 본다.

왜 있는가
---------
**[2026-09-01 운영자 지시] 사이트 어디에도 운영자 실명이 들어가지 않는다.**
그날 실측으로 **공개 대상 11곳**에 있었다(발행본 3편 · README · about 둘 · verify 둘 ·
전 페이지 푸터 · CITATION). 전부 지웠다.

**그런데 지운 것은 그때 상태일 뿐이다.** §2.6 이 「새 편은 기준편(`report_07`)을 열어
형식을 베껴 쓴다」고 정하므로, 표기 블록은 **베껴지면서 퍼진다.** 한 번 되살아나면
그 뒤 전 편에 실린다. **조심으로 안 되는 것은 경로를 없앤다**(사고 75·81).

그리고 실명만의 문제가 아니다. 이 저장소는 **공개**이고, 나가면 안 되는 것이 넷이다.
넷을 한자리에서 본다 — 따로 두면 그중 하나만 검사되는 상태가 온다.

무엇을 보는가
-------------
1. **운영자 실명** — 한글 표기
2. **인증키** — `serviceKey`·`api_key` 류에 **문자열 리터럴이 직접 박힌 것**
3. **개인 이메일 주소**
4. **로컬 절대경로** — `C:\\Users\\<이름>\\...` 은 기계의 계정명을 그대로 흘린다

**git 이 추적하는 파일만 본다.** 무시되는 것(`config.py` · `_preview/`)은 안 나가므로
검사 대상이 아니다 — **나가지 않는 것을 잡으면 오탐이고, 오탐은 검사를 죽인다**(§3-5).

이 파일 자신에 대하여
---------------------
**금칙어를 소스에 그대로 적으면 이 파일이 스스로에게 걸린다.** 그래서 코드포인트로
조립한다. 읽기 나쁘지만 **자기 자신을 통과시키려고 검사 대상에서 빼는 것보다 낫다** —
예외를 한 번 열면 그 예외가 다음에도 열린다.

닿지 않는 곳
------------
· **이름을 아는 것만 찾는다.** 다른 형태(로마자 이름·별명·손글씨 이미지)는 못 본다.
· **이미지 안의 글자를 못 본다.** `assets/og.png` 같은 것은 사람이 눈으로 본다
  (2026-09-01 실측: 카드 원본 `_og/card.html` 에 이름 없음 · 렌더 결과도 눈으로 확인).
· **git 이력은 안 본다.** 과거 커밋에 남은 것은 이 검사가 못 지운다 —
  지우려면 이력을 다시 쓰는 일이고 그것은 운영자 판단이다.
· 인증키 검사는 **이름이 키처럼 생긴 변수**만 본다. 이름 없이 흘린 문자열은 못 잡는다.

  python analysis/check_private.py
  python analysis/check_private.py --selftest
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HUB = os.path.normpath(os.path.join(ROOT, "..", "jisangj03-dev.github.io"))

# 실명 — 코드포인트로 조립한다(위 「이 파일 자신에 대하여」).
_NAME = "".join(chr(c) for c in (0xC815, 0xC9C0, 0xC0C1))
# 개인 이메일 — 같은 이유로 조립한다.
_MAIL = "jisangj03" + chr(0x40) + "gmail.com"

KEYISH = re.compile(
    r"""(?ix)
    \b(service[_-]?key|api[_-]?key|apikey|secret|token|password|passwd|access[_-]?key)
    \s*[:=]\s*
    (?P<q>['"])(?P<v>[^'"\n]{12,})(?P=q)
    """
)
# 자리표시자는 유출이 아니다 — 「여기에 키를 넣어라」는 문서다.
PLACEHOLDER = re.compile(
    r"(?i)^(x+|y+|<.*>|\{.*\}|your[_-]?|여기|보관|例|example|dummy|placeholder|"
    r"발급받|환경변수|env|os\.environ|config\.|\.\.\.|없음|none|null)"
)
LOCALPATH = re.compile(r"[A-Za-z]:[\\/]Users[\\/][^\s\"'<>|:*?\r\n]{1,40}")

TEXT_EXT = {
    ".md", ".markdown", ".html", ".htm", ".txt", ".yml", ".yaml", ".json",
    ".py", ".css", ".js", ".cff", ".csv", ".xml", ".toml", ".ini", ".sh",
}


def tracked(root):
    """git 이 추적하는 파일만 낸다. 무시되는 것은 안 나가므로 대상이 아니다."""
    try:
        out = subprocess.run(["git", "-C", root, "ls-files", "-z"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             timeout=60)
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return [p for p in out.stdout.decode("utf-8", "replace").split("\0") if p]


def scan_text(rel, text):
    """(종류, 줄번호, 발췌) 목록."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if _NAME in line:
            hits.append(("실명", i, line.strip()[:90]))
        if _MAIL in line:
            hits.append(("이메일", i, line.strip()[:90]))
        for m in KEYISH.finditer(line):
            v = m.group("v")
            if not PLACEHOLDER.match(v):
                hits.append(("인증키", i, f"{m.group(1)} = <{len(v)}자 리터럴>"))
        for m in LOCALPATH.finditer(line):
            hits.append(("로컬경로", i, m.group(0)[:70]))
    return hits


def scan_repo(root, name):
    """(발견목록, 분모). **분모를 같이 낸다** — 「0건」 옆에 「몇 건 검사」가 없으면
    0이 통과처럼 보인다(사고 77)."""
    files = tracked(root)
    if files is None:
        return None, None
    found, n = [], 0
    for rel in files:
        if os.path.splitext(rel)[1].lower() not in TEXT_EXT:
            continue
        p = os.path.join(root, rel)
        if not os.path.isfile(p):
            continue
        n += 1
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                t = f.read()
        except Exception:
            continue
        # 이 파일 자신은 금칙어를 조립해 들고 있다 — 조립된 것은 소스에 안 보인다.
        for kind, ln, snip in scan_text(rel, t):
            found.append((f"{name}/{rel}:{ln}", kind, snip))
    return found, n


# 실패로 볼 것과 경고로 볼 것을 가른다.
#   실명·이메일·인증키 — **나가면 되돌릴 수 없다.** 실패다.
#   로컬 절대경로     — 작업 폴더를 적는 것이 그 문서의 일일 수 있다(`CLAUDE.md` 가 그렇다).
#                      계정명이 흘러도 그것만으로 위험이 되진 않는다. **경고**로 낸다.
#   **오탐을 실패로 내면 그 검사가 먼저 무시당한다**(§3-5).
HARD = ("실명", "이메일", "인증키")


def report():
    rc = 0
    for root, name in ((ROOT, "인천"), (HUB, "허브")):
        found, n = scan_repo(root, name)
        if found is None:
            why = "저장소가 없다" if not os.path.isdir(root) else "git 이 안 돈다"
            print(f"  **모름**  {name} — {why}. **통과로 세지 않는다.**")
            rc = 1
            continue
        hard = [f for f in found if f[1] in HARD]
        soft = [f for f in found if f[1] not in HARD]
        head = "**유출**" if hard else ("경고" if soft else "통과")
        print(f"  {head:8} {name} — 유출 {len(hard)}건 · 경고 {len(soft)}건"
              f" / 추적 텍스트 파일 {n}개 검사")
        for where, kind, snip in hard[:20]:
            print(f"           FAIL [{kind}] {where}  {snip}")
        for where, kind, snip in soft[:8]:
            print(f"           WARN [{kind}] {where}  {snip}")
        if hard:
            rc = 1
    if rc == 0:
        print("\n실명 · 개인 이메일 · 인증키 — 셋 다 0건.")
        print("**이미지 안의 글자는 이 검사가 못 본다.** 그건 사람이 눈으로 본다.")
    return rc


# ----------------------------------------------------------------- 인수시험
def selftest():
    """**잡는 쪽과 안 잡는 쪽을 같이 친다.** 통과 픽스처만 두면 사고 26 이다."""
    cases = []

    def chk(label, got, want):
        cases.append((label, got == want, (got, want)))

    # 잡아야 하는 것 넷
    chk("실명을 잡는다", [k for k, _, _ in scan_text("a", "검수 · 발행: " + _NAME)], ["실명"])
    chk("이메일을 잡는다", [k for k, _, _ in scan_text("a", "문의 " + _MAIL)], ["이메일"])
    chk("박힌 인증키를 잡는다",
        [k for k, _, _ in scan_text("a", "service" + 'Key = "aZ90kLmn3QpR7sT1uV"')], ["인증키"])
    chk("로컬 절대경로를 잡는다",
        [k for k, _, _ in scan_text("a", "경로는 C:" + chr(92) + r"Users\hong 다")], ["로컬경로"])

    # 안 잡아야 하는 것 — 오탐이 검사를 죽인다
    chk("자리표시자는 안 잡는다",
        scan_text("a", "service" + 'Key = "여기에 발급받은 키를 넣는다"'), [])
    chk("환경변수 참조는 안 잡는다",
        scan_text("a", "api" + '_key = "os.environ 에서 받는다"'), [])
    chk("짧은 값은 안 잡는다", scan_text("a", "to" + 'ken = "abc"'), [])
    chk("보통 문장은 안 잡는다",
        scan_text("a", "인천항 컨테이너 부두는 신항·남항으로 나뉜다."), [])
    chk("상대경로는 안 잡는다", scan_text("a", "analysis/build_series_chart.py"), [])

    # **이 파일 자신이 통과해야 한다** — 금칙어를 소스에 안 적었다는 확인이다.
    with open(os.path.abspath(__file__), encoding="utf-8") as f:
        me = f.read()
    chk("이 검사기 자신이 깨끗하다", scan_text("self", me), [])

    # 없는 저장소는 「모름」
    chk("없는 저장소는 모름을 낸다",
        scan_repo(os.path.join(tempfile.mkdtemp(), "없다"), "t")[0], None)

    bad = 0
    for label, ok, got in cases:
        print(f"  {label:34} {'OK' if ok else '**FAIL** ' + repr(got)[:110]}")
        if not ok:
            bad += 1
    print(f"\n  실패 {bad}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description="공개 저장소에 나가면 안 되는 것을 본다.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    return selftest() if a.selftest else report()


if __name__ == "__main__":
    sys.exit(main())

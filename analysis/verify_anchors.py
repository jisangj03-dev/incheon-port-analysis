"""정지선 앵커 검사 — 기록된 해시를 실행되는 검사로 바꾼다.

왜 있는가
---------
앵커 3건의 SHA-256이 `docs/다음세션_인수인계.md`에만 적혀 있었다.
그 파일은 v5.0 확정과 함께 삭제 대상이었고, 지우면 앵커가 같이 사라질 뻔했다.
특히 `recheck_2025_direction_20260804.csv`(회귀 앵커 재수집분, 사고 7)의 해시는
저장소 어디에도 다른 사본이 없었다.

사고 28이 말한 것 그대로다 — **정지선이 문서에만 있으면 「지켜졌는가」에 답할 수 없다.**
그래서 값을 옮겨 적는 대신 검사로 만들었다. 이제 답은 기억이 아니라 종료코드다.

무엇을 보는가
-------------
  1. 수정 금지 파일 3종의 SHA-256이 앵커와 일치하는가. **없어도, 달라도 위반이다** —
     둘 다 exit 1.
  2. 열람 금지 파일 2종이 제자리에 있는가. **내용은 읽지 않는다** — 존재와 크기만 본다.
     (읽는 순간 이 스크립트가 정지선을 어긴다.)

[2026-09-28 제안] 봉인 파일이 「이 저장소만 clone한 기계」에서 항상 없는 문제
------------------------------------------------------------------------
`_probe_dump.txt`는 `.gitignore` 대상이고 생성 스크립트가 없다 — **운영자의
로컬 기계에만 있는 사본**이다. 매번 새로 뜨는 클라우드 컨테이너(주간물동량
루틴 등)는 이 파일을 원천적으로 가진 적이 없다. 지금까지는 그 부재가 다른
위반(해시 불일치·앵커 자체 소실)과 똑같이 커밋을 막았다 — **환경 한계와
정지선 위반을 구별하지 못했다.**

이 결함을 고치되 **검사를 끄거나 약하게 만들지 않는다.** 이 저장소의 다른
장치(`check_refs.py`·`check_claims.py`)가 이미 같은 문제를 겪고 있고, 같은
관례로 푼다 — 운영자 홈의 `OneDrive\\문서\\본부`가 있는지로 「이 기계가
운영자의 실제 기계인가」를 가른다. **그 관례를 그대로 가져온다**(새 기전을
만들지 않는다).

- 앵커 3건의 소실·불일치는 **기계와 무관하게 항상 위반**이다(exit 1) — 이 셋은
  전부 git으로 커밋돼 있어 어떤 clone에도 있어야 정상이고, 없다는 것 자체가
  이상 신호다. **여기는 하나도 안 물렀다.**
- 봉인 파일이 없을 때:
  - **운영자의 기계(위 본부 폴더가 있다)** — 원래 있어야 할 파일이 없다는 뜻이므로
    **그대로 위반**이다(exit 1). **여기도 안 물렀다.**
  - **이 저장소만 clone한 기계(본부 폴더가 없다)** — 이 기계는 애초에 이 파일을
    가져 본 적이 없으므로 부재가 삭제·조작의 증거가 아니다. **exit 3**(새 코드 —
    "환경 한계", 위반이 아니다)으로 갈라 알린다. `hook_stopline.py`가 이 코드만
    막지 않는다.

**해시 대조로 못 바꾸는 이유.** 봉인 파일은 "내용을 안 읽는다"가 설계 목적이다
(위 §2, `selftest()`가 시험한다) — 해시를 내려면 바이트를 읽어야 하므로 그 자체가
이 파일의 존재 이유(열람 금지)와 부딪힌다. 그래서 이번 제안은 해시가 아니라
**"이 기계가 애초에 이 파일을 가질 수 있는 기계인가"**를 가르는 쪽을 택했다.

**아직 못 푸는 것.** 운영자 기계에서 이 파일이 사라진 경우와, 그 기계에
`본부` 폴더가 우연히 없어진 경우를 이 코드는 구별하지 못한다 — 후자도 똑같이
"이 저장소만 clone한 기계"로 오판해 exit 3을 낸다. 이 폴더는 저장소보다 오래
있어 온 로컬 고정물이라 가능성은 낮다고 보지만, **0은 아니다.** 이 한계는
`check_refs.py`·`check_claims.py`가 이미 안고 있는 것과 같다.

사용
----
  python analysis/verify_anchors.py

종료코드 0 = 전부 일치 / 1 = 정지선 위반 가능(항상 막는다) /
3 = 환경 한계 — 이 기계에서 봉인 파일을 잴 수 없다(막지 않는다. 사고 26 — 모름은 통과가 아니다).

정지선-집행: §4 — 앵커 3건 수정·정렬·재저장 금지 / 봉인 2건 열람 금지
정지선-명제: 앵커 3건의 SHA-256이 기록값과 같고, 이 코드가 봉인 2건의 내용을 안 읽는다
정지선-한계: 다른 도구·사람이 앵커를 고치는 것은 못 막는다. 커밋 시점에 **사후로** 알려 줄 뿐이다.
  「이 저장소만 clone한 기계」 판정은 `본부` 폴더 유무로만 가르므로, 그 폴더가
  없어진 운영자 기계를 오판할 수 있다(위 "아직 못 푸는 것").
"""

import contextlib
import hashlib
import io
import os
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# check_refs.py·check_claims.py 와 같은 관례 — 새 기전을 만들지 않는다.
HQ = Path(os.path.expanduser("~")) / "OneDrive" / "문서" / "본부"

# 수정·정렬·재저장 금지. 값은 CRLF 상태의 디스크 바이트로 측정됐다(.gitattributes가 csv를 CRLF로 고정하는 이유).
ANCHORS = {
    "analysis/container_2025_direction.csv":
        "EA17A4CA45FD59B308E558D1A01C9F9E7D66B885C1DEF13A1112B72BC8EDD954",
    "analysis/container_2026_direction.csv":
        "DF63A87327A0E34A97B08CB29F07466B67FE532059D07110A3E40072F6445B45",
    "analysis/probe/recheck_2025_direction_20260804.csv":
        "CCD319B157274905975A79C02561FCBE081FB392F8AA55734FF5FED8CCEF774B",
}

# 열람 금지. 존재만 확인한다.
SEALED = ["_probe_dump.txt", "analysis/probe/probe_2026_raw.csv"]


def repo_only_clone():
    """이 기계가 본부 폴더(운영자 로컬 고정물)를 안 가졌는가 — check_refs.py·check_claims.py 와 같은 판정."""
    return not HQ.is_dir()


def decide_exit(anchor_violation, sealed_violation, sealed_env_limited):
    """세 신호만으로 종료코드를 정하는 순수 함수 — 인수시험이 파일 없이 이 함수만 친다.

    앵커 위반이나 「진짜」 봉인 위반(운영자 기계에서 없어짐)은 늘 1이다 —
    환경 한계(exit 3)가 그것들을 절대 가리지 않는다.
    """
    if anchor_violation or sealed_violation:
        return 1
    if sealed_env_limited:
        return 3
    return 0


def main():
    anchor_violation = False
    sealed_violation = False
    sealed_env_limited = False
    only_clone = repo_only_clone()

    print("── 수정 금지 앵커 (SHA-256) ──")
    for rel, want in ANCHORS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"  [없음] {rel}")
            anchor_violation = True
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        ok = got == want
        anchor_violation = anchor_violation or (not ok)
        print(f"  [{'일치' if ok else '불일치'}] {rel}  ({p.stat().st_size} B)")
        if not ok:
            print(f"           기대 {want}")
            print(f"           실측 {got}")

    print("── 열람 금지 (존재만 확인. 내용은 읽지 않는다) ──")
    for rel in SEALED:
        p = ROOT / rel
        if p.exists():
            print(f"  [제자리] {rel}  ({p.stat().st_size} B)")
            continue
        if only_clone:
            print(f"  [모름] {rel} — 이 저장소만 clone한 기계에서는 잴 수 없다. 통과로 치지 않는다.")
            sealed_env_limited = True
        else:
            print(f"  [없음] {rel}")
            sealed_violation = True

    code = decide_exit(anchor_violation, sealed_violation, sealed_env_limited)
    print()
    if code == 1:
        print("정지선 위반 가능 — 커밋하지 마라.")
    elif code == 3:
        print("환경 한계 — 이 기계에서는 봉인 파일을 잴 수 없다(모름). 위반이 아니다.")
    else:
        print(f"앵커 {len(ANCHORS)}건 일치 · 봉인 파일 {len(SEALED)}건 제자리.")
    sys.exit(code)


def selftest():
    """「봉인 파일의 내용을 안 읽는다」와 「종료코드 분기가 옳다」를 함께 시험한다.

    지금까지 그 보장은 주석 한 줄과 「코드가 우연히 안 읽는다」였다.
    누가 read_bytes 한 줄만 넣어도 아무도 못 잡는다 — 사고 26(장치의 존재는 검사의 수행이 아니다).
    그래서 실제 읽기 경로를 가로채 확인한다.

    양방향으로 본다(사고 34) — ① 봉인 파일은 **안 열려야** 하고
    ② 앵커 파일은 **열려야** 한다. ②가 없으면 main()이 아무것도 안 해도 통과한다.
    """
    import builtins
    import pathlib

    ok = True

    print("── 인수시험: 종료코드 분기 (decide_exit — 파일 없이 순수 함수만) ──")
    cases = [
        # (anchor_violation, sealed_violation, sealed_env_limited) -> 기대 종료코드
        ((False, False, False), 0),
        ((False, False, True), 3),   # 환경 한계만 있으면 안 막는다
        ((False, True, False), 1),   # 진짜 봉인 위반은 막는다
        ((False, True, True), 1),    # 진짜 위반이 섞이면 환경 한계가 안 가린다
        ((True, False, False), 1),   # 앵커 위반은 늘 막는다
        ((True, False, True), 1),    # 앵커 위반은 환경 한계로 안 가려진다
    ]
    for args, want in cases:
        got = decide_exit(*args)
        hit = got == want
        ok = ok and hit
        print("  %s decide_exit%s -> %s (기대 %s)" % ("OK  " if hit else "FAIL", args, got, want))

    opened = []
    real_open = builtins.open
    real_rb = pathlib.Path.read_bytes
    real_rt = pathlib.Path.read_text

    def note(p):
        try:
            opened.append(str(pathlib.Path(p).resolve()))
        except Exception:
            opened.append(str(p))

    def spy_open(file, *a, **k):
        note(file)
        return real_open(file, *a, **k)

    def spy_rb(self, *a, **k):
        note(self)
        return real_rb(self, *a, **k)

    def spy_rt(self, *a, **k):
        note(self)
        return real_rt(self, *a, **k)

    builtins.open, pathlib.Path.read_bytes, pathlib.Path.read_text = spy_open, spy_rb, spy_rt
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                main()
            except SystemExit:
                pass
    finally:
        builtins.open, pathlib.Path.read_bytes, pathlib.Path.read_text = real_open, real_rb, real_rt

    print("── 인수시험: 봉인 파일 열람 ──")
    for rel in SEALED:
        target = str((ROOT / rel).resolve())
        hit = target in opened
        print(f"  {'FAIL' if hit else 'OK  '} 안 읽는다: {rel}")
        ok = ok and not hit

    for rel in ANCHORS:
        target = str((ROOT / rel).resolve())
        hit = target in opened
        print(f"  {'OK  ' if hit else 'FAIL'} 읽는다(대조 대상): {rel}")
        ok = ok and hit

    print("통과" if ok else "실패")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    main()

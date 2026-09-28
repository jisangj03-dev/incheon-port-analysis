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

[2026-09-28 제안 · v2 — 첫 시도를 채팅이 되짚었다] 봉인 파일 부재 판정
------------------------------------------------------------------
`_probe_dump.txt`는 `.gitignore` 대상이고 생성 스크립트가 없다 — **운영자의
로컬 기계에만 있는 사본**이다. 매번 새로 뜨는 클라우드 컨테이너(주간물동량
루틴 등)는 이 파일을 원천적으로 가진 적이 없다. 지금까지는 그 부재가 다른
위반(해시 불일치·앵커 자체 소실)과 똑같이 커밋을 막았다 — **환경 한계와
정지선 위반을 구별하지 못했다.**

**첫 시도(운영자 홈의 `본부` 폴더 유무로 가른다)는 방향이 거꾸로였다** —
채팅이 잡았다. 그 폴더는 정리·보관 계획이 있어 지워질 수 있고, 지워지면
**운영자의 실제 기계에서도** 봉인 파일 부재가 「이 저장소만 clone한
기계」로 오판돼 검사가 조용히 풀린다. **실패 방향이 안전한 쪽이 아니었다** —
확인 안 됨(폴더 없음)이 곧바로 "막지 않음"으로 이어졌다.

그래서 기본값을 뒤집는다:

- **기본값은 위반(exit 1, 막는다).** 아무 신호도 없으면 이 기계가 클라우드인지
  운영자 기계인지 모르고, **모르면 막는다** — 사고 26(모름은 통과가 아니다)과
  같은 원칙이다.
- **클라우드임을 적극적으로 확인했을 때만** exit 3("환경 한계" — 위반 아님)
  으로 가른다. 확인 수단은 Claude Code 자신이 원격/클라우드 실행에 심는
  환경변수다(`is_confirmed_cloud()`) — 사람이 흉내 낼 수는 있지만, **운영자의
  실제 기계에서 우연히 켜지는 값이 아니다.** 이 신호가 틀렸을 때의 위험도
  비대칭이다: 잘못 믿으면 "덜 들키는 삭제"가 아니라 "더 깐깐한 차단"(클라우드가
  아닌데 클라우드로 오판 → 여전히 exit 3은 앵커 위반이 섞이면 절대 못 가린다,
  아래 `decide_exit` 참고)이지, 그 반대(운영자 기계의 진짜 삭제를 클라우드로
  오판해 놓침)가 아니다 — `본부` 폴더 유무만으로 판정하던 첫 시도가 정확히
  그 반대 방향의 위험을 안고 있었다.
- 앵커 3건의 소실·불일치는 **기계·환경 신호와 무관하게 항상 위반**이다
  (exit 1) — 여기는 첫 시도와 마찬가지로 하나도 안 물렀다.

**해시 대조로 못 바꾸는 이유.** 봉인 파일은 "내용을 안 읽는다"가 설계 목적이다
(위 §2, `selftest()`가 시험한다) — 해시를 내려면 바이트를 읽어야 하므로 그 자체가
이 파일의 존재 이유(열람 금지)와 부딪힌다. 그래서 이번 제안도 해시가 아니라
**"이 기계가 클라우드임을 적극적으로 확인할 수 있는가"**를 가르는 쪽을 택했다.

**아직 못 푸는 것.** `is_confirmed_cloud()`가 보는 환경변수는 Claude Code가
스스로 심는 값이라 그 값 자체가 조작·위조됐을 가능성은 이 코드가 못 잡는다.
다만 그 경우도 **기본값 방향과 반대로 작동해야 위험해진다** — 즉 "클라우드가
아닌데 클라우드로 위조"해야 검사가 풀리므로, 값이 그냥 없어지거나 깨지는
사고(첫 시도가 겪은 것과 같은 종류)로는 안 뚫린다.

사용
----
  python analysis/verify_anchors.py

종료코드 0 = 전부 일치 / 1 = 정지선 위반 가능(항상 막는다, 확인 안 되면 이쪽이 기본값) /
3 = 클라우드임을 적극적으로 확인함 — 봉인 파일 검사를 생략한다(막지 않는다).

정지선-집행: §4 — 앵커 3건 수정·정렬·재저장 금지 / 봉인 2건 열람 금지
정지선-명제: 앵커 3건의 SHA-256이 기록값과 같고, 이 코드가 봉인 2건의 내용을 안 읽는다
정지선-한계: 다른 도구·사람이 앵커를 고치는 것은 못 막는다. 커밋 시점에 **사후로** 알려 줄 뿐이다.
  클라우드 판정은 Claude Code가 심는 환경변수를 신뢰한다 — 그 값 자체의 위조는
  못 잡는다(위 "아직 못 푸는 것").
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

# Claude Code가 원격/클라우드 실행에 스스로 심는 값들 — 실측(2026-09-28,
# 이 세션 자신의 `env`)으로 확인한 이름들이다. 하나라도 그 값이면 "적극적으로
# 확인됨"으로 본다. **기본값은 이 목록에 없다 — 아무 신호가 없으면 위반이다.**
_CLOUD_ENV_TRUE = ("CLAUDE_CODE_REMOTE",)
_CLOUD_ENV_NONEMPTY = ("CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE",)
_CLOUD_CONTAINER_MARKER = "claude_code_remote"


def is_confirmed_cloud(env=None):
    """이 기계가 클라우드/원격 컨테이너임을 **적극적으로 확인한다.**

    확인 안 되면 False — 그것이 기본값이고, `decide_exit`에서 위반(exit 1) 쪽으로
    떨어진다. 「본부 폴더가 없다」처럼 소극적 신호(무언가의 부재)로 클라우드를
    추론하지 않는다 — 그 폴더는 운영자 기계에서도 없어질 수 있어 실패 방향이
    거꾸로였다(첫 시도의 결함). 여기서는 **있어야 참이 되는 값**만 본다.
    """
    env = os.environ if env is None else env
    for k in _CLOUD_ENV_TRUE:
        if env.get(k, "").strip().lower() == "true":
            return True
    for k in _CLOUD_ENV_NONEMPTY:
        if env.get(k, "").strip():
            return True
    if _CLOUD_CONTAINER_MARKER in env.get("CLAUDE_CODE_CONTAINER_ID", ""):
        return True
    return False


def decide_exit(anchor_violation, sealed_violation, sealed_env_limited):
    """네 신호만으로 종료코드를 정하는 순수 함수 — 인수시험이 파일 없이 이 함수만 친다.

    앵커 위반이나 「진짜」 봉인 위반(클라우드로 확인 안 된 기계에서 없어짐)은
    늘 1이다 — 환경 한계(exit 3)가 그것들을 절대 가리지 않는다.
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
    cloud = is_confirmed_cloud()

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
        if cloud:
            print(f"  [생략] {rel} — 클라우드로 확인됨. 이 파일은 검사하지 않는다.")
            sealed_env_limited = True
        else:
            print(f"  [없음] {rel}")
            sealed_violation = True

    code = decide_exit(anchor_violation, sealed_violation, sealed_env_limited)
    print()
    if code == 1:
        print("정지선 위반 가능 — 커밋하지 마라.")
    elif code == 3:
        print("★★★ 봉인 파일 검사 생략(클라우드) — 위반이 아니다. 앵커 3건은 그대로 검사됐다. ★★★")
    else:
        print(f"앵커 {len(ANCHORS)}건 일치 · 봉인 파일 {len(SEALED)}건 제자리.")
    sys.exit(code)


def selftest():
    """「봉인 파일의 내용을 안 읽는다」·「클라우드 판정이 옳다」·「종료코드 분기가 옳다」를 함께 시험한다.

    지금까지 그 보장은 주석 한 줄과 「코드가 우연히 안 읽는다」였다.
    누가 read_bytes 한 줄만 넣어도 아무도 못 잡는다 — 사고 26(장치의 존재는 검사의 수행이 아니다).
    그래서 실제 읽기 경로를 가로채 확인한다.

    양방향으로 본다(사고 34) — ① 봉인 파일은 **안 열려야** 하고
    ② 앵커 파일은 **열려야** 한다. ②가 없으면 main()이 아무것도 안 해도 통과한다.
    """
    import builtins
    import pathlib

    ok = True

    print("── 인수시험: 클라우드 확인 — 기본값은 False(위반 쪽)다 ──")
    cloud_cases = [
        ({}, False),
        ({"CLAUDE_CODE_REMOTE": "false"}, False),
        ({"CLAUDE_CODE_REMOTE": ""}, False),
        ({"CLAUDE_CODE_REMOTE": "true"}, True),
        ({"CLAUDE_CODE_REMOTE": "TRUE"}, True),
        ({"CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE": "cloud_default"}, True),
        ({"CLAUDE_CODE_CONTAINER_ID": "container_x--claude_code_remote--y"}, True),
        ({"HOME": "/root"}, False),  # 아무 관련 없는 값은 클라우드로 안 읽는다
    ]
    for env, want in cloud_cases:
        got = is_confirmed_cloud(env)
        hit = got == want
        ok = ok and hit
        print("  %s is_confirmed_cloud(%s) -> %s (기대 %s)" % ("OK  " if hit else "FAIL", env, got, want))

    print("── 인수시험: 종료코드 분기 (decide_exit — 파일 없이 순수 함수만) ──")
    cases = [
        # (anchor_violation, sealed_violation, sealed_env_limited) -> 기대 종료코드
        ((False, False, False), 0),
        ((False, False, True), 3),   # 환경 한계만 있으면 안 막는다
        ((False, True, False), 1),   # 진짜 봉인 위반은 막는다
        ((False, True, True), 1),    # 진짜 위반이 섞이면 환경 한계가 안 가린다
        ((True, False, False), 1),   # 앵커 위반은 늘 막는다
        ((True, False, True), 1),    # 앵커 위반은 클라우드 확인으로 안 가려진다
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

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
  1. 수정 금지 파일 3종의 SHA-256이 앵커와 일치하는가.
  2. 열람 금지 파일 2종이 제자리에 있는가. **내용은 읽지 않는다** — 존재와 크기만 본다.
     (읽는 순간 이 스크립트가 정지선을 어긴다.)

사용
----
  python analysis/verify_anchors.py

종료코드 0 = 전부 일치 / 1 = 불일치(정지선 위반 가능) / 2 = 대상 파일 없음.
"""

import hashlib
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


def main():
    bad = missing = 0

    print("── 수정 금지 앵커 (SHA-256) ──")
    for rel, want in ANCHORS.items():
        p = ROOT / rel
        if not p.exists():
            print(f"  [없음] {rel}")
            missing += 1
            continue
        got = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        ok = got == want
        bad += (not ok)
        print(f"  [{'일치' if ok else '불일치'}] {rel}  ({p.stat().st_size} B)")
        if not ok:
            print(f"           기대 {want}")
            print(f"           실측 {got}")

    print("── 열람 금지 (존재만 확인. 내용은 읽지 않는다) ──")
    for rel in SEALED:
        p = ROOT / rel
        if p.exists():
            print(f"  [제자리] {rel}  ({p.stat().st_size} B)")
        else:
            print(f"  [없음] {rel}")
            missing += 1

    print()
    if missing:
        print(f"대상 파일 {missing}건 없음 — 검사 불성립.")
        sys.exit(2)
    if bad:
        print(f"앵커 {bad}건 불일치 — 정지선 위반 가능. 커밋하지 마라.")
        sys.exit(1)
    print(f"앵커 {len(ANCHORS)}건 일치 · 봉인 파일 {len(SEALED)}건 제자리.")


if __name__ == "__main__":
    main()

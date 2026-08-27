"""치환 가드 — 일치 개수가 정확히 1이 아니면 쓰지 않는다.

왜 파일인가
-----------
지침 정지선 「문서 수정은 전문 덮어쓰기 + 일치 개수 가드」는 사고 13에서 나왔다.
가드 없는 치환은 **아무 일도 안 하고 "완료"만 보고한다.**
그런데 그 가드는 여태 사람이 기억하는 형태로만 존재했다 — 사고 22가 말한 실패 구조 그대로다.
정지선을 파일로 내린다. 이제 "가드를 걸었는가"는 기억이 아니라 실행 기록으로 답한다.

무엇을 보장하는가
-----------------
  1. 치환 전 일치 개수를 세고, **1이 아니면 종료코드 2로 중단한다.** 파일은 손대지 않는다.
  2. 쓰기는 바이트 왕복(ReadAllBytes → 치환 → WriteAllBytes)이다. BOM·줄끝을 건드리지 않는다. (사고 12)
  3. 쓰기 전후 SHA-256과 바이트 수를 출력한다. 앵커 대조가 가능해야 한다. (사고 9)
  4. `--dry-run`이 기본이 아니다. 그러나 `--check`만 주면 세기만 하고 끝난다.

사용
----
  python analysis/safe_edit.py <파일> --old <옛문자열> --new <새문자열> [--check]
  python analysis/safe_edit.py <파일> --old-file a.txt --new-file b.txt
  python analysis/safe_edit.py --selftest

종료코드 0=치환됨(또는 --check 통과) / 2=가드 발동(중단) / 1=오류.

정지선-집행: §4 — 문서 치환은 safe_edit로만. 일치 개수 ≠ 1이면 안 쓴다
정지선-명제: 이 도구를 거친 치환은 일치 1건일 때만 파일을 바꾸고 전후 SHA-256을 남긴다
정지선-한계: **이 도구를 안 거치는 편집은 못 막는다.** Write·Edit·리다이렉션은 그대로 통한다
"""

import argparse
import hashlib
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def replace_once(path: Path, old: str, new: str, check_only: bool = False, enc: str = "utf-8"):
    """일치 개수가 1일 때만 치환한다. 반환: (종료코드, 메시지)"""
    raw = path.read_bytes()
    try:
        text = raw.decode(enc)
    except UnicodeDecodeError as e:
        return 1, f"[오류] 디코드 실패({enc}): {e}"

    n = text.count(old)
    head = f"{path}  {len(raw)} B  SHA-256 {digest(raw)[:16]}…"
    if n != 1:
        why = "대상 문자열이 없다" if n == 0 else f"대상 문자열이 {n}곳이다"
        return 2, (
            f"[가드 발동] {head}\n"
            f"  일치 개수 = {n} (요구: 1) — {why}. **쓰지 않았다.**\n"
            f"  찾은 것: {old[:70]!r}"
        )

    if check_only:
        return 0, f"[통과] {head}\n  일치 개수 = 1. --check 이므로 쓰지 않았다."

    out = text.replace(old, new, 1).encode(enc)
    path.write_bytes(out)
    return 0, (
        f"[치환 1건] {path}\n"
        f"  전: {len(raw)} B  SHA-256 {digest(raw)}\n"
        f"  후: {len(out)} B  SHA-256 {digest(out)}"
    )


def selftest() -> bool:
    ok = True
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.md"

        # ① 정상 — 1건이면 치환하고 바이트가 바뀐다.
        p.write_bytes("가 나 다\n".encode("utf-8"))
        code, _ = replace_once(p, "나", "라")
        got = p.read_bytes().decode("utf-8")
        good = (code == 0 and got == "가 라 다\n")
        ok &= good
        print(f"  {'✓' if good else '✗'} 1건 → 치환 (code={code})")

        # ② 0건 — 중단하고 파일이 그대로여야 한다. 이게 사고 13의 실패 지점이다.
        before = p.read_bytes()
        code, _ = replace_once(p, "없는문자열", "X")
        same = p.read_bytes() == before
        ok &= (code == 2 and same)
        print(f"  {'✓' if code == 2 and same else '✗'} 0건 → 중단·무변경 (code={code}, 무변경={same})")

        # ③ 2건 — 중단. 어느 쪽을 고칠지 코드가 결정하면 안 된다.
        p.write_bytes("가 가\n".encode("utf-8"))
        before = p.read_bytes()
        code, _ = replace_once(p, "가", "X")
        same = p.read_bytes() == before
        ok &= (code == 2 and same)
        print(f"  {'✓' if code == 2 and same else '✗'} 2건 → 중단·무변경 (code={code}, 무변경={same})")

        # ④ BOM·CRLF 보존 — 바이트 왕복이므로 건드리지 않아야 한다. (사고 12)
        p.write_bytes("\ufeff가\r\n나\r\n".encode("utf-8"))
        replace_once(p, "나", "다")
        raw = p.read_bytes()
        keep = raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw
        ok &= keep
        print(f"  {'✓' if keep else '✗'} BOM+CRLF 보존 ({raw!r})")
    return ok


def main():
    if "--selftest" in sys.argv:
        print("── 치환 가드 인수시험 ──")
        sys.exit(0 if selftest() else 1)

    ap = argparse.ArgumentParser(description="일치 개수 1일 때만 치환한다.")
    ap.add_argument("path")
    ap.add_argument("--old")
    ap.add_argument("--new", default=None)
    ap.add_argument("--old-file")
    ap.add_argument("--new-file")
    ap.add_argument("--check", action="store_true", help="세기만 하고 쓰지 않는다")
    ap.add_argument("--encoding", default="utf-8")
    a = ap.parse_args()

    old = Path(a.old_file).read_text(encoding=a.encoding) if a.old_file else a.old
    new = Path(a.new_file).read_text(encoding=a.encoding) if a.new_file else a.new
    if old is None:
        sys.exit("[오류] --old 또는 --old-file 필요")
    if new is None and not a.check:
        sys.exit("[오류] --new 또는 --new-file 필요 (세기만 하려면 --check)")

    code, msg = replace_once(Path(a.path), old, new or "", a.check, a.encoding)
    print(msg)
    sys.exit(code)


if __name__ == "__main__":
    main()

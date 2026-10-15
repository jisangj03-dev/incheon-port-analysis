# -*- coding: utf-8 -*-
"""예측 원장은 덧붙이기만 한다(정체성 전환 §3-4 F1). main 에 있는 원장의 행이 지금 파일의 앞부분과 한 글자도 다르면 실패.

  python tools-build/check_ledger.py              # origin/main 과 비교(CI 는 먼저 git fetch origin main)
  python tools-build/check_ledger.py --selftest
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGERS = ["data/forecast/incheon_container_teu.csv"]


def lines(text):
    return [l for l in text.replace("\r\n", "\n").split("\n") if l.strip()]


def compare(base_text, now_text):
    """(문제 목록, 기준 행 수, 지금 행 수). 기준이 없으면(새 원장) 문제 0."""
    if base_text is None:
        return [], 0, len(lines(now_text))
    b, n = lines(base_text), lines(now_text)
    bad = []
    for i, row in enumerate(b):
        if i >= len(n):
            bad.append(f"{i + 1}행이 지워졌다: {row}")
        elif n[i] != row:
            bad.append(f"{i + 1}행이 바뀌었다: {row!r} → {n[i]!r}")
    return bad, len(b), len(n)


def main_text(path, ref="origin/main"):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def run():
    fail = 0
    for p in LEDGERS:
        now = (ROOT / p).read_text(encoding="utf-8") if (ROOT / p).exists() else ""
        bad, nb, nn = compare(main_text(p), now)
        print(f"[원장] {p} — main {nb}줄 · 지금 {nn}줄 · 고침·지움 {len(bad)}건")
        for b in bad[:10]:
            print("   ", b)
        fail |= bool(bad)
    return 1 if fail else 0


def selftest():
    base = "issued,origin\n2026-10-14,2026-08\n"
    assert compare(base, base + "2026-11-14,2026-09\n")[0] == []          # 덧붙이기 = 통과
    assert compare(base, "issued,origin\n2026-10-15,2026-08\n")[0]       # 고침 = 실패
    assert compare(base, "issued,origin\n")[0]                            # 지움 = 실패
    assert compare(None, base)[0] == []                                   # 새 원장 = 통과
    print("check_ledger selftest OK (4)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else run())

"""프로브 — 연안(ocCt=2) 공컨테이너의 0은 언제부터인가.

**질문.** `/data/` 미관측 축 「연안 구간」의 남은 후보 둘 중 어느 쪽인가?
  ① 연안 **컨테이너**가 실제로 거의 없다
  ② 우리 소스의 해당 집계가 **비어 있다**

**방법.** 이미 갖고 있는 방향별 CSV 5개년을 **읽기만 해서** `ocCt=2` 행을 훑는다.
집계가 구조적으로 비어 있다면 **전 기간 0**이어야 한다. 한 해라도 값이 있으면 ②가 약해진다.

**답 (2026-08-28 실측).** **전 기간 0이 아니다.**
2022년과 2023년 초에는 값이 있었고, **2024년부터 2026년까지 전부 0이다.**
→ **②(집계가 비어 있다)는 약해졌다.** 같은 필드가 2022~2023에는 값을 냈다.

**그러나 ①로 확정되지 않는다.** 남은 대안이 최소 둘이다.
  - 2024년 어름에 **분류·집계 방식이 바뀌었을** 수 있다.
    (인천지방해양수산청 월별 통계는 「연안화물선 등에서 처리되는 컨테이너는
     **그 외 부두로 분류**」한다고 각주에 밝힌다 — 그런 종류의 변경일 수 있다.)
  - API가 특정 시점부터 해당 축을 안 채울 수도 있다.
**이 프로브는 그 둘을 가르지 못한다.**

──────────────────────────────────────────────────────────────────────
**절차 경고 — 이 관측을 다음 편의 선커밋 기준으로 쓰면 안 된다.**

여기서 **데이터를 이미 봤다.** 본 뒤에 기준을 세우면 그것이 §3-7이 막는 사후 기준이다.
연안 축으로 편을 열려면 **아직 안 본 구간**(예: 2021년 이전, 또는 향후 구간)에
질문 3개와 통과 조건을 **먼저** 커밋해야 한다.
이 파일은 그 사실을 남기려고 존재한다 — **관측 기록이지 기준이 아니다.**
──────────────────────────────────────────────────────────────────────

**정지선.** 이 스크립트는 CSV를 **읽기만 한다.** 앵커 3건은 수정·정렬·재저장 금지(§4)라
실행 전후 SHA-256 을 대조해 무변경을 스스로 증명한다.

    python analysis/probe/probe_10_coastal_zero.py
"""
from __future__ import annotations
import csv
import hashlib
import io
import os
import sys

# 운영자 콘솔(cp949)에서 출력이 터지지 않게 한다. **없으면 통과 문장의
# `—` 하나에 죽고, 죽은 종료코드를 다른 검사기가 판정으로 읽는다**
# (2026-09-02 실측 · `check_generated` 가 그것을 「낡았다」로 읽었다).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


FILES = [
    ("2022", "analysis/container_2022_direction.csv"),
    ("2023", "analysis/container_2023_direction.csv"),
    ("2024", "analysis/container_2024_direction.csv"),
    ("2025", "analysis/container_2025_direction.csv"),
    ("2026", "analysis/container_2026_direction.csv"),
]
VALUE_COLS = (
    "forEmpTeu", "korEmpTeu",
    "forEmp_10", "forEmp_20", "forEmp_40", "forEmp_99",
    "korEmp_10", "korEmp_20", "korEmp_40", "korEmp_99",
)


def num(s: str | None) -> float:
    s = (s or "").replace(",", "").strip()
    try:
        return float(s or 0)
    except ValueError:
        return 0.0


def sha(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest().upper()


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.chdir(root)

    present = [(y, p) for y, p in FILES if os.path.exists(p)]
    if not present:
        print("[중단] 방향별 CSV를 못 찾았다.")
        return 2
    before = {p: sha(p) for _y, p in present}

    print("== 프로브: 연안(ocCt=2) 공컨테이너의 0은 언제부터인가 ==")
    print("  ※ 읽기 전용. 앵커 파일은 수정·정렬·재저장 금지(§4).\n")
    print(f"  {'연도':<6}{'ocCt=2 행':>10}{'값 있는 달':>11}{'korEmpTeu 합':>14}{'forEmpTeu 합':>14}")
    print("  " + "-" * 55)

    last_nonzero = None
    per_year = {}
    for year, path in present:
        rows = list(csv.DictReader(io.open(path, encoding="utf-8-sig")))
        co = [r for r in rows if (r.get("ocCt") or "").strip() == "2"]
        months = set()
        kor = fore = 0.0
        for r in co:
            kor += num(r.get("korEmpTeu"))
            fore += num(r.get("forEmpTeu"))
            if any(num(r.get(c)) for c in VALUE_COLS):
                mm = str(r.get("mm") or "").zfill(2)
                months.add(mm)
                key = f"{r.get('yyyy')}-{mm}"
                if last_nonzero is None or key > last_nonzero:
                    last_nonzero = key
        per_year[year] = (len(co), len(months), kor, fore)
        print(f"  {year:<6}{len(co):>10}{len(months):>11}{kor:>14,.2f}{fore:>14,.2f}")

    print("\n== 판정 ==")
    nonzero_years = [y for y, v in per_year.items() if v[1] > 0]
    zero_years = [y for y, v in per_year.items() if v[1] == 0]
    if nonzero_years:
        print(f"  값이 있던 해: {', '.join(nonzero_years)}")
        print(f"  전부 0인 해 : {', '.join(zero_years) if zero_years else '없음'}")
        print(f"  마지막으로 0이 아니었던 달: **{last_nonzero}**")
        print("\n  → **전 기간 0이 아니다.** 후보 ②(집계가 비어 있다)는 **약해졌다.**")
        print("     같은 필드가 값을 낸 적이 있기 때문이다.")
    else:
        print("  전 기간 0 — 후보 ②(집계 공백)를 배제할 수 없다.")

    print("\n  **그러나 ①로 확정되지 않는다.** 분류·집계 변경 가능성이 남는다(파일 머리 주석).")
    print("  **그리고 이 관측은 선커밋 기준이 될 수 없다** — 데이터를 이미 봤다(§3-7).")

    after = {p: sha(p) for _y, p in present}
    same = all(before[p] == after[p] for p in before)
    print(f"\n  원본 무변경 확인: {'통과' if same else '**실패 — 파일이 바뀌었다**'}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())

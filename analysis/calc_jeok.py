# =============================================================
#  #05 주제검증: 적(積)컨테이너 방향별 복원 — 3개년(2022·2023·2024)
#
#  적컨 = 전체 컨테이너 − 공(空)컨테이너  (외항 방향별)
#   · 전체 방향별 : total_container_direction.csv
#                   (IPA 실적발표·해수청 연도별 표 — 방향별 확정값)
#   · 공컨 방향별 : container_YYYY_direction.csv (공컨 API 원시)
#                   → 외항(ocCt=1)만, (forEmpTeu + korEmpTeu)를 GInOut별 집계
#
#  GInOut: 1=수입 · 2=수출 · 3=수입환적 · 4=수출환적
#  ocCt  : 1=수출입항(외항) · 2=연안항(공컨 실적 0)
#   → 코드 정의 근거: docs/GInOut_코드규명.md [확정]
#
#  적컨 수입 = 전체 수입 − 공컨(GInOut=1)
#  적컨 수출 = 전체 수출 − 공컨(GInOut=2)
#
#  구성: (1) 집계 → (2) 대조 게이트 → (3) 출력표
#  ※ 게이트 하나라도 불일치이면 즉시 종료(이후 단계 진행 금지).
# =============================================================

import pandas as pd
import sys

# 윈도우 콘솔 한글 출력이 깨지지 않도록 UTF-8로 설정
sys.stdout.reconfigure(encoding="utf-8")

# ---- 상수 ----
YEARS = [2022, 2023, 2024]
# 기준값은 챗 두뇌가 소수 1자리로 반올림해 준 값이므로, 재현값도 소수
# 1자리로 반올림해 대조한다(예: 재현 1,563,280.75 → 1,563,280.8 = 기준).
TOL = 0.001  # 1자리 반올림 후 남는 부동소수 오차만 허용

# 대조 기준값(챗 두뇌 산출) — 세 값군 모두 일치해야 통과
EXPECT_EMPTY = {2022: 873_917.5, 2023: 999_990.2, 2024: 1_044_969.5}   # 공컨계(외항)
EXPECT_JEOK_IMP = {2022: 1_563_280.8, 2023: 1_595_793.2, 2024: 1_653_039.0}  # 적컨 수입
EXPECT_JEOK_EXP = {2022: 711_505.8, 2023: 821_962.5, 2024: 820_153.0}   # 적컨 수출
EXPECT_RATIO = {2022: 2.20, 2023: 1.94, 2024: 2.02}   # 적컨 수입:수출 배율


def fail(gate: str, msg: str) -> None:
    """대조 게이트 불일치 시 오류 메시지를 남기고 즉시 종료한다."""
    print(f"  [{gate}] FAIL — {msg}")
    print("  ▶ 게이트 불일치로 이후 단계를 진행하지 않고 종료합니다.")
    sys.exit(1)


# =============================================================
# (1) 집계 — 연도별 공컨(외항, GInOut별) → 적컨 복원
# =============================================================
print("=" * 64)
print(" (1) 집계 — 전체 − 공컨(외항) → 적컨 방향별 복원")
print("=" * 64)

# 전체 방향별 확정값
total_df = pd.read_csv("total_container_direction.csv").set_index("yyyy")

rows = []
for y in YEARS:
    # 공컨 API 원시 — 외항(ocCt=1)만
    df = pd.read_csv(f"container_{y}_direction.csv")
    df["GInOut"] = pd.to_numeric(df["GInOut"])
    df["ocCt"] = pd.to_numeric(df["ocCt"])
    df["공컨TEU"] = pd.to_numeric(df["forEmpTeu"]) + pd.to_numeric(df["korEmpTeu"])
    port = df[df["ocCt"] == 1]

    by = port.groupby("GInOut")["공컨TEU"].sum()
    emp_imp = float(by.get(1, 0.0))                       # 공컨 수입(GInOut=1)
    emp_exp = float(by.get(2, 0.0))                       # 공컨 수출(GInOut=2)
    emp_ts = float(by.get(3, 0.0)) + float(by.get(4, 0.0))  # 공컨 환적(3+4)
    emp_all = float(port["공컨TEU"].sum())                # 공컨계(외항 전체)

    # 전체 방향별 확정값
    tot_imp = float(total_df.loc[y, "수입"])
    tot_exp = float(total_df.loc[y, "수출"])
    tot_ts = float(total_df.loc[y, "환적"])

    # 적컨 = 전체 − 공컨 (방향별)
    jeok_imp = tot_imp - emp_imp
    jeok_exp = tot_exp - emp_exp
    jeok_ts = tot_ts - emp_ts
    ratio = jeok_imp / jeok_exp                           # 적컨 수입:수출 배율
    emp_ratio = emp_exp / emp_imp                         # 공컨 수출:수입 배율

    # 항등식(ID): 적컨 수입초과 == (전체수입−전체수출) + (공컨수출−공컨수입)
    id_lhs = jeok_imp - jeok_exp
    id_rhs = (tot_imp - tot_exp) + (emp_exp - emp_imp)

    rows.append({
        "yyyy": y,
        "전체수입": tot_imp, "전체수출": tot_exp, "전체환적": tot_ts,
        "공컨수입": emp_imp, "공컨수출": emp_exp, "공컨환적": emp_ts, "공컨계": emp_all,
        "적컨수입": jeok_imp, "적컨수출": jeok_exp, "적컨환적": jeok_ts,
        "적컨배율": ratio, "공컨배율": emp_ratio,
        "ID좌변": id_lhs, "ID우변": id_rhs, "ID차이": id_lhs - id_rhs,
    })

res = pd.DataFrame(rows).set_index("yyyy")

# =============================================================
# (2) 대조 게이트 — 세 값군 전부 일치해야 통과
# =============================================================
print("\n" + "=" * 64)
print(" (2) 대조 게이트 (공컨계 · 적컨수입 · 적컨수출 · 배율)")
print("=" * 64)

for y in YEARS:
    r = res.loc[y]
    # 공컨계(1자리 대조)
    if abs(round(r["공컨계"], 1) - EXPECT_EMPTY[y]) > TOL:
        fail("공컨계", f"{y} 재현={r['공컨계']:,.2f} vs 기준={EXPECT_EMPTY[y]:,.2f}")
    # 적컨 수입(1자리 대조)
    if abs(round(r["적컨수입"], 1) - EXPECT_JEOK_IMP[y]) > TOL:
        fail("적컨수입", f"{y} 재현={r['적컨수입']:,.2f} vs 기준={EXPECT_JEOK_IMP[y]:,.2f}")
    # 적컨 수출(1자리 대조)
    if abs(round(r["적컨수출"], 1) - EXPECT_JEOK_EXP[y]) > TOL:
        fail("적컨수출", f"{y} 재현={r['적컨수출']:,.2f} vs 기준={EXPECT_JEOK_EXP[y]:,.2f}")
    # 배율(소수 2자리 대조)
    if abs(round(r["적컨배율"], 2) - EXPECT_RATIO[y]) > 0.005:
        fail("배율", f"{y} 재현={r['적컨배율']:.2f} vs 기준={EXPECT_RATIO[y]:.2f}")

print("  [공컨계]  PASS — " + " / ".join(f"{y}={res.loc[y,'공컨계']:,.1f}" for y in YEARS))
print("  [적컨수입] PASS — " + " / ".join(f"{y}={res.loc[y,'적컨수입']:,.1f}" for y in YEARS))
print("  [적컨수출] PASS — " + " / ".join(f"{y}={res.loc[y,'적컨수출']:,.1f}" for y in YEARS))
print("  [배율]    PASS — " + " / ".join(f"{y}={res.loc[y,'적컨배율']:.2f}" for y in YEARS))
print("\n  ✅ 세 값군 전부 일치 — 출력 단계로 진행합니다.")

# =============================================================
# (3) 출력표 — 적컨 3개년 복원표 + 연도별 방향별 분해
# =============================================================
print("\n" + "=" * 64)
print(" (3-①) 적컨 3개년 복원표  (단위: TEU)")
print("=" * 64)
print(f"  {'연도':>4}{'적컨수입':>14}{'적컨수출':>14}{'적컨배율':>10}"
      f"{'공컨계':>14}{'공컨배율':>10}")
print("  " + "-" * 62)
for y in YEARS:
    r = res.loc[y]
    print(f"  {y:>4}{r['적컨수입']:>14,.1f}{r['적컨수출']:>14,.1f}{r['적컨배율']:>10.2f}"
          f"{r['공컨계']:>14,.1f}{r['공컨배율']:>10.2f}")
print("  " + "-" * 62)

print("\n" + "=" * 64)
print(" (3-②) 연도별 방향별 분해 (전체 − 공컨 = 적컨) + 항등식 검산")
print("=" * 64)
for y in YEARS:
    r = res.loc[y]
    print(f"\n  ── {y}년 ──")
    print(f"  {'방향':>4}{'전체(공표)':>14}{'공컨(API)':>16}{'적컨(=차)':>16}{'V4부호':>8}")
    print("  " + "-" * 56)
    trio = [("수입", "전체수입", "공컨수입", "적컨수입"),
            ("수출", "전체수출", "공컨수출", "적컨수출"),
            ("환적", "전체환적", "공컨환적", "적컨환적")]
    for label, tk, ek, jk in trio:
        sign = "양수" if r[jk] > 0 else "음수"
        print(f"  {label:>4}{r[tk]:>14,.0f}{r[ek]:>16,.2f}{r[jk]:>16,.2f}{sign:>8}")
    ratio_tot = r["전체수입"] / r["전체수출"]
    print(f"    배율 — 전체 수입:수출 {ratio_tot:.2f}배 │ "
          f"적컨 수입:수출 {r['적컨배율']:.2f}배 │ 공컨 수출:수입 {r['공컨배율']:.2f}배")
    print(f"    ID  — 좌변 {r['ID좌변']:,.2f}  우변 {r['ID우변']:,.2f}  "
          f"차이 {r['ID차이']:+.4f}  → {'닫힘' if abs(r['ID차이']) < 0.01 else '열림'}")

print("\n  · 적컨 수입:수출 배율 = " + " / ".join(f"{y} {res.loc[y,'적컨배율']:.2f}배" for y in YEARS))
print("  · 공컨 수출:수입 배율 = " + " / ".join(f"{y} {res.loc[y,'공컨배율']:.2f}배" for y in YEARS))
print("\n완료: 대조 게이트 전부 통과 → 적컨 3개년 복원 확정.")

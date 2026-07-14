# =============================================================
#  프로브 E — 후보 ① 컨테이너 수지 검증 (V1~V6)
#
#  적컨 = 전체(공표) − 공컨(API) 로 방향별 복원이 성립하는지 검증한다.
#
#  ※ 검증용 프로브. 판정 문장을 쓰지 않고 관측 사실만 출력한다.
#  ※ 이 스크립트는 전략 세션(챗)에서 수행된 2022·2024 예비계산을
#     로컬에서 독립 재현하는 것을 겸한다 — 자기 보고는 자기 실수를 못 잡는다.
#  ※ 2023·2025 공표 방향값은 세션 시점 미확보. 확보 시 PUB 딕셔너리에 채운다.
#
#  ⚠ 상쇄율은 검증 명제가 아니라 항등식이다:
#       적컨수입초과 = (전체수입 − 전체수출) + (공컨수출 − 공컨수입)
#     따라서 [ID]에서 '항등식이 수치적으로 닫히는지'만 파이프라인 검산으로 확인하고,
#     상쇄율 자체는 '초과분의 분해'로만 표기한다. 논거는 docs/05_주제검증.md §2.
#  ⚠ 비자명한 검증 명제는 V5(적컨 수입:수출 ≥ 1.5배)다. 이것은 실패할 수 있다.
# =============================================================
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)

TOL_ID = 0.01     # 항등식 허용오차 (TEU)
GATE_V5 = 1.5     # 선커밋 V5 기준: 적컨 수입:수출 배율

# -------------------------------------------------------------
#  공표값 (인천항 전체 컨테이너, 단위 TEU)
#   - 2022: 인천지방해양수산청 「인천항 컨테이너 물동량」 (연도별 표, TEU 정수)
#   - 2024: 인천항만공사 2024년 실적 (수입/수출/환적 TEU 정수)
#   - 2023 / 2025: ★ 미확보 ★  (보도자료는 '수출입' 합산 만TEU 단위로만 발표)
#       확보 경로 후보: e-나라지표 idx_cd=1267 통계표 / SP-IDC /
#                      인천지방해양수산청 연도별 페이지 갱신 / hwpx(프로브 D)
#   - None 인 항목은 계산에서 자동 제외된다.
# -------------------------------------------------------------
PUB = {
    2022: {"수입": 1593012, "수출": 1523905, "환적": 71789, "연안": 1866,
           "외항": 3188706, "합계": 3190571,
           "출처": "인천지방해양수산청 인천항 컨테이너 물동량(연도별)"},
    2023: {"수입": None, "수출": None, "환적": None, "연안": None,
           "외항": None, "합계": None, "출처": "미확보"},
    2024: {"수입": 1772061, "수출": 1737129, "환적": 49265, "연안": None,
           "외항": None, "합계": 3558455,
           "출처": "인천항만공사 2024년 실적"},
    2025: {"수입": None, "수출": None, "환적": None, "연안": None,
           "외항": None, "합계": None, "출처": "미확보"},
}

CSV = {y: os.path.join(ANALYSIS, f"container_{y}_direction.csv") for y in (2022, 2023, 2024, 2025)}
YEARS = (2022, 2023, 2024, 2025)


def load_empty(year: int):
    """공컨 API 원시 CSV → GInOut별 TEU (ocCt=1) + ocCt=2 합계."""
    p = CSV[year]
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, encoding="utf-8-sig")
    for c in ["forEmpTeu", "korEmpTeu", "GInOut", "ocCt"]:
        df[c] = pd.to_numeric(df[c])
    df["teu"] = df["forEmpTeu"] + df["korEmpTeu"]
    g = df[df.ocCt == 1].groupby("GInOut")["teu"].sum()
    return {
        "수입": float(g.get(1, 0.0)),
        "수출": float(g.get(2, 0.0)),
        "환적": float(g.get(3, 0.0)) + float(g.get(4, 0.0)),
        "oc1": float(df[df.ocCt == 1]["teu"].sum()),
        "oc2": float(df[df.ocCt == 2]["teu"].sum()),
    }


print("=" * 86)
print(" 프로브 E — 컨테이너 수지 (적컨 = 전체 − 공컨)")
print("=" * 86)

# -------------------- V1 --------------------
print("\n" + "-" * 86)
print(" V1  분모 확보 — 연도별 공표 방향값(수입/수출/환적)")
print("-" * 86)
print("   연도 |      수입 |      수출 |    환적 |    연안 | 출처")
have = []
for y in YEARS:
    p = PUB[y]
    if all(p[k] is not None for k in ("수입", "수출", "환적")):
        have.append(y)
    def f(v):
        return f"{v:>10,}" if v is not None else "    미확보"
    print(f"   {y} |{f(p['수입'])}|{f(p['수출'])}|{f(p['환적'])}|{f(p['연안'])}| {p['출처']}")
print(f"\n   → 확보: {have if have else '없음'}   미확보: {[y for y in YEARS if y not in have]}")
print(f"   → 2025년 확보 여부: {'예' if 2025 in have else '아니오'}   (선커밋: 2025 미확보 시 후보 ① 기각)")

# -------------------- V2 --------------------
print("\n" + "-" * 86)
print(" V2  공표값 내적 검산 + 정밀도 등급")
print("-" * 86)
for y in have:
    p = PUB[y]
    s = p["수입"] + p["수출"] + p["환적"]
    ref = p["외항"] if p["외항"] is not None else p["합계"]
    lbl = "외항" if p["외항"] is not None else "합계"
    print(f"   {y}: 수입+수출+환적 = {s:>10,}  vs 공표 {lbl} {ref:>10,}  차이 {s-ref:+,}")
    if None not in (p["외항"], p["연안"], p["합계"]):
        t = p["외항"] + p["연안"]
        print(f"         외항+연안     = {t:>10,}  vs 공표 합계 {p['합계']:>10,}  차이 {t-p['합계']:+,}  (공표 반올림)")
    print(f"         정밀도 등급: TEU 정수")

# -------------------- V3 --------------------
print("\n" + "-" * 86)
print(" V3  모집단 정합 — 공컨 ocCt 축 ↔ 공표 외항/연안 축")
print("     명제: 공컨 ocCt=2(연안항) ≤ 공표 연안    [위반 → 모집단 불일치 → 기각]")
print("-" * 86)
EMP = {}
for y in YEARS:
    e = load_empty(y)
    EMP[y] = e
    if e is None:
        print(f"   {y}: [실패] {os.path.basename(CSV[y])} 없음")
        continue
    pl = PUB[y]["연안"]
    if pl is None:
        note = "  (ocCt=2 실적 0 → 어떤 값과도 정합)" if e["oc2"] == 0 else ""
        print(f"   {y}: 공컨 ocCt=2 = {e['oc2']:>8,.1f} TEU  |  공표 연안 미확보 → 대조 보류{note}")
    else:
        ok = e["oc2"] <= pl
        print(f"   {y}: 공컨 ocCt=2 = {e['oc2']:>8,.1f} TEU  ≤  공표 연안 {pl:>7,}  → {'성립' if ok else '위반'}"
              f"   (적컨 연안 = {pl - e['oc2']:,.1f})")

# -------------------- V4 · V5 · ID --------------------
print("\n" + "-" * 86)
print(" V4  적컨 부호 — 적컨 = 전체 − 공컨 이 전 방향 양수인가          [음수 → 기각]")
print(f" V5  적컨 수입 우위 — 적컨 수입:수출 ≥ {GATE_V5}배 인가   ★ 비자명 명제 ★  [<1.0 → 기각]")
print(" ID  항등식 검산 — 적컨수입초과 == (전체수입−전체수출) + (공컨수출−공컨수입)")
print("-" * 86)
rows = []
for y in have:
    e = EMP[y]
    if e is None:
        continue
    p = PUB[y]
    print(f"\n   ── {y}년 ──")
    print(f"   {'방향':<6}{'전체(공표)':>14}{'공컨(API)':>15}{'적컨(=차)':>15}   V4 부호")
    full = {}
    for k in ("수입", "수출", "환적"):
        fv = p[k] - e[k]
        full[k] = fv
        print(f"   {k:<6}{p[k]:>14,}{e[k]:>15,.2f}{fv:>15,.2f}   {'양수' if fv > 0 else '음수 ← 모집단 불일치'}")

    r_tot = p["수입"] / p["수출"]
    r_full = full["수입"] / full["수출"] if full["수출"] else float("nan")
    r_emp = e["수출"] / e["수입"] if e["수입"] else float("nan")
    print(f"\n   배율 — 전체 수입:수출 {r_tot:5.2f}배  │  적컨 수입:수출 {r_full:5.2f}배  │  공컨 수출:수입 {r_emp:6.2f}배")
    print(f"   V5 — 적컨 {r_full:.2f}배  vs 기준 {GATE_V5}배  → {'기준 이상' if r_full >= GATE_V5 else '기준 미만'}")

    lhs = full["수입"] - full["수출"]
    rhs = (p["수입"] - p["수출"]) + (e["수출"] - e["수입"])
    print(f"   ID — 좌변 {lhs:>10,.2f}   우변 {rhs:>10,.2f}   차이 {lhs-rhs:+.4f}  → "
          f"{'닫힘' if abs(lhs - rhs) <= TOL_ID else '⚠ 안 닫힘 = 계산 오류'}")

    net = p["수입"] - p["수출"]
    emp_s = e["수출"] - e["수입"]
    base = p["외항"] if p["외항"] is not None else p["합계"]
    print(f"   분해 — 적컨 수입초과 {lhs:>9,.0f} = 공컨 수출초과 {emp_s:>9,.0f} ({emp_s/lhs*100:.1f}%)"
          f"  +  전체 순수입 {net:>7,.0f} ({net/lhs*100:.1f}%, 외항의 {net/base*100:.2f}%)")
    rows.append((y, r_tot, r_full, r_emp, emp_s / lhs * 100, net))

# -------------------- V6 --------------------
print("\n" + "-" * 86)
print(" V6  지속성 + 요약 (확보 연도만)")
print("-" * 86)
print("   연도 | 전체 수입:수출 | 적컨 수입:수출 | 공컨 수출:수입 | 공컨수출초과 비중 | 전체 순수입")
for (y, rt, rf, re_, share, net) in rows:
    print(f"   {y} | {rt:>12.2f}배 | {rf:>12.2f}배 | {re_:>12.2f}배 | {share:>15.1f}% | {net:>+11,.0f}")
if rows:
    allpass = all(r[2] >= GATE_V5 for r in rows)
    print(f"\n   V6 — 확보 전 연도에서 적컨 수입:수출 ≥ {GATE_V5}배: {'전부 성립' if allpass else '일부 미성립'}")
print(f"   미확보 연도: {[y for y in YEARS if y not in have]} — V1 미충족분")

print("\n(프로브 E 종료 — 관측 사실만 출력. 판정은 docs/05_주제검증.md §4에서.)")

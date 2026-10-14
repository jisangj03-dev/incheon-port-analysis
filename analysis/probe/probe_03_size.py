# =============================================================
#  프로브 A — 후보 ③ (규격별 10/20/40/99 구성) 데이터 가용성 검증
#  ※ 검증용 프로브. 확정·판정 문장을 쓰지 않고 관측 사실만 출력한다.
# =============================================================
import os
import sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
REPO = os.path.dirname(ANALYSIS)
RAW_CSV = os.path.join(ANALYSIS, "container_2025_direction.csv")  # 사전 확인한 실제 파일명
DOC = os.path.join(REPO, "docs", "GInOut_코드규명.md")

SPEC_FOR = ["forEmp_10", "forEmp_20", "forEmp_40", "forEmp_99"]
SPEC_KOR = ["korEmp_10", "korEmp_20", "korEmp_40", "korEmp_99"]
TOL = 0.01

print("=" * 64)
print(" 프로브 A — 후보 ③ 규격별 구성")
print("=" * 64)
print(f"  원시 CSV: {os.path.basename(RAW_CSV)}")

# -------------------------------------------------------------
# (a) 문서 확인 — 규격 필드 정의가 docs/GInOut_코드규명.md 에 있는가
# -------------------------------------------------------------
print("\n" + "-" * 64)
print(" (a) 문서 확인 — 규격 필드(_10/_20/_40/_99) 정의")
print("-" * 64)
with open(DOC, encoding="utf-8") as f:
    doc_lines = f.readlines()
hits = [ln.rstrip("\n") for ln in doc_lines
        if ("_10" in ln or "_20" in ln or "_40" in ln or "_99" in ln or "규격" in ln)]
if hits:
    print("  [문서 내 규격 관련 원문 인용]")
    for ln in hits:
        print(f"    │ {ln}")
else:
    print("  문서 미확인 — 규격 필드 정의가 docs/GInOut_코드규명.md 에 없음")

# -------------------------------------------------------------
# 데이터 로드 + 회귀 검산
# -------------------------------------------------------------
df = pd.read_csv(RAW_CSV)
numcols = ["forEmpTeu", "korEmpTeu"] + SPEC_FOR + SPEC_KOR
for c in numcols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

port = df[df["ocCt"] == 1].copy()
port["TeuAll"] = port["forEmpTeu"] + port["korEmpTeu"]

print("\n" + "-" * 64)
print(" (b) 지문 검산 — 먼저 기존 확정치 회귀")
print("-" * 64)
total = float(port["TeuAll"].sum())
print(f"  ocCt=1 전체 합 = {total:,.2f}  (기대 991,170.00)")
if abs(total - 991_170.0) > TOL:
    print("  [중단] 991,170 회귀 검산 실패 — 이후 진행 금지")
    sys.exit(1)

by_g = port.groupby("GInOut")["TeuAll"].sum()
imp = float(by_g.get(1, 0.0)); exphi = float(by_g.get(2, 0.0))
trans = float(by_g.get(3, 0.0) + by_g.get(4, 0.0))
# #03 표는 정수 반올림 공표치(원자료는 0.25 TEU 단위 소수 포함). 반올림 후 대조.
print(f"  수입(1)={imp:,.2f} → 반올림 {round(imp):,} (기대 139,418)")
print(f"  수출(2)={exphi:,.2f} → 반올림 {round(exphi):,} (기대 843,838)")
print(f"  환적(3+4)={trans:,.2f} → 반올림 {round(trans):,} (기대 7,914)")
bad = (round(imp) != 139_418) or (round(exphi) != 843_838) or (round(trans) != 7_914)
if bad:
    print("  [중단] GInOut별 회귀 검산 실패(반올림 후 불일치) — 이후 진행 금지")
    sys.exit(1)
print("  → 회귀 검산 통과(반올림 대조 일치, 원자료는 0.25 TEU 소수 포함). 규격 필드 가설 검증으로 진행.")


def spec_probe(label, specs, teucol):
    s10, s20, s40, s99 = specs
    sub = port[[teucol] + specs].copy()
    teu = sub[teucol]
    # 가설 H1: (_10 + _20 + _40 + _99) == Teu
    h1_sum = sub[s10] + sub[s20] + sub[s40] + sub[s99]
    h1_resid = teu - h1_sum
    h1_match = (h1_resid.abs() <= TOL)
    # 가설 H2: (0.5*_10 + 1*_20 + 2*_40) 와 Teu 의 잔차, 그 잔차와 _99 비율
    h2_val = 0.5 * sub[s10] + 1.0 * sub[s20] + 2.0 * sub[s40]
    h2_resid = teu - h2_val
    # 잔차 / _99 비율 (전체 합계 기준, _99!=0인 행만 개별 비율)
    tot_resid = float(h2_resid.sum())
    tot_99 = float(sub[s99].sum())
    ratio_agg = (tot_resid / tot_99) if abs(tot_99) > TOL else float("nan")
    nz99 = sub[sub[s99].abs() > TOL]
    per_ratio = ((teu - h2_val)[sub[s99].abs() > TOL] / nz99[s99]) if len(nz99) else pd.Series(dtype=float)

    print(f"\n  [{label}]  (행수 {len(sub)})")
    print(f"    H1  (_10+_20+_40+_99) == {teucol}")
    print(f"        일치 행수 = {int(h1_match.sum())} / {len(sub)}  · 불일치 = {int((~h1_match).sum())}")
    print(f"        잔차(Teu-합) 요약: min={h1_resid.min():.2f} max={h1_resid.max():.2f} "
          f"mean={h1_resid.mean():.2f} abs합={h1_resid.abs().sum():.2f}")
    print(f"    H2  0.5*_10 + 1*_20 + 2*_40  vs  {teucol}")
    print(f"        잔차(Teu-H2) 요약: min={h2_resid.min():.2f} max={h2_resid.max():.2f} "
          f"mean={h2_resid.mean():.2f} abs합={h2_resid.abs().sum():.2f}")
    print(f"        Σ잔차 / Σ_99 = {tot_resid:,.2f} / {tot_99:,.2f} = "
          f"{ratio_agg:.4f}" if abs(tot_99) > TOL else "        Σ_99=0 → 비율 계산 불가")
    if len(per_ratio):
        print(f"        행별 (Teu-H2)/_99 : min={per_ratio.min():.4f} max={per_ratio.max():.4f} "
              f"mean={per_ratio.mean():.4f}  (n={len(per_ratio)})")
    print(f"    _99 전부 0? {'예' if (sub[s99].abs() <= TOL).all() else '아니오'}  "
          f"(Σ_99={sub[s99].sum():.2f}, 0아닌 행={int((sub[s99].abs()>TOL).sum())})")


spec_probe("for (외국적)", SPEC_FOR, "forEmpTeu")
spec_probe("kor (한국적)", SPEC_KOR, "korEmpTeu")

# -------------------------------------------------------------
# (c) 서사 — 방향별 규격 구성 + 월별 40ft 비중 변동
# -------------------------------------------------------------
print("\n" + "-" * 64)
print(" (c) 서사 — 방향(GInOut 1 vs 2)별 규격 구성 비중 (for+kor 박스 합)")
print("-" * 64)
for code, name in [(1, "수입"), (2, "수출")]:
    d = port[port["GInOut"] == code]
    b10 = float(d["forEmp_10"].sum() + d["korEmp_10"].sum())
    b20 = float(d["forEmp_20"].sum() + d["korEmp_20"].sum())
    b40 = float(d["forEmp_40"].sum() + d["korEmp_40"].sum())
    b99 = float(d["forEmp_99"].sum() + d["korEmp_99"].sum())
    tot = b10 + b20 + b40 + b99
    if tot > 0:
        print(f"  {name}(GInOut={code}) 박스합={tot:,.0f} → "
              f"10ft {b10/tot*100:5.1f}% · 20ft {b20/tot*100:5.1f}% · "
              f"40ft {b40/tot*100:5.1f}% · 99 {b99/tot*100:5.1f}%")
    else:
        print(f"  {name}(GInOut={code}) 박스합=0")

print("\n  월별 40ft(박스) 비중  (수출 GInOut=2 기준, for+kor)")
exp2 = port[port["GInOut"] == 2].copy()
exp2["b40"] = exp2["forEmp_40"] + exp2["korEmp_40"]
exp2["ball"] = (exp2["forEmp_10"] + exp2["forEmp_20"] + exp2["forEmp_40"] + exp2["forEmp_99"]
               + exp2["korEmp_10"] + exp2["korEmp_20"] + exp2["korEmp_40"] + exp2["korEmp_99"])
g = exp2.groupby("mm").agg(b40=("b40", "sum"), ball=("ball", "sum"))
g["share40"] = g["b40"] / g["ball"] * 100
for m, r in g.iterrows():
    print(f"    {int(m):2d}월  40ft비중 {r['share40']:5.1f}%")
print(f"  → 40ft비중 min={g['share40'].min():.1f}% max={g['share40'].max():.1f}% "
      f"std={g['share40'].std():.2f}")

print("\n(프로브 A 종료 — 관측 사실만 출력. 판정은 문서에서.)")

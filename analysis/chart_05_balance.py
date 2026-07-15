# =============================================================
#  보고서 #05: 인천항 컨테이너 수지 — 적컨·공컨 방향 대비 (2022·2023·2024)
#  적컨 = 전체 컨테이너 − 공(空)컨테이너  (외항 방향별)
#  GInOut: 1=수입 · 2=수출 · 3=수입환적 · 4=수출환적 / ocCt: 1=수출입항 · 2=연안항
#  구성: (1) 복원 집계 → (2) 대조 게이트 → (3) 차트 2매
#  ※ 게이트 하나라도 불일치이면 즉시 종료. 2025년은 방향별 미확보로 3개년만 다룬다.
# =============================================================

import pandas as pd
import matplotlib.pyplot as plt
import sys

sys.stdout.reconfigure(encoding="utf-8")

YEARS = [2022, 2023, 2024]
TOL = 0.001

EXPECT_EMPTY = {2022: 873_917.5, 2023: 999_990.2, 2024: 1_044_969.5}
EXPECT_JEOK_IMP = {2022: 1_563_280.8, 2023: 1_595_793.2, 2024: 1_653_039.0}
EXPECT_JEOK_EXP = {2022: 711_505.8, 2023: 821_962.5, 2024: 820_153.0}
EXPECT_RATIO = {2022: 2.20, 2023: 1.94, 2024: 2.02}


def fail(gate, msg):
    print(f"  [{gate}] FAIL — {msg}")
    print("  ▶ 게이트 불일치로 차트를 생성하지 않고 종료합니다.")
    sys.exit(1)


print("=" * 64)
print(" (1) 복원 집계 — 전체 − 공컨(외항) → 적컨 방향별")
print("=" * 64)

total_df = pd.read_csv("total_container_direction.csv").set_index("yyyy")

rows = []
for y in YEARS:
    df = pd.read_csv(f"container_{y}_direction.csv")
    df["GInOut"] = pd.to_numeric(df["GInOut"])
    df["ocCt"] = pd.to_numeric(df["ocCt"])
    df["gong"] = pd.to_numeric(df["forEmpTeu"]) + pd.to_numeric(df["korEmpTeu"])
    port = df[df["ocCt"] == 1]
    by = port.groupby("GInOut")["gong"].sum()
    emp_imp = float(by.get(1, 0.0))
    emp_exp = float(by.get(2, 0.0))
    emp_all = float(port["gong"].sum())
    tot_imp = float(total_df.loc[y, "수입"])
    tot_exp = float(total_df.loc[y, "수출"])
    jeok_imp = tot_imp - emp_imp
    jeok_exp = tot_exp - emp_exp
    ratio = jeok_imp / jeok_exp
    emp_ratio = emp_exp / emp_imp
    jeok_excess = jeok_imp - jeok_exp
    emp_excess = emp_exp - emp_imp
    net_imp = tot_imp - tot_exp
    id_diff = jeok_excess - (emp_excess + net_imp)
    rows.append({
        "yyyy": y,
        "jeok_imp": jeok_imp, "jeok_exp": jeok_exp, "jeok_ratio": ratio,
        "emp_imp": emp_imp, "emp_exp": emp_exp, "emp_ratio": emp_ratio, "emp_all": emp_all,
        "jeok_excess": jeok_excess, "emp_excess": emp_excess, "net_imp": net_imp,
        "id_diff": id_diff,
    })

res = pd.DataFrame(rows).set_index("yyyy")

print("\n" + "=" * 64)
print(" (2) 대조 게이트 (공컨계 · 적컨수입 · 적컨수출 · 배율 · 항등식)")
print("=" * 64)

for y in YEARS:
    r = res.loc[y]
    if abs(round(r["emp_all"], 1) - EXPECT_EMPTY[y]) > TOL:
        fail("공컨계", f"{y} 재현={r['emp_all']:,.2f} vs 기준={EXPECT_EMPTY[y]:,.2f}")
    if abs(round(r["jeok_imp"], 1) - EXPECT_JEOK_IMP[y]) > TOL:
        fail("적컨수입", f"{y} 재현={r['jeok_imp']:,.2f} vs 기준={EXPECT_JEOK_IMP[y]:,.2f}")
    if abs(round(r["jeok_exp"], 1) - EXPECT_JEOK_EXP[y]) > TOL:
        fail("적컨수출", f"{y} 재현={r['jeok_exp']:,.2f} vs 기준={EXPECT_JEOK_EXP[y]:,.2f}")
    if abs(round(r["jeok_ratio"], 2) - EXPECT_RATIO[y]) > 0.005:
        fail("배율", f"{y} 재현={r['jeok_ratio']:.2f} vs 기준={EXPECT_RATIO[y]:.2f}")
    if abs(r["id_diff"]) > 0.01:
        fail("항등식", f"{y} 초과분 분해 잔차 {r['id_diff']:+.4f} (닫히지 않음)")

print("  [공컨계]  PASS — " + " / ".join(f"{y}={res.loc[y,'emp_all']:,.1f}" for y in YEARS))
print("  [적컨수입] PASS — " + " / ".join(f"{y}={res.loc[y,'jeok_imp']:,.1f}" for y in YEARS))
print("  [적컨수출] PASS — " + " / ".join(f"{y}={res.loc[y,'jeok_exp']:,.1f}" for y in YEARS))
print("  [배율]    PASS — " + " / ".join(f"{y}={res.loc[y,'jeok_ratio']:.2f}" for y in YEARS))
print("  [항등식]  PASS — 초과분 분해 잔차 전 연도 0.0000 (닫힘)")
print("\n  ✅ 대조 게이트 전부 통과 — 차트 생성으로 진행합니다.")

print("\n  [플롯 입력값]")
for y in YEARS:
    r = res.loc[y]
    print(f"  {y}: 적컨수입 {r['jeok_imp']:,.0f} / 적컨수출 {r['jeok_exp']:,.0f} / "
          f"공컨수입 {r['emp_imp']:,.0f} / 공컨수출 {r['emp_exp']:,.0f} / "
          f"적컨배율 {r['jeok_ratio']:.2f} / 공컨배율 {r['emp_ratio']:.2f}")

plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
C_IMP = "#2E86C1"
C_EXP = "#C0392B"

fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 6))
x = range(len(YEARS))
w = 0.38

# 왼쪽: 적컨 (수입 우위)
jimp = [res.loc[y, "jeok_imp"] for y in YEARS]
jexp = [res.loc[y, "jeok_exp"] for y in YEARS]
axL.bar([i - w / 2 for i in x], jimp, w, color=C_IMP, label="수입")
axL.bar([i + w / 2 for i in x], jexp, w, color=C_EXP, label="수출")
offL = max(jimp) * 0.03  # 막대 높이에 비례한 주석 간격(축 스케일 달라도 일관)
for i, y in zip(x, YEARS):
    axL.text(i, max(jimp[i], jexp[i]) + offL, f"수입:수출\n{res.loc[y,'jeok_ratio']:.2f}배",
             ha="center", va="bottom", fontsize=10.5, fontweight="bold", color="#111")
axL.set_title("적(積)컨테이너 — 수입 우위", fontsize=13, fontweight="bold")
axL.set_xticks(list(x))
axL.set_xticklabels([f"{y}년" for y in YEARS])
axL.set_ylabel("TEU")
axL.set_ylim(0, max(jimp) * 1.30)  # 주석이 놓일 상단 여백 확보
axL.grid(True, axis="y", alpha=0.3)

# 오른쪽: 공컨 (수출 우위)
gimp = [res.loc[y, "emp_imp"] for y in YEARS]
gexp = [res.loc[y, "emp_exp"] for y in YEARS]
axR.bar([i - w / 2 for i in x], gimp, w, color=C_IMP, label="수입")
axR.bar([i + w / 2 for i in x], gexp, w, color=C_EXP, label="수출")
offR = max(gexp) * 0.03
for i, y in zip(x, YEARS):
    axR.text(i, max(gimp[i], gexp[i]) + offR, f"수출:수입\n{res.loc[y,'emp_ratio']:.2f}배",
             ha="center", va="bottom", fontsize=10.5, fontweight="bold", color="#111")
axR.set_title("공(空)컨테이너 — 수출 우위", fontsize=13, fontweight="bold")
axR.set_xticks(list(x))
axR.set_xticklabels([f"{y}년" for y in YEARS])
axR.set_ylabel("TEU")
axR.set_ylim(0, max(gexp) * 1.30)
axR.grid(True, axis="y", alpha=0.3)

# 범례는 두 subplot 공통 → 그래프 밖(하단 중앙)에 하나만 두어 주석과 겹치지 않게 한다
handles, labels = axL.get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=11, frameon=True,
           bbox_to_anchor=(0.5, 0.01))

fig.suptitle("인천항 적컨·공컨 방향 대비 (2022–2024, 모집단 ocCt=1)", fontsize=15, fontweight="bold")
fig.tight_layout(rect=[0, 0.06, 1, 0.95])  # 하단은 범례, 상단은 suptitle 공간
fig.savefig("../reports/images/balance_direction_2022_2024.png", dpi=150)
plt.close(fig)
print("\n(3) 차트 저장(갱신): balance_direction_2022_2024.png")

plt.figure(figsize=(10, 6))
emp_ex = [res.loc[y, "emp_excess"] for y in YEARS]
net_ex = [res.loc[y, "net_imp"] for y in YEARS]
plt.bar(x, emp_ex, color="#5DADE2", label="공컨 수출초과")
plt.bar(x, net_ex, bottom=emp_ex, color="#7F8C8D", label="전체 순수입(잔차)")
for i, y in zip(x, YEARS):
    tot = emp_ex[i] + net_ex[i]
    plt.text(i, emp_ex[i] / 2, f"{emp_ex[i]:,.0f}\n({emp_ex[i]/tot*100:.1f}%)",
             ha="center", va="center", fontsize=10, color="white", fontweight="bold")
    plt.text(i, tot + 12000, f"합 {tot:,.0f}\n순수입 {net_ex[i]:,.0f} ({net_ex[i]/tot*100:.1f}%)",
             ha="center", fontsize=9.5, color="#111")
plt.title("적컨 수입초과의 분해 (2022–2024, TEU) — 항등식\n적컨 수입초과 = 공컨 수출초과 + 전체 순수입",
          fontsize=14, fontweight="bold")
plt.xticks(list(x), [f"{y}년" for y in YEARS])
plt.ylabel("TEU")
plt.ylim(0, max(e + n for e, n in zip(emp_ex, net_ex)) * 1.2)
plt.legend(loc="upper right")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("../reports/images/balance_excess_2022_2024.png", dpi=150)
plt.close()
print("(3) 차트 저장: balance_excess_2022_2024.png")

print("\n완료: 대조 게이트 통과 → 차트 2매 생성 마침.")

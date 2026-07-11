# =============================================================
#  보고서 #03: 인천항 공컨테이너 '수출입 방향 분해' 분석
#
#  GInOut(수출입구분): 1=수입 · 2=수출 · 3=수입환적 · 4=수출환적
#  ocCt(외내항구분):   1=수출입항 · 2=연안항(공컨 실적 0)
#  → 코드 정의 근거: docs/GInOut_코드규명.md [확정]
#
#  구성: (1) 원시 재수집·저장 → (2) 검증 게이트 → (3) 집계 → (4) 차트
#  ※ 게이트 하나라도 FAIL이면 즉시 종료(이후 단계 진행 금지).
# =============================================================

# requests: API 호출 / ET: XML 파싱 / pandas: 표 / matplotlib: 차트 / sys: 인코딩·종료
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import sys
# config.py 의 인증키 (코드에 키를 직접 쓰지 않기 위함)
from config import SERVICE_KEY

# 윈도우 콘솔 한글 출력이 깨지지 않도록 UTF-8로 설정
sys.stdout.reconfigure(encoding="utf-8")

# ---- 상수 ----
GINOUT_LABEL = {"1": "수입", "2": "수출", "3": "수입환적", "4": "수출환적"}
# 추출 대상 태그: 핵심 6 + 규격별 8 (규격별은 이번 분석 미사용, 후속 재료로 보존)
CORE_TAGS = ["yyyy", "mm", "GInOut", "ocCt", "forEmpTeu", "korEmpTeu"]
SPEC_TAGS = ["forEmp_10", "forEmp_20", "forEmp_40", "forEmp_99",
             "korEmp_10", "korEmp_20", "korEmp_40", "korEmp_99"]
WANTED_TAGS = CORE_TAGS + SPEC_TAGS
# 수치 필드(0 검사·합계에 쓰이는 열)
NUMERIC_TAGS = ["forEmpTeu", "korEmpTeu"] + SPEC_TAGS
TOL = 0.01  # 허용오차

# =============================================================
# (1) 수집 — gonggong_container.py 와 동일 엔드포인트·패턴
# =============================================================
url = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"
params = {
    "serviceKey": SERVICE_KEY,
    "searchYear": "2025",
    "searchStartM": "01",
    "searchEndM": "12",
    "numOfRows": "100",   # 한 페이지에 전부(2025년은 64행)
    "pageNo": "1",
}

resp = requests.get(url, params=params, timeout=25)
root = ET.fromstring(resp.content)  # 원본 바이트로 파싱(한글 안전)

result_code = root.findtext(".//resultCode")
result_msg = root.findtext(".//resultMsg")
total_count = root.findtext(".//totalCount")
print("=" * 60)
print(" (1) 수집")
print("=" * 60)
print(f"  resultCode={result_code} / resultMsg={result_msg} / totalCount={total_count}")

items = root.findall(".//item")
print(f"  받은 item 수 = {len(items)}")

# 실제 응답 XML의 태그명을 직접 확인(문서 기록이 아니라 실제 태그 기준)
actual_tags = [child.tag for child in items[0]]
print(f"  첫 item 실제 태그({len(actual_tags)}개): {actual_tags}")
missing = [t for t in WANTED_TAGS if t not in actual_tags]
if missing:
    print(f"  [수집 실패] 기대 태그가 응답에 없음: {missing}")
    sys.exit(1)
print("  → 필요한 14개 태그 모두 실제 응답에 존재함(확인 완료).")

# 원시 그대로 추출(가공 금지). 각 행 = {태그: 텍스트}
raw_rows = [{t: item.findtext(t) for t in WANTED_TAGS} for item in items]
raw_df = pd.DataFrame(raw_rows, columns=WANTED_TAGS)

# 원시 CSV 저장(규격별 8필드 포함 — 후속 재료 보존 목적)
RAW_CSV = "container_2025_direction.csv"
raw_df.to_csv(RAW_CSV, index=False, encoding="utf-8-sig")
print(f"  → {RAW_CSV} 저장 완료 ({len(raw_df)}행 × {len(raw_df.columns)}열, 원시 그대로)")

# 검증·집계용 숫자 사본(원시 CSV는 이미 저장됨 — 여기서만 형변환)
df = raw_df.copy()
df["mm"] = pd.to_numeric(df["mm"])
for c in NUMERIC_TAGS:
    df[c] = pd.to_numeric(df[c], errors="coerce")

# =============================================================
# (2) 검증 게이트 — 하나라도 FAIL 시 즉시 종료
# =============================================================
print("\n" + "=" * 60)
print(" (2) 검증 게이트")
print("=" * 60)


def fail(gate: str, msg: str) -> None:
    """게이트 실패 시 오류 메시지를 남기고 즉시 종료한다."""
    print(f"  [{gate}] FAIL — {msg}")
    print("  ▶ 게이트 실패로 이후 단계를 진행하지 않고 종료합니다.")
    sys.exit(1)


# --- G1: 행수·코드 집합 ---
n_rows = len(df)
ginout_set = set(df["GInOut"].unique())
occt_set = set(df["ocCt"].unique())
ok_rows = (n_rows == 64)
ok_ginout = ginout_set.issubset({"1", "2", "3", "4"})
ok_occt = occt_set.issubset({"1", "2"})
if not (ok_rows and ok_ginout and ok_occt):
    fail("G1", f"행수={n_rows}(기대 64) / GInOut={sorted(ginout_set)} / ocCt={sorted(occt_set)}")
print(f"  [G1] PASS — 총 행수 {n_rows}=64, "
      f"GInOut={sorted(ginout_set)}⊆{{1,2,3,4}}, ocCt={sorted(occt_set)}⊆{{1,2}}")

# --- G2-①: ocCt=2 행의 모든 수치 필드가 0 ---
coastal = df[df["ocCt"] == "2"]
coastal_max = coastal[NUMERIC_TAGS].abs().to_numpy().max() if len(coastal) else 0.0
if coastal_max > TOL:
    fail("G2-①", f"ocCt=2({len(coastal)}행) 수치 필드에 0이 아닌 값 존재(최대 |값|={coastal_max})")
print(f"  [G2-①] PASS — ocCt=2({len(coastal)}행)의 모든 수치 필드=0 (최대 |값|={coastal_max})")

# --- G2-②: ocCt=1 월합(for+kor) vs container_2025.csv 전체공컨TEU (월별 일치) ---
base = pd.read_csv("container_2025.csv")  # 검산 기준(#01 산출물)
port = df[df["ocCt"] == "1"].copy()
port["공컨TEU"] = port["forEmpTeu"] + port["korEmpTeu"]
month_sum = port.groupby("mm")["공컨TEU"].sum()
cmp = base.set_index("월")["전체공컨TEU"]
diffs = []
for m in range(1, 13):
    got = float(month_sum.get(m, 0.0))
    exp = float(cmp.get(m))
    if abs(got - exp) > TOL:
        diffs.append((m, got, exp, got - exp))
if diffs:
    detail = " / ".join(f"{m}월 재수집={g:.2f} vs CSV={e:.2f}(Δ{d:+.2f})" for m, g, e, d in diffs)
    fail("G2-②", f"월별 불일치: {detail}")
print("  [G2-②] PASS — ocCt=1 월합(for+kor)이 container_2025.csv 전체공컨TEU와 12개월 모두 일치")
print("           월별 대조(재수집 = CSV):")
for m in range(1, 13):
    print(f"             {m:2d}월  {float(month_sum.get(m,0.0)):>11,.2f} = {float(cmp.get(m)):>11,.2f}")

# --- G2-③: 연간 총합 = 991,170 ---
annual_total = float(port["공컨TEU"].sum())
if abs(annual_total - 991_170.0) > TOL:
    fail("G2-③", f"연간 총합={annual_total:,.2f} (기대 991,170.00, Δ{annual_total-991170:+.2f})")
print(f"  [G2-③] PASS — 연간 총합 {annual_total:,.2f} = 991,170.00")

# --- G3: 1~3월 부분합(ocCt=1)의 GInOut별 회귀 검산 ---
expected_q1 = {"1": 35_244.0, "2": 190_781.5, "3": 2_228.0, "4": 1_120.0}
q1 = port[port["mm"].isin([1, 2, 3])]
q1_by = q1.groupby("GInOut")["공컨TEU"].sum()
g3_diffs = []
for code, exp in expected_q1.items():
    got = float(q1_by.get(code, 0.0))
    if abs(got - exp) > TOL:
        g3_diffs.append((code, got, exp, got - exp))
if g3_diffs:
    detail = " / ".join(f"{GINOUT_LABEL[c]}={g:.2f} vs {e:.2f}(Δ{d:+.2f})" for c, g, e, d in g3_diffs)
    fail("G3", f"1~3월 GInOut별 회귀 불일치: {detail}")
print("  [G3] PASS — 1~3월 부분합(ocCt=1) GInOut별 회귀 검산 일치:")
for code, exp in expected_q1.items():
    print(f"           {GINOUT_LABEL[code]:<5} 재수집={float(q1_by.get(code,0.0)):>11,.2f} = 기준 {exp:>11,.2f}")

print("\n  ✅ 모든 검증 게이트 PASS — 집계 단계로 진행합니다.")

# =============================================================
# (3) 집계 (ocCt=1 기준)
# =============================================================
print("\n" + "=" * 60)
print(" (3) 집계 — 2025년 공컨테이너 수출입 방향 분해")
print("=" * 60)

# 월별 × GInOut 피벗 (결측 조합은 0)
pivot = port.pivot_table(index="mm", columns="GInOut", values="공컨TEU",
                         aggfunc="sum", fill_value=0.0)
for code in ["1", "2", "3", "4"]:
    if code not in pivot.columns:
        pivot[code] = 0.0
pivot = pivot[["1", "2", "3", "4"]].sort_index()

# 표시용 3분류: 수입·수출·환적(3+4)
disp = pd.DataFrame(index=pivot.index)
disp["수입"] = pivot["1"]
disp["수출"] = pivot["2"]
disp["환적"] = pivot["3"] + pivot["4"]
disp["합계"] = disp["수입"] + disp["수출"] + disp["환적"]
disp["수출비중(%)"] = (disp["수출"] / disp["합계"] * 100).round(1)

# --- 연간 4분류 요약 ---
annual = {code: float(pivot[code].sum()) for code in ["1", "2", "3", "4"]}
total4 = sum(annual.values())
print("\n[① 연간 요약 — 4분류]")
print(f"  {'구분':<8}{'TEU':>16}{'비중(%)':>10}")
print("  " + "-" * 34)
for code in ["1", "2", "3", "4"]:
    print(f"  {GINOUT_LABEL[code]:<8}{annual[code]:>16,.2f}{annual[code]/total4*100:>10.1f}")
print("  " + "-" * 34)
print(f"  {'합계':<8}{total4:>16,.2f}{100.0:>10.1f}")

# --- 헤드라인 지표 ---
imp_y, exp_y = annual["1"], annual["2"]
ratio_year = round(exp_y / imp_y, 1)                 # 수출÷수입 (환적 제외)
export_share_year = round(exp_y / total4 * 100, 1)   # 수출÷전체 4분류 합
m_ratio = (disp["수출"] / disp["수입"]).round(1)      # 월별 배율
rmin_m, rmax_m = int(m_ratio.idxmin()), int(m_ratio.idxmax())
rmin_v, rmax_v = float(m_ratio.min()), float(m_ratio.max())

print("\n[헤드라인 지표]")
print(f"  · 연간 수출÷수입 배율(환적 제외) = {ratio_year} 배  (수출 {exp_y:,.0f} / 수입 {imp_y:,.0f})")
print(f"  · 연간 수출 비중(4분류 대비)     = {export_share_year} %")
print(f"  · 월별 배율 최소 = {rmin_v} 배 ({rmin_m}월) / 최대 = {rmax_v} 배 ({rmax_m}월)")

# --- 월별 표 ---
print("\n[② 월별 표]  (단위: TEU)")
print(f"  {'월':>3}{'수입':>12}{'수출':>12}{'환적':>10}{'합계':>13}{'수출비중':>9}")
print("  " + "-" * 60)
for m in disp.index:
    r = disp.loc[m]
    print(f"  {int(m):>3}{r['수입']:>12,.1f}{r['수출']:>12,.1f}{r['환적']:>10,.1f}"
          f"{r['합계']:>13,.1f}{r['수출비중(%)']:>8.1f}%")
print("  " + "-" * 60)
print(f"  {'합':>3}{disp['수입'].sum():>12,.1f}{disp['수출'].sum():>12,.1f}"
      f"{disp['환적'].sum():>10,.1f}{disp['합계'].sum():>13,.1f}"
      f"{disp['수출'].sum()/disp['합계'].sum()*100:>8.1f}%")

# =============================================================
# (4) 차트 2매 — #01·#02 스타일(맑은 고딕) 재사용
# =============================================================
plt.rcParams["font.family"] = "Malgun Gothic"     # 한글 폰트
plt.rcParams["axes.unicode_minus"] = False        # 마이너스 기호 깨짐 방지

months = list(disp.index)

# 차트 1: 월별 수입 vs 수출 2선 꺾은선 (환적은 규모 작아 생략)
plt.figure(figsize=(10, 6))
plt.plot(months, disp["수입"], marker="o", linewidth=2, color="#2E86C1", label="수입")
plt.plot(months, disp["수출"], marker="o", linewidth=2, color="#C0392B", label="수출")
plt.title("2025년 인천항 공컨테이너 월별 수입 vs 수출 (TEU)", fontsize=15, fontweight="bold")
plt.xlabel("월")
plt.ylabel("공컨테이너 TEU")
plt.xticks(range(1, 13))
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("../reports/images/direction_chart_2025.png", dpi=150)
plt.close()
print("\n(4) 차트 저장: ../reports/images/direction_chart_2025.png")

# 차트 2: 월별 방향 구성비 100% 누적막대 (수입/수출/환적)
share = disp[["수입", "수출", "환적"]].div(disp["합계"], axis=0) * 100
plt.figure(figsize=(10, 6))
bottom_imp = share["수입"]
bottom_exp = bottom_imp + share["수출"]
plt.bar(months, share["수입"], color="#2E86C1", label="수입")
plt.bar(months, share["수출"], bottom=bottom_imp, color="#C0392B", label="수출")
plt.bar(months, share["환적"], bottom=bottom_exp, color="#7F8C8D", label="환적")
plt.title("2025년 인천항 공컨테이너 월별 방향 구성비 (100%)", fontsize=15, fontweight="bold")
plt.xlabel("월")
plt.ylabel("구성비 (%)")
plt.xticks(range(1, 13))
plt.ylim(0, 100)
plt.legend(loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.15))
plt.tight_layout()
plt.savefig("../reports/images/direction_share_2025.png", dpi=150)
plt.close()
print("(4) 차트 저장: ../reports/images/direction_share_2025.png")

print("\n완료: 검증 게이트 전부 통과 → 집계·차트 생성 마침. (보고서·커밋은 다음 지시 대기)")

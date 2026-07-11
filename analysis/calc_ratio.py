# =============================================================
#  보고서 #02: 인천항 '전체 컨테이너 대비 공컨테이너 비율' 분석
#
#  분자(공컨) : container_2025.csv       - 인천항만공사 공컨 통계 API(15157693), 월별 TEU(정밀값)
#  분모(전체) : container_total_2025.csv - 인천지방해양수산청 월별 물동량 공표(천TEU 반올림)
#
#  ※ 정밀도 한계: 분모가 '천TEU 단위 반올림' 공표치라, 비율은 소수 첫째자리까지만 신뢰한다.
# =============================================================

# pandas: 표(데이터프레임)를 다루는 도구
import pandas as pd
# matplotlib: 그래프를 그리는 도구
import matplotlib.pyplot as plt
# sys: 화면 출력 인코딩 설정
import sys

# 윈도우 콘솔에서 한글이 깨지지 않도록 출력을 UTF-8로 설정한다
sys.stdout.reconfigure(encoding="utf-8")

# 그래프 안의 한글이 깨지지 않도록 폰트를 '맑은 고딕'으로 지정한다 (윈도우 기본 한글 폰트)
plt.rcParams["font.family"] = "Malgun Gothic"
# 폰트를 바꾸면 마이너스(-) 기호가 깨질 수 있어, 이를 방지하는 설정
plt.rcParams["axes.unicode_minus"] = False

# --- 1) 데이터 불러오기 ---
# 분자: 월별 공컨 TEU (전체공컨TEU = 외국적+한국적)
empty = pd.read_csv("container_2025.csv")
# 분모: 월별 전체 컨테이너 TEU (적컨+공컨 포함, 공표 반올림값)
total = pd.read_csv("container_total_2025.csv")

# 월을 기준으로 두 표를 합친다 (같은 '월'끼리 짝지음)
df = pd.merge(
    empty[["월", "전체공컨TEU"]],          # 분자 쪽에서 월·공컨만
    total[["월", "전체컨테이너TEU"]],       # 분모 쪽에서 월·전체만
    on="월",                              # '월' 기준으로 결합
)

# --- 2) 월별 공컨 비율(%) 계산 ---
# 비율 = 공컨 ÷ 전체 × 100. round(1)로 소수 첫째자리까지만 남긴다(정밀도 한계 반영)
df["공컨비율(%)"] = (df["전체공컨TEU"] / df["전체컨테이너TEU"] * 100).round(1)

# --- 3) 연간 공컨 비율 계산 ---
# 분자 연간합계: 월별 공컨을 모두 더함
empty_year = df["전체공컨TEU"].sum()
# 분모 연간값: 공식 연간 누계 3,444천TEU = 3,444,000 TEU (월별 반올림합이 아닌 공식 누계 사용)
total_year_official = 3_444_000
# 연간 비율(소수 첫째자리)
ratio_year = round(empty_year / total_year_official * 100, 1)

# --- 4) 결과 출력 ---
print("=" * 55)
print(" 2025년 인천항 공컨테이너 비율 분석 (보고서 #02)")
print("=" * 55)
print("\n[연간 요약]")
print(f"  공컨 연간합계(분자) = {empty_year:,.0f} TEU  (공컨 API 15157693)")
print(f"  전체 연간 공식누계(분모) = {total_year_official:,} TEU  (인천지방해수청 공표)")
print(f"  ▶ 연간 공컨 비율 = {ratio_year} %")

print("\n[월별 공컨 비율]")
# 보기 좋게 정수 TEU와 비율을 표로 출력
for _, r in df.iterrows():
    print(
        f"  {int(r['월']):2d}월  공컨 {r['전체공컨TEU']:>9,.0f} / "
        f"전체 {int(r['전체컨테이너TEU']):>9,} TEU  →  {r['공컨비율(%)']:>4.1f} %"
    )

# --- 5) 월별 비율 꺾은선 그래프 ---
plt.figure(figsize=(10, 6))
# x=월, y=공컨비율. 마커(o)로 각 월 값을 점으로 표시
plt.plot(df["월"], df["공컨비율(%)"], marker="o", linewidth=2, color="#1f77b4")
# 각 점 위에 값(%) 라벨을 달아 읽기 쉽게 한다
for _, r in df.iterrows():
    plt.annotate(f"{r['공컨비율(%)']:.1f}",
                 (r["월"], r["공컨비율(%)"]),
                 textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
# 연간 평균 비율을 점선으로 표시 (기준선)
plt.axhline(ratio_year, color="gray", linestyle="--", linewidth=1,
            label=f"연간 비율 {ratio_year}%")

plt.title("2025년 인천항 월별 공컨테이너 비율", fontsize=15, fontweight="bold")
plt.xlabel("월")
plt.ylabel("공컨 비율(%)")
plt.xticks(range(1, 13))               # x축 눈금을 1~12월로
plt.grid(True, alpha=0.3)              # 옅은 격자
plt.legend()
plt.tight_layout()
# PNG로 저장 (보고서가 참조하는 이미지 폴더 reports/images에 바로 저장)
plt.savefig("../reports/images/ratio_chart_2025.png", dpi=150)
print("\n그래프 저장 완료: ../reports/images/ratio_chart_2025.png")

# --- 6) 출처·정밀도 한계 명시 ---
print("\n[출처 및 정밀도 한계]")
print("  · 분자(공컨): 인천항만공사 공컨테이너 화물 통계 API(공공데이터포털 15157693), 월별 TEU")
print("  · 분모(전체): 인천지방해양수산청 「인천항 물동량」 월별 공표자료(2025.01~12월),")
print("               '컨테이너(천TEU) 합계' = 적컨+공컨 전체. 천TEU 단위 반올림값.")
print("  · 연간 전체는 12월 공식 누계 3,444천TEU 사용(월별 반올림합 3,442천과 +2 차이는 반올림오차).")
print("  · 분모가 천TEU 반올림이라 비율은 소수 첫째자리까지만 신뢰(그 이상은 표기하지 않음).")

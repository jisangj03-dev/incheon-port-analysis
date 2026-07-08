# requests: 인터넷으로 API를 호출하는 도구
import requests
# xml.etree.ElementTree: 받은 XML을 분석(파싱)하는 도구
import xml.etree.ElementTree as ET
# pandas: 데이터를 표(데이터프레임)로 다루는 도구
import pandas as pd
# matplotlib.pyplot: 그래프를 그리는 도구. 관례상 plt 로 부른다
import matplotlib.pyplot as plt
# sys: 화면 출력 인코딩을 바꾸기 위해 사용
import sys
# config.py 에 따로 보관한 인증키를 불러온다 (코드에 키를 직접 쓰지 않기 위함)
from config import SERVICE_KEY

# 윈도우 콘솔에서 한글이 깨지지 않도록 출력을 UTF-8로 설정한다
sys.stdout.reconfigure(encoding="utf-8")

# 그래프 안의 한글이 깨지지 않도록 폰트를 '맑은 고딕'으로 지정한다 (윈도우 기본 한글 폰트)
plt.rcParams["font.family"] = "Malgun Gothic"
# 폰트를 바꾸면 마이너스(-) 기호가 깨질 수 있어, 이를 방지하는 설정
plt.rcParams["axes.unicode_minus"] = False

# ── 1) API로 2025년 월별 공컨테이너 데이터 준비 (analyze_container.py와 동일) ──

# 공컨테이너 화물 통계 API 주소 (인천항만공사)
url = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"

# 요청 파라미터: 2025년 1~12월 데이터를 한 번에 요청한다
params = {
    "serviceKey": SERVICE_KEY,  # 인증키 (config.py에서 불러옴)
    "searchYear": "2025",   # 조회 연도
    "searchStartM": "01",   # 조회 시작 월
    "searchEndM": "12",     # 조회 종료 월
    "numOfRows": "100",     # 한 페이지에 받을 최대 건수
    "pageNo": "1",          # 페이지 번호
}

# API를 호출한다
response = requests.get(url, params=params, timeout=25)

# 응답을 원본 바이트(content)로 파싱한다 → 한글 인코딩이 정확히 처리됨
root = ET.fromstring(response.content)

# 응답이 정상인지 결과 코드를 확인한다
print(f"resultCode = {root.findtext('.//resultCode')} / totalCount = {root.findtext('.//totalCount')}")

# XML 안의 모든 <item>(레코드)을 찾는다
items = root.findall(".//item")

# 각 item에서 필요한 값만 꺼내 리스트로 담는다 (아직 월마다 여러 행)
rows = []
for item in items:
    rows.append({
        "월": item.findtext("mm"),                    # 월
        "외국적공컨TEU": item.findtext("forEmpTeu"),   # 외국적 공컨테이너 TEU
        "한국적공컨TEU": item.findtext("korEmpTeu"),   # 한국적 공컨테이너 TEU
    })

# pandas 표로 만들고 값을 숫자로 바꾼다
df = pd.DataFrame(rows)
df["월"] = pd.to_numeric(df["월"])
df["외국적공컨TEU"] = pd.to_numeric(df["외국적공컨TEU"])
df["한국적공컨TEU"] = pd.to_numeric(df["한국적공컨TEU"])

# 같은 월끼리 합쳐서 12행으로 집계하고, 전체 합계 열을 추가한다
monthly = df.groupby("월")[["외국적공컨TEU", "한국적공컨TEU"]].sum().reset_index()
monthly["전체공컨TEU"] = monthly["외국적공컨TEU"] + monthly["한국적공컨TEU"]
monthly = monthly.sort_values("월").reset_index(drop=True)

# ── 2) matplotlib로 꺾은선 그래프 그리기 ──

# 그림(도화지) 크기를 가로 10 세로 6 인치로 만든다
plt.figure(figsize=(10, 6))

# 선 1: 전체 공컨 TEU (marker="o" 는 각 점에 동그라미 표시)
plt.plot(monthly["월"], monthly["전체공컨TEU"], marker="o", label="전체 공컨")
# 선 2: 외국적 공컨 TEU
plt.plot(monthly["월"], monthly["외국적공컨TEU"], marker="s", label="외국적 공컨")
# 선 3: 한국적 공컨 TEU
plt.plot(monthly["월"], monthly["한국적공컨TEU"], marker="^", label="한국적 공컨")

# 그래프 제목과 축 라벨을 한글로 단다
plt.title("2025년 인천항 월별 공컨테이너 물동량")
plt.xlabel("월")
plt.ylabel("공컨테이너 물동량 (TEU)")

# x축 눈금을 1~12로 고정해서 모든 월이 보이게 한다
plt.xticks(range(1, 13))
# 어떤 선이 무엇인지 알려주는 범례를 표시한다
plt.legend()
# 값을 읽기 쉽게 옅은 격자선을 넣는다
plt.grid(True, alpha=0.3)
# 요소들이 겹치지 않게 여백을 자동 정리한다
plt.tight_layout()

# 완성된 그래프를 PNG 파일로 저장한다 (dpi=150: 선명도)
plt.savefig("container_chart_2025.png", dpi=150)
print("→ container_chart_2025.png 파일로 저장 완료")

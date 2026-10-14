# requests: 인터넷으로 API를 호출하는 도구
import requests
# xml.etree.ElementTree: 받은 XML을 분석(파싱)하는 도구
import xml.etree.ElementTree as ET
# pandas: 데이터를 표(데이터프레임)로 다루는 도구. 관례상 pd 로 부른다
import pandas as pd
# sys: 화면 출력 인코딩을 바꾸기 위해 사용
import sys
# config.py 에 따로 보관한 인증키를 불러온다 (코드에 키를 직접 쓰지 않기 위함)
from config import SERVICE_KEY

# 윈도우 콘솔에서 한글이 깨지지 않도록 출력을 UTF-8로 설정한다
sys.stdout.reconfigure(encoding="utf-8")

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
result_code = root.findtext(".//resultCode")
result_msg = root.findtext(".//resultMsg")
print(f"resultCode = {result_code} / resultMsg = {result_msg}")
print(f"totalCount = {root.findtext('.//totalCount')}")

# XML 안의 모든 <item>(레코드)을 찾는다
items = root.findall(".//item")

# 표에 넣을 데이터를 한 줄씩 담을 빈 리스트
rows = []
# 각 item에서 필요한 값만 꺼낸다
for item in items:
    rows.append({
        "월": item.findtext("mm"),                # 월
        "반입반출": item.findtext("GInOut"),        # 반입/반출 구분코드(1~4)
        "외국적공컨TEU": item.findtext("forEmpTeu"),  # 외국적 공컨테이너 TEU
        "한국적공컨TEU": item.findtext("korEmpTeu"),  # 한국적 공컨테이너 TEU
    })

# 꺼낸 데이터로 pandas 표(데이터프레임)를 만든다
df = pd.DataFrame(rows)

# 월과 TEU 값을 숫자로 바꾼다 (정렬·계산이 가능해짐)
df["월"] = pd.to_numeric(df["월"])
df["외국적공컨TEU"] = pd.to_numeric(df["외국적공컨TEU"])
df["한국적공컨TEU"] = pd.to_numeric(df["한국적공컨TEU"])

# 월(mm) → 반입반출 순서대로 정렬하고, 기존 인덱스는 버리고 새로 매긴다
df = df.sort_values(["월", "반입반출"]).reset_index(drop=True)

# 완성된 표를 화면에 출력한다
print("\n=== 2025년 인천항 공컨테이너 TEU ===")
print(df)

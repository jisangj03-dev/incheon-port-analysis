# requests: 인터넷으로 API를 호출하는 도구
import requests
# xml.etree.ElementTree: 받은 XML 문자열을 프로그램이 다룰 수 있게 분석(파싱)해 주는 도구
import xml.etree.ElementTree as ET
# pandas: 데이터를 표(데이터프레임) 형태로 다루는 도구. 관례상 pd 라는 별명으로 부른다
import pandas as pd
# sys: 파이썬 실행 환경을 다루는 도구. 여기서는 화면 출력 인코딩을 바꾸는 데 쓴다
import sys
# config.py 에 따로 보관한 인증키를 불러온다 (코드에 키를 직접 쓰지 않기 위함)
from config import SERVICE_KEY

# 윈도우 콘솔에서 한글이 깨지지 않도록, 화면 출력을 UTF-8로 다시 설정한다
sys.stdout.reconfigure(encoding="utf-8")

# 호출할 API의 기본 주소(URL)
url = "https://apis.data.go.kr/B551504/ipaGtqyProcessAcmslt/getGtqyProcessAcmsltMnby"

# API에 함께 보낼 요청 값(파라미터)들
params = {
    "serviceKey": SERVICE_KEY,  # 인증키 (config.py에서 불러옴)
    "yyyy": "2023",  # 조회할 연도
}

# 준비한 주소와 파라미터로 API를 한 번 호출한다
response = requests.get(url, params=params)

# 받은 응답(바이트 데이터)을 XML 구조로 분석(파싱)한다. content(원본 바이트)를 쓰면 인코딩이 정확하게 처리된다
root = ET.fromstring(response.content)

# XML 안에서 <item> 태그들을 모두 찾는다. 각 item 하나가 '한 달치 레코드'다
items = root.findall(".//item")

# --- 1단계: 각 레코드(item) 안에 어떤 항목(태그)들이 있는지 먼저 확인한다 ---
print("=== 첫 번째 item 안에 들어있는 태그(항목) 목록 ===")
# 첫 번째 item의 자식 태그들을 하나씩 돌면서, 태그 이름과 값을 출력한다
for child in items[0]:
    print(f"{child.tag} = {child.text}")
print()  # 보기 좋게 빈 줄 하나 출력

# --- 2단계: 필요한 값만 뽑아서 표로 만든다 ---
# 뽑아낼 항목(태그)들을 한글 설명과 함께 정리해 둔다 (딕셔너리: 태그이름 -> 표에 쓸 열 이름)
columns = {
    "ym": "연월",
    "inoutgbnm": "수출입구분",
    "selYearSelMonth": "당월물동량",
    "selYear": "당해연도누적",
    "preYearSelMonth": "전년동월",
    "preYear": "전년누적",
}

# 표에 넣을 데이터를 한 줄(한 달)씩 모을 빈 리스트를 만든다
rows = []
# 모든 item(달)을 하나씩 돌면서 필요한 값을 꺼낸다
for item in items:
    row = {}  # 이번 달의 값을 담을 빈 딕셔너리
    # 위에서 정한 항목들만 골라서 꺼낸다
    for tag, name in columns.items():
        # item 안에서 해당 태그를 찾아 그 안의 텍스트 값을 가져온다
        value = item.findtext(tag)
        row[name] = value  # '열 이름 -> 값' 형태로 저장
    rows.append(row)  # 이번 달 데이터를 전체 리스트에 추가

# 모은 데이터로 pandas 데이터프레임(표)을 만든다
df = pd.DataFrame(rows)

# 숫자여야 하는 물동량 열들은 글자(문자열)로 들어와 있으니, 숫자로 바꿔준다 (계산·정렬이 가능해진다)
for name in ["당월물동량", "당해연도누적", "전년동월", "전년누적"]:
    df[name] = pd.to_numeric(df[name])

# --- 3단계: 완성된 표를 화면에 출력한다 ---
print("=== 2023년 인천항 물동량 표 ===")
print(df)

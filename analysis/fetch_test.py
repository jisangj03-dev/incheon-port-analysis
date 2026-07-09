# requests 라이브러리를 불러온다. (인터넷으로 데이터를 주고받을 때 쓰는 도구)
import requests
# config.py 에 따로 보관한 인증키를 불러온다 (코드에 키를 직접 쓰지 않기 위함)
from config import SERVICE_KEY

# 호출할 API의 기본 주소(URL)를 변수에 담아둔다.
url = "https://apis.data.go.kr/B551504/ipaGtqyProcessAcmslt/getGtqyProcessAcmsltMnby"

# API에 함께 보낼 요청 값(파라미터)들을 딕셔너리(사전) 형태로 준비한다.
params = {
    "serviceKey": SERVICE_KEY,  # 공공데이터포털에서 받은 인증키 (config.py에서 불러옴)
    "yyyy": "2023",  # 조회할 연도
}

# 준비한 주소와 파라미터로 API를 실제로 한 번 호출한다. (GET 방식 요청)
response = requests.get(url, params=params)

# 응답으로 받은 내용(XML 문자열)을 화면에 그대로 출력한다.
print(response.text)

# requests: 인터넷으로 API를 호출하는 도구
import requests
# xml.etree.ElementTree: 받은 XML을 분석(파싱)하는 도구
import xml.etree.ElementTree as ET
# sys: 화면 출력 인코딩을 바꾸기 위해 사용
import sys
# config.py 에 따로 보관한 인증키를 불러온다 (코드에 키를 직접 쓰지 않기 위함)
from config import SERVICE_KEY

# 윈도우 콘솔에서 한글이 깨지지 않도록 출력을 UTF-8로 설정
sys.stdout.reconfigure(encoding="utf-8")

# 검증할 새 API 주소 (해양수산부 SP-IDC: 수출입 컨테이너 월별)
URL = "https://apis.data.go.kr/1192000/SsopCargContnImxprt2/Ym"
# 인증키 (config.py에서 불러온 값을 KEY라는 이름으로 사용)
KEY = SERVICE_KEY

# 참고문서(활용가이드)에서 확인한 필수 파라미터:
#   sym = 조회시작연월(YYYYMM), eym = 조회종료연월(YYYYMM)
params = {
    "serviceKey": KEY,
    "sym": "202301",   # 2023년 1월부터
    "eym": "202312",   # 2023년 12월까지
    "numOfRows": "500",
    "pageNo": "1",
}

# API 호출 후 응답을 UTF-8 바이트로 받아 파싱 (한글 안 깨지게)
resp = requests.get(URL, params=params, timeout=25)
body = resp.content.decode("utf-8", errors="replace")
print(f"HTTP {resp.status_code}")

root = ET.fromstring(body)                         # XML 파싱
result_code = root.findtext(".//resultCode")       # 결과 코드
print("resultCode =", result_code, "/ resultMsg =", root.findtext(".//resultMsg"))

items = root.findall(".//item")                    # 데이터(item) 목록
print("totalCount =", root.findtext(".//totalCount"), "/ 받은 item 수 =", len(items))

if items:
    # 1) 첫 item에 어떤 태그(항목)가 있는지 전부 출력
    print("\n=== 첫 번째 item의 태그(항목) 목록 ===")
    tags = []
    for child in items[0]:
        tags.append(child.tag)
        print(f"  {child.tag} = {child.text}")

    # 2) 목적 3가지 자동 점검
    print("\n=== 목적 자동 점검 ===")
    # (1) 인천항 지정/필터 가능한가? → 국내 '항만' 구분 태그가 있는지
    port_tags = [t for t in tags if any(k in t.lower() for k in ["prt", "port", "hang"])]
    print(f"(1) 인천항 필터: 국내 항만 구분 태그 {port_tags if port_tags else '없음'}")
    # areaCd/areaNm은 '국내 항만'이 아니라 '해외 교역지역' 구분임을 안내
    if any(t.lower().startswith("area") for t in tags):
        sample_areas = sorted({it.findtext("areaNm") for it in items if it.findtext("areaNm")})[:6]
        print(f"    → 구분 기준은 areaNm(해외 교역지역)입니다. 예: {sample_areas}")

    # (2) 수출/수입 구분: e*(export)와 t* 두 계열이 있는지
    io = [t for t in tags if t.lower().startswith("econtn") or t.lower().startswith("tcontn")
          or t.lower().startswith("efn") or t.lower().startswith("tfn")
          or t.lower().startswith("eint") or t.lower().startswith("tint")]
    print(f"(2) 수출/수입 구분: e*(수출)·t* 계열 TEU 항목 {'있음' if io else '없음'}")
    print("    → 각 계열은 내항선(Intrvssl)/외항선(Fnshpl), 적컨(Fcontn)/공컨(Econtn)으로 다시 나뉨")

    # (3) 월 단위 여부: useYm 태그와 실제 연월 목록
    yms = sorted({it.findtext("useYm") for it in items if it.findtext("useYm")})
    print(f"(3) 월(연월) 단위: useYm 제공 → {yms}")

    print("\n=== 결론 ===")
    print("월별·수출입·TEU는 제공되지만, '국내 항만' 구분이 없어 인천항만 따로 뽑을 수 없음(전국×해외지역 합계).")
else:
    print("\n데이터가 없습니다. 응답 앞부분:", body[:300])

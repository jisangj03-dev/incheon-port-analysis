# =============================================================
#  보고서 #02: 분모(전체 컨테이너 TEU) 확보 가능성 검증
#
#  대상: 해양수산부 수출입컨테이너처리실적(15059131) - 이미 승인된 데이터.
#  핵심 질문: "이 데이터로 '인천항' 분모를 뽑을 수 있는가?"
#   1) 응답에 항만 구분 필드(항만코드/prtAtCode/항만명 등)가 있는가?
#      있다면 인천(어제 공컨 데이터 기준 prtAtCode=030)만 필터 가능한가?
#   2) 항만 필드가 없고 전국 총계만 나오면 → 분모로 못 씀.
#   3) eContnTeuTotal, tContnTeuTotal 등이 실제로 무슨 값인가?
#
#  지금 단계는 '확인만' 한다. 비율 계산은 아직 하지 않는다.
# =============================================================

# requests: 인터넷으로 API를 호출하는 도구
import requests
# xml.etree.ElementTree: 받은 XML을 분석(파싱)하는 도구
import xml.etree.ElementTree as ET
# sys: 화면 출력 인코딩을 바꾸기 위해 사용
import sys

# config.py 에 보관한 인증키를 불러온다 (코드에 키를 직접 쓰지 않기 위함)
from config import SERVICE_KEY

# 윈도우 콘솔에서 한글이 깨지지 않도록 출력을 UTF-8로 설정한다
sys.stdout.reconfigure(encoding="utf-8")

# 수출입컨테이너처리실적 - 연월(Ym) 단위 조회 주소
URL = "https://apis.data.go.kr/1192000/SsopCargContnImxprt2/Ym"

# 요청 파라미터: 2025년 1월~12월(연월 범위)로 조회한다
params = {
    "serviceKey": SERVICE_KEY,  # 인증키 (config.py에서 불러옴)
    "sym": "202501",            # 조회 시작 연월
    "eym": "202512",            # 조회 종료 연월
    "numOfRows": "500",         # 한 페이지 최대 건수 (항만별로 여러 행일 수 있어 넉넉히)
    "pageNo": "1",              # 페이지 번호
}

# API를 호출한다 (25초 안에 응답 없으면 포기)
response = requests.get(URL, params=params, timeout=25)
print(f"HTTP 상태 = {response.status_code}")

# 응답을 XML로 분석한다. content(원본 바이트)를 쓰면 한글이 정확히 처리된다
try:
    root = ET.fromstring(response.content)
except ET.ParseError:
    # XML이 아니면(에러 페이지 등) 앞부분만 보여주고 종료
    print("XML 파싱 실패. 응답 앞부분:")
    print(response.text[:500])
    sys.exit(1)

# 결과 코드/메시지/총건수를 확인한다
result_code = root.findtext(".//resultCode")
result_msg = root.findtext(".//resultMsg")
total_count = root.findtext(".//totalCount")
print(f"resultCode = {result_code} / resultMsg = {result_msg}")
print(f"totalCount = {total_count}")

# 응답 안의 모든 <item>(레코드)을 찾는다
items = root.findall(".//item")
print(f"받은 item 개수 = {len(items)}")

# item이 없으면 여기서 종료
if not items:
    print("item이 없어 확인 불가. 응답 앞부분:")
    print(response.text[:500])
    sys.exit(0)

# --- 확인 1: 첫 번째 item의 모든 태그를 원본 그대로 찍는다 ---
# 이 태그 목록에서 '항만 구분 필드'가 있는지 눈으로 확인한다.
print("\n=== [확인] 첫 번째 item의 전체 태그(원본) ===")
first = items[0]
for child in first:
    print(f"  <{child.tag}> = {child.text}")

# --- 확인 2: 항만/지역으로 보이는 필드가 있는지 자동 탐지 ---
# 항만 관련 흔한 키워드가 태그 이름에 들어있는지 훑어본다.
port_keywords = ["prt", "port", "항만", "harb", "지역", "area", "rgn", "region", "code", "cd"]
tag_names = [child.tag for child in first]
print("\n=== [확인] 항만/지역 후보 필드 자동 탐지 ===")
suspects = [t for t in tag_names if any(k.lower() in t.lower() for k in port_keywords)]
if suspects:
    print(f"  후보 태그: {suspects}")
    # 후보 필드가 item마다 어떤 값을 갖는지, 서로 다른 값(=구분 존재)인지 본다
    for tag in suspects:
        values = sorted({(it.findtext(tag) or "").strip() for it in items})
        print(f"    {tag} 의 고유값들 = {values}")
else:
    print("  → 항만/지역으로 보이는 태그가 없음 (전국 총계일 가능성).")

# --- 확인 3: 몇 개의 item이 오는지 & useYm(연월) 분포 ---
# 항만 구분이 있으면 한 달에 여러 항만 행이 있어 item이 12개보다 많을 것이다.
# 전국 총계뿐이면 한 달에 1행씩, 총 12행 안팎이 온다.
ym_values = sorted((it.findtext("useYm") or "").strip() for it in items)
print("\n=== [확인] useYm(연월) 값 분포 ===")
print(f"  useYm 목록 = {ym_values}")
print(f"  → item {len(items)}개 / 연월 고유값 {len(set(ym_values))}개")
print("     (연월당 1행이면 전국 총계, 연월당 여러 행이면 항만 등 추가 구분 존재)")

# --- 확인 4: TEU 필드 값 예시 ---
# eContnTeuTotal / tContnTeuTotal 등이 실제로 어떤 숫자인지 첫 행 기준으로 본다.
print("\n=== [확인] TEU 관련 필드 값 예시(첫 item) ===")
teu_keywords = ["teu", "contn", "cargo", "imxprt", "sum"]
for child in first:
    if any(k.lower() in child.tag.lower() for k in teu_keywords):
        print(f"  <{child.tag}> = {child.text}")

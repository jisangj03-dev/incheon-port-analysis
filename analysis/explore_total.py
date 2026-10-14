# =============================================================
#  보고서 #02 준비: "월별 전체 컨테이너 TEU" 데이터를 주는 API가
#  이미 승인받은 15003817(인천항 물동량 처리 실적)에 있는지 확인한다.
#
#  지금 단계의 목표: "전체 컨테이너 TEU를 월별로 주는 데이터가 있는가?"
#  → 각 오퍼레이션 응답의 <item> 안 태그를 '원본 그대로' 찍어 보고 판단만 한다.
#    (아직 공컨 비율 계산은 하지 않는다)
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

# 15003817(인천항 물동량 처리 실적)이 들어있는 서비스 폴더의 공통 주소.
# 우리 인증키로는 이 폴더(ipaGtqyProcessAcmslt) 하나만 호출할 수 있다.
BASE = "https://apis.data.go.kr/B551504/ipaGtqyProcessAcmslt"

# 조회할 연도 (2025년 데이터를 대상으로 한다)
YEAR = "2025"


def dump_operation(op_name: str, extra_params: dict | None = None) -> None:
    """오퍼레이션 하나를 호출해서 응답 상태와 item 태그를 원본 그대로 찍어 본다.

    op_name: 호출할 오퍼레이션 이름 (예: getAllFrghtGtqyMnthng)
    extra_params: yyyy 외에 추가로 넣어 볼 파라미터 (없으면 None)
    """
    # 화면에 구분선을 찍어 어떤 오퍼레이션을 보는지 표시한다
    print("=" * 60)
    print(f"[오퍼레이션] {op_name}")
    print("=" * 60)

    # 기본 파라미터: 인증키 + 연도 + 넉넉한 페이지 크기
    params = {
        "serviceKey": SERVICE_KEY,
        "yyyy": YEAR,
        "numOfRows": "100",
        "pageNo": "1",
    }
    # 추가 파라미터가 있으면 합친다
    if extra_params:
        params.update(extra_params)

    # API 주소를 만든다 (폴더 + 오퍼레이션)
    url = f"{BASE}/{op_name}"

    try:
        # API를 호출한다 (25초 안에 응답 없으면 포기)
        response = requests.get(url, params=params, timeout=25)
    except Exception as e:
        # 네트워크 오류 등으로 호출 자체가 실패하면 그 이유를 찍고 끝낸다
        print(f"  호출 실패: {e}\n")
        return

    # HTTP 상태 코드(200이면 정상 도달)를 찍는다
    print(f"  HTTP 상태 = {response.status_code}")

    # 응답을 XML로 분석한다. content(원본 바이트)를 쓰면 한글이 정확히 처리된다
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        # XML이 아니면(에러 페이지 등) 앞부분만 잘라서 보여준다
        print("  XML 파싱 실패. 응답 앞부분:")
        print("  " + response.text[:300].replace("\n", " "))
        print()
        return

    # 게이트웨이/서비스 결과 코드를 확인한다
    result_code = root.findtext(".//resultCode")
    result_msg = root.findtext(".//resultMsg")
    total_count = root.findtext(".//totalCount")
    print(f"  resultCode = {result_code} / resultMsg = {result_msg}")
    print(f"  totalCount = {total_count}")

    # 응답 안의 모든 <item>(레코드)을 찾는다
    items = root.findall(".//item")
    print(f"  받은 item 개수 = {len(items)}")

    # item이 하나도 없으면 여기서 끝낸다
    if not items:
        print("  → item이 없어 태그를 확인할 수 없음.\n")
        return

    # 첫 번째 item의 '모든 태그와 값'을 원본 그대로 찍는다.
    # 이 태그 이름들을 보고 "컨테이너 TEU인지 / 화물 톤수인지"를 판단한다.
    print("  --- 첫 번째 item의 태그(원본) ---")
    for child in items[0]:
        # 태그이름 = 값  형태로 한 줄씩 출력
        print(f"    <{child.tag}> = {child.text}")

    # 참고: 몇 개월치가 오는지 확인하려고 각 item의 월 후보 필드를 모아 본다.
    # (월을 뜻하는 흔한 태그 이름들을 순서대로 찾아본다)
    month_tags = ["mm", "month", "ym", "selYearSelMonth"]
    months = []
    for item in items:
        for tag in month_tags:
            value = item.findtext(tag)
            if value is not None:
                months.append(value)
                break
    if months:
        print(f"  --- item들의 월/기간 값 모음 = {months}")

    # 오퍼레이션 하나 확인이 끝나면 한 줄 띄운다
    print()


# 확인할 오퍼레이션 목록.
# 1) getAllFrghtGtqyMnthng: '전체 화물 물동량 월간'. 이게 컨테이너 TEU인지 화물 톤수인지 태그로 확인.
# 2) getGtqyProcessAcmsltMnby: 어제 '연안 물동량'으로 확인됨 — 참고로 다시 태그만 본다.
# 3) getCntanrLandngLoading: 유일한 '컨테이너' 레벨 후보 — 태그를 다시 확인해 본다.
OPERATIONS = [
    ("getAllFrghtGtqyMnthng", None),
    ("getGtqyProcessAcmsltMnby", None),
    ("getCntanrLandngLoading", None),
]

if __name__ == "__main__":
    print("\n인천항 물동량 처리 실적(15003817) — '전체 컨테이너 TEU' 존재 여부 탐색\n")
    for name, extra in OPERATIONS:
        dump_operation(name, extra)
    print("탐색 종료. 위 태그들을 보고 컨테이너 TEU 제공 여부를 판단한다.")

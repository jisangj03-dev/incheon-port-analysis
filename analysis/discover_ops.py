# =============================================================
#  보고서 #02: 15003817(인천항 물동량 처리 실적)의 '숨은 오퍼레이션' 탐지
#
#  목적: 데이터셋 설명에 "컨테이너 처리량"이 있으니, 어제 본 3개 외에
#        "월별 컨테이너 물동량(TEU)"을 주는 오퍼레이션이 있는지 실측으로 찾는다.
#
#  게이트웨이 신호(어제 파악):
#   - HTTP 404  → 그 이름의 오퍼레이션이 없음
#   - rc=00     → 오퍼레이션 존재 + 정상 응답
#   - rc=99     → 오퍼레이션 존재하나 요청 파라미터가 틀림
#   - HTTP 500  → 서비스(폴더) 자체가 키에 없음
# =============================================================

import requests
import xml.etree.ElementTree as ET
import sys
from config import SERVICE_KEY

sys.stdout.reconfigure(encoding="utf-8")

# 15003817이 들어있는 서비스 폴더(엔드포인트)
BASE = "https://apis.data.go.kr/B551504/ipaGtqyProcessAcmslt"

# 데이터셋 설명의 8개 서비스(전체화물 연/월, 처리실적 연/월, 선박 입출항 연/월,
# 컨테이너 반출입 예정, 컨테이너 양적하)를 근거로 한 후보 오퍼레이션명 목록.
# 특히 '컨테이너(Cntanr/Container)'가 들어간 이름을 넓게 시도한다.
CANDIDATES = [
    # 이미 아는 3개 (대조군)
    "getAllFrghtGtqyMnthng",
    "getGtqyProcessAcmsltMnby",
    "getCntanrLandngLoading",
    # 전체화물 연간
    "getAllFrghtGtqyYear",
    "getAllFrghtGtqyYearly",
    # 물동량 처리실적 연도별
    "getGtqyProcessAcmsltYear",
    "getGtqyProcessAcmsltYearly",
    "getGtqyProcessAcmslt",
    # 선박 입출항 통계 연/월
    "getShipInoutYear",
    "getShipInoutMnthng",
    "getShipInoutMnby",
    "getVsslInoutMnthng",
    # 컨테이너 반출입 예정 정보
    "getCntanrCarryInoutPrearnge",
    "getCntanrCarryInout",
    "getCntanrInoutPrearnge",
    "getCntanrCarryInoutInfo",
    # 컨테이너 처리량/물동량 (핵심 타깃)
    "getCntanrGtqy",
    "getCntanrGtqyMnthng",
    "getCntanrGtqyProcess",
    "getCntanrProcessAcmslt",
    "getCntanrProcessAcmsltMnby",
    "getContainerGtqy",
    "getCntanrTeu",
    "getCntanrTeuMnthng",
    "getCntanrProcess",
    "getCntanrMnby",
]


def probe(op: str) -> tuple[str, str, int, list[str]]:
    """오퍼레이션 하나를 호출해 (상태문자열, 결과메시지, item수, 태그목록)을 돌려준다."""
    url = f"{BASE}/{op}"
    # 연/월 파라미터를 둘 다 넣어 어느 쪽이든 맞으면 응답이 오도록 한다
    params = {
        "serviceKey": SERVICE_KEY,
        "yyyy": "2025",
        "sym": "202501",
        "eym": "202512",
        "numOfRows": "50",
        "pageNo": "1",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
    except Exception as e:
        return (f"호출오류:{e}", "", 0, [])

    # HTTP 404/500 이면 오퍼레이션/서비스 부재로 판단
    if r.status_code != 200:
        # 본문에서 힌트 문구를 짧게 뽑는다
        hint = r.text[:80].replace("\n", " ")
        return (f"HTTP{r.status_code}", hint, 0, [])

    # 200이면 XML을 파싱해 결과코드와 태그를 본다
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return ("XML파싱실패", r.text[:80].replace("\n", " "), 0, [])

    rc = root.findtext(".//resultCode") or "?"
    msg = (root.findtext(".//resultMsg") or "")[:40]
    items = root.findall(".//item")
    tags = [c.tag for c in items[0]] if items else []
    return (f"rc={rc}", msg, len(items), tags)


if __name__ == "__main__":
    print("15003817 오퍼레이션 탐지 시작\n")
    # 존재(rc=00 또는 rc=99)로 확인된 오퍼레이션을 따로 모은다
    exists = []
    for op in CANDIDATES:
        status, msg, n, tags = probe(op)
        mark = ""
        if status in ("rc=00", "rc=99"):
            mark = "  <== 존재"
            exists.append((op, status, n, tags))
        print(f"[{status:>10}] {op:<30} items={n} {mark}")
        # 정상(rc=00)이고 태그가 있으면 태그 목록을 함께 보여준다
        if status == "rc=00" and tags:
            print(f"             태그: {tags}")

    # 존재하는 오퍼레이션 중 '컨테이너/TEU' 태그를 가진 게 있는지 요약한다
    print("\n=== 요약: 존재하는 오퍼레이션의 컨테이너/TEU 태그 여부 ===")
    for op, status, n, tags in exists:
        teu_like = [t for t in tags if any(k in t.lower() for k in ("teu", "cntanr", "contn", "container"))]
        print(f"  {op} ({status}, items={n}) → 컨테이너/TEU 태그: {teu_like or '없음'}")

# =============================================================
#  프로브 #07-C1 — 2026년 공컨 API 커버리지 확인 (값 비노출)
#
#  목적: 보고서 #07(2026 표본외 연장 검증)의 대상 범위 S 확정.
#  규칙: ① 존재·건수·코드 조합·적재일(esbCntcDt)만 출력한다.
#        ② TEU·규격(_10/_20/_40/_99) 값은 출력·저장하지 않는다.
#           (선커밋 보전 — docs/07_주제검증.md §0 노출 사고 기록 참조)
#        ③ 원시 CSV 저장 없음(probe_02b 방식은 이번엔 쓰지 않는다).
#  근거 교훈: 0패딩("01") / 응답 성공 ≠ 데이터 완결 / 태그명 기준 접근.
# =============================================================
import os
import sys
import xml.etree.ElementTree as ET
import requests

# probe/ 상위의 analysis/ 를 경로에 넣어 config.py 의 인증키를 불러온다
HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
sys.path.insert(0, ANALYSIS)
from config import SERVICE_KEY

# 윈도우 콘솔 한글 출력이 깨지지 않도록 UTF-8로 설정
sys.stdout.reconfigure(encoding="utf-8")

URL = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"

# 2026년 1~12월을 요청한다 (0패딩 필수 — "1" 이면 오탐)
params = {"serviceKey": SERVICE_KEY, "searchYear": "2026",
          "searchStartM": "01", "searchEndM": "12",
          "numOfRows": "300", "pageNo": "1"}
root = ET.fromstring(requests.get(URL, params=params, timeout=25).content)

print("=" * 68)
print(" 프로브 #07-C1 — 2026 커버리지 (존재·건수·코드·적재일만)")
print("=" * 68)
print(f" resultCode={root.findtext('.//resultCode')}"
      f" / resultMsg={root.findtext('.//resultMsg')}"
      f" / totalCount={root.findtext('.//totalCount')}")

items = root.findall(".//item")
print(f" 받은 item 수 = {len(items)}")

# 스키마 확인: 첫 행의 태그 '이름'만 출력한다 (값은 출력하지 않는다)
if items:
    print(f" 태그 목록(첫 행) = {[c.tag for c in items[0]]}")

# 월별 구조 집계: 행수 / GInOut·ocCt 코드 조합 / 적재일(날짜까지만)
by_month = {}
for it in items:
    mm = it.findtext("mm") or "?"
    combo = f"G{it.findtext('GInOut')}/oc{it.findtext('ocCt')}"
    esb = (it.findtext("esbCntcDt") or "")[:10]
    d = by_month.setdefault(mm, {"rows": 0, "combo": set(), "esb": set()})
    d["rows"] += 1
    d["combo"].add(combo)
    d["esb"].add(esb)

for mm in sorted(by_month, key=lambda x: int(x)):
    d = by_month[mm]
    print(f"  {int(mm):02d}월: 행수={d['rows']:2d}"
          f"  조합={sorted(d['combo'])}  적재일={sorted(d['esb'])}")

print("\n ▶ 2026 존재 월 =",
      sorted(int(m) for m in by_month) if by_month else "없음")
print("(프로브 #07-C1 종료 — 값 필드는 출력·저장하지 않았다.)")

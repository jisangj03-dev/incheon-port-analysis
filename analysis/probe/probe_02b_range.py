# =============================================================
#  프로브 C2 — 공컨 API 실제 가용 기간 경계 확인
#  ※ 존재 여부·월 목록만. 데이터로 계산하지 않는다.
#
#  [핵심 교훈 2026-07-13] searchStartM 은 반드시 0패딩("01"). "1" 로 넣으면
#   API가 10·11·12월만 반환한다(존재월 문자열에 '1' 포함). 응답 성공(rc=00)
#   이라도 존재 월 목록·totalCount 를 반드시 확인해야 오탐을 피한다.
# =============================================================
import os
import sys
import xml.etree.ElementTree as ET
import requests
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
sys.path.insert(0, ANALYSIS)
from config import SERVICE_KEY

sys.stdout.reconfigure(encoding="utf-8")
URL = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"


def call_year(year: int, sm="01", em="12"):
    params = {"serviceKey": SERVICE_KEY, "searchYear": str(year),
              "searchStartM": sm, "searchEndM": em, "numOfRows": "300", "pageNo": "1"}
    root = ET.fromstring(requests.get(URL, params=params, timeout=25).content)
    items = root.findall(".//item")
    months = sorted({int(it.findtext("mm")) for it in items if it.findtext("mm")})
    return root.findtext(".//resultCode"), root.findtext(".//totalCount"), len(items), months, items


print("=" * 68)
print(" 프로브 C2 — 공컨 API 가용 기간 경계 (0패딩 searchStartM='01')")
print("=" * 68)

# 패딩 함정 재현(참고): 2025 를 '1' vs '01' 로 대조
print("\n [패딩 함정 재현] 2025년 호출")
for sm, lab in [("1", "'1'  (오탐)"), ("01", "'01' (정상)")]:
    rc, tc, n, months, _ = call_year(2025, sm=sm)
    print(f"   searchStartM={lab}: rc={rc} totalCount={tc} 월={months}")

print("\n [연도별 존재 월 — 0패딩]")
results = {}
for y in [2022, 2023, 2024, 2025, 2026]:
    rc, tc, n, months, items = call_year(y)
    results[y] = months
    print(f"   {y}: rc={rc} totalCount={tc} 행={n} 월={months if months else '없음'}")
    if y == 2026 and items:
        raw = pd.DataFrame([{c.tag: c.text for c in it} for it in items])
        out = os.path.join(HERE, "probe_2026_raw.csv")
        raw.to_csv(out, index=False, encoding="utf-8-sig")
        print(f"       2026 원시 저장: {os.path.basename(out)} ({len(raw)}행)")

m25 = results.get(2025, [])
print(f"\n 2025 존재 월 = 1~12 전부? {'예' if m25 == list(range(1, 13)) else '아니오: ' + str(m25)}")

# 가용 기간 경계
allm = []
for y in [2022, 2023, 2024, 2025, 2026]:
    for mm in results[y]:
        allm.append((y, mm))
allm.sort()
if allm:
    s, e = allm[0], allm[-1]
    print(f"\n ▶ 공컨 API 실제 가용 기간 = {s[0]}-{s[1]:02d} ~ {e[0]}-{e[1]:02d} (확인일 2026-07-13)")
    print(f"   (2022 존재 여부로 시작 경계 판단: 2022={results[2022] if results[2022] else '없음'})")

print("\n(프로브 C2 종료 — 존재 여부·월 목록만.)")

# =============================================================
#  프로브 C — 후보 ② (2024 vs 2025 공컨 연도 비교) 데이터 가용성 검증
#  공컨 API를 searchYear=2024로 1회 호출해 스키마·완결성·비율을 관측한다.
#  ※ 검증용 프로브. 판정 문장을 쓰지 않고 관측 사실만 출력한다.
# =============================================================
import os
import sys
import xml.etree.ElementTree as ET
import requests
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
sys.path.insert(0, ANALYSIS)          # config.py 는 analysis/ 에 있음(.gitignore 제외)
from config import SERVICE_KEY         # 인증키 — 하드코딩·출력 금지

sys.stdout.reconfigure(encoding="utf-8")

RAW_OUT = os.path.join(HERE, "probe_2024_raw.csv")
DIR_CSV = os.path.join(ANALYSIS, "container_2025_direction.csv")  # 2025 스키마 비교용

# 2025 원시 필드 집합(비교 기준)
cols_2025 = set(pd.read_csv(DIR_CSV, nrows=0).columns.str.strip().str.replace("﻿", ""))

# 프로브 B V5(전년동월)에서 관측된 2024년 월별 컨테이너 총계(천TEU). 출처: probe_01_terminal.py V5.
TOTAL_2024_THOUSAND = {1: 311, 2: 261, 3: 298, 4: 314, 5: 310, 6: 295,
                       7: 278, 8: 302, 9: 286, 10: 298, 11: 284, 12: 322}

print("=" * 68)
print(" 프로브 C — 후보 ② 2024 공컨 API")
print("=" * 68)

url = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"
params = {
    "serviceKey": SERVICE_KEY,
    "searchYear": "2024",
    "searchStartM": "01",   # [정정 2026-07-13] 반드시 0패딩. "1"이면 API가 10~12월만 반환(존재월에 '1' 포함되는 달) — 오탐 유발.
    "searchEndM": "12",
    "numOfRows": "200",
    "pageNo": "1",
}
resp = requests.get(url, params=params, timeout=25)
root = ET.fromstring(resp.content)
print(f"  resultCode={root.findtext('.//resultCode')} / resultMsg={root.findtext('.//resultMsg')} "
      f"/ totalCount={root.findtext('.//totalCount')}")

items = root.findall(".//item")
print(f"  받은 item(행) 수 = {len(items)}")
if not items:
    print("  [중단] 2024년 응답에 item 없음")
    sys.exit(1)

# 실제 태그 집합(첫 item 기준) + 원시 전체 추출(미사용 필드 포함)
tags_2024 = [c.tag for c in items[0]]
rows = [{c.tag: c.text for c in it} for it in items]
raw = pd.DataFrame(rows)
raw.to_csv(RAW_OUT, index=False, encoding="utf-8-sig")
print(f"  원시 저장: {os.path.basename(RAW_OUT)} ({len(raw)}행 × {len(raw.columns)}열, 가공 없음)")

print("\n--- 스키마 ---")
print(f"  2024 필드({len(tags_2024)}): {tags_2024}")
set24 = set(t.strip() for t in tags_2024)
print(f"  2025 필드({len(cols_2025)}): {sorted(cols_2025)}")
only24 = set24 - cols_2025
only25 = cols_2025 - set24
print(f"  2024에만 있는 필드: {sorted(only24) if only24 else '없음'}")
print(f"  2025에만 있는 필드: {sorted(only25) if only25 else '없음'}")
print(f"  → 핵심 축(GInOut·ocCt·forEmpTeu·korEmpTeu) 포함 동일 여부: "
      f"{'동일' if not only24 and not only25 else '차이 있음(위 참조)'}")

# 값 종류·완결성
raw["mm_n"] = pd.to_numeric(raw["mm"], errors="coerce")
months = sorted(int(m) for m in raw["mm_n"].dropna().unique())
print("\n--- 완결성·값 종류 ---")
print(f"  존재하는 월: {months}  (12개월 완결: {'예' if months == list(range(1,13)) else '아니오'})")
print(f"  GInOut 값 종류: {sorted(raw['GInOut'].dropna().unique())}")
print(f"  ocCt 값 종류: {sorted(raw['ocCt'].dropna().unique())}")

for c in ["forEmpTeu", "korEmpTeu"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
coastal = raw[raw["ocCt"] == "2"]
cmax = coastal[["forEmpTeu", "korEmpTeu"]].abs().to_numpy().max() if len(coastal) else 0.0
print(f"  ocCt=2(연안항) 행수={len(coastal)}, 실적 최대|값|={cmax}  "
      f"→ 전부 0? {'예' if cmax == 0 else '아니오'}")

# ocCt=1 기준 2024 공컨 월별·연간
port = raw[raw["ocCt"] == "1"].copy()
port["teu"] = port["forEmpTeu"].fillna(0) + port["korEmpTeu"].fillna(0)
port["mm_n"] = pd.to_numeric(port["mm"], errors="coerce")
monthly = port.groupby("mm_n")["teu"].sum()
annual = float(port["teu"].sum())
print("\n--- 2024 공컨(ocCt=1) 월별·연간 ---")
for m in range(1, 13):
    print(f"    {m:2d}월  {float(monthly.get(m, 0.0)):>12,.2f} TEU")
print(f"    연간  {annual:>12,.2f} TEU")

# 2024 공컨 비율 (분모 = 프로브 B V5의 2024 월별 총계 천TEU ×1000)
print("\n--- 2024 공컨 비율 (분자=API 공컨, 분모=hwpx 전년동월 총계) ---")
print("   월 | 공컨(TEU) | 전체(TEU) | 공컨비율%")
num_year = 0.0
den_year = 0.0
for m in range(1, 13):
    num = float(monthly.get(m, 0.0))
    den = TOTAL_2024_THOUSAND[m] * 1000
    num_year += num
    den_year += den
    print(f"   {m:2d} | {num:>9,.0f} | {den:>9,} | {num/den*100:6.1f}%")
print(f"   연간 | {num_year:>9,.0f} | {den_year:>9,.0f} | {num_year/den_year*100:6.1f}%")
print(f"   → 연간 비율이 20~40% 대역 안인가: "
      f"{'예' if 20 <= num_year/den_year*100 <= 40 else '아니오'}")

print("\n(프로브 C 종료 — 관측 사실만 출력. 판정은 문서에서.)")

# =============================================================
#  프로브 B2 — 후보 ① 보강: 검산 방식 명확화 + 2024 부두별 + '그외' 정체
#  probe_01_terminal.py 의 파싱 함수를 그대로 재사용한다(새로 짜지 않음).
#  ※ 검증용 프로브. 판정 문장 없음, 관측 사실만 출력.
# =============================================================
import os
import re
import sys
import io
import contextlib
import zipfile
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# probe_01_terminal 의 실행부(V1~V5 출력)를 삼키고 파싱 함수만 가져온다.
class _Sink(io.StringIO):
    def reconfigure(self, *a, **k):  # probe_01 이 sys.stdout.reconfigure 를 호출하므로 no-op 제공
        pass

with contextlib.redirect_stdout(_Sink()):
    import probe_01_terminal as p1

TOTAL_CSV = p1.TOTAL_CSV
V5_2024_TOTAL = {1: 311, 2: 261, 3: 298, 4: 314, 5: 310, 6: 295,
                 7: 278, 8: 302, 9: 286, 10: 298, 11: 284, 12: 322}  # 프로브 B V5 관측치(천TEU)
TERMS = ["신항", "남항", "국제여객부두", "그외"]

# 각 월 파싱 결과 캐시
M = {}
for mm in range(1, 13):
    M[mm] = p1.extract_month(mm)

tot_df = pd.read_csv(TOTAL_CSV)
tot_map = {int(r["월"]): int(r["전체컨테이너TEU"]) for _, r in tot_df.iterrows()}


def gv(d, k):
    v = d.get(k)
    return 0 if v is None else v


print("=" * 74)
print(" 프로브 B2 — 후보 ① 보강")
print("=" * 74)

# =============================================================
# (1) 검산 방식 명확화 + (a) 산술합 재계산
# =============================================================
print("\n" + "-" * 74)
print(" (1) 검산 방식 — 이전 V4 는 (b) 인쇄된 '컨테이너 합계' 행(R3)을 썼다.")
print("     [근거] probe_01_terminal.py L205: hsum = months[mm]['cur'].get('합계')")
print("     아래는 (a) 부두 산술합[신항+남항+국제여객+그외] 으로 재계산.")
print("-" * 74)
print("   월 | (a)산술합 | (b)인쇄합계행 | 차이(a-b) 천TEU")
arith = {}
for mm in range(1, 13):
    cur = M[mm]["cur"]
    a = sum(gv(cur, t) for t in TERMS)
    b = gv(cur, "합계")
    arith[mm] = a
    print(f"   {mm:2d} | {a:>8.0f} | {b:>11.0f} | {a-b:>+6.0f}")

print("\n   (a) 산술합 × 1000  vs  #02 분모(container_total_2025.csv)")
print("   월 | (a)×1000(TEU) | #02분모(TEU) | 차이(TEU) | 차이%")
for mm in range(1, 13):
    a_teu = arith[mm] * 1000
    ref = tot_map[mm]
    diff = a_teu - ref
    print(f"   {mm:2d} | {a_teu:>12,.0f} | {ref:>10,} | {diff:>+8,.0f} | {diff/ref*100:+.3f}%")

# =============================================================
# (2) '그외' 정체
# =============================================================
print("\n" + "-" * 74)
print(" (2) '그외' 구분 — 2025년 값·비중 + 원문 각주")
print("-" * 74)
go_year = 0.0
tot_year = 0.0
print("   월 | 그외(천TEU) | 합계(천TEU) | 비중%")
for mm in range(1, 13):
    cur = M[mm]["cur"]
    go = gv(cur, "그외")
    tt = gv(cur, "합계")
    go_year += go
    tot_year += tt
    sh = (go / tt * 100) if tt else 0
    print(f"   {mm:2d} | {go:>9.0f} | {tt:>9.0f} | {sh:5.1f}%")
print(f"   연간 | 그외 {go_year:>6.0f} | 합계 {tot_year:>6.0f} | 비중 {go_year/tot_year*100:.2f}%")

print("\n   [원문 각주 탐색] '그 외/그외' 및 각주 마커(*, **, ※, 주)) 텍스트 런:")
data1 = zipfile.ZipFile(os.path.join(p1.DOWNLOADS, p1.fname(1))).read("Contents/section0.xml").decode("utf-8")
runs = re.findall(r"<hp:t>(.*?)</hp:t>", data1, re.DOTALL)
found = []
for t in runs:
    s = t.strip()
    if not s:
        continue
    if ("그" in s and "외" in s) or s.startswith("*") or s.startswith("※") or "주)" in s or "**" in s or "컨테이너" in s:
        found.append(s)
seen = set()
for s in found:
    if s not in seen:
        seen.add(s)
        print(f"     │ {s}")
if not any(("그" in s and "외" in s and len(s) > 3) for s in found):
    print("     → '그외'를 설명하는 별도 각주·괄호 표기: 각주 없음(라벨 '그  외'만 존재).")

# =============================================================
# (3) 2024 부두별 매트릭스
# =============================================================
print("\n" + "-" * 74)
print(" (3) 2024 부두별 매트릭스 (전년동월 열, 단위 천TEU)")
print("-" * 74)
print("   월 |   신항 |   남항 | 국제여객 |  그외 | 산술합 | V5총계 | 차이")
miss = []
y24 = {}
for mm in range(1, 13):
    prev = M[mm]["prev"]
    row = {t: prev.get(t) for t in TERMS}
    y24[mm] = row
    for t in TERMS:
        if row[t] is None:
            miss.append((mm, t))
    a = sum((row[t] or 0) for t in TERMS)
    v5 = V5_2024_TOTAL[mm]
    print(f"   {mm:2d} | {gv(prev,'신항'):>5.0f} | {gv(prev,'남항'):>5.0f} | "
          f"{gv(prev,'국제여객부두'):>6.0f} | {gv(prev,'그외'):>4.0f} | {a:>5.0f} | {v5:>5.0f} | {a-v5:>+4.0f}")
print(f"   결측 셀: {miss if miss else '없음 (12개월 × 4구분 = 48셀 전부 추출)'}")

# '24년 연간' 열의 부두별 값 (매 파일 동일해야 함) + 24년 월별 합과 대조
print("\n   [24년 연간 열] 부두별 값 (파일 간 일관성 + 월별합 대조)")
# 연간열은 레이아웃 무관하게 라벨행의 첫 숫자 열(24연간). block 재파싱.
def annual24(block, layout):
    out = {}
    for r in block:
        if not r:
            continue
        f = r[0].replace(" ", "")
        # 24연간 = 라벨 뒤 첫 숫자열. 소계행은 '소 계' 셀이 라벨 다음에 옴.
        vals = [p1.to_num(c) for c in r]
        nums = [v for v in vals if v is not None]
        val = nums[0] if nums else None
        key = None
        if f == "신항": key = "신항"
        elif f == "남항": key = "남항"
        elif f.startswith("국제여객"): key = "국제여객부두"
        elif f.startswith("그외"): key = "그외"
        if key:
            out[key] = val
    return out
ann_by_file = {}
for mm in range(1, 13):
    ann_by_file[mm] = annual24(M[mm]["block"], M[mm]["layout"])
for t in TERMS:
    vals = [ann_by_file[mm].get(t) for mm in range(1, 13)]
    uniq = sorted(set(v for v in vals if v is not None))
    msum = sum((y24[mm][t] or 0) for mm in range(1, 13))
    a0 = uniq[0] if len(uniq) == 1 else None
    print(f"     {t:>8}: 연간열 고유값={uniq}  · 24월별합={msum:.0f}  "
          f"· 차이(연간-월합)={(a0-msum):+.0f}" if a0 is not None else
          f"     {t:>8}: 연간열 값이 파일마다 다름 {uniq} · 24월별합={msum:.0f}")

# =============================================================
# (4) 증감률 대조 (참고용)
# =============================================================
print("\n" + "-" * 74)
print(" (4) 증감률 대조 (참고용) — 계산(25/24-1) vs 원문 증감률 열, 최대 절대차")
print("-" * 74)
def printed_rate(block, layout):
    """터미널별 인쇄 증감률(당월). Layout B: cells[-2], Layout A: cells[-1]."""
    out = {}
    for r in block:
        if not r:
            continue
        f = r[0].replace(" ", "")
        key = None
        if f == "신항": key = "신항"
        elif f == "남항": key = "남항"
        elif f.startswith("국제여객"): key = "국제여객부두"
        elif f.startswith("그외"): key = "그외"
        if key is None:
            continue
        cell = r[-2] if layout == "B" else r[-1]
        out[key] = p1.to_num(cell)
    return out
maxdiff = 0.0
where = ""
for mm in range(1, 13):
    pr = printed_rate(M[mm]["block"], M[mm]["layout"])
    cur, prev = M[mm]["cur"], M[mm]["prev"]
    for t in TERMS:
        c, p, rr = cur.get(t), prev.get(t), pr.get(t)
        if c is None or p in (None, 0) or rr is None:
            continue
        calc = (c / p - 1) * 100
        d = abs(calc - rr)
        if d > maxdiff:
            maxdiff = d; where = f"{mm}월 {t} (계산{calc:.1f} vs 원문{rr:.1f})"
print(f"   최대 절대차 = {maxdiff:.2f}%p  @ {where}")
print("   (원문 증감률은 소수1자리 반올림 인쇄값이라 소폭 차이는 정상)")

print("\n(프로브 B2 종료 — 관측 사실만. 판정은 문서에서.)")

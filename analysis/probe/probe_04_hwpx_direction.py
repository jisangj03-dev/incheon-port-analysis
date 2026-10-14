# =============================================================
#  프로브 D — 후보 ① V7: hwpx 월별 공표자료의 '방향별(수입/수출/환적) 컨테이너 표' 탐색
#
#  목적: hwpx 안의 모든 표를 열거하고, 컨테이너를 수입/수출/환적/연안으로
#        분해한 표가 존재하는지 확인한다. 존재하면 월 단위 수지 시계열이 가능해진다.
#
#  ※ 검증용 프로브. 판정 문장을 쓰지 않고 관측 사실만 출력한다.
#  ※ 라벨/단위가 원문에서 명확히 안 읽히면 추정하지 말고 '불명'으로 표시한다.
# =============================================================
import os
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")

DIR_KEYS = ["수입", "수출", "환적", "연안"]
CON_KEYS = ["컨테이너", "TEU"]


def fname(mm: int) -> str:
    return f"인천항 물동량('25.{mm:02d}월)_홈페이지용.hwpx"


def cell_text(tc: str) -> str:
    return " ".join(re.findall(r"<hp:t>(.*?)</hp:t>", tc, re.DOTALL)).strip()


def table_grid(tbl: str):
    rows = []
    for tr in re.findall(r"<hp:tr\b.*?</hp:tr>", tbl, re.DOTALL):
        cells = [cell_text(c) for c in re.findall(r"<hp:tc\b.*?</hp:tc>", tr, re.DOTALL)]
        rows.append(cells)
    return rows


def all_tables(data: str):
    return [table_grid(t) for t in re.findall(r"<hp:tbl\b.*?</hp:tbl>", data, re.DOTALL)]


def flat(grid):
    return " ".join(" ".join(r) for r in grid)


def read_hwpx(mm: int):
    path = os.path.join(DOWNLOADS, fname(mm))
    if not os.path.exists(path):
        return None
    return zipfile.ZipFile(path).read("Contents/section0.xml").decode("utf-8")


print("=" * 82)
print(" 프로브 D — hwpx 방향별 컨테이너 표 탐색 (후보 ① V7)")
print("=" * 82)
print(f"  hwpx 위치: {DOWNLOADS}")

# -------------------- D1: 표 인벤토리 --------------------
print("\n" + "-" * 82)
print(" D1  2025년 1월 hwpx — 전체 표 인벤토리")
print("-" * 82)
data1 = read_hwpx(1)
if data1 is None:
    print("   [실패] 파일 없음 — 이후 단계 중단")
    sys.exit(0)

tables1 = all_tables(data1)
print(f"   총 표 개수: {len(tables1)}")
print("   idx | 행수 | 컨테이너kw | 방향kw            | 1행 라벨(앞 6셀)")
cand = []
for i, g in enumerate(tables1):
    body = flat(g)
    has_con = [k for k in CON_KEYS if k in body]
    has_dir = [k for k in DIR_KEYS if k in body]
    head = (g[0][:6] if g else [])
    print(f"   {i:>3} | {len(g):>4} | {','.join(has_con) if has_con else '-':<10} | "
          f"{','.join(has_dir) if has_dir else '-':<17} | {head}")
    if has_con and len(has_dir) >= 2:
        cand.append(i)

print(f"\n   → 컨테이너 키워드 + 방향 키워드 2종 이상을 함께 가진 표: {cand if cand else '없음'}")

# -------------------- D2: 후보 표 전문 --------------------
print("\n" + "-" * 82)
print(" D2  후보 표 원문 그대로 (행 라벨·열 머리글·숫자 전부)")
print("-" * 82)
if not cand:
    print("   후보 표 없음 — hwpx에 방향별 컨테이너 표가 존재하지 않는 것으로 관측됨.")
    print("   (주의: 이 부정 관측은 D1의 키워드 매칭에 의존한다. D3에서 원문 텍스트로 교차 확인한다.)")
else:
    for i in cand:
        print(f"\n   ===== 표 idx={i} =====")
        for ri, r in enumerate(tables1[i]):
            print(f"   R{ri:2d} ({len(r)}셀): {r}")

# -------------------- D3: 부정 관측 교차검증 --------------------
print("\n" + "-" * 82)
print(" D3  교차검증 — 원문 텍스트 런에서 방향 키워드 (키워드 매칭 실패 대비)")
print("-" * 82)
runs = [t.strip() for t in re.findall(r"<hp:t>(.*?)</hp:t>", data1, re.DOTALL) if t.strip()]
print(f"   텍스트 런 총 {len(runs)}개")
hits = [s for s in runs if any(k in s for k in DIR_KEYS)]
seen, shown = set(), 0
for s in hits:
    if s in seen:
        continue
    seen.add(s)
    print(f"     │ {s}")
    shown += 1
    if shown >= 40:
        print("     │ ... (이하 생략)")
        break
print(f"   → 방향 키워드를 포함한 고유 텍스트 런: {len(seen)}개")

# -------------------- D4: 단위 표기 --------------------
print("\n" + "-" * 82)
print(" D4  단위 표기")
print("-" * 82)
for u in ["천TEU", "TEU", "천톤", "톤"]:
    print(f"   '{u}' 등장: {'있음' if u in data1 else '없음'}")

# -------------------- D5: 12월 파일 --------------------
print("\n" + "-" * 82)
print(" D5  2025년 12월 hwpx — 표 인벤토리 (누계 열 = 연간값)")
print("-" * 82)
data12 = read_hwpx(12)
if data12 is None:
    print("   [실패] 12월 파일 없음")
else:
    tables12 = all_tables(data12)
    print(f"   총 표 개수: {len(tables12)}")
    cand12 = []
    for i, g in enumerate(tables12):
        body = flat(g)
        has_con = [k for k in CON_KEYS if k in body]
        has_dir = [k for k in DIR_KEYS if k in body]
        if has_con and len(has_dir) >= 2:
            cand12.append(i)
    print(f"   → 컨테이너+방향 표: {cand12 if cand12 else '없음'}")
    for i in cand12:
        print(f"\n   ===== 12월 표 idx={i} =====")
        for ri, r in enumerate(tables12[i]):
            print(f"   R{ri:2d} ({len(r)}셀): {r}")

print("\n(프로브 D 종료 — 관측 사실만 출력. 판정은 문서에서.)")

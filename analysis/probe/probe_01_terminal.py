# =============================================================
#  프로브 B — 후보 ① (터미널별 신항/남항/국제여객부두) 데이터 가용성 검증
#  hwpx 원문(Downloads, 2025년 1~12월)에서 컨테이너 터미널 표를 추출·검산한다.
#  ※ 검증용 프로브. 판정 문장을 쓰지 않고 관측 사실만 출력한다.
#  ※ 라벨/단위가 원문에서 명확히 안 읽히면 추정하지 말고 실패로 표시한다.
# =============================================================
import os
import re
import sys
import zipfile
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
TOTAL_CSV = os.path.join(ANALYSIS, "container_total_2025.csv")  # #02 분모 산출물


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


def find_terminal_table(data: str):
    for tbl in re.findall(r"<hp:tbl\b.*?</hp:tbl>", data, re.DOTALL):
        if "신항" in tbl and "국제여객" in tbl:
            return table_grid(tbl)
    return None


def to_num(s: str):
    """콤마 제거 후 정수화. 빈칸→None. △/- 는 음수(증감률용)."""
    s = (s or "").strip()
    if s == "" or s == "-":
        return None
    neg = s.startswith("△") or s.startswith("-") or s.startswith("▲")
    s2 = re.sub(r"[^0-9.]", "", s)
    if s2 == "":
        return None
    v = float(s2)
    return -v if neg else v


def container_block(grid):
    """컨테이너 합계 행 ~ 벌크 합계 행 사이만 반환(벌크의 남항/내항 혼입 방지)."""
    start = end = None
    for i, r in enumerate(grid):
        first = r[0] if r else ""
        if start is None and ("컨테이너" in first and "합계" in first):
            start = i
        elif start is not None and "벌크" in first:
            end = i
            break
    if start is None:
        return None
    return grid[start:(end if end is not None else len(grid))]


# 열 배치는 월별로 2가지:
#  · 레이아웃 A(1월, 당월≡누계로 병합): [라벨…, 24연간, 24당월, 25당월, 증감]      → 당월=-2, 전년동월=-3
#  · 레이아웃 B(2~12월, 당월/누계 분리): [라벨…, 24연간, 24당월, 24누계, 25당월, 25누계, 증감당월, 증감누계]
#                                                                              → 당월=-4, 전년동월=-6
# 레이아웃은 '컨테이너 합계' 행의 셀 수로 판별(≥8 → B, 아니면 A). 전월 검출값은 모두 '당월'(누계 아님).
def row_vals(cells, layout):
    if layout == "B":
        cur = to_num(cells[-4]) if len(cells) >= 4 else None
        prev = to_num(cells[-6]) if len(cells) >= 6 else None
    else:  # A
        cur = to_num(cells[-2]) if len(cells) >= 2 else None
        prev = to_num(cells[-3]) if len(cells) >= 3 else None
    return cur, prev


TERM_KEYS = ["신항", "SNCT", "HJIT", "남항", "E1CT", "ICT", "국제여객부두", "그외", "합계"]


def extract_month(mm: int):
    path = os.path.join(DOWNLOADS, fname(mm))
    if not os.path.exists(path):
        return {"error": "파일없음"}
    data = zipfile.ZipFile(path).read("Contents/section0.xml").decode("utf-8")
    grid = find_terminal_table(data)
    if grid is None:
        return {"error": "터미널표 못찾음"}
    block = container_block(grid)
    if block is None:
        return {"error": "컨테이너 블록 못찾음"}
    unit = "천TEU" if "천TEU" in data else "?"
    # 레이아웃 판별: 컨테이너 합계 행의 셀 수 (≥8 → B, 아니면 A)
    layout = "A"
    for r in block:
        f0 = (r[0] if r else "").replace(" ", "")
        if f0.startswith("컨테이너") and "합계" in f0:
            layout = "B" if len(r) >= 8 else "A"
            break
    out = {"unit": unit, "layout": layout, "block": block, "cur": {}, "prev": {}}
    for r in block:
        if not r:
            continue
        first = r[0].replace(" ", "")
        cur, prev = row_vals(r, layout)
        if first.startswith("컨테이너") and "합계" in first:
            out["cur"]["합계"], out["prev"]["합계"] = cur, prev
        elif first == "신항":
            out["cur"]["신항"], out["prev"]["신항"] = cur, prev
        elif first == "SNCT":
            out["cur"]["SNCT"], out["prev"]["SNCT"] = cur, prev
        elif first == "HJIT":
            out["cur"]["HJIT"], out["prev"]["HJIT"] = cur, prev
        elif first == "남항":
            out["cur"]["남항"], out["prev"]["남항"] = cur, prev
        elif first == "E1CT":
            out["cur"]["E1CT"], out["prev"]["E1CT"] = cur, prev
        elif first == "ICT":
            out["cur"]["ICT"], out["prev"]["ICT"] = cur, prev
        elif first.startswith("국제여객"):
            out["cur"]["국제여객부두"], out["prev"]["국제여객부두"] = cur, prev
        elif first.startswith("그외"):
            out["cur"]["그외"], out["prev"]["그외"] = cur, prev
    return out


print("=" * 72)
print(" 프로브 B — 후보 ① 터미널별(신항/남항/국제여객부두)")
print("=" * 72)
print(f"  hwpx 위치: {DOWNLOADS}")

# -------------------- V1: 파일 존재 --------------------
print("\n" + "-" * 72)
print(" V1  파일 존재 (2025년 1~12월)")
print("-" * 72)
present = {}
for mm in range(1, 13):
    p = os.path.join(DOWNLOADS, fname(mm))
    present[mm] = os.path.exists(p)
    print(f"   {mm:2d}월  {'있음' if present[mm] else '없음 ✗'}   {fname(mm)}")
print(f"   → 확보 {sum(present.values())}/12")

# -------------------- V2: 1월 원문 그대로 --------------------
print("\n" + "-" * 72)
print(" V2  2025년 1월 컨테이너 터미널 표 — 원문 그대로 (행 라벨·열 머리글·숫자 전부)")
print("-" * 72)
data1 = zipfile.ZipFile(os.path.join(DOWNLOADS, fname(1))).read("Contents/section0.xml").decode("utf-8")
grid1 = find_terminal_table(data1)
for ri, r in enumerate(grid1):
    print(f"   R{ri:2d} ({len(r)}셀): {r}")
print(f"   단위 근거: 원문에 '천TEU' 표기 {'존재' if '천TEU' in data1 else '없음'} "
      f"(컨테이너 행 라벨 '컨테이너 ** (천TEU) 합계').")

# -------------------- V3: 12개월 매트릭스 + 검산 --------------------
print("\n" + "-" * 72)
print(" V3  12개월 × 부두별 당월 매트릭스 (단위: 천TEU) + 행내 검산")
print("-" * 72)
hdr = "월 | " + " ".join(f"{k:>7}" for k in ["신항", "SNCT", "HJIT", "남항", "E1CT", "ICT", "국제여객", "그외", "합계"])
print("   " + hdr)
months = {}
for mm in range(1, 13):
    res = extract_month(mm)
    if "error" in res:
        print(f"   {mm:2d}  [실패] {res['error']}")
        continue
    c = res["cur"]
    months[mm] = res
    def g(k):
        v = c.get(k)
        return 0 if v is None else v
    line = (f"   {mm:2d} | "
            + f"{g('신항'):7.0f} {g('SNCT'):7.0f} {g('HJIT'):7.0f} "
            + f"{g('남항'):7.0f} {g('E1CT'):7.0f} {g('ICT'):7.0f} "
            + f"{g('국제여객부두'):7.0f} {g('그외'):7.0f} {g('합계'):7.0f}")
    # 검산: 신항=SNCT+HJIT / 남항=E1CT+ICT / 합계=신항+남항+국제+그외
    chk_sin = g('SNCT') + g('HJIT') - g('신항')
    chk_nam = g('E1CT') + g('ICT') - g('남항')
    chk_tot = g('신항') + g('남항') + g('국제여객부두') + g('그외') - g('합계')
    flags = []
    if abs(chk_sin) > 0.5: flags.append(f"신항Δ{chk_sin:+.0f}")
    if abs(chk_nam) > 0.5: flags.append(f"남항Δ{chk_nam:+.0f}")
    if abs(chk_tot) > 0.5: flags.append(f"합계Δ{chk_tot:+.0f}")
    print(line + f"  [{res['layout']}]" + ("  ✓" if not flags else "  ⚠ " + " ".join(flags)))

# -------------------- V4: #02 분모와 대조 --------------------
print("\n" + "-" * 72)
print(" V4  검산 — 부두별 합계(당월) vs #02 분모(container_total_2025.csv)")
print("-" * 72)
tot_df = pd.read_csv(TOTAL_CSV)
tot_map = {int(r["월"]): int(r["전체컨테이너TEU"]) for _, r in tot_df.iterrows()}
print("   월 | hwpx합계(천TEU) | hwpx×1000(TEU) | #02분모(TEU) | 차이(TEU) | 차이%")
for mm in range(1, 13):
    if mm not in months:
        print(f"   {mm:2d} | (추출실패)")
        continue
    hsum = months[mm]["cur"].get("합계") or 0
    h_teu = hsum * 1000
    ref = tot_map.get(mm)
    diff = h_teu - ref
    pct = (diff / ref * 100) if ref else float("nan")
    print(f"   {mm:2d} | {hsum:>12.0f} | {h_teu:>12,.0f} | {ref:>10,} | {diff:>+9,.0f} | {pct:+.3f}%")

# -------------------- V5: 전년동월(2024) 월별 총계 --------------------
print("\n" + "-" * 72)
print(" V5  전년동월 열 → 2024년 월별 컨테이너 총계(천TEU)")
print("-" * 72)
print("   월 | 2024합계(전년동월) | 2024신항 | 2024남항 | 2024국제여객")
y2024_total = {}
for mm in range(1, 13):
    if mm not in months:
        print(f"   {mm:2d} | (추출실패)")
        continue
    p = months[mm]["prev"]
    y2024_total[mm] = p.get("합계")
    def gp(k):
        v = p.get(k)
        return 0 if v is None else v
    print(f"   {mm:2d} | {gp('합계'):>16.0f} | {gp('신항'):>7.0f} | {gp('남항'):>7.0f} | {gp('국제여객부두'):>7.0f}")
vals = [v for v in y2024_total.values() if v is not None]
print(f"   → 2024 연간(전년동월 12개월 합) = {sum(vals):,.0f} 천TEU  (12개월 추출: {len(vals)}/12)")

print("\n(프로브 B 종료 — 관측 사실만 출력. 판정은 문서에서.)")

# =============================================================
#  보고서 #07 — 3단계: X-CHECK 독립 판정 (클로드 코드 측)
#
#  기준: docs/07_주제검증.md §4 (blob c95bbfc85...)
#  입력: analysis/container_2026_direction.csv (2단계 정식 수집분)
#        analysis/container_2025_direction.csv (읽기 전용 — ⓒ용 덤프만)
#
#  정의: 방향별 TEU = forEmpTeu + korEmpTeu
#        규격 박스   = forEmp_x + korEmp_x
#        40ft 비중   = _40합 ÷ (_10+_20+_40+_99 합)   [박스 수 기준, TEU 금지]
#        모집단 = ocCt=1 · 수입 = GInOut 1 · 수출 = GInOut 2
#        비중·격차는 반올림 전 값으로 계산 후 소수 1자리 표기
#        분모 0 월 = 미성립(보수 처리) · 저볼륨 월 제외 금지
#  월(mm)은 문자열로만 다룬다("01"~"06").
# =============================================================
import os
import sys
import csv

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_2026 = os.path.join(HERE, "container_2026_direction.csv")
CSV_2025 = os.path.join(HERE, "container_2025_direction.csv")

MONTHS = ["01", "02", "03", "04", "05", "06"]
SPEC = ["_10", "_20", "_40", "_99"]


def load(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def teu(r):
    return float(r["forEmpTeu"]) + float(r["korEmpTeu"])


def box(r, suf):
    return int(float(r[f"forEmp{suf}"])) + int(float(r[f"korEmp{suf}"]))


def num_den(rows):
    """40ft 분자(=_40 박스합) / 분모(=_10+_20+_40+_99 박스합). 정수."""
    n = sum(box(r, "_40") for r in rows)
    d = sum(box(r, s) for r in rows for s in SPEC)
    return n, d


def sel(rows, mm=None, g=None):
    out = [r for r in rows if r["ocCt"] == "1"]
    if mm is not None:
        out = [r for r in out if r["mm"] == mm]      # 문자열 비교
    if g is not None:
        out = [r for r in out if r["GInOut"] == g]
    return out


# =============================================================
# A. ⓒ용 2025 상반기 원본 덤프 (파생값 계산 없음)
# =============================================================
print("=" * 74)
print(" [A1] container_2025_direction.csv — mm '01'~'06' · ocCt=1 · GInOut∈{1,2} 원본 덤프")
print("=" * 74)
with open(CSV_2025, "r", encoding="utf-8-sig", newline="") as f:
    lines = f.read().split("\r\n")
header = lines[0]
print(header)
hit = 0
for ln in lines[1:]:
    if not ln.strip():
        continue
    c = ln.split(",")
    mm, ginout, occt = c[1], c[2], c[3]          # 헤더 순서 CORE14 기준
    if mm in MONTHS and occt == "1" and ginout in ("1", "2"):
        print(ln)
        hit += 1
print(f"\n  해당 행 수 = {hit}행 (기대 12행)  {'일치' if hit == 12 else '★불일치★'}")

# =============================================================
# B. X-CHECK — 2026 정식 수집분으로 §4 독립 산출
# =============================================================
d26 = load(CSV_2026)
print("\n" + "=" * 74)
print(" [B] X-CHECK — container_2026_direction.csv 로 §4 판정 독립 산출")
print("=" * 74)
print(f"  입력 행수 = {len(d26)} / ocCt=1 행수 = {len(sel(d26))}")

# ---- B1: V1 (2026-06 단독) ----
imp06 = sum(teu(r) for r in sel(d26, "06", "1"))
exp06 = sum(teu(r) for r in sel(d26, "06", "2"))
print("\n  [B1] V1 (방향 지속, 2026-06 단독) — 수출 TEU > 수입 TEU ?")
print(f"     수입 TEU (G1) = {imp06!r}")
print(f"     수출 TEU (G2) = {exp06!r}")
v1 = exp06 > imp06
print(f"     판정: 수출 {exp06!r} {'>' if v1 else '≤'} 수입 {imp06!r}  →  V1 {'PASS' if v1 else 'FAIL'}")

# ---- B2: V2 (2026-06 단독) ----
print("\n  [B2] V2 (배율 하한, 2026-06 단독) — 배율 ≥ 3.9 ?")
if imp06 == 0:
    print("     분모 0 → 미성립(보수 처리)")
    v2 = False
    ratio06 = None
else:
    ratio06 = exp06 / imp06
    v2 = ratio06 >= 3.9
    print(f"     배율 = {exp06!r} ÷ {imp06!r} = {ratio06:.3f}")
    print(f"     판정: {ratio06:.3f} {'≥' if v2 else '<'} 3.9  →  V2 {'PASS' if v2 else 'FAIL'}")

# ---- B3: V3 (01~06 월별) ----
print("\n  [B3] V3 (규격 격차 부호, 월별 전수) — (수입 40ft 비중 − 수출 40ft 비중) > 0 ?")
hdr = (f"     {'월':<4}{'수입분자':>9}{'수입분모':>9}{'수입비중%':>10}"
       f"{'수출분자':>10}{'수출분모':>10}{'수출비중%':>10}{'격차%p':>9}  성립")
print(hdr)
print("     " + "-" * (len(hdr) - 5))
v3_ok = 0
gaps = {}
for mm in MONTHS:
    inum, iden = num_den(sel(d26, mm, "1"))
    enum, eden = num_den(sel(d26, mm, "2"))
    if iden == 0 or eden == 0:
        print(f"     {mm:<4}{inum:>9}{iden:>9}{'분모0':>10}{enum:>10}{eden:>10}{'분모0':>10}{'—':>9}  미성립(보수)")
        gaps[mm] = None
        continue
    ish = inum / iden * 100.0
    esh = enum / eden * 100.0
    gap = ish - esh
    gaps[mm] = gap
    ok = gap > 0
    v3_ok += 1 if ok else 0
    print(f"     {mm:<4}{inum:>9}{iden:>9}{ish:>10.1f}{enum:>10}{eden:>10}{esh:>10.1f}"
          f"{gap:>9.1f}  {'성립' if ok else '미성립'}")
print(f"\n     성립 월 수 = {v3_ok}/6  →  V3 {'PASS' if v3_ok == 6 else 'FAIL'}")

# ---- B4: V4 (S 합산) ----
print("\n  [B4] V4 (규격 격차 크기, S=2026-01~06 합산) — 합산 격차 ≥ +5.0%p ?")
Inum, Iden = num_den([r for r in sel(d26, g="1") if r["mm"] in MONTHS])
Enum, Eden = num_den([r for r in sel(d26, g="2") if r["mm"] in MONTHS])
print(f"     수입 분자 = {Inum} / 수입 분모 = {Iden}")
print(f"     수출 분자 = {Enum} / 수출 분모 = {Eden}")
if Iden == 0 or Eden == 0:
    print("     분모 0 → 미성립(보수 처리)")
    v4 = False
else:
    Ish, Esh = Inum / Iden * 100.0, Enum / Eden * 100.0
    Gap = Ish - Esh
    v4 = Gap >= 5.0
    print(f"     수입 비중 = {Ish:.1f}% / 수출 비중 = {Esh:.1f}%")
    print(f"     합산 격차 = {Gap:.1f}%p")
    print(f"     판정: {Gap:.1f} {'≥' if v4 else '<'} 5.0  →  V4 {'PASS' if v4 else 'FAIL'}")

# ---- B5: 참고 ⓐ 2026-01~05 월별 ----
print("\n  [B5] 참고 ⓐ — 2026-01~05 월별 수입/수출 TEU · 배율")
print("     ※ docs/07_주제검증.md §0 노출 이력 ② 별표 대상 구간(검증 아님, 확정 집계)")
print(f"     {'월':<4}{'수입TEU':>14}{'수출TEU':>14}{'배율':>10}")
print("     " + "-" * 42)
for mm in ["01", "02", "03", "04", "05"]:
    i = sum(teu(r) for r in sel(d26, mm, "1"))
    e = sum(teu(r) for r in sel(d26, mm, "2"))
    rr = f"{e / i:.3f}" if i else "분모0"
    print(f"     {mm:<4}{i:>14.2f}{e:>14.2f}{rr:>10}")

# ---- B6: 참고 ⓑ 01~06 합산 ----
print("\n  [B6] 참고 ⓑ — 2026-01~06 합산")
Itot = sum(teu(r) for r in sel(d26, g="1") if r["mm"] in MONTHS)
Etot = sum(teu(r) for r in sel(d26, g="2") if r["mm"] in MONTHS)
print(f"     합산 수입 TEU = {Itot!r}")
print(f"     합산 수출 TEU = {Etot!r}")
print(f"     합산 배율     = {Etot / Itot:.3f}" if Itot else "     합산 배율 = 분모0")

# ---- B7: 환적 별도 ----
print("\n  [B7] 환적 별도 (ocCt=1, 2026-01~06)")
g3 = sum(teu(r) for r in sel(d26, g="3") if r["mm"] in MONTHS)
g4 = sum(teu(r) for r in sel(d26, g="4") if r["mm"] in MONTHS)
print(f"     G3(수입환적) 합계 TEU = {g3!r}")
print(f"     G4(수출환적) 합계 TEU = {g4!r}")
print(f"     환적계(G3+G4)         = {g3 + g4!r}")

# ---- 요약 ----
print("\n" + "=" * 74)
print(" [판정 요약] 클로드 코드 측 독립 산출 (X-CHECK 대조용)")
print("=" * 74)
print(f"   V1 = {'PASS' if v1 else 'FAIL'}")
print(f"   V2 = {'PASS' if v2 else 'FAIL'}" + (f"  (배율 {ratio06:.3f})" if ratio06 is not None else ""))
print(f"   V3 = {'PASS' if v3_ok == 6 else 'FAIL'}  (성립 {v3_ok}/6)")
print(f"   V4 = {'PASS' if v4 else 'FAIL'}")
print("\n  ⛔ ⓒ(전년 동기 대비) 는 산출하지 않았다 — A1 덤프를 챗이 처리한다.")

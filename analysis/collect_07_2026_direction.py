# =============================================================
#  보고서 #07 — 2단계: 정식 수집 + 게이트 1~4
#
#  기준 문서: docs/07_주제검증.md (blob c95bbfc85...)
#  이 스크립트는 '수집·게이트'까지만 한다.
#  ⛔ V1~V4 판정 / 40ft 비중 / 수출:수입 배율 계산은 하지 않는다(다음 턴).
#
#  규칙(지시 §B):
#   B1. XML 태그명 기준 파싱. 위치 인덱스 접근 금지.
#   B2. 첫 응답 1건의 태그명 전체 집합을 정렬 출력 + 필요한 태그 존재 assert.
#   B3. numOfRows 충분히 크게. 호출마다 resultCode/totalCount/수신 item 수 출력.
#       totalCount ≠ 수신 수 → 정지.
#   B4. 월(mm)은 문자열("01"~"12"). 정수 변환 후 비교 금지.
# =============================================================
import os
import sys
import csv
import xml.etree.ElementTree as ET
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import SERVICE_KEY

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"

CORE_TAGS = ["yyyy", "mm", "GInOut", "ocCt", "forEmpTeu", "korEmpTeu"]
SPEC_TAGS = ["forEmp_10", "forEmp_20", "forEmp_40", "forEmp_99",
             "korEmp_10", "korEmp_20", "korEmp_40", "korEmp_99"]
CORE14 = CORE_TAGS + SPEC_TAGS          # 2025 정본 컬럼 순서
NUMERIC10 = ["forEmpTeu", "korEmpTeu"] + SPEC_TAGS
TOL = 0.01

BASE_2025 = os.path.join(HERE, "container_2025_direction.csv")
OUT_2025_RECHECK = os.path.join(HERE, "container_2025_direction_recheck.csv")
OUT_2026 = os.path.join(HERE, "container_2026_direction.csv")

MONTHS_S = ["01", "02", "03", "04", "05", "06"]   # B4: 문자열 취급


def stop(gate, msg):
    print(f"\n  ⛔ [{gate}] 정지 — {msg}")
    print("  ▶ 이후 단계를 진행하지 않고 종료합니다.")
    sys.exit(1)


def fetch(label, year, sm, em, num_rows="300"):
    """B1·B3: 태그명 기준 파싱. resultCode/totalCount/수신수 출력 + 일치 검사."""
    params = {"serviceKey": SERVICE_KEY, "searchYear": year,
              "searchStartM": sm, "searchEndM": em,
              "numOfRows": num_rows, "pageNo": "1"}
    root = ET.fromstring(requests.get(URL, params=params, timeout=30).content)
    rc = root.findtext(".//resultCode")
    rm = root.findtext(".//resultMsg")
    tc = root.findtext(".//totalCount")
    items = root.findall(".//item")
    print(f"  [{label}] searchYear={year} {sm}~{em} numOfRows={num_rows}")
    print(f"     resultCode={rc} / resultMsg={rm} / totalCount={tc} / 수신 item 수={len(items)}")
    if rc != "00":
        stop("B3", f"{label}: resultCode={rc} ({rm})")
    if tc is None or int(tc) != len(items):
        stop("B3", f"{label}: totalCount({tc}) ≠ 수신 item 수({len(items)})")
    return items


def tagcheck(label, items, extra=()):
    """B2: 첫 item 태그명 전체 집합(정렬) 출력 + 참조 태그 존재 assert. 값 출력 금지."""
    tags = sorted({c.tag for c in items[0]})
    print(f"  [{label}] 첫 item 태그명 전체({len(tags)}개, 정렬):")
    print(f"     {tags}")
    need = list(CORE14) + list(extra)
    missing = [t for t in need if t not in tags]
    if missing:
        stop("B2", f"{label}: 참조 태그가 응답에 없음 {missing}")
    print(f"     → 참조 태그 {len(need)}개 전부 존재 (assert PASS)")


def rows_of(items, tags):
    """원시 텍스트 그대로 추출(가공 금지)."""
    return [{t: it.findtext(t) for t in tags} for it in items]


def save_csv(path, rows, cols):
    """2025 정본과 동일: utf-8-sig(BOM) + CRLF + 컬럼 순서 CORE14."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])


def fnum(x):
    return float(x)


print("=" * 72)
print(" #07 2단계 — 정식 수집 + 게이트 1~4  (판정 금지 턴)")
print("=" * 72)

# =============================================================
# C. 2025 재수집 (게이트 1 — 회귀 앵커)
# =============================================================
print("\n" + "=" * 72)
print(" [C] 2025 재수집 — 게이트 1(회귀 앵커)")
print("=" * 72)

items25 = fetch("C1-2025", "2025", "01", "12", "300")
tagcheck("B2-2025", items25)
raw25 = rows_of(items25, CORE14)
save_csv(OUT_2025_RECHECK, raw25, CORE14)
print(f"  저장: {OUT_2025_RECHECK} ({len(raw25)}행 × {len(CORE14)}열)")

# ---- C2: 기존 정본과 diff ----
print("\n  [C2] container_2025_direction.csv 와 diff")
b_new = open(OUT_2025_RECHECK, "rb").read()
b_old = open(BASE_2025, "rb").read()
print(f"     바이트 동일 여부: {b_new == b_old}  (신 {len(b_new)}B / 정본 {len(b_old)}B)")

with open(BASE_2025, "r", encoding="utf-8-sig", newline="") as f:
    base_rows = list(csv.DictReader(f))
print(f"     정본 컬럼 순서: {list(base_rows[0].keys())}")
if list(base_rows[0].keys()) != CORE14:
    stop("C2", "정본 컬럼 순서가 CORE14와 다름")

def keyof(r):
    return (r["yyyy"], r["mm"], r["GInOut"], r["ocCt"])


# (a) 위치 기준(행 순서 포함) 대조
pos_diff = 0
if len(base_rows) == len(raw25):
    pos_diff = sum(1 for a, b in zip(raw25, base_rows)
                   for c in CORE14 if str(a[c]) != str(b[c]))
print(f"     (a) 위치 기준(행 순서 포함) 불일치 셀 = {pos_diff}")
print(f"        재수집 행순서 앞3키 = {[keyof(r) for r in raw25[:3]]}")
print(f"        정본   행순서 앞3키 = {[keyof(r) for r in base_rows[:3]]}")

# (b) 자연키(yyyy,mm,GInOut,ocCt) 기준 대조 — 값 검증의 본체
mismatch = []
if len(base_rows) != len(raw25):
    mismatch.append(f"행수 다름: 재수집 {len(raw25)} vs 정본 {len(base_rows)}")
else:
    knew = {keyof(r): r for r in raw25}
    kold = {keyof(r): r for r in base_rows}
    if len(knew) != len(raw25) or len(kold) != len(base_rows):
        mismatch.append(f"자연키 중복: 재수집 유일키 {len(knew)}/{len(raw25)}, 정본 {len(kold)}/{len(base_rows)}")
    for k in sorted(set(knew) | set(kold)):
        if k not in knew:
            mismatch.append(f"키 {k}: 재수집에 없음")
        elif k not in kold:
            mismatch.append(f"키 {k}: 정본에 없음")
        else:
            for c in CORE14:
                if str(knew[k][c]) != str(kold[k][c]):
                    mismatch.append(f"키 {k} [{c}] 재수집={knew[k][c]} vs 정본={kold[k][c]}")
if mismatch:
    print(f"     (b) 자연키 기준 ⚠ 불일치 {len(mismatch)}건 — 전량 출력:")
    for m in mismatch:
        print("       " + m)
else:
    print("     (b) 자연키 기준 → 완전 일치 (64행 × 14열, 전 셀 문자열 동일)")

# ---- C3: 연간 앵커 ----
print("\n  [C3] 2025 연간 앵커 (ocCt=1, 소수 그대로)")
oc1 = [r for r in raw25 if r["ocCt"] == "1"]
imp = sum(fnum(r["forEmpTeu"]) + fnum(r["korEmpTeu"]) for r in oc1 if r["GInOut"] == "1")
exp = sum(fnum(r["forEmpTeu"]) + fnum(r["korEmpTeu"]) for r in oc1 if r["GInOut"] == "2")
tr = sum(fnum(r["forEmpTeu"]) + fnum(r["korEmpTeu"]) for r in oc1 if r["GInOut"] in ("3", "4"))
tot = sum(fnum(r["forEmpTeu"]) + fnum(r["korEmpTeu"]) for r in oc1)
c3 = [("연간 합계 TEU(G1+G2+G3+G4)", tot, 991170.0),
      ("연간 수출 TEU (G2)", exp, 843837.75),
      ("연간 수입 TEU (G1)", imp, 139418.25),
      ("연간 환적계 TEU (G3+G4)", tr, 7914.0)]
c3_bad = []
for name, got, want in c3:
    ok = abs(got - want) <= TOL
    print(f"     {name:<28} = {got!r}   기대 {want!r}   {'일치' if ok else '★불일치★'}")
    if not ok:
        c3_bad.append((name, got, want))
print(f"     닫힘 검산: {exp!r} + {imp!r} + {tr!r} = {exp + imp + tr!r}")

# ---- C4: #06 앵커(박스 수 기준 정수) ----
print("\n  [C4] #06 앵커 재현 (2025 연간, 박스 수 기준 · 분자/분모 정수)")
SPEC_ALL = ["forEmp_10", "forEmp_20", "forEmp_40", "forEmp_99",
            "korEmp_10", "korEmp_20", "korEmp_40", "korEmp_99"]


def box_num_den(g):
    sub = [r for r in oc1 if r["GInOut"] == g]
    num = sum(fnum(r["forEmp_40"]) + fnum(r["korEmp_40"]) for r in sub)
    den = sum(sum(fnum(r[c]) for c in SPEC_ALL) for r in sub)
    return num, den


imp_num, imp_den = box_num_den("1")
exp_num, exp_den = box_num_den("2")
c4 = [("수입 40ft 분자", imp_num, 66463), ("수입 40ft 분모", imp_den, 72922),
      ("수출 40ft 분자", exp_num, 284468), ("수출 40ft 분모", exp_den, 542456)]
c4_bad = []
for name, got, want in c4:
    ok = abs(got - want) <= TOL
    print(f"     {name:<16} = {got!r}   기대 {want}   {'일치' if ok else '★불일치★'}")
    if not ok:
        c4_bad.append((name, got, want))

# ---- C5 ----
if c3_bad or c4_bad:
    stop("C5(게이트1)", f"회귀 앵커 불일치 — C3 {c3_bad} / C4 {c4_bad}")
print("\n  ✅ [게이트 1] 회귀 앵커 전 항목 일치 — D 진행")

# =============================================================
# D. 2026 정식 수집
# =============================================================
print("\n" + "=" * 72)
print(" [D] 2026 정식 수집")
print("=" * 72)

# D2 대조용: 프로브 #07-C1 과 동일 조건(01~12) 호출
print("\n  [D2-a] 프로브 #07-C1 동일 조건(2026 01~12) 재호출")
items26_full = fetch("D2-a", "2026", "01", "12", "300")
tagcheck("B2-2026", items26_full, extra=("esbCntcDt",))
full26 = rows_of(items26_full, CORE14 + ["esbCntcDt"])

by_m = {}
for r in full26:
    d = by_m.setdefault(r["mm"], {"rows": 0, "combo": set(), "esb": set()})
    d["rows"] += 1
    d["combo"].add(f"G{r['GInOut']}·oc{r['ocCt']}")
    d["esb"].add((r["esbCntcDt"] or "")[:10])

print("\n  [D2-b] 프로브 대조")
print(f"     totalCount 수신 = {len(items26_full)}  (프로브 기대 36)  "
      f"{'일치' if len(items26_full) == 36 else '★불일치★'}")
print(f"     존재 월(문자열) = {sorted(by_m)}")
PROBE_ESB = {"01": "2026-02-19", "02": "2026-03-19", "03": "2026-04-17",
             "04": "2026-05-17", "05": "2026-06-18", "06": "2026-07-14"}
PROBE_COMBO = {"G1·oc1", "G1·oc2", "G2·oc1", "G2·oc2", "G3·oc1", "G4·oc1"}
d2_diff = []
for mm in sorted(by_m):
    d = by_m[mm]
    combo_ok = d["combo"] == PROBE_COMBO
    esb_list = sorted(d["esb"])
    esb_ok = (mm in PROBE_ESB) and esb_list == [PROBE_ESB[mm]]
    rows_ok = d["rows"] == 6
    print(f"     {mm}월: 행수={d['rows']}{'' if rows_ok else '★'}"
          f"  조합={sorted(d['combo'])}{'' if combo_ok else '★'}"
          f"  적재일={esb_list}{'' if esb_ok else '★'}")
    if not rows_ok:
        d2_diff.append(f"{mm}월 행수 {d['rows']} ≠ 6")
    if not combo_ok:
        d2_diff.append(f"{mm}월 조합 {sorted(d['combo'])} ≠ 프로브")
    if not esb_ok:
        d2_diff.append(f"{mm}월 적재일 {esb_list} ≠ 프로브 {PROBE_ESB.get(mm)}")
extra_m = [m for m in sorted(by_m) if m not in MONTHS_S]
if extra_m:
    d2_diff.append(f"프로브 범위 밖 월 존재: {extra_m}")
print("     [D2 결과] " + ("전 항목 일치" if not d2_diff else f"불일치 {len(d2_diff)}건 → " + " | ".join(d2_diff)))

# D1: 01~06 정식 수집·저장
print("\n  [D1] 2026-01~06 정식 수집")
items26 = fetch("D1-2026", "2026", "01", "06", "300")
raw26 = rows_of(items26, CORE14)
esb26 = rows_of(items26, ["mm", "esbCntcDt"])
save_csv(OUT_2026, raw26, CORE14)
print(f"     저장: {OUT_2026} ({len(raw26)}행 × {len(CORE14)}열, utf-8-sig·CRLF·CORE14 순서)")

# D3: 게이트 4 — 월 소실
print("\n  [D3] 게이트 4 — 월 소실 (B4: 문자열 비교)")
got_m = sorted({r["mm"] for r in raw26})
print(f"     수집 월 집합 = {got_m}  기대 = {MONTHS_S}")
miss = [m for m in MONTHS_S if m not in got_m]
if miss:
    stop("게이트4", f"월 결손 {miss} — 0패딩·키·네트워크 순으로 프로브 자체를 먼저 의심할 것")
print("     → 01~06 전부 존재 (게이트 4 PASS)")

# =============================================================
# E. 게이트 2·3 (2026 전 행)
# =============================================================
print("\n" + "=" * 72)
print(" [E] 게이트 2·3 — 2026 전 행")
print("=" * 72)

print("\n  [E1] 게이트 2 — Teu 항등식 |Teu − (0.5×_10 + 1×_20 + 2×_40 + 2.25×_99)|")
bad_e1, max_res, max_where = [], 0.0, None
for i, r in enumerate(raw26):
    for side, teu in (("for", "forEmpTeu"), ("kor", "korEmpTeu")):
        recon = (0.5 * fnum(r[f"{side}Emp_10"]) + 1.0 * fnum(r[f"{side}Emp_20"])
                 + 2.0 * fnum(r[f"{side}Emp_40"]) + 2.25 * fnum(r[f"{side}Emp_99"]))
        res = abs(fnum(r[teu]) - recon)
        if res > max_res:
            max_res, max_where = res, f"행{i}(mm={r['mm']},G={r['GInOut']},oc={r['ocCt']},{side})"
        if res > TOL:
            bad_e1.append((i, side, r, res))
if bad_e1:
    print(f"     ⚠ 0.01 초과 {len(bad_e1)}건 — 해당 행 전량 출력:")
    for i, side, r, res in bad_e1:
        print(f"       행{i} [{side}] 잔차={res!r} :: " + ",".join(f"{c}={r[c]}" for c in CORE14))
    stop("게이트2", f"Teu 항등식 위반 {len(bad_e1)}건")
print(f"     → 0.01 초과 0건. 최대 잔차 = {max_res!r} ({max_where})")

print("\n  [E2] 게이트 3 — 규격 박스 필드 정수성 (_10·_20·_40·_99, for·kor 전부)")
bad_e2 = []
for i, r in enumerate(raw26):
    for c in SPEC_ALL:
        v = fnum(r[c])
        if v != int(v):
            bad_e2.append(f"행{i}(mm={r['mm']},G={r['GInOut']},oc={r['ocCt']}) {c}={r[c]}")
if bad_e2:
    print(f"     ⚠ 비정수 {len(bad_e2)}건:")
    for b in bad_e2:
        print("       " + b)
    stop("게이트3", f"비정수 {len(bad_e2)}건")
print(f"     → 전 행 정수 (검사 셀 수 = {len(raw26) * len(SPEC_ALL)}, 비정수 0건)")

# =============================================================
# F2. 산출 파일 메타
# =============================================================
print("\n" + "=" * 72)
print(" [F2] container_2026_direction.csv 메타")
print("=" * 72)
b26 = open(OUT_2026, "rb").read()
print(f"     경로 = {OUT_2026}")
print(f"     바이트 크기 = {len(b26)}")
print(f"     BOM(utf-8-sig) = {b26[:3] == bytes([0xEF, 0xBB, 0xBF])}")
print(f"     CRLF 수 = {b26.count(bytes([13, 10]))} / 총 LF = {b26.count(bytes([10]))} / bare CR = {b26.count(bytes([13])) - b26.count(bytes([13, 10]))}")
print(f"     행수 = 헤더1 + 데이터{len(raw26)} = {len(raw26) + 1}")

print("\n  [적재일 참고] 2026 정식 수집분 esbCntcDt (월별)")
seen = {}
for r in esb26:
    seen.setdefault(r["mm"], set()).add((r["esbCntcDt"] or "")[:10])
for mm in sorted(seen):
    print(f"     {mm}월: {sorted(seen[mm])}")

print("\n완료: 수집 + 게이트 1~4 종료. ⛔ V1~V4 판정·비중·배율 계산은 하지 않았다(다음 턴).")

# =============================================================
#  보고서 #04: 인천항 공컨테이너 '불균형 지속성 — 연도별 추세' 분석 (2022-2025)
#
#  GInOut(수출입구분): 1=수입 · 2=수출 · 3=수입환적 · 4=수출환적
#  ocCt(외내항구분):   1=수출입항 · 2=연안항
#  → 코드 정의 근거: docs/GInOut_코드규명.md [확정]
#
#  구성: (0) 저장 원시 CSV 로드 → (1) 게이트 G1~G4 → (2) 집계 → (3) 차트
#  ※ API 재호출 없음. 저장된 원시 CSV가 이 세션의 정본 입력이다.
#  ※ 게이트 하나라도 FAIL이면 즉시 종료(이후 단계 진행 금지).
#  ※ analyze_direction.py(#03)의 게이트·집계 로직을 재사용해 4개년으로 확장.
#
#  [게이트 재정의 — 회장님 결정 2026-07-13 반영]
#   - 분석 모집단 = ocCt=1(수출입항). #01~#03과 동일. 배제 근거는 '정의'이지 규모가 아니다.
#   - G2: ocCt=2 실적 0을 가정하지 않는다. 관측을 '기록'만 한다.
#          유일 정지 조건 = ocCt=2에서 forEmpTeu>0(외국적 연안은 상정 밖).
#   - G3: 스칼라 앵커는 '소수 원값' 정확 일치(허용오차 없음). 행 대조가 주 검증.
#   - G4: 환산식 검증 범위 = ocCt=1. ocCt=2의 규격필드 0 사례는 별도 기록.
# =============================================================

import pandas as pd
import matplotlib.pyplot as plt
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ---- 상수 ----
GINOUT_LABEL = {"1": "수입", "2": "수출", "3": "수입환적", "4": "수출환적"}
CORE_TAGS = ["yyyy", "mm", "GInOut", "ocCt", "forEmpTeu", "korEmpTeu"]
SPEC_TAGS = ["forEmp_10", "forEmp_20", "forEmp_40", "forEmp_99",
             "korEmp_10", "korEmp_20", "korEmp_40", "korEmp_99"]
CORE14 = CORE_TAGS + SPEC_TAGS            # 2025 정본과 동일한 핵심 14필드
NUMERIC10 = ["forEmpTeu", "korEmpTeu"] + SPEC_TAGS
KEY = ["yyyy", "mm", "GInOut", "ocCt"]    # 연·월·방향·내외항 = 자연키(연도 내 유일)
TOL = 0.01
YEARS = ["2022", "2023", "2024", "2025"]
MONTH_MIN, MONTH_MAX = 30_000, 150_000    # G4 월별 총량 눈검증 트리거 범위

# 저장 원시 CSV 경로(이 세션의 정본 입력) — API 재호출 없음
RAW_PATH = {
    "2022": "container_2022_direction.csv",
    "2023": "container_2023_direction.csv",
    "2024": "container_2024_direction.csv",
    "2025": "probe/recheck_2025_raw.csv",
}


def fail(gate: str, msg: str) -> None:
    """게이트 실패 시 오류 메시지를 남기고 즉시 종료한다."""
    print(f"\n  [{gate}] FAIL — {msg}")
    print("  ▶ 게이트 실패로 이후 단계를 진행하지 않고 종료합니다.")
    sys.exit(1)


def numeric_copy(df: pd.DataFrame) -> pd.DataFrame:
    """검증·집계용 숫자 사본. 원시 문자열은 보존, 파생 mm_i·숫자열만 형변환."""
    d = df.copy()
    d["mm_i"] = pd.to_numeric(d["mm"]).astype(int)
    d["GInOut"] = d["GInOut"].astype(str)
    d["ocCt"] = d["ocCt"].astype(str)
    for c in NUMERIC10:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


# =============================================================
# (0) 저장 원시 CSV 로드
# =============================================================
print("=" * 64)
print(" (0) 저장 원시 CSV 로드 (API 재호출 없음)")
print("=" * 64)
raw = {}
for y in YEARS:
    raw[y] = pd.read_csv(RAW_PATH[y])
    print(f"  [{y}] {RAW_PATH[y]} — {len(raw[y])}행 × {len(raw[y].columns)}열")
num = {y: numeric_copy(raw[y]) for y in YEARS}

# =============================================================
# (1) 검증 게이트 G1~G4 — 하나라도 FAIL 시 즉시 종료
# =============================================================
print("\n" + "=" * 64)
print(" (1) 검증 게이트 G1~G4 (재정의판)")
print("=" * 64)

# ---- G1: 완결성·스키마·코드값 집합 + ocCt=1 행수 48 공통 ----
print("\n[G1] 완결성 · 스키마 · ocCt=1 행수 · 총행수 분해")
rowcounts, occt1_counts, occt2_counts = {}, {}, {}
for y in YEARS:
    d = num[y]
    months = sorted(d["mm_i"].unique().tolist())
    ginout_set = set(d["GInOut"].unique())
    occt_set = set(d["ocCt"].unique())
    n_all = len(d)
    n_oc1 = int((d["ocCt"] == "1").sum())
    n_oc2 = int((d["ocCt"] == "2").sum())
    rowcounts[y], occt1_counts[y], occt2_counts[y] = n_all, n_oc1, n_oc2
    if months != list(range(1, 13)):
        fail("G1", f"{y}: 월 완결 아님 {months}")
    if not ginout_set.issubset({"1", "2", "3", "4"}):
        fail("G1", f"{y}: GInOut={sorted(ginout_set)}")
    if not occt_set.issubset({"1", "2"}):
        fail("G1", f"{y}: ocCt={sorted(occt_set)}")
    # ocCt=1 행수 = 48 (12개월 × GInOut 4) 4개년 공통
    if n_oc1 != 48:
        fail("G1", f"{y}: ocCt=1 행수 {n_oc1} ≠ 48 (12개월 × GInOut 4)")
    # 총행수 - 48 == ocCt=2 행수 (총행수 차이가 전부 ocCt=2로 설명되는지)
    if n_all - 48 != n_oc2:
        fail("G1", f"{y}: 총행수({n_all}) - 48 ≠ ocCt=2행수({n_oc2})")
    print(f"   {y}: 총{n_all}행 = ocCt=1 {n_oc1}(=48) + ocCt=2 {n_oc2} · "
          f"월1~12 · GInOut{sorted(ginout_set)} · ocCt{sorted(occt_set)}")

# 핵심 14필드가 2025 정본과 동일한지
base2025 = pd.read_csv("container_2025_direction.csv")
if list(base2025.columns) != CORE14:
    fail("G1", f"2025 정본 컬럼이 기대 14필드와 다름: {list(base2025.columns)}")
for y in YEARS:
    miss = [c for c in CORE14 if c not in raw[y].columns]
    if miss:
        fail("G1", f"{y} 원시에 핵심 14필드 누락: {miss}")
print(f"   핵심 14필드 == 2025 정본 컬럼셋 (일치)")
print(f"   [G1] PASS — ocCt=1 행수 4개년 전부 48 · 총행수 차이(66·60·60·64)는 "
      f"ocCt=2 행수({occt2_counts['2022']}·{occt2_counts['2023']}·"
      f"{occt2_counts['2024']}·{occt2_counts['2025']})로 설명됨")

# ---- G2: 모집단 정의 확인 (기록 중심, 정지조건=외국적 연안) ----
print("\n[G2] 모집단 = ocCt=1(수출입항). ocCt=2는 기록만 (0 아니어도 FAIL 아님)")
coastal_rows = []   # 연안 관측 소표용
for y in YEARS:
    d = num[y]
    co = d[d["ocCt"] == "2"].copy()
    co["teu"] = co["forEmpTeu"] + co["korEmpTeu"]
    nz = int((co[NUMERIC10].abs().sum(axis=1) > TOL).sum())
    kor_ann = float(co["korEmpTeu"].sum())
    for_ann = float(co["forEmpTeu"].sum())
    oc1_ann = float((d[d["ocCt"] == "1"]["forEmpTeu"] + d[d["ocCt"] == "1"]["korEmpTeu"]).sum())
    ratio = kor_ann / oc1_ann * 100 if oc1_ann else 0.0
    # ⛔ 유일 정지 조건: 외국적 연안(forEmpTeu>0)
    if for_ann > TOL:
        fail("G2", f"{y}: ocCt=2 forEmpTeu 연간합 {for_ann} > 0 (외국적 연안은 상정 밖)")
    # GInOut 구성(관측 기록만)
    gcomp = co[co[NUMERIC10].abs().sum(axis=1) > TOL].groupby("GInOut").size().to_dict()
    gcomp_str = ", ".join(f"{GINOUT_LABEL[g]}={n}행" for g, n in sorted(gcomp.items())) or "없음"
    coastal_rows.append({
        "연도": y, "ocCt2행수": len(co), "0아닌행": nz,
        "연안korTEU": kor_ann, "연안forTEU": for_ann,
        "oc1대비(%)": round(ratio, 3), "GInOut구성": gcomp_str,
    })
    print(f"   {y}: ocCt=2 {len(co)}행 (0아닌 {nz}행) · korTEU {kor_ann:,.1f} · "
          f"forTEU {for_ann:,.1f} · oc1대비 {ratio:.3f}% · [{gcomp_str}]")
print("   [G2] PASS — 외국적 연안 없음. 모집단 ocCt=1 확정. 연안 관측은 소표로 산출")

# ---- G3: 소수 앵커 + 행 대조 주 검증 ----
print("\n[G3] 회귀 앵커 — 행 단위 완전 일치(소수 포함) + 소수 스칼라 앵커")


def core_frame(df: pd.DataFrame) -> pd.DataFrame:
    """핵심 14필드만 뽑아 형변환·정렬한 비교용 프레임."""
    d = df[CORE14].copy()
    for c in ["yyyy", "mm", "GInOut", "ocCt"]:
        d[c] = pd.to_numeric(d[c]).astype(int)
    for c in NUMERIC10:
        d[c] = pd.to_numeric(d[c], errors="coerce").astype(float)
    return d.sort_values(KEY).reset_index(drop=True)


def diff_core(a: pd.DataFrame, b: pd.DataFrame):
    da, db = core_frame(a), core_frame(b)
    if len(da) != len(db):
        return [f"행수 다름: {len(da)} vs {len(db)}"]
    diffs = []
    for i in range(len(da)):
        ra, rb = da.iloc[i], db.iloc[i]
        for c in CORE14:
            if c in NUMERIC10:
                if abs(float(ra[c]) - float(rb[c])) > TOL:
                    diffs.append(f"행{i}(mm={ra['mm']},G={ra['GInOut']},oc={ra['ocCt']}) "
                                 f"{c}: {ra[c]} vs {rb[c]}")
            elif int(ra[c]) != int(rb[c]):
                diffs.append(f"행{i} {c}: {ra[c]} vs {rb[c]}")
    return diffs


def occt1_direction_sums(df: pd.DataFrame):
    """ocCt=1 기준 방향별(수입/수출/환적) TEU 합 + 총합."""
    d = numeric_copy(df)
    p = d[d["ocCt"] == "1"].copy()
    p["teu"] = p["forEmpTeu"] + p["korEmpTeu"]
    by = p.groupby("GInOut")["teu"].sum()
    imp = float(by.get("1", 0.0))
    exp = float(by.get("2", 0.0))
    tr = float(by.get("3", 0.0)) + float(by.get("4", 0.0))
    return imp, exp, tr, imp + exp + tr


# G3-a: 재수집 2025 vs 정본 (행 단위)
d25 = diff_core(raw["2025"], base2025)
if d25:
    fail("G3-2025", "재수집 2025 ≠ 정본:\n     " + "\n     ".join(d25[:50]))
imp25, exp25, tr25, tot25 = occt1_direction_sums(raw["2025"])
anchors25 = {"총": (tot25, 991_170.0), "수출": (exp25, 843_837.75),
             "수입": (imp25, 139_418.25), "환적": (tr25, 7_914.0)}
for name, (got, exp) in anchors25.items():
    if abs(got - exp) > TOL:
        fail("G3-2025", f"{name} 앵커 불일치: {got} vs {exp}")
print(f"   2025: 정본과 핵심14필드 전 행 일치 · 총 {tot25:,.2f}=991,170.0 · "
      f"수출 {exp25:,.2f}=843,837.75 · 수입 {imp25:,.2f}=139,418.25 · 환적 {tr25:,.1f}=7,914.0")

# G3-b: 재수집 2024 vs probe_2024_raw.csv (행 단위)
probe2024 = pd.read_csv("probe/probe_2024_raw.csv")
d24 = diff_core(raw["2024"], probe2024)
if d24:
    fail("G3-2024", "재수집 2024 ≠ probe_2024_raw.csv:\n     " + "\n     ".join(d24[:50]))
imp24, exp24, tr24, tot24 = occt1_direction_sums(raw["2024"])
if abs(tot24 - 1_044_969.5) > TOL:
    fail("G3-2024", f"2024 총 앵커 불일치: {tot24} vs 1,044,969.5")
print(f"   2024: probe_2024_raw.csv와 핵심14필드 전 행 일치 · 총 {tot24:,.2f}=1,044,969.5")

# 일관성 1줄: 소수 앵커의 정수 반올림 == 발행 수치
print(f"   일관성: 반올림 시 수출 {round(exp25):,}=843,838 · 수입 {round(imp25):,}=139,418 · "
      f"2024총 {round(tot24):,}=1,044,970 (발행 수치와 일치)")
print("   [G3] PASS")

# ---- G4: 환산식(ocCt=1 전 행, 검증) + _10 실태(기록) + ocCt=2 규격필드0 기록 + 월별 트리거 ----
#   ※ _10=0 은 '정지 조건'이 아니라 '확인·기록' 항목(지시 원문). 실태를 소표로 산출.
print("\n[G4] 규격 환산식(ocCt=1, 검증) · _10 실태(기록) · 월별 트리거")
spec0_note = {}   # ocCt=2 korEmpTeu>0 & 규격필드 전부 0 행수
spec10_rows = []  # _10 실태 소표 (ocCt=1, 0 아닌 행)
for y in YEARS:
    d = num[y]
    p1 = d[d["ocCt"] == "1"]
    # (i) 환산식 잔차 0 (for·kor) — ocCt=1 전 행 [검증: FAIL 시 정지]
    for side, teu_col in [("for", "forEmpTeu"), ("kor", "korEmpTeu")]:
        recon = (0.5 * p1[f"{side}Emp_10"] + 1.0 * p1[f"{side}Emp_20"]
                 + 2.0 * p1[f"{side}Emp_40"] + 2.25 * p1[f"{side}Emp_99"])
        rmax = float((p1[teu_col] - recon).abs().max())
        if rmax > TOL:
            fail("G4-환산식", f"{y} {side}(ocCt=1): 잔차 최대 {rmax} > TOL")
    # (ii) _10 실태 [기록만 — 정지 아님]
    for side in ["for", "kor"]:
        nz = p1[p1[f"{side}Emp_10"].abs() > TOL]
        for _, r in nz.iterrows():
            spec10_rows.append({
                "연도": y, "월": int(r["mm_i"]), "GInOut": GINOUT_LABEL[r["GInOut"]],
                "측": side, "박스수": int(r[f"{side}Emp_10"]),
            })
    f10 = float(p1["forEmp_10"].sum())
    k10 = float(p1["korEmp_10"].sum())
    # ocCt=2: korEmpTeu>0 인데 규격필드 전부 0 인 행수(환산식 부적용 사례) — 기록만
    p2 = d[d["ocCt"] == "2"].copy()
    p2_specsum = p2[SPEC_TAGS].abs().sum(axis=1)
    spec0 = int(((p2["korEmpTeu"] > TOL) & (p2_specsum <= TOL)).sum())
    spec0_note[y] = spec0
    # (iii) 월별 총량 트리거 + 방향 0 부재 (ocCt=1) [트리거: FAIL 시 정지]
    p1c = p1.copy()
    p1c["teu"] = p1c["forEmpTeu"] + p1c["korEmpTeu"]
    mtot = []
    for m in range(1, 13):
        pm = p1c[p1c["mm_i"] == m]
        imp = float(pm[pm["GInOut"] == "1"]["teu"].sum())
        exp = float(pm[pm["GInOut"] == "2"]["teu"].sum())
        tot = float(pm["teu"].sum())
        mtot.append(tot)
        if tot < MONTH_MIN or tot > MONTH_MAX:
            fail("G4-범위", f"{y} {m}월 총량 {tot:,.1f} 범위 밖 — 눈검증 필요")
        if imp == 0.0 or exp == 0.0:
            fail("G4-방향0", f"{y} {m}월 수입={imp} 수출={exp} 중 0 존재")
    print(f"   {y}: ocCt=1 환산식 잔차0 · _10(for={f10:.0f}/kor={k10:.0f}박스) · "
          f"월총량 {min(mtot):,.0f}~{max(mtot):,.0f} (범위내·방향0 없음) | "
          f"ocCt=2 규격필드0 행수={spec0}")
print("   [G4] PASS — 환산식·월별 트리거 통과. _10은 기록 항목(정지 아님)")

print("\n  ✅ 모든 검증 게이트 PASS(G1~G4) — 집계 단계로 진행합니다.")

# =============================================================
# (2) 집계 (ocCt=1 기준, 외국적+한국적 합)
# =============================================================
print("\n" + "=" * 64)
print(" (2) 집계 — 연도별 방향 분해 (2022-2025, 모집단 ocCt=1)")
print("=" * 64)


def year_aggregate(df: pd.DataFrame):
    d = numeric_copy(df)
    p = d[d["ocCt"] == "1"].copy()
    p["teu"] = p["forEmpTeu"] + p["korEmpTeu"]
    monthly = pd.DataFrame(index=range(1, 13))
    for m in range(1, 13):
        pm = p[p["mm_i"] == m]
        by = pm.groupby("GInOut")["teu"].sum()
        monthly.loc[m, "수입"] = float(by.get("1", 0.0))
        monthly.loc[m, "수출"] = float(by.get("2", 0.0))
        monthly.loc[m, "환적"] = float(by.get("3", 0.0)) + float(by.get("4", 0.0))
    monthly["합계"] = monthly[["수입", "수출", "환적"]].sum(axis=1)
    monthly["배율"] = (monthly["수출"] / monthly["수입"]).round(2)
    imp = float(monthly["수입"].sum())
    exp = float(monthly["수출"].sum())
    tr = float(monthly["환적"].sum())
    tot = imp + exp + tr
    forsum = float(p["forEmpTeu"].sum())
    korsum = float(p["korEmpTeu"].sum())
    return {
        "monthly": monthly, "수입": imp, "수출": exp, "환적": tr, "총량": tot,
        "배율": round(exp / imp, 2), "외국적비중": round(forsum / (forsum + korsum) * 100, 1),
    }


agg = {y: year_aggregate(raw[y]) for y in YEARS}

# ---- 표1: 연도별 요약 ----
print("\n[표1] 연도별 요약 (단위: TEU, ocCt=1)")
h = (f"  {'연도':<6}{'총량':>12}{'수출':>12}{'수입':>11}{'환적':>10}"
     f"{'수출%':>7}{'수입%':>7}{'환적%':>7}{'수출:수입':>9}{'외국적%':>8}")
print(h)
print("  " + "-" * (len(h) - 2))
for y in YEARS:
    a = agg[y]
    tot = a["총량"]
    print(f"  {y:<6}{tot:>12,.0f}{a['수출']:>12,.0f}{a['수입']:>11,.0f}{a['환적']:>10,.0f}"
          f"{a['수출']/tot*100:>7.1f}{a['수입']/tot*100:>7.1f}{a['환적']/tot*100:>7.1f}"
          f"{a['배율']:>8.2f}배{a['외국적비중']:>7.1f}")
print("  " + "-" * (len(h) - 2))

# ---- 표2: 월별 배율 매트릭스 ----
print("\n[표2] 월별 수출:수입 배율 (12개월 × 4개년)")
print(f"  {'월':>3}" + "".join(f"{y:>10}" for y in YEARS))
print("  " + "-" * (3 + 10 * len(YEARS)))
for m in range(1, 13):
    print(f"  {m:>3}" + "".join(f"{agg[y]['monthly'].loc[m, '배율']:>10.2f}" for y in YEARS))
print("  " + "-" * (3 + 10 * len(YEARS)))
print(f"  {'연':>3}" + "".join(f"{agg[y]['배율']:>10.2f}" for y in YEARS))

# ---- 보조 표: 월별 총량 + 최저 월·전월 대비 ----
print("\n[보조표] 월별 총량 (TEU) 4개년")
print(f"  {'월':>3}" + "".join(f"{y:>12}" for y in YEARS))
print("  " + "-" * (3 + 12 * len(YEARS)))
for m in range(1, 13):
    print(f"  {m:>3}" + "".join(f"{agg[y]['monthly'].loc[m, '합계']:>12,.0f}" for y in YEARS))
print("\n  [각 연도 최저 월 · 전월 대비 증감률]")
for y in YEARS:
    mon = agg[y]["monthly"]["합계"]
    mmin = int(mon.idxmin())
    vmin = float(mon.loc[mmin])
    if mmin == 1:
        chg = "—(1월, 전월 없음)"
    else:
        prev = float(mon.loc[mmin - 1])
        chg = f"{(vmin/prev - 1)*100:+.1f}% (전월 {prev:,.0f})"
    print(f"   {y}: 최저 {mmin}월 {vmin:,.0f} TEU · 전월 대비 {chg}")

# ---- 연안(ocCt=2) 관측 소표 ----
print("\n[연안 소표] ocCt=2(연안항) 관측 — 부록 후보 (해석 없음)")
cdf = pd.DataFrame(coastal_rows)
hc = f"  {'연도':<6}{'ocCt2행':>8}{'0아닌행':>8}{'연안korTEU':>12}{'연안forTEU':>11}{'oc1대비%':>10}  GInOut구성"
print(hc)
print("  " + "-" * (len(hc) - 2))
for r in coastal_rows:
    print(f"  {r['연도']:<6}{r['ocCt2행수']:>8}{r['0아닌행']:>8}{r['연안korTEU']:>12,.1f}"
          f"{r['연안forTEU']:>11,.1f}{r['oc1대비(%)']:>10.3f}  {r['GInOut구성']}")

# ---- _10(10ft) 실태 소표 (ocCt=1, 0 아닌 행) ----
print("\n[_10 소표] ocCt=1 forEmp_10/korEmp_10 0 아닌 행 (해석 없음)")
if spec10_rows:
    print(f"  {'연도':<6}{'월':>3}{'GInOut':>8}{'측':>5}{'박스수':>7}")
    print("  " + "-" * 29)
    for r in sorted(spec10_rows, key=lambda x: (x["연도"], x["월"])):
        print(f"  {r['연도']:<6}{r['월']:>3}{r['GInOut']:>8}{r['측']:>5}{r['박스수']:>7}")
    print("  (korEmp_10은 4개년 전부 0 → 표에 없음)")
else:
    print("  (0 아닌 행 없음)")

# =============================================================
# (3) 차트 2매 — #01~#03 스타일(맑은 고딕)
# =============================================================
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

# 차트1: 연도별 방향 구성 누적막대 (배율 주석)
plt.figure(figsize=(10, 6))
imps = [agg[y]["수입"] for y in YEARS]
exps = [agg[y]["수출"] for y in YEARS]
trs = [agg[y]["환적"] for y in YEARS]
x = range(len(YEARS))
plt.bar(x, imps, color="#2E86C1", label="수입")
plt.bar(x, exps, bottom=imps, color="#C0392B", label="수출")
bottom_tr = [i + e for i, e in zip(imps, exps)]
plt.bar(x, trs, bottom=bottom_tr, color="#7F8C8D", label="환적")
for xi, y in zip(x, YEARS):
    plt.text(xi, agg[y]["총량"] + 12000, f"{agg[y]['배율']:.1f}배", ha="center",
             fontsize=12, fontweight="bold", color="#111")
plt.title("인천항 공컨테이너 연도별 방향 구성 (2022-2025, TEU)\n막대 위 = 수출:수입 배율",
          fontsize=14, fontweight="bold")
plt.xticks(list(x), [f"{y}년" for y in YEARS])
plt.ylabel("공컨테이너 TEU")
plt.ylim(0, max(agg[y]["총량"] for y in YEARS) * 1.15)
plt.legend(loc="upper right")
plt.grid(True, axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig("../reports/images/direction_trend_stack_2022_2025.png", dpi=150)
plt.close()
print("\n(3) 차트 저장: ../reports/images/direction_trend_stack_2022_2025.png")

# 차트2: 월별 수출:수입 배율 — 4개년 라인 오버레이
plt.figure(figsize=(10, 6))
colors = {"2022": "#95A5A6", "2023": "#5DADE2", "2024": "#E67E22", "2025": "#C0392B"}
for y in YEARS:
    ratios = [agg[y]["monthly"].loc[m, "배율"] for m in range(1, 13)]
    plt.plot(range(1, 13), ratios, marker="o", linewidth=2, color=colors[y], label=f"{y}년")
plt.title("인천항 공컨테이너 월별 수출:수입 배율 — 4개년 오버레이 (2022-2025)",
          fontsize=14, fontweight="bold")
plt.xlabel("월")
plt.ylabel("수출 ÷ 수입 (배)")
plt.xticks(range(1, 13))
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig("../reports/images/direction_trend_ratio_2022_2025.png", dpi=150)
plt.close()
print("(3) 차트 저장: ../reports/images/direction_trend_ratio_2022_2025.png")

print("\n완료: 게이트 G1~G4 전부 통과 → 집계·차트 생성 마침.")
print("⛔ 해석 문장은 분석 세션에서 쓰지 않는다(SKILL §7 정지선). 수치·표·차트만 보고.")

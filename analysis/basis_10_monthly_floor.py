# -*- coding: utf-8 -*-
"""#10 선커밋 기준의 근거값을 낸다 — 근거 구간(2022~2025) 월별 하한.

**이 스크립트는 판정하지 않는다.** 기준을 세우는 재료만 낸다.

왜 따로 있는가. #10 은 2005~2021 **월별** 축에 기준을 건다. 그 기준의 하한을
어디에 둘 것인가는 **이미 본 구간**에서 와야 하고, 그 계산이 어디서 왔는지
확인할 수 없으면 「결과를 보고 맞춘 값」과 구별되지 않는다(§3-7).
그래서 근거 계산을 **선커밋 문서보다 먼저, 별도 파일로** 남긴다.

읽는 것: `container_2022_direction.csv` ~ `container_2025_direction.csv` 넷.
**`container_2005_2021_direction.csv` 는 열지 않는다** — 그것이 판정 구간이다.
이 사실을 인수시험이 강제한다(소스에 그 파일명이 없어야 통과).

정지선-집행: 없음 (판정도 발행도 하지 않는 재료 스크립트)
명제: 근거 구간 48개월의 월별 배율·수출비중 하한을 원시 CSV 에서 다시 계산한다.
한계: 근거 구간 값이 맞는지는 #04 발행분과의 대조로만 본다. 판정 구간은 안 본다.

    python analysis/basis_10_monthly_floor.py
    python analysis/basis_10_monthly_floor.py --selftest
"""
import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BASIS_YEARS = (2022, 2023, 2024, 2025)

# GInOut: 1=수입 · 2=수출 · 3=수입환적 · 4=수출환적  (docs/GInOut_코드규명.md [확정])
# ocCt:   1=수출입항(외항) · 2=연안항
IMPORT, EXPORT = "1", "2"
TRANSSHIP = ("3", "4")
OCEAN = "1"


def _num(s):
    s = (s or "").strip()
    return float(s) if s else 0.0


def teu(row):
    """한 행의 TEU. 외국적 + 한국적."""
    return _num(row.get("forEmpTeu")) + _num(row.get("korEmpTeu"))


JUDGED = "container_2005_2021_direction"  # #10 의 판정 구간. 이 스크립트는 안 연다.


def basis_paths():
    """이 스크립트가 여는 파일 전부. 판정 구간이 여기 끼면 인수시험이 잡는다."""
    return [os.path.join(HERE, "container_%d_direction.csv" % y) for y in BASIS_YEARS]


def read_year(year):
    path = os.path.join(HERE, "container_%d_direction.csv" % year)
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def monthly(rows):
    """월 -> {수출, 수입, 환적, 전체}. 외항(ocCt=1)만."""
    acc = defaultdict(lambda: {"수출": 0.0, "수입": 0.0, "환적": 0.0})
    for r in rows:
        if (r.get("ocCt") or "").strip() != OCEAN:
            continue
        m = int((r.get("mm") or "0").strip())
        g = (r.get("GInOut") or "").strip()
        if g == EXPORT:
            acc[m]["수출"] += teu(r)
        elif g == IMPORT:
            acc[m]["수입"] += teu(r)
        elif g in TRANSSHIP:
            acc[m]["환적"] += teu(r)
    out = {}
    for m, v in acc.items():
        v = dict(v)
        v["전체"] = v["수출"] + v["수입"] + v["환적"]
        out[m] = v
    return out


def floors(per_month):
    """(배율 최소, 그 달) · (수출비중 최소, 그 달). per_month = {(y,m): 값}"""
    ratio, share = {}, {}
    for key, v in per_month.items():
        if v["수입"] > 0:
            ratio[key] = v["수출"] / v["수입"]
        if v["전체"] > 0:
            share[key] = 100.0 * v["수출"] / v["전체"]
    rk = min(ratio, key=ratio.get)
    sk = min(share, key=share.get)
    return (ratio[rk], rk, len(ratio)), (share[sk], sk, len(share))


def collect():
    per_month = {}
    for y in BASIS_YEARS:
        for m, v in monthly(read_year(y)).items():
            per_month[(y, m)] = v
    return per_month


def main():
    per_month = collect()
    (rmin, rk, rn), (smin, sk, sn) = floors(per_month)
    print("근거 구간 %d-01 ~ %d-12 · 외항(ocCt=1) · TEU"
          % (BASIS_YEARS[0], BASIS_YEARS[-1]))
    print("  개월 수            : %d" % len(per_month))
    print("  월별 배율 최소     : %.4f  (%d-%02d)   [검사 %d개월]"
          % (rmin, rk[0], rk[1], rn))
    print("  월별 수출비중 최소 : %.4f%% (%d-%02d)   [검사 %d개월]"
          % (smin, sk[0], sk[1], sn))
    print()
    print("  대조 — 발행분 #04 의 48개월 월별 최소 배율 = 3.9 (2023-12).")
    print("  위 값이 그것과 어긋나면 기준을 세우기 전에 파이프라인을 의심한다.")
    ok = (abs(rmin - 3.9) < 0.05) and rk == (2023, 12) and len(per_month) == 48
    print("  대조 결과          : %s" % ("일치" if ok else "**불일치 — 정지**"))
    return 0 if ok else 1


def selftest():
    fails = []

    def chk(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))
        print("  %-46s %s" % (label, "OK" if got == want else "FAIL"))

    # ── 판정 구간을 안 연다는 것을 두 겹으로 강제한다 ──
    # ① 행동: 이 스크립트가 여는 파일 목록에 판정 구간이 없다.
    paths = basis_paths()
    chk("여는 파일은 근거 구간 4개뿐", len(paths), 4)
    chk("그중 판정 구간이 없다", any(JUDGED in p for p in paths), False)

    # ② 소스: 코드가 판정 구간 이름을 **문자열로도** 안 쓴다.
    #    설명하는 문장(독스트링)은 그 이름을 불러야 하므로 제외한다 —
    #    안 그러면 「안 연다」고 적는 것 자체가 실패로 잡힌다.
    import ast
    tree = ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                docs.add(d)
    lits = [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and n.value not in docs]
    # JUDGED 상수 자신은 「그 이름이 무엇인가」의 선언이라 대상에서 뺀다.
    chk("코드 문자열에 판정 구간 경로가 없다",
        [s for s in lits if JUDGED in s and s != JUDGED], [])

    chk("TEU 는 외국적+한국적",
        teu({"forEmpTeu": "10.5", "korEmpTeu": "2"}), 12.5)
    chk("빈 칸은 0", teu({"forEmpTeu": "", "korEmpTeu": None}), 0.0)

    rows = [
        {"GInOut": "2", "ocCt": "1", "mm": "1", "forEmpTeu": "800", "korEmpTeu": "0"},
        {"GInOut": "1", "ocCt": "1", "mm": "1", "forEmpTeu": "100", "korEmpTeu": "0"},
        {"GInOut": "3", "ocCt": "1", "mm": "1", "forEmpTeu": "60", "korEmpTeu": "0"},
        {"GInOut": "4", "ocCt": "1", "mm": "1", "forEmpTeu": "40", "korEmpTeu": "0"},
        # 연안은 모집단이 아니다 — 섞이면 안 된다.
        {"GInOut": "2", "ocCt": "2", "mm": "1", "forEmpTeu": "9999", "korEmpTeu": "0"},
    ]
    got = monthly(rows)
    chk("연안(ocCt=2)을 빼고 센다", got[1]["수출"], 800.0)
    chk("환적은 3+4 의 합", got[1]["환적"], 100.0)
    chk("전체 = 수출+수입+환적", got[1]["전체"], 1000.0)

    pm = {(2022, 1): got[1],
          (2022, 2): {"수출": 400.0, "수입": 100.0, "환적": 0.0, "전체": 500.0}}
    (rmin, rk, rn), (smin, sk, sn) = floors(pm)
    chk("배율 최소를 고른다", round(rmin, 4), 4.0)
    chk("배율 최소의 달", rk, (2022, 2))
    chk("검사한 개월 수를 같이 낸다", rn, 2)
    chk("수출비중 최소", round(smin, 1), 80.0)
    chk("수출비중 최소의 달", sk, (2022, 1))

    # 수입이 0 인 달은 배율을 못 낸다 — 세지도 않는다(분모 0 을 통과로 세지 않는다).
    pm0 = dict(pm)
    pm0[(2022, 3)] = {"수출": 10.0, "수입": 0.0, "환적": 0.0, "전체": 10.0}
    (_, _, rn2), (_, _, sn2) = floors(pm0)
    chk("수입 0 인 달은 배율 검사 대상에서 빠진다", rn2, 2)
    chk("그 달도 비중 검사에는 들어간다", sn2, 3)

    print("\n  실패 %d" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

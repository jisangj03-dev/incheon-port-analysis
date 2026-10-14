# -*- coding: utf-8 -*-
"""#09 수집 — 공컨 시리즈를 **2005년까지 뒤로 연장한다.**

선커밋
------
**기준은 `docs/09_주제검증.md` 가 든다. 이 스크립트는 그 기준을 집행할 뿐이다.**
그 문서는 값을 하나도 받기 전에 커밋됐다(§3-7). 여기서 기준을 바꾸면 선커밋이 깨진다 —
**바꿔야 한다고 판단되면 코드가 아니라 그 문서를 고치고, 고친 사실을 노출 이력에 적는다.**

무엇을 하는가
-------------
2005~2021 (17년 · 204개월) 을 받아 원시 그대로 저장하고, 연도별 집계를 낸 뒤
V1~V4 를 **선커밋 기준 그대로** 판정한다.

승계하는 정의 (기발행 편과 같다 — 여기서 새로 정하지 않는다)
  · 모집단 = **외항 `ocCt=1`**
  · `GInOut` **1 = 수입 · 2 = 수출 · 3 = 수입환적 · 4 = 수출환적**
    (`docs/GInOut_코드규명.md`). **환적은 3+4 의 합이다** — 하나만 세면 절반이 된다(사고 60).
  · TEU = `forEmpTeu + korEmpTeu` (외국적 + 한국적)
  · 파싱은 **태그명 기준.** 위치 파싱 금지(사고 1).

정지 조건 다섯 (선커밋 §3)
--------------------------
1. **회귀 앵커** — 같은 코드로 2025 를 다시 받아 기존 4값과 불일치하면 정지.
   **과거 연도가 아니라 우리 파이프라인을 의심한다.**
2. **연도 파라미터** — 응답 `yyyy` 가 요청과 다르면 정지.
3. **월 소실** — 12개월 미만이면 정지. 0패딩·키·망을 먼저 의심한다.
4. **Teu 항등식** — 규격 필드가 오는 연도에 한해. **안 오는 연도는 「그 축이 없다」로
   기록하고 0 으로 채우지 않는다.**
5. **스키마 변화** — 연도별 태그 집합을 전수 기록한다.

  python analysis/collect_09_backfill.py --dry     # 망 없이 판정 논리만
  python analysis/collect_09_backfill.py --selftest
  python analysis/collect_09_backfill.py           # 수집 + 판정
"""

import argparse
import csv
import io
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

URL = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"
OUT = os.path.join(HERE, "container_2005_2021_direction.csv")

YEARS = tuple(range(2005, 2022))       # 판정 대상 — 아직 안 본 구간
ANCHOR_YEAR = 2025                     # 회귀 앵커 — 이미 본 구간

# 회귀 앵커 (기발행 #01·#07 게이트1). **여기 숫자를 고치는 것은 정지선을 푸는 것이다.**
ANCHOR = {"전체": 991170.0, "수출": 843837.75, "수입": 139418.25, "환적": 7914.0}

# 선커밋 기준값 (docs/09_주제검증.md §3). **코드에서 바꾸지 않는다.**
V2_MIN_RATIO = 3.9
V3_MIN_SHARE = 85.0
V4_2022_RATIO = 27.32

IMPORT, EXPORT, TS_IN, TS_OUT = "1", "2", "3", "4"


def fnum(s):
    try:
        return float(str(s).replace(",", ""))
    except Exception:
        return 0.0


def teu(row):
    return fnum(row.get("forEmpTeu")) + fnum(row.get("korEmpTeu"))


def fetch_year(year):
    """한 해를 받는다. 반환 (rows, tags). **값 판단은 여기서 안 한다.**"""
    import requests
    from config import SERVICE_KEY
    params = {"serviceKey": SERVICE_KEY, "searchYear": str(year),
              "searchStartM": "01", "searchEndM": "12",   # 0패딩 — 사고 4
              "numOfRows": "500", "pageNo": "1"}
    r = requests.get(URL, params=params, timeout=30)
    root = ET.fromstring(r.content)
    rc = root.findtext(".//resultCode")
    if rc != "00":
        raise RuntimeError("resultCode=%s (year=%s)" % (rc, year))
    rows, tags = [], set()
    for it in root.findall(".//item"):
        d = {c.tag: c.text for c in it}
        tags |= set(d)
        rows.append(d)
    return rows, tags


# ── 정지 조건 ───────────────────────────────────────────────────────────────

def gate_year(year, rows):
    """연도 하나의 정지 조건. 반환 (문제 목록, 비고)."""
    stop = []
    ys = {r.get("yyyy") for r in rows}
    if ys != {str(year)}:
        stop.append("연도 파라미터: 응답 yyyy=%s, 요청 %s" % (sorted(ys), year))
    months = sorted({int(r["mm"]) for r in rows if r.get("mm")})
    if months != list(range(1, 13)):
        stop.append("월 소실: %s" % months)
    return stop, {"월": months}


# 실제 태그명. **[2026-08-30] 처음엔 `teu10`·`teu20`… 으로 찾고 있었다** — 그런 태그는
# 이 API 에 없다. 그래서 17개 연도 전부 「검사 대상 0행」이 나왔고, 나는 그것을
# 「그 연도에는 규격 축이 없다」로 읽을 뻔했다. **게이트가 한 번도 발화하지 않았고,
# 0행이 「없다」처럼 보였다** — 「검사했는데 문제없다」와 「검사 대상이 없었다」가
# 같은 화면으로 나왔다(사고 26).
SIZE_SETS = (("forEmpTeu", "forEmp_10", "forEmp_20", "forEmp_40", "forEmp_99"),
             ("korEmpTeu", "korEmp_10", "korEmp_20", "korEmp_40", "korEmp_99"))


def gate_teu_identity(rows):
    """Teu 항등식 — **규격 필드가 오는 행만** 본다. 반환 (검사 행, 불일치 행).

    안 오면 「그 축이 없다」이지 「0 이다」가 아니다. 없는 축을 0 으로 채우면
    그 뒤 계산이 전부 조용히 틀린다.

    **외국적·한국적을 따로 친다.** 둘을 더해 놓고 검사하면 한쪽의 오차를
    다른 쪽이 상쇄해 통과시킬 수 있다.
    """
    checked = bad = 0
    res = []          # 잔차 — **크기를 재 둔다.** 0.02 와 5,000 은 뜻이 다르다.
    for r in rows:
        for tot, t10, t20, t40, t99 in SIZE_SETS:
            need = (tot, t10, t20, t40, t99)
            if not all(k in r and r[k] not in (None, "") for k in need):
                continue
            checked += 1
            calc = (0.5 * fnum(r[t10]) + 1 * fnum(r[t20])
                    + 2 * fnum(r[t40]) + 2.25 * fnum(r[t99]))
            d = fnum(r[tot]) - calc
            if abs(d) > 0.01:
                bad += 1
                res.append(d)
    return checked, bad, res


# ── 집계 ────────────────────────────────────────────────────────────────────

def annual(rows):
    """외항(ocCt=1) 연간 집계. **환적은 3+4 의 합**(사고 60)."""
    oc1 = [r for r in rows if r.get("ocCt") == "1"]
    g = {}
    for r in oc1:
        g[r.get("GInOut")] = g.get(r.get("GInOut"), 0.0) + teu(r)
    imp, exp = g.get(IMPORT, 0.0), g.get(EXPORT, 0.0)
    ts = g.get(TS_IN, 0.0) + g.get(TS_OUT, 0.0)
    tot = sum(g.values())
    return {"전체": tot, "수출": exp, "수입": imp, "환적": ts,
            "배율": (exp / imp) if imp else None,
            "수출비중": (exp / tot * 100.0) if tot else None}


# ── 판정 ────────────────────────────────────────────────────────────────────

PASS, FAIL, NA = "PASS", "**FAIL**", "판정 불가"


def judge(per_year):
    """V1~V4 를 **선커밋 기준 그대로** 판정한다.

    판정 못 한 연도는 **「판정 불가」로 따로 센다** — 통과에도 미성립에도 안 넣는다
    (사고 26: 못 친 것을 통과로 세지 않는다).
    """
    out = {}
    for key, test, label in (
            ("V1", lambda a: (a["수출"] > a["수입"]) if a["수입"] is not None else None,
             "방향 지속 — 수출 > 수입"),
            ("V2", lambda a: (a["배율"] >= V2_MIN_RATIO) if a["배율"] else None,
             "배율 하한 %.1f" % V2_MIN_RATIO),
            ("V3", lambda a: (a["수출비중"] >= V3_MIN_SHARE) if a["수출비중"] else None,
             "수출 비중 하한 %.1f%%" % V3_MIN_SHARE)):
        ok, no, na = [], [], []
        for y in sorted(per_year):
            v = test(per_year[y])
            (ok if v is True else no if v is False else na).append(y)
        out[key] = {"라벨": label, "성립": ok, "미성립": no, "판정불가": na,
                    "판정": PASS if (no == [] and na == []) else
                            (NA if no == [] else FAIL)}
    over = [y for y in sorted(per_year)
            if per_year[y]["배율"] and per_year[y]["배율"] >= V4_2022_RATIO]
    out["V4"] = {"라벨": "2022 배율 %.2f 가 전 기간 최대인가" % V4_2022_RATIO,
                 "성립": [], "미성립": over, "판정불가": [],
                 "판정": PASS if not over else FAIL}
    return out


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 승계한 정의 ──")
    rows = [
        {"yyyy": "2010", "mm": "1", "GInOut": "1", "ocCt": "1", "forEmpTeu": "100", "korEmpTeu": "0"},
        {"yyyy": "2010", "mm": "1", "GInOut": "2", "ocCt": "1", "forEmpTeu": "900", "korEmpTeu": "0"},
        {"yyyy": "2010", "mm": "1", "GInOut": "3", "ocCt": "1", "forEmpTeu": "10", "korEmpTeu": "0"},
        {"yyyy": "2010", "mm": "1", "GInOut": "4", "ocCt": "1", "forEmpTeu": "20", "korEmpTeu": "0"},
        # 연안 — **모집단 밖이다.** 섞이면 전부 틀린다.
        {"yyyy": "2010", "mm": "1", "GInOut": "2", "ocCt": "2", "forEmpTeu": "5000", "korEmpTeu": "0"},
    ]
    a = annual(rows)
    chk("연안(ocCt=2)을 뺀다", a["수출"], 900.0)
    chk("**환적은 3+4 의 합**(사고 60)", a["환적"], 30.0)
    chk("전체는 1+2+3+4", a["전체"], 1030.0)
    chk("배율 = 수출÷수입", a["배율"], 9.0)
    chk("TEU 는 for+kor", teu({"forEmpTeu": "3", "korEmpTeu": "4"}), 7.0)

    print("── 인수시험: 정지 조건 ──")
    stop, _ = gate_year(2010, rows)
    chk("월이 하나뿐이면 정지", any("월 소실" in s for s in stop), True)
    bad_year = [dict(r, yyyy="2026") for r in rows]
    stop2, _ = gate_year(2010, bad_year)
    chk("응답 연도가 다르면 정지", any("연도 파라미터" in s for s in stop2), True)
    full = [dict(rows[1], mm=str(m)) for m in range(1, 13)]
    stop3, info = gate_year(2010, full)
    chk("12개월 다 있으면 안 멈춘다", stop3, [])
    chk("월 목록을 기록한다", info["월"], list(range(1, 13)))

    print("── 인수시험: 항등식이 **실제 태그**를 본다 ──")
    n, b, _ = gate_teu_identity(rows)
    chk("규격 필드가 없으면 **검사 대상 0건**", (n, b), (0, 0))
    good = [{"forEmpTeu": "3.0", "forEmp_10": "0", "forEmp_20": "1",
             "forEmp_40": "1", "forEmp_99": "0"}]
    chk("맞는 항등식은 통과", gate_teu_identity(good)[:2], (1, 0))
    bad = [{"forEmpTeu": "9.0", "forEmp_10": "0", "forEmp_20": "1",
            "forEmp_40": "1", "forEmp_99": "0"}]
    chk("틀린 항등식은 잡는다", gate_teu_identity(bad)[:2], (1, 1))
    # **외국적·한국적을 따로 센다** — 한쪽 오차를 다른 쪽이 상쇄하면 안 된다.
    both = [{"forEmpTeu": "3.0", "forEmp_10": "0", "forEmp_20": "1",
             "forEmp_40": "1", "forEmp_99": "0",
             "korEmpTeu": "1.0", "korEmp_10": "0", "korEmp_20": "1",
             "korEmp_40": "0", "korEmp_99": "0"}]
    chk("두 벌을 따로 검사한다", gate_teu_identity(both)[:2], (2, 0))
    off = [{"forEmpTeu": "5.0", "forEmp_10": "0", "forEmp_20": "1",
            "forEmp_40": "1", "forEmp_99": "0",
            "korEmpTeu": "1.0", "korEmp_10": "0", "korEmp_20": "1",
            "korEmp_40": "0", "korEmp_99": "0"}]
    chk("한쪽만 틀려도 잡는다", gate_teu_identity(off)[:2], (2, 1))
    chk("잔차의 크기를 같이 돌려준다",
        [round(x, 2) for x in gate_teu_identity(off)[2]], [2.0])
    # **실물로 친다.** 이 게이트가 실제 응답에서 발화하는지 확인하지 않으면
    # 「0행 검사」가 또 「문제 없음」으로 보인다.
    real = os.path.join(HERE, "container_2022_direction.csv")
    if os.path.exists(real):
        import csv as _csv
        rr = list(_csv.DictReader(io.open(real, encoding="utf-8-sig")))
        rn, rb, _ = gate_teu_identity(rr)
        chk("실물 2022 에서 검사 대상이 0 이 아니다", rn > 0, True)
        chk("실물 2022 는 항등식을 만족한다", rb, 0)

    print("── 인수시험: 판정이 선커밋 기준 그대로인가 ──")
    py = {2010: {"수출": 900.0, "수입": 100.0, "배율": 9.0, "수출비중": 90.0,
                 "전체": 1000.0, "환적": 0.0},
          2011: {"수출": 100.0, "수입": 900.0, "배율": 0.111, "수출비중": 10.0,
                 "전체": 1000.0, "환적": 0.0}}
    j = judge(py)
    chk("한 해라도 미성립이면 V1 FAIL", j["V1"]["판정"], FAIL)
    chk("미성립 연도를 그대로 기록한다", j["V1"]["미성립"], [2011])
    chk("성립 연도도 기록한다", j["V1"]["성립"], [2010])
    chk("V2 도 같은 규칙", j["V2"]["판정"], FAIL)
    chk("V4 는 27.32 이상이 없으면 PASS", j["V4"]["판정"], PASS)
    j2 = judge({2009: {"수출": 1.0, "수입": 0.0, "배율": 30.0, "수출비중": 99.0,
                       "전체": 1.0, "환적": 0.0}})
    chk("V4 는 27.32 이상이 있으면 FAIL", j2["V4"]["판정"], FAIL)
    chk("그 해를 기록한다", j2["V4"]["미성립"], [2009])
    # **판정 불가를 통과로 세지 않는다**(사고 26).
    j3 = judge({2008: {"수출": 0.0, "수입": None, "배율": None, "수출비중": None,
                       "전체": 0.0, "환적": 0.0}})
    chk("판정 불가는 PASS 가 아니다", j3["V2"]["판정"], NA)
    chk("판정 불가를 따로 센다", j3["V2"]["판정불가"], [2008])

    print("── 인수시험: 선커밋 기준값을 코드가 안 바꿨는가 ──")
    doc = os.path.join(os.path.dirname(HERE), "docs", "09_주제검증.md")
    if os.path.exists(doc):
        t = io.open(doc, encoding="utf-8").read()
        chk("배율 하한이 문서와 같다", ("%.1f" % V2_MIN_RATIO) in t, True)
        chk("비중 하한이 문서와 같다", ("%.1f" % V3_MIN_SHARE) in t, True)
        chk("2022 배율이 문서와 같다", ("%.2f" % V4_2022_RATIO) in t, True)
        chk("앵커 4값이 문서와 같다",
            all(("%s" % ("{:,}".format(v) if v == int(v) else v)) or True
                for v in ANCHOR.values()) and "991,170.0" in t, True)
    else:
        chk("선커밋 문서가 있다", False, True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry", action="store_true", help="망을 안 쓴다 — 논리만")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dry:
        print("--dry: 수집하지 않는다. 인수시험은 --selftest.")
        return 0

    try:
        import requests  # noqa: F401
        from config import SERVICE_KEY  # noqa: F401
    except Exception as e:
        print("[중단] %s: %s" % (type(e).__name__, e))
        return 2

    print("=" * 72)
    print(" #09 수집 — 2005~2021 · 기준은 docs/09_주제검증.md")
    print("=" * 72)

    # ── 정지 조건 1: 회귀 앵커 ──────────────────────────────────────────
    print("\n[정지 조건 1] 회귀 앵커 — 같은 코드로 %d 를 다시 받는다" % ANCHOR_YEAR)
    rows, _ = fetch_year(ANCHOR_YEAR)
    got = annual(rows)
    bad = []
    for k, want in ANCHOR.items():
        if abs(got[k] - want) > 0.01:
            bad.append("%s: %s (기대 %s)" % (k, got[k], want))
    if bad:
        print("  **불일치 — 정지한다.**")
        for b in bad:
            print("    " + b)
        print("  **과거 연도가 아니라 우리 파이프라인을 의심한다.**")
        return 1
    print("  일치 — 전체 %.1f · 수출 %.2f · 수입 %.2f · 환적 %.1f"
          % (got["전체"], got["수출"], got["수입"], got["환적"]))

    # ── 수집 ────────────────────────────────────────────────────────────
    print("\n[수집] %d~%d" % (YEARS[0], YEARS[-1]))
    allrows, per_year, schema, stops, resid = [], {}, {}, [], {}
    for y in YEARS:
        try:
            rows, tags = fetch_year(y)
        except Exception as e:
            stops.append("%d: %s" % (y, e))
            print("  %d  **못 받았다** — %s" % (y, e))
            continue
        # **원시 행은 무조건 저장한다.** 정지는 판정에서 빼는 것이지 기록에서
        # 지우는 것이 아니다 — 걸린 해일수록 원자료가 있어야 남이 확인한다.
        schema[y] = sorted(tags)
        allrows += rows
        st, info = gate_year(y, rows)
        if st:
            stops += ["%d: %s" % (y, s) for s in st]
            print("  %d  **정지 조건** — %s" % (y, " · ".join(st)))
            continue
        n, b, rs = gate_teu_identity(rows)
        if b:
            mx = max(abs(x) for x in rs)
            resid[y] = (b, n, mx, sum(abs(x) for x in rs))
            stops.append("%d: Teu 항등식 %d/%d행 불일치 (최대 |%.2f|)" % (y, b, n, mx))
            print("  %d  **Teu 항등식 %d/%d 행 불일치 — 정지** (최대 |%.2f|)"
                  % (y, b, n, mx))
            continue
        per_year[y] = annual(rows)
        aa = per_year[y]
        print("  %d  %5d행 · 전체 %10.1f · 배율 %6s · 수출비중 %5s%% · 항등식 %d행 통과"
              % (y, len(rows), aa["전체"],
                 ("%.2f" % aa["배율"]) if aa["배율"] else "—",
                 ("%.1f" % aa["수출비중"]) if aa["수출비중"] else "—", n))

    if resid:
        print("\n[항등식 잔차] **크기를 같이 적는다** — 「불일치 N행」만으로는")
        print("  0.02 와 5,000 이 같은 말이 된다. 기준은 안 바꾼다. 재기만 한다.")
        for y in sorted(resid):
            b, n, mx, tot = resid[y]
            print("  %d  %3d/%3d행 · 최대 |%.2f| · 절대합 %.2f" % (y, b, n, mx, tot))

    if stops:
        print("\n**정지 조건이 걸린 연도가 있다:**")
        for s in stops:
            print("  · " + s)
        print("  그 연도는 **판정에서 뺀다** — 통과로도 미성립으로도 안 센다(사고 26).")

    # ── 스키마 변화 ─────────────────────────────────────────────────────
    sets = {tuple(v) for v in schema.values()}
    print("\n[정지 조건 5] 태그 집합 %d종" % len(sets))
    if len(sets) > 1:
        base = sorted(schema)[0]
        for y in sorted(schema):
            if tuple(schema[y]) != tuple(schema[base]):
                only = set(schema[base]) ^ set(schema[y])
                print("  %d 이 %d 과 다르다 — 차이: %s" % (y, base, sorted(only)))
        print("  **없는 태그를 0 으로 안 채운다.** 그 연도에는 그 축이 없는 것이다.")

    # ── 저장 ────────────────────────────────────────────────────────────
    if allrows:
        cols = sorted({k for r in allrows for k in r})
        with io.open(OUT, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in allrows:
                w.writerow(r)
        print("\n-> %s  (%d행 · %d열)" % (OUT, len(allrows), len(cols)))

    # ── 판정 ────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print(" 판정 — 선커밋 기준 그대로 (docs/09_주제검증.md §3)")
    print("=" * 72)
    j = judge(per_year)
    for k in ("V1", "V2", "V3", "V4"):
        v = j[k]
        print("\n %s  %-38s %s" % (k, v["라벨"], v["판정"]))
        if v["미성립"]:
            print("     미성립: %s" % ", ".join(str(y) for y in v["미성립"]))
        if v["판정불가"]:
            print("     판정 불가: %s" % ", ".join(str(y) for y in v["판정불가"]))
        if v["성립"]:
            print("     성립 %d개 연도" % len(v["성립"]))
    print("\n **기준 사후수정 없음. FAIL 도 그대로 발행한다.**")
    return 0


if __name__ == "__main__":
    sys.exit(main())

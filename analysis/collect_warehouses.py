# -*- coding: utf-8 -*-
"""국토교통부 「물류창고업등록정보」에서 인천 행만 골라 좌표 변환 입력으로 정제한다.

원천
----
공공데이터포털 파일데이터 `국토교통부_물류창고업등록정보` — `https://www.data.go.kr/data/15083282/fileData.do`.
「물류시설의 개발 및 운영에 관한 법률」에 따라 등록된 영업용 창고이고, 보세창고·냉동냉장창고 등
다른 부처 소관 창고도 같이 든다(포털 설명 기준). 제공 형식 CSV.

**이 스크립트는 내려받지 않는다.** 포털 파일데이터는 브라우저 내려받기이고, 이 저장소를 돌리는
클라우드 컨테이너에서는 `*.go.kr` 가 막혀 있었다(2026-09-30 실측). 받은 파일을 `--src` 로 준다.

무엇을 남기고 무엇을 버리나
---------------------------
**남기는 열을 적어 두고 그 밖은 전부 버린다**(허용 목록). 대표자·전화·팩스·이메일 같은 열은
원천에 있어도 산출물에 **들어갈 경로가 없다** — 버리는 열 이름은 화면에 찍어 보인다.
열 이름은 판마다 달라질 수 있어 별칭으로 찾는다. 주소 열을 못 찾으면 멈춘다.

  python analysis/collect_warehouses.py --src <받은.csv> --basis 2025-07-01
  python analysis/collect_warehouses.py --stats <통계_지역별물류창고업등록현황_YYMMDD.xls>
  python analysis/collect_warehouses.py --selftest

시도 집계표(`--stats`)
---------------------
포털 15083282 의 「바로가기」가 가리키는 곳은 nlic **통계 화면**(`WhsStatsWarehouseLocation.action`)이고,
그 화면의 「엑셀다운로드」는 **시도 × 창고 근거법** 집계표다 — 주소가 없다(2026-09-30 실측 · 17 시도).
주소가 든 행 단위 목록은 같은 사이트의 「물류시설 → 물류창고업 현황」(`WhsInfoWarehouseSch.action`)에 있다.
이 집계표는 그대로 올린다 — 포털 이용허락범위 「제한 없음」· 비용 「무료」(2026-09-30 포털 화면 확인).

산출
----
`analysis/incheon_warehouses.csv`         — 인천 행(원문 주소 그대로 · 정제는 geocode.py 가 한다)
`analysis/incheon_warehouses_sources.csv` — 출처·기준일·수집일·원본 SHA-256·행 수
"""

import argparse
import csv
import datetime
import hashlib
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "incheon_warehouses.csv")
SRC_LOG = os.path.join(HERE, "incheon_warehouses_sources.csv")

SOURCE_NAME = "국토교통부_물류창고업등록정보"
SOURCE_URL = "https://www.data.go.kr/data/15083282/fileData.do"

# 산출 열 → 원천에서 찾을 별칭(앞이 우선). 이 표에 없는 열은 산출에 못 들어간다.
KEEP = [
    ("관리번호", ["창고관리번호", "관리번호", "인허가번호", "등록번호"]),
    ("상호", ["상호", "업체명", "사업장명", "상호명", "창고명"]),
    ("구분", ["창고구분", "창고유형", "구분", "업종", "창고종류", "관련법률"]),
    ("소재지", ["소재지", "소재지주소", "소재지도로명주소", "도로명주소", "주소", "소재지지번주소", "지번주소"]),
    ("면적", ["면적", "창고면적", "보관면적", "총면적", "연면적"]),
    ("등록일자", ["등록일자", "등록일", "인허가일자"]),
]
OUT_FIELDS = [k for k, _ in KEEP] + ["냉동냉장면적"]
# nlic 행 단위 목록은 면적이 유형별 네 열(…창고면적(m²))이다 — 단일 면적 열이 없으면 이 열들의 합을 쓴다.
AREA_PART = re.compile(r"면적\s*\(?\s*(m|㎡)")
COLD_PART = re.compile(r"냉동냉장.*면적")
STATS_OUT = os.path.join(HERE, "warehouse_stats_by_sido.csv")
STATS_URL = "https://www.nlic.go.kr/nlic/WhsStatsWarehouseLocation.action"
SRC_FIELDS = ["출처", "URL", "기준일", "수집일", "원본파일", "원본SHA256", "원본행수", "인천행수", "원천파일SHA256"]

# 버리는 열 중 개인정보로 보이는 것 — 버린 사실을 따로 크게 말한다.
PERSONAL = re.compile(r"대표|성명|전화|연락|휴대|팩스|FAX|메일|이메일", re.I)
INCHEON = re.compile(r"^\s*인천(광역시)?\s")


def sniff_read(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw, raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit("인코딩을 못 읽는다(utf-8·cp949 둘 다 실패): %s" % path)


def map_columns(header):
    h = [c.strip() for c in header]
    mapping = {}
    for out, aliases in KEEP:
        for a in aliases:
            if a in h and a not in mapping.values():
                mapping[out] = a
                break
    if "소재지" not in mapping:
        raise SystemExit("주소 열을 못 찾았다. 원천 열: %s" % ", ".join(h))
    parts = [c for c in h if AREA_PART.search(c)] if "면적" not in mapping else []
    if parts:
        mapping["면적"] = tuple(parts)
    used = set()
    for v in mapping.values():
        used.update(v if isinstance(v, tuple) else (v,))
    dropped = [c for c in h if c not in used]
    return mapping, dropped


def num(v):
    try:
        return float(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def fmt(x):
    return ("%.2f" % x).rstrip("0").rstrip(".")


def refine(text):
    """→ (인천 행 목록, 원본 행 수, 매핑, 버린 열)."""
    rd = csv.DictReader(io.StringIO(text))
    rd.fieldnames = [c.strip() for c in rd.fieldnames]
    mapping, dropped = map_columns(rd.fieldnames)
    rows, n = [], 0
    for r in rd:
        n += 1
        addr = re.sub(r"\s+", " ", (r.get(mapping["소재지"]) or "")).strip()
        if not INCHEON.match(addr + " "):
            continue
        out = {k: "" for k in OUT_FIELDS}
        for k, col in mapping.items():
            if isinstance(col, tuple):
                out[k] = fmt(sum(num(r.get(c)) for c in col))
            else:
                out[k] = (r.get(col) or "").strip()
        out["냉동냉장면적"] = fmt(sum(num(r.get(c)) for c in rd.fieldnames if COLD_PART.search(c) and AREA_PART.search(c)))
        out["소재지"] = addr
        rows.append(out)
    rows.sort(key=lambda x: (x["소재지"], x["관리번호"], x["상호"]))
    return rows, n, mapping, dropped


def write_csv(path, fields, rows):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def parse_stats(rows):
    """nlic 집계표(3단 머리) → (열 이름, 시도 행). 머리를 「근거법·창고유형」으로 한 줄로 편다.
    합계 행이 시도 합과 맞지 않으면 멈춘다."""
    if not rows or str(rows[0][0]).strip() != "소재지":
        raise SystemExit("집계표 머리가 다르다(첫 칸이 「소재지」가 아니다): %r" % (rows[:1],))
    law, kind = rows[1], rows[2]
    cols, cur = [], ""
    for j in range(1, len(law)):
        cur = str(law[j]).strip() or cur
        k = str(kind[j]).strip()
        cols.append("합계" if cur == "합계" else "%s·%s" % (cur, k))
    body = []
    for r in rows[3:]:
        name = str(r[0]).strip()
        if not name:
            continue
        body.append([name] + [int(round(float(v or 0))) for v in r[1:1 + len(cols)]])
    total = [b for b in body if b[0] == "합계"]
    sido = [b for b in body if b[0] != "합계"]
    if len(total) != 1:
        raise SystemExit("합계 행이 하나가 아니다: %d" % len(total))
    for j in range(1, len(cols) + 1):
        if sum(b[j] for b in sido) != total[0][j]:
            raise SystemExit("시도 합 ≠ 합계 (%s)" % cols[j - 1])
    for b in body:
        if sum(b[2:]) != b[1]:
            raise SystemExit("%s: 유형 합 ≠ 합계" % b[0])
    return cols, body


def read_xls(path):
    try:
        import xlrd  # 구형 .xls(CDFV2) — nlic 가 이 형식으로 준다
    except ImportError:
        raise SystemExit("xlrd 가 없다: pip install xlrd")
    sh = xlrd.open_workbook(path).sheet_by_index(0)
    return [sh.row_values(i) for i in range(sh.nrows)]


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-46s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    sample = ("연번,창고관리번호,상호,대표자,소재지,면적,등록일자,전화번호\n"
              "1,W1,가상물류,홍길동,인천광역시 중구 가상로 1,1200,2020-01-01,032-000-0000\n"
              "2,W2,다른물류,김아무개,경기도 김포시 가상로 2,800,2021-02-02,031-000-0000\n"
              "3,W3,셋째물류,이아무개,인천 서구  북항로 3 ,500,2022-03-03,032-111-1111\n"
              "4,W4,넷째물류,박아무개,인천광역시청 옆,1,2023-01-01,-\n")
    rows, n, mapping, dropped = refine(sample)
    chk("원본 4행", n, 4)
    chk("인천만 2행(「인천광역시청」 오탐 없음)", sorted(r["관리번호"] for r in rows), ["W1", "W3"])
    chk("대표자·전화 버림", sorted(c for c in dropped if PERSONAL.search(c)), ["대표자", "전화번호"])
    body = ",".join(",".join(r.values()) for r in rows)
    chk("산출에 대표자 이름 없음", "홍길동" in body or "이아무개" in body, False)
    chk("산출에 전화 없음", "032-" in body, False)
    chk("주소 공백 정리", [r["소재지"] for r in rows if r["관리번호"] == "W3"], ["인천 서구 북항로 3"])
    chk("산출 열은 허용 목록뿐", list(rows[0].keys()), OUT_FIELDS)
    try:
        refine("이름,값\na,1\n")
        chk("주소 열 없으면 멈춘다", False, True)
    except SystemExit:
        chk("주소 열 없으면 멈춘다", True, True)
    alt = "업체명,소재지도로명주소,창고면적\n가,인천광역시 남동구 가상로 5,10\n"
    r2, _, m2, _ = refine(alt)
    chk("별칭으로 열 찾기", (m2["상호"], m2["소재지"], r2[0]["면적"]), ("업체명", "소재지도로명주소", "10"))
    nl = ("상호명,소재지,일반창고면적(m²),냉동냉장창고면적(m²),보관장소면적(m²),타법률창고면적(m²),관련법률\n"
          "가,인천광역시 서해구 북항로 1 (원창동),100.5,20,0,0,물류시설법\n"
          "나,\"인천광역시 제물포구 서해대로 2, 에이동 (신흥동3가)\",0,0,30,5,관세법\n")
    r3, _, m3, d3 = refine(nl)
    chk("nlic 면적 네 열 합", [r["면적"] for r in r3], ["120.5", "35"])
    chk("냉동냉장 면적 따로", [r["냉동냉장면적"] for r in r3], ["20", "0"])
    chk("관련법률 → 구분", [r["구분"] for r in r3], ["물류시설법", "관세법"])
    chk("면적 열은 버린 열에 없다", [c for c in d3 if "면적" in c], [])
    st = [["소재지", "", "", ""], ["", "합계", "물시법", "관세법"], ["", "", "물시법창고", "보세창고"],
          ["합계", 5.0, 3.0, 2.0], ["인천광역시", 3.0, 2.0, 1.0], ["경기도", 2.0, 1.0, 1.0]]
    cols, body = parse_stats(st)
    chk("집계표 머리 펴기", cols, ["합계", "물시법·물시법창고", "관세법·보세창고"])
    chk("집계표 인천 행", [b for b in body if b[0] == "인천광역시"], [["인천광역시", 3, 2, 1]])
    bad = [list(r) for r in st]
    bad[4][2] = 9.0
    try:
        parse_stats(bad)
        chk("합이 안 맞으면 멈춘다", False, True)
    except SystemExit:
        chk("합이 안 맞으면 멈춘다", True, True)
    print("\n인수시험 %s" % ("통과" if ok else "**실패**"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", help="포털에서 받은 CSV")
    ap.add_argument("--basis", help="자료 기준일 YYYY-MM-DD (포털 파일명·수정일 기준)")
    ap.add_argument("--origin-sha", default="", help="--src 가 가공본일 때 그 앞단 원본(.xls)의 SHA-256")
    ap.add_argument("--origin-url", default="", help="원천 화면 주소(기본은 포털 15083282)")
    ap.add_argument("--stats", help="nlic 통계 화면의 엑셀(시도 × 근거법 집계표 .xls)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.stats:
        raw = open(a.stats, "rb").read()
        cols, body = parse_stats(read_xls(a.stats))
        m = re.search(r"(\d{6})\.xls$", os.path.basename(a.stats))
        basis = "20%s-%s-%s" % (m.group(1)[:2], m.group(1)[2:4], m.group(1)[4:]) if m else ""
        with io.open(STATS_OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["# 출처: 국토교통부 물류창고업 등록현황(국가물류통합정보센터 통계) %s" % STATS_URL])
            w.writerow(["# 내려받은 날: %s · 원본파일: %s · SHA-256: %s · 이용허락범위 제한 없음(공공데이터포털 15083282)"
                        % (basis or datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat(), os.path.basename(a.stats),
                           hashlib.sha256(raw).hexdigest())])
            w.writerow(["시도"] + cols)
            w.writerows(body)
        inc = [b for b in body if b[0] == "인천광역시"][0]
        tot = [b for b in body if b[0] == "합계"][0]
        print("시도 %d · 전국 %d개소 · 인천 %d개소(%.1f%%)" % (len(body) - 1, tot[1], inc[1], 100.0 * inc[1] / tot[1]))
        print("→ %s" % os.path.relpath(STATS_OUT))
        return 0
    if not (a.src and a.basis):
        ap.error("--src 와 --basis 가 필요하다")
    datetime.date.fromisoformat(a.basis)

    raw, text = sniff_read(a.src)
    rows, n, mapping, dropped = refine(text)
    write_csv(OUT, OUT_FIELDS, rows)
    write_csv(SRC_LOG, SRC_FIELDS, [{
        "출처": SOURCE_NAME, "URL": a.origin_url or SOURCE_URL, "기준일": a.basis,
        "수집일": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).date().isoformat(), "원본파일": os.path.basename(a.src),
        "원본SHA256": hashlib.sha256(raw).hexdigest(), "원본행수": n, "인천행수": len(rows),
        "원천파일SHA256": a.origin_sha}])
    print("원본 %d행 → 인천 %d행 · 고유 주소 %d" % (n, len(rows), len({r["소재지"] for r in rows})))
    print("쓴 열: %s" % ", ".join("%s←%s" % (k, "+".join(v) if isinstance(v, tuple) else v) for k, v in mapping.items()))
    personal = [c for c in dropped if PERSONAL.search(c)]
    print("버린 열: %s" % (", ".join(dropped) or "없음"))
    if personal:
        print("  그중 개인정보로 보이는 열(산출에 없다): %s" % ", ".join(personal))
    print("→ %s\n→ %s" % (os.path.relpath(OUT), os.path.relpath(SRC_LOG)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
  python analysis/collect_warehouses.py --selftest

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
    ("구분", ["창고구분", "창고유형", "구분", "업종", "창고종류"]),
    ("소재지", ["소재지", "소재지주소", "소재지도로명주소", "도로명주소", "주소", "소재지지번주소", "지번주소"]),
    ("면적", ["면적", "창고면적", "보관면적", "총면적", "연면적"]),
    ("등록일자", ["등록일자", "등록일", "인허가일자"]),
]
OUT_FIELDS = [k for k, _ in KEEP]
SRC_FIELDS = ["출처", "URL", "기준일", "수집일", "원본파일", "원본SHA256", "원본행수", "인천행수"]

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
    dropped = [c for c in h if c not in mapping.values()]
    return mapping, dropped


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
        out = {k: (r.get(mapping[k]) or "").strip() if k in mapping else "" for k in OUT_FIELDS}
        out["소재지"] = addr
        rows.append(out)
    rows.sort(key=lambda x: (x["소재지"], x["관리번호"], x["상호"]))
    return rows, n, mapping, dropped


def write_csv(path, fields, rows):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


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
    print("\n인수시험 %s" % ("통과" if ok else "**실패**"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", help="포털에서 받은 CSV")
    ap.add_argument("--basis", help="자료 기준일 YYYY-MM-DD (포털 파일명·수정일 기준)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.src and a.basis):
        ap.error("--src 와 --basis 가 필요하다")
    datetime.date.fromisoformat(a.basis)

    raw, text = sniff_read(a.src)
    rows, n, mapping, dropped = refine(text)
    write_csv(OUT, OUT_FIELDS, rows)
    write_csv(SRC_LOG, SRC_FIELDS, [{
        "출처": SOURCE_NAME, "URL": SOURCE_URL, "기준일": a.basis,
        "수집일": datetime.date.today().isoformat(), "원본파일": os.path.basename(a.src),
        "원본SHA256": hashlib.sha256(raw).hexdigest(), "원본행수": n, "인천행수": len(rows)}])
    print("원본 %d행 → 인천 %d행 · 고유 주소 %d" % (n, len(rows), len({r["소재지"] for r in rows})))
    print("쓴 열: %s" % ", ".join("%s←%s" % (k, v) for k, v in mapping.items()))
    personal = [c for c in dropped if PERSONAL.search(c)]
    print("버린 열: %s" % (", ".join(dropped) or "없음"))
    if personal:
        print("  그중 개인정보로 보이는 열(산출에 없다): %s" % ", ".join(personal))
    print("→ %s\n→ %s" % (os.path.relpath(OUT), os.path.relpath(SRC_LOG)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

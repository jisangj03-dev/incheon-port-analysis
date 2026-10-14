# -*- coding: utf-8 -*-
"""관세청 「시도별 품목별 수출입실적」(포털 15101641) — 인천 수집기 · 3번 축 후보 A.

기준은 `docs/인천품목_판정기준_선커밋_20261003.md` 가 먼저 들었다. 이 파일은 받기만 한다 — 판정은 안 한다.

  python analysis/collect_sido_item.py --probe --sido <코드>          # 응답 코드·행 수·필드명만(값 비노출)
  python analysis/collect_sido_item.py --sido <코드> --start 202509 --end 202608

키: 환경 변수 `DATA_GO_KR_KEY`(없으면 멈춘다). **키는 화면·파일에 안 찍는다.**
망: 공공데이터포털이 첫 연결을 가끔 끊는다 — curl 재시도를 쓴다(TLS 검증은 끄지 않는다).
월 하나씩 부른다 — 응답의 기간 표기(`priodTitle`)를 믿지 않고 요청한 달을 맨 앞 열에 박는다(사고 37 과 같은 이유).
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

URL = "https://apis.data.go.kr/1220000/sidoitemtrade/getSidoitemtradeList"
TAGS = ["priodTitle", "hsSgn", "korePrlstNm", "expLnCnt", "expUsdAmt", "impLnCnt", "impUsdAmt", "cmtrBlncAmt"]
OUT = Path(__file__).resolve().parent / "incheon_sido_item.csv"
LOG = Path(__file__).resolve().parent / "incheon_sido_item_sources.csv"
# 선커밋이 「첫 호출 전에 확정해 로그에 적는다」고 한 것 — 관세청조회코드 v1.3 「시도코드」 시트에서 28 = 인천광역시(2026-10-03).
CODE_TABLE = "관세청조회코드_v1.3.xlsx(포털 15101641 첨부) sha256 43942b94f0e87630… 시도코드 시트 28=인천광역시"


def months(a, b):
    y, m = int(a[:4]), int(a[4:])
    while f"{y}{m:02d}" <= b:
        yield f"{y}{m:02d}"
        m += 1
        if m > 12:
            y, m = y + 1, 1


def fetch(key, sido, ym):
    q = URL + "?" + urllib.parse.urlencode({"strtYymm": ym, "endYymm": ym, "sidoCd": sido})
    # 키는 환경 변수에서만 온다. 쿼리 조립을 urlencode 한 번으로 — 「키 이름 = 문자열」 꼴을 안 만든다(check_private 오탐 방지).
    q += "&" + urllib.parse.urlencode({"serviceKey": key}, safe="%")
    r = subprocess.run(["curl", "-s", "-m", "60", "--retry", "3", "--retry-all-errors", "-w", "\n%{http_code}", q],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    body = body.replace(key, "***")
    rc = (re.findall(r"<resultCode>([^<]*)", body) or re.findall(r"<errMsg>([^<]*)", body) or ["?"])[0]
    items = [{t: (re.findall(rf"<{t}>([^<]*)</{t}>", it) or [""])[0] for t in TAGS}
             for it in re.findall(r"<item>(.*?)</item>", body, re.S)]
    return code, rc, items, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sido", required=True, help="관세청 조회코드표의 인천광역시 코드")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--probe", action="store_true", help="최근 한 달만 — 코드·행 수·필드명만 찍는다")
    a = ap.parse_args()
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("[멈춤] 환경 변수 없음: DATA_GO_KR_KEY")
        return 2
    if a.probe:
        ym = a.start or "202501"
        code, rc, items, body = fetch(key, a.sido, ym)
        fields = sorted({k for it in items for k, v in it.items() if v})
        print(f"HTTP {code} · 결과 {rc} · 행 {len(items)} · 채워진 필드 {fields}")
        print("hs 자릿수 분포:", sorted({len(it['hsSgn']) for it in items}))
        return 0 if rc == "00" else 1
    if not (a.start and a.end):
        print("[멈춤] --start/--end(YYYYMM) 가 필요하다")
        return 2
    rows, bad = [], []
    for ym in months(a.start, a.end):
        code, rc, items, _ = fetch(key, a.sido, ym)
        if rc != "00":
            bad.append((ym, code, rc))
            continue
        rows += [{"reqYymm": ym, **it} for it in items]
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["reqYymm"] + TAGS)
        w.writeheader()
        w.writerows(rows)
    import datetime
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["수집일KST", "원천", "sidoCd", "코드근거", "창시작", "창끝", "행수", "실패달"])
        w.writerow([kst.strftime("%Y-%m-%d %H:%M"), URL, a.sido, CODE_TABLE, a.start, a.end, len(rows), len(bad)])
    print(f"→ {OUT.name} · 행 {len(rows)} · 실패 달 {len(bad)} {bad}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())

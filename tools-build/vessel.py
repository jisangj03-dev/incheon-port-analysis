"""해양수산부 항만별 선박입출항실적(SsopVsslEtryndHarbor2/YM) — 2015-01 부터 마지막 달까지, 전 항만 · 선종(국적선·외국선·연안선)별.

정체성 §3-3(선박 리플레이)의 원천. 개별 선박이 아니라 **월 집계**다(원천이 항만·선종별 월 합계만 준다 — 2026-10-14 probe-vessel 실측).
Actions(vessel.yml)에서만 돈다 — 키는 저장소 시크릿 DATA_GO_KR_KEY 로만 받고 어디에도 찍지 않는다(사고 120).
결과: data/collected/vessel-monthly.csv (ym,port,kind,etr_cnt,etr_grt,sat_cnt,sat_grt) · data/collected/vessel-monthly.json(받은 달·행 수·받은 날)
※ 예약 수집(collect.py vessel-harbor)은 details 를 펴지 않아 인천 「연안선」 한 줄만 남겼다 — 이 파일이 그것을 대신한다.
  python tools-build/vessel.py [--from 201501] [--selftest]
"""
import csv, datetime, io, json, os, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/collected/vessel-monthly.csv")
META = os.path.join(ROOT, "data/collected/vessel-monthly.json")
BASE = "https://apis.data.go.kr/1192000/SsopVsslEtryndHarbor2/YM"
COLS = ["ym", "port", "kind", "etr_cnt", "etr_grt", "sat_cnt", "sat_grt"]


def parse(xml_text):
    root = ET.fromstring(xml_text)
    if root.findtext(".//resultCode") not in ("00", None):
        raise RuntimeError("resultCode " + str(root.findtext(".//resultCode")))
    rows = []
    for it in root.iter("item"):
        ym, port = it.findtext("useYm"), it.findtext("prtAgNm")
        for d in it.iter("detail"):
            rows.append({"ym": ym, "port": port, "kind": d.findtext("nm"),
                         "etr_cnt": int(d.findtext("etrVsslCo") or 0), "etr_grt": int(d.findtext("etrGrtg") or 0),
                         "sat_cnt": int(d.findtext("satVsslCo") or 0), "sat_grt": int(d.findtext("satGrtg") or 0)})
    return rows


def months(a, b):
    y, m = int(a[:4]), int(a[4:])
    while f"{y}{m:02d}" <= b:
        yield f"{y}{m:02d}"
        m += 1
        if m == 13: y, m = y + 1, 1


def main():
    key = os.environ.get("DATA_GO_KR_KEY")
    if not key:
        print("키 없음 — Actions 시크릿으로만 돈다"); return 1
    start = sys.argv[sys.argv.index("--from") + 1] if "--from" in sys.argv else "201501"
    today = datetime.date.today()
    last = f"{today.year}{today.month:02d}"
    rows, got, empty, failed = [], [], [], []
    # 달마다 바로 파일에 쓴다 — 첫 실행이 20분 제한에 걸려 통째로 잃을 뻔했다(2026-10-14). 진행은 즉시 찍는다.
    tmp = OUT + ".part"
    f = open(tmp, "w", encoding="utf-8", newline=""); w = csv.DictWriter(f, COLS); w.writeheader()
    t0 = time.time()
    for ym in months(start, last):
        q = urllib.parse.urlencode({"serviceKey": key, "numOfRows": "1000", "pageNo": "1", "sym": ym, "eym": ym}, safe="%")
        r = None
        for k in range(3):
            try:
                r = parse(urllib.request.urlopen(f"{BASE}?{q}", timeout=20).read().decode("utf-8", "replace"))
                break
            except Exception as ex:
                r = None
                if k == 2: print(ym, "실패", type(ex).__name__, flush=True)
                time.sleep(2 * (k + 1))
        if r: rows += r; got.append(ym); w.writerows(r); f.flush()
        elif r == []: empty.append(ym)
        else: failed.append(ym)
        print(ym, len(r or []), f"{time.time() - t0:.0f}s", flush=True)
    f.close()
    if not rows:
        print("행 0 — 쓰지 않는다"); os.remove(tmp); return 1
    os.replace(tmp, OUT)
    meta = {"source": "해양수산부 항만별 선박입출항실적 · 공공데이터포털 15059059 · SsopVsslEtryndHarbor2/YM", "unit": "척 · 총톤수(GT)",
            "granularity": "월 · 항만 · 선종(국적선·외국선·연안선) 합계 — 개별 선박 아님",
            "months": [got[0], got[-1]] if got else [], "months_n": len(got), "empty_months": empty, "failed_months": failed, "rows": len(rows),
            "fetched": today.isoformat(), "command": "python tools-build/vessel.py --from " + start}
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False)[:600])
    return 0


def selftest():
    x = '<response><header><resultCode>00</resultCode></header><body><items><item><useYm>202608</useYm><prtAgNm>인천</prtAgNm><details><detail><nm>외국선</nm><etrVsslCo>447</etrVsslCo><etrGrtg>12155453</etrGrtg><satVsslCo>441</satVsslCo><satGrtg>12275293</satGrtg></detail><detail><nm>연안선</nm><etrVsslCo>574</etrVsslCo><etrGrtg>1</etrGrtg><satVsslCo>2</satVsslCo><satGrtg>3</satGrtg></detail></details></item></items></body></response>'
    r = parse(x)
    assert len(r) == 2 and r[0]["kind"] == "외국선" and r[0]["etr_cnt"] == 447 and r[1]["port"] == "인천", r
    assert list(months("202511", "202602")) == ["202511", "202512", "202601", "202602"]
    print("selftest 2/2 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

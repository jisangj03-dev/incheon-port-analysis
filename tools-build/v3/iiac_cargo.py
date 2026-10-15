"""인천공항 항공사별 노선별 운송실적(공공데이터포털 15062056 · 파일데이터 CSV · 로그인 없이) → data/derived/air_cargo.json.
나라마다 도착·출발 항공화물 톤(직화물 + 환적화물 + 우편물 · 여객기+화물기). 반기 갱신 — 「○○년 ○월까지」를 같이 낸다.
내려받기 주소는 데이터 상세 화면에서 읽는다(파일 번호가 갱신 때 바뀐다). 덜 오면 지난 파일을 지킨다.
  python tools-build/v3/iiac_cargo.py [--csv 경로] [--selftest]
"""
import csv, datetime, io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, get, say

PAGE = "https://www.data.go.kr/data/15062056/fileData.do"
OUT = os.path.join(ROOT, "data/derived/air_cargo.json")
KG = ("직화물(kg)", "환적화물(kg)", "우편물(kg)")


def num(s):
    try: return float(str(s).replace(",", "").strip() or 0)
    except ValueError: return 0.0


def download(last=None):
    """데이터 상세 화면에서 내려받기 주소(파일 번호)를 읽어 받는다. 화면이 안 열리면 지난번에 쓴 파일 번호로 바로 받는다
    (2026-10-15 data-v3: 화면이 Actions 에서 연달아 timed out — 파일 주소는 갱신 때만 바뀐다)."""
    st, h = get(PAGE, tries=4, timeout=60)
    m = re.search(r"fileDownload\.do\?atchFileId=(FILE_\d+)&(?:amp;)?fileDetailSn=(\d+)", h or "")
    ref = {"atchFileId": m.group(1), "fileDetailSn": m.group(2)} if m else (last or None)
    if not ref: say("내려받기 주소를 못 찾았다", st); return None, None, None
    if not m: say("화면이 안 열려 지난 파일 번호로 받는다", st, ref["atchFileId"])
    url = f"https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId={ref['atchFileId']}&fileDetailSn={ref['fileDetailSn']}&insertDataPrcus=N"
    st, b = get(url, tries=4, timeout=120, binary=True)
    say("받음", st, len(b or b""), ref["atchFileId"])
    upd = re.search(r"수정일\s*</?[^>]*>?\s*(\d{4}-\d{2}-\d{2})", h or "") or re.search(r"수정일[^0-9]{0,40}(\d{4}-\d{2}-\d{2})", re.sub(r"<[^>]+>", " ", h or ""))
    return (b.decode("utf-8-sig", "replace") if b else None), (upd.group(1) if upd else (last or {}).get("portal_updated")), ref


def derive(text, updated=None):
    R = list(csv.DictReader(io.StringIO(text)))
    if not R or "국가" not in R[0]: return None
    by, months = {}, set()
    for r in R:
        if r.get("국제_국내", "국제") != "국제": continue
        ym = f"{re.sub(r'[^0-9]', '', r['년도'])}-{re.sub(r'[^0-9]', '', r['월']).zfill(2)}"; months.add(ym)
        t = sum(num(r.get(k)) for k in KG) / 1000  # 톤
        c = by.setdefault(r["국가"].strip(), {"in_t": 0.0, "out_t": 0.0, "freighter_t": 0.0})
        c["in_t" if r["도착_출발"].strip() == "도착" else "out_t"] += t
        if r["여객_화물"].strip() == "화물": c["freighter_t"] += t
    ti, to = sum(c["in_t"] for c in by.values()) or 1, sum(c["out_t"] for c in by.values()) or 1
    countries = {k: {"in_t": round(v["in_t"]), "out_t": round(v["out_t"]), "in_pct": round(100 * v["in_t"] / ti, 1), "out_pct": round(100 * v["out_t"] / to, 1),
                     "freighter_pct": round(100 * v["freighter_t"] / max(1, v["in_t"] + v["out_t"]), 1)} for k, v in by.items()}
    M = sorted(months)
    return {"_설명": "인천공항 국제선 항공화물(직화물+환적화물+우편물 · 여객기+화물기) 나라별 도착·출발 톤 — 인천국제공항공사 항공사별 노선별 운송실적. 반기 갱신.",
            "source": "인천국제공항공사_항공사별 노선별 운송실적(공공데이터포털 15062056 · 이용허락범위 제한 없음)", "portal_updated": updated,
            "fetched": datetime.date.today().isoformat(), "months": M, "through": M[-1], "total_in_t": round(ti), "total_out_t": round(to),
            "countries": dict(sorted(countries.items(), key=lambda kv: -(kv[1]["in_t"] + kv[1]["out_t"])))}


def main():
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if "--csv" in sys.argv:
        text, upd, ref = open(sys.argv[sys.argv.index("--csv") + 1], encoding="utf-8-sig").read(), None, None
    else:
        last = dict(old["file"], portal_updated=old.get("portal_updated")) if old.get("file") else None
        text, upd, ref = download(last)
    if not text:
        # 원천에 닿지 못했다 — 반기 갱신 자료라 잃는 것이 없다. 지난 파일을 지키고 경고만 남긴다(형식이 바뀐 것은 아래에서 빨강)
        print("::warning::인천공항 파일(15062056)에 닿지 못했다 — 지난 파일을 지킨다"); return 0
    d = derive(text, upd)
    if not d or len(d["countries"]) < 20:
        say("자료가 덜 왔다(형식이 바뀌었을 수 있다) — 지난 파일을 지킨다"); return 1
    if old.get("through", "") > d["through"]: say("새 파일이 지난 것보다 이르다 — 지킨다", d["through"], old["through"]); return 1
    if ref: d["file"] = {k: ref[k] for k in ("atchFileId", "fileDetailSn")}
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    top = list(d["countries"].items())[:5]
    say(f"{d['months'][0]}~{d['through']} · 나라 {len(d['countries'])} · 도착 {d['total_in_t']:,}톤 · 출발 {d['total_out_t']:,}톤 · 위 다섯 {[(k, v['in_pct'], v['out_pct']) for k, v in top]}")
    return 0


def selftest():
    t = "년도,월,국제_국내,국가,도착_출발,여객_화물,직화물(kg),환적화물(kg),우편물(kg)\n2026년,01월,국제,중국,도착,화물,1000,500,500\n2026년,02월,국제,미국,출발,여객,2000 ,0,0\n2026년,02월,국내,한국,도착,여객,9,9,9\n"
    d = derive(t)
    assert d["through"] == "2026-02" and d["countries"]["중국"]["in_t"] == 2 and d["countries"]["미국"]["out_pct"] == 100.0 and "한국" not in d["countries"], d
    print("selftest 1/1 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

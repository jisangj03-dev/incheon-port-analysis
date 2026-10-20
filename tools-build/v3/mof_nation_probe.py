"""해양수산부 국가별·수출입 컨테이너처리실적(공공데이터포털 15057250 · 15059131) 탐색 — 인천항을 나라별로 가른 실측이 있는가(2026-10-20 · 품질기준 Q3).

홈 흐름 지도의 나라별 양이 「관문 교역액 × 전국 나라 몫(가정)」이라 4차 화면 판정이 Q3 미달로 잡았다.
인천항 나라별 TEU 가 있으면 바다 흐름을 실측으로 바꾼다. 여기서는 명세와 응답 머리만 남긴다(키 값은 남기지 않는다).

  python tools-build/v3/mof_nation_probe.py     # 결과 data/collected/v3/mof_nation_probe.json
"""
import datetime, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import KEY, get, write, say, scrub
from collect import parse
from kr_apis import spec

IDS = {"15057250": "국가별컨테이너처리실적", "15059131": "수출입컨테이너처리실적"}


def main():
    ym = (datetime.date.today().replace(day=1) - datetime.timedelta(days=40)).strftime("%Y%m")
    out = {"checked": datetime.date.today().isoformat(), "ym": ym, "sets": {}}
    for did, nm in IDS.items():
        sp = spec(did)
        rec = {"name": nm, "spec": sp, "calls": []}
        eps = [e for e in sp["endpoints"] if "1192000" in e] or sp["endpoints"]
        for ep in eps[:4]:
            for extra in ({"sym": ym, "eym": ym}, {"sym": ym, "eym": ym, "prtAgCd": "030"}, {"sym": ym, "eym": ym, "prtAgNm": "인천"}):
                p = {"serviceKey": KEY, "numOfRows": "50", "pageNo": "1", "type": "json", "_type": "json", **extra}
                st, b = get(ep, p, timeout=40, tries=2)
                b = scrub(b)
                rc, msg, rows = parse(b)
                rec["calls"].append({"url": ep, "params": extra, "status": st, "resultCode": rc, "resultMsg": (msg or "")[:120], "rows": len(rows), "keys": sorted(rows[0].keys()) if rows else [], "sample": rows[:6], "body_head": (b or "")[:400]})
                say(nm, ep.rsplit("/", 2)[-2:], extra, st, rc, len(rows))
        out["sets"][did] = rec
    write("data/collected/v3/mof_nation_probe.json", out)


if __name__ == "__main__":
    main()

"""IMF PortWatch — 인천·부산·평택 일별 입항(선종별)·추정 수출입량 + 초크포인트 일별 통항(2026-10-14 · 인천항 일일 맥박 · 초크포인트 충격).
서비스 주소는 ArcGIS 검색으로 찾는다(이름 Daily_Ports_Data · Daily_Chokepoints_Data). 필드 이름은 층 메타데이터에서 읽는다(추정하지 않는다).
결과: data/collected/v3/portwatch_ports.json · portwatch_chokepoints.json · portwatch_quality.json(선커밋 기준: 2025-01 이후 인천 일별 입항 0·빈 날 10% 초과면 「품질 부족」).
  python tools-build/v3/portwatch.py
"""
import datetime, json, os, sys, time
from common import ROOT, jget, write, say

PORTS = ["Incheon", "Busan", "Pyeongtaek"]


def find_service(name):
    tried = []
    for url, params in [
        ("https://www.arcgis.com/sharing/rest/search", {"q": f'title:"{name}" AND owner:*', "f": "json", "num": 20}),
        ("https://www.arcgis.com/sharing/rest/search", {"q": name, "f": "json", "num": 20}),
        ("https://portwatch-imf-dataviz.hub.arcgis.com/api/search/v1/collections/all/items", {"q": name, "limit": 20}),
    ]:
        st, d = jget(url, params)
        tried.append({"url": url, "status": st})
        if not d: continue
        items = d.get("results") or d.get("features") or []
        tried[-1]["titles"] = [((it.get("properties") or it).get("title") or (it.get("properties") or it).get("name"), (it.get("properties") or it).get("url")) for it in items[:10]]
        for it in items:
            props = it.get("properties") or it
            u = props.get("url") or ""
            t = props.get("title") or props.get("name") or ""
            if "FeatureServer" in u and name.lower() in (t + u).lower():
                return u.split("/FeatureServer")[0] + "/FeatureServer", tried
    # 보조 후보 — 공개 튜토리얼들이 쓰는 주소(검색이 비면 직접 메타데이터를 물어 맞는지 본다)
    for svc in [f"https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/{name}/FeatureServer"]:
        st, d = jget(svc, {"f": "json"})
        tried.append({"url": svc, "status": st, "ok": bool(d and (d.get("layers") or d.get("tables")))})
        if d and (d.get("layers") or d.get("tables")): return svc, tried
    return None, tried


def layer_fields(svc):
    for lid in (0, 1):
        st, d = jget(f"{svc}/{lid}", {"f": "json"})
        if d and d.get("fields"): return lid, [f["name"] for f in d["fields"]]
    return None, []


def query_all(svc, lid, where, fields="*", order=None, page=1000):
    """쪽 넘기기 — 쪽마다 세 번까지 다시 묻는다. 실패하면 None(부분 결과로 덮어쓰지 않게 · 2026-10-14 #8: 부산 0행 · 인천 1000행에서 끊김)."""
    rows, off = [], 0
    while True:
        p = {"where": where, "outFields": fields, "f": "json", "resultOffset": off, "resultRecordCount": page, "returnGeometry": "false"}
        if order: p["orderByFields"] = order
        d = None
        for k in range(3):
            st, d = jget(f"{svc}/{lid}/query", p, timeout=120)
            if d and "features" in d: break
            say("질의 실패 — 다시", k + 1, st, str(d)[:160]); time.sleep(10 * (k + 1)); d = None
        if d is None: return None
        feats = [f["attributes"] for f in d["features"]]
        rows += feats
        if not feats or (not d.get("exceededTransferLimit") and len(feats) < page): break
        off += len(feats)
    return rows


def day(v):
    if isinstance(v, (int, float)) and v > 1e11: return datetime.datetime.utcfromtimestamp(v / 1000).date().isoformat()
    return str(v)[:10]


def merge_ports(by, old_ports, datef):
    """새로 받은 항만은 그대로, 못 받은(빈) 항만은 지난 파일의 행을 쓴다. 반환 = (항만별 행, {지킨 항만: 그 마지막 날}, 지난 마지막 날, 새로 받은 것의 마지막 날)."""
    prev_last = max((v[-1][datef] for v in old_ports.values() if v), default=None)
    fresh = {p: v for p, v in by.items() if v}
    new_last = min((v[-1][datef] for v in fresh.values()), default=None)
    carried = {p: old_ports[p][-1][datef] for p in by if not by[p] and old_ports.get(p)}
    return {p: (by[p] or old_ports.get(p, [])) for p in by}, carried, prev_last, new_last


def selftest():
    o = {"Incheon": [{"date": "2026-10-09"}], "Busan": [{"date": "2026-10-09"}], "Pyeongtaek": [{"date": "2026-10-09"}]}
    n = {"Incheon": [{"date": "2026-10-12"}], "Busan": [{"date": "2026-10-12"}], "Pyeongtaek": []}
    by, carried, pl, nl = merge_ports(n, o, "date")
    assert by["Pyeongtaek"] == o["Pyeongtaek"] and carried == {"Pyeongtaek": "2026-10-09"} and nl == "2026-10-12" and pl == "2026-10-09", (by, carried)
    by, carried, _, _ = merge_ports({"Incheon": [], "Busan": [{"date": "2026-10-12"}]}, o, "date")
    assert carried == {"Incheon": "2026-10-09"}  # 인천을 못 받으면 main 이 쓰지 않는다
    print("selftest 2/2 ok"); return 0


def main():
    rc = 0
    out = {"fetched": datetime.date.today().isoformat(), "source": "IMF PortWatch(portwatch.imf.org)"}
    svc, tried = find_service("Daily_Ports_Data")
    out["service"], out["search"] = svc, tried
    if not svc:
        write("data/collected/v3/portwatch_ports.json", {**out, "error": "서비스를 못 찾았다"}); return 1
    lid, fields = layer_fields(svc)
    out["layer"], out["fields"] = lid, fields
    say("PortWatch 층", lid, "필드", len(fields))
    namef = next((f for f in fields if f.lower() in ("portname", "port_name", "name")), None)
    datef = next((f for f in fields if f.lower() in ("date", "day")), None)
    keep = [f for f in fields if f.lower().startswith(("portcalls", "import", "export")) or f in (namef, datef, "portid", "country", "ISO3")]
    # 항만마다 따로 · 2024년 이후만(2026-10-14 실측: 2019년부터 셋을 한꺼번에 물으면 6000행에서 쪽 넘기기가 끊겨 최근이 비었다)
    yf = next((f for f in fields if f.lower() == "year"), None)
    by = {}
    for p in PORTS if namef else []:
        w = f"{namef}='{p}'" + (f" AND {yf} >= 2024" if yf else "")
        rows = query_all(svc, lid, w, ",".join(keep), f"{datef} ASC") or []
        by[p] = [{k: (day(v) if k == datef else v) for k, v in r.items() if k != namef} for r in rows]
        say(p, len(rows), "행", by[p][0][datef] if by[p] else "", "~", by[p][-1][datef] if by[p] else "")
    out["ports"] = by
    out["counts"] = {k: len(v) for k, v in by.items()}
    # 덮어쓰기 전 검사 — 인천이 비었거나 새로 받은 항만의 마지막 날이 지난 파일보다 이르면 지난 파일을 지킨다.
    # [2026-10-15 · 실행 15~17] 평택 질의만 원천에서 400(Invalid query parameters)이 이어졌고, 평택 하나 때문에 인천·부산 새 자료까지 버려
    # 「일일 맥박」이 멈췄다 → 못 받은 항만만 지난 행을 지키고 `carried` 에 그 항만의 마지막 날을 적는다(지면이 「○까지」로 밝힌다).
    old = os.path.join(ROOT, "data/collected/v3/portwatch_ports.json")
    prev = json.load(open(old, encoding="utf-8")) if os.path.exists(old) else {}
    by, carried, prev_last, new_last = merge_ports(by, prev.get("ports", {}), datef)
    out["ports"], out["counts"], out["carried"] = by, {k: len(v) for k, v in by.items()}, carried
    if not by.get("Incheon") or "Incheon" in carried:
        # 원천 장애(2026-10-15: 세 항만 모두 400) — 지난 파일을 지키고 경고만. 지면은 「○ 기준」으로 날짜를 이미 밝힌다(가짜 실시간 아님)
        say("인천 자료를 못 받았다 — 지난 파일을 지킨다", out["counts"], "지난", prev_last)
        print(f"::warning::PortWatch 인천 질의 실패(원천 장애로 보임) — 지난 파일({prev_last}까지)을 지킨다")
    elif prev_last and new_last and new_last < prev_last:
        say("새로 받은 자료가 지난 파일보다 이르다 — 지난 파일을 지킨다", out["counts"], "새 마지막", new_last, "지난", prev_last); rc = 1  # 거꾸로 간 자료는 빨강
    else:
        write("data/collected/v3/portwatch_ports.json", out)
        if carried: print(f"::warning::PortWatch {', '.join(carried)} 질의 실패 — 그 항만은 지난 자료를 지켰다 {carried}")
    # 품질(선커밋 §3): 2025-01 이후 인천 일별 입항이 0 이거나 빈 날의 비율
    inc = [r for r in by.get("Incheon", []) if str(r.get(datef, "")) >= "2025-01-01"]
    callf = next((f for f in fields if f.lower() == "portcalls"), None)
    if inc and callf:
        first, last = datetime.date.fromisoformat(inc[0][datef]), datetime.date.fromisoformat(inc[-1][datef])
        span = (last - first).days + 1
        have = {r[datef]: r.get(callf) for r in inc}
        bad = sum(1 for i in range(span) if not have.get((first + datetime.timedelta(i)).isoformat()))
        q = {"from": first.isoformat(), "to": last.isoformat(), "days": span, "zero_or_missing": bad, "pct": round(100 * bad / span, 1), "rule": "10% 초과면 품질 부족 → 해양수산부 월 통계로 대체"}
        q["verdict"] = "품질 부족" if q["pct"] > 10 else "사용"
    else:
        q = {"verdict": "자료 없음", "rows": len(inc)}
    if rc == 0: write("data/collected/v3/portwatch_quality.json", q)
    say("인천 품질", json.dumps(q, ensure_ascii=False))
    # 초크포인트
    svc2, tried2 = find_service("Daily_Chokepoints_Data")
    ck = {"fetched": out["fetched"], "service": svc2, "search": tried2}
    if svc2:
        lid2, f2 = layer_fields(svc2)
        ck["fields"] = f2
        df = next((f for f in f2 if f.lower() in ("date", "day")), None)
        nf = next((f for f in f2 if f.lower() in ("portname", "name", "chokepoint")), None)
        kf = [f for f in f2 if f.lower().startswith(("n_", "capacity")) or f in (df, nf)]
        rows2 = query_all(svc2, lid2, f"{df} >= DATE '2023-01-01'" if df else "1=1", ",".join(kf) or "*", f"{df} ASC" if df else None)
        if rows2 is None: say("초크포인트 질의 실패 — 지난 파일을 지킨다"); return 1
        if len({r.get(nf) for r in rows2}) < 20: say("초크포인트 이름이 20 곳 미만 — 지난 파일을 지킨다"); return 1
        by2 = {}
        for r in rows2: by2.setdefault(r.get(nf), []).append({k: (day(v) if k == df else v) for k, v in r.items() if k not in (nf, "ObjectId", "OBJECTID")})
        ck["chokepoints"] = by2
        ck["counts"] = {k: len(v) for k, v in by2.items()}
    write("data/collected/v3/portwatch_chokepoints.json", ck)
    return rc


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

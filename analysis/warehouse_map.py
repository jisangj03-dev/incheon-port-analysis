# -*- coding: utf-8 -*-
"""인천 물류창고 분포 — 좌표가 있으면 점 지도, 없으면 행정구역 집계(표 또는 경계 지도).

무엇을 그리나 — 데이터가 허락하는 만큼만
--------------------------------------
단계는 캐시(`analysis/geocode_cache.csv`) 상태가 정한다. 사람이 고르지 않는다.

  1. **점 지도** — 상태 `OK`(좌표 있음) 행이 하나라도 있으면. folium(Leaflet) HTML 한 장.
     팝업에는 **구·동과 창고 구분만** 넣는다. 상호·원주소는 안 넣는다(지도가 주소록이 되지 않게).
  2. **구·동 집계** — 좌표가 없고 정제(`REFINED`)만 된 행으로. 건물식별의 `admCd`(법정동코드 10자리)
     앞 5자리 = 시군구, 앞 8자리 = 읍면동. 이름은 정제된 지번주소에서 읽는다.
     · 경계 파일을 `--boundary` 로 주고 **이용허락 문구를 `--boundary-license` 로 같이 주면** 단계구분도.
     · 그렇지 않으면 **표로 대신한다**(CSV + 마크다운). 경계 파일은 출처·이용허락을 확인하지 못하면 안 쓴다.
  3. 둘 다 없으면 **분모 0** 이라고 말하고 아무것도 안 쓴다 — 빈 지도는 통과가 아니다.

도구와 이용허락 (2026-09-30 설치본에서 LICENSE 파일을 열어 확인)
------------------------------------------------------------
· folium 0.20.0 — MIT (`folium-0.20.0.dist-info/licenses/LICENSE.txt`)
· geopandas 1.2.0 — BSD-3-Clause (`geopandas-1.2.0.dist-info/licenses/LICENSE.txt`) — 경계 지도에서만 쓴다.
· Leaflet 1.9.3 — BSD-2-Clause. folium 이 jsDelivr CDN 에서 부른다(HTML 에 번들하지 않는다).
· 바탕 타일 — OpenStreetMap(ODbL). folium 기본값이 저작자 표시를 지도 우하단에 넣는다.

  python analysis/warehouse_map.py --in analysis/incheon_warehouses.csv --col 소재지
  python analysis/warehouse_map.py --in ... --col 소재지 --boundary <경계.geojson> --code-field <코드열> \\
         --boundary-license "<출처 · 이용허락 문구>"
  python analysis/warehouse_map.py --selftest

산출(`analysis/`) — 집계만. 원주소·상호는 어느 산출에도 안 들어간다.
  warehouse_by_gu.csv · warehouse_by_dong.csv · warehouse_by_area.md   (집계 단계)
  warehouse_points.html                                                  (점 단계)
  warehouse_choropleth.html                                              (경계 파일이 있을 때)
"""

import argparse
import csv
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geocode  # noqa: E402  캐시 형식·경계 판정을 한 곳에서만 정의한다

OUT_GU = os.path.join(HERE, "warehouse_by_gu.csv")
OUT_DONG = os.path.join(HERE, "warehouse_by_dong.csv")
OUT_MD = os.path.join(HERE, "warehouse_by_area.md")
OUT_POINTS = os.path.join(HERE, "warehouse_points.html")
OUT_CHORO = os.path.join(HERE, "warehouse_choropleth.html")
CENTER = (37.456, 126.705)  # 인천시청 부근 — 지도 초기 화면만 정한다


def area_of(row):
    """캐시 한 행 → (구코드, 구이름, 동코드, 동이름). admCd 가 없으면 None."""
    bld = geocode.bld_unpack(row.get("건물식별"))
    adm = (bld or {}).get("admCd", "")
    if len(adm) != 10 or not adm.isdigit():
        return None
    parts = (row.get("지번주소") or row.get("정제주소") or "").split()
    # 「인천광역시 중구 항동7가 …」 · 군 지역은 「인천광역시 강화군 강화읍 …」 — 둘째·셋째 토큰
    gu = parts[1] if len(parts) > 1 else ""
    dong = parts[2] if len(parts) > 2 else ""
    return adm[:5], gu, adm[:8], dong


def _name_by_code(counter):
    """한 코드에 이름이 여럿이면(옛 구 이름·새 구 이름) 가장 많이 나온 것을 쓴다."""
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if counter else ""


def aggregate(rows, facts=None):
    """→ (구 집계, 동 집계, 코드 없는 행 수).
    rows = 캐시 행(고유 원주소당 1). facts = {원주소: [{구분, 면적, 냉동냉장면적}, …]} — 주면 **창고 한 곳당 1개소**로 세고
    면적 합·구분별 개소를 얹는다(한 주소에 창고가 여럿이면 여럿). 안 주면 고유 주소당 1개소."""
    from collections import Counter
    gu, dong, nocode = {}, {}, 0
    for r in rows:
        a = area_of(r)
        ents = (facts or {}).get(r.get("원주소"), [None]) or [None]
        if not a:
            nocode += len(ents)
            continue
        gc, gn, dc, dn = a
        g = gu.setdefault(gc, {"코드": gc, "이름": "", "개소": 0, "면적합": 0.0, "냉동냉장면적": 0.0,
                               "구분별": Counter(), "_n": Counter()})
        d = dong.setdefault(dc, {"코드": dc, "구": "", "이름": "", "개소": 0, "면적합": 0.0, "_n": Counter(), "_g": Counter()})
        g["_n"][gn] += len(ents)
        d["_n"][dn] += len(ents)
        d["_g"][gn] += len(ents)
        for e in ents:
            g["개소"] += 1
            d["개소"] += 1
            if e:
                g["면적합"] += e.get("면적", 0.0)
                g["냉동냉장면적"] += e.get("냉동냉장면적", 0.0)
                d["면적합"] += e.get("면적", 0.0)
                g["구분별"][e.get("구분") or "미상"] += 1
    for g in gu.values():
        g["이름"] = _name_by_code(g.pop("_n"))
    for d in dong.values():
        d["이름"] = _name_by_code(d.pop("_n"))
        d["구"] = _name_by_code(d.pop("_g"))
    key = lambda x: (-x["개소"], x["코드"])
    return sorted(gu.values(), key=key), sorted(dong.values(), key=key), nocode


def write_tables(gu, dong, nocode, n, note, out_gu=OUT_GU, out_dong=OUT_DONG, out_md=OUT_MD):
    kinds = sorted({k for g in gu for k in g["구분별"]})
    has_area = any(g["면적합"] for g in gu)
    gu_fields = ["코드", "이름", "개소"] + (["면적합_m2", "냉동냉장면적_m2"] if has_area else []) + ["개소·" + k for k in kinds]
    dong_fields = ["코드", "구", "이름", "개소"] + (["면적합_m2"] if has_area else [])

    def gu_row(g):
        r = {"코드": g["코드"], "이름": g["이름"], "개소": g["개소"]}
        if has_area:
            r["면적합_m2"] = round(g["면적합"])
            r["냉동냉장면적_m2"] = round(g["냉동냉장면적"])
        for k in kinds:
            r["개소·" + k] = g["구분별"].get(k, 0)
        return r

    def dong_row(d):
        r = {"코드": d["코드"], "구": d["구"], "이름": d["이름"], "개소": d["개소"]}
        if has_area:
            r["면적합_m2"] = round(d["면적합"])
        return r
    for path, fields, rows in ((out_gu, gu_fields, [gu_row(g) for g in gu]),
                               (out_dong, dong_fields, [dong_row(d) for d in dong])):
        with io.open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    total = sum(g["개소"] for g in gu)
    lines = ["# 인천 물류창고 — 구·군별 개소(정제 주소의 법정동코드 기준)", "",
             "> %s" % note, "",
             "고유 주소 %d · 코드로 집계 %d개소 · 코드 없음 %d" % (n, total, nocode), ""]
    head = "| 구·군 | 법정동코드(5) | 개소 | 비중 |" + (" 면적 합(m²) | 냉동냉장(m²) |" if has_area else "")
    lines += [head, "|---|---|---:|---:|" + ("---:|---:|" if has_area else "")]
    for g in gu:
        row = "| %s | %s | %d | %.1f%% |" % (g["이름"], g["코드"], g["개소"], 100.0 * g["개소"] / total if total else 0)
        if has_area:
            row += " %s | %s |" % (format(round(g["면적합"]), ","), format(round(g["냉동냉장면적"]), ","))
        lines.append(row)
    if kinds:
        lines += ["", "관련법률(구분)별 개소: " + " · ".join(
            "%s %d" % (k, sum(g["구분별"].get(k, 0) for g in gu)) for k in kinds)]
    lines += ["", "읍·면·동 상위 15 (전체는 `warehouse_by_dong.csv`)", "",
              "| 구·군 | 읍·면·동 | 개소 |", "|---|---|---:|"]
    lines += ["| %s | %s | %d |" % (d["구"], d["이름"], d["개소"]) for d in dong[:15]]
    with io.open(out_md, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def point_map(ok_rows, kinds, out=OUT_POINTS):
    import folium  # 점 단계에서만 필요하다
    m = folium.Map(location=CENTER, zoom_start=10, tiles="OpenStreetMap")
    for r in ok_rows:
        a = area_of(r)
        label = " ".join(x for x in ((a[1], a[3]) if a else ()) if x) or "인천"
        kind = kinds.get(r["원주소"], "")
        folium.CircleMarker(location=(float(r["위도"]), float(r["경도"])), radius=4, weight=1,
                            fill=True, fill_opacity=0.7,
                            popup=folium.Popup("%s%s" % (label, " · " + kind if kind else ""), max_width=220)
                            ).add_to(m)
    m.save(out)
    return out


def choropleth(gu, boundary, code_field, license_note, out=OUT_CHORO):
    import folium
    import geopandas as gpd
    g = gpd.read_file(boundary).to_crs(4326)
    g[code_field] = g[code_field].astype(str).str[:5]
    counts = {x["코드"]: x["개소"] for x in gu}
    g["개소"] = g[code_field].map(counts).fillna(0).astype(int)
    m = folium.Map(location=CENTER, zoom_start=10, tiles="OpenStreetMap")
    folium.Choropleth(geo_data=g.__geo_interface__, data=g, columns=[code_field, "개소"],
                      key_on="feature.properties.%s" % code_field, fill_opacity=0.7, line_weight=1,
                      legend_name="물류창고 개소").add_to(m)
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;bottom:4px;left:4px;font:11px sans-serif;background:#fff;padding:2px 4px">'
        '경계: %s</div>' % license_note))
    m.save(out)
    return out


def load(inp, col):
    if not os.path.exists(inp):
        raise SystemExit("%s 가 없다 — 창고 목록 수집 전이다(collect_warehouses.py --src). **분모 0.**" % inp)
    addrs = geocode.read_input(inp, col)
    cache = geocode.read_cache()
    kinds, facts = {}, {}

    def num(v):
        try:
            return float(str(v).replace(",", "") or 0)
        except ValueError:
            return 0.0
    with io.open(inp, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            k = geocode.norm_key(r.get(col, ""))
            kinds.setdefault(k, (r.get("구분") or "").strip())
            facts.setdefault(k, []).append({"구분": (r.get("구분") or "").strip(), "면적": num(r.get("면적")),
                                          "냉동냉장면적": num(r.get("냉동냉장면적"))})
    return addrs, cache, kinds, facts


def run(addrs, cache, kinds, boundary=None, code_field=None, license_note=None, outs=None, facts=None):
    """→ (단계, 쓴 파일들). outs 는 시험용 산출 경로 덮어쓰기."""
    outs = outs or {}
    rows = [cache[a] for a in addrs if a in cache]
    ok = [r for r in rows if r["상태"] == "OK"]
    refined = [r for r in rows if r.get("건물식별")]
    if not addrs or not refined:
        print("분모 %d · 정제 %d — **그릴 것이 없다. 빈 지도는 통과가 아니다.**" % (len(addrs), len(refined)))
        return "없음", []
    wrote = []
    if ok:
        wrote.append(point_map(ok, kinds, outs.get("points", OUT_POINTS)))
    gu, dong, nocode = aggregate(refined, facts)
    note = ("좌표 %d건 — 점 지도는 `warehouse_points.html`." % len(ok)) if ok else \
        "좌표가 아직 없다(좌표제공 키 대기). 정제 결과의 행정구역 코드로만 셌다."
    write_tables(gu, dong, nocode, len(addrs), note,
                 outs.get("gu", OUT_GU), outs.get("dong", OUT_DONG), outs.get("md", OUT_MD))
    wrote += [outs.get("gu", OUT_GU), outs.get("dong", OUT_DONG), outs.get("md", OUT_MD)]
    if boundary:
        if not (code_field and license_note):
            print("경계 파일은 --code-field 와 --boundary-license 가 같이 있어야 쓴다 — **표로 대신했다.**")
        else:
            wrote.append(choropleth(gu, boundary, code_field, license_note, outs.get("choro", OUT_CHORO)))
    stage = "점" if ok else "집계"
    print("단계: %s · 고유 주소 %d · 좌표 %d · 정제 %d · 구 %d · 동 %d · 코드 없음 %d"
          % (stage, len(addrs), len(ok), len(refined), len(gu), len(dong), nocode))
    return stage, wrote


def selftest():
    import tempfile
    ok_all = True

    def chk(label, got, want):
        nonlocal ok_all
        good = got == want
        ok_all = ok_all and good
        print("  %s %-44s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    def row(addr, adm, jibun, st="REFINED", lat="", lon=""):
        return {"원주소": addr, "지번주소": jibun, "정제주소": "", "상태": st, "위도": lat, "경도": lon,
                "건물식별": "%s|281103000001|0|1|0" % adm if adm else ""}

    cache = {r["원주소"]: r for r in [
        row("가", "2811012500", "인천광역시 중구 항동7가 1"),
        row("나", "2811012500", "인천광역시 중구 항동7가 2"),
        row("다", "2826010100", "인천광역시 서구 오류동 3"),
        row("라", "", ""),
        row("마", "2871025000", "인천광역시 강화군 강화읍 관청리 5"),
    ]}
    addrs = ["가", "나", "다", "라", "마", "바"]
    gu, dong, nocode = aggregate([cache[a] for a in addrs if a in cache])
    chk("구 집계(개소 내림차순)", [(g["이름"], g["개소"]) for g in gu], [("중구", 2), ("서구", 1), ("강화군", 1)])
    chk("동 코드 8자리", dong[0]["코드"], "28110125")
    chk("군 지역 읍 이름", [d["이름"] for d in dong if d["구"] == "강화군"], ["강화읍"])
    chk("코드 없는 행은 따로 센다", nocode, 1)
    # 창고 단위 집계 — 한 주소에 창고 둘, 구 이름이 섞여 있어도 코드로 묶고 다수 이름을 쓴다
    cache2 = dict(cache)
    cache2["사"] = row("사", "2811012500", "인천광역시 제물포구 항동7가 9")
    facts = {"가": [{"구분": "물류시설법", "면적": 100.0, "냉동냉장면적": 10.0}, {"구분": "관세법", "면적": 50.0, "냉동냉장면적": 0.0}],
             "사": [{"구분": "물류시설법", "면적": 25.0, "냉동냉장면적": 0.0}]}
    gu2, dong2, nc2 = aggregate([cache2[a] for a in ("가", "나", "사")], facts)
    chk("창고 단위 개소(한 주소 둘)", gu2[0]["개소"], 4)
    chk("면적 합·냉동냉장 합", (gu2[0]["면적합"], gu2[0]["냉동냉장면적"]), (175.0, 10.0))
    chk("구분별 개소", dict(gu2[0]["구분별"]), {"물류시설법": 2, "관세법": 1})
    chk("이름 섞이면 다수 이름", gu2[0]["이름"], "중구")
    d = tempfile.mkdtemp()
    outs = {k: os.path.join(d, k) for k in ("gu", "dong", "md", "points", "choro")}
    stage, wrote = run(addrs, cache, {}, outs=outs)
    chk("좌표 없으면 집계 단계", stage, "집계")
    chk("집계 단계는 HTML 을 안 쓴다", os.path.exists(outs["points"]), False)
    body = open(outs["gu"], encoding="utf-8").read() + open(outs["md"], encoding="utf-8").read()
    chk("산출에 원주소 번지 없음", "항동7가 1" in body, False)
    stage, wrote = run(addrs, cache, {}, boundary="x.geojson", outs=outs)
    chk("이용허락 없는 경계 파일은 안 쓴다", os.path.exists(outs["choro"]), False)
    chk("분모 0 이면 아무것도 안 쓴다", run([], {}, {}, outs=outs), ("없음", []))
    try:
        import folium  # noqa: F401
    except ImportError:
        print("  **모름** folium 이 없다 — 점 지도 시험을 못 쳤다(pip install folium). 통과로 세지 않는다.")
        return 2
    cache["가"].update(상태="OK", 위도="37.4700000", 경도="126.6000000")
    stage, wrote = run(addrs, cache, {"가": "보세창고"}, outs=outs)
    html = open(outs["points"], encoding="utf-8").read()
    chk("좌표 있으면 점 단계", stage, "점")
    chk("점 지도 팝업에 구·동·구분", "중구 항동7가 · 보세창고" in html, True)
    chk("점 지도에 원주소 없음", "항동7가 1" in html, False)
    chk("OSM 저작자 표시", "openstreetmap" in html.lower(), True)
    print("\n인수시험 %s" % ("통과" if ok_all else "**실패**"))
    return 0 if ok_all else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", help="창고 목록 CSV (collect_warehouses.py 산출)")
    ap.add_argument("--col", default="소재지")
    ap.add_argument("--boundary", help="행정경계 파일(GeoJSON·SHP) — 출처·이용허락을 확인한 것만")
    ap.add_argument("--code-field", help="경계 파일의 시군구 코드 열(법정동코드 앞 5자리와 맞는 것)")
    ap.add_argument("--boundary-license", help="경계 파일의 출처·이용허락 문구(지도에 그대로 찍힌다)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.inp:
        ap.error("--in 이 필요하다")
    addrs, cache, kinds, facts = load(a.inp, a.col)
    stage, wrote = run(addrs, cache, kinds, a.boundary, a.code_field, a.boundary_license, facts=facts)
    for w in wrote:
        print("→ %s" % os.path.relpath(w))
    return 0 if wrote else 1


if __name__ == "__main__":
    sys.exit(main())

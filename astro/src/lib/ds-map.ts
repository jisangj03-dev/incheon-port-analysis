// 시안 ③ 지도 — 해도 색으로 다시 칠한 내장 PMTiles 바탕 + 장소 넷(크기 = 마지막 달 처리량). 셰입맵처럼 덜어 낸다:
// 길·건물·라벨 층은 빼고, 땅·물·해안선만. 글리프 서버가 없어 이름은 HTML 표지로 단다(외부 요청 0).
type Place = { id: string; label: string; kind: string; lon: number; lat: number; approx?: boolean; v: number | null };
const $ = (id: string) => document.getElementById(id)!;

const C = { paper: "#f5f2eb", water: "#e3ded2", coast: "#b9b1a1", ink: "#191714", signal: "#b3361e", sea: "#5d7a86" };

export async function initDsMap() {
  const cfg = (window as any).__mapcfg;
  const P = JSON.parse($("ds-map-data").textContent || "[]") as Place[];
  const css = document.createElement("link"); css.rel = "stylesheet"; css.href = cfg.css; document.head.append(css);
  const [ml, pm, bm] = await Promise.all([import(/* @vite-ignore */ cfg.ml), import("pmtiles"), import("@protomaps/basemaps")]);
  ml.setWorkerUrl(new URL(cfg.worker, location.href).href);
  const tilesUrl = new URL(cfg.tiles, location.href).href;
  const has = await fetch(tilesUrl, { method: "HEAD" }).then((r) => r.ok, () => false);
  const style: any = { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": C.paper } }] };
  if (has) {
    const proto = new pm.Protocol(); ml.addProtocol("pmtiles", proto.tile);
    style.sources.protomaps = { type: "vector", url: `pmtiles://${tilesUrl}`, attribution: "© OpenStreetMap · Protomaps" };
    const keep = (l: any) => l.type === "background" || /^(earth|water|landcover|landuse_(park|urban))/.test(l.id);
    style.layers = bm.layers("protomaps", bm.namedFlavor("light"), { lang: "ko" }).filter(keep).map((l: any) => {
      if (l.type === "background") return { ...l, paint: { "background-color": C.paper } };
      if (/^water/.test(l.id)) return l.type === "fill" ? { ...l, paint: { "fill-color": C.water } } : { ...l, paint: { ...l.paint, "line-color": C.water } };
      if (/^earth/.test(l.id)) return { ...l, paint: { "fill-color": C.paper } };
      return l.type === "fill" ? { ...l, paint: { "fill-color": C.paper, "fill-opacity": 0 } } : l;
    });
    // 해안선 한 줄 — 물 면의 테두리
    style.layers.push({ id: "coast", type: "line", source: "protomaps", "source-layer": "water", paint: { "line-color": C.coast, "line-width": 0.6 } });
  }
  const map = new ml.Map({
    container: "ds-map", style, center: [126.56, 37.43], zoom: 9.7, attributionControl: { compact: true },
    maxBounds: [[126.2, 37.15], [127.0, 37.72]], dragRotate: false, pitchWithRotate: false,
  });
  map.scrollZoom.disable();
  // 장소 넷이 다 들어오게 — 화면 폭에 맞춰 둘레를 잡는다
  const lons = P.map((p) => p.lon), lats = P.map((p) => p.lat);
  map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: { top: 60, bottom: 60, left: 60, right: 160 }, animate: false });
  map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
  const vmax = Math.max(1, ...P.map((p) => p.v || 0));
  map.on("load", () => {
    map.addSource("places", { type: "geojson", data: { type: "FeatureCollection", features: P.map((p) => ({ type: "Feature", properties: { ...p, r: p.v ? 6 + 22 * Math.sqrt(p.v / vmax) : 6, top: p.v === vmax }, geometry: { type: "Point", coordinates: [p.lon, p.lat] } })) } });
    map.addLayer({ id: "dots", type: "circle", source: "places", paint: {
      "circle-radius": ["get", "r"], "circle-color": ["case", ["get", "top"], C.signal, C.ink], "circle-opacity": 0.85,
      "circle-stroke-color": C.paper, "circle-stroke-width": 1.5 } });
    for (const p of P) {
      const el = document.createElement("div");
      el.className = "ds-label";
      el.innerHTML = `<b>${p.id}</b>${p.v != null ? `<span>${p.v}천TEU</span>` : `<span>${p.kind === "air" ? "항공" : ""}</span>`}${p.approx ? "<em>개략 위치</em>" : ""}`;
      // 가까운 이웃이 동쪽에 있으면 이름을 왼쪽에 단다 — 겹침 방지
      const left = P.some((q) => q !== p && Math.abs(q.lat - p.lat) < 0.04 && Math.abs(q.lon - p.lon) < 0.04 && q.lon > p.lon);
      const r = (p.v ? 10 + 22 * Math.sqrt(p.v / vmax) : 12);
      if (left) el.style.textAlign = "right";
      new ml.Marker({ element: el, anchor: left ? "right" : "left", offset: [left ? -r : r, 0] }).setLngLat([p.lon, p.lat]).addTo(map);
    }
    (window as any).__dsmap = { tiles: has, places: P.length };
    $("ds-map").dataset.ready = has ? "tiles" : "no-tiles";
  });
}

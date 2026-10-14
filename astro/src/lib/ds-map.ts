// 시안 ③ 지도 — 해도 색으로 다시 칠한 내장 PMTiles 바탕 + 장소 넷(크기 = 마지막 달 처리량). 셰입맵처럼 덜어 낸다:
// 길·건물·라벨 층은 빼고, 땅·물·해안선만. 글리프 서버가 없어 이름은 HTML 표지로 단다(외부 요청 0).
type Place = { id: string; label: string; kind: string; lon: number; lat: number; approx?: boolean; v: number | null };
const $ = (id: string) => document.getElementById(id)!;

const C = { paper: "#f5f2eb", water: "#e3ded2", coast: "#b9b1a1", contour: "#cdc4b1", ink: "#191714", signal: "#b3361e", sea: "#5d7a86" };

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
    // 면·선만 남긴다 — 이름이 water·earth 로 시작해도 글자 층(symbol)은 글리프가 없어 스타일 전체를 무효로 만든다(2026-10-14 Actions 빈 지도)
    const keep = (l: any) => l.type === "background" || ((l.type === "fill" || l.type === "line") && /^(earth|water|landcover|landuse_(park|urban))/.test(l.id));
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
  // 지도 오류를 화면 밖에 남긴다 — maplibre 오류는 pageerror 로 안 잡혀 시험이 「오류 0」으로 지나갔다
  const errs: string[] = ((window as any).__dsmapErr = []);
  map.on("error", (e: any) => errs.push(String(e?.error?.message || e?.error || e)));
  // 점은 스타일만 읽히면 단다(load 는 바탕 원천까지 기다려 바탕이 실패하면 점도 같이 사라진다)
  map.once("style.load", () => {
    map.addSource("places", { type: "geojson", data: { type: "FeatureCollection", features: P.map((p) => ({ type: "Feature", properties: { ...p, r: p.v ? 6 + 22 * Math.sqrt(p.v / vmax) : 6, top: p.v === vmax }, geometry: { type: "Point", coordinates: [p.lon, p.lat] } })) } });
    map.addLayer({ id: "dots", type: "circle", source: "places", paint: {
      "circle-radius": ["get", "r"], "circle-color": ["case", ["get", "top"], C.signal, C.ink], "circle-opacity": 0.85,
      "circle-stroke-color": C.paper, "circle-stroke-width": 1.5 } });
    for (const p of P) {
      const el = document.createElement("div");
      el.className = "ds-label";
      el.innerHTML = `<b>${p.id}</b>${p.v != null ? `<i>${p.v}<small>천TEU</small></i>` : `<em>${p.kind === "air" ? "항공 · 컨테이너 아님" : ""}</em>`}${p.approx ? "<em>개략 위치</em>" : ""}`;
      // 가까운 이웃이 동쪽에 있으면 이름을 왼쪽에 단다 — 겹침 방지
      const left = P.some((q) => q !== p && Math.abs(q.lat - p.lat) < 0.04 && Math.abs(q.lon - p.lon) < 0.04 && q.lon > p.lon);
      const r = (p.v ? 10 + 22 * Math.sqrt(p.v / vmax) : 12);
      if (left) el.style.textAlign = "right";
      new ml.Marker({ element: el, anchor: left ? "right" : "left", offset: [left ? -r : r, 0] }).setLngLat([p.lon, p.lat]).addTo(map);
    }
  });
  // 등심선(라이선스 확인된 것만 지면에 박힌다) — 아주 옅은 선 + 몇 군데에만 기울임 수심 숫자
  const bathy = JSON.parse(document.getElementById("ds-bathy")?.textContent || "null");
  if (bathy) map.once("style.load", () => {
    map.addSource("bathy", { type: "geojson", data: { type: "FeatureCollection", features: bathy.features } });
    const below = map.getLayer("dots") ? "dots" : undefined;
    map.addLayer({ id: "contour", type: "line", source: "bathy", filter: ["==", ["get", "kind"], "contour"],
      paint: { "line-color": C.contour, "line-width": ["interpolate", ["linear"], ["get", "depth"], 5, 0.5, 50, 0.9], "line-opacity": 0.9 } }, below);
    // 타일이 없을 때만 등심선 0m 를 해안선으로 쓴다
    if (!has) map.addLayer({ id: "coast0", type: "line", source: "bathy", filter: ["==", ["get", "kind"], "coast"], paint: { "line-color": C.coast, "line-width": 0.7 } }, below);
    depthLabels(ml, map, bathy.features);
  });
  graticule(map);
  // 다 그린 뒤(idle) 상태를 적는다 — 시험이 이것을 기다렸다가 화면 픽셀을 잰다
  map.once("idle", () => {
    const base = has && map.isSourceLoaded("protomaps");
    (window as any).__dsmap = { tiles: has, base, places: P.length, errors: errs };
    $("ds-map").dataset.ready = base ? "tiles" : has ? "tiles-failed" : "no-tiles";
  });
}

// 등심선 수심 숫자 — 긴 선의 가운데 한 곳에만(해도처럼 드문드문) · HTML 표지(글리프 서버 없이)
function depthLabels(ml: any, map: any, feats: any[]) {
  const long = feats.filter((f) => f.properties.kind === "contour" && f.geometry.coordinates.length > 24)
    .sort((a, b) => b.geometry.coordinates.length - a.geometry.coordinates.length);
  const seen: Record<number, number> = {};
  for (const f of long) {
    const d = f.properties.depth;
    if ((seen[d] = (seen[d] || 0) + 1) > 2) continue;
    const c = f.geometry.coordinates[Math.floor(f.geometry.coordinates.length / 2)];
    const el = document.createElement("div");
    el.className = "ds-depth";
    el.textContent = String(d);
    new ml.Marker({ element: el }).setLngLat(c).addTo(map);
  }
}

// 가장자리 위경도 눈금 — 분(′) 단위 흑백 막대 + 5′ 마다 숫자(종이 해도 테두리). 움직일 때마다 다시 그린다.
function graticule(map: any) {
  const host = map.getContainer() as HTMLElement;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "ds-grat");
  host.append(svg);
  const T = 5; // 막대 두께
  const draw = () => {
    const w = host.clientWidth, h = host.clientHeight, b = map.getBounds();
    const span = b.getNorth() - b.getSouth();
    const step = span > 0.6 ? 5 : span > 0.25 ? 2 : 1; // 분
    const lab = step * 5;
    let out = `<rect x="0.5" y="0.5" width="${w - 1}" height="${h - 1}" fill="none" stroke="var(--s-ink-2)" stroke-width="1"/>`;
    const fmt = (deg: number, pos: string, neg: string) => { const a = Math.abs(deg), d = Math.floor(a + 1e-9), m = Math.round((a - d) * 60); return `${d}°${String(m).padStart(2, "0")}′${deg >= 0 ? pos : neg}`; };
    for (let m = Math.floor(b.getSouth() * 60 / step) * step; m <= b.getNorth() * 60; m += step) {
      const y0 = map.project([b.getWest(), m / 60]).y, y1 = map.project([b.getWest(), (m + step) / 60]).y;
      const dark = Math.round(m / step) % 2 === 0;
      for (const x of [0, w - T]) out += `<rect x="${x}" y="${Math.min(y0, y1)}" width="${T}" height="${Math.abs(y1 - y0)}" fill="${dark ? "var(--s-ink-2)" : "var(--s-paper)"}" stroke="var(--s-ink-2)" stroke-width="0.5"/>`;
      if (m % lab === 0 && y0 > 14 && y0 < h - 6) out += `<text x="${T + 4}" y="${y0 + 3}">${fmt(m / 60, "N", "S")}</text>`;
    }
    for (let m = Math.floor(b.getWest() * 60 / step) * step; m <= b.getEast() * 60; m += step) {
      const x0 = map.project([m / 60, b.getSouth()]).x, x1 = map.project([(m + step) / 60, b.getSouth()]).x;
      const dark = Math.round(m / step) % 2 === 0;
      for (const y of [0, h - T]) out += `<rect x="${Math.min(x0, x1)}" y="${y}" width="${Math.abs(x1 - x0)}" height="${T}" fill="${dark ? "var(--s-ink-2)" : "var(--s-paper)"}" stroke="var(--s-ink-2)" stroke-width="0.5"/>`;
      if (m % lab === 0 && x0 > 40 && x0 < w - 70) out += `<text x="${x0 + 3}" y="${h - T - 4}">${fmt(m / 60, "E", "W")}</text>`;
    }
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.innerHTML = out;
  };
  map.on("move", draw);
  map.on("resize", draw);
  draw();
}

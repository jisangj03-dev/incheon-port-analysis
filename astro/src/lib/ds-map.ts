import { placeLabels, boxesOf } from "./label-place";
// 지도 — 해도 색으로 다시 칠한 내장 PMTiles 바탕 + 장소 넷(크기 = 마지막 달 처리량). 셰입맵처럼 덜어 낸다:
// 길·건물·라벨 층은 빼고, 땅·물·해안선만. 글리프 서버가 없어 이름은 HTML 표지로 단다(외부 요청 0).
type Place = { id: string; label: string; kind: string; lon: number; lat: number; approx?: boolean; v: number | null; values?: (number | null)[] | null };
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
    // 내장 타일은 동경 126.35°부터라 그 서쪽(황해)이 종이색(=땅색)으로 보인다 — 바다색으로 칠해 둔다(그 안 작은 섬은 안 보인다 · 캡션에 적음)
    style.sources.westsea = { type: "geojson", data: { type: "Feature", properties: {}, geometry: { type: "Polygon", coordinates: [[[125.9, 37.0], [126.35, 37.0], [126.35, 37.9], [125.9, 37.9], [125.9, 37.0]]] } } };
    style.layers.splice(1, 0, { id: "westsea", type: "fill", source: "westsea", paint: { "fill-color": C.water } });
    // 해안선 한 줄 — 물 면의 테두리
    style.layers.push({ id: "coast", type: "line", source: "protomaps", "source-layer": "water", paint: { "line-color": C.coast, "line-width": 0.6 } });
  }
  const map = new ml.Map({
    container: "ds-map", style, center: [126.56, 37.43], zoom: 9.7, attributionControl: { compact: true },
    // 경계는 넉넉히 — 납작한 칸에서 신항~서울을 다 담으려면 더 멀리 물러나야 한다(좁은 경계가 맞춤을 막았다)
    maxBounds: [[125.9, 37.0], [127.4, 37.9]], dragRotate: false, pitchWithRotate: false,
  });
  map.scrollZoom.disable();
  const LB: { el: HTMLElement; lon: number; lat: number; r: () => number; pri: number }[] = [];
  const curR: Record<string, number> = {};
  const layer = document.createElement("div"); layer.className = "ds-labels"; map.getContainer().append(layer);
  const lineSvg = document.createElementNS("http://www.w3.org/2000/svg", "svg") as SVGSVGElement; lineSvg.setAttribute("class", "ds-lines"); layer.append(lineSvg);
  // 장소 넷이 다 들어오게 — 화면 폭에 맞춰 둘레를 잡는다
  const MD0 = JSON.parse(document.getElementById("ds-map-months")?.textContent || "null");
  const lons = P.map((p) => p.lon).concat(MD0 ? [MD0.to.lon] : []), lats = P.map((p) => p.lat).concat(MD0 ? [MD0.to.lat] : []);
  // 장소 넷 + 서울이 다 들어오게 — 칸 높이가 그려진 뒤 바뀌므로 처음 다 그린 때와 크기가 바뀔 때 다시 맞춘다
  const fit = () => map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: { top: 50, bottom: 50, left: 60, right: 110 }, animate: false });
  fit();
  map.once("load", () => { map.resize(); fit(); });
  map.on("resize", fit);
  map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
  const MD = JSON.parse(document.getElementById("ds-map-months")?.textContent || "null") as { months: string[]; to: { label: string; lon: number; lat: number } } | null;
  // 눈금은 전 기간 최대로 고정 — 달이 바뀔 때 원이 실제로 커지고 작아지게(숨 쉬기)
  const vmax = Math.max(1, ...P.flatMap((p) => (p.values || [p.v]).map((v) => v || 0)));
  const valAt = (p: Place, i: number) => (p.values ? p.values[i] ?? null : p.v);
  const radius = (v: number | null) => (v ? 6 + 22 * Math.sqrt(v / vmax) : 6);
  const topLast = Math.max(...P.map((p) => p.v || 0));
  // 지도 오류를 화면 밖에 남긴다 — maplibre 오류는 pageerror 로 안 잡혀 시험이 「오류 0」으로 지나갔다
  const errs: string[] = ((window as any).__dsmapErr = []);
  map.on("error", (e: any) => errs.push(String(e?.error?.message || e?.error || e)));
  // 점은 스타일만 읽히면 단다(load 는 바탕 원천까지 기다려 바탕이 실패하면 점도 같이 사라진다)
  map.once("style.load", () => {
    map.addSource("places", { type: "geojson", data: placesAt(MD ? MD.months.length - 1 : 0) });
    // [2026-10-20 · docs/품질기준.md Q3] 항만 → 서울 흐름선(개념선 — 길이 실제 경로가 아님)을 뺐다. 점 = 그 달 실제 처리량만.
    map.addLayer({ id: "dots", type: "circle", source: "places", paint: {
      "circle-radius": ["get", "r"], "circle-color": ["case", ["get", "top"], C.signal, C.ink], "circle-opacity": 0.85,
      "circle-stroke-color": C.paper, "circle-stroke-width": 1.5 } });
    for (const p of P) {
      const el = document.createElement("div");
      el.className = "ds-label";
      el.innerHTML = `<b>${p.id}</b>${p.v != null ? `<i data-v="${p.id}">${p.v}<small>천TEU</small></i>` : `<em>${p.kind === "air" ? "항공 · 컨테이너 아님" : ""}</em>`}${p.approx ? "<em>개략 위치</em>" : ""}`;
      // 자리는 배치기가 잡는다(값 큰 점 먼저 · 막히면 멀리 + 지시선 — 채팅 검수 ①: 390 에서 인천공항·남항·국제여객부두가 겹쳤다)
      LB.push({ el, lon: p.lon, lat: p.lat, r: () => curR[p.id] ?? radius(p.v), pri: p.v ?? 0.5 }); layer.append(el);
    }
    relayout();
  });
  // 이름표 덮개 층 — 지도가 움직이면 다시 놓는다(한 프레임에 한 번)
  let raf = 0;
  map.on("move", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(relayout); });
  map.on("resize", () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(relayout); });
  map.once("idle", relayout);
  (document as any).fonts?.addEventListener?.("loadingdone", () => relayout());
  function relayout() {
    const host = map.getContainer() as HTMLElement;
    const items = LB.map((l) => { const q = map.project([l.lon, l.lat]); return { el: l.el, x: q.x, y: q.y, r: l.r() + 1, pri: l.pri }; });
    const block = boxesOf(host, host.querySelectorAll(".ds-grat text, .maplibregl-ctrl-group, .maplibregl-ctrl-attrib"));
    const placed = placeLabels(host, items, { lines: lineSvg, block });
    // 수심 숫자는 장식이다 — 이름표·점과 겹치면 숨긴다
    const labelBoxes = placed.slice(block.length);
    for (const d of host.querySelectorAll<HTMLElement>(".ds-depth")) {
      d.style.visibility = "visible";
      const [b] = boxesOf(host, [d]);
      if (b && labelBoxes.some((p) => Math.min(b.r, p.r) > Math.max(b.l, p.l) && Math.min(b.b, p.b) > Math.max(b.t, p.t))) d.style.visibility = "hidden";
    }
  }
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
  // 달 넘기기 — 막대 하나 + 재생/멈춤. 숨 쉬듯 천천히 돈다(움직임 줄이기 설정이면 자동 재생 없음).
  function placesAt(i: number): any {
    return { type: "FeatureCollection", features: P.map((p) => { const v = valAt(p, i); return { type: "Feature", properties: { id: p.id, r: radius(v), top: p.v === topLast && p.v != null }, geometry: { type: "Point", coordinates: [p.lon, p.lat] } }; }) };
  }
  const slider = document.getElementById("ds-m") as HTMLInputElement | null, play = document.getElementById("ds-play") as HTMLButtonElement | null;
  const setMonth = (i: number) => {
    if (!MD || !map.getSource("places")) return;
    (map.getSource("places") as any).setData(placesAt(i));
    document.getElementById("ds-ym")!.textContent = MD.months[i];
    for (const p of P) { const n = document.querySelector(`[data-v="${p.id}"]`); const v = valAt(p, i); if (n) n.innerHTML = `${v ?? "—"}<small>천TEU</small>`; }
    for (const p of P) curR[p.id] = radius(valAt(p, i));
    relayout();
    if (slider) slider.value = String(i);
    $("ds-map").dataset.month = MD.months[i];
    const ps = (window as any).__mapPlay; if (ps) { ps.i = i; ps.frames++; }
  };
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let timer: any = null;
  const start = () => {
    if (!MD) return;
    play && (play.textContent = "멈춤", play.setAttribute("aria-pressed", "false"));
    timer = setInterval(() => setMonth((Number(slider?.value || 0) + 1) % MD.months.length), 900);
  };
  const stop = () => { clearInterval(timer); timer = null; play && (play.textContent = "재생", play.setAttribute("aria-pressed", "true")); };
  // [2026-10-15 P0] 만지면(달 막대·끌기·확대) 멈췄다가 6초 뒤 다시 돈다 · 「멈춤」 단추로 멈춘 것(held)은 그대로 — 첫 장면(해도 그림)의 상태를 이어받는다
  const PS = ((window as any).__mapPlay ||= { held: reduce, i: MD ? MD.months.length - 1 : 0, frames: 0 });
  let rt: any = 0;
  const touch = () => { stop(); clearTimeout(rt); if (!PS.held && !reduce) rt = setTimeout(() => { if (!timer && !PS.held) start(); }, 6000); };
  slider?.addEventListener("input", () => { touch(); setMonth(Number(slider.value)); });
  play?.addEventListener("click", () => { clearTimeout(rt); if (timer) { PS.held = true; stop(); } else { PS.held = false; start(); } });
  for (const ev of ["dragstart", "zoomstart", "rotatestart", "pitchstart"]) map.on(ev, (e: any) => { if (e.originalEvent) touch(); });
  // 첫 장면에서 흐르던 달에서 이어 돈다
  map.once("idle", () => { (window as any).__mapPosterStop?.(); if (MD && PS.i != null) setMonth(PS.i); if (reduce || PS.held) stop(); else start(); });
  // 다 그린 뒤(idle) 상태를 적는다 — 시험이 이것을 기다렸다가 화면 픽셀을 잰다
  map.once("idle", () => {
    const base = has && map.isSourceLoaded("protomaps");
    (window as any).__dsmap = { tiles: has, base, places: P.length, errors: errs };
    $("ds-map").dataset.ready = base ? "tiles" : has ? "tiles-failed" : "no-tiles";
    relayout();
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

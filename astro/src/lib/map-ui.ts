// 3D 지도 — maplibre(같은 주소 vendor/) + pmtiles(내장 타일) + deck.gl(interleaved:false · 판정 v2).
// 늦게 불러온다: 누르거나, 넓은 화면에서 첫 화면이 다 그려진 뒤(기준 20 · 홈 성능 90 지키기).
type Place = { id: string; label: string; kind: string; lon: number; lat: number; values: (number | null)[] | null };
const $ = (id: string) => document.getElementById(id)!;

export function initMap() {
  const D = JSON.parse($("map-data").textContent || "{}") as { months: string[]; places: Place[] };
  const cfg = (window as any).__mapcfg;
  const range = $("month") as HTMLInputElement;
  const out = $("month-out");
  let idx = Number(range.value);
  let overlay: any = null, deckMods: any = null, loading = false, timer = 0;

  const layers = () => {
    if (!deckMods) return [];
    const { ColumnLayer, TextLayer, ScatterplotLayer } = deckMods;
    const pts = D.places.map((p) => ({ ...p, v: p.values ? p.values[idx] : null }));
    return [
      new ColumnLayer({
        id: "cols", data: pts.filter((p) => p.v !== null), diskResolution: 24, radius: 700, extruded: true, elevationScale: 45,
        getPosition: (d: any) => [d.lon, d.lat], getElevation: (d: any) => d.v, getFillColor: [63, 211, 230, 230], material: { ambient: 0.5, diffuse: 0.6, shininess: 40 },
        transitions: { getElevation: 400 }, updateTriggers: { getElevation: idx },
      }),
      new ScatterplotLayer({ id: "air", data: pts.filter((p) => p.kind === "air"), getPosition: (d: any) => [d.lon, d.lat], getRadius: 1200, getFillColor: [255, 181, 71, 220] }),
      new TextLayer({
        id: "labels", data: pts, characterSet: "auto", fontFamily: "system-ui, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif", fontWeight: 700,
        getPosition: (d: any) => [d.lon, d.lat, d.v ? d.v * 45 + 500 : 300], getText: (d: any) => (d.v !== null ? `${d.id} ${d.v}천TEU` : d.label),
        getSize: 14, getColor: [238, 245, 250], outlineWidth: 3, outlineColor: [5, 9, 15], fontSettings: { sdf: true }, updateTriggers: { getText: idx, getPosition: idx },
      }),
    ];
  };
  const redraw = () => { out.textContent = D.months[idx]; if (overlay) overlay.setProps({ layers: layers() }); };
  range.addEventListener("input", () => { idx = Number(range.value); redraw(); });
  $("play").addEventListener("click", () => {
    if (timer) { clearInterval(timer); timer = 0; $("play").textContent = "▶ 재생"; return; }
    $("play").textContent = "❚❚ 멈춤";
    if (idx >= D.months.length - 1) idx = 0;
    timer = window.setInterval(() => { idx = (idx + 1) % D.months.length; range.value = String(idx); redraw(); if (idx === D.months.length - 1) $("play").click(); }, 450);
  });

  async function open3d() {
    if (loading) return; loading = true;
    $("open3d").textContent = "불러오는 중…";
    const css = document.createElement("link"); css.rel = "stylesheet"; css.href = cfg.css; document.head.append(css);
    const [ml, pm, bm, mb, dl] = await Promise.all([
      import(/* @vite-ignore */ cfg.ml), import("pmtiles"), import("@protomaps/basemaps"), import("@deck.gl/mapbox"), import("@deck.gl/layers"),
    ]);
    deckMods = dl;
    ml.setWorkerUrl(new URL(cfg.worker, location.href).href);
    const tilesUrl = new URL(cfg.tiles, location.href).href;
    const has = await fetch(tilesUrl, { method: "HEAD" }).then((r) => r.ok, () => false);
    const style: any = { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#05090f" } }] };
    if (has) {
      const proto = new pm.Protocol(); ml.addProtocol("pmtiles", proto.tile);
      style.sources.protomaps = { type: "vector", url: `pmtiles://${tilesUrl}`, attribution: "© OpenStreetMap · Protomaps" };
      // 라벨(symbol) 층은 뺀다 — 글리프 서버가 필요하고, 라벨은 deck TextLayer(시스템 글꼴)로 직접 단다(주의 ④).
      style.layers = bm.layers("protomaps", bm.namedFlavor("dark"), { lang: "ko" }).filter((l: any) => l.type !== "symbol");
    }
    $("map").hidden = false;
    (document.querySelector(".mp__still") as SVGElement).style.display = "none"; // SVG 요소는 hidden 속성 프로퍼티가 없다
    const map = new ml.Map({
      container: "map", style, center: [126.56, 37.41], zoom: 9.6, pitch: 55, bearing: -18, maxPitch: 70,
      maxBounds: [[126.2, 37.15], [127.0, 37.72]], attributionControl: false,
    });
    map.addControl(new ml.NavigationControl({ visualizePitch: true }), "top-right");
    map.on("load", () => {
      overlay = new mb.MapboxOverlay({ interleaved: false, layers: layers() });
      map.addControl(overlay);
      $("open3d").textContent = has ? "3D 지도" : "3D 지도(바탕 타일 없음)";
      (window as any).__map3d = { tiles: has, layers: 3 };
    });
  }
  $("open3d").addEventListener("click", open3d);
  // 넓은 화면은 첫 화면을 다 그린 뒤 스스로 연다. 움직임 줄이기면 누를 때만.
  if (matchMedia("(min-width: 900px)").matches && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    addEventListener("load", () => setTimeout(open3d, 600), { once: true });
  }
}

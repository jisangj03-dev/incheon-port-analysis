// 해도 한 장의 그림 좌표(빌드 때) — 경위도 사각 투영(위도 37.44° 에서 cos 보정). 홈·공급망 따라가기가 같이 쓴다.
// 땅·고속도로 = data/derived/land_incheon.geojson(OSM · ODbL) · 등심선·해안선 = data/derived/bathy_incheon.geojson(NOAA ETOPO 2022).
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

export const BB = [126.0, 37.0, 127.4, 37.9]; // 그림 좌표 범위(넓게 — 보이는 범위는 화면에서 맞춘다)
export const KX = 1000 / (BB[2] - BB[0]), KY = KX / Math.cos((37.44 * Math.PI) / 180);
export const px = (lon: number) => (lon - BB[0]) * KX;
export const py = (lat: number) => (BB[3] - lat) * KY;
export const CH = Math.round(py(BB[1]));
export const path = (c: number[][], close = false) => c.map(([x, y], i) => `${i ? "L" : "M"}${px(x).toFixed(1)},${py(y).toFixed(1)}`).join("") + (close ? "Z" : "");
const rd = (f: string) => { const q = join(repoRoot(), f); return existsSync(q) ? JSON.parse(readFileSync(q, "utf-8")) : null; };

let _base: any = null;
/** 바탕 — 땅 면(한 path) · 고속도로(한 path) · 등심선 · 해안선(땅 자료가 없을 때만) */
export function base() {
  if (_base) return _base;
  const bathy = rd("data/derived/bathy_incheon.geojson"), land = rd("data/derived/land_incheon.geojson");
  // 자료가 있는 범위(그림 좌표) — 보이는 범위가 이 밖으로 나가면 땅이 직선으로 잘려 보인다(2026-10-14) → 화면 맞춤이 이 안에 가둔다
  const xs: number[] = [], ys: number[] = [];
  if (land) for (const f of land.features) for (const c of (f.geometry.type === "Polygon" ? f.geometry.coordinates[0] : f.geometry.coordinates)) { xs.push(c[0]); ys.push(c[1]); }
  // 서쪽은 열어 둔다 — 자료 밖 서쪽은 황해(바다 = 종이)라 잘려 보이지 않는다. 남·북·동은 땅이 있어 가둔다.
  const limit = xs.length ? [px(BB[0]), py(Math.max(...ys)), px(Math.max(...xs)), py(Math.min(...ys))] : null;
  _base = {
    limit,
    land: land ? land.features.filter((f: any) => f.properties.kind === "land").map((f: any) => path(f.geometry.coordinates[0], true)).join("") : "",
    road: land ? land.features.filter((f: any) => f.properties.kind === "road").map((f: any) => path(f.geometry.coordinates)).join("") : "",
    contours: bathy ? bathy.features.filter((f: any) => f.properties.kind === "contour").map((f: any) => path(f.geometry.coordinates)) : [],
    coast: bathy ? bathy.features.filter((f: any) => f.properties.kind === "coast").map((f: any) => path(f.geometry.coordinates)) : [],
  };
  return _base;
}

/** 두 점 사이 완만한 곡선(개념선 — 실제 경로 아님) */
export function curve(a: [number, number], b: [number, number], bend = [0.18, 0.12]) {
  const [x0, y0, x1, y1] = [px(a[0]), py(a[1]), px(b[0]), py(b[1])];
  const cx = (x0 + x1) / 2 - (y1 - y0) * bend[0], cy = (y0 + y1) / 2 + (x1 - x0) * bend[1];
  return `M${x0.toFixed(1)},${y0.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`;
}

/** 맞출 범위(그림 좌표) */
export function fitBox(pts: [number, number][]) {
  const xs = pts.map((p) => px(p[0])), ys = pts.map((p) => py(p[1]));
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

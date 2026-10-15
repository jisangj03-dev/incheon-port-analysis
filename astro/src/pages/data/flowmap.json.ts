// 홈 「살아 있는 지도」가 받아 그리는 묶음(지연 로딩 · 외부 요청 0) — 먼 바탕(Natural Earth 땅) · 가까운 바탕(인천 땅·고속도로·등심선) · 흐름 숫자.
// 숫자는 data/derived/home_flows.json 그대로(tools-build/flows_derive.py). 좌표는 소수 넷째 자리로 줄인다.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "../../lib/content";
const J = (f: string) => JSON.parse(readFileSync(join(repoRoot(), f), "utf-8"));
const q = (c: number[][]) => c.flatMap(([x, y]) => [Math.round(x * 1e4) / 1e4, Math.round(y * 1e4) / 1e4]);

export function GET() {
  const W = J("data/derived/world_land.json"), L = J("data/derived/land_incheon.geojson"), B = J("data/derived/bathy_incheon.geojson"), F = J("data/derived/home_flows.json");
  const land = L.features.filter((f: any) => f.properties.kind === "land").map((f: any) => q(f.geometry.coordinates[0]));
  const road = L.features.filter((f: any) => f.properties.kind === "road").map((f: any) => q(f.geometry.coordinates));
  const ct = B.features.filter((f: any) => f.properties.kind === "contour").map((f: any) => q(f.geometry.coordinates));
  const xs: number[] = [], ys: number[] = [];
  for (const r of land) for (let i = 0; i < r.length; i += 2) { xs.push(r[i]); ys.push(r[i + 1]); }
  const body = { world: W.rings, near: { bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)], land, road, ct }, flows: F,
    credit: { world: W.source, near: `${L.source || "OpenStreetMap"} · ${L.license || "ODbL"}`, ct: "NOAA ETOPO 2022" } };
  return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
}

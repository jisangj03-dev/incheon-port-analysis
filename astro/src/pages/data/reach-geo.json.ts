// 수도권 도달 등시선의 바탕(땅·고속도로)만 — 등시선 화면 범위로 잘라 보낸다(2026-10-14: 홈 지도 묶음 flowmap.json 을 통째로 받아 모바일 성능 71).
// 자르기 = 사각형에 대한 서덜랜드–호지먼(다각형 채우기용 · 테두리를 따라 생기는 변은 화면 밖이라 안 보인다).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "../../lib/content";
const J = (f: string) => JSON.parse(readFileSync(join(repoRoot(), f), "utf-8"));
const BOX = [125.6, 36.4, 128.3, 38.5]; // 등시선 격자(126.2~127.75 · 36.85~37.98)보다 넉넉히 — 가로로 긴 화면에서 옆이 비지 않게
const r4 = (v: number) => Math.round(v * 1e4) / 1e4;

function clip(flat: number[]) {
  let pts: number[][] = []; for (let i = 0; i < flat.length; i += 2) pts.push([flat[i], flat[i + 1]]);
  const edges: [(p: number[]) => boolean, (a: number[], b: number[]) => number[]][] = [
    [(p) => p[0] >= BOX[0], (a, b) => [BOX[0], a[1] + ((b[1] - a[1]) * (BOX[0] - a[0])) / (b[0] - a[0])]],
    [(p) => p[0] <= BOX[2], (a, b) => [BOX[2], a[1] + ((b[1] - a[1]) * (BOX[2] - a[0])) / (b[0] - a[0])]],
    [(p) => p[1] >= BOX[1], (a, b) => [a[0] + ((b[0] - a[0]) * (BOX[1] - a[1])) / (b[1] - a[1]), BOX[1]]],
    [(p) => p[1] <= BOX[3], (a, b) => [a[0] + ((b[0] - a[0]) * (BOX[3] - a[1])) / (b[1] - a[1]), BOX[3]]],
  ];
  for (const [inside, cut] of edges) {
    const out: number[][] = [];
    for (let i = 0; i < pts.length; i++) { const a = pts[(i + pts.length - 1) % pts.length], b = pts[i];
      if (inside(b)) { if (!inside(a)) out.push(cut(a, b)); out.push(b); } else if (inside(a)) out.push(cut(a, b)); }
    pts = out; if (!pts.length) return null;
  }
  return pts.length >= 3 ? pts.flatMap(([x, y]) => [r4(x), r4(y)]) : null;
}
const inBox = (flat: number[]) => { for (let i = 0; i < flat.length; i += 2) if (flat[i] >= BOX[0] && flat[i] <= BOX[2] && flat[i + 1] >= BOX[1] && flat[i + 1] <= BOX[3]) return true; return false; };

export function GET() {
  const W = J("data/derived/world_land.json"), L = J("data/derived/land_incheon.geojson");
  const world = (W.rings as number[][]).map(clip).filter(Boolean);
  const land = L.features.filter((f: any) => f.properties.kind === "land").map((f: any) => clip(f.geometry.coordinates[0].flat())).filter(Boolean);
  const road = L.features.filter((f: any) => f.properties.kind === "road").map((f: any) => f.geometry.coordinates.flat().map(r4)).filter(inBox);
  return new Response(JSON.stringify({ box: BOX, world, near: { land, road }, credit: { world: W.source, near: `${L.source || "OpenStreetMap"} · ${L.license || "ODbL"}` } }), { headers: { "Content-Type": "application/json" } });
}

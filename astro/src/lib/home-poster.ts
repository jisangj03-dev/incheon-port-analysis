// 홈 살아 있는 지도의 정지 그림(빌드 때) — 캔버스 첫 장면과 같은 카메라·같은 색. 그림 파일(assets/home-poster.svg)로 따로 낸다:
// 문서 안 인라인 SVG 는 첫 배치·칠하기를 붙잡았다(2026-10-14 실측 · 모바일 4배 감속에서 약 0.2초). 그림은 비동기로 풀린다.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";
import { projector, mx, my, VIEWS } from "./flowmap";

export const PW = 1600, PH = 900;
const J = (f: string) => JSON.parse(readFileSync(join(repoRoot(), f), "utf-8"));

export function poster() {
  const F = J("data/derived/home_flows.json"), WL = J("data/derived/world_land.json");
  const PJ = projector(VIEWS.asia, PW, PH).fn, o = [0, 0, 0];
  const pt = (lon: number, lat: number) => { PJ(mx(lon), my(lat), 0, o); return `${o[0].toFixed(0)},${o[1].toFixed(0)}`; };
  const inView = (r: number[]) => { for (let i = 0; i < r.length; i += 8) { PJ(mx(r[i]), my(r[i + 1]), 0, o); if (o[0] > -200 && o[0] < PW + 200 && o[1] > -200 && o[1] < PH + 200) return true; } return false; };
  // 화면에서 4px 안쪽 꼭짓점은 건너뛰고, 화면 넓이 40px² 아래 섬은 뺀다
  const land = (WL.rings as number[][]).filter(inView).map((r) => {
    const q: number[][] = [];
    for (let i = 0; i < r.length; i += 2) { PJ(mx(r[i]), my(r[i + 1]), 0, o); const l = q[q.length - 1]; if (!l || Math.abs(o[0] - l[0]) + Math.abs(o[1] - l[1]) > 4) q.push([Math.round(o[0]), Math.round(o[1])]); }
    let A = 0; for (let i = 0; i < q.length; i++) { const a = q[i], b = q[(i + 1) % q.length]; A += a[0] * b[1] - b[0] * a[1]; }
    return q.length > 3 && Math.abs(A) / 2 > 40 ? "M" + q.map((v) => v.join(",")).join("L") + "Z" : "";
  }).join("");
  const sg = F.sea_gates[0];
  const lanes = F.partners.map((p: any) => "M" + [...p.sea, ...sg.approach, [sg.lon, sg.lat]].map(([a, b]: number[]) => pt(a, b)).join("L")).join("");
  PJ(mx(F.air_gate.lon), my(F.air_gate.lat), 0, o);
  const gate = [Math.round(o[0]), Math.round(o[1])];
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${PW} ${PH}" width="${PW}" height="${PH}">` +
    `<rect width="${PW}" height="${PH}" fill="#f3efe5"/><path d="${land}" fill="#e7dfcc" fill-rule="evenodd"/>` +
    `<path d="${lanes}" fill="none" stroke="#191714" stroke-opacity="0.12" stroke-width="1.2"/>` +
    `<circle cx="${gate[0]}" cy="${gate[1]}" r="6" fill="#b3361e"/>` +
    `<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f5f2eb" stop-opacity="0.96"/><stop offset="1" stop-color="#f5f2eb" stop-opacity="0"/></linearGradient></defs>` +
    `<rect width="${PW}" height="${PH * 0.42}" fill="url(#f)"/></svg>`;
  return { svg, gate };
}

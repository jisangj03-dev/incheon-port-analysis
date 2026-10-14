// 시안(lab) 장면의 계열 CSV — 차트와 같은 함수에서 나온다(화면과 파일이 갈라지지 않게). lab/ 이라 공개 배포물에는 없다.
import { portMonthly, mapSeries } from "../../../lib/data";

const DATA: Record<string, () => { rows: Record<string, unknown>[]; note: string }> = {
  "port-monthly": () => { const d = portMonthly(); return { rows: d.series.map((r) => ({ 연월: r.ym, 당월_천TEU: r.v, 전년대비_pct: r.yoy })), note: `${d.source} · 인천항 컨테이너 합계 · 마지막 갱신 ${d.updated}` }; },
  "map-places": () => { const d = mapSeries(); const ym = d.months[d.months.length - 1]; return { rows: d.places.map((p: any) => ({ 연월: ym, 장소: p.id, 구분: p.kind, 경도: p.lon, 위도: p.lat, 개략위치: p.approx ? 1 : 0, 당월_천TEU: p.values ? p.values[p.values.length - 1] : "" })), note: `${d.source} · 자리 OpenStreetMap 시설 면 중심 · 마지막 갱신 ${d.updated}` }; },
};

export function getStaticPaths() { return Object.keys(DATA).map((name) => ({ params: { name } })); }
const cell = (v: unknown) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
export function GET({ params }: { params: { name: string } }) {
  const { rows, note } = DATA[params.name]();
  const head = Object.keys(rows[0] || {});
  const body = [`# 측심 · ${note}`, head.join(","), ...rows.map((r) => head.map((h) => cell(r[h])).join(","))].join("\n") + "\n";
  return new Response("﻿" + body, { headers: { "Content-Type": "text/csv; charset=utf-8" } });
}

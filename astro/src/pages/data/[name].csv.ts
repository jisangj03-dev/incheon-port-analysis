// 보고서 ② 층 위젯의 계열을 CSV 로(B7 · 퍼가기·내려받기). 위젯과 같은 함수에서 나온다 — 화면과 파일이 갈라지지 않는다.
import { emptyDirection, sizeDirection, terminals, items } from "../../lib/report-data";

const DATA: Record<string, () => { rows: Record<string, unknown>[]; note: string }> = {
  "empty-direction": () => { const d = emptyDirection(); return { rows: d.series.map((r) => ({ 연월: r.ym, 수입방향_TEU: r.imp, 수출방향_TEU: r.exp, 환적_TEU: r.tr })), note: `${d.source} · 외항(ocCt=1) · 외국적+한국적 공컨 · 마지막 갱신 ${d.updated}` }; },
  "size-direction": () => { const d = sizeDirection(); return { rows: d.series.map((r) => ({ 연월: r.ym, 수입_40ft비중_pct: r.impShare, 수출_40ft비중_pct: r.expShare, 격차_pp: r.gap, 수입_총박스: r.impBox, 저볼륨: r.lowVolume })), note: `${d.source} · 박스 수 기준 · 마지막 갱신 ${d.updated}` }; },
  terminals: () => { const d = terminals(); return { rows: d.series.map((r) => ({ 연월: r.ym, 터미널: r.name, 부두군: r.group, 당월_천TEU: r.v, 전년대비_pct: r.yoy })), note: `${d.source} · 마지막 갱신 ${d.updated}` }; },
  items: () => { const d = items(); return { rows: d.series.map((r) => ({ 연월: r.ym, HS류: r.hs, 품목: r.name, 수출_천달러: r.exp, 수입_천달러: r.imp })), note: `${d.source} · 인천광역시 · 금액 단위 천 달러 · 마지막 갱신 ${d.updated}` }; },
};

export function getStaticPaths() {
  return Object.keys(DATA).map((name) => ({ params: { name } }));
}

const cell = (v: unknown) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };

export function GET({ params }: { params: { name: string } }) {
  const { rows, note } = DATA[params.name]();
  const head = Object.keys(rows[0] || {});
  const body = [`# 측심 · ${note} · 출처 대장 https://jisangj03-dev.github.io/incheon-port-analysis/data.html`, head.join(","), ...rows.map((r) => head.map((h) => cell(r[h])).join(","))].join("\n") + "\n";
  return new Response("﻿" + body, { headers: { "Content-Type": "text/csv; charset=utf-8" } });
}

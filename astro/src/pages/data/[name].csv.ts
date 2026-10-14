// 지면 차트·보고서 위젯의 계열을 CSV 로(B7 · 퍼가기·내려받기 · 신뢰 꼬리). 차트와 같은 함수·같은 파일에서 나온다 — 화면과 파일이 갈라지지 않는다.
import { emptyDirection, sizeDirection, terminals, items } from "../../lib/report-data";
import { portMonthly, mapSeries } from "../../lib/data";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "../../lib/content";
const J = (f: string) => JSON.parse(readFileSync(join(repoRoot(), f), "utf-8"));

const DATA: Record<string, () => { rows: Record<string, unknown>[]; note: string }> = {
  "empty-direction": () => { const d = emptyDirection(); return { rows: d.series.map((r) => ({ 연월: r.ym, 수입방향_TEU: r.imp, 수출방향_TEU: r.exp, 환적_TEU: r.tr })), note: `${d.source} · 외항(ocCt=1) · 외국적+한국적 공컨 · 마지막 갱신 ${d.updated}` }; },
  "size-direction": () => { const d = sizeDirection(); return { rows: d.series.map((r) => ({ 연월: r.ym, 수입_40ft비중_pct: r.impShare, 수출_40ft비중_pct: r.expShare, 격차_pp: r.gap, 수입_총박스: r.impBox, 저볼륨: r.lowVolume })), note: `${d.source} · 박스 수 기준 · 마지막 갱신 ${d.updated}` }; },
  terminals: () => { const d = terminals(); return { rows: d.series.map((r) => ({ 연월: r.ym, 터미널: r.name, 부두군: r.group, 당월_천TEU: r.v, 전년대비_pct: r.yoy })), note: `${d.source} · 마지막 갱신 ${d.updated}` }; },
  items: () => { const d = items(); return { rows: d.series.map((r) => ({ 연월: r.ym, HS류: r.hs, 품목: r.name, 수출_천달러: r.exp, 수입_천달러: r.imp })), note: `${d.source} · 인천광역시 · 금액 단위 천 달러 · 마지막 갱신 ${d.updated}` }; },
  "port-monthly": () => { const d = portMonthly(); return { rows: d.series.map((r) => ({ 연월: r.ym, 당월_천TEU: r.v, 전년대비_pct: r.yoy })), note: `${d.source} · 인천항 컨테이너 합계 · 마지막 갱신 ${d.updated}` }; },
  "map-places": () => { const d = mapSeries(); const ym = d.months[d.months.length - 1]; return { rows: d.places.map((p: any) => ({ 연월: ym, 장소: p.id, 구분: p.kind, 경도: p.lon, 위도: p.lat, 개략위치: p.approx ? 1 : 0, 당월_천TEU: p.values ? p.values[p.values.length - 1] : "" })), note: `${d.source} · 자리 OpenStreetMap 시설 면 중심 · 마지막 갱신 ${d.updated}` }; },
  // 공급망 따라가기 — 구간마다 화면에 쓴 숫자를 한 줄씩(구간·항목·값·단위·범위). 데이터 없음 구간도 그대로 적는다.
  "supply-hs85": () => {
    const D = J("data/derived/supply_hs85.json"); const rows: Record<string, unknown>[] = [];
    for (const s of D.steps) {
      if (!s.data) { rows.push({ 구간: s.title, 항목: "데이터 없음", 값: "", 단위: "", 기준월: "", 범위: s.why }); continue; }
      const d = s.data, ym = d.ym || "";
      if (s.id === "origin") for (const c of d.countries) rows.push({ 구간: s.title, 항목: `${c.name} 수입`, 값: c.musd, 단위: "백만 달러", 기준월: ym, 범위: d.scope }), rows.push({ 구간: s.title, 항목: `${c.name} 비중`, 값: c.share_pct, 단위: "%", 기준월: ym, 범위: d.scope });
      if (s.id === "sea") rows.push({ 구간: s.title, 항목: "컨테이너", 값: d.kteu, 단위: "천TEU", 기준월: ym, 범위: d.scope }, { 구간: s.title, 항목: "전년 같은 달 대비", 값: d.yoy_pct, 단위: "%", 기준월: ym, 범위: d.scope });
      if (s.id === "customs") for (const g of d.gates) rows.push({ 구간: s.title, 항목: g.name, 값: g.share_pct, 단위: "% (전국 수입액 중)", 기준월: ym, 범위: d.scope });
      if (s.id === "firms") rows.push({ 구간: s.title, 항목: "인천 소재 수입자 전기기기 수입", 값: d.imp_kusd, 단위: "천 달러", 기준월: ym, 범위: d.scope }, { 구간: s.title, 항목: "인천 수입 중 비중", 값: d.share_of_incheon_imports_pct, 단위: "%", 기준월: ym, 범위: d.scope });
      if (s.id === "warehouse") rows.push({ 구간: s.title, 항목: "물류창고", 값: d.sites, 단위: "곳", 기준월: "", 범위: d.scope }, { 구간: s.title, 항목: "보세(관세법)", 값: d.bonded_sites, 단위: "곳", 기준월: "", 범위: d.scope });
    }
    return { rows, note: `공급망 따라가기 · 전기기기(HS 85) · 계산 ${D.command} · ${D.computed}` };
  },
  "vessel-replay": () => {
    const V = J("data/derived/vessel_replay.json");
    const ports = Object.keys(V.ocean_arrivals);
    return { rows: V.months.map((m: string, i: number) => Object.fromEntries([["연월", m], ...ports.map((p) => [`${p}_외항선_입항척수`, V.ocean_arrivals[p][i]]), ["인천_연안선_입항척수", V.incheon_coastal[i]]])), note: `선박 리플레이 · 해양수산부 항만별 선박입출항실적 · 월 집계(개별 선박 아님) · 외항 = 국적선+외국선 · 계산 ${V.command}` };
  },
  // 수요예측 원장 — 덧붙이기만 하는 예측 기록 그대로(발행·기준월·목표월·수평·모델·예측값)
  "forecast-ledger": () => {
    const [head, ...rows] = readFileSync(join(repoRoot(), "data/forecast/incheon_container_teu.csv"), "utf-8").replace(/^\uFEFF/, "").trim().split(/\r?\n/);
    const k = head.split(",");
    return { rows: rows.map((r) => Object.fromEntries(r.split(",").map((v, i) => [k[i], v]))), note: "수요예측 실험실 원장 · data/forecast/incheon_container_teu.csv(덧붙이기만 · 고치지 않는다) · 단위 천TEU" };
  },
  "ops-stats": () => {
    const S = J("data/derived/ops_stats.json");
    const keys: [string, string][] = [["commits_total", "커밋(병합 제외)"], ["ai_coauthored", "AI 세션 꼬리표 커밋"], ["bot_routine", "예약 루틴 커밋"], ["human_only", "AI 꼬리표 없는 커밋"], ["corrections", "제목에 정정·되돌림이 적힌 커밋(반대 지표)"], ["prs_merged", "머지된 PR"], ["active_days", "커밋이 있었던 날"], ["ai_share_pct", "AI 꼬리표 비율(%)"], ["human_share_pct", "꼬리표 없는 비율(%)"]];
    return { rows: keys.map(([k, n]) => ({ 항목: n, 값: S[k] })), note: `AI 운영실 · 이 저장소 main(${S.ref_sha}) ${S.first_day}~${S.last_day} · 명령 ${S.command}` };
  },
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

// 지면 차트·보고서 위젯의 계열을 CSV 로(B7 · 퍼가기·내려받기 · 신뢰 꼬리). 차트와 같은 함수·같은 파일에서 나온다 — 화면과 파일이 갈라지지 않는다.
import { emptyDirection, sizeDirection, terminals, items } from "../../lib/report-data";
import { portMonthly, mapSeries } from "../../lib/data";
import { readFileSync, existsSync } from "node:fs";
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
      if (s.id === "warehouse") rows.push({ 구간: s.title, 항목: "물류창고", 값: d.sites, 단위: "곳", 기준월: "", 범위: d.scope }, { 구간: s.title, 항목: "보세창고(관세법 제174조 특허)", 값: d.bonded_sites, 단위: "곳", 기준월: "", 범위: d.scope });
    }
    return { rows, note: `전기기기(HS 85) 구간별 원천 숫자 · 계산 ${D.command} · ${D.computed}` };
  },
  // 홈 살아 있는 지도 — 관문별 월 수출입(억 달러) · 전국 대비 비중 · 부두군 컨테이너(천TEU)
  "home-flows": () => {
    const F = J("data/derived/home_flows.json");
    return { rows: F.months.map((m: any) => ({ 연월: m.ym, 인천공항_수입_억달러: m.air_imp, 인천공항_수출_억달러: m.air_exp, 인천항_수입_억달러: m.port_imp, 인천항_수출_억달러: m.port_exp,
      인천_수입_전국비중_pct: m.imp_share_pct, 인천_수출_전국비중_pct: m.exp_share_pct, 신항_천TEU: m.teu?.["신항"] ?? "", 남항_천TEU: m.teu?.["남항"] ?? "", 국제여객부두_천TEU: m.teu?.["국제여객부두"] ?? "" })),
      note: `관세청 항구·공항별 수출입실적 · 인천지방해양수산청 항만운영통계 · 계산 tools-build/flows_derive.py · ${F.made}` };
  },
  // 홈 「최신 공표분으로 잰 숫자」 절 — 절에 보이는 숫자를 한 줄씩(항목·값·단위·기준월·원천). 지면과 같은 파일에서 읽는다(28차 사실 대조 — 종전 CSV 는 관문 금액뿐)
  "home-now": () => {
    const F = J("data/derived/home_flows.json"), L = F.months[F.months.length - 1];
    const AX = existsSync(join(repoRoot(), "data/derived/home_axes.json")) ? J("data/derived/home_axes.json") : null, T = AX?.trade, R = AX?.retail;
    const P = portMonthly(), PL = P.series[P.series.length - 1], V = J("data/derived/vessel_replay.json").latest;
    const r = (항목: string, 값: unknown, 단위: string, 기준월: string, 원천: string) => ({ 항목, 값, 단위, 기준월, 원천 });
    const rows = [
      r("전국 수입액", L.nat_imp, "억 달러", L.ym, "관세청 항구·공항별 수출입실적"),
      r("인천 관문(공항+항만) 수입 몫", L.imp_share_pct, "%", L.ym, "관세청 항구·공항별 수출입실적 · 입항지 기준"),
      r("인천 관문 수출 몫", L.exp_share_pct, "%", L.ym, "관세청 항구·공항별 수출입실적"),
      r("인천공항 수입", L.air_imp, "억 달러", L.ym, "관세청 항구·공항별 수출입실적"),
      r("인천항 수입", L.port_imp, "억 달러", L.ym, "관세청 항구·공항별 수출입실적"),
      r("인천공항 수출", L.air_exp, "억 달러", L.ym, "관세청 항구·공항별 수출입실적"),
      r("인천항 수출", L.port_exp, "억 달러", L.ym, "관세청 항구·공항별 수출입실적"),
      r("인천 관문 수입 중 공항 몫", Math.round((L.air_imp / L.imp_total) * 100), "%", L.ym, "관세청 항구·공항별 수출입실적"),
      r("인천항 컨테이너", PL.v, "천TEU", PL.ym, "인천지방해양수산청 항만운영통계"),
      r("인천항 컨테이너 전년 대비(공표값)", PL.yoy, "%", PL.ym, "인천지방해양수산청 항만운영통계"),
      r("인천항 외항선 입항", V.incheon, "척", V.ym, "해양수산부 항만별 선박입출항실적"),
      ...(T ? [r("수도권 화주 수입 몫(전국 대비)", T.imp_pct, "%", T.ym, "관세청 시도별 품목별 수출입실적 ÷ 관세청 국가별 수출입실적"),
        r("수도권 화주 수입", T.sudo_imp, "억 달러", T.ym, "관세청 시도별 품목별 수출입실적"), r("수도권 화주 수출", T.sudo_exp, "억 달러", T.ym, "관세청 시도별 품목별 수출입실적"),
        r(`수도권 수입 1위 HS ${T.top_imp[0].hs} 몫`, T.top_imp[0].pct, "%", T.ym, "관세청 시도별 품목별 수출입실적")] : []),
      ...(R ? [r("수도권 화주 생활소비재 수입", R.cons_imp, "억 달러", R.ym, "관세청 시도별 품목별 수출입실적 · 묶음 = tools-build/axes_derive.py CONSUMER"),
        r("생활소비재 수입 전년 같은 달 대비", R.cons_yoy, "%", R.ym, "같은 원천")] : []),
    ];
    return { rows, note: `홈 「최신 공표분으로 잰 숫자」 절 · 계산 tools-build/flows_derive.py · tools-build/axes_derive.py · ${F.made}` };
  },
  // 위성으로 본 묘박지 — 달마다 고른 장면 · 배 어림
  anchorage: () => {
    const S = J("data/derived/s2_anchorage.json");
    return { rows: S.frames.map((f: any) => ({ 날짜: f.date, 장면: f.scene, 타일구름_pct: f.tile_cloud_pct, 창구름_pct: f.aoi_cloud_pct, 배_어림: f.ships_seen, 신뢰낮음: f.low_confidence ? 1 : 0 })),
      note: `Contains modified Copernicus Sentinel data · ${S.method} · 계산 tools-build/v3/s2_anchorage.py · ${S.made}` };
  },
  // 인천항 일일 맥박 — 항만 × 날(입항 척수 · 선종별 · 추정 교역량 톤)
  "port-pulse": () => {
    const D = J("data/derived/port_pulse.json");
    return { rows: Object.values(D.ports).flatMap((p: any) => p.days.map((x: any) => ({ 항만: p.ko, 날짜: x.d, 입항_척: x.calls, ...Object.fromEntries(D.types.map((t: any) => [`${t.ko}_척`, x[t.id]])), 추정수입_톤: x.imp, 추정수출_톤: x.exp }))),
      note: `IMF PortWatch(AIS 기반 추정 · 비상업 이용) · ${D.asof} 기준 · 평소 = 직전 91일 · 계산 tools-build/v3/pulse_derive.py` };
  },
  // 환율 파도 · 수입원가 — 주 × 통화(관세청 과세환율 · 수입)
  "import-cost": () => {
    const D = J("data/derived/import_cost.json");
    return { rows: D.weeks.map((w: any[]) => Object.fromEntries([["적용개시일", w[0]], ...D.currencies.map((c: string, i: number) => [`${c}_원`, w[i + 1]])])),
      note: `${D.source} · JPY 는 1엔당 · 계산 tools-build/v3/fx_derive.py · 참고용 · 자문 아님` };
  },
  // 초크포인트 충격 — 길목 × 주(통항) · 길목 × 나라(교역)
  chokepoint: () => {
    const D = J("data/derived/chokepoints.json");
    const rows: Record<string, unknown>[] = [];
    for (const p of D.points) { for (const [w, v] of p.weeks) rows.push({ 길목: p.ko, 구분: "통항(주 평균 · 척/일)", 주_또는_나라: w, 값: v }); for (const t of p.top) rows.push({ 길목: p.ko, 구분: "교역(전국 · 12달 · 백만 달러)", 주_또는_나라: t.name, 값: t.musd }); }
    return { rows, note: `IMF PortWatch 초크포인트 일별 · 관세청 국가별 수출입(전국 ${D.months[0]}~${D.months[1]}) · 나라 → 길목 경유 = 대표 항로 가정(지면 「이 길목을 거치는 것으로 셈한 나라」) · 계산 tools-build/v3/choke_derive.py` };
  },
  // 품목 트리맵 레이스 — 해 × HS 2단위(인천 소재 기업 · 백만 달러)
  "trade-race": () => {
    const D = J("data/derived/trade_race.json");
    return { rows: D.years.flatMap((y: any) => y.items.map((i: any) => ({ 연도: y.y, 마지막달: y.through, HS2: i.hs, 품목: i.name, 수출_백만달러: i.exp, 수입_백만달러: i.imp, 수출비중_pct: i.exp_pct, 수입비중_pct: i.imp_pct }))),
      note: `관세청 시도별 품목별 수출입실적(공공데이터포털 15101641) · 시도 = 인천(28) · 원천 금액은 천 달러 → 이 CSV 의 금액 열은 백만 달러 · 관세청이 인천(시도 28)으로 집계한 업체 실적 — 업체를 시도에 넣는 기준은 공개 명세에 없다(입·출항 관문 기준이 아니다) · 계산 tools-build/v3/race_derive.py` };
  },
  // 수도권 배송 등시선 — 출발지 × 도시 도착 분(자유 흐름 속도 가정)
  "delivery-reach": () => {
    const I = J("data/derived/isochrones.json"), RS = existsSync(join(repoRoot(), "data/derived/reach_slots.json")) ? J("data/derived/reach_slots.json") : null;
    const SL = (RS?.slots ?? []).filter((t: any) => t.k !== 1);
    // 화면 기본값(낮 등 시간대 보정 분)을 CSV 로도 재현하게 — 시간대별 열을 같이 싣는다(9차 사실 대조: 자유 흐름 분만 있었다)
    return { rows: I.origins.flatMap((o: any, oi: number) => Object.entries(o.cities).map(([c, m]) => ({ 출발지: o.name, 구분: o.kind, 도시: c, 자유흐름_분: m ?? "", ...Object.fromEntries(SL.map((t: any) => [`${t.id}_분`, RS?.table?.[oi]?.[t.id]?.car?.[c] ?? ""])) }))),
      note: `OpenStreetMap 기여자(ODbL) · 도로 등급별 자유 흐름 속도 가정 · 시간대 열 = 자유 흐름 분 × 카카오 내비 대조 배율(${SL.map((t: any) => `${t.id} ×${t.k}`).join(" · ")}) · ${I.made}` };
  },
  // 공공입찰 레이더 — 스냅샷 공고 한 줄씩(담당자 개인정보 칸 없음 · 목록 검수 안 함)
  "bid-radar": () => {
    const R = J("data/derived/bid_radar.json");
    return { rows: R.items.map((x: any) => ({ 묶음: x.group, 공고번호: x.bidNtceNo, 차수: x.bidNtceOrd, 공고명: x.bidNtceNm, 공고기관: x.ntceInsttNm, 수요기관: x.dminsttNm, 공고일시: x.bidNtceDt, 마감일시: x.bidClseDt, 추정가격_원: x.presmptPrce ?? "", 나라장터: x.bidNtceDtlUrl })),
      note: `${R.source} · ${R.snapshot} 스냅샷(그 뒤 마감·정정됐을 수 있음) · 고르는 규칙 = 선커밋 ③-가 · 자동 수집 · 검수 안 함 · 계산 tools-build/v3/bid_radar.py` };
  },
  "vessel-replay": () => {
    const V = J("data/derived/vessel_replay.json");
    const ports = Object.keys(V.ocean_arrivals);
    return { rows: V.months.map((m: string, i: number) => Object.fromEntries([["연월", m], ...ports.map((p) => [`${p}_외항선_입항척수`, V.ocean_arrivals[p][i]]), ["인천_연안선_입항척수", V.incheon_coastal[i]]])), note: `외항선 입항 추이 · 해양수산부 항만별 선박입출항실적 · 월 집계(개별 선박 아님) · 외항 = 국적선+외국선 · 계산 ${V.command}` };
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

// 원천 파일이 아직 없는 표(수집 워크플로가 만들 것)는 빼고 낸다 — 없는 파일로 빌드가 깨지지 않게
// [2026-10-20 9차 사실 대조] 내린 지면만 쓰던 CSV 는 내지 않는다(링크 0 인데 주소로 열렸고 머리줄에 내부어가 남았다) — 만드는 함수는 남겨 다시 올릴 때 쓴다
const DOWN_CSV = new Set(["empty-direction", "size-direction", "terminals", "items", "map-places", "port-pulse", "bid-radar", "ops-stats", "anchorage"]);
export function getStaticPaths() {
  return Object.keys(DATA).filter((n) => !DOWN_CSV.has(n)).filter((name) => { try { DATA[name](); return true; } catch { return false; } }).map((name) => ({ params: { name } }));
}

const cell = (v: unknown) => { const s = v === null || v === undefined ? "" : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };

export function GET({ params }: { params: { name: string } }) {
  const { rows, note } = DATA[params.name]();
  const head = Object.keys(rows[0] || {});
  const body = [`# 측심 · ${note} · 출처 대장 https://jisangj03-dev.github.io/incheon-port-analysis/data.html`, head.join(","), ...rows.map((r) => head.map((h) => cell(r[h])).join(","))].join("\n") + "\n";
  return new Response("﻿" + body, { headers: { "Content-Type": "text/csv; charset=utf-8" } });
}

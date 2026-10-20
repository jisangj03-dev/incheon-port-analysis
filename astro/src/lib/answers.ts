// 도구마다 「지금의 답」 한 줄 — 도구 목록·노트 목록 첫 화면에 질문만 늘어놓고 답이 없었다(4차 화면 판정 Q1).
// 숫자는 각 도구 지면이 읽는 파생 파일과 같은 파일에서 같은 규칙으로 읽는다(지면 숫자는 데이터 파일에만 · 정체성 §2-1).
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";
import { portMonthly } from "./data";

const J = (p: string) => { const f = join(repoRoot(), p); return existsSync(f) ? JSON.parse(readFileSync(f, "utf-8")) : null; };
const sg = (v: number) => (v > 0 ? `+${v}` : v < 0 ? `−${-v}` : `${v}`); // 마이너스 = U+2212
export type Answer = { num: string; unit?: string; text: string; neg?: boolean; src?: string; // src = 숫자마다 출처 한 줄(8차 화면 판정 Q5)
  asof?: string; basis?: string; // 기준(정렬 키 = ISO 날짜 · 화면 글) — 도구 목록은 기준이 최신인 것부터(2026-10-21 Claude Design 시안 채택)
  bars?: { label: string; v: number; hi?: boolean }[]; barUnit?: string }; // 작은 그림 = 그 줄 숫자의 두 값 막대(시안의 「그 줄 숫자로만」 · 지어낸 값 0)

export function answers(): Record<string, Answer> {
  const out: Record<string, Answer> = {};
  const I = J("data/derived/isochrones.json"), RS = J("data/derived/reach_slots.json");
  if (I) {
    const first = Math.max(0, I.origins.findIndex((o: any) => o.kind === "물류단지")), O = I.origins[first];
    const SL = RS?.slots ?? [{ id: "자유 흐름", k: 1 }], DEF = SL.find((t: any) => t.id === RS?.default) ?? SL[0];
    const TB = RS?.table?.[first]?.[DEF.id], C0 = (TB?.car ?? O.cities) as Record<string, number | null>, W = TB?.within ?? O.cities_within;
    if (C0["서울시청"] != null) out["/tools/delivery-reach.html"] = { num: `${C0["서울시청"]}`, unit: "분", text: `${O.name} → 서울시청(승용차 · ${DEF.id}${DEF.k === 1 ? "" : " 시간 보정"}) · 수도권 ${O.n_cities}곳 가운데 1시간 안 ${W["1h"]}곳`, src: "OpenStreetMap 도로망으로 계산 · 카카오 내비 대조 보정", basis: `도로망 계산 · 갱신 ${I.made ?? ""}`.trim(), bars: [{ label: "서울시청", v: C0["서울시청"]!, hi: true }, { label: "1시간", v: 60 }], barUnit: "분" };
  }
  const R = J("data/derived/trade_race.json");
  if (R) { const Y = R.years.filter((y: any) => !y.partial), L = Y[Y.length - 1]; out["/tools/trade-race.html"] = { num: `${Number(L.top_exp.pct).toFixed(1)}%`, text: `${L.y}년 인천 소재 기업 수출 1위 ${L.top_exp.name}의 몫`, src: "관세청 시도별 품목별 수출입실적(연간)", asof: `${L.y}-12-31`, basis: `${L.y}년 · 연간`, bars: [{ label: Y[0].y, v: Number(Y[0].top_exp.pct) }, { label: L.y, v: Number(L.top_exp.pct), hi: true }], barUnit: "%" }; }
  const E = J("data/derived/import_cost.json")?.example;
  if (E) out["/tools/import-cost.html"] = { num: `${sg(E.pct)}%`, text: `1만 달러 물건 원가(부가세 제외) — ${E.ago_weeks}주 전보다 · ${E.now.week.slice(0, 4)}-${E.now.week.slice(4, 6)}-${E.now.week.slice(6, 8)} 주 과세환율 ${E.now.fx.toLocaleString("ko-KR")}원/달러`, neg: E.pct < 0, src: "관세청 관세환율(수입 · 주간)", asof: `${E.now.week.slice(0, 4)}-${E.now.week.slice(4, 6)}-${E.now.week.slice(6, 8)}`, basis: `${E.now.week.slice(0, 4)}-${E.now.week.slice(4, 6)}-${E.now.week.slice(6, 8)} 주 · 주간`, bars: [{ label: `${E.ago_weeks}주 전`, v: E.ago.cost }, { label: "지금", v: E.now.cost, hi: true }], barUnit: "원" };
  const C = J("data/derived/chokepoints.json");
  if (C) { const F = C.points.filter((p: any) => p.vs_base_pct != null).sort((a: any, b: any) => a.vs_base_pct - b.vs_base_pct)[0]; if (F) out["/tools/chokepoint.html"] = { num: `${sg(F.vs_base_pct)}%`, text: `${F.ko} 통항 — 공개 마지막 28일 하루 평균(${F.asof}까지), 2023년 같은 달 대비`, neg: F.vs_base_pct < 0, src: "IMF PortWatch 길목 통항(AIS 기반 추정)", asof: F.asof, basis: `${F.asof}까지 · 일별`, bars: [{ label: "2023년 같은 달", v: F.base_2023_same_month }, { label: "최근 28일", v: F.now28, hi: true }], barUnit: "척/일" }; }
  const V = J("data/derived/vessel_replay.json")?.latest;
  if (V) out["/map/vessels.html"] = { num: `${V.busan_to_incheon}배`, text: `${V.ym} 외항선 입항 — 부산 ${V.busan.toLocaleString("ko-KR")}척 · 인천 ${V.incheon}척`, src: "해양수산부 항만별 선박입출항실적(월)", asof: `${V.ym}-28`, basis: `${V.ym} · 월간`, bars: [{ label: "부산", v: V.busan }, { label: "인천", v: V.incheon, hi: true }], barUnit: "척" };
  const P = portMonthly(), last = P.series[P.series.length - 1];
  if (last?.yoy != null) out["/notes/port-yoy.html"] = { num: `${sg(last.yoy)}%`, text: `${last.ym} 인천항 컨테이너 ${last.v}천TEU — 작년 같은 달 대비(공표값)`, neg: last.yoy < 0, src: "인천지방해양수산청 월별 항만운영통계" };
  return out;
}

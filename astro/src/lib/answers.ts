// 도구마다 「지금의 답」 한 줄 — 도구 목록·노트 목록 첫 화면에 질문만 늘어놓고 답이 없었다(4차 화면 판정 Q1).
// 숫자는 각 도구 지면이 읽는 파생 파일과 같은 파일에서 같은 규칙으로 읽는다(지면 숫자는 데이터 파일에만 · 정체성 §2-1).
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";
import { portMonthly } from "./data";

const J = (p: string) => { const f = join(repoRoot(), p); return existsSync(f) ? JSON.parse(readFileSync(f, "utf-8")) : null; };
const sg = (v: number) => (v > 0 ? `+${v}` : v < 0 ? `−${-v}` : `${v}`); // 마이너스 = U+2212
const md = (d: string) => `${Number(d.slice(5, 7))}.${Number(d.slice(8, 10))}`;
export type Answer = { num: string; unit?: string; text: string; neg?: boolean };

export function answers(): Record<string, Answer> {
  const out: Record<string, Answer> = {};
  const pp = J("data/derived/port_pulse.json")?.ports?.Incheon?.judge;
  if (pp) out["/tools/port-pulse.html"] = { num: `${sg(pp.pct)}%`, text: `인천항 하루 입항 ${pp.recent_avg.toFixed(1)}척 · 평소 ${pp.base_avg.toFixed(1)}척 대비(${md(pp.recent_from)}~${md(pp.recent_to)} · 공개된 마지막 7일) — ${pp.word}`, neg: pp.pct < 0 };
  const I = J("data/derived/isochrones.json"), RS = J("data/derived/reach_slots.json");
  if (I) {
    const first = Math.max(0, I.origins.findIndex((o: any) => o.kind === "물류단지")), O = I.origins[first];
    const SL = RS?.slots ?? [{ id: "자유 흐름", k: 1 }], DEF = SL.find((t: any) => t.id === RS?.default) ?? SL[0];
    const TB = RS?.table?.[first]?.[DEF.id], C0 = (TB?.car ?? O.cities) as Record<string, number | null>, W = TB?.within ?? O.cities_within;
    if (C0["서울시청"] != null) out["/tools/delivery-reach.html"] = { num: `${C0["서울시청"]}`, unit: "분", text: `${O.name} → 서울시청(${DEF.id}${DEF.k === 1 ? "" : " 시간 보정"}) · 수도권 ${O.n_cities}곳 가운데 1시간 안 ${W["1h"]}곳` };
  }
  const R = J("data/derived/trade_race.json");
  if (R) { const Y = R.years.filter((y: any) => !y.partial), L = Y[Y.length - 1]; out["/tools/trade-race.html"] = { num: `${Number(L.top_exp.pct).toFixed(1)}%`, text: `${L.y}년 인천 소재 기업 수출 1위 ${L.top_exp.name}의 몫` }; }
  const E = J("data/derived/import_cost.json")?.example;
  if (E) out["/tools/import-cost.html"] = { num: `${sg(E.pct)}%`, text: `1만 달러 물건 원가(부가세 제외) — ${E.ago_weeks}주 전보다 · 이번 주 과세환율 ${E.now.fx.toLocaleString("ko-KR")}원/달러`, neg: E.pct < 0 };
  const C = J("data/derived/chokepoints.json");
  if (C) { const F = C.points.filter((p: any) => p.vs_base_pct != null).sort((a: any, b: any) => a.vs_base_pct - b.vs_base_pct)[0]; if (F) out["/tools/chokepoint.html"] = { num: `${sg(F.vs_base_pct)}%`, text: `${F.ko} 통항 — 2023년 같은 달 대비(${F.asof} 주)`, neg: F.vs_base_pct < 0 }; }
  const V = J("data/derived/vessel_replay.json")?.latest;
  if (V) out["/map/vessels.html"] = { num: `${V.busan_to_incheon}배`, text: `${V.ym} 외항선 입항 — 부산 ${V.busan.toLocaleString("ko-KR")}척 · 인천 ${V.incheon}척` };
  const P = portMonthly(), last = P.series[P.series.length - 1];
  if (last?.yoy != null) out["/notes/port-yoy.html"] = { num: `${sg(last.yoy)}%`, text: `${last.ym} 인천항 컨테이너 ${last.v}천TEU — 작년 같은 달 대비(공표값)`, neg: last.yoy < 0 };
  return out;
}

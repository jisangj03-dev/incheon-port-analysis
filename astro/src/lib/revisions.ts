// 원천 정정 이력(2026-11-02 링크드인 공개 답장의 이행) — tools-build/revisions.py 가 data/revisions.csv(줄) · data/derived/revisions.json(요약)을 쓴다.
// 「방법·출처」에 한 줄로 단다. 0건이어도 「없음」이라 적는다 — 원천 정정을 견주고 있다는 사실 자체가 독자가 알아야 할 방법이다.
// 숫자는 요약 파일·대장 값과 날짜만 쓴다 — 지면 숫자 전수 시험(numbers.spec)이 데이터 파일에 있는 숫자만 허용한다.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";
import { REPO } from "./site";

export const REVISIONS_URL = `${REPO}/blob/main/data/revisions.csv`;

interface Row { 지표: string; 기준기: string; "옛 값": string; "새 값": string; 단위: string; "지표 표시"?: string; "옛 값 표시"?: string; "새 값 표시"?: string; "단위 표시"?: string }
export interface RevSummary { n: number; last: string | null; since: string | null; latest: Row | null; backfilled: number }

export function revSummary(): RevSummary {
  const p = join(repoRoot(), "data/derived/revisions.json");
  if (!existsSync(p)) return { n: 0, last: null, since: null, latest: null, backfilled: 0 };
  const d = JSON.parse(readFileSync(p, "utf-8"));
  return { n: d.n ?? 0, last: d.last ?? null, since: d.since ?? null, latest: d.latest ?? null, backfilled: d.backfilled ?? 0 };
}

const per = (s: string) => /^\d{6}$/.test(s) ? `${s.slice(0, 4)}-${s.slice(4)}` : s; // 202608 → 2026-08
const num = (s: string) => Number(s).toLocaleString("ko-KR");

// head = 「2026-10-21부터 N건 · 최근 감지 YYYY-MM-DD」 또는 「…부터 없음」 · how = 무엇을 하나 · latest = 최근 한 줄 예시
export function revisionLine(): { head: string; how: string; latest: string | null } {
  const S = revSummary();
  const from = S.since ? `${S.since}(자동 갱신 첫 회차)부터 ` : "";
  const head = S.n ? `${from}${S.n}건 · 최근 감지 ${S.last}` : `${from}없음`;
  const how = `기관이 이미 공표한 달의 값을 나중에 고치면(잠정치 → 확정치 등) 지면 숫자도 새 값으로 바뀌고, 대장에 원천·지표·기준월·옛 값·새 값·감지일을 한 줄씩 남긴다. 지면 숫자의 증감 부호(늘었다·줄었다)를 뒤집는 수정은 자동 반영을 멈추고 사람이 문구를 확인한 뒤 반영한다.${S.backfilled ? ` 이 가운데 ${S.backfilled}건은 비교 장치를 넣기 전 회차분이라 지난 기록을 뒤져 나중에 적었다(소급 기록).` : ""}`;
  const L = S.latest;
  // 표시 칸(revisions.py show — 억 원·억 달러로 바꾼 값)이 있으면 그것을, 없으면 원천 단위 그대로
  const latest = L ? `최근: ${L["지표 표시"] ?? L.지표} ${per(L.기준기)} ${L["옛 값 표시"] ?? num(L["옛 값"])} → ${L["새 값 표시"] ?? num(L["새 값"])}${L["단위 표시"] ? "" : " "}${L["단위 표시"] ?? L.단위}` : null; // 표시 단위(억 원)는 숫자에 붙인다
  return { head, how, latest };
}

// 원천 정정 이력(2026-11-02 링크드인 공개 답장의 이행) — tools-build/revisions.py 가 data/revisions.csv(줄) · data/derived/revisions.json(요약)을 쓴다.
// 「방법·출처」에 한 줄로 단다. 0건이어도 「없음」이라 적는다 — 원천 정정을 견주고 있다는 사실 자체가 독자가 알아야 할 방법이다.
// 숫자는 요약 파일(n)·날짜만 쓴다 — 지면 숫자 전수 시험(numbers.spec)이 데이터 파일에 있는 숫자만 허용한다.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";
import { REPO } from "./site";

export const REVISIONS_URL = `${REPO}/blob/main/data/revisions.csv`;

export interface RevSummary { n: number; last: string | null; since: string | null }

export function revSummary(): RevSummary {
  const p = join(repoRoot(), "data/derived/revisions.json");
  if (!existsSync(p)) return { n: 0, last: null, since: null };
  const d = JSON.parse(readFileSync(p, "utf-8"));
  return { n: d.n ?? 0, last: d.last ?? null, since: d.since ?? null };
}

// 한 줄 — 「정정 이력 — 없음」 또는 「정정 이력 — N건 · 마지막 감지 YYYY-MM-DD」 + 무엇을 견주는지
export function revisionLine(): { head: string; how: string } {
  const S = revSummary();
  const head = S.n ? `${S.n}건 · 마지막 감지 ${S.last}` : "없음";
  const how = `자동 갱신이 원천을 다시 받을 때 이미 실은 달의 값이 원천에서 바뀌었는지 견주고, 바뀌면 원천·지표·기준월·옛 값·새 값·감지일을 한 줄씩 남긴다${S.since ? `(${S.since}부터)` : ""}. 정정으로 증감 방향(늘었다·줄었다)이 뒤집히면 자동 반영을 멈추고 사람이 문구를 본다.`;
  return { head, how };
}

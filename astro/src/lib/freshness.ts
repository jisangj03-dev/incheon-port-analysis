// 원천별 신선도(data/derived/freshness.json · tools-build/refresh.py 가 쓴다) — 지면 출처 줄에 「마지막 확인 · 다음 공표 예정」을 붙인다.
// 「다음 공표 예정」은 관측한 공표 주기로 잡은 날이라 「무렵」으로 적는다(기관이 날짜를 약속하지 않는다).
// 확인일이 예정일을 넘겼는데 원천 마지막 기준기가 그대로면 「예정일이 지났으나 그날까지 미공표」 — 빌드 날짜가 아니라 확인일 기준의 사실만 쓴다.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

type Rec = { label: string; ours: string | null; source_latest: string | null; checked: string | null; next_expected: string | null; behind: boolean };
let _f: Record<string, Rec> | null = null;
const all = () => (_f ??= (() => { const p = join(repoRoot(), "data/derived/freshness.json"); return existsSync(p) ? JSON.parse(readFileSync(p, "utf-8")).sources : {}; })());

export function freshRec(id: string): Rec | null { return all()[id] ?? null; }

/** 출처 줄 한 토막 — 원천 여럿이면 가장 이른 「다음 공표 예정」 하나와 가장 이른 확인일을 쓴다. */
export function freshLine(ids: string[]): string | null {
  const rs = ids.map(freshRec).filter(Boolean) as Rec[];
  if (!rs.length) return null;
  const checked = rs.map((r) => r.checked).filter(Boolean).sort()[0] ?? null;
  const next = rs.map((r) => r.next_expected).filter(Boolean).sort()[0] ?? null;
  const late = rs.find((r) => r.checked && r.next_expected && r.checked > r.next_expected);
  const parts: string[] = [];
  if (checked) parts.push(`마지막 확인 ${checked}`);
  if (late) parts.push(`다음 공표 예정 ${late.next_expected} 무렵이었으나 ${late.checked} 확인 때 아직 미공표`);
  else if (next) parts.push(`다음 공표 예정 ${next} 무렵`);
  return parts.join(" · ") || null;
}

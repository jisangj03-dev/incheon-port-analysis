// 원천별 신선도(data/derived/freshness.json · tools-build/refresh.py 가 쓴다) — 지면 출처 줄에 「원천 확인 · 다음 공표 예정」을 붙인다.
// 「다음 공표 예정」은 관측한 공표 주기로 잡은 날이라 「무렵」으로 적는다(기관이 날짜를 약속하지 않는다).
// 확인일이 예정일을 넘겼는데 원천 마지막 기준기가 그대로면 「예정일이 지났으나 그날까지 미공표」 — 빌드 날짜가 아니라 확인일 기준의 사실만 쓴다.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

type Rec = { label: string; ours: string | null; source_latest: string | null; checked: string | null; next_expected: string | null; behind: boolean };
let _f: Record<string, Rec> | null = null;
const all = () => (_f ??= (() => { const p = join(repoRoot(), "data/derived/freshness.json"); return existsSync(p) ? JSON.parse(readFileSync(p, "utf-8")).sources : {}; })());

export function freshRec(id: string): Rec | null { return all()[id] ?? null; }

// 출처 줄에 쓰는 짧은 이름 — 원천이 여럿인 지면에서 「다음 공표 예정」이 어느 자료의 것인지 갈라 적는다(16차 판정 경미 3·8).
const SHORT: Record<string, string> = {
  "kcs-porttrade": "관세청", "kcs-nation": "관세청", "kcs-sido-item": "관세청", "kcs-sido-sudo": "관세청", "kcs-fx": "관세환율", "kosis-retail": "KOSIS",
  "kobc-kcci": "KCCI", "imf-portwatch": "PortWatch", "mof-vessel": "해양수산부", "mof-incheon-port-stats": "인천해수청", "iiac-route-cargo": "인천공항공사",
};

/** 출처 줄 한 토막 — 「원천 확인 날짜 · 다음 공표 예정(주기 추정) 원천별 날짜 무렵」. 「마지막 갱신」(자료가 바뀐 날)과 다른 날이다. */
export function freshLine(ids: string[]): string | null {
  const rs = ids.map((id) => [id, freshRec(id)] as const).filter((x) => x[1]) as [string, Rec][];
  if (!rs.length) return null;
  const checked = rs.map(([, r]) => r.checked).filter(Boolean).sort()[0] ?? null;
  const parts: string[] = [];
  if (checked) parts.push(`원천 확인 ${checked}`);
  const late = rs.filter(([, r]) => r.checked && r.next_expected && r.checked > r.next_expected);
  const next = new Map<string, string>();
  for (const [id, r] of rs) {
    if (!r.next_expected || late.some(([i]) => i === id)) continue;
    const k = SHORT[id] ?? r.label;
    if (!next.has(k) || r.next_expected < next.get(k)!) next.set(k, r.next_expected);
  }
  const nx = [...next].sort((a, b) => a[1].localeCompare(b[1])).map(([k, d]) => `${k} ${d}`);
  if (nx.length) parts.push(`다음 공표 예정(지난 주기로 본 추정) ${nx.join(" · ")} 무렵`);
  for (const [id, r] of late) parts.push(`${SHORT[id] ?? r.label} 공표 예정 ${r.next_expected} 무렵이었으나 ${r.checked} 확인 때 아직 미공표`);
  return parts.join(" · ") || null;
}

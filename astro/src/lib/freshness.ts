// 원천별 신선도(data/derived/freshness.json · tools-build/refresh.py 가 쓴다) — 지면 출처 줄에 「원천 확인 · 다음 공표 예정」을 붙인다.
// 「다음 공표 예정」은 관측한 공표 주기로 잡은 날이라 「무렵」으로 적는다(기관이 날짜를 약속하지 않는다).
// 확인일이 예정일을 넘겼는데 원천 마지막 기준기가 그대로면 「예정일이 지났으나 그날까지 미공표」 — 빌드 날짜가 아니라 확인일 기준의 사실만 쓴다.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

type Rec = { label: string; ours: string | null; source_latest: string | null; checked: string | null; next_expected: string | null; behind: boolean; delayed?: boolean; delay_reason?: string | null };
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

/** [2026-10-22 갱신 무인화 ④] 「갱신 지연」 한 줄 — 원천 받기가 끊겼거나(키·형식·이틀 넘는 실패) 확인이 주기 한도를 넘었거나 지면이 원천보다 뒤처진 원천.
 *  출처 줄 접기와 상관없이 늘 보인다(지난 숫자를 새것처럼 읽지 않게). refresh.py judge() 가 정하고 시험 freshness.spec 이 지면에 보이는지 본다. */
export function delayLine(ids: string[]): string | null {
  const rs = ids.map((id) => freshRec(id)).filter((r): r is Rec => !!r && !!r.delayed);
  if (!rs.length) return null;
  return `갱신 지연 — ${rs.map((r) => `${SHORT[ids.find((i) => freshRec(i) === r)!] ?? r.label}: ${r.delay_reason}${r.ours ? ` · 이 지면 숫자는 ${r.ours} 기준` : ""}`).join(" / ")}`;
}

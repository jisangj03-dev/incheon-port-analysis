// 원천별 신선도(data/derived/freshness.json · tools-build/refresh.py 가 쓴다) — 지면 출처 줄에 「원천 확인 · 다음 공표 예정」을 붙인다.
// 「다음 공표 예정」은 관측한 공표 주기로 잡은 날이라 「무렵」으로 적는다(기관이 날짜를 약속하지 않는다).
// 확인일이 예정일을 넘겼는데 원천 마지막 기준기가 그대로면 「예정일이 지났으나 그날까지 미공표」 — 빌드 날짜가 아니라 확인일 기준의 사실만 쓴다.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

type Rec = { label: string; ours: string | null; source_latest: string | null; checked: string | null; next_expected: string | null; behind: boolean; delayed?: boolean; delay_reason?: string | null; fail_kind?: string | null; fail_days?: number; max_age?: number };
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
  const checked = rs.filter(([, r]) => !r.fail_kind).map(([, r]) => r.checked).filter(Boolean).sort()[0] ?? null; // 받기가 끊긴 원천의 확인일은 「갱신 지연」 줄이 따로 적는다(10/22 화면 판정 — 한 날짜가 끊긴 원천까지 덮어 읽혔다)
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

/** [2026-10-22 갱신 무인화 ④] 원천이 끊겼거나 뒤처졌을 때의 한 줄 — 출처 줄 접기와 상관없이 늘 보인다. 켜는 조건은 refresh.py judge()(delayed).
 *  말은 원천 하나로 좁힌다(10/22 화면 판정 중대: 「이 지면 숫자는 …기준」이 지면 전체의 기준일로 읽혔다) ·
 *  아직 다음 공표 전이면 「자동 받기 실패 — 다음 공표분부터 늦을 수 있음」, 지났거나 뒤처졌으면 「갱신 지연」(늦은 것이 없는데 지연이라 쓰지 않는다).
 *  today = 빌드 날(refresh 가 그날 다시 빌드한다). */
export function delayLine(ids: string[], today = new Date().toISOString().slice(0, 10)): string | null {
  const parts: string[] = [];
  let late = false;
  for (const id of ids) {
    const r = freshRec(id);
    if (!r || !r.delayed) continue;
    const name = SHORT[id] ?? r.label;
    const basis = r.ours ? `${name} 숫자는 ${r.ours}${/^\d{4}-\d{2}-\d{2}$/.test(r.ours) ? " 주" : ""} 기준` : `${name} 숫자`;
    const why = r.behind ? `원천은 ${r.source_latest} 까지 냈으나 아직 반영 전`
      : r.fail_kind === "auth" ? "자동 받기가 막힘(이용 인증)"
      : r.fail_kind === "format" ? "원천 자료 형식이 바뀌어 자동 받기가 멈춤"
      : r.fail_kind ? `자동 받기 실패 ${r.fail_days ?? 1}일째`
      : r.next_expected && today > r.next_expected ? `공표 예정 ${r.next_expected} 무렵이 지났는데 새 자료를 아직 못 받음(마지막 확인 ${r.checked ?? "—"})`
      : `마지막 확인 ${r.checked ?? "—"} — 확인 주기를 넘김`;
    const due = r.next_expected && today > r.next_expected;
    if (r.behind || due || !r.fail_kind) { late = true; parts.push(`${basis} — ${why}${due && r.fail_kind ? ` · 다음 공표 예정 ${r.next_expected} 무렵이 지났다` : ""}`); }
    else parts.push(`${name} ${why} — 지금 숫자(${r.ours ?? "—"}${/^\d{4}-\d{2}-\d{2}$/.test(r.ours ?? "") ? " 주" : ""})는 최신이고, 다음 공표분(${r.next_expected} 무렵)부터 늦을 수 있다`);
  }
  if (!parts.length) return null;
  return `${late ? "갱신 지연" : "자동 받기 실패"} · ${parts.join(" / ")}`;
}

// 출처 대장(data/sources.json) 한 줄 — 지면의 신뢰 꼬리가 「출처 · 이용허락 · 공공누리 유형」을 대장 그대로 옮긴다(기준 16).
// 유형을 확인 못 한 것은 대장이 「미확인」이라 적고, 지면도 그대로 적는다(추측으로 채우지 않는다).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

type Src = { id: string; name: string; owner: string; license: string; kogl: string };
let _all: Src[] | null = null;
export function source(id: string): Src | null {
  _all ??= JSON.parse(readFileSync(join(repoRoot(), "data/sources.json"), "utf-8")).sources;
  return _all!.find((s) => s.id === id) || null;
}
/** 공개면 문구 — 출처 대장의 작업 기록 말(운영자 호칭·세션·워크플로 이름·저장소 경로)을 독자 말로 바꾼다(화면 판정 10/20 Q8).
 *  대장 원문은 저장소에 그대로 남는다(확인 경위의 정본) — 지면만 걸러 보인다. */
// 작업 기록 말 — 지면에 보이면 독자가 작업 로그를 읽게 된다(2026-10-20 화면 판정·사실 대조)
const INTERNAL = /운영자|GW\b|GW 묶음|HTTP \d{3}|=N\b|\bget[A-Z]\w+|git 기록|따라가기|키로 |FACTS\.md|Actions|워크플로|workflow|세션|선커밋|판정 v\d|\.ya?ml\b|\.py\b|\.mjs\b|크론|운영자 손|_KEY|비밀|앱 \d{4,}|(?:data|analysis|tools-build|docs)\/|api_probe|terms-check|ops_stats|kogl-check|blob|\bPASS\b|\bFAIL\b|→ 자동|사실 대조|판단 대기|주의 ⑥/;
export function pub(t: string): string {
  let x = String(t ?? "").replace(/선장님/g, "운영자");
  // 괄호 안이 작업 기록이면 괄호째 뺀다(안쪽 괄호부터)
  for (let i = 0; i < 4; i++) x = x.replace(/\s*[(（]([^()（）]*)[)）]/g, (m, inner) => (INTERNAL.test(inner) ? "" : m));
  // 「 · 」·「 — 」로 나뉜 조각 가운데 작업 기록인 것은 뺀다
  // 괄호·낫표 안의 「 · 」에서는 가르지 않는다(Trust 와 같은 규칙 — 「…P2(「사업」」처럼 괄호가 깨졌다 · 2차 사실 대조)
  const top = (t: string, sep: string) => { const out: string[] = []; let cur = "", d = 0; for (const p of t.split(sep)) { cur = cur ? cur + sep + p : p; d += (p.match(/[(「（]/g) || []).length - (p.match(/[)」）]/g) || []).length; if (d <= 0) { out.push(cur); cur = ""; d = 0; } } if (cur) out.push(cur); return out; };
  x = top(x, " · ").map((seg) => top(seg, " — ").filter((p) => !INTERNAL.test(p)).join(" — ")).filter((seg) => seg.trim() && !INTERNAL.test(seg)).join(" · ");
  return x.replace(/\s*\[미확인\]/g, " — 미확인").replace(/\s{2,}/g, " ").replace(/\s+([,.)])/g, "$1").trim();
}
/** 신뢰 꼬리용 한 줄 — 「기관 · 이름 · 공공누리 유형」 */
export function sourceLine(id: string): string {
  const s = source(id);
  if (!s) return `출처 대장에 없음(${id})`;
  const kogl = /^해당 없음/.test(s.kogl) ? s.license : `공공누리 ${s.kogl === "미확인" ? "유형 미확인" : s.kogl} · ${s.license}`;
  return pub(`${s.owner} 「${s.name}」 · ${kogl}`);
}

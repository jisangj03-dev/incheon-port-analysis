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
export function pub(t: string): string {
  return String(t ?? "")
    .replace(/선장님/g, "운영자")
    .replace(/세션이 /g, "").replace(/세션 —/g, "운영 측 —").replace(/세션에서/g, "작업 환경에서")
    .replace(/[A-Za-z-]+ 워크플로가/g, "자동 화면 점검이").replace(/[A-Za-z-]+ 워크플로/g, "자동 화면 점검")
    .replace(/\s*\((?:data|analysis|tools-build|docs)\/[^)]*\)/g, "")
    .replace(/(?:data|analysis|tools-build|docs)\/[\w./-]+/g, "저장소 기록")
    .replace(/\s{2,}/g, " ").trim();
}
/** 신뢰 꼬리용 한 줄 — 「기관 · 이름 · 공공누리 유형」 */
export function sourceLine(id: string): string {
  const s = source(id);
  if (!s) return `출처 대장에 없음(${id})`;
  const kogl = /^해당 없음/.test(s.kogl) ? s.license : `공공누리 ${s.kogl === "미확인" ? "유형 미확인" : s.kogl} · ${s.license}`;
  return pub(`${s.owner} 「${s.name}」 · ${kogl}`);
}

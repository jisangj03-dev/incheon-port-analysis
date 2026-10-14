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
/** 신뢰 꼬리용 한 줄 — 「기관 · 이름 · 공공누리 유형」 */
export function sourceLine(id: string): string {
  const s = source(id);
  if (!s) return `출처 대장에 없음(${id})`;
  const kogl = /^해당 없음/.test(s.kogl) ? s.license : `공공누리 ${s.kogl === "미확인" ? "유형 미확인" : s.kogl} · ${s.license}`;
  return `${s.owner} 「${s.name}」 · ${kogl}`;
}

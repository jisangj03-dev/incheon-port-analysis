// 운영자 공개 프로필 — data/profile.json 한 곳(실명이 사는 유일한 파일 · check_private NAME_HOME). 지면은 여기서만 읽는다.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

export type Profile = {
  name: string; role: string; affiliation: string; credentials: string[]; credentials_note?: string;
  education?: { school: string; major: string; status: string }[];
  writing: { title: string; outlet?: string; when: string; url: string }[];
  contact: { linkedin: string; mail: { user: string; domain: string } };
};
let _p: Profile | null = null;
export function profile(): Profile {
  return (_p ??= JSON.parse(readFileSync(join(repoRoot(), "data/profile.json"), "utf-8")));
}
/** AI 산출물 표기(정체성 §2-4 · 지침 §2.2-4) — 「〈실명〉 검수」는 **검수 기록(docs/검수기록.md)에 그 지면 줄이 있을 때만**.
 *  [2026-10-20 독립 사실 대조] 기록이 report_07 한 줄뿐인데 공개 지면 아홉에 「〈실명〉 검수」가 붙어 있었다 → 기록이 없는 지면은 「AI 정리」만.
 *  지면 주소(예: "/sim/forecast.html")나 문서 이름을 주면 그 이름이 기록 표의 「문서」 칸에 있는지 본다. */
let _rev: string | null = null;
export function reviewed(key?: string): boolean {
  if (!key) return false;
  _rev ??= (() => { try { return readFileSync(join(repoRoot(), "docs/검수기록.md"), "utf-8"); } catch { return ""; } })();
  const k = key.replace(/^\//, "").replace(/\.html$/, "");
  // 칸 = 검수한 파일 이름 — 부분 문자열이 아니라 같은 이름(또는 경로 끝)으로만 맞춘다(「index」가 tools/index 줄에 걸려 홈에 실명이 뜨지 않게 · 2026-10-22 25차 사실 대조)
  return _rev.split("\n").some((l) => { if (!l.startsWith("| 20")) return false; const c = (l.split("|")[2] || "").trim().replace(/\.(md|html)$/, ""); return c === k || c.endsWith(`/${k}`) || k.endsWith(`/${c}`); });
}
export const aiMark = (key?: string) => (reviewed(key) ? `AI 정리 · ${profile().name} 검수` : "AI 정리");

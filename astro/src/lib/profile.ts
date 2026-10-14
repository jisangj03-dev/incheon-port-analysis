// 운영자 공개 프로필 — data/profile.json 한 곳(실명이 사는 유일한 파일 · check_private NAME_HOME). 지면은 여기서만 읽는다.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "./content";

export type Profile = {
  name: string; role: string; affiliation: string; credentials: string[]; credentials_note?: string;
  education?: { school: string; major: string; status: string }[];
  writing: { title: string; when: string; url: string }[];
  contact: { linkedin: string; mail: { user: string; domain: string } };
};
let _p: Profile | null = null;
export function profile(): Profile {
  return (_p ??= JSON.parse(readFileSync(join(repoRoot(), "data/profile.json"), "utf-8")));
}
/** AI 산출물 표기 — 「AI 정리 · 〈실명〉 검수」(정체성 §2-4) */
export const aiMark = () => `AI 정리 · ${profile().name} 검수`;

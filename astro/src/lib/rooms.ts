// 콘텐츠 목록 하나(data/rooms.json) → 홈·노트가 자동 배치하는 형태로. 새 콘텐츠는 목록에 한 줄 + 장면 부품 하나.
// 노트 제목·날짜는 원문에서 자동(보고서 = 첫 # 제목 · 날짜 = git 기록). 단계는 목록이 든다(사람이 정한다).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";
import { repoRoot, lastUpdated, title } from "./content";

export type Stage = "초안" | "갱신 중" | "정본";
export const STAGES: Stage[] = ["초안", "갱신 중", "정본"];
export type Note = { id: string; title: string; stage: Stage; href: string; planted: string; tended: string; links: string[]; backlinks: string[] };

const raw = () => JSON.parse(readFileSync(join(repoRoot(), "data/rooms.json"), "utf-8"));

/** 파일이 처음 커밋된 날(심은 날). git 이 없으면 마지막 갱신일. */
function planted(rel: string): string {
  try {
    const out = execFileSync("git", ["log", "--diff-filter=A", "--follow", "--format=%cs", "--", rel], { cwd: repoRoot(), encoding: "utf-8" }).trim().split("\n");
    return out[out.length - 1] || lastUpdated(rel);
  } catch { return lastUpdated(rel); }
}

export function rooms() { return raw().rooms as { id: string; kind: string; title: string; lead: string; href: string }[]; }
export function route() { return raw().route; }

export function notes(): Note[] {
  const list = raw().notes as any[];
  const out: Note[] = list.map((n) => {
    const rel = n.file || `reports/${n.id}.md`;
    const t = n.title || title(readFileSync(join(repoRoot(), rel), "utf-8"));
    return { id: n.id, title: t, stage: n.stage, href: n.href || `/reports/${n.id}.html`, planted: planted(rel), tended: lastUpdated(rel), links: n.links || [], backlinks: [] };
  });
  // 되짚는 링크 — 이 노트를 가리키는 노트들(디지털 가든의 「이 노트로 오는 길」)
  for (const a of out) for (const id of a.links) out.find((b) => b.id === id)?.backlinks.push(a.id);
  return out.sort((a, b) => (a.tended < b.tended ? 1 : a.tended > b.tended ? -1 : 0));
}

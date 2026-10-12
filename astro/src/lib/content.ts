// 발행본 마크다운에서 지면 머리에 쓸 것을 뽑는다 — 본문은 바꾸지 않는다(발행본 불변 · 지침 §3-11).
import { execFileSync } from "node:child_process";
import { statSync } from "node:fs";
import { resolve } from "node:path";

const plain = (s: string) => s.replace(/\*\*|__|`/g, "").replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").trim();

export function title(body: string): string {
  const m = body.match(/^#\s+(.+)$/m);
  return m ? plain(m[1]) : "";
}
/** 「보고서 #01 — 제목」·「#04 제목」 두 꼴 → { no: "#01", text: "제목" } */
export function splitTitle(t: string): { no: string | null; text: string } {
  const m = t.match(/^\s*(?:보고서\s*)?(#\d+)\s*(?:[—–-]\s*)?(.+)$/);
  return m ? { no: m[1], text: m[2].trim() } : { no: null, text: t };
}
export function conclusion(body: string): string {
  const m = body.match(/\*\*한 줄 결론\*\*\s*[:：]\s*(.+)$/m);
  return m ? plain(m[1]) : "";
}
export function written(body: string): string {
  const m = body.match(/\*\*작성일\*\*\s*[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})/);
  return m ? m[1] : "";
}
export function firstImage(body: string): { src: string; alt: string } | null {
  const m = body.match(/!\[([^\]]*)\]\(([^)\s]+)\)/);
  return m ? { alt: plain(m[1]), src: m[2] } : null;
}
/** 제목 다음 첫 문단(인용 포함) — 결론 줄이 없는 정리형 지면의 설명 대신. */
export function lede(body: string): string {
  for (const raw of body.split(/\n\s*\n/).slice(1)) {
    const t = raw.trim();
    if (!t || t.startsWith("#") || t.startsWith("|") || t.startsWith("---")) continue;
    if (/^[-*]\s/.test(t) && !t.startsWith("> ")) continue;
    return plain(t.replace(/^>\s?/gm, "").replace(/\s+/g, " "));
  }
  return "";
}
export function description(body: string, fallback: string): string {
  const c = conclusion(body) || lede(body);
  // 결론이 짧으면(정리형 스냅샷) 제목을 앞에 붙인다 — 검색 결과에서 무슨 지면인지 보이게.
  const s = !c ? fallback : c.length < 40 ? `${fallback} — ${c}` : c;
  return s.length > 155 ? `${s.slice(0, 152)}…` : s;
}

let _repo = "";
export function repoRoot(): string {
  if (_repo) return _repo;
  try {
    _repo = execFileSync("git", ["rev-parse", "--show-toplevel"], { encoding: "utf-8" }).trim();
  } catch {
    _repo = process.cwd();
  }
  return _repo;
}

/** 파일의 마지막 커밋 날짜(YYYY-MM-DD) — 「마지막 갱신일」(기준 14). git 이 없으면 파일 시각. */
export function lastUpdated(relFromRepo: string): string {
  const repo = repoRoot();
  const file = resolve(repo, relFromRepo);
  try {
    const out = execFileSync("git", ["log", "-1", "--format=%cs", "--", file], { cwd: repo, encoding: "utf-8" }).trim();
    if (out) return out;
  } catch {}
  try {
    return statSync(file).mtime.toISOString().slice(0, 10);
  } catch {
    return "";
  }
}

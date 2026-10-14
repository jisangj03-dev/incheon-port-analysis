// 세션 시작 컨텍스트 근사치 — 기준 25(개편 전후 비교).
// /context 는 세션 안의 슬래시 명령이라 스크립트가 못 친다. 대신 **세션이 시작할 때 자동으로 실리는 저장소 몫**을 잰다:
//   ① CLAUDE.md 전문 ② .claude/skills/*/SKILL.md 의 front matter(name·description — 세션은 설명만 싣는다) ③ .mcp.json 서버 수.
// 사용자 설정·플러그인·전역 MCP(Claude.ai 커넥터)는 저장소 밖이라 여기서 못 잰다 — 그 몫은 /context 로만 보인다.
// 토큰은 글자 수 근사(한글 1자 ≈ 1토큰, 그 밖 4자 ≈ 1토큰)다. 비교용이지 청구 토큰이 아니다.
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../..", import.meta.url).pathname;
const est = (s) => {
  const hangul = (s.match(/[ㄱ-ㆎ가-힣]/g) || []).length;
  return Math.round(hangul + (s.length - hangul) / 4);
};
const rows = [];
const claude = readFileSync(join(root, "CLAUDE.md"), "utf-8");
rows.push(["CLAUDE.md", Buffer.byteLength(claude), est(claude)]);
const sk = join(root, ".claude/skills");
let skills = 0;
for (const d of readdirSync(sk)) {
  const f = join(sk, d, "SKILL.md");
  if (!existsSync(f) || !statSync(join(sk, d)).isDirectory()) continue;
  skills++;
  const m = readFileSync(f, "utf-8").match(/^---\n([\s\S]*?)\n---/);
  const fm = m ? m[1] : "";
  rows.push([`skill:${d} (front matter)`, Buffer.byteLength(fm), est(fm)]);
}
let mcp = 0;
const mf = join(root, ".mcp.json");
if (existsSync(mf)) mcp = Object.keys(JSON.parse(readFileSync(mf, "utf-8")).mcpServers || {}).length;
const total = rows.reduce((a, r) => a + r[2], 0);
console.log("| 항목 | 바이트 | 근사 토큰 |\n|---|---:|---:|");
for (const r of rows) console.log(`| ${r[0]} | ${r[1]} | ${r[2]} |`);
console.log(`| **합** | ${rows.reduce((a, r) => a + r[1], 0)} | **${total}** |`);
console.log(`\n스킬 ${skills}개(상한 10) · .mcp.json 서버 ${mcp}개(상한 3)`);
if (skills > 10 || mcp > 3) process.exit(1);

// 공개 사이트 실물 점검(A-7) — Actions 에서만 돈다. 결과는 마크다운 한 장(표준 출력)으로.
//  ① 지면 응답(200/404) ② PMTiles range 요청 206(판정 v2 주의 ③) ③ Cloudflare 비컨 스니펫 존재 ④ Lighthouse 모바일(실물)
//  Lighthouse 「권장」이 왜 96 이었는지(로컬 서버 비컨 오류 추정)를 실물에서 가른다 — 감점 항목 이름을 같이 적는다.
import { readFileSync, mkdirSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";

const cfg = JSON.parse(readFileSync("tools-build/live-check.json", "utf-8"));
const L = [`# 실물 점검 — ${new Date().toISOString().slice(0, 16)}Z`, "", `대상: ${cfg.base} · 도구: curl·Lighthouse 13.5.0(모바일 기본) · GitHub Actions`, ""];
L.push("## ① 지면 응답", "", "| 지면 | 상태 | 형식 |", "|---|---|---|");
for (const p of cfg.pages) {
  const r = await fetch(encodeURI(cfg.base + p), { redirect: "manual" });
  L.push(`| \`${p}\` | ${r.status} | ${(r.headers.get("content-type") || "").split(";")[0]} |`);
}
L.push("", "## ② PMTiles range 요청", "");
{
  const r = await fetch(cfg.base + cfg.range, { headers: { Range: "bytes=0-511" } });
  const b = new Uint8Array(await r.arrayBuffer());
  const magic = String.fromCharCode(...b.slice(0, 7));
  L.push(`- \`Range: bytes=0-511\` → **${r.status}** · 받은 바이트 ${b.length} · Content-Range \`${r.headers.get("content-range")}\` · 머리 \`${magic}\`(PMTiles 표지)`);
}
L.push("", "## ③ Cloudflare 비컨", "");
{
  const html = await (await fetch(cfg.base + "/")).text();
  L.push(`- 홈 HTML 에 비컨 스크립트: **${/static\.cloudflareinsights\.com\/beacon\.min\.js/.test(html) ? "있다" : "없다"}** · 토큰 표지 ${/data-cf-beacon/.test(html) ? "있다" : "없다"}`);
}
// ⑤ 홈 실물 화면(2026-10-22 · 첫 화면 정체성 배포 확인) — cfg.shots 의 폭마다 첫 화면을 찍고(띠 둘째·셋째 그림 포함) 실명이 홈 원문에 0인지 잰다
if (cfg.shots?.length) {
  const { chromium } = await import("@playwright/test");
  mkdirSync("docs/live-shots", { recursive: true });
  const P = JSON.parse(readFileSync("data/profile.json", "utf-8"));
  const html = await (await fetch(cfg.base + "/")).text();
  L.push("", "## ⑤ 홈 실물 화면", "", `- 홈 원문 실명(profile.json name) 등장: **${html.split(P.name).length - 1}회** · 「수도권 물류·무역·유통을」 제목: ${html.includes("수도권 물류·무역·유통을") ? "있음" : "없음"}`);
  const b = await chromium.launch();
  for (const [w, h] of cfg.shots) {
    const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500, deviceScaleFactor: w < 500 ? 2 : 1 });
    const pg = await ctx.newPage();
    await pg.goto(cfg.base + "/", { waitUntil: "load" }); await pg.waitForTimeout(2500);
    for (const k of [0, 1, 2]) {
      if (k) { await pg.evaluate((k) => window.__shots?.show(k), k); await pg.waitForTimeout(1500); }
      const f = `docs/live-shots/home--${w}x${h}${k ? `-shot${k + 1}` : ""}.png`;
      await pg.screenshot({ path: f }); L.push(`- \`${f}\``);
    }
    await ctx.close();
  }
  await b.close();
}
L.push("", "## ④ Lighthouse 모바일(실물)", "", "| 지면 | 성능 | 접근성 | 권장 | SEO | 권장 감점 항목 |", "|---|---|---|---|---|---|");
mkdirSync("lighthouse-live", { recursive: true });
for (const p of cfg.lighthouse) {
  const out = `lighthouse-live/${p.replace(/[^a-z0-9]+/gi, "_") || "home"}.json`;
  spawnSync("npx", ["lighthouse", cfg.base + p, "--quiet", "--output=json", `--output-path=${out}`, "--chrome-flags=--headless=new --no-sandbox"], { stdio: "inherit" });
  if (!existsSync(out)) { L.push(`| \`${p}\` | 실행 실패 | | | | |`); continue; }
  const rep = JSON.parse(readFileSync(out, "utf-8"));
  const s = (k) => Math.round((rep.categories[k]?.score ?? NaN) * 100);
  const bp = rep.categories["best-practices"].auditRefs.filter((a) => rep.audits[a.id].score !== null && rep.audits[a.id].score < 1).map((a) => a.id);
  L.push(`| \`${p}\` | ${s("performance")} | ${s("accessibility")} | ${s("best-practices")} | ${s("seo")} | ${bp.join(", ") || "—"} |`);
  const con = rep.audits["errors-in-console"]?.details?.items || [];
  if (con.length) L.push(`|  | 콘솔 오류: ${con.map((c) => String(c.description || c.source || "").slice(0, 80).replace(/\|/g, "/")).join(" · ")} | | | | |`);
}
console.log(L.join("\n"));

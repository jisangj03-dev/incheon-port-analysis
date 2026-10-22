// 공개 사이트 실물 점검(A-7) — Actions 에서만 돈다. 결과는 마크다운 한 장(표준 출력)으로.
//  ① 지면 응답(200/404) ② PMTiles range 요청 206(판정 v2 주의 ③) ③ Cloudflare 비컨 스니펫 존재 ④ Lighthouse 모바일(실물)
//  Lighthouse 「권장」이 왜 96 이었는지(로컬 서버 비컨 오류 추정)를 실물에서 가른다 — 감점 항목 이름을 같이 적는다.
//  [2026-10-22 갱신 무인화 ⑤] 주 1회 예약 실행 — ⑤ 실제 브라우저 외부 요청 0 · ⑥ 링크 전수(안쪽 · 바깥 출처) · ④ 성능·접근성 문턱(cfg.min).
//   어긋난 것은 live-check-fail.txt 에 한 줄씩 — 워크플로가 자동경보 이슈로 올린다(봇 차단 403·429 는 「확인 불가」로 따로 · 경보 아님).
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";

const cfg = JSON.parse(readFileSync("tools-build/live-check.json", "utf-8"));
const FAIL = []; // 사람이 볼 것 — 끝에 live-check-fail.txt
const L = [`# 실물 점검 — ${new Date().toISOString().slice(0, 16)}Z`, "", `대상: ${cfg.base} · 도구: curl·Lighthouse 13.5.0(모바일 기본) · GitHub Actions`, ""];
L.push("## ① 지면 응답", "", "| 지면 | 상태 | 형식 |", "|---|---|---|");
for (const p of cfg.pages) {
  const r = await fetch(encodeURI(cfg.base + p), { redirect: "manual" });
  L.push(`| \`${p}\` | ${r.status} | ${(r.headers.get("content-type") || "").split(";")[0]} |`);
  const want = /no-such-page/.test(p) ? 404 : [200, 301, 302];
  if (!(Array.isArray(want) ? want.includes(r.status) : r.status === want)) FAIL.push(`지면 응답 ${p} → ${r.status}`);
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
  for (const [k, m] of Object.entries(cfg.min || {})) if (!(s(k) >= m)) FAIL.push(`Lighthouse ${p} ${k} ${s(k)} < ${m}`);
  const con = rep.audits["errors-in-console"]?.details?.items || [];
  if (con.length) L.push(`|  | 콘솔 오류: ${con.map((c) => String(c.description || c.source || "").slice(0, 80).replace(/\|/g, "/")).join(" · ")} | | | | |`);
}
// ⑤ 실제 브라우저로 열기 — 지면마다 상태 · 화면 오류 · 외부 요청(자기 호스트 밖 · Cloudflare 비컨 한 곳만 예외)
if (cfg.open?.length) {
  const { chromium } = await import("@playwright/test");
  const br = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
  const own = new URL(cfg.base).host, okHost = (h) => h === own || /(^|\.)cloudflareinsights\.com$/.test(h);
  L.push("", "## ⑤ 실제 브라우저로 열기(외부 요청 0 · Cloudflare 비컨 예외)", "", "| 지면 | 상태 | 화면 오류 | 외부 요청(예외 밖) | Cloudflare |", "|---|---|---|---|---|");
  for (const p of cfg.open) {
    const pg = await br.newPage({ viewport: { width: 1440, height: 900 } });
    const ext = new Set(), errs = []; let cf = 0;
    pg.on("request", (r) => { try { const h = new URL(r.url()).host; if (!h) return; if (/cloudflareinsights\.com$/.test(h)) cf++; else if (!okHost(h)) ext.add(h); } catch {} });
    pg.on("pageerror", (e) => errs.push(String(e.message || e).slice(0, 80)));
    let st = "—";
    try { const r = await pg.goto(encodeURI(cfg.base + p), { waitUntil: "load", timeout: 60000 }); st = r ? r.status() : "—"; await pg.waitForTimeout(4000); } catch (e) { st = "열기 실패: " + String(e.message).slice(0, 60); }
    L.push(`| \`${p}\` | ${st} | ${errs.length ? errs.join(" / ").replace(/\|/g, "/") : "0"} | ${ext.size ? [...ext].join(", ") : "0"} | ${cf ? "있음" : "없음"} |`);
    if (ext.size) FAIL.push(`외부 요청 ${p}: ${[...ext].join(", ")}`);
    if (errs.length) FAIL.push(`화면 오류 ${p}: ${errs[0]}`);
    if (st !== 200) FAIL.push(`브라우저 열기 ${p}: ${st}`);
    await pg.close();
  }
  await br.close();
}
// ⑥ 링크 전수 — 열어 본 지면의 <a href> 전부. 안쪽(자기 사이트)은 200 이어야 하고, 바깥 출처는 4xx·5xx 면 깨짐(봇 차단 401·403·429·999 는 「확인 불가」)
if (cfg.open?.length) {
  const seen = new Map(), BLOCK = [401, 403, 405, 429, 999];
  const status = async (u) => {
    if (seen.has(u)) return seen.get(u);
    let st = "오류";
    for (const m of ["HEAD", "GET"]) {
      try { const r = await fetch(u, { method: m, redirect: "follow", signal: AbortSignal.timeout(20000), headers: { "user-agent": "Mozilla/5.0 (compatible; cheuksim-linkcheck/1.0; weekly)" } }); st = r.status; if (r.status < 400 || m === "GET") break; } catch (e) { st = "연결 실패"; }
    }
    seen.set(u, st); return st;
  };
  const broken = [], unknown = [];
  for (const p of cfg.open) {
    const html = await (await fetch(encodeURI(cfg.base + p))).text();
    const hrefs = [...html.matchAll(/<a\b[^>]*\bhref="([^"#][^"]*)"/g)].map((m) => m[1].replace(/&amp;/g, "&")).filter((h) => !/^(mailto|tel|javascript):/.test(h));
    for (const h of new Set(hrefs)) {
      const u = new URL(h, cfg.base + p).href.split("#")[0];
      const st = await status(u);
      const inside = u.startsWith(cfg.base) || new URL(u).host === new URL(cfg.base).host;
      if (st === 200 || (typeof st === "number" && st < 400)) continue;
      if (!inside && BLOCK.includes(st)) unknown.push(`${u} (${st})`);
      else broken.push(`${p} → ${u} (${st})`);
    }
  }
  L.push("", "## ⑥ 링크 전수", "", `- 검사한 주소 ${seen.size}개 · 깨짐 **${broken.length}** · 확인 불가(봇 차단) ${unknown.length}`);
  for (const b of broken) { L.push(`  - 깨짐: ${b}`); FAIL.push(`링크 깨짐 ${b}`); }
  for (const u of [...new Set(unknown)]) L.push(`  - 확인 불가: ${u}`);
}
L.push("", `## 판정 — 어긋남 ${FAIL.length}`, "", ...(FAIL.length ? FAIL.map((f) => `- ${f}`) : ["- 없음"]));
writeFileSync("live-check-fail.txt", FAIL.join("\n"));
console.log(L.join("\n"));

// 공개 사이트 실물 점검(A-7) — Actions 에서만 돈다. 결과는 마크다운 한 장(표준 출력)으로.
//  ⑥ [2026-10-20 #71] 공유 카드 — 지면 og:image · /assets/og.jpg = /og/home.jpg(바이트) · 1200×630
//  ⑤ [2026-10-20 공개] 실제 브라우저로 열기 — 상태 · 화면 오류 · 외부 요청 0(Cloudflare 비컨 예외)
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
// ⑤ 실제 브라우저로 열기 — 지면마다 상태 · 화면 오류 · 외부 요청(자기 호스트 밖 · Cloudflare 비컨 한 곳만 예외)
if (cfg.open?.length) {
  const { chromium } = await import("playwright");
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
    await pg.close();
  }
  await br.close();
}
// ⑥ 공유 카드 — 지면이 가리키는 og:image 와, 옛 주소 /assets/og.jpg 가 새 홈 카드와 같은 그림인가(SHA-256 · JPEG 크기)
if (cfg.og?.length) {
  const { createHash } = await import("node:crypto");
  const jpg = async (u) => { const r = await fetch(u); const b = Buffer.from(await r.arrayBuffer()); let wh = "—";
    for (let i = 2; i < b.length - 9;) { if (b[i] !== 0xff) break; const m = b[i + 1], n = b.readUInt16BE(i + 2); if (m === 0xc0 || m === 0xc2) { wh = `${b.readUInt16BE(i + 7)}×${b.readUInt16BE(i + 5)}`; break; } i += 2 + n; }
    return { st: r.status, n: b.length, h: createHash("sha256").update(b).digest("hex").slice(0, 12), wh }; };
  L.push("", "## ⑥ 공유 카드(og:image)", "", "| 지면 | og:image |", "|---|---|");
  for (const p of cfg.og) {
    const html = await (await fetch(encodeURI(cfg.base + p))).text();
    L.push(`| \`${p}\` | ${(html.match(/<meta property="og:image" content="([^"]+)"/)?.[1] || "없음").replace(cfg.base, "")} |`);
  }
  const a = await jpg(cfg.base + "/og/home.jpg"), b = await jpg(cfg.base + "/assets/og.jpg");
  L.push("", `- \`/og/home.jpg\` → ${a.st} · ${a.wh} · ${a.n}B · sha256 ${a.h}`, `- \`/assets/og.jpg\` → ${b.st} · ${b.wh} · ${b.n}B · sha256 ${b.h}`, `- 같은 그림: **${a.h === b.h && a.st === 200 ? "예" : "아니오"}**`);
}
console.log(L.join("\n"));

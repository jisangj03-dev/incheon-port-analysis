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
    // [2026-10-23] 연결 실패는 한 번 더 — 레이더의 기업마당 원문 링크가 회차마다 다른 공고에서 끊겼다(1회차 2건 · 2회차 다른 1건 · 같은 호스트 70건은 200).
    //   해외 러너에서 연달아 부를 때의 끊김이라 링크 깨짐이 아니다. 다시 불러도 끊기면 그대로 깨짐으로 센다(분류는 바꾸지 않는다).
    if (st === "연결 실패") { await new Promise((r) => setTimeout(r, 5000)); try { st = (await fetch(u, { method: "GET", redirect: "follow", signal: AbortSignal.timeout(30000), headers: { "user-agent": "Mozilla/5.0 (compatible; cheuksim-linkcheck/1.0; weekly)" } })).status; } catch { st = "연결 실패"; } }
    seen.set(u, st); return st;
  };
  // 해외 러너에서만 끊기는 호스트 — 사람이 한국에서 열어 정상을 확인한 것만 적는다(호스트 · 확인일 · 누가). 「연결 실패」일 때만 「확인 불가」로 옮기고, 4xx·5xx 는 그대로 깨짐이다.
  //   ygpa.incruit.com = 여수광양항만공사 채용(레이더) — Actions 에서 4회 연속 연결 실패 · 2026-10-23 채팅(선장님 브라우저)이 한국에서 채용 홈페이지 정상 로드를 확인.
  const GEO = { "ygpa.incruit.com": "2026-10-23 한국 접속 정상(채팅 확인)" };
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
      else if (!inside && st === "연결 실패" && GEO[new URL(u).host]) unknown.push(`${u} (해외 러너 연결 실패 · ${GEO[new URL(u).host]})`);
      else broken.push(`${p} → ${u} (${st})`);
    }
  }
  L.push("", "## ⑥ 링크 전수", "", `- 검사한 주소 ${seen.size}개 · 깨짐 **${broken.length}** · 확인 불가(봇 차단·해외 접속) ${unknown.length}`);
  for (const b of broken) { L.push(`  - 깨짐: ${b}`); FAIL.push(`링크 깨짐 ${b}`); }
  for (const u of [...new Set(unknown)]) L.push(`  - 확인 불가: ${u}`);
}
// ⑦ 홍보 초안 숫자 = 공개판(2026-10-22 갱신 무인화 · launch 대조) — content-queue/live/launch.md 의 숫자는 전부 data/derived/facts.json 이름에서 온다.
//   이름마다 공개 지면 실물(HTML 보이는 글자)에 같은 값이 같은 꼴로 있는지 잰다. 초안에 나온 자리 수(같은 숫자가 여러 번)도 같이 적는다.
if (existsSync("data/derived/facts.json") && existsSync("content-queue/templates/launch.md")) {
  const F = JSON.parse(readFileSync("data/derived/facts.json", "utf-8")).facts;
  const tpl = readFileSync("content-queue/templates/launch.md", "utf-8").split("\n---\n").slice(1).join("\n---\n");
  const uses = {}; for (const m of tpl.matchAll(/\{\{\s*([^}:]+?)\s*\}\}/g)) uses[m[1]] = (uses[m[1]] || 0) + 1;
  const vis = (h) => h.replace(/<script[\s\S]*?<\/script>/gi, " ").replace(/<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/\s+/g, " ");
  const esc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pat = (f) => f.ctx ? new RegExp(f.ctx.split("{v}").map(esc).join(`\\s*${esc(f.v)}\\s*`)) : new RegExp(`(?<![\\d.])${esc(f.v)}(?![\\d])`);
  const cache = {};
  const page = async (p) => (cache[p] ??= vis(await (await fetch(cfg.base + (p === "/" ? "/" : p))).text()));
  L.push("", "## ⑦ 홍보 초안(launch) 숫자 = 공개판", "", "| 이름 | 값 | 초안 자리 | 공개 지면 | 공개판에 같은 값 |", "|---|---|---|---|---|");
  let n = 0, bad = 0;
  for (const [k, c] of Object.entries(uses)) {
    const f = F[k]; if (!f) { L.push(`| ${k} | (facts 없음) | ${c} | — | **없음** |`); bad++; FAIL.push(`launch 숫자 ${k} — facts 없음`); continue; }
    n += c;
    const res = [];
    for (const p of f.pages) res.push(pat(f).test(await page(p)) ? `\`${p}\` 있음` : `\`${p}\` **없음**`);
    const ok = f.pages.length && res.every((r) => r.endsWith("있음"));
    if (!ok && f.pages.length) { bad++; FAIL.push(`launch 숫자 ${k}=${f.v} — 공개판에 없음`); }
    L.push(`| ${k} | ${f.v} | ${c} | ${f.pages.join(" · ") || "(지면 없음)"} | ${f.pages.length ? res.join(" · ") : "—"} |`);
  }
  L.push("", `- 초안 숫자 자리 ${n}개 · 이름 ${Object.keys(uses).length}개 · 공개판 불일치 ${bad}`);
}
// ⑧ 띠 그림 = 등시선 지면(2026-10-22 갱신 무인화 · 주 1회) — 배포된 띠 그림이 찍힌 순간의 장면 상태(assets/toolshots/delivery-reach*.json · og-cards guard 가 냄)를
//   등시선 지면 첫 문장의 서울시청 분·차종과 대조하고, 홈 띠 설명이 같은 기준(승용차)인지 본다. 어긋나면 FAIL → 자동경보.
//   cfg.shots 가 있으면 홈 첫 화면·띠 그림 원본·지면 지도를 docs/live-shots 에 받아 둔다(브랜치 실행만 커밋 · main 은 결과 이슈만).
{
  const { chromium } = await import("@playwright/test");
  const P = JSON.parse(readFileSync("data/profile.json", "utf-8"));
  const html = await (await fetch(cfg.base + "/")).text();
  const carNote = /승용차·평일 [^<]*출발로 계산한 도달 시간/.test(html), truckNote = /화물차·[^<]*계산한 도달 시간/.test(html);
  L.push("", "## ⑧ 띠 그림 = 등시선 지면", "", `- 홈 원문 실명 등장: **${html.split(P.name).length - 1}회** · 띠 설명 「승용차·평일 … 출발」: ${carNote ? "있음" : "**없음**"} · 「화물차·」: ${truckNote ? "**있음**" : "없음"}`);
  if (!carNote || truckNote) FAIL.push("홈 띠 설명이 승용차 기준이 아니다");
  const b = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined });
  const pg = await b.newPage({ viewport: { width: 560, height: 900 }, deviceScaleFactor: 2 });
  await pg.goto(cfg.base + "/tools/delivery-reach.html", { waitUntil: "load" }); await pg.waitForTimeout(4000);
  const lead = (await pg.locator(".tool__lead").first().textContent()) || "";
  const leadMin = Number((lead.match(/서울시청까지 (\d+)분/) || [])[1]), leadCar = /승용차로 출발하면/.test(lead);
  L.push(`- 등시선 지면 첫 문장: 「${lead.slice(0, 90)}…」 → 서울시청 **${leadMin}분** · ${leadCar ? "승용차" : "**승용차 아님**"}`);
  for (const f of ["delivery-reach", "delivery-reach-m"]) {
    const r = await fetch(`${cfg.base}/assets/toolshots/${f}.json`);
    if (!r.ok) { L.push(`- 띠 그림 상태 ${f}.json: ${r.status}`); FAIL.push(`띠 그림 상태 ${f}.json ${r.status}`); continue; }
    const st = await r.json(), same = st.서울시청분 === leadMin && st.차종 === "승용" && leadCar;
    L.push(`- 띠 그림 \`${f}.jpg\` 찍힌 장면: ${st.출발지} · ${st.차종} · ${st.시간대} · 서울시청 **${st.서울시청분}분** → ${same ? "**같다**" : "**다르다**"}`);
    if (!same) FAIL.push(`띠 그림(${f}) 서울시청 ${st.서울시청분}분·${st.차종} ≠ 등시선 지면 ${leadMin}분`);
  }
  if (cfg.shots?.length) {
    mkdirSync("docs/live-shots", { recursive: true });
    for (const f of ["delivery-reach.jpg", "delivery-reach-m.jpg"]) {
      const r = await fetch(`${cfg.base}/assets/toolshots/${f}`);
      if (r.ok) { writeFileSync(`docs/live-shots/toolshot-${f}`, Buffer.from(await r.arrayBuffer())); L.push(`- 공개판 띠 그림 \`docs/live-shots/toolshot-${f}\``); } else FAIL.push(`띠 그림 ${f} ${r.status}`);
    }
    await pg.locator(".reach__map").first().screenshot({ path: "docs/live-shots/delivery-reach-map-560.png" }); L.push("- `docs/live-shots/delivery-reach-map-560.png` (실물 지면 지도)");
    for (const [w, h] of cfg.shots) {
      const ctx = await b.newContext({ viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500, deviceScaleFactor: w < 500 ? 2 : 1 });
      const hp = await ctx.newPage();
      await hp.goto(cfg.base + "/", { waitUntil: "load" }); await hp.waitForTimeout(2500);
      const f = `docs/live-shots/home--${w}x${h}.png`; await hp.screenshot({ path: f }); L.push(`- \`${f}\``);
      await ctx.close();
    }
  }
  await b.close();
}
// ⑨ 홈 유통 줄 = 파생 파일(2026-10-22 유통 축 KOSIS · 사고 137) — 공개판 홈의 #ax-retail 줄이 data/derived/home_axes.json retail.kosis 와 같은 값·같은 달인지.
//   KOSIS 가 없거나 출처 대장 줄이 없으면 지면은 종전 줄(생활소비재 수입)이라 그 값을 댄다. 배포 뒤 공개판이 저장소와 갈리면 FAIL → 자동경보.
{
  const AX = JSON.parse(readFileSync("data/derived/home_axes.json", "utf-8")), R = AX.retail || {};
  const SRC = JSON.parse(readFileSync("data/sources.json", "utf-8")).sources;
  const KO = R.kosis?.large && R.kosis?.online && SRC.some((s) => s.id === "kostat-kosis") ? R.kosis : null;
  const one = (v) => v.toLocaleString("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const home = await (await fetch(cfg.base + "/")).text();
  const i = home.indexOf('href="#ax-retail"');
  const row = i < 0 ? "" : home.slice(i, home.indexOf("</a>", i)).replace(/<[^>]+>/g, " ").replace(/\s+/g, " ");
  const want = KO ? [`${one(KO.large.sudo_jo)}`, "조 원", KO.large.ym, `온라인쇼핑 거래액 ${one(KO.online.jo)}조 원`, KO.online.ym] : [one(R.cons_imp), "억 달러", R.ym];
  const miss = want.filter((w) => !row.includes(w));
  L.push("", "## ⑨ 홈 유통 줄 = 파생 파일", "", `- 기준: ${KO ? "KOSIS(수도권 대형소매점 · 전국 온라인쇼핑)" : "종전(생활소비재 수입)"} · 공개판 줄: 「${row.trim().slice(0, 160)}」`, `- 찾을 값 ${want.length} · 빠진 값 ${miss.length ? miss.join(" · ") : "0"}`);
  if (!row) FAIL.push("홈 유통 줄(#ax-retail)이 공개판에 없다");
  else if (miss.length) FAIL.push(`홈 유통 줄이 파생 파일과 다르다 — 빠진 값 ${miss.join(" · ")}`);
}
L.push("", `## 판정 — 어긋남 ${FAIL.length}`, "", ...(FAIL.length ? FAIL.map((f) => `- ${f}`) : ["- 없음"]));
writeFileSync("live-check-fail.txt", FAIL.join("\n"));
console.log(L.join("\n"));

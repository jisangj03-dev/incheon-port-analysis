// 우리 면 조작 녹화 — 선장님이 폰에서도 판정하게(2026-10-14). 우리 면만(기준 사이트 없음) · 390 세로 · 1440 가로 · 면마다 15초 안팎 mp4 + 첫 화면 PNG.
// [공개 전환] 공개 주소로 · 면에 따라가기·선박 더함 · 영상마다 움직이는 중간 프레임 2장(35%·65% — 채팅 검수 ③: GitHub 화면은 mp4 를 못 튼다)
// · 공개 지면 전체 페이지 캡처(두 폭 · full/).
// Playwright 녹화(webm) → ffmpeg 로 H.264 mp4(폰 재생 · faststart). 외부 요청은 막는다(지면이 외부 요청 0 인지도 같이 본다).
//   node tests/capture/record-ds.mjs [--base http://127.0.0.1:4173/incheon-port-analysis] [--out lab-out/ours]
import { chromium } from "@playwright/test";
import { mkdirSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { execFileSync } from "node:child_process";

const arg = (k, d) => { const i = process.argv.indexOf(`--${k}`); return i > 0 ? process.argv[i + 1] : d; };
const base = arg("base", "http://127.0.0.1:4173/incheon-port-analysis"), out = arg("out", "lab-out/ours");
mkdirSync(out, { recursive: true });
const tmp = join(out, "_webm"); mkdirSync(tmp, { recursive: true });

const wait = (p, ms) => p.waitForTimeout(ms);
// 천천히 내린다 — 사람이 스크롤하듯(스크롤로 그려지는 주홍 선이 보이게)
async function glide(p, to, ms) {
  const from = await p.evaluate(() => scrollY), steps = Math.max(1, Math.round(ms / 50));
  for (let i = 1; i <= steps; i++) { await p.evaluate((y) => scrollTo(0, y), from + ((to - from) * i) / steps); await wait(p, 50); }
}
async function sweep(p, sel, values, each) { for (const v of values) { await p.locator(sel).fill(String(v)); await p.locator(sel).dispatchEvent("input"); await wait(p, each); } }

const FACES = {
  // 홈(2026-10-14 판정 뒤): 살아 있는 지도 — 정지 해도 → 흐름이 돈다(아시아) → 스스로 인천·수도권으로 날아든다 → 관문 숫자 판 → 끌어서 돌린다 → 같이 푸는 질문
  home: { gif: [1.5, 14], path: "/", run: async (p, V) => {
    await wait(p, 800);
    if (V.mobile) await p.touchscreen.tap(V.w / 2, V.h - 140); // 좁은 화면은 만지면 움직인다
    await p.waitForSelector("#live-stage[data-ready='1']", { timeout: 20_000 });
    await wait(p, 7500); // 아시아 → 둘러보기가 인천으로 날아든다
    await p.click("[data-view=incheon]"); await wait(p, 6000);
    await p.click("#fm-gates"); await wait(p, 2200); await p.click("#fm-x");
    const box = await p.locator("#fm").boundingBox();
    if (box && !V.mobile) { await p.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.6); await p.mouse.down(); for (let i = 0; i < 20; i++) { await p.mouse.move(box.x + box.width * 0.7 - i * 12, box.y + box.height * 0.6 + i * 2); await wait(p, 40); } await p.mouse.up(); }
    await p.click("[data-view=asia]"); await wait(p, 4500);
    const q = await p.evaluate(() => document.getElementById("questions").getBoundingClientRect().top + scrollY - 40);
    await glide(p, q, 2500); await wait(p, 1500);
  } },
  // 맥주 게임: 막대를 잠깐 → 「직접 해 보기」 소매를 맡아 36주를 빠른 주문으로 → 내 점수 · 공유 카드
  beer: { gif: [5.5, 15], path: "/sim/beer-game.html", run: async (p) => {
    await p.waitForSelector("#wave[data-ready]"); await wait(p, 1000);
    await sweep(p, "#beta", [0.34, 0.15, 0, 0.5, 1, 0.34], 380);
    await p.click(".try-cta a"); await wait(p, 900);
    await p.click("#start"); await wait(p, 1200);
    for (let i = 0; i < 36; i++) { await p.locator("#quick button").nth([2, 3, 4, 1, 2, 0][i % 6] % Math.max(1, await p.locator("#quick button").count())).click(); await wait(p, i < 10 ? 420 : 160); }
    await wait(p, 900);
    const y = await p.evaluate(() => document.getElementById("result").getBoundingClientRect().top + scrollY - 20);
    await glide(p, y, 1000); await wait(p, 2500);
    const c = await p.evaluate(() => document.querySelector(".card").getBoundingClientRect().top + scrollY - 80);
    await glide(p, c, 1200); await wait(p, 2000);
  } },
  // 지도: 그대로 두면 달이 흐르고 점이 숨 쉰다 → 달 막대로 앞뒤
  map: { path: "/map.html", run: async (p) => {
    await wait(p, 1200); // 정지 해도 그림(손대기 전)
    await p.mouse.move(40, 40); // 사람이 움직이면 지도가 뜬다
    await p.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 });
    const top = await p.evaluate(() => document.getElementById("ds-map").getBoundingClientRect().top + scrollY - 80);
    await glide(p, top, 1200);
    await wait(p, 9000);
    const max = Number(await p.locator("#ds-m").getAttribute("max"));
    await sweep(p, "#ds-m", [max, Math.round(max * 0.75), Math.round(max * 0.5), Math.round(max * 0.25), 0, max], 500);
    await wait(p, 600);
  } },
  // 노트: 단계·날짜 → 막대 차트 → 자라려면 → 이어지는 노트
  // 공급망 따라가기: 단계마다 내려가며 그림이 바뀐다
  follow: { gif: [2, 16], path: "/map/follow.html", run: async (p, V) => {
    await wait(p, 900);
    if (V.mobile) await p.touchscreen.tap(V.w / 2, 120);
    else await p.mouse.wheel(0, 2);
    await p.waitForSelector("#trip-stage[data-ready='1']", { timeout: 20_000 });
    // 단계마다 천천히 내린다 — 카메라가 상자를 따라 난다(바다 구간은 길게)
    for (const id of await p.locator(".st[data-s]").evaluateAll((a) => a.map((x) => x.getAttribute("data-s")))) {
      const [y0, h] = await p.evaluate((id) => { const el = document.querySelector(`[data-s="${id}"]`); return [el.getBoundingClientRect().top + scrollY - innerHeight * 0.5, el.offsetHeight]; }, id);
      await glide(p, y0 + h * 0.1, 700);
      if (id === "sea" || id === "firms" || id === "last") await glide(p, y0 + h * 0.9, id === "sea" ? 4200 : 2200);
      await wait(p, 1100);
    }
  } },
  // 선박 리플레이: 재생 → 2015년부터 달이 흐른다
  vessels: { path: "/map/vessels.html", run: async (p) => {
    await wait(p, 1200);
    const y = await p.evaluate(() => document.getElementById("replay").getBoundingClientRect().top + scrollY - 60);
    await glide(p, y, 900);
    await p.click("#vr-play"); await wait(p, 12000);
  } },
  note: { path: "/notes/port-yoy.html", run: async (p) => {
    await wait(p, 1800);
    const H = await p.evaluate(() => document.documentElement.scrollHeight - innerHeight);
    await glide(p, H, 10000);
    await wait(p, 1500);
    await glide(p, 0, 1500);
  } },
};
const VIEWS = [{ name: "390", w: 390, h: 844, mobile: true }, { name: "1440", w: 1440, h: 900, mobile: false }];

const ONLY = arg("only", "");
if (ONLY) for (const k of Object.keys(FACES)) if (!ONLY.split(",").includes(k)) delete FACES[k];
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM_PATH || undefined, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const report = [];
for (const [face, F] of Object.entries(FACES)) for (const V of VIEWS) {
  const dir = join(tmp, `${face}-${V.name}`); rmSync(dir, { recursive: true, force: true }); mkdirSync(dir, { recursive: true });
  const ctx = await browser.newContext({ viewport: { width: V.w, height: V.h }, isMobile: V.mobile, hasTouch: V.mobile, deviceScaleFactor: 1, recordVideo: { dir, size: { width: V.w, height: V.h } } });
  const page = await ctx.newPage();
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => { ext.push(r.request().url()); return r.abort(); });
  const t0 = Date.now();
  let err = null;
  try {
    await page.goto(base + F.path, { waitUntil: "networkidle", timeout: 45_000 });
    await page.screenshot({ path: join(out, `${face}-${V.name}-first.png`) });
    await F.run(page, V);
  } catch (e) { err = String(e).split("\n")[0]; }
  await ctx.close();
  const webm = readdirSync(dir).find((f) => f.endsWith(".webm"));
  const mp4 = join(out, `${face}-${V.name}.mp4`);
  if (webm) {
    // 폰 재생용 — H.264 · yuv420p · 앞머리에 색인(faststart) · 짝수 크기
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-i", join(dir, webm), "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", mp4]);
  }
  // 움직이는 중간 프레임 2장(35% · 65%) — 영상을 못 트는 화면에서도 움직임을 본다
  const frames = [];
  if (webm) {
    const dur = Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4]).toString().trim()) || 0;
    for (const f of [0.35, 0.65]) {
      const png = join(out, "frames", `${face}-${V.name}-${Math.round(f * 100)}.png`);
      mkdirSync(join(out, "frames"), { recursive: true });
      execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-ss", (dur * f).toFixed(2), "-i", mp4, "-frames:v", "1", png]);
      frames.push(png);
    }
  }
  // 움직임이 보이는 GIF — GitHub 화면이 바로 튼다(채팅 검수 · 10/14 판정 뒤). 10fps · 폭 ≤ 480 · 팔레트 두 번 거르기
  let gif = null;
  if (webm && F.gif) {
    mkdirSync(join(out, "gif"), { recursive: true });
    gif = join(out, "gif", `${face}-${V.name}.gif`);
    const [ss, len] = F.gif, wpx = Math.min(480, V.w);
    execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-ss", String(ss), "-t", String(len), "-i", mp4, "-vf", `fps=10,scale=${wpx}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`, gif]);
  }
  report.push({ face, view: V.name, frames, gif, seconds: Math.round((Date.now() - t0) / 1000), mp4: webm ? mp4 : null, external: ext.length, err });
  console.log(`${face} ${V.name} · ${Math.round((Date.now() - t0) / 1000)}초 · ${webm ? mp4 : "녹화 없음"} · 외부 요청 ${ext.length}${err ? ` · 오류 ${err}` : ""}`);
}
// 공개 지면 전체 페이지 캡처(두 폭) — 공개 뒤 모습 그대로(지도는 움직이는 지도가 뜬 상태)
const FULL = ["/", "/map.html", "/map/follow.html", "/map/vessels.html", "/sim/", "/sim/beer-game.html", "/sim/forecast.html", "/notes.html", "/notes/port-yoy.html", "/notes/ai-ops.html", "/about.html", "/data.html"];
if (arg("full", "1") === "0") FULL.length = 0;
mkdirSync(join(out, "full"), { recursive: true });
for (const V of VIEWS) for (const path of FULL) {
  const ctx = await browser.newContext({ viewport: { width: V.w, height: V.h }, isMobile: V.mobile, hasTouch: V.mobile, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  const name = `${V.name}-${path === "/" ? "home" : path.replace(/^\//, "").replace(/\.html$/, "").replace(/\/$/, "").replace(/\//g, "_")}.png`;
  try {
    await page.goto(base + path, { waitUntil: "networkidle", timeout: 45_000 });
    if (path === "/map.html") { await page.mouse.move(40, 40); await page.waitForSelector("#ds-map[data-ready]", { timeout: 45_000 }); }
    // 스크롤로 나타나는 장면까지 다 보이게 끝까지 한 번 내렸다 올린다
    await glide(page, await page.evaluate(() => document.documentElement.scrollHeight), 1500); await glide(page, 0, 300); await wait(page, 500);
    await page.screenshot({ path: join(out, "full", name), fullPage: true });
    console.log(`전체 ${name}`);
  } catch (e) { console.log(`전체 ${name} 실패 ${String(e).split("\n")[0]}`); report.push({ face: `full:${path}`, view: V.name, err: String(e).split("\n")[0] }); }
  await ctx.close();
}
await browser.close();
rmSync(tmp, { recursive: true, force: true });
writeFileSync(join(out, "report.json"), JSON.stringify(report, null, 1));
if (report.some((r) => r.err || (r.face && !r.face.startsWith("full:") && !r.mp4))) process.exit(1);

// B6 공유 카드 · B7 퍼가기 — 보고서마다 1200×630 카드가 있고 og:image 가 그것을 가리키는가 · 퍼가기 지면이 밖으로 요청을 안 내는가.
// 카드는 빌드 뒤 `npm run site:og` 가 만든다(CI 는 시험 전에 돈다). 로컬에서 안 돌렸으면 건너뛴다.
import { test, expect } from "@playwright/test";
import { readFileSync, existsSync, readdirSync } from "node:fs";

const jpegSize = (buf) => { // SOF0/SOF2 표지에서 높이·너비
  for (let i = 2; i < buf.length; ) {
    if (buf[i] !== 0xff) return null;
    const m = buf[i + 1], len = buf.readUInt16BE(i + 2);
    if (m === 0xc0 || m === 0xc2) return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) };
    i += 2 + len;
  }
  return null;
};

// 홈 카드(2026-10-20) — 지면 기본 카드가 옛 남색 og.jpg 가 아니라 og/home.jpg · 옛 주소 assets/og.jpg 도 같은 그림 · 카드 숫자 = 홈 첫 문장 숫자
test("B6 홈 — 기본 카드 og/home.jpg · assets/og.jpg = 같은 그림 · 홈·지도·노트·소개·도구 목록이 그 카드", async ({ request }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  test.skip(!existsSync("astro/dist/og/cards.json"), "npm run site:og 를 안 돌렸다");
  const home = readFileSync("astro/dist/og/home.jpg");
  expect(jpegSize(home)).toEqual({ w: 1200, h: 630 });
  expect(Buffer.compare(home, readFileSync("astro/dist/assets/og.jpg")), "assets/og.jpg 가 홈 카드와 다르다").toBe(0);
  expect(existsSync("astro/dist/og/home.html"), "홈 카드 틀 HTML 이 배포물에 남았다").toBe(false);
  for (const path of ["/", "/notes.html", "/about.html", "/tools/", "/map/vessels.html", "/sim/beer-game.html", "/notes/port-yoy.html"]) {
    const html = await (await request.get(`/incheon-port-analysis${path}`)).text();
    expect(html.match(/<meta property="og:image" content="([^"]+)"/)?.[1], path).toBe("https://jisangj03-dev.github.io/incheon-port-analysis/og/home.jpg");
  }
  const F = JSON.parse(readFileSync("data/derived/home_flows.json", "utf-8")), M = F.months[F.months.length - 1];
  const html = await (await request.get("/incheon-port-analysis/")).text();
  expect(html, "홈 첫 문장 숫자 = 카드 숫자(home_flows 마지막 달)").toContain(`${M.imp_share_pct}%</span>가</span> 인천으로 들어옵니다`); // 숫자+조사 한 덩어리(live__nb)
});

// 도구 일곱(전권 위임 ④) — 카드가 있고, og:image 가 그 카드이고, 카드에 찍힌 숫자 = 지면 큰 숫자(cards.json 은 찍는 순간 지면에서 읽은 값)
const TOOLS = JSON.parse(readFileSync("data/rooms.json", "utf-8")).rooms.find((r) => r.id === "tools").items.filter((t) => /^\/tools\/.+\.html$/.test(t.href)); // 공유 카드·퍼가기는 /tools/ 도구만(og-cards.mjs 와 같은 거름)
test("B6 도구 — 도구마다 1200×630 카드 · og:image · 카드 숫자 = 지면 큰 숫자", async ({ request }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  test.skip(!existsSync("astro/dist/og/cards.json"), "npm run site:og 를 안 돌렸다");
  const C = JSON.parse(readFileSync("astro/dist/og/cards.json", "utf-8")).cards;
  expect(TOOLS.length).toBeGreaterThanOrEqual(4); // 2026-10-20 묘박지·입찰 레이더·맥박 내림
  for (const t of TOOLS) {
    expect(jpegSize(readFileSync(`astro/dist/og/tool-${t.id}.jpg`)), t.id).toEqual({ w: 1200, h: 630 });
    const html = await (await request.get(`/incheon-port-analysis${t.href}`)).text();
    expect(html.match(/<meta property="og:image" content="([^"]+)"/)[1], t.id).toBe(`https://jisangj03-dev.github.io/incheon-port-analysis/og/tool-${t.id}.jpg`);
    const num = html.match(/<[^>]*\bdata-og-num\b[^>]*>([\s\S]*?)<\/(?:b|i)>/)[1].replace(/<[^>]+>/g, "").replace(/\s+/g, "");
    expect(C[t.id].num, `${t.id} 카드 숫자`).toBe(num);
    expect(html).toContain(C[t.id].q);
  }
  expect(existsSync("astro/dist/og/tool.html"), "카드 틀 HTML 이 배포물에 남았다").toBe(false);
});

test("B7 도구 — 퍼가기 지면: 카드 그림 · 원 도구 링크 · 출처 · 외부 요청 0(분석도 없다) · 도구 지면에 퍼가기 코드", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  test.skip(!existsSync("astro/dist/og/cards.json"), "npm run site:og 를 안 돌렸다");
  const ext = [];
  await page.route(/^https?:\/\/(?!127\.0\.0\.1)/, (r) => { ext.push(r.request().url()); return r.abort(); });
  for (const t of TOOLS) {
    await page.goto(`/incheon-port-analysis/embed/tool-${t.id}.html`, { waitUntil: "load" });
    expect(await page.locator("main img").evaluate((i) => i.complete && i.naturalWidth), t.id).toBe(1200);
    await expect(page.locator(`main a[href$="${t.href}"]`).first()).toBeVisible();
    await expect(page.locator("main small")).toContainText("측심 도구");
    expect(await page.locator('meta[name="robots"][content="noindex"]').count()).toBe(1);
  }
  expect(ext, "퍼가기 지면은 분석 비콘도 안 싣는다").toEqual([]);
  await page.goto(`/incheon-port-analysis${TOOLS[0].href}`);
  await page.locator(".tool__more > summary").click();
  await expect(page.locator(".tool__embed textarea")).toHaveValue(new RegExp(`<iframe src="https://jisangj03-dev\\.github\\.io/incheon-port-analysis/embed/tool-${TOOLS[0].id}\\.html"`));
});

// 홈 첫 화면(히어로) 겹침 0 — 2026-10-15 채팅 검수: 1536×640(노트북 크롬 실측)에서 「2026-07 인천 관문을 지난 수출입 908.7억 달러」가
// LinkedIn 단추를 가렸다. 노트북 흔한 크기 9가지에서 글·단추·숫자판·지도 단추가 서로 겹치지 않는지 본다(지도 그림 위 겹침은 설계 — 글자끼리만).
import { test, expect } from "@playwright/test";
import { still } from "./lib/still.mjs";
import { labelHits } from "./label-hits.mjs";
const B = "/incheon-port-analysis";
const SIZES = [1280, 1440, 1536].flatMap((w) => [640, 720, 900].map((h) => ({ width: w, height: h })));

test("히어로 — 너비 1280·1440·1536 × 높이 640·720·900 에서 글·단추·숫자판·지도 단추 겹침 0 · 첫 화면 안 · 인천이 지도 칸 안", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "크기를 시험 안에서 바꾼다 — 한 번이면 된다");
  // CI 에서 홈 지도 움직임이 주 스레드를 막아 9번 여는 동안 90초를 넘었다(QA 185) — 움직임만 끈다(배치는 같다 · 따라가기 시험과 같은 방법)
  test.setTimeout(240_000);
  await still(page); // 정지 화면 = 동작 줄이기 + 멈춤(2026-10-20 · 동작 줄이기만으로는 흐름이 멈추지 않는다)
  const bad = [];
  for (const vp of SIZES) {
    await page.setViewportSize(vp);
    await page.goto(`${B}/`, { waitUntil: "load" });
    await page.waitForSelector("#live-stage[data-ready='1']", { timeout: 30_000 });
    await page.waitForTimeout(300);
    const hits = await page.evaluate(() => {
      const sel = [".live__text > *", ".live__cta a", ".live__cta button", ".live__stat", ".live__ctl", ".live__legend", ".live__pause"];
      const els = [...new Set(sel.flatMap((s) => [...document.querySelectorAll(s)]))].filter((e) => { const r = e.getBoundingClientRect(); return r.width && r.height && getComputedStyle(e).visibility !== "hidden"; });
      const nm = (e) => `${e.className?.toString().split(" ")[0] || e.tagName}「${(e.textContent || "").trim().slice(0, 12)}」`;
      const out = [];
      for (let i = 0; i < els.length; i++) for (let j = i + 1; j < els.length; j++) {
        const a = els[i], c = els[j]; if (a.contains(c) || c.contains(a)) continue;
        const A = a.getBoundingClientRect(), C = c.getBoundingClientRect();
        const ox = Math.min(A.right, C.right) - Math.max(A.left, C.left), oy = Math.min(A.bottom, C.bottom) - Math.max(A.top, C.top);
        if (ox > 1 && oy > 1) out.push(`${nm(a)} × ${nm(c)}`);
      }
      return out;
    });
    for (const h of hits) bad.push(`${vp.width}×${vp.height} ${h}`);
    // [2026-10-20 품질기준 Q1·Q6] 첫 화면 안에서 끝난다 — 제목·한 문장·큰 숫자·행동 둘·지도 단추가 접힘선 위 · 인천 관문(공항)이 지도 칸 안
    const f = await page.evaluate(() => {
      const vh = innerHeight, b = (s) => document.querySelector(s)?.getBoundingClientRect();
      const st = b("#live-stage"), fm = window.__fm, g = fm?.D.flows.air_gate, s = fm && g ? fm.screen(g.lon, g.lat) : null;
      return { vh, h1: b("#live-h").bottom, one: b(".live__one").bottom, stat: b(".live__stat").bottom, cta: b(".live__cta").bottom, ctl: b(".live__ctl").bottom,
        inc: s ? [st.left + s[0], st.top + s[1], st.left, st.right, st.top, Math.min(st.bottom, vh)] : null };
    });
    for (const k of ["h1", "one", "stat", "cta", "ctl"]) if (f[k] > f.vh + 1) bad.push(`${vp.width}×${vp.height} ${k} 가 접힘선 아래(${Math.round(f[k])} > ${f.vh})`);
    if (f.inc && !(f.inc[0] > f.inc[2] + 8 && f.inc[0] < f.inc[3] - 8 && f.inc[1] > f.inc[4] + 8 && f.inc[1] < f.inc[5] - 8)) bad.push(`${vp.width}×${vp.height} 인천공항이 지도 칸 밖(${f.inc.map(Math.round).join(",")})`);
  }
  expect(bad, bad.join("\n")).toEqual([]);
});

// [2026-10-20 #67 ③ · 1568×709 검수] 지도 이름표(서울·의왕 ICD 등)가 글 블록(문장·단추)과 겹치지 않는다
// CI 에서 움직이는 지도가 주 스레드를 막아 16크기를 다 열면 5분을 넘었다(QA 287) → 16크기는 동작 줄이기(배치는 같다 · 위 시험과 같은 방법),
// 검수한 1568×709 만 움직이는 그대로 여러 번 잰다
const SIZES2 = [1280, 1440, 1536, 1568].flatMap((w) => [640, 709, 720, 900].map((h) => ({ width: w, height: h })));
test("히어로 — 지도 이름표 × 글·단추 겹침 0(너비 1280·1440·1536·1568 × 높이 640·709·720·900)", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "크기를 시험 안에서 바꾼다 — 한 번이면 된다");
  test.setTimeout(240_000);
  await still(page); // 정지 화면 = 동작 줄이기 + 멈춤(2026-10-20 · 동작 줄이기만으로는 흐름이 멈추지 않는다)
  const bad = [];
  for (const vp of SIZES2) {
    await page.setViewportSize(vp);
    await page.goto(`${B}/`, { waitUntil: "load" });
    await page.waitForTimeout(500);
    for (const h of await labelHits(page)) bad.push(`${vp.width}×${vp.height} ${h}`);
  }
  expect([...new Set(bad)], [...new Set(bad)].join("\n")).toEqual([]);
});
// 1568×709 움직이는 지도 시험은 tests/autoplay.spec.mjs 에 있다 — 움직이는 지도 시험끼리 한 파일(한 작업자)에서 차례로 돌게(QA 288)

// [2026-10-21 채팅 공개판 검수] 제목의 「50.5%」와 조사 「가」가 다른 줄로 갈리지 않는다 — 데스크톱에서 「가」가 둘째 줄 맨 앞에 혼자 갔다.
// 헤드리스 글꼴 폭으로는 768 에서만 재현됐다(실제 브라우저는 창·확대·글꼴에 따라 1520 에서도) — 크기 열둘 모두에서 덩어리가 한 줄인지 본다.
test("히어로 — 제목의 숫자와 조사(「는」)가 한 줄(크기 열둘)", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "크기를 시험 안에서 바꾼다 — 한 번이면 된다");
  test.setTimeout(180_000);
  await still(page);
  const bad = [];
  for (const [width, height] of [[1280, 720], [1280, 800], [1366, 768], [1440, 900], [1520, 730], [1520, 860], [1536, 864], [1680, 1050], [1920, 1080], [2560, 1440], [390, 844], [768, 1024]]) {
    await page.setViewportSize({ width, height });
    await page.goto(`${B}/`, { waitUntil: "load" });
    const r = await page.evaluate(() => [...document.querySelectorAll("#live-h .live__nb")].map((nb) => new Set([...nb.getClientRects()].map((x) => Math.round(x.top))).size));
    if (!r.length || r.some((n) => n !== 1)) bad.push(`${width}×${height} 숫자·조사 덩어리 줄 수 ${r.join(",") || "없음"}`);
  }
  expect(bad, bad.join("\n")).toEqual([]);
});

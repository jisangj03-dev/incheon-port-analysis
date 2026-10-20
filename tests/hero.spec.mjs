// 홈 첫 화면(히어로) 겹침 0 — 2026-10-15 채팅 검수: 1536×640(노트북 크롬 실측)에서 「2026-07 인천 관문을 지난 수출입 908.7억 달러」가
// LinkedIn 단추를 가렸다. 노트북 흔한 크기 9가지에서 글·단추·숫자판·지도 단추가 서로 겹치지 않는지 본다(지도 그림 위 겹침은 설계 — 글자끼리만).
import { test, expect } from "@playwright/test";
import { labelHits } from "./label-hits.mjs";
const B = "/incheon-port-analysis";
const SIZES = [1280, 1440, 1536].flatMap((w) => [640, 720, 900].map((h) => ({ width: w, height: h })));

test("히어로 — 너비 1280·1440·1536 × 높이 640·720·900 에서 글·단추·숫자판·지도 단추 겹침 0", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop-1440", "크기를 시험 안에서 바꾼다 — 한 번이면 된다");
  // CI 에서 홈 지도 움직임이 주 스레드를 막아 9번 여는 동안 90초를 넘었다(QA 185) — 움직임만 끈다(배치는 같다 · 따라가기 시험과 같은 방법)
  test.setTimeout(240_000);
  await page.emulateMedia({ reducedMotion: "reduce" });
  const bad = [];
  for (const vp of SIZES) {
    await page.setViewportSize(vp);
    await page.goto(`${B}/`, { waitUntil: "load" });
    await page.waitForTimeout(400);
    const hits = await page.evaluate(() => {
      const sel = [".live__text > *", ".live__cta a", ".live__cta button", ".live__hud > *", ".live__ctl"];
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
    // 숫자판은 무대 안에 있어야 한다(무대가 늘어난 뒤에도 바닥에 붙어 있다)
    const inStage = await page.evaluate(() => { const s = document.getElementById("live-stage").getBoundingClientRect(), h = document.getElementById("fm-hud").getBoundingClientRect(); return h.top >= s.top && h.bottom <= s.bottom + 1; });
    if (!inStage) bad.push(`${vp.width}×${vp.height} 숫자판이 무대 밖`);
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
  await page.emulateMedia({ reducedMotion: "reduce" });
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

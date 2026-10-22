// 홈 지도 이름표(.fm-lb) 중 보이는 것이 글 블록과 겹치는 쌍 — hero.spec · autoplay.spec 이 같이 쓴다(#67 ③)
// [2026-10-22 시안 v3] 지도는 첫 화면 아래 「지금 숫자」 절(#now-axes)로 갔다 — 이웃 글 = .now__text · 첫 화면 글(.live__text)도 그대로 본다
export const labelHits = (page) => page.evaluate(() => {
  const R = (e) => e.getBoundingClientRect(), txt = [...document.querySelectorAll(".live__text > *, .live__text a, .live__text button, .now__text > *, .now__text a")].map((e) => [e.className?.toString().split(" ")[0] || e.tagName, R(e)]);
  const out = [];
  for (const l of document.querySelectorAll(".fm-lb")) {
    if (getComputedStyle(l).visibility === "hidden") continue;
    const a = R(l); if (!a.width) continue;
    for (const [n, c] of txt) { const ox = Math.min(a.right, c.right) - Math.max(a.left, c.left), oy = Math.min(a.bottom, c.bottom) - Math.max(a.top, c.top); if (ox > 1 && oy > 1) out.push(`${(l.textContent || "").slice(0, 10)} × ${n}`); }
  }
  return out;
});

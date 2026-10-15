// 그림 속 글자 명암비(2026-10-14 채팅 검수 ② — 맥주 게임 선 끝 「유통」 라벨이 연한 청회색이라 안 읽혔다).
// Lighthouse 접근성 검사는 HTML 글자만 보고 SVG 글자(fill)는 안 본다 — 그래서 따로 잰다. 기준 WCAG AA: 4.5:1(큰 글자 24px↑ · 굵은 18.66px↑ 은 3:1).
// 바탕 = 가장 가까운 조상의 불투명 배경색(없으면 흰색). 투명도·그림자 글자 테두리는 계산에 넣지 않는다(보수적).
export const SEL = "svg text, .h-lb, .h-lb *, .ds-label, .ds-label *, .ds-depth, .f-tag";
export async function lowContrast(page, sel = SEL) {
  return page.evaluate((sel) => {
    const rgb = (s) => { const m = s.match(/rgba?\(([^)]+)\)/); if (!m) return null; const [r, g, b, a = 1] = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { r, g, b, a }; };
    const lum = ({ r, g, b }) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
    const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor); if (c && c.a > 0.9) return c; } return { r: 255, g: 255, b: 255 }; };
    const vis = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) < 0.05) return false; } return true; };
    const out = [];
    for (const el of document.querySelectorAll(sel)) {
      const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
      if (!own || !vis(el)) continue;
      const r = el.getBoundingClientRect(); if (r.width < 1) continue;
      const cs = getComputedStyle(el);
      const fg = rgb(el instanceof SVGElement ? cs.fill : cs.color); if (!fg) continue;
      const bg = bgOf(el.closest("svg")?.parentElement || el);
      const L1 = lum(fg), L2 = lum(bg), ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      const px = parseFloat(cs.fontSize), bold = Number(cs.fontWeight) >= 700;
      const need = px >= 24 || (bold && px >= 18.66) ? 3 : 4.5;
      if (ratio < need) out.push(`「${el.textContent.trim().slice(0, 14)}」 ${ratio.toFixed(2)}:1 < ${need} (${cs.fill !== "none" && el instanceof SVGElement ? cs.fill : cs.color})`);
    }
    return out;
  }, sel);
}

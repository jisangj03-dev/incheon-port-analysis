// 라벨 겹침 판정(2026-10-14 채팅 검수 ①) — 지면에 보이는 라벨끼리 경계 상자가 겹치면 읽히지 않는다.
// 라벨 = 지도·해도 이름표(.h-lb · .ds-label · .ds-depth) · 따라가기 꼬리표(.f-tag) · 차트·그림 안 글자(svg text).
// 보이는 것만 센다: 크기 0 · display:none · visibility:hidden · 투명도 0(조상 포함)은 뺀다. 1px 미만 스침은 겹침으로 안 본다.
export const SEL = ".h-lb, .ds-label, .ds-depth, .f-tag, svg text, [data-label]";
export async function overlaps(page, sel = SEL) {
  return page.evaluate((sel) => {
    const vis = (el) => {
      for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) < 0.05) return false;
      }
      return true;
    };
    const els = [...document.querySelectorAll(sel)].filter((el) => !el.closest("[aria-hidden='true'] [data-overlap-skip], [data-overlap-skip]"));
    const boxes = [];
    for (const el of els) {
      if (!vis(el) || !(el.textContent || "").trim()) continue;
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
      // 바깥 라벨이 안쪽 글자를 품는 경우(라벨 안의 숫자 등)는 같은 라벨로 본다
      boxes.push({ el, r, name: `${el.tagName.toLowerCase()}.${String(el.className.baseVal ?? el.className).split(" ")[0]}「${el.textContent.trim().slice(0, 16)}」` });
    }
    const out = [];
    for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
      const a = boxes[i], b = boxes[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const w = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left), h = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (w > 1 && h > 1) out.push(`${a.name} × ${b.name} (${Math.round(w)}×${Math.round(h)}px)`);
    }
    return { n: boxes.length, out };
  }, sel);
}

// 라벨 충돌 회피(2026-10-14 채팅 검수 ① — 지도 390 첫 화면에서 인천공항·남항·국제여객부두 이름표가 겹쳤다).
// 값이 큰 점부터 자리를 잡는다. 자리 후보 = 점 둘레 8방향 × 거리 4단(가까이 → 멀리). 이미 잡힌 이름표·점·막힌 칸과
// 겹치지 않는 첫 후보를 쓰고, 첫 단보다 멀리 나가면 점에서 이름표까지 가는 지시선을 긋는다. 다 겹치면 덜 겹치는 자리.
// 좌표는 모두 host 안의 화면 px. 이름표 요소는 position:absolute 여야 한다(left/top 을 여기서 준다).
export type LabelItem = { el: HTMLElement; x: number; y: number; r: number; pri: number };
type Box = { l: number; t: number; r: number; b: number };

const area = (a: Box, b: Box) => Math.max(0, Math.min(a.r, b.r) - Math.max(a.l, b.l)) * Math.max(0, Math.min(a.b, b.b) - Math.max(a.t, b.t));

export function placeLabels(host: HTMLElement, items: LabelItem[], opt: { pad?: number; block?: Box[]; lines?: SVGSVGElement | null; gap?: number } = {}) {
  const W = host.clientWidth, H = host.clientHeight, pad = opt.pad ?? 4, gap = opt.gap ?? 2;
  const placed: Box[] = [...(opt.block || [])];
  // 점 자체도 막는다(이름표가 다른 점을 덮지 않게)
  for (const it of items) placed.push({ l: it.x - it.r, t: it.y - it.r, r: it.x + it.r, b: it.y + it.r });
  let svg = "";
  const order = [...items].sort((a, b) => b.pri - a.pri);
  for (const it of order) {
    const w = it.el.offsetWidth, h = it.el.offsetHeight;
    let best: { box: Box; s: number; ring: number } | null = null;
    for (let ring = 0; ring < 4 && !(best && best.s === 0); ring++) {
      const d = it.r + 5 + ring * 18, k = d * 0.72;
      const cand: [number, number][] = [
        [it.x + d, it.y - h / 2], [it.x - d - w, it.y - h / 2], [it.x + k, it.y - k - h], [it.x + k, it.y + k],
        [it.x - k - w, it.y - k - h], [it.x - k - w, it.y + k], [it.x - w / 2, it.y - d - h], [it.x - w / 2, it.y + d],
      ];
      for (const [l, t] of cand) {
        const box = { l, t, r: l + w, b: t + h };
        const g = { l: l - gap, t: t - gap, r: l + w + gap, b: t + h + gap };
        let s = placed.reduce((a, p) => a + area(g, p), 0);
        // 칸 밖으로 나가면 큰 벌점(잘려서 안 읽힌다)
        const out = Math.max(0, pad - l) + Math.max(0, l + w - (W - pad)) + Math.max(0, pad - t) + Math.max(0, t + h - (H - pad));
        s += out * 1000;
        if (!best || s < best.s) best = { box, s, ring };
        if (s === 0) break;
      }
    }
    const b = best!.box;
    it.el.style.left = `${b.l.toFixed(1)}px`; it.el.style.top = `${b.t.toFixed(1)}px`; it.el.style.transform = "none";
    it.el.dataset.ring = String(best!.ring);
    if (best!.s > 0) it.el.dataset.collide = "1"; else delete it.el.dataset.collide;
    placed.push(b);
    if (best!.ring > 0) {
      // 지시선 — 점 가장자리에서 이름표의 가장 가까운 점까지
      const cx = Math.min(Math.max(it.x, b.l), b.r), cy = Math.min(Math.max(it.y, b.t), b.b);
      const dx = cx - it.x, dy = cy - it.y, L = Math.hypot(dx, dy) || 1;
      svg += `<line x1="${(it.x + (dx / L) * it.r).toFixed(1)}" y1="${(it.y + (dy / L) * it.r).toFixed(1)}" x2="${cx.toFixed(1)}" y2="${cy.toFixed(1)}"/>`;
    }
  }
  if (opt.lines) { opt.lines.setAttribute("viewBox", `0 0 ${W} ${H}`); opt.lines.innerHTML = svg; }
  return placed;
}

/** host 안 요소들의 경계 상자(host 기준 px) — 이름표가 피해야 할 칸(눈금 글자 등) */
export function boxesOf(host: HTMLElement, els: Iterable<Element>): Box[] {
  const o = host.getBoundingClientRect();
  return [...els].map((e) => { const r = e.getBoundingClientRect(); return { l: r.left - o.left, t: r.top - o.top, r: r.right - o.left, b: r.bottom - o.top }; }).filter((b) => b.r > b.l && b.b > b.t);
}

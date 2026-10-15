// 지면 눈 검사(2026-10-14 채팅 검수 — 수요예측의 옛 상자·잘린 「마지막 갱신」·선박 차트에서 안 보이던 인천 선).
//  · mainSeries: 차트 주 계열([data-main])이 실제로 보인다 — 신호색(주홍) · 크기 0 아님 · 그림 칸 안 · 같은 그림의 다른 선보다 뒤에 그려져 맨 앞
//  · clipped: 그림 속 글자가 그림 칸 밖으로 나가 잘리지 않는다 · 날짜·숫자 칸과 「마지막 갱신 날짜」가 한 줄
//  · boxes: 해도 원칙(상자 없음) — 본문에 테두리 네 변 + 바탕색을 가진 상자가 없다(단추·입력은 뺀다)
export async function mainSeries(page) {
  return page.evaluate(() => {
    const SIGNAL = "rgb(179, 54, 30)";
    return [...document.querySelectorAll("[data-main]")].map((el) => {
      const svg = el.ownerSVGElement, r = el.getBoundingClientRect(), s = svg.getBoundingClientRect();
      const cs = getComputedStyle(el);
      const lines = [...svg.querySelectorAll("polyline, path, line")].filter((x) => x.tagName !== "line");
      const inside = r.left >= s.left - 1 && r.right <= s.right + 1 && r.top >= s.top - 1 && r.bottom <= s.bottom + 1;
      return { name: el.getAttribute("data-main"), stroke: cs.stroke, signal: cs.stroke === SIGNAL, w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top), inside,
        front: lines.indexOf(el) === lines.length - 1, opacity: Number(cs.strokeOpacity) * Number(cs.opacity) };
    });
  });
}
export async function clipped(page) {
  return page.evaluate(() => {
    const out = [];
    const vis = (el) => { for (let e = el; e && e.nodeType === 1; e = e.parentElement) { const c = getComputedStyle(e); if (c.display === "none" || c.visibility === "hidden" || Number(c.opacity) < 0.05) return false; } return true; };
    for (const t of document.querySelectorAll("svg text")) {
      if (!vis(t) || !t.textContent.trim()) continue;
      const svg = t.ownerSVGElement; if (!svg || getComputedStyle(svg).overflow === "visible") continue;
      const r = t.getBoundingClientRect(), s = svg.getBoundingClientRect();
      if (r.width < 1) continue;
      if (r.left < s.left - 1 || r.right > s.right + 1 || r.top < s.top - 1 || r.bottom > s.bottom + 1) out.push(`그림 밖으로 잘림 「${t.textContent.trim().slice(0, 16)}」`);
    }
    // 한 줄인가 — 글자 노드의 줄 상자만 센다(<code> 같은 안쪽 상자의 여백 때문에 몇 px 어긋난 것은 같은 줄 · 3px 안)
    const oneLine = (el) => {
      const tops = [], w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let n = w.nextNode(); n; n = w.nextNode()) { const rg = document.createRange(); rg.selectNodeContents(n); for (const q of rg.getClientRects()) if (q.width > 0) tops.push(q.top); }
      return tops.every((t) => Math.abs(t - tops[0]) <= 3);
    };
    for (const el of document.querySelectorAll(".updated__k")) if (vis(el) && !oneLine(el)) out.push(`「${el.textContent.trim()}」 줄바꿈`);
    for (const td of document.querySelectorAll("main td, main th")) {
      const x = td.textContent.trim();
      if (vis(td) && /^[\d\s.,%+\-−–·()]+$/.test(x) && x.length <= 14 && !oneLine(td)) out.push(`표 칸 숫자 쪼개짐 「${x}」`);
    }
    return out;
  });
}
export async function boxes(page) {
  return page.evaluate(() => {
    const bodyBg = getComputedStyle(document.body).backgroundColor, out = [];
    for (const el of document.querySelectorAll("main *")) {
      if (/^(BUTTON|INPUT|SELECT|TEXTAREA|A|SUMMARY|svg|path|polyline|line|circle|rect|text|g|IMG|CANVAS)$/i.test(el.tagName) || el.closest("button, .s-btn, .maplibregl-map, svg, canvas")) continue;
      const c = getComputedStyle(el);
      const four = ["Top", "Right", "Bottom", "Left"].every((k) => parseFloat(c[`border${k}Width`]) > 0 && c[`border${k}Style`] !== "none");
      const bg = c.backgroundColor, filled = !/rgba?\(0, 0, 0, 0\)|transparent/.test(bg) && bg !== bodyBg;
      const r = el.getBoundingClientRect();
      if (four && filled && r.width > 120 && r.height > 60) out.push(`${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]} (${Math.round(r.width)}×${Math.round(r.height)})`);
    }
    return out;
  });
}

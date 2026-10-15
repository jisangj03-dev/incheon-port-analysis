// 인천항 일일 맥박(실무 도구 · Q1) — 일별 입항 막대 + 7일 이동평균 선 + 「평소」(직전 91일 평균) 점선 + 최근 7일 띠.
// 서버(첫 그림 · 정지 화면)와 브라우저(조작 뒤 다시 그림)가 같은 함수로 SVG 문자열을 만든다 — 화면 둘이 갈라지지 않는다.
export type Day = { d: string; calls: number; imp: number; exp: number; [k: string]: number | string };
export type Judge = { recent_from: string; recent_to: string; base_from: string; base_to: string; recent_avg: number; base_avg: number; pct: number; word: string; by_type: Record<string, number>; base_by_type: Record<string, number> };

const P = { l: 34, r: 8, t: 14, b: 26 };
export const val = (x: Day, k: string) => Number(k === "all" ? x.calls : x[k]) || 0;
export const mean = (a: number[]) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : 0);

/** 어긋난 달 목록을 「2025-01~2026-04」처럼 묶는다 */
export function ranges(ms: string[]) {
  const nx = (m: string) => { let [y, mo] = m.split("-").map(Number); mo++; if (mo > 12) { y++; mo = 1; } return `${y}-${String(mo).padStart(2, "0")}`; };
  const out: string[][] = [];
  for (const m of [...ms].sort()) { const l = out[out.length - 1]; if (l && nx(l[1]) === m) l[1] = m; else out.push([m, m]); }
  return out.map(([a, b]) => (a === b ? a : `${a}~${b}`)).join(" · ");
}

/** 최근 7일 ÷ 그 앞 91일 — 선종을 골랐을 때 브라우저에서 같은 규칙으로 다시 잰다(선커밋 §4) */
export function judgeOf(days: Day[], k: string, recent = 7, base = 91, thr = 10) {
  const rec = days.slice(-recent).map((x) => val(x, k)), bs = days.slice(-(recent + base), -recent).map((x) => val(x, k));
  const r = mean(rec), b = mean(bs), pct = b ? 100 * (r / b - 1) : 0;
  return { r, b, pct, word: pct > thr ? "평소보다 많다" : pct < -thr ? "평소보다 적다" : "평소 수준" };
}

/** odd = 해수부 월 통계와 어긋난 달(YYYY-MM) — 그 달 막대는 흐리게(원천 수집 변동 · pulse_derive.mof_check) */
export function pulseSvg(days: Day[], k: string, span: number, recent = 7, base = 91, odd: string[] = [], W = 1000, H = 300) {
  // 브라우저는 실제 폭을 W 로 넘긴다 — viewBox 를 화면 폭에 맞춰야 390 에서 눈금 글자가 찌그러지지 않는다
  const all = days, s = all.slice(-span), n = s.length;
  const v = s.map((x) => val(x, k));
  const roll = s.map((_, i) => { const j = all.length - n + i; return mean(all.slice(Math.max(0, j - 6), j + 1).map((x) => val(x, k))); });
  const b = mean(all.slice(-(recent + base), -recent).map((x) => val(x, k)));
  const top = Math.max(4, ...v, b * 1.3), step = niceStep(top), ymax = Math.ceil(top / step) * step;
  const iw = W - P.l - P.r, ih = H - P.t - P.b, bw = iw / n;
  const X = (i: number) => P.l + i * bw, Y = (y: number) => P.t + ih - (y / ymax) * ih;
  let g = "<g data-furniture>"; // 눈금·달 이름 = 지면의 틀(데이터 주장 아님)
  for (let y = 0; y <= ymax; y += step) g += `<line x1="${P.l}" x2="${W - P.r}" y1="${Y(y).toFixed(1)}" y2="${Y(y).toFixed(1)}" class="pg"/><text x="${P.l - 6}" y="${(Y(y) + 4).toFixed(1)}" class="pt" text-anchor="end">${y}</text>`;
  g += "</g>";
  // 최근 7일 띠
  const r0 = X(n - recent);
  g += `<rect x="${r0.toFixed(1)}" y="${P.t}" width="${(W - P.r - r0).toFixed(1)}" height="${ih}" class="pr"/>`;
  // 막대 — 자라나는 움직임은 CSS(--i 지연)
  const gap = bw > 4 ? 1 : 0.3;
  g += `<g class="pb">` + v.map((y, i) => `<rect x="${(X(i) + gap / 2).toFixed(2)}" y="${Y(y).toFixed(1)}" width="${Math.max(0.6, bw - gap).toFixed(2)}" height="${(Y(0) - Y(y)).toFixed(1)}" style="--i:${i}"${i >= n - recent ? ' class="on"' : odd.includes(s[i].d.slice(0, 7)) ? ' class="odd"' : ""}><title>${s[i].d} · ${y}척</title></rect>`).join("") + `</g>`;
  // 평소(직전 91일 평균) 점선 — 그 기간 위에만
  const b0 = Math.max(0, n - recent - base);
  g += `<line x1="${X(b0).toFixed(1)}" x2="${r0.toFixed(1)}" y1="${Y(b).toFixed(1)}" y2="${Y(b).toFixed(1)}" class="pa"/><text x="${(X(b0) + 4).toFixed(1)}" y="${(Y(b) - 6).toFixed(1)}" class="pt pa-t">평소 ${b.toFixed(1)}척/일</text>`;
  // 7일 이동평균
  g += `<path class="pl" pathLength="1" d="${roll.map((y, i) => `${i ? "L" : "M"}${(X(i) + bw / 2).toFixed(1)} ${Y(y).toFixed(1)}`).join("")}"/>`;
  // 달 눈금
  g += "<g data-furniture>";
  const every = W < 600 ? 2 : 1; let mi = 0;
  s.forEach((x, i) => { if (x.d.endsWith("-01") && mi++ % every === 0) g += `<line x1="${X(i).toFixed(1)}" x2="${X(i).toFixed(1)}" y1="${Y(0)}" y2="${Y(0) + 5}" class="pg"/><text x="${(X(i) + 3).toFixed(1)}" y="${H - 6}" class="pt">${x.d.slice(2, 7).replace("-", ".")}</text>`; });
  g += "</g>";
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" class="pulse__svg" aria-hidden="true">${g}</svg>`;
}

/** 견줌 카드의 작은 선(7일 이동평균 ÷ 평소 · 100 = 평소) */
export function sparkSvg(days: Day[], span = 120, recent = 7, base = 91) {
  const b = mean(days.slice(-(recent + base), -recent).map((x) => x.calls)) || 1;
  const s = days.slice(-span).map((_, i, a) => { const j = days.length - a.length + i; return (100 * mean(days.slice(Math.max(0, j - 6), j + 1).map((x) => x.calls))) / b; });
  const lo = Math.min(70, ...s), hi = Math.max(130, ...s), w = 240, h = 56;
  const Y = (y: number) => h - 4 - ((y - lo) / (hi - lo)) * (h - 8);
  return `<svg viewBox="0 0 ${w} ${h}" class="pulse__spark" aria-hidden="true"><line x1="0" x2="${w}" y1="${Y(100).toFixed(1)}" y2="${Y(100).toFixed(1)}" class="pa"/><path class="pl" d="${s.map((y, i) => `${i ? "L" : "M"}${((i / (s.length - 1)) * w).toFixed(1)} ${Y(y).toFixed(1)}`).join("")}"/></svg>`;
}

function niceStep(top: number) { const raw = top / 4, p = 10 ** Math.floor(Math.log10(raw)), m = raw / p; return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p; }

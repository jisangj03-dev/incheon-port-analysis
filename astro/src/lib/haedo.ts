// 해도 장면을 화면 비율에 맞춘다 — 맞출 범위(FIT)를 여백(pad)을 빼고 가득 채운다. 이름표·점 크기·선 굵기·가장자리 눈금은 화면 픽셀로.
// pad.tText 에 선택자를 주면 그 글자 덩어리 높이만큼 위를 비운다(글자 뒤로 지도가 숨지 않게).
const BB = [126.0, 37.0, 127.4, 37.9], KX = 1000 / (BB[2] - BB[0]), KY = KX / Math.cos((37.44 * Math.PI) / 180);

export function initHaedo(fig: HTMLElement, onFit?: (s: number) => void) {
  const G = JSON.parse(fig.querySelector("[data-haedo-geo]")!.textContent || "{}");
  const sea = fig.querySelector(".haedo__sea") as SVGSVGElement, grat = fig.querySelector(".haedo__grat") as SVGSVGElement;
  const fit = () => {
    const W = fig.clientWidth, H = fig.clientHeight, narrow = W < 700;
    if (!W || !H) return;
    const tt = G.pad.tText ? (document.querySelector(G.pad.tText) as HTMLElement | null)?.getBoundingClientRect().height || 0 : 0;
    // 1 보다 작은 값은 화면 비율(가로 = 폭 · 세로 = 높이) · 좁은 화면은 왼쪽 글 기둥 비율을 쓰지 않는다
    const rel = (v: number | undefined, dim: number, dflt: number) => (v == null ? dflt : v < 1 ? v * dim : v);
    const pad = { t: rel(G.pad.t, H, narrow ? 40 : 60) + tt, b: rel(G.pad.b, H, 120), l: narrow ? 24 : rel(G.pad.l, W, W * 0.18), r: narrow ? 64 : rel(G.pad.r, W, W * 0.1) };
    const [fx0, fy0, fx1, fy1] = G.FIT, bw = Math.max(1, fx1 - fx0), bh = Math.max(1, fy1 - fy0);
    let s = Math.max(0.05, Math.min((W - pad.l - pad.r) / bw, (H - pad.t - pad.b) / bh));
    let vx = fx0 - pad.l / s - ((W - pad.l - pad.r) / s - bw) / 2, vy = fy0 - pad.t / s - ((H - pad.t - pad.b) / s - bh) / 2;
    // 자료 범위 안에 가둔다 — 밖으로 나가면 땅이 직선으로 잘린다. 필요하면 조금 당겨(확대) 채운다.
    if (G.LIMIT) {
      const [lx0, ly0, lx1, ly1] = G.LIMIT;
      s = Math.max(s, W / (lx1 - lx0), H / (ly1 - ly0));
      const cw = W / s, chh = H / s, cx = vx + (W / s) / 2, cy = vy + (H / s) / 2;
      vx = Math.min(Math.max(cx - cw / 2, lx0), lx1 - cw); vy = Math.min(Math.max(cy - chh / 2, ly0), ly1 - chh);
      // 맞출 범위가 다시 들어오게(확대 뒤 가운데를 맞출 범위 쪽으로)
      vx = Math.min(Math.max(vx, fx1 - cw + pad.r / s), fx0 - pad.l / s); vx = Math.min(Math.max(vx, lx0), lx1 - cw);
      vy = Math.min(Math.max(vy, fy1 - chh + pad.b / s), fy0 - pad.t / s); vy = Math.min(Math.max(vy, ly0), ly1 - chh);
    }
    sea.setAttribute("viewBox", `${vx.toFixed(1)} ${vy.toFixed(1)} ${(W / s).toFixed(1)} ${(H / s).toFixed(1)}`);
    for (const el of fig.querySelectorAll<HTMLElement>("[data-x]")) {
      el.style.left = `${(Number(el.dataset.x) - vx) * s + Number(el.dataset.off || 10)}px`; el.style.top = `${(Number(el.dataset.y) - vy) * s}px`;
    }
    // 점 크기·선 굵기는 화면 픽셀로 고정 — 선에 vector-effect 를 쓰면 대시(그려지는 효과)가 화면 픽셀로 계산돼 끊긴다
    for (const c of fig.querySelectorAll<SVGCircleElement>("circle[data-rpx]")) c.setAttribute("r", String(Number(c.dataset.rpx) / s));
    for (const p of fig.querySelectorAll<SVGPathElement>("path[data-wpx]")) p.style.strokeWidth = String(Number(p.dataset.wpx) / s);
    // 가장자리 위경도 눈금(5′)
    const lon = (x: number) => BB[0] + (x / s + vx) / KX, lat = (y: number) => BB[3] - (y / s + vy) / KY;
    const X = (lo: number) => ((lo - BB[0]) * KX - vx) * s, Y = (la: number) => ((BB[3] - la) * KY - vy) * s;
    const dm = (deg: number) => { const d = Math.floor(deg + 1e-9), m = Math.round((deg - d) * 60); return `${d}°${String(m).padStart(2, "0")}′`; };
    let g = "";
    for (let m = Math.ceil(lat(H) * 12) * 5; m <= lat(0) * 60; m += 5) { const y = Y(m / 60); if (y < pad.t - 20 || y > H - 130) continue; g += `<line x1="0" x2="8" y1="${y}" y2="${y}"/><text x="12" y="${y + 3}">${dm(m / 60)}N</text>`; }
    const lstep = W < 600 ? 10 : 5;
    for (let m = Math.ceil((lon(0) * 60) / lstep) * lstep; m <= lon(W) * 60; m += lstep) { const x = X(m / 60); if (x > 60 && x < W - 60) g += `<line x1="${x}" x2="${x}" y1="${H}" y2="${H - 8}"/><text x="${x + 3}" y="${H - 12}">${dm(m / 60)}E</text>`; }
    grat.setAttribute("viewBox", `0 0 ${W} ${H}`); grat.innerHTML = g;
    fig.dataset.fit = "1";
    onFit?.(s);
  };
  new ResizeObserver(fit).observe(fig);
  fit();
  return fit;
}

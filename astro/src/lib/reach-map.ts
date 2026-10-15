// 수도권 배송 등시선(실무 도구 · 2026-10-14) — 출발지에서 도착 분 격자(빌드 때 계산 · tools-build/v3/osm_iso.py)를 받아,
// 0분에서 180분까지 문턱을 올리며 도달권이 번지는 장면을 그린다(1시간·2시간·3시간 띠). 바탕 = 홈과 같은 땅(Natural Earth · OSM 인천 상세).
// 투영 = 위도 보정 경위도 평면(위에서 내려다본 지도) — 등시선은 길이·넓이를 읽어야 해서 기울이지 않는다.
export type Iso = { bbox: number[]; step: number; w: number; h: number; cities: Record<string, number[]>; origins: { name: string; kind: string; lon: number; lat: number; cities: Record<string, number | null>; b64: string }[] };
type Geo = { world: number[][]; near: { land: number[][]; road: number[][] } };

// 30분 계단 여섯 — 가까울수록 진하다(자유 흐름이면 1시간 띠가 넓어 한 색으로는 안 읽혔다 · 2026-10-14 첫 실데이터)
export const STEPS = [
  { max: 30, c: [143, 38, 20], a: 0.78 },
  { max: 60, c: [179, 54, 30], a: 0.62 },
  { max: 90, c: [205, 98, 62], a: 0.5 },
  { max: 120, c: [222, 146, 110], a: 0.42 },
  { max: 150, c: [150, 160, 162], a: 0.32 },
  { max: 180, c: [120, 140, 148], a: 0.24 },
];

export class ReachMap {
  cv: HTMLCanvasElement; ctx: CanvasRenderingContext2D; iso: Iso; geo: Geo | null; o = 0; t = 180; k = 1; prep = 0; grid: Uint8Array; W = 0; H = 0; dpr = 1; // k = 시간대 배율(자유 흐름 분 × k · 내비 대조 보정) · prep = 상하차·준비 분(모든 도착에 더한다)
  view: number[]; // 보이는 경위도 범위
  field: HTMLCanvasElement; raf = 0;
  onFrame?: (r: ReachMap) => void;
  constructor(cv: HTMLCanvasElement, iso: Iso, geo: Geo | null) {
    this.cv = cv; this.ctx = cv.getContext("2d")!; this.iso = iso; this.geo = geo;
    this.view = [126.25, 36.95, 127.6, 37.9];
    this.grid = this.decode(0);
    this.field = document.createElement("canvas"); this.field.width = iso.w; this.field.height = iso.h;
    this.resize();
  }
  /** 화물차 판(고속도로 80km/h · hgv=no 길 제외) — 데이터에 b64_truck 이 있을 때만 */ truck = false;
  decode(i: number) { const O: any = this.iso.origins[i], s = atob(this.truck && O.b64_truck ? O.b64_truck : O.b64), a = new Uint8Array(s.length); for (let k = 0; k < s.length; k++) a[k] = s.charCodeAt(k); return a; }
  setOrigin(i: number) { this.o = i; this.grid = this.decode(i); }
  resize() {
    const r = this.cv.getBoundingClientRect(); this.dpr = Math.min(2, devicePixelRatio || 1);
    this.W = Math.max(1, r.width); this.H = Math.max(1, r.height);
    this.cv.width = Math.round(this.W * this.dpr); this.cv.height = Math.round(this.H * this.dpr);
    // 화면 비율에 맞춰 보이는 범위를 넓힌다(가운데 고정 · 위도 보정)
    const k = Math.cos((37.45 * Math.PI) / 180), cx = (126.25 + 127.6) / 2, cy = (36.95 + 37.9) / 2;
    let w = 127.6 - 126.25, h = 37.9 - 36.95;
    if ((w * k) / h > this.W / this.H) h = (w * k * this.H) / this.W; else w = (h * this.W) / this.H / k;
    this.view = [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2];
  }
  px(lon: number, lat: number) { const v = this.view; return [((lon - v[0]) / (v[2] - v[0])) * this.W, ((v[3] - lat) / (v[3] - v[1])) * this.H]; }
  /** 문턱 t(분)까지의 도달권을 칸 그림으로 */
  paintField() {
    const { w, h } = this.iso, img = new ImageData(w, h), d = img.data, t = this.t, g = this.grid, k = this.k, pp = this.prep;
    for (let i = 0; i < g.length; i++) {
      if (g[i] === 255) continue;
      const m = g[i] * k + pp; if (m > t || m > 180) continue;
      const b = STEPS.find((b) => m <= b.max)!; const edge = t - m < 4 * k ? 0.22 : 0;
      d[i * 4] = b.c[0]; d[i * 4 + 1] = b.c[1]; d[i * 4 + 2] = b.c[2]; d[i * 4 + 3] = Math.round(255 * Math.min(1, b.a + edge));
    }
    this.field.getContext("2d")!.putImageData(img, 0, 0);
  }
  draw() {
    const { ctx, W, H, dpr } = this; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#f3efe5"; ctx.fillRect(0, 0, W, H);
    const ring = (r: number[], close = true) => { for (let i = 0; i < r.length; i += 2) { const [x, y] = this.px(r[i], r[i + 1]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } if (close) ctx.closePath(); };
    if (this.geo) {
      ctx.beginPath(); for (const r of this.geo.world) ring(r); ctx.fillStyle = "#e7dfcc"; ctx.fill("evenodd");
      ctx.beginPath(); for (const r of this.geo.near.land) ring(r); ctx.fill();
    }
    // 도달권(부드럽게 늘려 그린다)
    this.paintField();
    const b = this.iso.bbox, [x0, y0] = this.px(b[0], b[3]), [x1, y1] = this.px(b[2], b[1]);
    ctx.imageSmoothingEnabled = true; ctx.drawImage(this.field, x0, y0, x1 - x0, y1 - y0);
    if (this.geo) { ctx.beginPath(); for (const r of this.geo.near.road) ring(r, false); ctx.strokeStyle = "rgba(90,80,64,0.32)"; ctx.lineWidth = 0.8; ctx.stroke(); }
    // 출발지
    const O = this.iso.origins[this.o], [ox, oy] = this.px(O.lon, O.lat);
    ctx.beginPath(); ctx.arc(ox, oy, 7, 0, Math.PI * 2); ctx.fillStyle = "#191714"; ctx.fill();
    ctx.beginPath(); ctx.arc(ox, oy, 7 + ((performance.now() / 40) % 18), 0, Math.PI * 2); ctx.strokeStyle = "rgba(25,23,20,0.35)"; ctx.lineWidth = 1.5; ctx.stroke();
    // 도시 점·이름(도착했으면 진하게 · 이름은 겹치면 건너뛴다)
    const boxes: number[][] = [];
    ctx.font = `500 ${this.W < 500 ? 10.5 : 12}px system-ui, sans-serif`; ctx.textBaseline = "middle";
    for (const [nm, [x, y]] of Object.entries(this.iso.cities)) {
      const [cx, cy] = this.px(x, y), m0 = ((this.truck && (O as any).cities_truck) || O.cities)[nm], m = m0 == null ? null : Math.round(m0 * this.k + this.prep), on = m != null && m <= this.t;
      ctx.beginPath(); ctx.arc(cx, cy, on ? 3.5 : 2.5, 0, Math.PI * 2); ctx.fillStyle = on ? "#191714" : "rgba(25,23,20,0.35)"; ctx.fill();
      const label = on ? `${nm} ${m}분` : nm, tw = ctx.measureText(label).width, bx = [cx + 6, cy - 7, cx + 6 + tw, cy + 7];
      if (bx[2] > this.W - 2 || boxes.some((q) => !(bx[2] < q[0] || bx[0] > q[2] || bx[3] < q[1] || bx[1] > q[3]))) continue;
      boxes.push(bx);
      ctx.lineWidth = 3; ctx.strokeStyle = "rgba(243,239,229,0.85)"; ctx.strokeText(label, cx + 6, cy);
      ctx.fillStyle = on ? "#191714" : "rgba(25,23,20,0.5)"; ctx.fillText(label, cx + 6, cy);
    }
    this.onFrame?.(this);
  }
  /** 0 → 180분을 dur 초에 번지게 */
  play(dur = 3.2, done?: () => void) {
    cancelAnimationFrame(this.raf);
    const t0 = performance.now(), reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const f = (now: number) => {
      const k = reduce ? 1 : Math.min(1, (now - t0) / (dur * 1000));
      this.t = Math.round(180 * (1 - (1 - k) ** 2)); this.draw();
      if (k < 1) this.raf = requestAnimationFrame(f); else done?.();
    };
    this.raf = requestAnimationFrame(f);
  }
}

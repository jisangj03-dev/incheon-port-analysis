// 수도권 도달 등시선(실무 도구 · 2026-10-14) — 출발지에서 도착 분 격자(빌드 때 계산 · tools-build/v3/osm_iso.py)를 받아,
// 0분에서 180분까지 문턱을 올리며 도달권이 번지는 장면을 그린다(1시간·2시간·3시간 띠). 바탕 = 홈과 같은 땅(Natural Earth · OSM 인천 상세).
// 투영 = 위도 보정 경위도 평면(위에서 내려다본 지도) — 등시선은 길이·넓이를 읽어야 해서 기울이지 않는다.
import { pace, paused } from "./motion";
export type Iso = { bbox: number[]; step: number; w: number; h: number; cities: Record<string, number[]>; origins: { name: string; kind: string; lon: number; lat: number; cities: Record<string, number | null>; b64: string; cities_truck?: Record<string, number | null>; b64_truck?: string }[] };
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
  /** 정지 그림으로 자를 띠 [위, 아래, 여백](캔버스 CSS px) — 주면 이름표는 띠 안 여백 밖이나 띠 밖에만 둔다(홈 띠 그림 · og-cards.mjs · 10/22 화면 판정: 그림 끝에 닿은 이름표) */ crop?: number[];
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
    // 화면 비율에 맞춰 보이는 범위를 정한다 — 계산 격자(bbox) **안쪽만** 잘라 보인다(넓히면 격자 끝이 세로 직선·회색 상자로 드러났다 · 화면 판정 10/20)
    const B = this.iso.bbox, k = Math.cos((37.45 * Math.PI) / 180);
    // 표에 든 도시가 모두 틀 안에 들게 — 도시 범위(+여백)를 화면 비율로 넓힌 만큼 보인다(6차 화면 판정: 1280·1520 에서 「평택 103분」 점이 틀 밖)
    const C = [...Object.values(this.iso.cities), ...this.iso.origins.map((o) => [o.lon, o.lat])], padd = 0.06;
    const c0 = Math.min(...C.map((c) => c[0])) - padd, c2 = Math.max(...C.map((c) => c[0])) + padd, c1 = Math.min(...C.map((c) => c[1])) - padd, c3 = Math.max(...C.map((c) => c[1])) + padd;
    let w = c2 - c0, h = c3 - c1;
    if ((w * k) / h > this.W / this.H) h = (w * k * this.H) / this.W; else w = (h * this.W) / this.H / k;
    // 계산 격자 밖은 보이지 않게(격자 끝이 직선으로 드러났다) — 격자보다 크면 격자에 맞춘다
    if (w > B[2] - B[0]) { const f = (B[2] - B[0]) / w; w *= f; h *= f; }
    if (h > B[3] - B[1]) { const f = (B[3] - B[1]) / h; w *= f; h *= f; }
    const cl = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
    const cx = cl((c0 + c2) / 2, B[0] + w / 2, B[2] - w / 2), cy = cl((c1 + c3) / 2, B[1] + h / 2, B[3] - h / 2);
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
    // 출발지 이름(2차 화면 판정 — 고리 두른 점에 이름이 없었다)
    ctx.font = `700 ${this.W < 500 ? 12.5 : 13}px system-ui, sans-serif`; ctx.textBaseline = "middle"; ctx.lineWidth = 3.5; ctx.strokeStyle = "rgba(243,239,229,0.9)";
    // 도시 점 자리 = 모든 이름표가 피할 자리(4차 화면 판정: 「용인 기흥」 점이 「수원 72분」 글자 한가운데 · 출발지 이름표가 다른 점까지 뻗었다)
    const dots = Object.values(this.iso.cities).map(([x, y]) => { const [cx, cy] = this.px(x, y); return [cx - 4, cy - 4, cx + 4, cy + 4]; });
    const clash = (bx: number[], list: number[][]) => list.some((q) => !(bx[2] < q[0] || bx[0] > q[2] || bx[3] < q[1] || bx[1] > q[3]));
    const oname = `출발 · ${O.name}`, ow = ctx.measureText(oname).width;
    // 출발점 고리(반지름 7→18)와 겹치지 않는 거리 — 이름표 바탕 상자가 고리를 덮었다(10/22 화면 3차 판정 경미)
    const fits = (bx: number[]) => { const c = this.crop; return !c || (bx[1] >= c[0] + c[2] && bx[3] <= c[1] - c[2]) || bx[3] <= c[0] || bx[1] >= c[1]; }; // 자를 띠 안 여백 밖 · 또는 띠 밖
    //   바탕 상자는 bx 보다 2px 더 칠한다 — 옆 후보 24px 이면 칠한 모서리(20, ±6)까지 20.9px > 고리 18 + 선 0.75 · 위·아래 28px 이면 20px
    //   순서는 예전 그대로(왼쪽 위 먼저 — 10/22 사실 대조: 순서를 바꿔 넓은 화면에서 이름표가 오른쪽으로 옮겨 갔다)
    const all = [[ox - 24 - ow, oy - 14], [ox + 24, oy - 14], [ox - ow / 2, oy - 28], [ox - ow / 2, oy + 28], [ox - 24 - ow, oy + 14], [ox + 24, oy + 14]]
      .map(([ax, ay]) => ({ ax, ay, bx: [ax - 2, ay - 8, ax + ow + 2, ay + 8] })).filter((c) => c.bx[0] >= 2 && c.bx[2] <= this.W - 2 && c.bx[1] >= 2 && c.bx[3] <= this.H - 2);
    const oc = all.filter((c) => fits(c.bx));
    // 출발지 이름은 출발점 바로 옆(왼쪽·오른쪽 위 둘 중 화면에 드는 쪽)에 바탕 상자와 함께 — 도시 점을 피해 멀리 가면 다른 점의 이름처럼 읽혔다(8차 화면 판정 · 390) · 도시 이름표가 이 자리를 피한다
    const og = oc.slice(0, 2).find((c) => !clash(c.bx, dots)) || oc[0] || all[0] || { ax: ox + 24, ay: oy - 14, bx: [ox + 22, oy - 22, ox + 26 + ow, oy - 6] }; // 자를 띠 때문에 다 걸러지면 화면 안 자리(고리와 떨어진 거리는 같다)
    ctx.fillStyle = "rgba(243,239,229,0.92)"; ctx.fillRect(og.bx[0] - 2, og.bx[1], og.bx[2] - og.bx[0] + 4, og.bx[3] - og.bx[1]);
    ctx.fillStyle = "#191714"; ctx.fillText(oname, og.ax, og.ay);
    const oBox = og.bx; // 도시 이름표가 출발지 이름을 덮지 않게(3차 화면 판정 · 390)
    ctx.beginPath(); ctx.arc(ox, oy, 7 + ((performance.now() / 40) % 11), 0, Math.PI * 2); ctx.strokeStyle = "rgba(25,23,20,0.35)"; ctx.lineWidth = 1.5; ctx.stroke();
    // 도시 점·이름(도착했으면 진하게 · 이름은 겹치면 건너뛴다)
    const boxes: number[][] = [oBox, [ox - 20, oy - 20, ox + 20, oy + 20]]; // 출발점 고리 최대 반지름 18 + 선 — ±9 였을 때 김포 이름표가 고리에 맞닿아 보였다(35차 화면 판정 경미 · 2026-10-23)
    ctx.font = `500 12px system-ui, sans-serif`; ctx.textBaseline = "middle"; // 좁은 화면도 12px — 10.5px 은 홈 띠 그림에서 10px 로 읽혔다(10/22 화면 판정 경미)
    for (const [nm, [x, y]] of Object.entries(this.iso.cities)) {
      const [cx, cy] = this.px(x, y), m0 = ((this.truck && (O as any).cities_truck) || O.cities)[nm], m = m0 == null ? null : Math.round(m0 * this.k + this.prep), on = m != null && m <= this.t;
      const label = on ? `${nm} ${m}분` : nm, tw = ctx.measureText(label).width;
      // 이름표 자리 넷(오른쪽·왼쪽·위·아래)을 차례로 — 모두 막히면 그때만 점도 뺀다(이름 없는 점 0 · 3차 화면 판정: 「용인 기흥」이 빠져 18곳인데 점 17)
      const cand = [[cx + 6, cy], [cx - 6 - tw, cy], [cx - tw / 2, cy - 13], [cx - tw / 2, cy + 13], [cx + 5, cy - 11], [cx - 5 - tw, cy - 11], [cx + 5, cy + 11], [cx - 5 - tw, cy + 11],
        // 틀 끝 점 — 위·아래 자리를 틀 안으로 당긴 변형(점은 이름표 폭 안에 남는다) · 좁은 화면 오른쪽 끝 이천이 자리를 못 찾아 빠졌다(35차 화면 판정 경미 · 2026-10-23)
        [Math.max(2, Math.min(this.W - 2 - tw, cx - tw / 2)), cy - 13], [Math.max(2, Math.min(this.W - 2 - tw, cx - tw / 2)), cy + 13]];
      const others = dots.filter((d) => !(d[0] === cx - 4 && d[1] === cy - 4));
      let lx = 0, ly = 0, hit = true;
      for (const [ax, ay] of cand) { const bx = [ax, ay - 7, ax + tw, ay + 7]; if (bx[0] < 2 || bx[2] > this.W - 2 || bx[1] < 2 || bx[3] > this.H - 2 || !fits(bx)) continue; if (clash(bx, boxes) || clash(bx, others)) continue; lx = ax; ly = ay; hit = false; boxes.push(bx); break; }
      if (hit) continue;
      ctx.beginPath(); ctx.arc(cx, cy, on ? 3.5 : 2.5, 0, Math.PI * 2); ctx.fillStyle = on ? "#191714" : "rgba(25,23,20,0.35)"; ctx.fill();
      ctx.lineWidth = 3; ctx.strokeStyle = "rgba(243,239,229,0.85)"; ctx.strokeText(label, lx, ly);
      ctx.fillStyle = on ? "#191714" : "rgba(25,23,20,0.5)"; ctx.fillText(label, lx, ly);
    }
    this.onFrame?.(this);
  }
  /** 번지는 중인가를 알린다(지면의 「번지기 멈춤」 단추) */ onPlay?: (on: boolean) => void;
  /** 번지기를 멈추고 끝 그림(180분) */
  stopPlay() { cancelAnimationFrame(this.raf); this.t = 180; this.draw(); this.onPlay?.(false); }
  /** 0 → 180분을 dur 초에 번지게 */
  play(dur = 3.2, done?: () => void) {
    cancelAnimationFrame(this.raf);
    // 번지는 시간 = 자료(0→180분) — 동작 줄이기면 천천히 · 멈춤을 골랐으면 바로 끝 그림(품질기준 Q7)
    // [2026-10-20] 동작 줄이기면 번지기 없이 답(끝 그림) — 번지기는 한 번 지나가는 장식이라 멈춤 단추를 둘 자리가 아니다(화면 판정 Q7)
    // 동작 줄이기 = 천천히 번진다(품질기준 Q7 — 데이터는 움직인다) · 「번지기 멈춤」 단추(stopPlay)로 바로 끝 그림 · 멈춤을 골랐으면 처음부터 끝 그림
    const t0 = performance.now(), still = paused(), d = dur / pace();
    this.onPlay?.(!still);
    const f = (now: number) => {
      const k = still ? 1 : Math.min(1, (now - t0) / (d * 1000));
      this.t = Math.round(180 * (1 - (1 - k) ** 2)); this.draw();
      if (k < 1) this.raf = requestAnimationFrame(f); else { this.onPlay?.(false); done?.(); }
    };
    this.raf = requestAnimationFrame(f);
  }
}

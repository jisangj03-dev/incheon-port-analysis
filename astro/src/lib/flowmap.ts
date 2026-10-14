// 살아 있는 지도 — 기울인 해도 위로 월 통계를 흐름으로 그린다(2026-10-14 선장님 판정 「동적인 콘텐츠」 · 채팅 위임 A).
// 바깥 의존 0: maplibre·deck.gl 을 싣지 않고 캔버스 2D 에 원근 투영을 직접 한다(모바일 성능 90 · 외부 요청 0 · 내장 자료만).
// 원리: 셰입맵(shipmap.org)처럼 점이 꼬리를 끌며 흐른다. 단 실시간 위치가 아니다 — 그 달 교역액만큼 점을 내보낸다(점 하나 ≈ unit 억 달러).
// 투영: 웹 메르카토르 평면을 카메라(중심·줌·기울기·방위)로 본다. 같은 식을 빌드 때 정지 그림에도 쓴다(projector).

export type Cam = { lon: number; lat: number; zoom: number; pitch: number; bearing: number; ox?: number; oy?: number }; // ox·oy = 화면 중심을 옮기는 몫(글자 자리 비우기)
export const mx = (lon: number) => (lon + 180) / 360;
export const my = (lat: number) => { const s = Math.sin((lat * Math.PI) / 180); return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI); };
const R_EARTH_M = 40075016.7; // 적도 둘레 — 메르카토르 1 = 이 길이(위도 보정은 cos)

/** 카메라 → 투영 함수. (X,Y)=메르카토르 0..1, h=높이(메르카토르 단위). 화면 밖·카메라 뒤는 깊이를 잘라 아래로 밀어낸다. */
export function projector(c: Cam, W: number, H: number) {
  const S = 512 * 2 ** c.zoom, cx = mx(c.lon) * S, cy = my(c.lat) * S;
  const b = (c.bearing * Math.PI) / 180, p = (c.pitch * Math.PI) / 180;
  const cb = Math.cos(b), sb = Math.sin(b), cp = Math.cos(p), sp = Math.sin(p);
  const D = 1.5 * H, near = 0.12 * D, ox = c.ox || 0, oy = c.oy || 0;
  const fn = (X: number, Y: number, h = 0, out: number[] = [0, 0, 0]) => {
    const dx = X * S - cx, dy = Y * S - cy;
    const rx = dx * cb + dy * sb, ry = -dx * sb + dy * cb, hz = h * S;
    let depth = D - ry * sp - hz * cp;
    if (depth < near) depth = near;
    const k = D / depth;
    out[0] = W * (0.5 + ox) + rx * k; out[1] = H * (0.5 + oy) + (ry * cp - hz * sp) * k; out[2] = k;
    return out;
  };
  /** 화면 → 땅(h=0) — 보이는 범위 셈 */
  const inv = (sx: number, sy: number) => {
    const x = sx - W * (0.5 + ox), y = sy - H * (0.5 + oy), den = cp * D + y * sp;
    const ry = den > 1e-6 ? (y * D) / den : -1e9;
    const rx = (x * (D - ry * sp)) / D;
    const dx = rx * cb - ry * sb, dy = rx * sb + ry * cb;
    return [(dx + cx) / S, (dy + cy) / S];
  };
  return { fn, inv, S };
}

type Data = {
  world: number[][];
  near: { bbox: number[]; land: number[][]; road: number[][]; ct: number[][] };
  flows: any;
};
type Leg = { pts: Float32Array; n: number; dur: number };
const DT = 1 / 30; // 경로 표본 간격(초)

/** 경유점 → 매끈한 곡선(캣멀–롬) → 일정한 속도(km/s)로 시간 표본. 높이 h(t) 를 받으면 아크. */
function legFrom(ll: number[][], speedKm: number, arc = 0): Leg {
  // 메르카토르로 바꾸고 촘촘히
  const P = ll.map(([lon, lat]) => [mx(lon), my(lat)]);
  const dense: number[][] = [];
  for (let i = 0; i < P.length - 1; i++) {
    const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(P.length - 1, i + 2)];
    for (let k = 0; k < 12; k++) {
      const t = k / 12, t2 = t * t, t3 = t2 * t;
      dense.push([0, 1].map((j) => 0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3)));
    }
  }
  dense.push(P[P.length - 1]);
  // 길이(km) — 메르카토르 거리 × 둘레 × cos(위도)
  const cum = [0];
  for (let i = 1; i < dense.length; i++) {
    const [x0, y0] = dense[i - 1], [x1, y1] = dense[i];
    const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y0 + y1) / 2))) ;
    const d = Math.hypot(x1 - x0, y1 - y0) * (R_EARTH_M / 1000) * Math.cos(lat);
    cum.push(cum[i - 1] + d);
  }
  const L = cum[cum.length - 1], dur = Math.max(DT * 3, L / speedKm), n = Math.ceil(dur / DT) + 1;
  const pts = new Float32Array(n * 3);
  let j = 0;
  const flat = arc ? Math.hypot(dense[dense.length - 1][0] - dense[0][0], dense[dense.length - 1][1] - dense[0][1]) : 0;
  for (let i = 0; i < n; i++) {
    const s = Math.min(L, (i / (n - 1)) * L);
    while (j < cum.length - 2 && cum[j + 1] < s) j++;
    const f = cum[j + 1] > cum[j] ? (s - cum[j]) / (cum[j + 1] - cum[j]) : 0;
    const u = s / (L || 1);
    pts[i * 3] = dense[j][0] + (dense[j + 1][0] - dense[j][0]) * f;
    pts[i * 3 + 1] = dense[j][1] + (dense[j + 1][1] - dense[j][1]) * f;
    pts[i * 3 + 2] = arc ? arc * flat * 4 * u * (1 - u) : 0;
  }
  return { pts, n, dur };
}

/** 대권(큰 원) 경유점 — 하늘 길. 경도는 끊기지 않게 이어 붙인다. */
function greatCircle(a: number[], b: number[], k = 24) {
  const r = Math.PI / 180, v = (p: number[]) => [Math.cos(p[1] * r) * Math.cos(p[0] * r), Math.cos(p[1] * r) * Math.sin(p[0] * r), Math.sin(p[1] * r)];
  const A = v(a), B = v(b), w = Math.acos(Math.min(1, A[0] * B[0] + A[1] * B[1] + A[2] * B[2]));
  const out: number[][] = [];
  for (let i = 0; i <= k; i++) {
    const t = i / k, s1 = Math.sin((1 - t) * w) / Math.sin(w), s2 = Math.sin(t * w) / Math.sin(w);
    const x = s1 * A[0] + s2 * B[0], y = s1 * A[1] + s2 * B[1], z = s1 * A[2] + s2 * B[2];
    let lon = Math.atan2(y, x) / r; const lat = Math.atan2(z, Math.hypot(x, y)) / r;
    if (out.length) { const prev = out[out.length - 1][0]; while (lon - prev > 180) lon -= 360; while (prev - lon > 180) lon += 360; }
    else { while (lon - a[0] > 180) lon -= 360; while (a[0] - lon > 180) lon += 360; }
    out.push([lon, lat]);
  }
  return out;
}

/** 두 점 사이 완만한 곡선(육상 개념선) */
function bend(a: number[], b: number[], k = 0.18) {
  const c = [(a[0] + b[0]) / 2 - (b[1] - a[1]) * k, (a[1] + b[1]) / 2 + (b[0] - a[0]) * k * 0.6];
  return [a, [(a[0] + c[0]) / 2, (a[1] + c[1]) / 2], c, [(c[0] + b[0]) / 2, (c[1] + b[1]) / 2], b];
}

const SPEED = { sea: 950, air: 2600, land: 15 }; // km/s(그림 속도 — 실제 속도 아님)
export const VIEWS: Record<string, Cam> = {
  asia: { lon: 122.5, lat: 30.5, zoom: 3.0, pitch: 46, bearing: -10, ox: 0.17, oy: 0.04 },
  incheon: { lon: 126.72, lat: 37.43, zoom: 9.1, pitch: 54, bearing: 18, ox: 0.16, oy: 0.06 },
};
/** 좁은 화면(세로) — 글자가 위에 따로 있으니 가운데로 · 조금 더 멀리 */
export const VIEWS_M: Record<string, Cam> = {
  asia: { lon: 121.0, lat: 30.0, zoom: 2.55, pitch: 44, bearing: -10, ox: 0.05, oy: -0.1 },
  incheon: { lon: 126.75, lat: 37.42, zoom: 8.45, pitch: 52, bearing: 18, ox: 0, oy: -0.08 },
};

export type Opts = { unit: number; monthSec: number; maxDpr: number; lite: boolean; onMonth?: (i: number) => void; onFrame?: (f: FlowMap) => void;
  /** 점 진하기(1 = 기본 · 따라가기처럼 배경으로 깔 때는 낮춘다) */ dim?: number;
  /** 덧그림 — 점 위·안개 아래(따라가기의 상자·길) */ overlay?: (ctx: CanvasRenderingContext2D, P: (x: number, y: number, h?: number, out?: number[]) => number[], near: boolean) => void;
  /** 카메라를 밖에서 몬다(따라가기 — 스크롤이 카메라) */ camStep?: (f: FlowMap, dt: number) => void };

export class FlowMap {
  cv: HTMLCanvasElement; ctx: CanvasRenderingContext2D; D: Data; o: Opts;
  cam: Cam; W = 0; H = 0; dpr = 1;
  legsG: Leg[] = []; gMeta: { p: number; g: number; dir: number }[] = [];
  legsL: Leg[] = []; lMeta: { g: number; d: number; dir: number }[] = [];
  gates: { id: string; lon: number; lat: number; kind: "sea" | "air" }[] = [];
  routes: { g: number; l: number; dir: number; rate: Float32Array }[] = []; // rate[month] = 점/초
  // 점(입자) — 구조체 배열 대신 평면 배열
  N = 0; pr = new Int32Array(8192); pt = new Float32Array(8192); pj = new Float32Array(8192); acc: Float32Array = new Float32Array(0);
  t = 0; month = 0; running = false; raf = 0; last = 0;
  arrive: Float32Array = new Float32Array(8); // 관문별 최근 도착(고리 반짝임)
  tour: { from: Cam; to: Cam; t0: number; dur: number } | null = null;
  touring = false; tourStep = 0; tourT = 0; views: Record<string, Cam> = VIEWS;
  private wR: { r: number[]; bb: number[] }[] = []; private nR: number[][] = []; private rdR: number[][] = []; private ctR: number[][] = [];

  constructor(cv: HTMLCanvasElement, data: Data, o: Opts, cam: Cam) {
    this.cv = cv; this.ctx = cv.getContext("2d")!; this.D = data; this.o = o; this.cam = { ...cam };
    const F = data.flows;
    this.month = F.months.length - 1;
    // 바탕 — 메르카토르로 한 번만 바꿔 둔다
    const tm = (r: number[]) => { const o: number[] = []; for (let i = 0; i < r.length; i += 2) o.push(mx(r[i]), my(r[i + 1])); return o; };
    this.wR = data.world.map((r) => { const m = tm(r); let a = 9, b = 9, c = -9, d = -9; for (let i = 0; i < m.length; i += 2) { a = Math.min(a, m[i]); c = Math.max(c, m[i]); b = Math.min(b, m[i + 1]); d = Math.max(d, m[i + 1]); } return { r: m, bb: [a, b, c, d] }; });
    this.nR = data.near.land.map(tm); this.rdR = data.near.road.map(tm); this.ctR = data.near.ct.map(tm);
    // 관문 — 바다 셋(부두군) + 하늘 하나
    for (const g of F.sea_gates) this.gates.push({ id: g.id, lon: g.lon, lat: g.lat, kind: "sea" });
    this.gates.push({ id: F.air_gate.id, lon: F.air_gate.lon, lat: F.air_gate.lat, kind: "air" });
    // 먼 길(나라 ↔ 관문) · 가까운 길(관문 ↔ 목적지) — 들어오는 길(dir 0)과 나가는 길(dir 1)
    const gIdx: Record<string, number> = {}, lIdx: Record<string, number> = {};
    F.partners.forEach((p: any, pi: number) => this.gates.forEach((g, gi) => {
      for (const dir of [0, 1]) {
        let ll: number[][], arc = 0, speed = SPEED.sea;
        if (g.kind === "sea") { const sg = F.sea_gates.find((x: any) => x.id === g.id); ll = [...p.sea, ...sg.approach, [g.lon, g.lat]]; }
        else { ll = greatCircle(p.air, [g.lon, g.lat]); arc = 0.22; speed = SPEED.air; }
        if (dir) ll = [...ll].reverse();
        gIdx[`${pi}|${gi}|${dir}`] = this.legsG.length; this.legsG.push(legFrom(ll, speed, arc)); this.gMeta.push({ p: pi, g: gi, dir });
      }
    }));
    F.dests.forEach((d: any, di: number) => this.gates.forEach((g, gi) => {
      for (const dir of [0, 1]) {
        let ll = bend([g.lon, g.lat], [d.lon, d.lat], (gi % 2 ? -1 : 1) * 0.16);
        if (dir) ll = [...ll].reverse();
        lIdx[`${gi}|${di}|${dir}`] = this.legsL.length; this.legsL.push(legFrom(ll, SPEED.land)); this.lMeta.push({ g: gi, d: di, dir });
      }
    }));
    // 빈도 — 그 달 관문 교역액 × 나라 비중 × 목적지 비중(창고 개소) × 바다 부두군 비중(컨테이너) ÷ 점 하나 값 ÷ 한 달 초
    const dSum = F.dests.reduce((s: number, d: any) => s + d.n, 0);
    F.partners.forEach((p: any, pi: number) => this.gates.forEach((g, gi) => F.dests.forEach((d: any, di: number) => {
      for (const dir of [0, 1]) {
        const rate = new Float32Array(F.months.length);
        F.months.forEach((m: any, mi: number) => {
          const sea = g.kind === "sea";
          const v = dir === 0 ? (sea ? m.port_imp : m.air_imp) : sea ? m.port_exp : m.air_exp;
          let split = 1;
          if (sea) { const T = m.teu || {}; const tot = F.sea_gates.reduce((s: number, x: any) => s + (T[x.id] || 0), 0); split = tot ? (T[g.id] || 0) / tot : 1 / F.sea_gates.length; }
          const share = (dir === 0 ? p.imp_pct : p.exp_pct) / 100;
          rate[mi] = (v * share * (d.n / dSum) * split) / this.o.unit / this.o.monthSec;
        });
        // 들어오면 먼 길 → 가까운 길 · 나가면 가까운 길 → 먼 길
        this.routes.push({ g: gIdx[`${pi}|${gi}|${dir}`], l: lIdx[`${gi}|${di}|${dir}`], dir, rate });
      }
    })));
    this.acc = new Float32Array(this.routes.length);
    this.arrive = new Float32Array(this.gates.length);
    this.resize();
  }

  resize() {
    const r = this.cv.getBoundingClientRect();
    this.dpr = Math.min(this.o.maxDpr, devicePixelRatio || 1);
    this.W = Math.max(1, r.width); this.H = Math.max(1, r.height);
    this.cv.width = Math.round(this.W * this.dpr); this.cv.height = Math.round(this.H * this.dpr);
  }

  /** 점 하나의 위치(t 초 지난 뒤) */
  private pos(ri: number, age: number, out: number[]) {
    const R = this.routes[ri];
    const A = R.dir === 0 ? this.legsG[R.g] : this.legsL[R.l], B = R.dir === 0 ? this.legsL[R.l] : this.legsG[R.g];
    let L = A, a = age;
    if (a > A.dur) { a -= A.dur; L = B; }
    const f = Math.min(L.n - 1.001, Math.max(0, a / DT)), i = Math.floor(f), u = f - i, p = L.pts;
    out[0] = p[i * 3] + (p[i * 3 + 3] - p[i * 3]) * u;
    out[1] = p[i * 3 + 1] + (p[i * 3 + 4] - p[i * 3 + 1]) * u;
    out[2] = p[i * 3 + 2] + (p[i * 3 + 5] - p[i * 3 + 2]) * u;
    return out;
  }
  private dur(ri: number) { const R = this.routes[ri]; return this.legsG[R.g].dur + this.legsL[R.l].dur; }

  /** 시간 한 걸음 — 낳고, 늙히고, 다 간 점은 지운다 */
  step(dt: number) {
    this.t += dt;
    const mi = this.monthAt();
    if (mi !== this.month) { this.month = mi; this.o.onMonth?.(mi); }
    for (let r = 0; r < this.routes.length; r++) {
      this.acc[r] += this.routes[r].rate[mi] * dt;
      while (this.acc[r] >= 1) {
        this.acc[r] -= 1;
        if (this.N >= this.pr.length) this.grow();
        this.pr[this.N] = r; this.pt[this.N] = this.t - Math.random() * dt; this.pj[this.N] = (Math.random() - 0.5) * 2; this.N++;
      }
    }
    // 다 간 점 지우기(뒤에서 채운다) · 관문을 지나는 순간 고리를 반짝인다
    for (let i = 0; i < this.N; i++) {
      const r = this.pr[i], age = this.t - this.pt[i], R = this.routes[r];
      const first = R.dir === 0 ? this.legsG[R.g].dur : this.legsL[R.l].dur;
      if (age >= first && age - dt < first) this.arrive[this.gMeta[R.g].g] = 1;
      if (age > this.dur(r)) { this.N--; this.pr[i] = this.pr[this.N]; this.pt[i] = this.pt[this.N]; this.pj[i] = this.pj[this.N]; i--; }
    }
    for (let g = 0; g < this.arrive.length; g++) this.arrive[g] *= Math.exp(-dt * 3);
  }
  private grow() { const n = this.pr.length * 2, a = new Int32Array(n), b = new Float32Array(n), c = new Float32Array(n); a.set(this.pr); b.set(this.pt); c.set(this.pj); this.pr = a; this.pt = b; this.pj = c; }
  monthAt() { const n = this.D.flows.months.length; return ((((n - 1) + Math.floor(this.t / this.o.monthSec)) % n) + n) % n; }
  /** 처음에 점을 미리 깔아 둔다(빈 화면에서 시작하지 않게) — 지난 시간을 거꾸로 채운다 */
  warm(sec: number) { const t0 = this.t; this.t -= sec; const cb = this.o.onMonth; this.o.onMonth = undefined; for (let s = 0; s < sec; s += 1 / 15) this.step(1 / 15); this.t = t0; this.month = this.monthAt(); this.o.onMonth = cb; }

  // ── 그리기 ──
  draw() {
    const { ctx, W, H, dpr } = this, c = this.cam;
    const PJ = projector(c, W, H), P = PJ.fn, o = [0, 0, 0], o2 = [0, 0, 0];
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#f3efe5"; ctx.fillRect(0, 0, W, H); // 바다 = 종이
    // 보이는 범위(메르카토르) — 고리마다 상자로 거른다
    const cs = [PJ.inv(0, 0), PJ.inv(W, 0), PJ.inv(0, H), PJ.inv(W, H)];
    const vb = [Math.min(...cs.map((v) => v[0])), Math.min(...cs.map((v) => v[1])), Math.max(...cs.map((v) => v[0])), Math.max(...cs.map((v) => v[1]))];
    const stride = this.o.lite && c.zoom < 5 ? 4 : 2; // 가벼운 판 · 멀리 = 꼭짓점 하나 건너(1:50m 이라 눈에 안 띈다)
    const ringPath = (r: number[], close: boolean, st = 2) => {
      P(r[0], r[1], 0, o); ctx.moveTo(o[0], o[1]);
      for (let i = st; i < r.length; i += st) { P(r[i], r[i + 1], 0, o); ctx.lineTo(o[0], o[1]); }
      if (close) ctx.closePath();
    };
    const near = c.zoom > 6.2, nb = this.D.near.bbox, nbm = [mx(nb[0]), my(nb[3]), mx(nb[2]), my(nb[1])];
    ctx.beginPath();
    for (const w of this.wR) if (!(w.bb[2] < vb[0] || w.bb[0] > vb[2] || w.bb[3] < vb[1] || w.bb[1] > vb[3])) ringPath(w.r, true, w.r.length > 40 ? stride : 2);
    ctx.fillStyle = "#e7dfcc"; ctx.fill("evenodd");
    if (near) {
      // 가까이 — 인천 상세 땅이 있는 네모는 바다로 덮고 상세 땅을 다시 칠한다(1:50m 해안선이 갯벌·섬을 뭉갠다)
      ctx.beginPath(); ringPath([nbm[0], nbm[1], nbm[2], nbm[1], nbm[2], nbm[3], nbm[0], nbm[3]], true); ctx.fillStyle = "#f3efe5"; ctx.fill();
      ctx.beginPath(); for (const r of this.nR) ringPath(r, true); ctx.fillStyle = "#e7dfcc"; ctx.fill();
      ctx.lineWidth = 0.7; ctx.strokeStyle = "#ddd4bf"; ctx.beginPath(); for (const r of this.ctR) ringPath(r, false); ctx.stroke();
      ctx.lineWidth = 1; ctx.strokeStyle = "#d3c7ad"; ctx.beginPath(); for (const r of this.rdR) ringPath(r, false); ctx.stroke();
    }
    // 길(옅게) — 먼 길은 나라마다 한 줄(신항·공항만), 가까운 길은 목적지마다
    ctx.lineWidth = 1; ctx.strokeStyle = "rgba(25,23,20,0.10)"; ctx.beginPath();
    this.legsG.forEach((L, i) => { const m = this.gMeta[i]; if (m.dir || (m.g !== 0 && m.g !== this.gates.length - 1) || (near && m.g === this.gates.length - 1)) return; this.legPath(L, P, o); });
    if (near) this.legsL.forEach((L, i) => { if (!this.lMeta[i].dir) this.legPath(L, P, o); });
    ctx.stroke();
    // 점 — 꼬리(지난 0.3초)를 끈다. 들어오는 것 = 주홍 · 나가는 것 = 바다색
    const TAIL = 0.4, heads: number[] = [], spread = near ? 5 : 2.5, maxTail = near ? 26 : 34;
    for (const dir of [1, 0]) {
      ctx.beginPath();
      for (let i = 0; i < this.N; i++) {
        const r = this.pr[i]; if (this.routes[r].dir !== dir) continue;
        const age = this.t - this.pt[i];
        this.pos(r, age, o); const h = P(o[0], o[1], o[2], o2); const x1 = h[0], y1 = h[1];
        if (x1 < -20 || x1 > W + 20 || y1 < -20 || y1 > H + 20) continue;
        this.pos(r, Math.max(0, age - TAIL), o); P(o[0], o[1], o[2], o);
        // 같은 길 위 점이 한 줄로 겹치지 않게 진행 방향의 옆으로 조금 비킨다(띠)
        let ddx = x1 - o[0], ddy = y1 - o[1]; const len = Math.hypot(ddx, ddy) || 1, j = this.pj[i] * spread;
        // 꼬리는 화면에서 최대 maxTail px — 가까이 볼 때 빠른 하늘 길 점이 화면을 가로지르는 빛줄기가 되지 않게
        if (len > maxTail) { ddx *= maxTail / len; ddy *= maxTail / len; o[0] = x1 - ddx; o[1] = y1 - ddy; }
        const jx = (-ddy / len) * j, jy = (ddx / len) * j;
        ctx.moveTo(o[0] + jx, o[1] + jy); ctx.lineTo(x1 + jx, y1 + jy);
        heads.push(x1 + jx, y1 + jy);
      }
      ctx.lineCap = "round"; ctx.lineWidth = this.o.lite ? 1.5 : 1.3;
      const dm = this.o.dim ?? 1;
      ctx.strokeStyle = dir === 0 ? `rgba(179,54,30,${0.55 * dm})` : `rgba(52,84,98,${0.45 * dm})`;
      ctx.stroke();
      // 머리 — 작은 점(꼬리보다 진하게)
      ctx.fillStyle = dir === 0 ? `rgba(179,54,30,${0.95 * dm})` : `rgba(40,70,84,${0.9 * dm})`;
      ctx.beginPath();
      for (let k = 0; k < heads.length; k += 2) { ctx.moveTo(heads[k] + 1.6, heads[k + 1]); ctx.arc(heads[k], heads[k + 1], 1.6, 0, Math.PI * 2); }
      ctx.fill(); heads.length = 0;
    }
    // 관문 — 고리가 도착할 때 반짝인다
    this.gates.forEach((g, gi) => {
      P(mx(g.lon), my(g.lat), 0, o);
      const r0 = near ? (g.kind === "air" ? 6 : 4.5) : 3.5, a = this.arrive[gi];
      ctx.beginPath(); ctx.arc(o[0], o[1], r0 + a * 7, 0, Math.PI * 2); ctx.strokeStyle = `rgba(179,54,30,${0.25 + 0.5 * a})`; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.beginPath(); ctx.arc(o[0], o[1], r0, 0, Math.PI * 2); ctx.fillStyle = "#b3361e"; ctx.fill();
    });
    // 목적지(가까이에서만) — 원 넓이 = 창고 개소
    if (near) {
      const F = this.D.flows, nmax = Math.max(...F.dests.map((d: any) => d.n));
      for (const d of F.dests) { P(mx(d.lon), my(d.lat), 0, o); ctx.beginPath(); ctx.arc(o[0], o[1], 2.5 + 9 * Math.sqrt(d.n / nmax), 0, Math.PI * 2); ctx.strokeStyle = "rgba(25,23,20,0.55)"; ctx.lineWidth = 1.2; ctx.stroke(); }
    }
    // 나라 점(멀리에서만)
    if (!near) for (const p of this.D.flows.partners) { P(mx(p.sea[0][0]), my(p.sea[0][1]), 0, o); ctx.beginPath(); ctx.arc(o[0], o[1], 2.5, 0, Math.PI * 2); ctx.fillStyle = "#191714"; ctx.fill(); }
    this.o.overlay?.(ctx, P, near);
    // 먼 곳은 종이로 흐린다(대기 원근 · 위쪽 글자 바림도 겸한다)
    const g = ctx.createLinearGradient(0, 0, 0, H * 0.42);
    g.addColorStop(0, "rgba(245,242,235,0.96)"); g.addColorStop(1, "rgba(245,242,235,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H * 0.42);
    this.o.onFrame?.(this);
  }
  private legPath(L: Leg, P: (x: number, y: number, h?: number, out?: number[]) => number[], o: number[]) {
    const s = Math.max(1, Math.floor(L.n / 60));
    for (let i = 0; i < L.n; i += s) { P(L.pts[i * 3], L.pts[i * 3 + 1], L.pts[i * 3 + 2], o); i ? this.ctx.lineTo(o[0], o[1]) : this.ctx.moveTo(o[0], o[1]); }
    const j = L.n - 1; P(L.pts[j * 3], L.pts[j * 3 + 1], L.pts[j * 3 + 2], o); this.ctx.lineTo(o[0], o[1]);
  }

  /** 화면 위 자리(이름표·누름 판정) */
  screen(lon: number, lat: number) { return projector(this.cam, this.W, this.H).fn(mx(lon), my(lat)); }

  // ── 카메라 ──
  flyTo(to: Cam, dur = 3.2) { this.tour = { from: { ...this.cam }, to: { ...to }, t0: this.t, dur }; }
  private camStep(dt: number) {
    if (this.tour) {
      const k = Math.min(1, (this.t - this.tour.t0) / this.tour.dur), e = k < 0.5 ? 4 * k * k * k : 1 - (-2 * k + 2) ** 3 / 2;
      const a = this.tour.from, b = this.tour.to;
      // 줌은 가운데서 살짝 물러났다 들어간다(비행 느낌) · 중심은 메르카토르에서 잇는다(들어갈 때는 중심을 먼저 옮긴다)
      const far = Math.min(1, Math.abs(a.zoom - b.zoom) / 3);
      this.cam.zoom = a.zoom + (b.zoom - a.zoom) * e - 0.7 * far * Math.sin(Math.PI * e);
      const ec = a.zoom < b.zoom ? Math.min(1, e * 1.35) : Math.max(0, (e - 0.26) / 0.74);
      const X = mx(a.lon) + (mx(b.lon) - mx(a.lon)) * ec, Y = my(a.lat) + (my(b.lat) - my(a.lat)) * ec;
      this.cam.lon = X * 360 - 180; this.cam.lat = (Math.atan(Math.sinh(Math.PI * (1 - 2 * Y))) * 180) / Math.PI;
      this.cam.pitch = a.pitch + (b.pitch - a.pitch) * e;
      this.cam.ox = (a.ox || 0) + ((b.ox || 0) - (a.ox || 0)) * e; this.cam.oy = (a.oy || 0) + ((b.oy || 0) - (a.oy || 0)) * e;
      let db = b.bearing - a.bearing; if (db > 180) db -= 360; if (db < -180) db += 360;
      this.cam.bearing = a.bearing + db * e;
      if (k >= 1) this.tour = null;
    } else if (this.touring) this.cam.bearing += dt * (this.cam.zoom > 6 ? 1.6 : 0.8); // 머무는 동안 천천히 돈다
    if (this.touring && !this.tour) {
      this.tourT += dt;
      const hold = this.tourStep % 2 === 0 ? 9 : 10;
      if (this.tourT > hold) { this.tourT = 0; this.tourStep++; this.flyTo(this.tourStep % 2 ? this.views.incheon : this.views.asia, 4.2); }
    }
  }

  start() {
    if (this.running) return;
    this.running = true; this.last = performance.now();
    const loop = (now: number) => {
      if (!this.running) return;
      const dt = Math.min(0.1, (now - this.last) / 1000); this.last = now;
      this.step(dt); if (this.o.camStep) this.o.camStep(this, dt); else this.camStep(dt); this.draw();
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }
  stop() { this.running = false; cancelAnimationFrame(this.raf); }
}

// 살아 있는 지도 — 기울인 해도 위로 월 통계를 흐름으로 그린다(2026-10-14 선장님 판정 「동적인 콘텐츠」 · 채팅 위임 A).
// 바깥 의존 0: maplibre·deck.gl 을 싣지 않고 캔버스 2D 에 원근 투영을 직접 한다(모바일 성능 90 · 외부 요청 0 · 내장 자료만).
// 원리: 셰입맵(shipmap.org)처럼 점이 꼬리를 끌며 흐른다. 단 실시간 위치가 아니다 — 그 달 교역액만큼 점을 내보낸다(점 하나 ≈ unit 억 달러).
// 투영: 웹 메르카토르 평면을 카메라(중심·줌·기울기·방위)로 본다. 같은 식을 빌드 때 정지 그림에도 쓴다(projector).

export type Cam = { lon: number; lat: number; zoom: number; pitch: number; bearing: number; ox?: number; oy?: number }; // ox·oy = 화면 중심을 옮기는 몫(글자 자리 비우기)
export const mx = (lon: number) => (lon + 180) / 360;
export const my = (lat: number) => { const s = Math.sin((lat * Math.PI) / 180); return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI); };
const R_EARTH_M = 40075016.7; // 적도 둘레 — 메르카토르 1 = 이 길이(위도 보정은 cos)

/** 점들이 화면 안쪽 여백(몫 l·r·t·b) 안에 다 들어오는 가장 가까운 카메라 — 줌을 낮춰 가며 찾고, 화면 중심 몫(ox·oy)으로 가운데 맞춘다.
 *  홈 첫 화면이 인천(서)·서울·경부·영동축(동)을 한 장에 담게(2026-10-20 · 글 기둥과 지도 칸이 나뉜 뒤 캔버스 모양이 폭마다 다르다) */
export function fitCam(base: Cam, W: number, H: number, pts: number[][], m = { l: 0.08, r: 0.08, t: 0.2, b: 0.18 }): Cam {
  const o = [0, 0, 0];
  for (let z = base.zoom; z > 2.2; z -= 0.05) { // 하한 2.2 — 동북아 첫 화면이 좁은 화면에서 4 까지로는 안 맞아 맞추기 전 값으로 돌아갔다(2026-10-20)
    const c: Cam = { ...base, zoom: z, ox: 0, oy: 0 };
    let ok = false;
    for (let it = 0; it < 4; it++) {
      const P = projector(c, W, H).fn; let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      for (const [lon, lat] of pts) { P(mx(lon), my(lat), 0, o); x0 = Math.min(x0, o[0]); x1 = Math.max(x1, o[0]); y0 = Math.min(y0, o[1]); y1 = Math.max(y1, o[1]); }
      c.ox! += (W * (m.l + (1 - m.r)) / 2 - (x0 + x1) / 2) / W; c.oy! += (H * (m.t + (1 - m.b)) / 2 - (y0 + y1) / 2) / H;
      ok = x1 - x0 <= W * (1 - m.l - m.r) && y1 - y0 <= H * (1 - m.t - m.b);
    }
    if (ok) return c;
  }
  return { ...base };
}

/** 홈 첫 화면이 한 장에 담아야 할 자리 — 인천 관문 둘(공항·신항) · 서울 · 김포 · 광주 · 이천 · 안성(경부·영동축) · 자리는 데이터 파일에서 */
/** 홈 첫 화면 카메라의 바탕(자리·줌은 fitCam 이 맞춘다) · 여백 몫 — 위는 지평 안개, 아래는 범례·지도 단추 자리 */
export const HERO_CAM: Cam = { lon: 126.9, lat: 37.35, zoom: 9.6, pitch: 42, bearing: 8 };
export const HERO_M = { l: 0.07, r: 0.07, t: 0.2, b: 0.22 }, HERO_M_NARROW = { l: 0.06, r: 0.06, t: 0.14, b: 0.26 };
export const HERO_IDS = ["서울특별시", "김포", "광주", "이천", "안성"];
export function heroPts(D: { flows: any; sudo?: any }): number[][] {
  const F = D.flows, S = D.sudo, pts: number[][] = [[F.air_gate.lon, F.air_gate.lat], ...F.sea_gates.slice(0, 1).map((g: any) => [g.lon, g.lat])];
  for (const id of HERO_IDS) { const d = (S?.dests ?? F.dests ?? []).find((x: any) => x.id === id && !String(x.basis || "").startsWith("가정")); if (d) pts.push([d.lon, d.lat]); }
  return pts;
}
/** [2026-10-20 · 홈 내륙 흐름을 걷은 뒤] 첫 화면 = 동북아 — 관측된 흐름(교역국 ↔ 인천 관문)이 보이는 넓이. 인천 관문 둘 + 가까운 교역국(중국·일본)의 출발 자리(데이터 파일) */
export const REGION_CAM: Cam = { lon: 129.5, lat: 34.5, zoom: 5.2, pitch: 34, bearing: 0 };
export function regionPts(D: { flows: any }): number[][] {
  const F = D.flows, pts: number[][] = [[F.air_gate.lon, F.air_gate.lat], ...F.sea_gates.slice(0, 1).map((g: any) => [g.lon, g.lat])];
  for (const p of F.partners) if (p.name === "중국" || p.name === "일본") { pts.push(p.air); pts.push(p.sea[0]); }
  return pts;
}
/** 인천 관문 가까이(둘러보기 두 번째 장면) — 공항 · 항만 셋 · 인천 물류창고가 몰린 두 구(자리는 데이터 파일에서) */
export function gatePts(D: { flows: any; sudo?: any }): number[][] {
  const F = D.flows, S = D.sudo, pts: number[][] = [[F.air_gate.lon, F.air_gate.lat], ...F.sea_gates.map((g: any) => [g.lon, g.lat])];
  for (const id of ["서해구", "남동구"]) { const d = (S?.dests ?? []).find((x: any) => x.id === id); if (d) pts.push([d.lon, d.lat]); }
  return pts;
}

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
  /** 세계은행 선박 밀도(2015~2021 누적) — 칸 중심 경위도·세기(1~255) · 없으면 층을 안 그린다 */
  density?: { pts: number[]; period: string } | null;
  /** [2026-10-15 P0] 수도권 물류 흐름 층(tools-build/corridors_derive.py) — 관문→목적지 고속도로 길 · 구간 굵기 · 거점 · 경기 밀집지(몫은 가정) */
  sudo?: { dests: any[]; routes: Record<string, number[][]>; corridors: { w: number; pts: number[][] }[]; hubs: any[]; labels: any[] } | null;
};
type Leg = { pts: Float32Array; n: number; dur: number; tail: number; head: number }; // head·tail = 첫·마지막 원래 구간이 차지하는 초(바다 길이면 부두 ↔ 해상망 끝 마디 직선)
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
  const k0 = Math.max(0, (P.length - 2) * 12), tail = P.length > 2 && L > 0 ? (dur * (L - cum[Math.min(k0, cum.length - 1)])) / L : 0;
  const head = P.length > 2 && L > 0 ? (dur * cum[Math.min(12, cum.length - 1)]) / L : 0;
  return { pts, n, dur, tail, head };
}

/** 대권(큰 원) 경유점 — 하늘 길. 경도는 끊기지 않게 이어 붙인다. */
export function greatCircle(a: number[], b: number[], k = 24) {
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

// km/s(그림 속도 — 실제 속도 아님) · [2026-10-20] 첫 화면이 동북아로 바뀌어 바다·하늘 점이 화면을 1~3초에 건너게 늦췄다(종전 950·2600 = 눈에 안 보였다)
const SPEED = { sea: 320, air: 700, land: 15 };
// [2026-10-15 공개 전 개편 P0] 첫 화면 = 수도권(sudo) · 둘러보기는 수도권 안에서만(sudo ↔ 인천 관문) · 「아시아」는 단추로만
export const VIEWS: Record<string, Cam> = {
  asia: { lon: 122.5, lat: 30.5, zoom: 3.0, pitch: 46, bearing: -10, ox: 0.17, oy: 0.04 },
  sudo: { lon: 126.92, lat: 37.30, zoom: 8.15, pitch: 48, bearing: 10, ox: 0.2, oy: 0.17 }, // 글 기둥(왼쪽) 밖으로 — 인천 관문이 글 아래 깔리지 않게
  incheon: { lon: 126.72, lat: 37.43, zoom: 9.1, pitch: 54, bearing: 18, ox: 0.16, oy: 0.06 },
};
/** 좁은 화면(세로) — 글자가 위에 따로 있으니 가운데로 · 조금 더 멀리 */
export const VIEWS_M: Record<string, Cam> = {
  asia: { lon: 121.0, lat: 30.0, zoom: 2.55, pitch: 44, bearing: -10, ox: 0.05, oy: -0.1 },
  sudo: { lon: 126.95, lat: 37.30, zoom: 7.55, pitch: 48, bearing: 12, ox: 0, oy: -0.08 },
  incheon: { lon: 126.75, lat: 37.42, zoom: 8.45, pitch: 52, bearing: 18, ox: 0, oy: -0.08 },
};

export type Opts = { unit: number; monthSec: number; airTons?: boolean; maxDpr: number; lite: boolean; onMonth?: (i: number) => void; onFrame?: (f: FlowMap) => void;
  /** 점 진하기(1 = 기본 · 따라가기처럼 배경으로 깔 때는 낮춘다) */ dim?: number;
  /** 덧그림 — 점 위·안개 아래(따라가기의 상자·길) */ overlay?: (ctx: CanvasRenderingContext2D, P: (x: number, y: number, h?: number, out?: number[]) => number[], near: boolean) => void;
  /** 카메라를 밖에서 몬다(따라가기 — 스크롤이 카메라) */ camStep?: (f: FlowMap, dt: number) => void;
  /** 데이터 흐름 속도 배율(동작 줄이기 = lib/motion.ts SLOW) */ speed?: number;
  /** 차분하게 — 카메라 비행·관문 반짝임 없이(동작 줄이기 · docs/품질기준.md Q7) */ calm?: boolean;
  /** [2026-10-20 · 품질기준 Q3 · 독립 화면 판정] 관문 → 내륙 목적지 점 흐름을 그리나 — 끄면 점은 관문에서 끝나고(관측된 관문 교역액까지만),
   *  내륙은 실측 창고 개소 원만 정지 층으로 남는다(목적지 몫 배분은 관측이 아니라 모형이라 첫 화면에서 뺐다) */ inland?: boolean;
  /** 이 줌보다 가까울 때만 인천 안 원·거점 네모를 그린다(이름표가 그때만 보인다 — 이름 없는 표식 0) */ detailZoom?: number };

export class FlowMap {
  cv: HTMLCanvasElement; ctx: CanvasRenderingContext2D; D: Data; o: Opts;
  cam: Cam; W = 0; H = 0; dpr = 1;
  /** 이름표가 화면에 뜬 나라(지면이 장면마다 알려 준다) — 없으면 모두 그린다 */ labeled: Set<string> | null = null;
  legsG: Leg[] = []; gMeta: { p: number; g: number; dir: number }[] = [];
  legsL: Leg[] = []; lMeta: { g: number; d: number; dir: number }[] = [];
  wh: any[] = []; // 정지 층 — 실측 창고 개소 원
  gates: { id: string; lon: number; lat: number; kind: "sea" | "air" }[] = [];
  routes: { g: number; l: number; dir: number; rate: Float32Array }[] = []; // rate[month] = 점/초
  // 점(입자) — 구조체 배열 대신 평면 배열
  N = 0; pr = new Int32Array(8192); pt = new Float32Array(8192); pj = new Float32Array(8192); acc: Float32Array = new Float32Array(0);
  t = 0; month = 0; running = false; raf = 0; last = 0;
  arrive: Float32Array = new Float32Array(8); // 관문별 최근 도착(고리 반짝임)
  tour: { from: Cam; to: Cam; t0: number; dur: number } | null = null;
  touring = false; tourStep = 0; tourT = 0; views: Record<string, Cam> = VIEWS;
  /** 둘러보기가 도는 보기(이름) — 하나면 그 자리에서 천천히 돈다 */ tourViews: string[] = ["sudo", "incheon"];
  private dX = new Float32Array(0); private dY = new Float32Array(0); private dV = new Uint8Array(0); private dPh = new Float32Array(0);
  dests: any[] = [];
  private cB: number[][] = [[], [], [], []]; // 고속도로 통로 — 굵기 넷으로 묶은 선분(메르카토르 x1,y1,x2,y2 …)
  private wR: { r: number[]; bb: number[] }[] = []; private nR: number[][] = []; private rdR: number[][] = []; private ctR: number[][] = [];

  constructor(cv: HTMLCanvasElement, data: Data, o: Opts, cam: Cam) {
    this.cv = cv; this.ctx = cv.getContext("2d")!; this.D = data; this.o = o; this.cam = { ...cam };
    const F = data.flows;
    this.month = F.months.length - 1;
    // 바탕 — 메르카토르로 한 번만 바꿔 둔다
    const tm = (r: number[]) => { const o: number[] = []; for (let i = 0; i < r.length; i += 2) o.push(mx(r[i]), my(r[i + 1])); return o; };
    this.wR = data.world.map((r) => { const m = tm(r); let a = 9, b = 9, c = -9, d = -9; for (let i = 0; i < m.length; i += 2) { a = Math.min(a, m[i]); c = Math.max(c, m[i]); b = Math.min(b, m[i + 1]); d = Math.max(d, m[i + 1]); } return { r: m, bb: [a, b, c, d] }; });
    this.nR = data.near.land.map(tm); this.rdR = data.near.road.map(tm); this.ctR = data.near.ct.map(tm);
    // 밀도 칸 — 가벼운 판은 세기 순으로 앞쪽만(그리는 점 수 상한)
    if (data.density?.pts?.length) {
      // 세기 순으로 자르고(위 3200 · 가벼운 판 1400) 묶음(세기 넷)별로 이어 둔다 — 한 장면에 한 번만 훑는다(2026-10-14: 7000점 × 네 번 훑기가 소프트웨어 렌더에서 초당 1장면)
      const P = data.density.pts, n = P.length / 3, cap = o.lite ? 1400 : 3200, idx = Array.from({ length: n }, (_, i) => i).sort((a, b) => P[b * 3 + 2] - P[a * 3 + 2]).slice(0, cap);
      idx.sort((a, b) => FlowMap.dBucket(P[a * 3 + 2]) - FlowMap.dBucket(P[b * 3 + 2]));
      this.dX = new Float32Array(idx.length); this.dY = new Float32Array(idx.length); this.dV = new Uint8Array(idx.length); this.dPh = new Float32Array(idx.length);
      idx.forEach((i, k) => { this.dX[k] = mx(P[i * 3]); this.dY[k] = my(P[i * 3 + 1]); this.dV[k] = FlowMap.dBucket(P[i * 3 + 2]); this.dPh[k] = 0; });
    }
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
    // 목적지 — 수도권 층이 있으면 그 목적지(경기 = 밀집지 여섯)와 고속도로 길, 없으면 개념선
    const S = data.sudo;
    this.dests = S?.dests?.length ? S.dests : F.dests;
    const inland = this.o.inland !== false;
    // 정지 층(원 넓이 = 창고 개소) — 실측인 것만(경기 밀집지 몫이 「가정」이면 원을 그리지 않는다)
    this.wh = this.dests.filter((d: any) => !String(d.basis || "실측").startsWith("가정"));
    if (!inland) this.dests = [{ id: "관문", n: 1, lon: 0, lat: 0 }];
    if (inland && S?.corridors) for (const c of S.corridors) { const b = Math.min(3, Math.floor(Math.sqrt(c.w) * 4)); this.cB[b].push(mx(c.pts[0][0]), my(c.pts[0][1]), mx(c.pts[1][0]), my(c.pts[1][1])); }
    this.dests.forEach((d: any, di: number) => this.gates.forEach((g, gi) => {
      for (const dir of [0, 1]) {
        let ll = !inland ? [[g.lon, g.lat], [g.lon + 0.0005, g.lat]] : S?.routes?.[`${gi}|${di}`] ?? bend([g.lon, g.lat], [d.lon, d.lat], (gi % 2 ? -1 : 1) * 0.16);
        if (dir) ll = [...ll].reverse();
        lIdx[`${gi}|${di}|${dir}`] = this.legsL.length; this.legsL.push(legFrom(ll, SPEED.land)); this.lMeta.push({ g: gi, d: di, dir });
      }
    }));
    // 빈도 — 그 달 관문 교역액 × 나라 비중 × 목적지 비중(창고 개소) × 바다 부두군 비중(컨테이너) ÷ 점 하나 값 ÷ 한 달 초
    const dSum = this.dests.reduce((s: number, d: any) => s + d.n, 0);
    // [2026-10-20 4차 화면 판정 Q3] airTons = 점은 인천공항 항공화물 실측(나라별 도착·출발 톤 · 인천국제공항공사)만 — 나라 몫 가정(관문 금액 × 전국 몫)을 걷는다.
    //   바다는 인천항을 나라별로 가른 공개 통계가 없어 점을 싣지 않는다(해상 경로는 옅은 선으로만 · 계산한 길) · 톤은 반기 자료라 달마다 바뀌지 않는다(달 넘김 없음)
    const AC = F.air_cargo, am = AC ? (Number(AC.through.slice(0, 4)) - Number(AC.from.slice(0, 4))) * 12 + Number(AC.through.slice(5, 7)) - Number(AC.from.slice(5, 7)) + 1 : 1;
    F.partners.forEach((p: any, pi: number) => this.gates.forEach((g, gi) => this.dests.forEach((d: any, di: number) => {
      if (this.o.airTons && g.kind === "sea") return;
      for (const dir of [0, 1]) {
        const rate = new Float32Array(F.months.length);
        F.months.forEach((m: any, mi: number) => {
          const sea = g.kind === "sea";
          const v = dir === 0 ? (sea ? m.port_imp : m.air_imp) : sea ? m.port_exp : m.air_exp;
          let split = 1;
          // 부두군 몫 = 그 달 부두군별 컨테이너(천TEU) · 그 달 자료가 아직 없으면 자료가 있는 가장 가까운 앞 달(같게 나누지 않는다 · 2차 사실 대조)
          if (sea) { let T: any = null; for (let k = mi; k >= 0 && !T; k--) T = F.months[k].teu; T = T || {}; const tot = F.sea_gates.reduce((s: number, x: any) => s + (T[x.id] || 0), 0); split = tot ? (T[g.id] || 0) / tot : 1 / F.sea_gates.length; }
          // 나라 몫(가정 하나) — 바다·하늘 모두 관세청 국가별의 「전국 대비」 몫을 관문에 그대로 쓴다. 관문별 나라 교차표가 없어서다.
          //   [2026-10-20 3차 사실 대조] 하늘에 쓰던 인천공항 항공화물 톤 비중은 환적·우편이 섞여 교역 몫이 아니었다(홍콩 0.3% → 10%) — 걷었다.
          //   10개국 밖 몫은 점이 없다(범례에 적는다)
          if (this.o.airTons) { rate[mi] = ((dir === 0 ? p.air_in_t : p.air_out_t) || 0) / am * (d.n / dSum) / this.o.unit / this.o.monthSec; return; }
          const share = (dir === 0 ? (p.imp_nat_pct ?? p.imp_pct) : (p.exp_nat_pct ?? p.exp_pct)) / 100;
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
  /** 지난 열두 달만 돈다(마지막 달에서 시작 → 열한 달 전 → … → 마지막 달) — 오래된 달로 건너뛰어 보이지 않게 */
  monthAt() { if (this.o.airTons) return this.D.flows.months.length - 1; const n = this.D.flows.months.length, k = Math.min(12, n), base = n - k; return base + ((((k - 1) + Math.floor(this.t / this.o.monthSec)) % k) + k) % k; }
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
    // 선박 밀도 「빛줄기」(세계은행 2015~2021 누적) — 세기 넷으로 나눠 한 번씩 칠하고, 칸마다 다른 위상으로 천천히 숨 쉰다(움직이는 배가 아니다)
    if (this.dX.length) {
      const sz = near ? 2.6 : 1.7, A = [0.10, 0.18, 0.30, 0.46];
      let b = -1;
      for (let k = 0; k <= this.dX.length; k++) {
        const v = k < this.dX.length ? this.dV[k] : -2;
        if (v !== b) { // 묶음이 바뀌면 칠한다 — 묶음마다 다른 위상으로 천천히 숨 쉰다(움직이는 배가 아니다)
          // [2026-10-20] 숨 쉬는 깜빡임은 데이터가 아니라 연출이라 뺐다 · 색은 수출 점(청회)과 겹치지 않게 회녹
          if (b >= 0) { ctx.fillStyle = `rgba(104,116,96,${A[b].toFixed(3)})`; ctx.fill(); }
          if (v < 0) break; b = v; ctx.beginPath();
        }
        P(this.dX[k], this.dY[k], 0, o); if (o[0] < -4 || o[0] > W + 4 || o[1] < -4 || o[1] > H + 4) continue;
        ctx.rect(o[0] - sz / 2, o[1] - sz / 2, sz, sz);
      }
    }
    // 길(옅게) — 먼 길은 나라마다 한 줄(신항·공항만), 가까운 길은 목적지마다
    ctx.lineWidth = 1; ctx.strokeStyle = "rgba(25,23,20,0.10)"; ctx.beginPath();
    // airTons = 하늘길만(점이 실린 길) — 양이 없는 바닷길 선은 이름 없는 표식이 된다(실제 바닷길은 선박 통행 밀도 층이 보인다)
    this.legsG.forEach((L, i) => { const m = this.gMeta[i]; if (m.dir || (m.g !== 0 && m.g !== this.gates.length - 1) || near || (this.o.airTons && m.g !== this.gates.length - 1)) return; this.legPath(L, P, o); }); // 가까이 = 바다 길·하늘 길 선 없음(관문에서 퍼지는 길만)
    if (near && !this.D.sudo) this.legsL.forEach((L, i) => { if (!this.lMeta[i].dir) this.legPath(L, P, o); });
    ctx.stroke();
    // 수도권 고속도로 통로 — 굵기 = 그 구간을 지나는 목적지 몫(추정) · 넷으로 묶어 한 번씩 칠한다
    if (near) this.cB.forEach((B, b) => {
      if (!B.length) return;
      ctx.beginPath();
      for (let i = 0; i < B.length; i += 4) { P(B[i], B[i + 1], 0, o); ctx.moveTo(o[0], o[1]); P(B[i + 2], B[i + 3], 0, o); ctx.lineTo(o[0], o[1]); }
      ctx.lineCap = "round"; ctx.lineWidth = 1 + b * 1.6; ctx.strokeStyle = `rgba(179,54,30,${0.10 + b * 0.05})`; ctx.stroke();
    });
    // 점 — 꼬리(지난 0.3초)를 끈다. 들어오는 것 = 주홍 · 나가는 것 = 바다색
    const TAIL = 0.4, heads: number[] = [], spread = near ? 5 : 2.5, maxTail = near ? 26 : 34;
    for (const dir of [1, 0]) {
      ctx.beginPath();
      for (let i = 0; i < this.N; i++) {
        const r = this.pr[i], R = this.routes[r]; if (R.dir !== dir) continue;
        const age = this.t - this.pt[i];
        // [2026-10-20 · Q3] 가까이 보는 화면에서는 바다 위 구간을 그리지 않는다 — 해상망 끝 마디 → 부두는 계산한 길이 아니라 직선이라(섬을 가로지른다).
        //   들어오는 점은 부두에서 나타나 수도권으로 퍼지고, 나가는 점은 부두에서 사라진다(그 앞뒤 바다 길은 「아시아」 보기에서)
        // [2026-10-20 · 홈 내륙 흐름을 걷은 뒤] 가까이 보는 화면에서도 계산한 길 위의 점은 그린다 — 바다는 해상망(searoute) 끝 마디까지,
        //   마디 → 부두 직선(섬을 가로지른다)만 뺀다. 하늘 길은 가까이서 높이를 눌러 대권 경로를 땅 위에 그린다(높게 그리면 화면 밖으로 나갔다)
        if (near && this.gates[this.gMeta[R.g].g].kind === "sea") {
          const G = this.legsG[R.g], Lw = this.legsL[R.l];
          if (R.dir === 0 ? age > G.dur - G.tail : age < Lw.dur + G.head) continue; // 들어오는 길 = 끝이 부두 · 나가는 길(뒤집힌 길) = 처음이 부두
        }
        // 하늘 길 높이 — 동북아·인천 가까이(줌 4 넘게)에서는 0(대권을 땅 위에 그대로 · 2026-10-20 2차 화면 판정: 높이 때문에 동경 길이 대권보다 북쪽으로 부풀어 보였다) · 아시아 보기에서만 호
        const hz = c.zoom > 4 ? 0 : 1;
        this.pos(r, age, o); const h = P(o[0], o[1], o[2] * hz, o2); const x1 = h[0], y1 = h[1];
        if (x1 < -20 || x1 > W + 20 || y1 < -20 || y1 > H + 20) continue;
        this.pos(r, Math.max(0, age - TAIL), o); P(o[0], o[1], o[2] * hz, o);
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
    const detG = c.zoom > (this.o.detailZoom ?? 0);
    this.gates.forEach((g, gi) => {
      if (near && g.kind === "sea" && gi > 0 && !detG) return; // 이름표가 가까이서만 뜨는 부두군(남항·국제여객부두) — 원도 그때만(이름 없는 표식 0)
      P(mx(g.lon), my(g.lat), 0, o);
      const r0 = near ? (g.kind === "air" ? 6 : 4.5) : 3.5, a = this.o.calm ? 0 : this.arrive[gi];
      ctx.beginPath(); ctx.arc(o[0], o[1], r0 + a * 7, 0, Math.PI * 2); ctx.strokeStyle = `rgba(179,54,30,${0.25 + 0.5 * a})`; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.beginPath(); ctx.arc(o[0], o[1], r0, 0, Math.PI * 2); ctx.fillStyle = "#b3361e"; ctx.fill();
    });
    // 목적지(가까이에서만) — 원 넓이 = 창고 개소
    if (near) {
      const nmax = Math.max(1, ...this.wh.map((d: any) => d.n)), det = c.zoom > (this.o.detailZoom ?? 0);
      // 이름표 규칙과 같다 — 인천 안(구·군 · 인천 쪽 거점)은 가까이 들어왔을 때만(이름 없이 원·네모만 남지 않게)
      const inInc = (lon: number, lat: number) => lon < 126.8 && lat > 37.3;
      // 거점(자리만) — 작은 네모
      for (const h of this.D.sudo?.hubs || []) { if (inInc(h.lon, h.lat) && !det) continue; P(mx(h.lon), my(h.lat), 0, o); ctx.strokeStyle = "rgba(25,23,20,0.75)"; ctx.lineWidth = 1.3; ctx.strokeRect(o[0] - 3.5, o[1] - 3.5, 7, 7); }
      for (const d of this.wh) { if (/[구군]$/.test(d.id) && !det) continue; P(mx(d.lon), my(d.lat), 0, o); ctx.beginPath(); ctx.arc(o[0], o[1], 2.5 + 9 * Math.sqrt(d.n / nmax), 0, Math.PI * 2); ctx.strokeStyle = "rgba(25,23,20,0.55)"; ctx.lineWidth = 1.2; ctx.stroke(); }
    }
    // 나라 점(멀리에서만)
    if (!near) for (const p of this.D.flows.partners) { if (this.labeled && !this.labeled.has(p.name)) continue; /* 이름표가 안 뜬 나라는 점도 그리지 않는다(이름 없는 표식 0 · 9차 화면 판정 390) */ const at = this.o.airTons ? p.air : p.sea[0]; /* 나라 점 = 이름표 자리(공항) */ P(mx(at[0]), my(at[1]), 0, o); ctx.beginPath(); ctx.arc(o[0], o[1], 2.5, 0, Math.PI * 2); ctx.fillStyle = "#191714"; ctx.fill(); }
    this.o.overlay?.(ctx, P, near);
    // 먼 곳은 종이로 흐린다(대기 원근 · 위쪽 글자 바림도 겸한다)
    const g = ctx.createLinearGradient(0, 0, 0, H * 0.42);
    g.addColorStop(0, "rgba(245,242,235,0.96)"); g.addColorStop(1, "rgba(245,242,235,0)");
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H * 0.42);
    this.o.onFrame?.(this);
  }
  private legPath(L: Leg, P: (x: number, y: number, h?: number, out?: number[]) => number[], o: number[]) {
    const s = Math.max(1, Math.floor(L.n / 60)), hz = this.cam.zoom > 4 ? 0 : 1; // 점과 같은 규칙 — 동북아부터는 하늘 길도 땅 위 대권
    for (let i = 0; i < L.n; i += s) { P(L.pts[i * 3], L.pts[i * 3 + 1], L.pts[i * 3 + 2] * hz, o); i ? this.ctx.lineTo(o[0], o[1]) : this.ctx.moveTo(o[0], o[1]); }
    const j = L.n - 1; P(L.pts[j * 3], L.pts[j * 3 + 1], L.pts[j * 3 + 2] * hz, o); this.ctx.lineTo(o[0], o[1]);
  }

  /** 화면 위 자리(이름표·누름 판정) */
  screen(lon: number, lat: number) { return projector(this.cam, this.W, this.H).fn(mx(lon), my(lat)); }

  // ── 카메라 ──
  /** 밀도 값(0~255) → 세기 묶음 0~3 */
  static dBucket(v: number) { return v < 90 ? 0 : v < 150 ? 1 : v < 205 ? 2 : 3; }
  flyTo(to: Cam, dur = 3.2) { if (this.o.calm || !this.running) { this.cam = { ...to }; this.tour = null; if (!this.running) this.draw(); return; } this.tour = { from: { ...this.cam }, to: { ...to }, t0: this.t, dur }; }
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
    } else if (this.touring) this.cam.bearing += dt * (this.cam.zoom > 6 ? 0.5 : 0.8); // 머무는 동안 천천히 돈다(가까이는 아주 천천히 — 맞춘 틀 밖으로 이천·안성이 나가지 않게 · 2026-10-20)
    if (this.touring && !this.tour) {
      this.tourT += dt;
      const hold = this.tourStep % 2 === 0 ? 9 : 10, tv = this.tourViews;
      if (tv.length > 1 && this.tourT > hold) { this.tourT = 0; this.tourStep++; this.flyTo(this.views[tv[this.tourStep % tv.length]], 4.2); }
    }
  }

  start() {
    if (this.running) return;
    this.running = true; this.last = performance.now();
    const loop = (now: number) => {
      if (!this.running) return;
      const dt = Math.min(0.25, (now - this.last) / 1000) * (this.o.speed ?? 1); this.last = now; // 느린 기기에서도 한 달 = 7초(장면이 드물면 한 걸음이 크다)
      this.step(dt); if (this.o.camStep) this.o.camStep(this, dt); else this.camStep(dt); this.draw();
      this.raf = requestAnimationFrame(loop);
    };
    this.raf = requestAnimationFrame(loop);
  }
  stop() { this.running = false; cancelAnimationFrame(this.raf); }
}

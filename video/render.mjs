// 도구 시연 영상 렌더(⑤ · 선커밋 ⑤-상세) — 자막 묶음을 데이터에서 만들고, 숫자 검사를 통과한 편만 Remotion 으로 렌더한다.
//   (저장소 뿌리에서) node tests/capture/record-reels.mjs && (cd video && node render.mjs)
//   입력: astro/dist/og/cards.json(카드를 찍을 때 지면에서 읽은 값) · data/derived/*.json · video/public/rec/<편>-<판>.mp4·.json
//   출력: video/out/<편>-<판>.mp4 · video/out/manifest.json · 돈 0(로컬 렌더 · Lambda 안 씀)
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, cpSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { check } from "../tools-build/check-data-numbers.mjs";
import { spawnSync } from "node:child_process";

const HERE = dirname(fileURLToPath(import.meta.url)), ROOT = join(HERE, "..");
const J = (f) => JSON.parse(readFileSync(join(ROOT, f), "utf-8"));
const SITE = "https://jisangj03-dev.github.io/incheon-port-analysis";
const sign = (v) => (v > 0 ? `+${v}` : `${v}`), won = (v) => Math.round(v).toLocaleString("ko-KR");

const cards = J("astro/dist/og/cards.json").cards;
const DATA = [...readdirSync(join(ROOT, "data/derived")).filter((f) => f.endsWith(".json")).map((f) => `data/derived/${f}`), "astro/dist/og/cards.json", "data/rooms.json"].map((f) => readFileSync(join(ROOT, f), "utf-8"));

// 편마다 자막 — 표지 이름(record-reels.mjs 의 mark)에 숫자 문장을 붙인다. 숫자는 전부 데이터에서.
const CAP = {
  chokepoint: () => {
    const K = J("data/derived/chokepoints.json"), P = Object.fromEntries(K.points.map((p) => [p.id, p]));
    const line = (p) => `${p.ko} 통항 ${sign(p.vs_base_pct)}% · 이 길목 나라와의 교역 = 한국 수입의 ${p.imp_pct}%`;
    return { source: "IMF PortWatch · 관세청 국가별 수출입(전국 · 최근 12달)", marks: { hormuz: line(P.hormuz), redsea: line(P.redsea), malacca: line(P.malacca), taiwan: line(P.taiwan), hormuz2: `인천 관문은 전국 수입의 ${K.incheon_imp_share_pct}%를 받는다(${K.incheon_ym})` } };
  },
  "import-cost": () => {
    const C = J("data/derived/import_cost.json"), E = C.example, K = C.kcci, r1 = K.routes[1];
    return { source: "관세청 관세환율 · 한국해양진흥공사 KCCI(공공데이터포털)", marks: {
      now: `같은 ${won(E.goods)}달러 물건 원가 — ${E.ago_weeks}주 전보다 ${E.diff > 0 ? "+" : "−"}${won(Math.abs(E.diff))}원(${sign(E.pct)}%)`,
      wave: `운임 파도 · KCCI 종합 52주 ${sign(K.chg_52w_pct.KCCI)}%(마지막 반영 주 ${K.last_week})`,
      route: `${K.names[r1]} 52주 ${sign(K.chg_52w_pct[r1])}%`,
      apply: "운임 칸 제안은 지수 변동률만 — 지수는 달러 운임이 아니다",
      end: `관세환율 ${E.ago.fx.toLocaleString("ko-KR")}원 → ${E.now.fx.toLocaleString("ko-KR")}원(1달러)` } };
  },
  "bid-radar": () => {
    const R = J("data/derived/bid_radar.json"), top = [...R.items].sort((a, b) => (b.presmptPrce || 0) - (a.presmptPrce || 0))[0];
    return { source: "조달청 나라장터 입찰공고(용역 · 공공데이터포털) · 자동 수집 · 검수 안 함", marks: {
      all: `마감 전 물류·무역 용역 ${R.n}건 · ${R.snapshot} 스냅샷`,
      "보관·창고": `보관·창고 ${R.group_counts["보관·창고"]}건`, "항만·해운·항공": `항만·해운·항공 ${R.group_counts["항만·해운·항공"]}건`,
      price: `추정가격 1위 ${won(top.presmptPrce)}원 — ${top.bidNtceNm}` } };
  },
};


// ── 따라가기 카메라(채팅 검수 #55) — 녹화 프레임마다 초점 상자를 1.6~2배로, 차분히(지수 추종) 따라간다 ──────────────
const FPS = 30, ZMIN = 1.6, ZMAX = 2.0, MIN_DIGIT = 40;
const CAPBOX = { portrait: { bottom: 210, top: 120 }, square: { bottom: 120, top: 60 } }; // Reel.tsx CAP 과 같은 값
function camera(R) {
  const { width: W, height: H } = R.size, T = R.track, n = Math.ceil(((R.marks.done - (R.marks.loaded || 0)) / 1000) * FPS);
  const at = (ms) => { let s = null; for (const x of T) { if (x.t > ms) break; if (x.f) s = x; } return s || T.find((x) => x.f) || { f: [0, 0, W, H], k: [] }; };
  const cam = []; let cx, cy, z;
  for (let i = 0; i < n; i++) {
    const s = at((i / FPS) * 1000), [rx, ry, rw, rh] = s.f;
    let zt = Math.min(ZMAX, Math.max(ZMIN, Math.min((0.92 * W) / rw, (0.5 * H) / rh)));
    for (const k of s.k) if (k[5] > 0) zt = Math.min(ZMAX, Math.max(zt, MIN_DIGIT / k[5])); // 보이는 핵심 숫자가 40px 를 넘게
    // 초점 상자가 창보다 넓으면 가운데가 아니라 왼쪽에 맞춘다 — 지면 글이 왼쪽 정렬이라 가운데 맞춤은 왼쪽 숫자를 자른다(2026-10-15 프레임 띠: 「−96.5%」 앞자리 잘림)
    let tx = rw + 16 > W / zt ? rx - 8 + W / zt / 2 : rx + rw / 2; const ty = ry + rh / 2, wt = W / zt;
    // 초점 상자가 창보다 넓으면 가운데에 맞춘 창이 숫자를 자른다 → 초점 안의 첫 핵심 숫자(선택자 순서 = 우선순위)가 온전히 들도록 최소한만 민다
    const key = s.k.find((k) => k[2] < ry + rh && k[2] + k[4] > ry && k[3] + 16 <= wt);
    if (key) { if (key[1] - 8 < tx - wt / 2) tx = key[1] - 8 + wt / 2; if (key[1] + key[3] + 8 > tx + wt / 2) tx = key[1] + key[3] + 8 - wt / 2; }
    if (cx === undefined) { cx = tx; cy = ty; z = zt; } else { const a = 1 - Math.exp(-2.4 / FPS), b = 1 - Math.exp(-1.8 / FPS); cx += (tx - cx) * a; cy += (ty - cy) * a; z += (zt - z) * b; }
    const w = W / z, h = H / z;
    const x0 = Math.min(W - w, Math.max(0, cx - w / 2)), y0 = Math.min(H - h, Math.max(0, cy - 0.42 * h));
    cam.push([+x0.toFixed(1), +y0.toFixed(1), +z.toFixed(3)]);
  }
  return { cam, at };
}
// 자막은 초점의 반대편 — 그 자막이 뜬 뒤 0.4초의 초점 상자가 화면 아래 절반에 걸치면 위로
function place(callouts, R, cam, at) {
  const H = R.size.height;
  return callouts.map((c) => {
    const i = Math.min(cam.length - 1, Math.round(((c.at + 400) / 1000) * FPS)), [, y0, z] = cam[i], s = at(c.at + 400), [, ry, , rh] = s.f;
    const bot = (ry + rh - y0) * z, cap = H - CAPBOX[R.fmt].bottom - (R.fmt === "square" ? 200 : 260);
    return { ...c, pos: bot > cap ? "top" : "bottom" };
  });
}
// 시험 ① 화면 핵심 숫자 글자 높이 ≥ 40px(1080 기준) — 카메라 창 안에 온전히 든 숫자 모두
function digitTest(R, cam, at) {
  const bad = [], by = {}; let seen = 0, out = 0, ex = "";
  for (let i = 0; i < cam.length; i += 2) {
    const [x0, y0, z] = cam[i], w = R.size.width / z, h = R.size.height / z, s = at((i / FPS) * 1000);
    for (const [sel, x, y, kw, kh, dh] of s.k) {
      // 세로로는 창 안인데 옆으로 잘린 숫자 = 실패(읽히지 않는 숫자가 화면에 걸린다)
      if (y >= y0 && y + kh <= y0 + h && x < x0 + w && x + kw > x0 && (x < x0 || x + kw > x0 + w)) { bad.push(`${sel}@${(i / FPS).toFixed(1)}s 옆 잘림`); continue; }
      if (x < x0 || y < y0 || x + kw > x0 + w || y + kh > y0 + h) { out++; ex ||= `${sel} [${x},${y},${kw},${kh}] 창 [${x0},${y0},${w.toFixed(0)},${h.toFixed(0)}]`; continue; }
      seen++; by[sel] = (by[sel] || 0) + 1; if (dh * z < MIN_DIGIT) bad.push(`${sel}@${(i / FPS).toFixed(1)}s ${(dh * z).toFixed(0)}px`);
    }
  }
  return { seen, by, bad: [...new Set(bad)].slice(0, 8), why: seen ? "" : `창 밖 ${out}회 · 예 ${ex}` };
}
// 시험 ② 자막이 보이는 프레임의 자막 대비 ≥ 4.5:1 — 렌더된 mp4 에서 자막 상자 띠의 어두운 바탕(10%)과 밝은 글자(99.5%) 휘도
const FF = join(HERE, "node_modules/@remotion/compositor-linux-x64-gnu/ffmpeg");
const lum = (r, g, b) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
function contrastTest(file, props) {
  const W = props.w, H = props.h, intro = 75 / FPS, out = [];
  for (const c of props.callouts) for (const d of [1, 2, 3, 6, 15]) {
    const t = intro + c.at / 1000 + d / FPS; if (t > intro + props.clipMs / 1000 - 0.1) continue;
    const r = spawnSync(FF, ["-loglevel", "error", "-ss", t.toFixed(3), "-i", file, "-frames:v", "1", "-f", "image2pipe", "-c:v", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"], { maxBuffer: W * H * 3 + 1024 });
    const buf = r.stdout; if (!buf || buf.length < W * H * 3) { out.push({ at: c.at, d, err: "frame" }); continue; }
    const B = CAPBOX[props.fmt], y1 = c.pos === "top" ? B.top + 4 : H - B.bottom - 80, y2 = c.pos === "top" ? B.top + 80 : H - B.bottom - 4;
    const L = []; for (let y = y1; y < y2; y += 2) for (let x = 60; x < W - 60; x += 3) { const o = (y * W + x) * 3; L.push(lum(buf[o], buf[o + 1], buf[o + 2])); }
    L.sort((a, b) => a - b); const bg = L[Math.floor(L.length * 0.1)], fg = L[Math.floor(L.length * 0.995)], ratio = (fg + 0.05) / (bg + 0.05);
    out.push({ at: c.at, d, ratio: +ratio.toFixed(2) });
  }
  return out;
}

const only = process.env.REELS_ONLY ? process.env.REELS_ONLY.split(",") : null;
const jobs = [], skipped = [];
for (const [id, cap] of Object.entries(CAP)) {
  if (only && !only.includes(id)) continue;
  const c = cards[id], k = cap();
  for (const fmt of ["portrait", "square"]) {
    const rec = join(HERE, "public/rec", `${id}-${fmt}.json`);
    if (!existsSync(rec)) { skipped.push(`${id}-${fmt}: 녹화 없음`); continue; }
    const R = JSON.parse(readFileSync(rec, "utf-8")), t0 = R.marks.loaded || 0;
    const { cam, at } = camera(R);
    const callouts = place(Object.entries(k.marks).filter(([m]) => R.marks[m] != null).map(([m, text]) => ({ at: R.marks[m] - t0, text })).sort((a, b) => a.at - b.at), R, cam, at);
    const props = { id, fmt, w: R.size.width, h: R.size.height, clip: `rec/${id}-${fmt}.mp4`, clipMs: R.marks.done - t0, q: c.q, num: c.num, unit: c.unit, eb: "", source: k.source, asof: c.asof, url: `${SITE}${c.href}`, callouts, cam };
    const dt = digitTest(R, cam, at);
    if (!dt.seen || dt.bad.length) { skipped.push(`${id}-${fmt}: 핵심 숫자 글자 높이 40px 미만(본 ${dt.seen}) ${dt.bad.join(" · ")} ${dt.why}`); continue; }
    props.digit_checked = dt.seen; props.digit_by = dt.by;
    props.eb = { chokepoint: "포워더 · 수출입 담당", "import-cost": "수입 담당 · 구매", "bid-radar": "물류기업 영업 · 3PL" }[id];
    // 화면에 나오는 글 전부 → 숫자 검사(데이터 밖 숫자가 있으면 그 편은 렌더하지 않는다)
    const shown = [props.q, props.num, props.unit, props.source, props.asof, ...callouts.map((x) => x.text)].join("\n");
    const bad = check(shown, DATA).bad;
    if (bad.length) { skipped.push(`${id}-${fmt}: 데이터 밖 숫자 ${bad.join(",")}`); continue; }
    jobs.push(props);
  }
}
console.log(`렌더 ${jobs.length}편 · 건너뜀 ${skipped.length}`, skipped);
// REELS_DRY=1 — 시험(숫자 높이)과 자막 자리만 보고 렌더하지 않는다
if (process.env.REELS_DRY) { for (const j of jobs) console.log(`${j.id}-${j.fmt} 숫자 확인 ${j.digit_checked} ${JSON.stringify(j.digit_by)} · 자막 자리 ${j.callouts.map((c) => c.pos).join(",")}`); process.exit(skipped.length ? 1 : 0); }

// 글꼴 — 사이트와 같은 Pretendard(OFL). 렌더 중 바뀌지 않게 font-display 를 block 으로
mkdirSync(join(HERE, "public/fonts"), { recursive: true });
cpSync(join(ROOT, "astro/public/fonts/pretendard"), join(HERE, "public/fonts/pretendard"), { recursive: true });
const css = join(HERE, "public/fonts/pretendard/pretendard.css");
writeFileSync(css, readFileSync(css, "utf-8").replace(/font-display:\s*optional/g, "font-display: block"));

const serveUrl = await bundle({ entryPoint: join(HERE, "src/index.ts") });
mkdirSync(join(HERE, "out"), { recursive: true });
const made = [], failed = [];
for (const props of jobs) {
  const composition = await selectComposition({ serveUrl, id: `reel-${props.fmt}`, inputProps: props, browserExecutable: process.env.REMOTION_BROWSER || null });
  const out = join(HERE, "out", `${props.id}-${props.fmt}.mp4`);
  const t = Date.now();
  await renderMedia({ composition, serveUrl, codec: "h264", crf: 20, outputLocation: out, inputProps: props, browserExecutable: process.env.REMOTION_BROWSER || null, concurrency: Number(process.env.REMOTION_CONCURRENCY || 2), chromiumOptions: { gl: "swangle" } });
  const ct = contrastTest(out, props), low = ct.filter((x) => x.err || x.ratio < 4.5);
  console.log(`렌더 ${props.id}-${props.fmt} ${(composition.durationInFrames / composition.fps).toFixed(1)}초 · ${((Date.now() - t) / 1000).toFixed(0)}초 걸림 · 자막 대비 최저 ${Math.min(...ct.map((x) => x.ratio || 0))}:1(${ct.length}프레임) · 숫자 높이 확인 ${props.digit_checked}`);
  if (low.length) { failed.push(`${props.id}-${props.fmt}: 자막 대비 4.5 미만 ${JSON.stringify(low.slice(0, 4))}`); continue; }
  const { cam: _c, ...rest } = props;
  made.push({ file: `${props.id}-${props.fmt}.mp4`, seconds: +(composition.durationInFrames / composition.fps).toFixed(1), contrast_min: Math.min(...ct.map((x) => x.ratio)), ...rest });
}
writeFileSync(join(HERE, "out/manifest.json"), JSON.stringify({ _설명: "도구 시연 영상 — 화면 글(숫자 검사 통과분) · 자막 대비 ≥4.5:1 · 핵심 숫자 글자 높이 ≥40px · 게시 = 선장님", made, skipped, failed }, null, 1));
if (failed.length) console.error("시험 미달:", failed);
process.exit(failed.length || skipped.length ? 1 : 0);

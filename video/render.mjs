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

const only = process.env.REELS_ONLY ? process.env.REELS_ONLY.split(",") : null;
const jobs = [], skipped = [];
for (const [id, cap] of Object.entries(CAP)) {
  if (only && !only.includes(id)) continue;
  const c = cards[id], k = cap();
  for (const fmt of ["portrait", "square"]) {
    const rec = join(HERE, "public/rec", `${id}-${fmt}.json`);
    if (!existsSync(rec)) { skipped.push(`${id}-${fmt}: 녹화 없음`); continue; }
    const R = JSON.parse(readFileSync(rec, "utf-8")), t0 = R.marks.loaded || 0;
    const callouts = Object.entries(k.marks).filter(([m]) => R.marks[m] != null).map(([m, text]) => ({ at: R.marks[m] - t0, text })).sort((a, b) => a.at - b.at);
    const props = { id, fmt, w: R.size.width, h: R.size.height, clip: `rec/${id}-${fmt}.mp4`, clipMs: R.marks.done - t0, q: c.q, num: c.num, unit: c.unit, eb: "", source: k.source, asof: c.asof, url: `${SITE}${c.href}`, callouts };
    props.eb = { chokepoint: "포워더 · 수출입 담당", "import-cost": "수입 담당 · 구매", "bid-radar": "물류기업 영업 · 3PL" }[id];
    // 화면에 나오는 글 전부 → 숫자 검사(데이터 밖 숫자가 있으면 그 편은 렌더하지 않는다)
    const shown = [props.q, props.num, props.unit, props.source, props.asof, ...callouts.map((x) => x.text)].join("\n");
    const bad = check(shown, DATA).bad;
    if (bad.length) { skipped.push(`${id}-${fmt}: 데이터 밖 숫자 ${bad.join(",")}`); continue; }
    jobs.push(props);
  }
}
console.log(`렌더 ${jobs.length}편 · 건너뜀 ${skipped.length}`, skipped);

// 글꼴 — 사이트와 같은 Pretendard(OFL). 렌더 중 바뀌지 않게 font-display 를 block 으로
mkdirSync(join(HERE, "public/fonts"), { recursive: true });
cpSync(join(ROOT, "astro/public/fonts/pretendard"), join(HERE, "public/fonts/pretendard"), { recursive: true });
const css = join(HERE, "public/fonts/pretendard/pretendard.css");
writeFileSync(css, readFileSync(css, "utf-8").replace(/font-display:\s*optional/g, "font-display: block"));

const serveUrl = await bundle({ entryPoint: join(HERE, "src/index.ts") });
mkdirSync(join(HERE, "out"), { recursive: true });
const made = [];
for (const props of jobs) {
  const composition = await selectComposition({ serveUrl, id: `reel-${props.fmt}`, inputProps: props, browserExecutable: process.env.REMOTION_BROWSER || null });
  const out = join(HERE, "out", `${props.id}-${props.fmt}.mp4`);
  const t = Date.now();
  await renderMedia({ composition, serveUrl, codec: "h264", crf: 20, outputLocation: out, inputProps: props, browserExecutable: process.env.REMOTION_BROWSER || null, concurrency: Number(process.env.REMOTION_CONCURRENCY || 2), chromiumOptions: { gl: "swangle" } });
  console.log(`렌더 ${props.id}-${props.fmt} ${(composition.durationInFrames / composition.fps).toFixed(1)}초 · ${((Date.now() - t) / 1000).toFixed(0)}초 걸림`);
  made.push({ file: `${props.id}-${props.fmt}.mp4`, seconds: +(composition.durationInFrames / composition.fps).toFixed(1), ...props });
}
writeFileSync(join(HERE, "out/manifest.json"), JSON.stringify({ _설명: "도구 시연 영상 — 화면 글(숫자 검사 통과분) · 게시 = 선장님", made, skipped }, null, 1));
process.exit(skipped.length && !made.length ? 1 : 0);

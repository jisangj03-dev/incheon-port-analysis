// Lighthouse 13.5.0 직접 실행(2026-10-10 판정 변경 — @lhci/cli 는 쓰지 않는다: 의존성 취약점 17건).
// 결과는 로컬 파일(JSON)뿐이다. 어디에도 업로드하지 않는다. CI 는 이 폴더를 artifact 로 남긴다.
//
//   node tests/lighthouse/run.mjs [기준주소]      기본 http://127.0.0.1:4173 (로컬 빌드)
//
// 크롬: CHROME_PATH(있으면) → PW_CHROMIUM_PATH → Playwright 가 깐 크로미움.
// 설정: Lighthouse 기본값 = 모바일 · 모의 스로틀링 — 판정 기준 문서의 「Lighthouse 모바일」과 같은 축이다.
import { spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";

const base = (process.argv[2] || "http://127.0.0.1:4173").replace(/\/$/, "");
// [2026-10-14 공개 전환] 구조 넷 지면 전부 + 남이 링크한 계산기 — 출고 검사 「모바일 성능 90↑ · 접근성」의 축.
const PAGES = [
  ["home", "/incheon-port-analysis/"],
  ["tools", "/incheon-port-analysis/tools/"],
  ["port-pulse", "/incheon-port-analysis/tools/port-pulse.html"],
  ["delivery-reach", "/incheon-port-analysis/tools/delivery-reach.html"],
  ["trade-race", "/incheon-port-analysis/tools/trade-race.html"],
  ["import-cost", "/incheon-port-analysis/tools/import-cost.html"],
  ["anchorage", "/incheon-port-analysis/tools/anchorage.html"],
  ["chokepoint", "/incheon-port-analysis/tools/chokepoint.html"],
  ["map", "/incheon-port-analysis/map.html"],
  ["follow", "/incheon-port-analysis/map/follow.html"],
  ["vessels", "/incheon-port-analysis/map/vessels.html"],
  ["sim", "/incheon-port-analysis/sim/"],
  ["beer-game", "/incheon-port-analysis/sim/beer-game.html"],
  ["forecast", "/incheon-port-analysis/sim/forecast.html"],
  ["notes", "/incheon-port-analysis/notes.html"],
  ["port-yoy", "/incheon-port-analysis/notes/port-yoy.html"],
  ["ai-ops", "/incheon-port-analysis/notes/ai-ops.html"],
  ["about", "/incheon-port-analysis/about.html"],
  ["calculator", "/incheon-port-analysis/tools/logistics-cost.html"],
  ["warehouse-map", "/incheon-port-analysis/tools/warehouse-map.html"],
];
const OUT = "lighthouse-results";
mkdirSync(OUT, { recursive: true });

function chromePath() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  if (process.env.PW_CHROMIUM_PATH) return process.env.PW_CHROMIUM_PATH;
  const req = createRequire(import.meta.url);
  const { chromium } = req("@playwright/test");
  const p = chromium.executablePath();
  if (existsSync(p)) return p;
  throw new Error("크롬을 못 찾았다 — CHROME_PATH 또는 PW_CHROMIUM_PATH 를 준다");
}

const env = { ...process.env, CHROME_PATH: chromePath() };
// [2026-10-10 CI] 세 지면 모두 CHROME_INTERSTITIAL_ERROR(최종 chrome-error://chromewebdata/)로 멈췄다.
// 브라우저 탓으로 보고 HttpsUpgrades·Local Network Access 를 꺼 봤으나 **원인은 서버였다** — 채팅 재현:
// 서버가 없을 때만 정확히 같은 오류가 나고(메인 문서 net::ERR_CONNECTION_REFUSED), 떠 있으면 200 으로 잰다.
// 그래서 브라우저 플래그는 되돌렸고, 워크플로가 with_server.py 로 서버 준비를 기다린 뒤 이 파일을 부른다.
// 시작 전에 홈 200 을 확인해, 서버가 없으면 「브라우저 오류」로 보이기 전에 여기서 멈춘다.
const FLAGS = ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"].join(" ");

const probe = await fetch(`${base}/incheon-port-analysis/`).then((r) => r.status, (e) => `연결 실패 ${e.cause?.code || e.message}`);
if (probe !== 200) {
  console.error(`서버가 응답하지 않는다: ${base}/incheon-port-analysis/ → ${probe}. Lighthouse 를 돌리지 않고 멈춘다.`);
  process.exit(1);
}

function diagnose(url) {
  // 같은 크롬·같은 플래그로 크롬이 직접 열게 해 DOM 을 받는다 — 오류 화면이면 오류 이름(ERR_…)이 그 안에 있다.
  const r = spawnSync(env.CHROME_PATH, [...FLAGS.split(" "), "--dump-dom", url], { encoding: "utf-8", timeout: 30_000 });
  const dom = (r.stdout || "").replace(/\s+/g, " ");
  const err = dom.match(/(?:net::)?ERR_[A-Z_]+/);
  console.error(`[진단] 크롬 직접 열기(--dump-dom): 종료 ${r.status} · ${err ? err[0] : "오류 이름 없음"} · DOM ${dom.length}자 · ${dom.slice(0, 160)}`);
}
// 지면마다 LH_RUNS 번(기본 3) 재고 성능은 중앙값을 적는다 — 한 번 재기는 같은 빌드에서도 ±5 흔들렸다(2026-10-14 실측: 따라가기 87~99).
// 중앙값 회차의 JSON 을 <지면>.json 으로 남기고, 회차별 성능 점수를 같이 적는다(고른 값만 보이지 않게).
const RUNS = Math.max(1, Number(process.env.LH_RUNS || 3));
const rows = [];
let bad = 0;
// LH_ONLY=이름,이름 — 그 지면만(새 지면을 다룰 때 · 출고 검사는 전부)
const ONLY = (process.env.LH_ONLY || "").split(",").filter(Boolean);
for (const [name, path] of PAGES.filter(([n]) => !ONLY.length || ONLY.includes(n))) {
  const reps = [];
  let fail = "";
  for (let k = 0; k < RUNS; k++) {
    const json = `${OUT}/${name}.run${k}.json`;
    const r = spawnSync("npx", ["lighthouse", base + path, "--quiet", "--output=json", `--output-path=${json}`,
      `--chrome-flags=${FLAGS}`], { env, stdio: ["ignore", "inherit", "inherit"] });
    if (!existsSync(json)) { fail = `실행 실패(종료 ${r.status})`; break; }
    const rep = JSON.parse(readFileSync(json, "utf-8"));
    if (rep.runtimeError) {   // 점수 대신 이유를 남긴다 — 「실행 실패」 넉 자로는 다음 수를 못 고른다
      console.error(`[진단] ${name}: 요청 ${rep.requestedUrl} → 최종 ${rep.finalDisplayedUrl} · 브라우저 ${rep.environment?.hostUserAgent}`);
      for (const w of rep.runWarnings || []) console.error(`[진단] ${name} 경고: ${w}`);
      if (!bad) diagnose(base + path);   // 첫 실패에서 한 번만
      fail = `실행 실패: ${rep.runtimeError.code}`; break;
    }
    reps.push({ rep, json });
  }
  if (fail) { rows.push([name, fail, "", "", "", ""]); bad++; continue; }
  const sc = (rep, k) => Math.round((rep.categories[k]?.score ?? NaN) * 100);
  reps.sort((x, y) => sc(x.rep, "performance") - sc(y.rep, "performance"));
  const mid = reps[Math.floor(reps.length / 2)];
  writeFileSync(`${OUT}/${name}.json`, readFileSync(mid.json, "utf-8"));
  rows.push([name, sc(mid.rep, "performance"), sc(mid.rep, "accessibility"), sc(mid.rep, "best-practices"), sc(mid.rep, "seo"), reps.map((x) => sc(x.rep, "performance")).join(" · ")]);
}
const md = [
  `# Lighthouse 요약 — ${new Date().toISOString()}`,
  "",
  `브라우저: ${env.CHROME_PATH}`,
  "",
  `대상: ${base} · Lighthouse 13.5.0 · 모바일(기본) · 결과 JSON 은 같은 폴더`,
  "",
  `| 지면 | 성능(중앙값) | 접근성 | 권장 | SEO | 성능 회차별(${RUNS}회) |`,
  "|---|---|---|---|---|---|",
  ...rows.map((r) => `| ${r.join(" | ")} |`),
  "",
].join("\n");
writeFileSync(`${OUT}/summary.md`, md);
console.log(md);
process.exit(bad ? 1 : 0);

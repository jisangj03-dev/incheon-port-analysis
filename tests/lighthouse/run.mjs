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
const PAGES = [
  ["home", "/incheon-port-analysis/"],
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
// [2026-10-10 첫 CI] 세 지면 모두 CHROME_INTERSTITIAL_ERROR 로 멈췄다(Playwright 크로미움 = Chrome for Testing 153).
// 둘째 시도로 HttpsUpgrades 를 꺼 봤으나 같았다 — 그 가설은 틀렸다. 그리고 --disable-features 를 따로 주면
// chrome-launcher 의 기본 목록을 덮을 수 있어 뺐다. CI 는 러너의 Google Chrome 안정판(CHROME_PATH)을 쓴다 —
// Lighthouse 가 시험받는 짝이다. 실패하면 아래 진단 줄(최종 주소·경고)이 다음 수를 고르게 한다.
const FLAGS = ["--headless=new", "--no-sandbox", "--disable-dev-shm-usage"].join(" ");
const rows = [];
let bad = 0;
for (const [name, path] of PAGES) {
  const json = `${OUT}/${name}.json`;
  const r = spawnSync("npx", ["lighthouse", base + path, "--quiet", "--output=json", `--output-path=${json}`,
    `--chrome-flags=${FLAGS}`], { env, stdio: ["ignore", "inherit", "inherit"] });
  if (!existsSync(json)) { rows.push([name, `실행 실패(종료 ${r.status})`, "", "", ""]); bad++; continue; }
  const rep = JSON.parse(readFileSync(json, "utf-8"));
  if (rep.runtimeError) {   // 점수 대신 이유를 남긴다 — 「실행 실패」 넉 자로는 다음 수를 못 고른다
    console.error(`[진단] ${name}: 요청 ${rep.requestedUrl} → 최종 ${rep.finalDisplayedUrl} · 브라우저 ${rep.environment?.hostUserAgent}`);
    for (const w of rep.runWarnings || []) console.error(`[진단] ${name} 경고: ${w}`);
    rows.push([name, `실행 실패: ${rep.runtimeError.code}`, "", "", ""]); bad++; continue;
  }
  const s = (k) => Math.round((rep.categories[k]?.score ?? NaN) * 100);
  rows.push([name, s("performance"), s("accessibility"), s("best-practices"), s("seo")]);
}
const md = [
  `# Lighthouse 요약 — ${new Date().toISOString()}`,
  "",
  `브라우저: ${env.CHROME_PATH}`,
  "",
  `대상: ${base} · Lighthouse 13.5.0 · 모바일(기본) · 결과 JSON 은 같은 폴더`,
  "",
  "| 지면 | 성능 | 접근성 | 권장 | SEO |",
  "|---|---|---|---|---|",
  ...rows.map((r) => `| ${r.join(" | ")} |`),
  "",
].join("\n");
writeFileSync(`${OUT}/summary.md`, md);
console.log(md);
process.exit(bad ? 1 : 0);

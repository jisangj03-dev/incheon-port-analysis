// Playwright 시험 구성(2026-10-10). 지면은 로컬 빌드만 연다 — 공개 사이트(밖)에 요청하지 않는다.
//  · _site/                 = Jekyll 빌드(GitHub Pages 와 같은 플러그인 묶음) + Pagefind 색인
//  · astro/dist/            = Astro 최소 구성 빌드(공개 사이트에 연결 안 됨)
// 크로미움: CI 는 `npx playwright install chromium` 판을 쓴다. 클라우드 세션은 내려받기가 막혀 있어
// 미리 깔린 판을 PW_CHROMIUM_PATH 로 쓴다(.claude/hooks/session-start.sh 가 넣는다).
import { defineConfig, devices } from "@playwright/test";

const SITE = 4173;
const ASTRO = 4174;
const exe = process.env.PW_CHROMIUM_PATH || undefined;

export default defineConfig({
  testDir: "tests",
  testMatch: /.*\.spec\.mjs$/,
  timeout: 60_000,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: `http://127.0.0.1:${SITE}`,
    launchOptions: { executablePath: exe },
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop-1440", use: { browserName: "chromium", viewport: { width: 1440, height: 900 } } },
    // iPhone 13 기기 묘사(390×844 · DPR 3 · 모바일 UA)를 크로미움으로 — 엔진은 측정 대상이 아니다.
    { name: "iphone-13", use: { ...devices["iPhone 13"], browserName: "chromium", defaultBrowserType: "chromium" } },
  ],
  webServer: [
    { command: `python3 -m http.server ${SITE} --bind 127.0.0.1 --directory _site`, port: SITE, reuseExistingServer: true, stderr: "ignore" },
    { command: `python3 -m http.server ${ASTRO} --bind 127.0.0.1 --directory astro/dist`, port: ASTRO, reuseExistingServer: true, stderr: "ignore" },
  ],
});

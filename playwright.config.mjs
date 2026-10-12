// Playwright 시험 구성(2026-10-10 · 2026-10-12 Astro 이전). 지면은 로컬 빌드만 연다 — 공개 사이트(밖)에 요청하지 않는다.
//  · astro/dist/ = Astro 빌드(SOUNDING_LAB=1 이면 lab/ 시험 지면 포함) + Pagefind 색인
//  · tests/serve.mjs 가 GitHub Pages 와 같은 모양(기준주소 · 404 · Range)으로 낸다.
// 크로미움: CI 는 `npx playwright install chromium` 판, 클라우드 세션은 미리 깔린 판(PW_CHROMIUM_PATH).
import { defineConfig, devices } from "@playwright/test";

const SITE = 4173;
const exe = process.env.PW_CHROMIUM_PATH || undefined;

export default defineConfig({
  testDir: "tests",
  testMatch: /.*\.spec\.mjs$/,
  timeout: 90_000,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  use: {
    baseURL: `http://127.0.0.1:${SITE}`,
    launchOptions: { executablePath: exe, args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] },
    trace: "retain-on-failure",
  },
  projects: [
    { name: "desktop-1440", use: { browserName: "chromium", viewport: { width: 1440, height: 900 } } },
    // iPhone 13 기기 묘사(390×844 · DPR 3 · 모바일 UA)를 크로미움으로 — 엔진은 측정 대상이 아니다.
    { name: "iphone-13", use: { ...devices["iPhone 13"], browserName: "chromium", defaultBrowserType: "chromium" } },
  ],
  webServer: [
    { command: `node tests/serve.mjs ${SITE} astro/dist`, port: SITE, reuseExistingServer: true, stderr: "ignore" },
  ],
});

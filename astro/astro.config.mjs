// 측심 사이트 — Astro 정적 생성(2026-10-12 · Jekyll 에서 이전).
// 주소는 그대로: 기준주소 /incheon-port-analysis · 지면은 `….html`(build.format "preserve" — about.astro → about.html,
// tools/index.astro → tools/index.html). 발행본 마크다운은 저장소 자리(reports/ · docs/)에서 직접 읽는다 — 사본을 만들지 않는다.
// 외부 요청 0: 글꼴·지도 라이브러리·워커는 public/ 으로 복사해 같은 주소에서 낸다(scripts/sync-public.mjs).
import { defineConfig } from "astro/config";
import { rewriteDir } from "./src/lib/md-links.mjs";
import { checkDist } from "./src/lib/public-docs.mjs";
import { rmSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const lab = process.env.SOUNDING_LAB === "1";

export default defineConfig({
  site: "https://jisangj03-dev.github.io",
  base: "/incheon-port-analysis",
  output: "static",
  trailingSlash: "ignore",
  build: { format: "preserve", assets: "_a", inlineStylesheets: "always" }, // CSS 를 지면에 넣어 요청 하나 줄인다(첫 화면)
  devToolbar: { enabled: false },
  integrations: [
    {
      // 시안·도구 시험 지면(lab/)은 SOUNDING_LAB=1 일 때만 산출물에 남긴다 — 공개 배포물에는 없다.
      name: "sounding-lab-gate",
      hooks: {
        "astro:build:done": ({ dir, logger }) => {
          // 발행본의 상대 링크(`report_07_….md` · `../docs/….md`)를 지면 주소(`.html`)로.
          logger.info(`상대 .md 링크 ${rewriteDir(fileURLToPath(dir))}개를 .html 로 바꿨다`);
          const p = fileURLToPath(new URL("lab", dir));
          if (!lab && existsSync(p)) rmSync(p, { recursive: true, force: true });
          // 운영 문서가 공개 지면으로 새면 빌드를 멈춘다(허용 목록 = src/lib/public-docs.mjs).
          const leaks = checkDist(fileURLToPath(dir));
          if (leaks.length) throw new Error(`공개 허용 목록 밖 docs 가 산출물에 있다 ${leaks.length}건:\n  ${leaks.slice(0, 20).join("\n  ")}`);
          logger.info("공개 docs 검사: 허용 목록 밖 지면·링크·sitemap 줄 0");
        },
      },
    },
  ],
});

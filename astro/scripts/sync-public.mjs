// 빌드 전에 public/ 의 「생성되는 몫」을 채운다(2026-10-12). 여기서 복사하는 것은 커밋하지 않는다(.gitignore).
// 원본이 저장소·node_modules 에 이미 있어 사본을 커밋하면 소스가 둘이 되기 때문이다(사고 31).
//   · 발행본 그림        reports/images/*      → public/reports/images/
//   · 사이트 자산        assets/*(css 제외)     → public/assets/   (기존 주소 /assets/og.jpg · /assets/js/cost-check.js 유지)
//   · 글꼴              pretendard 동적 부분집합 → public/fonts/pretendard/  (CDN 0 · 기준 10)
//   · 지도 라이브러리     maplibre-gl dist        → public/vendor/maplibre/   (워커가 같은 주소에서 shared 를 읽는다 · 주의 ②)
import { cpSync, mkdirSync, rmSync, readFileSync, writeFileSync, readdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const astro = dirname(dirname(fileURLToPath(import.meta.url)));
const repo = dirname(astro);
const pub = join(astro, "public");
const nm = join(repo, "node_modules");
const fresh = (d) => { rmSync(d, { recursive: true, force: true }); mkdirSync(d, { recursive: true }); return d; };

cpSync(join(repo, "reports/images"), fresh(join(pub, "reports/images")), { recursive: true });

const assets = fresh(join(pub, "assets"));
for (const f of readdirSync(join(repo, "assets"), { withFileTypes: true })) {
  if (f.name === "css") continue; // 옛 Jekyll 스타일은 새 사이트에 안 쓴다
  cpSync(join(repo, "assets", f.name), join(assets, f.name), { recursive: true });
}

const fontDir = fresh(join(pub, "fonts/pretendard"));
const pv = join(nm, "pretendard/dist/web/variable");
cpSync(join(pv, "woff2-dynamic-subset"), join(fontDir, "woff2-dynamic-subset"), { recursive: true });
// 라이선스(OFL-1.1) 고지는 이 CSS 머리글이 든다(패키지에 LICENSE 파일이 따로 없다).
// font-display: swap → optional — 글꼴이 늦으면 그 화면은 시스템 서체로 끝까지 간다(글자 바뀜에 따른 화면 밀림 0 · 기준 10 성능).
// 다음 지면부터는 캐시된 글꼴이 바로 쓰인다. CSS 는 비동기로 붙인다(Base.astro) — 첫 화면을 막지 않는다.
writeFileSync(join(fontDir, "pretendard.css"), readFileSync(join(pv, "pretendardvariable-dynamic-subset.css"), "utf-8").replace(/font-display:\s*swap/g, "font-display: optional"));

// 제목 명조 시안(디자인 「해도」 글꼴 두 안 · 2026-10-14) — Noto Serif KR 700 하나만(OFL-1.1 · LICENSE 같이). 지면 CSS 가 unicode-range 로 쓰는 글자만 받는다.
// [2026-10-14 공개 전환] 제목 명조 확정(토큰 --s-font-head) — 공개 지면도 쓴다.
const serif = join(nm, "@fontsource/noto-serif-kr");
if (existsSync(serif)) {
  const sd = fresh(join(pub, "fonts/noto-serif-kr"));
  mkdirSync(join(sd, "files"), { recursive: true });
  for (const f of readdirSync(join(serif, "files"))) if (/-700-normal\.woff2$/.test(f)) cpSync(join(serif, "files", f), join(sd, "files", f));
  cpSync(join(serif, "LICENSE"), join(sd, "LICENSE"));
  writeFileSync(join(sd, "noto-serif-kr-700.css"), "/* Noto Serif KR 700 · OFL-1.1 · @fontsource/noto-serif-kr */\n" +
    readFileSync(join(serif, "700.css"), "utf-8").replace(/,\s*url\([^)]*\.woff\) format\('woff'\)/g, ""));
}

const ml = fresh(join(pub, "vendor/maplibre"));
for (const f of ["maplibre-gl.mjs", "maplibre-gl-shared.mjs", "maplibre-gl-worker.mjs", "maplibre-gl.css"]) {
  cpSync(join(nm, "maplibre-gl/dist", f), join(ml, f));
}
cpSync(join(nm, "maplibre-gl/LICENSE.txt"), join(ml, "LICENSE.txt"));

const tiles = join(pub, "tiles/incheon.pmtiles");
console.log(`[sync-public] 그림·자산·글꼴·maplibre 복사 완료 · 지도 타일 ${existsSync(tiles) ? "있음" : "없음(Actions 가 빌드 때 추출 — 없으면 지도는 정지 이미지로 남는다)"}`);

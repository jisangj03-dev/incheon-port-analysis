// docs/ 의 무엇이 공개 지면이 되는가 — 허용 목록(2026-10-12 · 채팅 지시).
// 기준: 독자가 공개물의 근거로 읽는 「방법」 문서만 지면으로 낸다. 운영 문서(STATUS·작업기록·위임문·사고기록·
// 개편 판정기준·디자인브리프·도구 판정·채널 대기열·실물 점검 …)는 우리가 읽는 것이라 산출물에 안 넣는다.
// 저장소는 공개라 원문은 GitHub 에 그대로 있다 — 공개물 본문이 그 문서를 가리키면 링크를 저장소 원문으로 돌린다
// (발행본 본문은 고치지 않는다 · 깨진 링크 0).
// 새 문서를 독자용으로 내려면 여기에 한 줄과 이유를 단다. 목록 밖 docs 지면이 산출물에 있으면 빌드가 실패한다(checkDist).
import { readdirSync, readFileSync, statSync, existsSync } from "node:fs";
import { join, posix } from "node:path";

export const REPO_BLOB = "https://github.com/jisangj03-dev/incheon-port-analysis/blob/main";
const BASE = "/incheon-port-analysis";

export const PUBLIC_DOCS = [
  [/^\d\d_(주제검증|판정결과)$/, "편마다의 데이터 확인·사전 판정 기준과 그 결과 — 보고서가 근거로 링크한다"],
  [/^FACTS$/, "수치 대장 — 결론 자리 수치의 값·창·지위(기자용 지면이 링크한다)"],
  [/^GInOut_코드규명$/, "API 코드(수입·수출·환적) 해석의 근거 — 보고서 #01~#09 가 링크한다"],
  [/^검수기록$/, "보고서 표기 블록의 「검수」 근거(지침 §2.2 표기 의무)"],
  [/^무역라인_개시게이트$/, "보고서 #08 의 사전 선언 판정 기준"],
  [/^인천품목_판정기준_선커밋_20261003$/, "보고서 #13 의 선커밋 판정 기준"],
  [/^주소좌표_판정기준_선커밋_20260930$/, "물류창고 지면의 좌표 단계 선커밋 기준"],
  [/^인천물류지수_방법론_선커밋_20261012$/, "인천 물류 지수 방법론(독자용 · 채팅 지정)"],
  [/^수요예측_방법론_선커밋_20261014$/, "인천항 수요예측 실험실 방법론 — 예측보다 먼저 커밋한 기준(정체성 전환 §3-4)"],
];

export const isPublicDoc = (id) => PUBLIC_DOCS.some(([re]) => re.test(id));

// 지면 경로(기준주소 뺀 것 · 예: "docs/STATUS.html")가 목록 밖 docs 지면이면 그 문서 id, 아니면 null.
export function hiddenDoc(sitePath) {
  const m = /^docs\/(.+)\.(?:html|md)$/i.exec(sitePath);
  if (!m) return null;
  const id = m[1];
  return isPublicDoc(id) ? null : id;
}

// href 를 산출물 안의 지면 경로로 푼다. here = 그 HTML 파일이 있는 폴더(산출물 뿌리 기준 · "" · "reports" · "docs").
export function sitePathOf(href, here) {
  if (!href || /^[a-z]+:/i.test(href) || href.startsWith("#") || href.startsWith("//")) return null;
  const path = href.split("#")[0].split("?")[0];
  let p;
  try { p = decodeURIComponent(path); } catch { p = path; }
  if (p.startsWith(BASE + "/")) p = p.slice(BASE.length + 1);
  else if (p.startsWith("/")) p = p.slice(1);
  else p = posix.normalize(posix.join(here, p));
  return p.replace(/^\.\//, "");
}

// 목록 밖 docs 를 가리키는 href → 저장소 원문 주소. 그 밖은 그대로.
export function toRepoIfHidden(href, here) {
  const sp = sitePathOf(href, here);
  const id = sp && hiddenDoc(sp);
  if (!id) return href;
  const i = href.indexOf("#");
  return `${REPO_BLOB}/docs/${encodeURI(id)}.md${i < 0 ? "" : href.slice(i)}`;
}

// 빌드 검사 — 산출물에 목록 밖 docs 지면 · 그것을 가리키는 링크 · sitemap 줄이 있으면 문제 목록을 낸다.
export function checkDist(dist) {
  const problems = [];
  const docsDir = join(dist, "docs");
  const walk = (d, rel) => {
    for (const name of readdirSync(d)) {
      const p = join(d, name);
      const r = rel ? `${rel}/${name}` : name;
      if (statSync(p).isDirectory()) { walk(p, r); continue; }
      if (hiddenDoc(r)) problems.push(`지면: ${r}`);
      if (!name.endsWith(".html") && name !== "sitemap.xml") continue;
      const src = readFileSync(p, "utf-8");
      if (name === "sitemap.xml") {
        for (const [, loc] of src.matchAll(/<loc>([^<]+)<\/loc>/g)) {
          const sp = sitePathOf(new URL(loc).pathname, "");
          if (sp && sp.startsWith("docs/") && hiddenDoc(sp)) problems.push(`sitemap: ${loc}`);
        }
        continue;
      }
      for (const [, h] of src.matchAll(/href="([^"]+)"/g)) {
        const sp = sitePathOf(h, rel);
        if (sp && sp.startsWith("docs/") && hiddenDoc(sp)) problems.push(`링크: ${r} → ${h}`);
      }
    }
  };
  if (existsSync(dist)) walk(dist, "");
  return problems;
}

// 자체 시험 — node astro/src/lib/public-docs.mjs --selftest
if (process.argv[1] && process.argv[1].endsWith("public-docs.mjs") && process.argv.includes("--selftest")) {
  const eq = (a, b, m) => { if (a !== b) { console.error(`FAIL ${m}: ${a} ≠ ${b}`); process.exit(1); } };
  eq(isPublicDoc("07_판정결과"), true, "편 판정결과");
  eq(isPublicDoc("STATUS"), false, "STATUS");
  eq(isPublicDoc("portfolio/C후보_측심확장_20261012"), false, "하위 폴더");
  eq(hiddenDoc("docs/작업기록.html"), "작업기록", "작업기록 숨김");
  eq(hiddenDoc("docs/FACTS.html"), null, "FACTS 공개");
  eq(sitePathOf("../docs/STATUS.html#a", "reports"), "docs/STATUS.html", "상대 경로");
  eq(sitePathOf("/incheon-port-analysis/docs/%EC%82%AC%EA%B3%A0%EA%B8%B0%EB%A1%9D.html", ""), "docs/사고기록.html", "절대 경로 · 인코딩");
  eq(sitePathOf("STATUS.html", "docs"), "docs/STATUS.html", "docs 안 상대");
  eq(toRepoIfHidden("../docs/사고기록.html#x", "reports"), `${REPO_BLOB}/docs/${encodeURI("사고기록")}.md#x`, "저장소로");
  eq(toRepoIfHidden("../docs/FACTS.html", "reports"), "../docs/FACTS.html", "공개는 그대로");
  eq(toRepoIfHidden("https://example.com/docs/STATUS.html", ""), "https://example.com/docs/STATUS.html", "외부 그대로");
  console.log("public-docs selftest OK (11)");
}

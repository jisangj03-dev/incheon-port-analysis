// 빌드 뒤 HTML 의 상대 링크를 지면 주소로 바꾼다(표시 글자는 그대로) — Jekyll(jekyll-relative-links)과 같은 결과.
//   report_07_x.md        → report_07_x.html
//   ../docs/FACTS.md#a    → ../docs/FACTS.html#a
//   ../README.md          → ../index.html   (README 가 첫 화면이었다)
// 외부(http)·앵커(#)·메일 링크는 건드리지 않는다. Astro 7 의 기본 마크다운 처리기(Sätteri)는 remark 플러그인을 안 받아서
// 렌더 단계가 아니라 산출물 단계에서 고친다.
import { readdirSync, readFileSync, writeFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { toRepoIfHidden } from "./public-docs.mjs";

export function fixHref(url) {
  if (!url || /^[a-z]+:/i.test(url) || url.startsWith("#") || url.startsWith("//")) return url;
  const i = url.indexOf("#");
  const path = i < 0 ? url : url.slice(0, i);
  const hash = i < 0 ? "" : url.slice(i);
  if (!/\.md$/i.test(decodeURIComponent(path))) return url;
  const out = /(^|\/)README\.md$/i.test(path) ? path.replace(/README\.md$/i, "index.html") : path.replace(/\.md$/i, ".html");
  return out + hash;
}

// here = 이 폴더의 산출물 뿌리 기준 경로. 공개 목록 밖 docs 를 가리키는 링크는 저장소 원문으로 돌린다(public-docs.mjs).
export function rewriteDir(dir, here = "") {
  let n = 0;
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) { n += rewriteDir(p, here ? `${here}/${name}` : name); continue; }
    if (!name.endsWith(".html")) continue;
    const src = readFileSync(p, "utf-8");
    const out = nbCells(src.replace(/href="([^"]+)"/g, (m, h) => {
      const f = toRepoIfHidden(fixHref(h), here);
      if (f !== h) n++;
      return `href="${f}"`;
    }));
    if (out !== src) writeFileSync(p, out);
  }
  return n;
}

// 짧은 숫자·날짜만 든 표 칸(「232.5」 「37.3%」 「2022-01」)에 nb 표지 — 좁은 화면에서 칸 안에서 쪼개지지 않게(2026-10-14 눈 검사).
// 글이 든 칸은 그대로 줄바꿈된다. 이미 class 가 있는 칸은 건드리지 않는다.
export function nbCells(html) {
  // 칸 안이 글자뿐이거나 <code> 하나로 감싼 글자일 때(「<code>2020-02-26</code>」)
  return html.replace(/<(td|th)((?:\s(?![^>]*\bclass=)[^>]*)?)>((?:<code>)?([^<]{1,14})(?:<\/code>)?)<\/\1>/g, (m, tag, attrs, inner, txt) =>
    /^[\d\s.,%+\-−–·()]+$/.test(txt.trim()) && /\d/.test(txt) ? `<${tag}${attrs || ""} class="nb">${inner}</${tag}>` : m);
}

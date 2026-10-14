// 화면 수치 = 데이터 파일(정체성 전환 정본 §2-1). 빌드된 지면의 보이는 글자에서 숫자를 모두 뽑아,
// 그 콘텐츠의 데이터 파일(JSON·CSV)에 있는 숫자인지 본다. 지면·컴포넌트 본문에 손으로 적은 수치를 잡는다.
// 예외: 연도(19xx·20xx)·날짜(YYYY-MM-DD) — 정본이 허용한다. 실행 중 계산되어 나중에 그려지는 값은 이 검사의 대상이 아니다
// (계산은 시험이 고정한다). 콘텐츠마다 이 검사를 그 콘텐츠의 시험에서 부른다.
//   node tools-build/check-data-numbers.mjs <지면.html> <데이터 파일…>
//   node tools-build/check-data-numbers.mjs --selftest
import { readFileSync } from "node:fs";

export function visibleText(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<head[\s\S]*?<\/head>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n));
}

const norm = (s) => { const v = Number(String(s).replace(/,/g, "")); return Number.isFinite(v) ? String(v) : s; };

export function numbersIn(text) {
  const t = text.replace(/\b\d{4}-\d{2}-\d{2}\b/g, " ");
  // 천 단위 쉼표는 세 자리 묶음일 때만 — 「M1,302.6」 같은 CSV 칸 구분을 한 숫자로 붙이지 않는다
  return [...t.matchAll(/\d{1,3}(?:,\d{3})+(?:\.\d+)?(?!\d)|\d+(?:\.\d+)?/g)].map((m) => m[0]).filter((n) => !/^(19|20)\d{2}$/.test(n));
}

// 지면 머리·바닥글(공통 틀)은 빼고 콘텐츠 본문만 본다 — data-sim/data-content 표지부터 그 뒤 첫 <script 앞까지.
export function contentOf(html) {
  const i = html.search(/data-(sim|content)=/);
  if (i < 0) return html;
  const j = html.indexOf("<script", i);
  return html.slice(html.lastIndexOf("<", i), j < 0 ? undefined : j);
}

export function check(html, dataTexts) {
  html = contentOf(html);
  // 데이터 파일은 CSV 쉼표를 칸 구분으로도 읽는다(「M1,302.6」 → 302.6) — 천 단위 묶음으로 읽은 것과 둘 다 허용
  const allowed = new Set(dataTexts.flatMap((t) => [...numbersIn(t), ...numbersIn(t.replace(/,/g, " "))].map(norm)));
  const found = numbersIn(visibleText(html));
  const bad = [...new Set(found.map(norm).filter((n) => !allowed.has(n)))];
  return { checked: found.length, bad };
}

if (process.argv[1] && process.argv[1].endsWith("check-data-numbers.mjs")) {
  if (process.argv.includes("--selftest")) {
    const data = ['{"weeks":36,"cost":{"holding":0.5},"cite":"Management Science, 35(3), 321–339"}'];
    const ok = check("<h1>36주</h1><p>재고 0.5 · 35(3) · 2026-10-14 · 1989</p><script>var x=999</script>", data);
    const ng = check('<footer>2,000</footer><div data-sim="x"><p>재고 12상자</p></div><script></script>', data);
    const csv = check('<div data-sim="x"><td>302.6</td><td>1,302</td></div>', ["a,M1,302.6\nb,\"1,302\""]);
    if (ok.bad.length || ok.checked !== 4 || ng.bad.join() !== "12" || csv.bad.length) { console.error("FAIL selftest", ok, ng, csv); process.exit(1); }
    console.log("check-data-numbers selftest OK (3)");
    process.exit(0);
  }
  const [html, ...files] = process.argv.slice(2);
  const r = check(readFileSync(html, "utf-8"), files.map((f) => readFileSync(f, "utf-8")));
  console.log(`[화면 수치] ${html} — 숫자 ${r.checked}개 검사 · 데이터 파일 밖 ${r.bad.length}개${r.bad.length ? ": " + r.bad.join(", ") : ""}`);
  process.exit(r.bad.length ? 1 : 0);
}

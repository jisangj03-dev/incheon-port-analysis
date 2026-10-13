// 기준 사이트 추출 결과(dembrandt --json-only)에서 「수치」만 남긴다 — 디자인 도구 판정 v3 경계.
// 남기는 것: 색(hex·rgb·hsl)·글꼴 이름·크기·여백·라운드·그림자·중단점 같은 값.
// 버리는 것: 로고·파비콘·이미지·스크린샷(data URI 포함)·문구·HTML·SVG·외부 주소 — 남의 이미지·문구·코드를 들이지 않는다.
//   node tools-build/design-tokens.mjs <dembrandt.json> <out.json>   → 요약 마크다운을 표준 출력으로
//   node tools-build/design-tokens.mjs --selftest
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

const DROP_KEY = /logo|favicon|image|img|screenshot|svg|icon|html|url|href|src|^og/i; // 문구는 아래 KEEP_STR 가 걸러 낸다(색·크기 꼴만 통과)
const KEEP_STR = /^(#[0-9a-f]{3,8}|rgba?\(|hsla?\(|oklch\(|-?\d+(\.\d+)?(px|rem|em|%|ms|s|vw|vh)?(\s+-?\d+(\.\d+)?(px|rem|em|%)?)*$)/i;

export function sanitize(v, key = "") {
  if (key && DROP_KEY.test(key)) return undefined;
  if (typeof v === "number" || typeof v === "boolean" || v === null) return v;
  if (typeof v === "string") {
    if (/^data:|^https?:\/\/|<[a-z]/i.test(v) || v.length > 120) return undefined;
    // 글꼴 이름은 문자열 그대로(fontFamily 류 키에서만)
    if (/font|family/i.test(key)) return v;
    return KEEP_STR.test(v.trim()) ? v.trim() : undefined;
  }
  if (Array.isArray(v)) { const a = v.map((x) => sanitize(x, key)).filter((x) => x !== undefined); return a.length ? a : undefined; }
  if (typeof v === "object") {
    const o = {};
    for (const [k, x] of Object.entries(v)) { const s = sanitize(x, k); if (s !== undefined) o[k] = s; }
    return Object.keys(o).length ? o : undefined;
  }
  return undefined;
}

export function summarize(clean) {
  const colors = new Set(), fonts = new Set(), sizes = new Set();
  const walk = (v, k = "") => {
    if (typeof v === "string") {
      if (/^(#|rgb|hsl|oklch)/i.test(v)) colors.add(v.toLowerCase());
      else if (/font|family/i.test(k)) fonts.add(v);
      else if (/px|rem/.test(v)) sizes.add(v);
    } else if (Array.isArray(v)) v.forEach((x) => walk(x, k));
    else if (v && typeof v === "object") Object.entries(v).forEach(([kk, x]) => walk(x, kk));
  };
  walk(clean);
  return { colors: [...colors], fonts: [...fonts], sizes: [...sizes] };
}

if (process.argv[1] && process.argv[1].endsWith("design-tokens.mjs")) {
  if (process.argv.includes("--selftest")) {
    const raw = { logo: { url: "https://x/logo.svg", data: "data:image/png;base64,AAA" }, favicon: "data:x", colors: { primary: "#0A2540", list: ["rgb(1, 2, 3)", "hero headline copy here"] },
      typography: { fontFamily: "Inter, sans-serif", sizes: ["16px", "1.25rem"], heading: { text: "Ship faster" } }, spacing: ["4px", "8px"], screenshot: "data:image/png;base64,BBB" };
    const c = sanitize(raw);
    const s = JSON.stringify(c);
    if (/logo|favicon|data:|Ship faster|hero headline|screenshot/.test(s) || !s.includes("#0A2540") || !s.includes("Inter") || !s.includes("8px")) { console.error("FAIL", s); process.exit(1); }
    const sum = summarize(c);
    if (sum.colors.length !== 2 || sum.fonts.length !== 1) { console.error("FAIL summary", sum); process.exit(1); }
    console.log("design-tokens selftest OK (2)");
    process.exit(0);
  }
  const [inp, out] = process.argv.slice(2);
  const raw = JSON.parse(readFileSync(inp, "utf-8"));
  const clean = sanitize(raw) || {};
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, JSON.stringify(clean, null, 1) + "\n");
  const s = summarize(clean);
  console.log(`- 색 ${s.colors.length}개: ${s.colors.slice(0, 16).join(" · ")}`);
  console.log(`- 글꼴 ${s.fonts.length}개: ${s.fonts.slice(0, 6).join(" · ")}`);
  console.log(`- 크기·여백 값 ${s.sizes.length}개: ${s.sizes.slice(0, 20).join(" · ")}`);
  console.log(`- 원본 ${readFileSync(inp).length}B → 수치만 ${JSON.stringify(clean).length}B`);
}

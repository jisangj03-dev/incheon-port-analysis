// 출고 검사(2026-10-14 정체성 §5-4 공개 전환 · 선장님 위임 「스스로 거르는 출고 검사」) — 공개 빌드(astro/dist)를 파일로 전부 훑는다.
// 화면을 띄워 재는 것(외부 요청·넘침·오류)은 criteria.spec · ds.spec 이 지면마다 한다. 여기는 빌드 산출물 전체에 대한 판정이다.
//  ① 깨진 내부 링크 0 ② 외부 자원 0 — Cloudflare 분석 비콘 하나만(2026-10-14 채팅이 코드를 줬다 · 그 밖은 0) ③ 개인 주소·전화·학번·메일 원문 0
//  ④ AI 표기 = 「AI 정리 · 〈실명〉 검수」 ⑤ 자문 아님 고지가 모든 지면에 ⑥ 공공 데이터 차트의 출처 줄에 공공누리 유형 ⑦ 자산 출처 목록 밖 파일 0
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname, posix } from "node:path";

const DIST = "astro/dist", BASE = "/incheon-port-analysis";
// lab 빌드 여부는 산출물로 판단한다 — CI 는 빌드에만 SOUNDING_LAB=1 을 주고 시험 프로세스에는 안 준다
const LAB = !!process.env.SOUNDING_LAB || existsSync("astro/dist/lab");
const walk = (d) => readdirSync(d).flatMap((n) => { const p = join(d, n); return statSync(p).isDirectory() ? walk(p) : [p]; });
const ALL = existsSync(DIST) ? walk(DIST).map((p) => p.slice(DIST.length + 1).split("\\").join("/")) : [];
const PUBLIC = ALL.filter((f) => !f.startsWith("lab/") && !f.startsWith("pagefind/"));
const HTML = PUBLIC.filter((f) => f.endsWith(".html") && f !== "googledd0ee48b82282e37.html");
const read = (f) => readFileSync(join(DIST, f), "utf-8");
const P = JSON.parse(readFileSync("data/profile.json", "utf-8"));

test("공개 빌드에 lab/ 이 없다", () => {
  test.skip(LAB, "SOUNDING_LAB=1 빌드");
  expect(existsSync(join(DIST, "lab"))).toBe(false);
  expect(HTML.length).toBeGreaterThan(20);
});

test("① 깨진 내부 링크 0 — 모든 지면의 href·src 가 빌드 안의 파일로 간다", () => {
  const exists = (rel) => {
    const p = join(DIST, rel);
    if (existsSync(p) && statSync(p).isFile()) return true;
    return existsSync(join(p, "index.html"));
  };
  const bad = [];
  for (const f of HTML) {
    const html = read(f);
    for (const m of html.matchAll(/\s(?:href|src)="([^"]+)"/g)) {
      let v = m[1].replace(/&amp;/g, "&");
      if (/^(https?:|mailto:|tel:|data:|javascript:|#|\/\/)/.test(v) || v.includes("${")) continue;
      v = v.split("#")[0].split("?")[0];
      if (!v) continue;
      let rel;
      if (v.startsWith(BASE + "/") || v === BASE) rel = v.slice(BASE.length + 1);
      else if (v.startsWith("/")) { bad.push(`${f} → ${m[1]} (기준주소 밖)`); continue; }
      else rel = posix.normalize(posix.join(posix.dirname(f), v));
      try { rel = decodeURI(rel); } catch {}
      if (LAB && rel.startsWith("lab/")) continue;
      if (!exists(rel)) bad.push(`${f} → ${m[1]}`);
    }
  }
  expect(bad, "깨진 링크").toEqual([]);
});

test("② 외부 자원 0 — 스크립트·스타일·그림·글꼴·틀을 밖에서 받지 않는다", () => {
  const bad = [];
  // 허용 = Cloudflare 분석 비콘 스크립트 하나(site.ts CF_BEACON) — 지면마다 많아야 한 번 · 다른 바깥 자원은 0
  const CF = /^<script type='module' src='https:\/\/static\.cloudflareinsights\.com\/beacon\.min\.js' data-cf-beacon=/;
  for (const f of HTML) {
    const html = read(f);
    if ((html.match(/cloudflareinsights/g) || []).length > 1) bad.push(`${f}: Cloudflare 비콘이 두 번 이상`);
    for (const m of html.matchAll(/<script type='module' src='https:\/\/static\.cloudflareinsights[^>]*>/g)) if (!CF.test(m[0])) bad.push(`${f}: Cloudflare 비콘 모양이 다르다`);
    for (const m of html.matchAll(/<(script|img|iframe|video|audio|source|embed)\b[^>]*\ssrc="(https?:)?\/\/[^"]+"/g)) bad.push(`${f}: ${m[0].slice(0, 120)}`);
    for (const m of html.matchAll(/<link\b[^>]*rel="(?:stylesheet|preload|modulepreload|preconnect|dns-prefetch|icon|manifest)"[^>]*href="(https?:)?\/\/[^"]+"/g)) bad.push(`${f}: ${m[0].slice(0, 120)}`);
    for (const m of html.matchAll(/url\(\s*['"]?(https?:)?\/\/[^)]+\)/g)) bad.push(`${f}: ${m[0].slice(0, 120)}`);
  }
  expect(bad).toEqual([]);
});

test("③ 개인정보 — 메일 원문 · 전화번호 · 학번 · 집 주소 0", () => {
  const TEXT = PUBLIC.filter((f) => /\.(html|csv|xml|txt|json)$/.test(f));
  const bad = [];
  for (const f of TEXT) {
    const s = read(f);
    for (const m of s.matchAll(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g)) if (!/@(users\.noreply\.github\.com|example\.(com|org))$/.test(m[0])) bad.push(`${f}: 메일 ${m[0]}`);
    // 관세율표 류별 파일(data/tariff/<류>.json)은 HSK 10자리 코드 — 01류(0101…)가 휴대전화 모양에 걸린다(QA 250) · 메일·학번 검사는 그대로
    if (!/(^|\/)data\/tariff\/\d+\.json$/.test(f)) for (const m of s.matchAll(/(?<![\d.])01[016789][-. ]?\d{3,4}[-. ]?\d{4}(?![\d.])/g)) bad.push(`${f}: 전화 ${m[0]}`);
    if (/학번/.test(s)) bad.push(`${f}: 「학번」`);
  }
  expect(bad).toEqual([]);
  // 프로필 파일에는 그런 칸 자체가 없다
  const keys = JSON.stringify(Object.keys(P).concat(Object.keys(P.contact)));
  for (const k of ["phone", "tel", "address", "student", "학번", "전화", "주소"]) expect(keys, k).not.toContain(k);
  expect(JSON.stringify(P.contact.mail)).not.toContain("@");
});

test("④ AI 표기 — AI 산출물 지면마다 「AI 정리 · 실명 검수」 · 검수 전 표기 0", () => {
  const MARK = `AI 정리 · ${P.name} 검수`;
  for (const f of ["map.html", "map/vessels.html", "sim/beer-game.html", "sim/forecast.html", "notes/port-yoy.html", "notes/ai-ops.html"]) {
    const html = read(f);
    expect(html, `${f} 표기`).toMatch(new RegExp(`data-ai-mark[^>]*>\\s*${MARK.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`));
  }
  for (const f of HTML) expect(read(f), `${f} 「검수 전」`).not.toContain("AI 정리 · 검수 전");
});

test("⑤ 자문 아님 고지 · 실명 — 모든 지면 바닥글", () => {
  for (const f of HTML.filter((f) => !f.startsWith("embed/") && !f.startsWith("og/"))) {
    const html = read(f);
    expect(html, f).toContain("법률·세무·관세 자문이 아닙니다");
    expect(html, f).toContain(`${P.name}의`);
  }
});

test("⑥ 공공 데이터 차트의 출처 줄 = 출처 대장 그대로(공공누리 유형 포함 · 이용 조건은 줄 아래 접기 — 품질기준 Q5)", () => {
  const DATAPAGES = ["index.html", "map.html", "map/vessels.html", "notes/port-yoy.html"];
  for (const f of DATAPAGES) {
    const trust = [...read(f).matchAll(/<p class="s-trust[^"]*"[^>]*>([\s\S]*?)<\/p>/g)].map((m) => m[1]);
    expect(trust.length, `${f} 신뢰 꼬리`).toBeGreaterThan(0);
    for (const t of trust) expect(t, `${f} 출처 한 줄에 행정 문구`).not.toMatch(/공공누리|이용허락/);
    expect(read(f), `${f} 이용 조건 접기`).toMatch(/<details class="s-terms"[^>]*>[\s\S]*?공공누리[\s\S]*?<\/details>/);
  }
  expect(read("sim/forecast.html")).toContain("공공누리");
  // 보고서는 출처 대장의 used_by 로 이용허락 줄을 단다
  for (const f of HTML.filter((f) => /^reports\/[^/]+\.html$/.test(f) && !f.endsWith("index.html"))) expect(read(f), f).toMatch(/data-sources[^>]*>출처와 이용허락 — [^<]*공공누리/);
});

test("⑦ 자산 출처 — 그림·영상·글꼴은 목록에 적힌 자리에서만(기준 사이트 자산 복제 0)", () => {
  // 자리마다 출처: _a = 발행본 그림(Astro 최적화) · reports/images = 발행본 그림 · assets = 자체 OG·아이콘 · media = 자체 AI 생성 장면(README 가 출처) ·
  // fonts = @fontsource Pretendard · Noto Serif KR(OFL-1.1) · og = 빌드가 만든 공유 카드 · tiles = OpenStreetMap(Protomaps) · vendor = npm 고정판(maplibre 등)
  const OK = /^(_a|reports\/images|assets|media|fonts\/(pretendard|noto-serif-kr)|og|tiles|vendor)\//;
  const BIN = PUBLIC.filter((f) => /\.(png|jpe?g|webp|avif|gif|svg|mp4|webm|woff2?|ttf|otf)$/i.test(f));
  expect(BIN.filter((f) => !OK.test(f)), "목록 밖 자산").toEqual([]);
});

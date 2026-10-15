// 관세율표 스냅샷(HS 2단위 류별 · tools-build/tariff_fetch.py --build → data/derived/tariff/<류>.json 그대로) — 수입원가 계산기가 HS 코드를 넣을 때만 받는다(같은 사이트 · 외부 요청 0).
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "../../../lib/content";
const DIR = join(repoRoot(), "data/derived/tariff");
export function getStaticPaths() {
  return existsSync(DIR) ? readdirSync(DIR).filter((f) => /^\d{2}\.json$/.test(f)).map((f) => ({ params: { ch: f.slice(0, 2) } })) : [];
}
export function GET({ params }: { params: { ch: string } }) {
  return new Response(readFileSync(join(DIR, `${params.ch}.json`), "utf-8"), { headers: { "Content-Type": "application/json" } });
}

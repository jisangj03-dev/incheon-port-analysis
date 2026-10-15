// 수도권 배송 등시선 격자(tools-build/v3/osm_iso.py → data/derived/isochrones.json 그대로) — 도구 지면이 지연 로딩으로 받는다.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot } from "../../lib/content";
export function GET() { return new Response(readFileSync(join(repoRoot(), "data/derived/isochrones.json"), "utf-8"), { headers: { "Content-Type": "application/json" } }); }

// sitemap.xml(개편 기준 9) — 독자용 지면만 싣는다. 기록 문서(docs/·analysis/)는 공개돼 있으나 싣지 않는다.
import { getCollection } from "astro:content";
import { abs } from "../lib/site";
import { lastUpdated } from "../lib/content";

export async function GET() {
  const reports = await getCollection("reports");
  // 구조 넷(정체성 §2 · 2026-10-14) — 지도 · 시뮬레이션 · 노트 · 소개. 옛 목록·입구(/reports/ · /tools/ · /for/*)는 돌려보내는 주소라 싣지 않는다.
  const pages: [string, string][] = [
    ["/", lastUpdated("astro/src/pages/index.astro")],
    ["/map.html", lastUpdated("analysis/terminal_monthly_long.csv")],
    ["/map/follow.html", lastUpdated("data/derived/supply_hs85.json")],
    ["/map/vessels.html", lastUpdated("data/derived/vessel_replay.json")],
    ["/sim/", lastUpdated("data/rooms.json")],
    ["/sim/beer-game.html", lastUpdated("data/sim/beer-game.json")],
    ["/sim/forecast.html", lastUpdated("data/forecast/lab.json")],
    ["/notes.html", lastUpdated("data/rooms.json")],
    ["/notes/port-yoy.html", lastUpdated("analysis/terminal_monthly_long.csv")],
    ["/notes/ai-ops.html", lastUpdated("data/derived/ops_stats.json")],
    ...reports.map((r) => [`/reports/${r.id}.html`, lastUpdated(`reports/${r.id}.md`)] as [string, string]),
    ["/tools/logistics-cost.html", lastUpdated("assets/js/cost-check.js")],
    ["/tools/simulate.html", lastUpdated("assets/js/cost-sim.js")],
    ["/tools/warehouse-map.html", lastUpdated("_data/warehouse_gu.json")],
    ["/about.html", lastUpdated("astro/src/pages/about.astro")],
    ["/data.html", lastUpdated("data/sources.json")],
  ];
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${pages
    .map(([p, d]) => `  <url><loc>${encodeURI(abs(p))}</loc>${d ? `<lastmod>${d}</lastmod>` : ""}</url>`)
    .join("\n")}\n</urlset>\n`;
  return new Response(body, { headers: { "Content-Type": "application/xml; charset=utf-8" } });
}

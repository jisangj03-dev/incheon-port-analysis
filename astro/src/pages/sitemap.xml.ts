// sitemap.xml(개편 기준 9) — 독자용 지면만 싣는다. 기록 문서(docs/·analysis/)는 공개돼 있으나 싣지 않는다.
import { getCollection } from "astro:content";
import { abs } from "../lib/site";
import { lastUpdated } from "../lib/content";

export async function GET() {
  const reports = await getCollection("reports");
  const pages: [string, string][] = [
    ["/", lastUpdated("astro/src/pages/index.astro")],
    ["/reports/", lastUpdated("reports")],
    ...reports.map((r) => [`/reports/${r.id}.html`, lastUpdated(`reports/${r.id}.md`)] as [string, string]),
    ["/tools/", lastUpdated("astro/src/pages/tools")],
    ["/tools/logistics-cost.html", lastUpdated("assets/js/cost-check.js")],
    ["/tools/warehouse-map.html", lastUpdated("_data/warehouse_gu.json")],
    ["/about.html", lastUpdated("astro/src/pages/about.astro")],
    ["/data.html", lastUpdated("data/sources.json")],
    ["/for/pro.html", ""], ["/for/press.html", ""], ["/for/student.html", ""],
  ];
  const body = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${pages
    .map(([p, d]) => `  <url><loc>${encodeURI(abs(p))}</loc>${d ? `<lastmod>${d}</lastmod>` : ""}</url>`)
    .join("\n")}\n</urlset>\n`;
  return new Response(body, { headers: { "Content-Type": "application/xml; charset=utf-8" } });
}

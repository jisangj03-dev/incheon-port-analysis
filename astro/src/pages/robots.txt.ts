// robots.txt(개편 기준 9). 프로젝트 사이트라 호스트 뿌리(/robots.txt)는 우리 것이 아니다 —
// 검색엔진은 호스트 뿌리의 robots.txt 만 읽는다. 이 파일은 기준 9의 「200」과 sitemap 위치 안내를 위한 것이고,
// sitemap 은 Search Console 에 직접 제출해야 한다(선장님 손 · PR 본문).
import { abs } from "../lib/site";
export function GET() {
  return new Response(`User-agent: *\nAllow: /\nDisallow: /incheon-port-analysis/go/\n\nSitemap: ${abs("/sitemap.xml")}\n`, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}

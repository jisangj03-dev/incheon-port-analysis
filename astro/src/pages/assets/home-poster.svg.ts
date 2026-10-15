// 홈 살아 있는 지도의 정지 그림(자체 · 빌드 때 그림 · lib/home-poster.ts)
import { poster } from "../../lib/home-poster";
export function GET() { return new Response(poster().svg, { headers: { "Content-Type": "image/svg+xml" } }); }

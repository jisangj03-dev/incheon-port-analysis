// 따라가기 지면의 정지 그림 — 아시아에서 시작하는 첫 장면(홈은 2026-10-15 부터 수도권 첫 화면이라 그림을 나눴다)
import { poster } from "../../lib/home-poster";
import { VIEWS } from "../../lib/flowmap";
export function GET() { return new Response(poster(VIEWS.asia).svg, { headers: { "Content-Type": "image/svg+xml" } }); }

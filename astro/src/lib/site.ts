// 사이트 상수 — 이름·문구·바깥 링크는 여기 한 곳에만 둔다. 이름은 코드·주소에 묶지 않는다(디자인 브리프 §5).
export const BRAND = {
  name: "측심",
  latin: "SOUNDING",
  tagline: "SCM 작업실",
  // [2026-10-15 P2 · 선장님 판정 「공개 전 개편」] 범위 = 수도권 물류·무역·유통 · 인천은 그 관문 · 목적에 「사업」(중소기업·셀러 문의 창구)
  lede: "수도권의 물류·무역·유통을, 그 관문 인천에서부터 실제 데이터를 움직여 보여 줍니다.",
  description:
    "측심 — 수도권 물류·무역·유통을 공공 통계와 공개 지도로 재는 SCM 작업실(관문 = 인천). 도구·시뮬레이션·노트 · 원시 데이터와 재현 코드 공개 · 중소기업·셀러 문의 환영.",
  author: "측심", // 실명은 data/profile.json 한 곳(정체성 §5-4) — 여기 적지 않는다
};

export const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");
/** 사이트 안 경로 → 기준주소를 붙인 경로. `u("/tools/")` → `/incheon-port-analysis/tools/` */
export const u = (p: string) => `${BASE}${p.startsWith("/") ? p : `/${p}`}`;
export const SITE = "https://jisangj03-dev.github.io";
export const abs = (p: string) => `${SITE}${u(p)}`;

export const REPO = "https://github.com/jisangj03-dev/incheon-port-analysis";
export const ISSUES = `${REPO}/issues/new`;

/** 바깥으로 나가는 링크의 LIVE 스위치. 판매 중·게시 중이 확인된 것만 true(기준 22 · 갈래 기준 C6).
 *  사이트 밖 링크는 /go/<id>.html 을 한 번 거친다 — 방문 수로 클릭을 센다(쿠키 0 · 외부 요청 0). */
export const OUT: Record<string, { live: boolean; url: string; label: string }> = {
  criteria: { live: true, url: "https://logisticsforeveryone.tistory.com/78", label: "셀러 물류비 판정 기준(블로그)" },
  sheet: { live: true, url: "https://logisticsforeveryone.tistory.com/79", label: "무료 3PL 견적 비교표(엑셀 · 블로그 /79)" },
  // [2026-10-14 정체성 전환] 크몽 판매 동선은 걷었다 — 옛 주소(/go/kmong-…)는 살아 있되 첫 화면으로 돌려보낸다(live:false).
  "kmong-829076": { live: false, url: "https://kmong.com/gig/829076", label: "정산·마진 시트(크몽)" },
  "kmong-824011": { live: false, url: "https://kmong.com/gig/824011", label: "광고 주간 리포트(크몽)" },
  blog: { live: true, url: "https://logisticsforeveryone.tistory.com/", label: "블로그" },
  // 뉴스레터(물류로그 · beehiiv) — 2026-10-12 선장님 지정. 클릭은 /go/newsletter.html 방문 수로 센다(기준 24·29).
  newsletter: { live: true, url: "https://logisticslog.beehiiv.com/subscribe?utm_source=sounding&utm_medium=site&utm_campaign=footer", label: "뉴스레터(물류로그)" },
};
export const go = (id: string) => u(`/go/${id}.html`);
export const newsletterHref = () => (OUT.newsletter.live ? go("newsletter") : go("blog"));
export const newsletterLabel = () => (OUT.newsletter.live ? "뉴스레터 구독" : "새 글 받아보기");

// 구조(정체성 §2 · 2026-10-20 품질 재정비) — 첫 화면이 지도(본체)다 · 도구 · 노트 · 소개. 지도 지면(/map.html)은 내렸다(빈 지도 · docs/품질기준.md).
export const NAV = [
  { id: "tools", href: "/tools/", label: "도구" },
  { id: "notes", href: "/notes.html", label: "노트" },
  { id: "about", href: "/about.html", label: "소개" },
];

/** Cloudflare Web Analytics — 공개 화면 외부 요청 0 의 유일한 예외(기준 17 · 28). 공개되는 값이라 비밀값이 아니다. */
// [2026-10-14 공개 전환] 채팅 지시: 「Cloudflare 분석 1개 자리만 비워 두기 — 코드는 채팅이 나중에 준다」. 토큰이 비면 비컨을 싣지 않는다(외부 요청 0).
//   이전 토큰(d508…7)은 check_private PUBLIC_IDS 에 근거와 함께 남아 있다 — 되살리려면 이 한 줄.
export const CF_BEACON = { src: "https://static.cloudflareinsights.com/beacon.min.js", token: "d50802d5e62b45baa1de6d74ea63add7" };

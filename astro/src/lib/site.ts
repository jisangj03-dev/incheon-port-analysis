// 사이트 상수 — 이름·문구·바깥 링크는 여기 한 곳에만 둔다. 이름은 코드·주소에 묶지 않는다(디자인 브리프 §5).
export const BRAND = {
  name: "측심",
  latin: "SOUNDING",
  tagline: "인천 물류를 잰다",
  lede: "인천 물류를 공공 데이터로 잰다 — 그리고 내 물류비도.",
  description:
    "인천 물류를 공공 1차 데이터로 재는 허브. 항만 물동량·물류창고·품목별 수출입 보고서와 셀러 물류비 계산기 · 원시 데이터와 재현 코드 공개.",
  author: "물류로그", // 필명만 — 실명 금지(지침 §2.2-3)
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
  "kmong-829076": { live: false, url: "https://kmong.com/gig/829076", label: "정산·마진 시트(크몽)" },
  "kmong-824011": { live: true, url: "https://kmong.com/gig/824011", label: "광고 주간 리포트(크몽)" },
  blog: { live: true, url: "https://logisticsforeveryone.tistory.com/", label: "블로그" },
  // 뉴스레터 — 주소가 정해지면 url 을 바꾸고 live 를 true 로. 그 전에는 블로그 구독으로 안내한다(기준 24 · 선장님 손).
  newsletter: { live: false, url: "", label: "뉴스레터" },
};
export const go = (id: string) => u(`/go/${id}.html`);
export const newsletterHref = () => (OUT.newsletter.live ? go("newsletter") : go("blog"));
export const newsletterLabel = () => (OUT.newsletter.live ? "뉴스레터 구독" : "새 글 받아보기");

export const NAV = [
  { href: "/reports/", label: "보고서" },
  { href: "/tools/", label: "도구" },
  { href: "/map.html", label: "지도" },
  { href: "/data.html", label: "데이터" },
  { href: "/about.html", label: "신뢰" },
];

/** 사람별 입구(기준 12 · A1). */
export const PERSONAS = [
  { key: "seller", who: "셀러", need: "택배비·3PL 견적이 맞는지", href: "/tools/logistics-cost.html", cta: "견적 비교 계산기" },
  { key: "pro", who: "물류 실무자 · 채용 담당자", need: "인천 창고·항만 현황을 한눈에", href: "/for/pro.html", cta: "현황 보기" },
  { key: "press", who: "기자 · 연구자", need: "출처가 붙은 숫자와 원자료", href: "/for/press.html", cta: "근거 자료" },
  { key: "student", who: "학생", need: "인천 물류를 처음부터", href: "/for/student.html", cta: "처음 읽을 것" },
];

/** Cloudflare Web Analytics — 공개 화면 외부 요청 0 의 유일한 예외(기준 17 · 28). 공개되는 값이라 비밀값이 아니다. */
export const CF_BEACON = { src: "https://static.cloudflareinsights.com/beacon.min.js", token: "d50802d5e62b45baa1de6d74ea63add7" };

// 초크포인트 덧칸(P1 ③ · 2026-10-15) — 우회 거리·일수 · 운임 충격(KCCI 실측) · 품목(HS2) 상위 · 경유 규칙. 서버 첫 그림과 단추 뒤 화면이 같은 함수를 쓴다.
const n = (v: number) => Math.round(v).toLocaleString("ko-KR");
export function chokeMore(p: any): string {
  const d = p.detour, s = p.shock, h = p.hs_top, r = p.rule;
  const det = !d ? "" : d.extra_nm != null
    ? `<p><b>막히면</b> 대표 항로 ${d.route} <b>+${n(d.extra_nm)}해리</b> · ${d.knot}노트로 <b>+${d.extra_days}일</b> <small>(searoute 해상 경로망 최단 거리 · 속력 가정)</small></p>`
    : `<p><b>막히면</b> ${d.route} — ${d.note}</p>`;
  const sh = s && s.routes?.length
    ? `<p><b>운임 충격(실측)</b> ${s.event}: ${s.routes.map((x: any) => `${x.ko} 운임지수 <b>+${x.pct}%</b>(평소 ${n(x.base)} → ${x.peak_week} ${n(x.peak)})`).join(" · ")} <small>(KCCI · 평소 = ${s.base_window[0].slice(0, 7)} 주 평균)</small></p>`
    : `<p><b>운임 충격</b> 원천 기간(2022-11~)에 이 길목이 막힌 적이 없어 실측이 없습니다.</p>`;
  const hs = h && h.items?.length
    ? `<p><b>품목(HS 2단위 · ${h.ym.slice(0, 4)}-${h.ym.slice(4)})</b> ${h.items.map((x: any) => `${x.name} ${x.pct}%`).join(" · ")}</p>`
    : `<p><b>품목</b> 관세청 품목별 국가별 원천에 이 길목 나라들의 줄이 없어 싣지 않았습니다.</p>`;
  const rule = r ? `<details><summary>경유 규칙 — 이 길목을 지난다고 본 나라 ${r.countries.length}곳</summary><p>${r.countries.map((c: any) => c.name).join(" · ")}</p><p class="s-cap">${r.basis}</p></details>` : "";
  return det + sh + hs + rule;
}

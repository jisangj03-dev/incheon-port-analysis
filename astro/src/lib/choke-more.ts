// 초크포인트 덧칸(P1 ③ · 2026-10-15) — 우회 거리·일수 · 운임 충격(KCCI 실측) · 경유 나라. 서버 첫 그림과 단추 뒤 화면이 같은 함수를 쓴다.
const n = (v: number) => Math.round(v).toLocaleString("ko-KR");
export function chokeMore(p: any): string {
  const d = p.detour, s = p.shock, r = p.rule;
  const det = !d ? "" : d.extra_nm != null
    ? `<p><b>막히면</b> 대표 항로 ${d.route} <b>+${n(d.extra_nm)}해리</b> · ${d.knot}노트로 <b>+${d.extra_days}일</b> <small>(searoute 해상 경로망 최단 거리 · 속력 가정)</small></p>`
    : `<p><b>막히면</b> ${d.route} — ${d.note}</p>`;
  const sh = s && s.routes?.length
    ? `<p><b>운임 충격(실측 · 부산발 수출 컨테이너 운임지수)</b> ${p.id === "hormuz" ? "한국이 이 해협으로 들여오는 것은 대부분 원유·LNG(탱커)다 — 탱커 운임은 무료 공개 원천이 없어 싣지 않았다. 아래는 같은 바다를 지나는 중동행 컨테이너 운임이다. " : ""}${s.event}: ${s.routes.map((x: any) => `${x.ko} 운임지수 <b>+${x.pct}%</b>(평소 ${n(x.base)} → ${x.peak_week} ${n(x.peak)})`).join(" · ")} <small>(KCCI · 평소 = ${s.base_window[0]}~${s.base_window[1]} 주 평균 · 정점 = 그 뒤 가장 높았던 주)</small></p>`
    : `<p><b>운임 충격</b> 원천 기간(PortWatch 2023~)에 이 길목 통항이 2023년 평균의 30% 아래로 4주 넘게 떨어진 적이 없어, 사건 전후 운임을 견주지 않았습니다.</p>`;
  // [2026-10-20 사실 대조] 품목(HS2) 칸은 이 길목 나라 전부가 아니라 수집한 10개국만 분모로 써(홍해 = 독일 한 나라) 뺐다 — 나라 전부를 받으면 다시 단다
  const rule = r ? `<details><summary>이 길목을 거치는 것으로 셈한 나라 ${r.countries.length}곳(해상 항로 기준)</summary><p>${r.countries.map((c: any) => c.name).join(" · ")}</p><p class="s-cap">${r.basis}</p></details>` : "";
  return det + sh + rule;
}

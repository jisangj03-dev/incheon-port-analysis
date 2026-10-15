// 맥주 게임 「직접 해 보기」 체험층(2026-10-14 선장님 판정 「동적인 콘텐츠」 · 채팅 위임 C) — 계산은 그대로(assets/js/beer-game.js · beer-ui.ts).
// 더하는 것: ① 공급망 띠(공장 → 유통 → 도매 → 소매 → 소비자 · 내 단계 강조 · 매주 상자·주문이 실제로 흐른다)
// ② 빠른 주문 단추(들어온 만큼 · ±) ③ 끝나면 내 점수(같은 자리를 논문 습관이 맡았을 때와 겨룸) ④ 공유 카드(캔버스 그림 · 저장 · 공유 · 서버 0).
type Rules = any;
const $ = (id: string) => document.getElementById(id)!;
const fmt = (n: number) => n.toLocaleString("ko-KR", { maximumFractionDigits: 1 });

export function initBeerPlay() {
  const R: Rules = JSON.parse($("beer-rules").textContent || "{}");
  const S = R.stages.length;
  // ① 띠 — 왼쪽이 공장(물건이 오른쪽으로 흐른다) · 오른쪽 끝이 소비자. 남의 단계 숫자는 원 규칙대로 가린다.
  const chain = $("chain");
  const order = [...R.stages.map((s: any, i: number) => ({ i, label: s.label }))].reverse();
  chain.innerHTML = order.map((s) => `<div class="node" data-i="${s.i}"><b>${s.label}</b><span class="inv" data-inv></span></div><div class="pipe" data-pipe="${s.i}"><i class="box"></i><i class="ord"></i></div>`).join("") +
    `<div class="node node--end"><b>소비자</b><span class="inv" data-dem></span></div>`;

  let role = -1;
  document.addEventListener("beer:start", (e: any) => {
    role = e.detail.opt.role;
    for (const n of chain.querySelectorAll<HTMLElement>(".node[data-i]")) n.classList.toggle("me", Number(n.dataset.i) === role);
    paint(e.detail.g, false);
  });
  document.addEventListener("beer:step", (e: any) => paint(e.detail.g, true));
  const paint = (g: any, move: boolean) => {
    for (const n of chain.querySelectorAll<HTMLElement>(".node[data-i]")) {
      const i = Number(n.dataset.i), st = g.stages[i];
      (n.querySelector("[data-inv]") as HTMLElement).textContent = i === role ? `재고 ${st.inventory}` : "?";
    }
    const last = g.week - 1;
    (chain.querySelector("[data-dem]") as HTMLElement).textContent = last >= 0 ? `이번 주 ${g.demand[last]}상자` : "";
    if (!move) return;
    // 상자는 오른쪽(아래 단계)으로, 주문은 왼쪽(위 단계)으로 한 칸 — 매주 다시 튼다
    for (const p of chain.querySelectorAll<HTMLElement>(".pipe")) { p.classList.remove("go"); void p.offsetWidth; p.classList.add("go"); }
    // 내 단계 칸이 숨 쉰다(재고가 비면 주홍)
    const me = chain.querySelector<HTMLElement>(".node.me");
    if (me) { const st = g.stages[role]; me.classList.toggle("short", st.backlog > 0); }
  };

  // ② 빠른 주문 — 들어온 만큼 · 거기서 ±2 · ±4(입력 칸에 채우고 바로 낸다)
  const quick = $("quick"), inp = $("order") as HTMLInputElement, form = $("f") as HTMLFormElement;
  const fillQuick = (g: any) => {
    const st = g.stages[role], inc = st.hist.incoming.length ? st.hist.incoming[st.hist.incoming.length - 1] : R.initial.pipeline;
    const vals = [...new Set([inc - 4, inc - 2, inc, inc + 2, inc + 4].map((v) => Math.max(0, v)))];
    quick.innerHTML = `<span class="s-cap">빠른 주문</span>` + vals.map((v) => `<button type="button" class="s-btn s-btn--ghost${v === inc ? " is-inc" : ""}" data-v="${v}">${v}${v === inc ? " · 들어온 만큼" : ""}</button>`).join("");
  };
  quick.addEventListener("click", (e) => { const b = (e.target as HTMLElement).closest("button"); if (!b) return; inp.value = b.dataset.v!; form.requestSubmit(); });
  document.addEventListener("beer:start", (e: any) => fillQuick(e.detail.g));
  document.addEventListener("beer:step", (e: any) => { if (e.detail.g.week < R.weeks) fillQuick(e.detail.g); });

  // ③ 내 점수 · ④ 공유 카드
  document.addEventListener("beer:done", (e: any) => {
    const { g, opt } = e.detail, B = (window as any).BeerGame;
    const s = B.summary(g), me = s.stages[opt.role];
    // 같은 자리를 논문 습관(고정·조정 식)이 맡았다면 — 같은 수요·같은 씨앗으로 네 단계 모두 자동
    const auto = B.summary(B.replay(R, { role: -1, demand: opt.demand, seed: opt.seed })).stages[opt.role];
    // 오는 중인 물건을 다 셌다면(β = 1)
    const full = B.summary(B.replay({ ...R, autoPolicy: { ...R.autoPolicy, beta: 1 } }, { role: -1, demand: opt.demand, seed: opt.seed })).stages[opt.role];
    const better = me.cost <= auto.cost;
    const ratio = auto.cost ? me.cost / auto.cost : 1;
    const grade = ratio <= 0.6 ? "공급망 관리자" : ratio <= 1 ? "논문 참가자보다 침착" : ratio <= 1.6 ? "채찍에 맞았다" : "채찍을 휘둘렀다";
    $("score").innerHTML =
      `<p class="s-cap">${me.label} 단계를 맡은 내 점수 — 비용(낮을수록 좋다)</p>` +
      `<p class="score__big"><b>${fmt(me.cost)}</b><span>달러</span> <em class="${better ? "" : "s-signal"}">${grade}</em></p>` +
      `<dl class="score__cmp"><div><dt>같은 자리를 논문 참가자 습관이 맡았다면</dt><dd>${fmt(auto.cost)}달러</dd></div>` +
      `<div><dt>오는 중인 물건을 다 셌다면</dt><dd>${fmt(full.cost)}달러</dd></div>` +
      `<div><dt>내 주문의 출렁임(소비자 수요 대비)</dt><dd>${me.amplification == null ? "—" : me.amplification.toFixed(1) + "배"}</dd></div></dl>`;
    const card = drawCard(R, g, opt, { me, auto, grade });
    const img = $("card-img") as HTMLImageElement;
    img.src = card.toDataURL("image/png"); img.hidden = false;
    ($("card-save") as HTMLAnchorElement).href = img.src;
    $("result").dataset.score = String(me.cost);
  });
  $("card-share").addEventListener("click", async () => {
    const img = $("card-img") as HTMLImageElement;
    try {
      const blob = await (await fetch(img.src)).blob();
      const file = new File([blob], "beer-game.png", { type: "image/png" });
      const nav: any = navigator;
      if (nav.canShare && nav.canShare({ files: [file] })) await nav.share({ files: [file], title: "맥주 게임 결과", url: location.href });
      else { await navigator.clipboard.writeText(location.href); $("card-say").textContent = "이 기기는 그림 공유를 못 해서 결과 주소를 복사했습니다."; }
    } catch { /* 사람이 취소 */ }
  });
}

// 공유 카드 1200×630 — 해도 색 · 내 단계 · 점수 · 주문 선(소비자 수요 점선 · 내 주문 주홍) · 사이트 이름. 외부 그림·글꼴 받기 0.
function drawCard(R: Rules, g: any, opt: any, r: { me: any; auto: any; grade: string }) {
  const c = $("card") as HTMLCanvasElement, x = c.getContext("2d")!, W = 1200, H = 630;
  const F = getComputedStyle(document.body).fontFamily || "system-ui, sans-serif";
  x.fillStyle = "#f5f2eb"; x.fillRect(0, 0, W, H);
  x.fillStyle = "#b3361e"; x.fillRect(0, 0, W, 8);
  x.fillStyle = "#6b655b"; x.font = `500 26px ${F}`; x.fillText(`맥주 게임 · ${R.weeks}주 · 나는 ${r.me.label}`, 64, 84);
  x.fillStyle = "#191714"; x.font = `700 120px ${F}`; x.fillText(fmt(r.me.cost), 60, 220);
  const w = x.measureText(fmt(r.me.cost)).width;
  x.font = `500 34px ${F}`; x.fillStyle = "#6b655b"; x.fillText("달러 비용", 76 + w, 218);
  x.font = `700 40px ${F}`; x.fillStyle = r.me.cost <= r.auto.cost ? "#191714" : "#b3361e"; x.fillText(r.grade, 64, 290);
  x.font = `500 26px ${F}`; x.fillStyle = "#3a3733";
  x.fillText(`같은 자리 논문 참가자 습관 ${fmt(r.auto.cost)}달러 · 내 주문 출렁임 ${r.me.amplification == null ? "—" : r.me.amplification.toFixed(1) + "배"}`, 64, 340);
  // 주문 선
  const st = g.stages[opt.role], dem = g.demand.slice(0, g.week), mine = st.hist.order, inc = st.hist.incoming;
  const X0 = 64, X1 = W - 64, Y0 = 400, Y1 = 560, max = Math.max(1, ...dem, ...mine, ...inc);
  const px = (i: number) => X0 + (i * (X1 - X0)) / Math.max(1, g.week - 1), py = (v: number) => Y1 - ((Y1 - Y0) * v) / max;
  const line = (v: number[], col: string, wd: number, dash: number[] = []) => { x.beginPath(); x.setLineDash(dash); v.forEach((a, i) => (i ? x.lineTo(px(i), py(a)) : x.moveTo(px(i), py(a)))); x.strokeStyle = col; x.lineWidth = wd; x.stroke(); x.setLineDash([]); };
  x.strokeStyle = "#d8d0bf"; x.lineWidth = 1; x.beginPath(); x.moveTo(X0, Y1); x.lineTo(X1, Y1); x.stroke();
  line(dem, "#6b655b", 2, [8, 6]); line(inc, "#5d7a86", 2); line(mine, "#b3361e", 4);
  x.font = `500 20px ${F}`; x.fillStyle = "#6b655b"; x.fillText("점선 소비자 수요 · 파랑 들어온 주문 · 주홍 내 주문", X0, 596);
  x.textAlign = "right"; x.fillStyle = "#191714"; x.font = `700 22px ${F}`; x.fillText("측심 SCM 작업실", X1, 596); x.textAlign = "left";
  return c;
}

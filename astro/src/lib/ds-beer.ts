// 시안 ② 맥주 게임 첫 장면 — 만지자마자 움직이는 그림(ncase 원리: 설명보다 손이 먼저).
// 네 단계가 모두 같은 주문 습관(Sterman 1989 고정·조정 식)으로 36주를 돌 때, 「오는 중인 물건을 셈에 넣는 정도」(β) 하나만 손으로 바꾼다.
// 계산 = assets/js/beer-game.js(엔진 그대로) · 규칙 = 지면에 박힌 data/sim/beer-game.json. β 기본값도 그 파일에서 온다.
type Rules = any;
const $ = (id: string) => document.getElementById(id)!;
const NS = "http://www.w3.org/2000/svg";

export function initDsBeer() {
  const R: Rules = JSON.parse($("beer-rules").textContent || "{}");
  const go = () => ((window as any).BeerGame ? run(R, (window as any).BeerGame) : setTimeout(go, 30));
  go();
}

function run(R: Rules, B: any) {
  const slider = $("beta") as HTMLInputElement;
  const sim = (beta: number) => B.replay({ ...R, autoPolicy: { ...R.autoPolicy, beta } }, {});
  // 세로 눈금은 고정한다 — 막대를 움직일 때 선이 커지고 작아지는 것이 보이게(눈금이 따라 움직이면 흔들림이 지워진다)
  let ymax = 1;
  for (let b = 0; b <= 1.0001; b += 0.05) {
    const g = sim(b);
    ymax = Math.max(ymax, ...g.demand, ...g.stages.flatMap((s: any) => s.hist.order));
  }
  const draw = () => {
    const beta = Number(slider.value);
    const g = sim(beta), s = B.summary(g);
    $("beta-out").textContent = `${Math.round(beta * 100)}%`;
    const f = s.stages[s.stages.length - 1];
    $("amp").textContent = f.amplification == null ? "—" : `${Math.round(f.amplification)}배`;
    $("amp-who").textContent = f.label;
    render($("wave"), R, g, ymax);
  };
  slider.addEventListener("input", draw);
  // CSV — 지금 화면에 그린 계열을 그 자리에서 파일로(서버 0 · 외부 요청 0)
  document.querySelector("[data-csv-client]")?.addEventListener("click", (e) => {
    const a = e.currentTarget as HTMLAnchorElement, beta = Number(slider.value), g = sim(beta);
    const head = ["주", "소비자_수요", ...R.stages.map((s: any) => `${s.label}_주문`), "오는중_반영"];
    const rows = g.demand.slice(0, g.week).map((d: number, i: number) => [i + 1, d, ...g.stages.map((st: any) => st.hist.order[i]), beta].join(","));
    const body = `# 측심 · 맥주 게임 모의 실험(실측 아님) · 규칙 Sterman(1989) · data/sim/beer-game.json\n${head.join(",")}\n${rows.join("\n")}\n`;
    a.href = URL.createObjectURL(new Blob(["\uFEFF" + body], { type: "text/csv;charset=utf-8" }));
  });
  // 그림은 칸의 실제 픽셀 폭으로 그린다(비율 고정 SVG 는 좁은 화면에서 납작해지고 넓은 화면에서 가운데로 몰린다)
  new ResizeObserver(() => draw()).observe($("wave"));
  draw();
  $("wave").dataset.ready = "1";
}

// 선 다섯 — 수요(점선 · 먹 3) · 소매·도매·유통(바다 농도) · 공장(신호 한 색). 범례 상자 없이 끝점에 직접 이름.
function render(host: HTMLElement, R: Rules, g: any, ymax: number) {
  const W = Math.max(280, Math.round(host.clientWidth || 1000)), H = W < 600 ? 180 : 300, L = 2, Rt = W < 600 ? 52 : 72, T = 12, Bt = 28, n = g.week;
  const fs = W < 600 ? 12 : 15;
  const x = (i: number) => L + (i * (W - L - Rt)) / Math.max(1, n - 1);
  const y = (v: number) => H - Bt - (v * (H - T - Bt)) / ymax;
  const series = [{ label: "소비자", v: g.demand.slice(0, n), c: "var(--s-ink-3)", w: 1.5, dash: "5 4" }].concat(
    g.stages.map((st: any, i: number) => {
      const last = i === g.stages.length - 1;
      return { label: R.stages[i].label, v: st.hist.order, c: last ? "var(--s-signal)" : ["var(--s-ink-2)", "var(--s-sea)", "var(--s-sea-2)"][i] || "var(--s-sea)", w: last ? 2.5 : 1.5, dash: "" };
    }),
  );
  let svg = host.querySelector("svg") as SVGSVGElement | null;
  if (!svg) {
    svg = document.createElementNS(NS, "svg") as SVGSVGElement;
    svg.setAttribute("role", "img");
    // 그림 설명은 그림(svg)에 — 감싼 div 의 aria-label 은 역할 없는 요소라 금지 속성이다(접근성 검사)
    svg.setAttribute("aria-label", host.getAttribute("aria-label") || host.dataset.label || "주별 주문 그림");
    if (host.hasAttribute("aria-label")) { host.dataset.label = host.getAttribute("aria-label")!; host.removeAttribute("aria-label"); }
    host.append(svg);
  }
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("width", String(W));
  svg.setAttribute("height", String(H));
  // 끝 이름은 겹치지 않게 민다(글자 높이 + 3)
  const ends = series.map((s, k) => ({ k, y: y(s.v[s.v.length - 1] ?? 0) })).sort((a, b) => a.y - b.y);
  for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < fs + 3) ends[i].y = ends[i - 1].y + fs + 3;
  // 아래로 밀다가 바닥을 넘으면 거꾸로 위로 민다(선이 끝에서 한데 모일 때 「공장」이 잘렸다)
  const floor = H - Bt - 4;
  for (let i = ends.length - 1; i >= 0; i--) {
    const cap = i === ends.length - 1 ? floor : ends[i + 1].y - (fs + 3);
    if (ends[i].y > cap) ends[i].y = cap;
  }
  const endY = Object.fromEntries(ends.map((e) => [e.k, e.y]));
  svg.innerHTML =
    `<line x1="${L}" y1="${H - Bt}" x2="${W - Rt}" y2="${H - Bt}" stroke="var(--s-rule)"/>` +
    `<text x="${L}" y="${H - 8}" font-size="13" fill="var(--s-ink-3)">1주</text>` +
    `<text x="${W - Rt}" y="${H - 8}" font-size="13" text-anchor="end" fill="var(--s-ink-3)">${n}주</text>` +
    series
      .map(
        (s, k) =>
          `<polyline fill="none" stroke="${s.c}" stroke-width="${s.w}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""} stroke-linejoin="round" vector-effect="non-scaling-stroke" points="${s.v.map((v: number, i: number) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>` +
          `<text x="${W - Rt + 8}" y="${(endY[k] + 5).toFixed(1)}" font-size="${fs}" font-weight="${k === series.length - 1 ? 700 : 500}" fill="${textColor(s.c)}">${s.label}</text>`,
      )
      .join("");
}

/** 선 색 → 글자 색(종이 대비 4.5:1 이상 · 채팅 검수 ②) */
export const textColor = (c: string) => c === "var(--s-sea-2)" ? "var(--s-sea-2-t)" : c === "var(--s-sea)" ? "var(--s-sea-t)" : c;

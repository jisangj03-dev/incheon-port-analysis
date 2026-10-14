// 맥주 게임 화면 — 계산은 assets/js/beer-game.js(window.BeerGame) · 규칙은 지면에 박힌 JSON(#beer-rules = data/sim/beer-game.json).
// 서버 0 · 저장 0 · 쿠키 0. 공유는 주소 값(?r=&d=&s=&o=)으로만 — 주소로 열면 같은 판을 그대로 되살린다(G2·G4).
type Rules = any;
const $ = (id: string) => document.getElementById(id)!;

export function initBeer() {
  const R: Rules = JSON.parse($("beer-rules").textContent || "{}");
  const ready = () => (window as any).BeerGame;
  const go = () => (ready() ? run(R, ready()) : setTimeout(go, 30));
  go();
}

function run(R: Rules, B: any) {
  let opt: any = null, g: any = null;
  const mine: number[] = [];

  const fromUrl = B.decode(location.search, R);
  if (location.search.includes("o=")) {
    ($("role") as HTMLSelectElement).value = String(fromUrl.role);
    ($("demand") as HTMLSelectElement).value = fromUrl.demand;
    ($("seed") as HTMLInputElement).value = String(fromUrl.seed);
  }

  const start = (preset?: any) => {
    opt = preset || {
      role: Number(($("role") as HTMLSelectElement).value),
      demand: ($("demand") as HTMLSelectElement).value,
      seed: Math.max(1, parseInt(($("seed") as HTMLInputElement).value, 10) || 1),
    };
    mine.length = 0;
    g = B.create(R, opt);
    ($("result") as HTMLElement).hidden = true;
    ($("play") as HTMLElement).hidden = false;
    $("who").textContent = `${R.stages[opt.role].label} 단계`;
    draw();
    ($("order") as HTMLInputElement).focus();
  };

  const draw = () => {
    const st = g.stages[opt.role], last = st.hist.incoming.length - 1;
    $("wk").textContent = `${g.week + 1}주 / ${R.weeks}주`;
    $("inv").textContent = String(st.inventory);
    $("bk").textContent = String(st.backlog);
    $("inc").textContent = last >= 0 ? String(st.hist.incoming[last]) : "—";
    $("oo").textContent = String(st.onOrder);
    // 지면에 #live 가 있으면(해도 시안) 한 주 낼 때마다 내 단계의 두 선을 그린다 — 들어온 주문 · 내 주문
    const live = document.getElementById("live");
    if (live) live.innerHTML = liveChart(st.hist.incoming, st.hist.order, R.weeks);
  };

  const finish = () => {
    const s = B.summary(g);
    ($("play") as HTMLElement).hidden = true;
    ($("result") as HTMLElement).hidden = false;
    $("rows").innerHTML = s.stages
      .map((r: any, i: number) => `<tr${i === opt.role ? ' class="me"' : ""}><th scope="row">${r.label}${i === opt.role ? " (나)" : ""}</th><td class="num">${r.amplification == null ? "—" : r.amplification.toFixed(1) + "배"}</td><td class="num">${fmt(r.cost)}</td><td class="num">${r.maxBacklog}</td></tr>`)
      .join("");
    const top = s.stages[s.stages.length - 1], me = s.stages[opt.role];
    $("verdict").textContent = `총비용 ${fmt(s.totalCost)} — ${me.label}(나)의 주문은 소비자 수요보다 ${me.amplification == null ? "—" : me.amplification.toFixed(1) + "배"}, ${top.label}은 ${top.amplification == null ? "—" : top.amplification.toFixed(1) + "배"} 출렁였습니다.`;
    $("chart").innerHTML = chart(R, g);
    history.replaceState(null, "", "?" + B.encode({ ...opt, orders: mine }));
  };

  $("start").addEventListener("click", () => start());
  $("again").addEventListener("click", () => { ($("result") as HTMLElement).hidden = true; history.replaceState(null, "", location.pathname); start(); });
  $("copy").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(location.href); $("verdict").textContent += " (주소를 복사했습니다)"; } catch { /* 복사 막힘 — 주소창 그대로 */ }
  });
  $("f").addEventListener("submit", (e) => {
    e.preventDefault();
    const inp = $("order") as HTMLInputElement, v = Math.floor(Number(inp.value));
    if (!Number.isFinite(v) || v < 0) { $("say").textContent = "0 이상의 정수를 넣어 주세요."; return; }
    mine.push(v); B.step(g, v); inp.value = "";
    $("say").textContent = `${g.week}주차 주문 ${v}상자를 냈습니다.`;
    if (g.week >= R.weeks) finish(); else draw();
  });

  // 주소에 끝난 판이 담겨 있으면 그대로 되살려 결과를 보인다
  if (location.search.includes("o=") && fromUrl.orders.length >= R.weeks) {
    opt = { role: fromUrl.role, demand: fromUrl.demand, seed: fromUrl.seed };
    g = B.replay(R, { ...opt, orders: fromUrl.orders });
    mine.push(...fromUrl.orders);
    finish();
  }
}

const fmt = (n: number) => n.toLocaleString("ko-KR", { maximumFractionDigits: 1 });

// 주별 주문 선 — 소비자 수요 + 네 단계(인라인 SVG · 외부 요청 0 · 시각 마감은 디자인 기준 뒤)
function chart(R: Rules, g: any) {
  const W = 640, H = 240, P = 28, n = g.week;
  const series = [{ label: "소비자 수요", v: g.demand.slice(0, n) }].concat(g.stages.map((s: any, i: number) => ({ label: R.stages[i].label, v: s.hist.order })));
  const max = Math.max(1, ...series.flatMap((s: any) => s.v));
  const x = (i: number) => P + (i * (W - 2 * P)) / Math.max(1, n - 1), y = (v: number) => H - P - (v * (H - 2 * P)) / max;
  const tones = ["var(--mist)", "var(--sonar)", "var(--pass)", "var(--sodium)", "var(--fail)"];
  const lines = series.map((s: any, k: number) => `<polyline fill="none" stroke="${tones[k]}" stroke-width="${k ? 2 : 1.5}" ${k ? "" : 'stroke-dasharray="4 3"'} points="${s.v.map((v: number, i: number) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"><title>${s.label}</title></polyline>`).join("");
  const legend = series.map((s: any, k: number) => `<tspan fill="${tones[k]}" dx="${k ? 12 : 0}">■ ${s.label}</tspan>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg"><line x1="${P}" y1="${H - P}" x2="${W - P}" y2="${H - P}" stroke="var(--hair-strong)"/>${lines}<text x="${P}" y="16" font-size="12" fill="var(--text)">${legend}</text><text x="${W - P}" y="${H - 8}" font-size="11" text-anchor="end" fill="var(--mist)">${n}주</text><text x="${P - 4}" y="${y(max) + 4}" font-size="11" text-anchor="end" fill="var(--mist)">${max}</text></svg>`;
}

// 놀이 중 그림 — 내 단계만(정보는 원 규칙대로 가린다). 가로는 판 전체 주 수로 고정해 선이 오른쪽으로 자라게 한다.
function liveChart(inc: number[], mine: number[], weeks: number) {
  const W = 1000, H = 160, P = 8, Rt = 92;
  const max = Math.max(1, ...inc, ...mine);
  const x = (i: number) => P + (i * (W - P - Rt)) / Math.max(1, weeks - 1), y = (v: number) => H - P - (v * (H - 2 * P)) / max;
  const line = (v: number[], c: string, w: number, dash = "") => v.length ? `<polyline fill="none" stroke="${c}" stroke-width="${w}" ${dash ? `stroke-dasharray="${dash}"` : ""} vector-effect="non-scaling-stroke" points="${v.map((a, i) => `${x(i).toFixed(1)},${y(a).toFixed(1)}`).join(" ")}"/><text x="${(x(v.length - 1) + 8).toFixed(1)}" y="${(y(v[v.length - 1]) + 5).toFixed(1)}" font-size="14" fill="${c}">${c.includes("signal") ? "내 주문" : "들어온 주문"}</text>` : "";
  return `<svg viewBox="0 0 ${W} ${H}" role="img"><line x1="${P}" y1="${H - P}" x2="${W - Rt}" y2="${H - P}" stroke="var(--s-rule, #ccc)"/>${line(inc, "var(--s-ink-3, #888)", 1.5, "5 4")}${line(mine, "var(--s-signal, #b3361e)", 2.5)}</svg>`;
}

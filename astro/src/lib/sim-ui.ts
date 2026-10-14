// 몬테카를로 화면 — 상태는 계산기와 같은 주소 꼴(?s=)로 받는다. 계산은 window.CostCheck·CostSim 만 한다.
declare global { interface Window { CostSim: any; __sim?: any } }
const $ = (id: string) => document.getElementById(id)!;
const won = (n: number | null) => (n === null ? "—" : `${Math.round(n).toLocaleString("ko-KR")}원`);
const pct = (p: number | null) => (p === null ? "—" : `${Math.round(p * 100)}%`);

export function initSim(retry = true) {
  const C = (window as any).CostCheck, S = window.CostSim;
  if (!C || !S) { if (retry) addEventListener("load", () => initSim(false), { once: true }); return; }
  let state: any = null;
  let hidden: any = null;
  const qs = new URLSearchParams(location.search).get("s");
  if (qs) { const d = C.decode(qs); if (d) { state = d.state; hidden = d.hidden; } }
  const useSample = () => {
    const s = C.SAMPLE;
    state = { ship: String(s.ship), ret: String(s.ret), blocks: s.blocks.map((rows: any[]) => rows.map((r) => [r[0], r[1] === null ? "" : String(r[1]), r[2] === null ? "" : String(r[2])])) };
    hidden = [{}, {}, {}];
    $("src-note").textContent = "가상 예시(실제 업체 견적 아님)로 돌립니다 — 출고 1,000건·반품 30건.";
  };
  if (!state) useSample(); else $("src-note").textContent = "계산기에서 넣은 값으로 돌립니다(주소에 담긴 입력값).";
  C.BLOCKS.forEach((n: string, b: number) => { const el = document.querySelector(`[data-name="${b}"]`); if (el) el.textContent = n; });
  const back = $("back") as HTMLAnchorElement;
  if (qs) back.href += `?s=${qs}`;

  let plot: any = null;
  async function run() {
    const caps = [0, 1, 2].map((b) => ($(`cap-${b}`) as HTMLInputElement).value.replace(/[^0-9.]/g, "") || null);
    const res = S.simulate(C, state, { runs: 4000, seed: 20261012, volSwing: Number(($("swing") as HTMLSelectElement).value), unknownMax: caps });
    window.__sim = res.map((r: any) => ({ name: r.name, pBest: r.pBest, p50: r.p50 }));
    const live = res.filter((r: any) => r.live);
    if (!live.length) { $("verdict").textContent = "계산할 견적이 없습니다 — 계산기에서 출고 건수와 견적을 넣어 주세요."; return; }
    const top = live.slice().sort((a: any, b: any) => b.pBest - a.pBest)[0];
    $("verdict").textContent = top.pBest >= 0.8
      ? `${top.name}가 ${pct(top.pBest)}의 경우에 가장 쌉니다 — 흔들어도 답이 거의 안 바뀝니다.`
      : `가장 쌀 확률이 갈립니다(${live.map((r: any) => `${r.name} ${pct(r.pBest)}`).join(" · ")}) — '모름' 칸을 먼저 물어보세요.`;
    $("rows").innerHTML = res.map((r: any) => r.live
      ? `<tr><th scope="row">${r.name}${r.unknown ? ` <small>(모름 ${r.unknown}칸 · 상한 ${won(r.cap)})</small>` : ""}</th><td class="num">${pct(r.pBest)}</td><td class="num">${won(r.p10)}</td><td class="num">${won(r.p50)}</td><td class="num">${won(r.p90)}</td></tr>`
      : `<tr><th scope="row">${r.name}</th><td class="num" colspan="4">비어 있음</td></tr>`).join("");
    try { plot = plot || (await import("@observablehq/plot")); } catch { return; }
    const pts = live.flatMap((r: any) => r.draws.map((v: number) => ({ name: r.name, v })));
    const box = $("hist");
    const svg = plot.plot({
      width: Math.max(300, Math.min(760, box.clientWidth || 600)), height: 240, marginLeft: 48,
      style: { fontFamily: "inherit", fontSize: "11px", background: "transparent" },
      x: { label: "건당 비용(원) →", tickFormat: (d: number) => d.toLocaleString("ko-KR") }, y: { label: "↑ 횟수", grid: true },
      color: { domain: C.BLOCKS, range: ["#4a6274", "#0a7286", "#c26a00"], legend: true },
      marks: [plot.rectY(pts, plot.binX({ y: "count" }, { x: "v", fill: "name", mixBlendMode: "multiply", fillOpacity: 0.55, thresholds: 40 })), plot.ruleY([0])],
    });
    box.innerHTML = ""; box.append(svg);
  }
  $("run").addEventListener("click", run);
  $("sample").addEventListener("click", () => { useSample(); run(); });
  run();
}

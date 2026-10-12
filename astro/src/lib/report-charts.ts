// 보고서 ② 층 위젯 동작 — 범위·보기를 고르면 문장(aria-live)과 차트를 다시 그린다. Plot 은 처음 그릴 때 늦게 불러온다.
type Cfg = { kind: "direction" | "size" | "terminal" | "item"; view?: string; data: any };
const fmt = (n: number, d = 0) => n.toLocaleString("ko-KR", { maximumFractionDigits: d, minimumFractionDigits: d });
const C = { exp: "#3fd3e6", imp: "#ffb547", grid: "rgba(170,210,235,.18)", ink: "#d5e2ec" };
const PAL = ["#3fd3e6", "#ffb547", "#8fa8ff", "#c792ea", "#38d39f", "#ff7a7a"];
let plotMod: any = null;

export function initReportCharts() {
  document.querySelectorAll<HTMLElement>(".rc[data-kind]").forEach((box) => {
    if (box.dataset.ready) return;
    box.dataset.ready = "1";
    const cfg: Cfg = JSON.parse(box.querySelector(".rc__data")!.textContent || "{}");
    const st: Record<string, string> = { view: cfg.view || (cfg.kind === "terminal" ? "v" : cfg.kind === "item" ? "exp" : "teu") };
    const sel = (k: string) => box.querySelector<HTMLSelectElement>(`select[data-k="${k}"]`);
    const draw = () => render(box, cfg, st, sel);
    box.querySelectorAll<HTMLButtonElement>("button[data-view]").forEach((b) =>
      b.addEventListener("click", () => {
        st.view = b.dataset.view!;
        box.querySelectorAll("button[data-view]").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        draw();
      }),
    );
    box.querySelectorAll("select, input[type=checkbox]").forEach((el) => el.addEventListener("change", draw));
    // 화면에 들어올 때 처음 그린다(첫 화면 JS 를 가볍게).
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); draw(); } }, { rootMargin: "200px" });
    io.observe(box);
  });
}

async function render(box: HTMLElement, cfg: Cfg, st: Record<string, string>, sel: (k: string) => HTMLSelectElement | null) {
  const say = box.querySelector<HTMLElement>(".rc__say")!;
  const out = box.querySelector<HTMLElement>(".rc__plot")!;
  let from = sel("from")?.value || "0000", to = sel("to")?.value || "9999";
  if (from > to) [from, to] = [to, from];
  const inRange = (ym: string) => ym.slice(0, 4) >= from && ym.slice(0, 4) <= to;
  try { plotMod = plotMod || (await import("@observablehq/plot")); } catch { say.textContent = "차트를 불러오지 못했다 — CSV 로 같은 값을 볼 수 있다."; return; }
  const Plot = plotMod;
  const width = Math.max(300, Math.min(940, out.clientWidth || 640));
  const base = { width, height: 300, marginLeft: 60, style: { background: "transparent", color: C.ink, fontFamily: "inherit", fontSize: "12px" } };
  const date = (ym: string) => new Date(`${ym}-01T00:00:00`);
  let chart: any;

  if (cfg.kind === "direction") {
    const s = cfg.data.series.filter((r: any) => inRange(r.ym));
    const imp = s.reduce((a: number, r: any) => a + r.imp, 0), exp = s.reduce((a: number, r: any) => a + r.exp, 0);
    if (st.view === "ratio") {
      const pts = s.filter((r: any) => r.imp > 0).map((r: any) => ({ d: date(r.ym), ym: r.ym, ratio: r.exp / r.imp }));
      say.textContent = `${from}~${to} 공컨 수출 방향 ÷ 수입 방향: 합계 기준 ${fmt(exp / imp, 2)}배 · 월별 ${fmt(Math.min(...pts.map((p: any) => p.ratio)), 1)}~${fmt(Math.max(...pts.map((p: any) => p.ratio)), 1)}배(수입 0 인 달 ${s.length - pts.length}개는 뺐다)`;
      chart = Plot.plot({ ...base, y: { type: "log", label: "↑ 배율(로그)", grid: true }, x: { label: null },
        marks: [Plot.ruleY([1], { stroke: C.grid }), Plot.lineY(pts, { x: "d", y: "ratio", stroke: C.exp, strokeWidth: 2 }), Plot.dot(pts, Plot.pointerX({ x: "d", y: "ratio", fill: C.exp, r: 4 })), Plot.tip(pts, Plot.pointerX({ x: "d", y: "ratio", title: (p: any) => `${p.ym} · ${fmt(p.ratio, 2)}배` }))] });
    } else {
      const pts = s.flatMap((r: any) => [{ d: date(r.ym), ym: r.ym, k: "수출 방향", v: r.exp }, { d: date(r.ym), ym: r.ym, k: "수입 방향", v: r.imp }]);
      say.textContent = `${from}~${to} 공컨(외항): 수출 방향 ${fmt(exp)} TEU · 수입 방향 ${fmt(imp)} TEU · ${s.length}개월`;
      chart = Plot.plot({ ...base, y: { label: "↑ TEU", grid: true, tickFormat: (d: number) => fmt(d) }, x: { label: null }, color: { domain: ["수출 방향", "수입 방향"], range: [C.exp, C.imp], legend: true },
        marks: [Plot.lineY(pts, { x: "d", y: "v", stroke: "k", strokeWidth: 2 }), Plot.tip(pts, Plot.pointerX({ x: "d", y: "v", stroke: "k", title: (p: any) => `${p.ym} ${p.k} · ${fmt(p.v)} TEU` }))] });
    }
  } else if (cfg.kind === "size") {
    const s = cfg.data.series.filter((r: any) => inRange(r.ym) && r.impShare !== null);
    const pos = s.filter((r: any) => r.gap > 0).length;
    const pts = s.flatMap((r: any) => [{ d: date(r.ym), ym: r.ym, k: "수입 공컨", v: r.impShare }, { d: date(r.ym), ym: r.ym, k: "수출 공컨", v: r.expShare }]);
    say.textContent = `${from}~${to} 40ft 비중(박스 수): 수입이 수출보다 높은 달 ${pos}/${s.length}개월`;
    chart = Plot.plot({ ...base, y: { label: "↑ 40ft 비중(%)", domain: [0, 100], grid: true }, x: { label: null }, color: { domain: ["수입 공컨", "수출 공컨"], range: [C.imp, C.exp], legend: true },
      marks: [Plot.lineY(pts, { x: "d", y: "v", stroke: "k", strokeWidth: 2 }), Plot.tip(pts, Plot.pointerX({ x: "d", y: "v", stroke: "k", title: (p: any) => `${p.ym} ${p.k} · ${fmt(p.v, 1)}%` }))] });
  } else if (cfg.kind === "terminal") {
    const on = new Set([...box.querySelectorAll<HTMLInputElement>("input[data-term]")].filter((c) => c.checked).map((c) => c.dataset.term));
    const key = st.view === "yoy" ? "yoy" : "v";
    const s = cfg.data.series.filter((r: any) => inRange(r.ym) && on.has(r.name) && r[key] !== null);
    const last = s.length ? s.reduce((a: string, r: any) => (r.ym > a ? r.ym : a), "") : "";
    const lastRows = s.filter((r: any) => r.ym === last);
    say.textContent = s.length
      ? `${from}~${to} · 터미널 ${on.size}곳 · 마지막 달 ${last}: ${lastRows.map((r: any) => `${r.name} ${key === "v" ? `${fmt(r.v)}천TEU` : `${r.yoy > 0 ? "+" : ""}${fmt(r.yoy, 1)}%`}`).join(" · ")}`
      : "고른 터미널이 없다.";
    const names = cfg.data.names as string[];
    chart = Plot.plot({ ...base, y: { label: key === "v" ? "↑ 천TEU" : "↑ 전년 같은 달 대비 %", grid: true }, x: { label: null },
      color: { domain: names, range: names.map((_, i) => PAL[i % PAL.length]), legend: true },
      marks: [key === "yoy" ? Plot.ruleY([0], { stroke: C.grid }) : null, Plot.lineY(s, { x: (r: any) => date(r.ym), y: key, stroke: "name", strokeWidth: 2 }),
        Plot.tip(s, Plot.pointerX({ x: (r: any) => date(r.ym), y: key, stroke: "name", title: (r: any) => `${r.ym} ${r.name} · ${key === "v" ? `${fmt(r.v)}천TEU` : `${fmt(r.yoy, 1)}%`}` }))].filter(Boolean) });
  } else {
    const m = sel("month")!.value;
    const k = st.view === "imp" ? "imp" : "exp";
    const rows = cfg.data.series.filter((r: any) => r.ym === m).sort((a: any, b: any) => b[k] - a[k]);
    const total = rows.reduce((a: number, r: any) => a + r[k], 0);
    const top = rows.slice(0, 10).map((r: any) => ({ ...r, label: `${r.hs} ${r.name.length > 9 ? r.name.slice(0, 9) + "…" : r.name}`, share: total ? (r[k] / total) * 100 : 0 }));
    const top3 = top.slice(0, 3).reduce((a: number, r: any) => a + r.share, 0);
    say.textContent = `${m} 인천 ${k === "exp" ? "수출" : "수입"} 상위 10개 류 · 상위 3개 류가 ${fmt(top3, 1)}% (HS 2단위 · 천 달러)`;
    chart = Plot.plot({ ...base, height: 340, marginLeft: 180, marginRight: 24, x: { label: "천 달러 →", grid: true, ticks: 4, tickFormat: (d: number) => fmt(d) }, y: { label: null, domain: top.map((r: any) => r.label) },
      marks: [Plot.barX(top, { x: k, y: "label", fill: k === "exp" ? C.exp : C.imp }), Plot.tip(top, Plot.pointerY({ x: k, y: "label", title: (r: any) => `${r.hs} ${r.name} · ${fmt(r[k])}천 달러 · ${fmt(r.share, 1)}%` }))] });
  }
  out.innerHTML = "";
  if (chart) out.append(chart);
  (window as any).__rc = ((window as any).__rc || 0) + 1;
}

// 계산기 v2 화면 동작. 계산은 window.CostCheck(assets/js/cost-check.js)만 한다 — 여기는 그리기와 주소 동기화뿐이다.
type Row = [string, string, string];
type State = { ship: string; ret: string; blocks: Row[][] };
type Hidden = Record<string, string>[];
declare global {
  interface Window { CostCheck: any; __calc?: { state: State; hidden: Hidden } }
}

const $ = (id: string) => document.getElementById(id)!;
const won = (n: number) => `${Math.round(n).toLocaleString("ko-KR")}원`;
const signed = (n: number) => {
  const r = Math.round(n);
  return `${r > 0 ? "+" : r < 0 ? "−" : ""}${Math.abs(r).toLocaleString("ko-KR")}원`;
};
const esc = (s: string) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);
const clean = (v: string) => v.replace(/[^0-9.]/g, "");

export function initCalc(retry = true) {
  const C = window.CostCheck;
  // 계산 파일(고전 스크립트)이 아직 안 돌았으면 load 뒤에 한 번 더 — 스크립트 순서에 기대지 않는다.
  if (!C) { if (retry) window.addEventListener("load", () => initCalc(false), { once: true }); return; }
  const NB = C.BLOCKS.length;
  const blank = (): State => ({ ship: "", ret: "", blocks: C.BLOCKS.map(() => C.ITEMS.map(() => ["", "", ""] as Row)) });
  let state: State = blank();
  let hidden: Hidden = C.BLOCKS.map(() => ({}));

  // 주소에 담긴 입력값이 있으면 그것으로 시작한다(공유 링크 · 기준 8).
  const qs = new URLSearchParams(location.search).get("s");
  if (qs) {
    const d = C.decode(qs);
    if (d) { state = d.state; hidden = d.hidden; }
  }
  window.__calc = { state, hidden };

  const inputs = () => Array.from(document.querySelectorAll<HTMLInputElement | HTMLSelectElement>("#cc input, #cc select"));

  function paint() {
    // 화면 칸 ← 상태(처음 · 예시 · 비우기 · 주소에서 불러오기)
    ($("ship") as HTMLInputElement).value = state.ship;
    ($("ret") as HTMLInputElement).value = state.ret;
    for (const el of inputs()) {
      const b = el.dataset.b, i = el.dataset.i, k = el.dataset.k, h = el.dataset.h;
      if (b === undefined) continue;
      if (h) { el.value = hidden[+b][h] || ""; continue; }
      if (el.hasAttribute("data-quick")) continue;
      if (i !== undefined && k !== undefined) el.value = state.blocks[+b][+i][+k] || "";
    }
    syncQuick();
  }

  function syncQuick() {
    for (const el of document.querySelectorAll<HTMLInputElement>("[data-quick]")) {
      const r = state.blocks[+el.dataset.b!][+el.dataset.i!];
      if (document.activeElement === el) continue;
      if (r[0] === "별도") {
        // 보관비·월 고정비처럼 수량을 곱하는 칸은 월 합계(단가×수량)로 보여 준다.
        const p = C.num(r[1]), q = C.num(r[2]);
        el.value = p === null ? "" : String(q !== null && +el.dataset.i! !== 0 && +el.dataset.i! !== 3 ? p * q : p);
        el.placeholder = C.BLOCKS[+el.dataset.b!];
      } else {
        el.value = "";
        el.placeholder = r[0] || C.BLOCKS[+el.dataset.b!];
      }
    }
  }

  let urlTimer = 0;
  function pushUrl() {
    clearTimeout(urlTimer);
    urlTimer = window.setTimeout(() => {
      const any = state.ship || state.blocks.some((rows) => rows.some((r) => r[0]));
      const url = new URL(location.href);
      if (any) url.searchParams.set("s", C.encode(state, hidden)); else url.searchParams.delete("s");
      history.replaceState(null, "", url);
      const sim = document.getElementById("simlink") as HTMLAnchorElement | null;
      if (sim) sim.href = sim.href.split("?")[0] + (any ? `?s=${url.searchParams.get("s")}` : "");
    }, 250);
  }

  function update() {
    const res = C.compute(state);
    const gaps = C.hiddenGaps(state, hidden);
    const filledPer = res.filter((r: any) => r.filled && r.perUnit !== null).map((r: any) => r.perUnit);
    const best = filledPer.length > 1 ? Math.min(...filledPer) : null;
    res.forEach((r: any, b: number) => {
      const card = $(`res-${b}`);
      const per = card.querySelector<HTMLElement>("[data-per]")!;
      const line = card.querySelector<HTMLElement>("[data-monthly-line]")!;
      const diff = card.querySelector<HTMLElement>("[data-diff]")!;
      const unk = card.querySelector<HTMLElement>("[data-unknown]")!;
      const gp = card.querySelector<HTMLElement>("[data-gaps]")!;
      const dock = document.querySelector<HTMLElement>(`[data-dock="${b}"]`)!;
      if (!r.filled) {
        per.textContent = "—"; line.textContent = "아직 비어 있음"; diff.hidden = true; unk.hidden = true; gp.hidden = true;
        dock.textContent = "—"; card.classList.remove("is-best"); return;
      }
      per.textContent = r.perUnit === null ? "출고 건수 필요" : won(r.perUnit);
      dock.textContent = r.perUnit === null ? "—" : won(r.perUnit);
      line.textContent = `건당 합계 · 월 ${won(r.monthly)}`;
      diff.hidden = r.diff === null;
      if (r.diff !== null) diff.textContent = `지금 방식보다 건당 ${signed(r.diff)}`;
      unk.hidden = !r.unknown.length;
      unk.textContent = r.unknown.length
        ? `⚠ 모름 칸 ${r.unknown.length}개 — ${r.unknown.map((i: number) => `${i + 1}번`).join("·")}이 견적서에 없음(숨은 비용 후보)`
        : "";
      gp.hidden = !gaps[b].length;
      gp.innerHTML = gaps[b].map(esc).join("<br>");
      card.classList.toggle("is-best", best !== null && r.perUnit === best);
    });
    $("flip").textContent = res.filter((r: any) => r.flip).map((r: any) =>
      `${r.name}의 모름 칸들을 합쳐 건당 ${won(r.flip.perUnit)}(월 ${won(r.flip.monthly)})을 넘으면 ${r.flip.against}보다 비싸집니다.`).join(" ");

    const q = C.questions(res, hidden).filter((x: any) => x.list.length);
    $("qs-box").hidden = !q.length;
    ($("copyq") as HTMLButtonElement).hidden = !q.length;
    $("qs").innerHTML = q.map((x: any) => `<p><strong>${esc(x.name)}</strong></p><ol>${x.list.map((s: string) => `<li>${esc(s)}</li>`).join("")}</ol>`).join("");

    breakeven();
    pushUrl();
  }

  // 손익분기 — 글은 바로, 그래프는 Plot 을 늦게 불러 그린다(첫 화면 JS 를 가볍게).
  let plotMod: any = null;
  async function breakeven() {
    const sp = C.split(state);
    const n0 = C.num(state.ship);
    const live = sp.filter((s: any) => s.filled);
    const txt = $("be-text");
    const box = $("be-chart");
    if (live.length < 2 || !n0) { txt.textContent = "견적 둘 이상과 월 출고 건수를 채우면 나옵니다."; box.innerHTML = ""; return; }
    const xs = C.crossings(sp);
    const order = live.map((s: any) => ({ name: s.name, v: C.perUnitAt(s, n0) })).sort((a: any, b: any) => a.v - b.v);
    let msg = `지금 물량(월 ${n0.toLocaleString("ko-KR")}건)에서는 ${order[0].name}가 가장 쌉니다.`;
    if (xs.length) msg += " " + xs.map((x: any) => `월 ${Math.ceil(x.n).toLocaleString("ko-KR")}건부터 ${x.cheaperAbove}가 ${x.cheaperAbove === x.a ? x.b : x.a}보다 쌉니다`).join(" · ") + ".";
    else msg += " 물량이 바뀌어도 순서가 그대로입니다(교차 없음).";
    txt.textContent = msg;
    try {
      plotMod = plotMod || (await import("@observablehq/plot"));
    } catch { return; }
    const Plot = plotMod;
    const lo = Math.max(1, Math.round(n0 / 5)), hi = Math.round(n0 * 3);
    const steps = 60, pts: any[] = [];
    for (const s of live) for (let k = 0; k <= steps; k++) {
      const n = lo + ((hi - lo) * k) / steps;
      pts.push({ name: s.name, n, v: C.perUnitAt(s, n) });
    }
    const cut = xs.filter((x: any) => x.n >= lo && x.n <= hi).map((x: any) => {
      const s = sp.find((t: any) => t.name === x.a);
      return { n: x.n, v: C.perUnitAt(s, x.n), label: `${Math.ceil(x.n).toLocaleString("ko-KR")}건` };
    });
    const vmax = Math.max(...pts.filter((p) => p.n >= n0 / 2).map((p) => p.v));
    const w = Math.max(260, Math.min(520, box.clientWidth || 360));
    const chart = Plot.plot({
      width: w, height: 220, marginLeft: 56, marginRight: 12, style: { fontFamily: "inherit", fontSize: "11px", background: "transparent" },
      x: { label: "월 출고 건수 →", tickFormat: (d: number) => d.toLocaleString("ko-KR") },
      y: { label: "↑ 건당(원)", domain: [0, vmax * 1.15], grid: true, tickFormat: (d: number) => d.toLocaleString("ko-KR") },
      color: { domain: C.BLOCKS, range: ["#4a6274", "#0a7286", "#c26a00"], legend: true },
      marks: [
        Plot.line(pts, { x: "n", y: "v", stroke: "name", strokeWidth: 2.5, clip: true }),
        Plot.ruleX([n0], { stroke: "#0b1a26", strokeDasharray: "3,3" }),
        Plot.text([{ n: n0 }], { x: "n", frameAnchor: "top", dy: 6, text: () => "지금", fill: "#0b1a26" }),
        Plot.dot(cut, { x: "n", y: "v", r: 5, fill: "#b3261e" }),
        Plot.text(cut, { x: "n", y: "v", text: "label", dy: -12, fill: "#b3261e", fontWeight: 700 }),
      ],
    });
    box.innerHTML = "";
    box.append(chart);
  }

  // 입력 → 상태
  document.getElementById("cc")!.addEventListener("input", onEdit);
  document.getElementById("cc")!.addEventListener("change", onEdit);
  function onEdit(e: Event) {
    const el = e.target as HTMLInputElement | HTMLSelectElement;
    if (el.id === "ship") { state.ship = clean(el.value); return update(); }
    if (el.id === "ret") { state.ret = clean(el.value); return update(); }
    const b = el.dataset.b, i = el.dataset.i;
    if (b === undefined) return;
    if (el.dataset.h) { hidden[+b][el.dataset.h] = el.value; return update(); }
    if (i === undefined) return;
    const row = state.blocks[+b][+i];
    if (el.hasAttribute("data-quick")) {
      const v = clean(el.value);
      // 빠른 칸: 값이 있으면 「별도」. 보관비·월 고정비는 월 합계를 단가로, 수량 1로 둔다.
      if (v) { row[0] = "별도"; row[1] = v; row[2] = +i === 0 || +i === 3 ? "" : "1"; }
      else if (row[0] === "별도") { row[0] = ""; row[1] = ""; row[2] = ""; }
      paintPrecise(+b, +i);
      return update();
    }
    row[+el.dataset.k!] = el.dataset.k === "0" ? el.value : clean(el.value);
    syncQuick();
    update();
  }
  function paintPrecise(b: number, i: number) {
    const r = state.blocks[b][i];
    (document.getElementById(`p-${b}-${i}-m`) as HTMLSelectElement).value = r[0];
    (document.getElementById(`p-${b}-${i}-p`) as HTMLInputElement).value = r[1];
    (document.getElementById(`p-${b}-${i}-q`) as HTMLInputElement).value = r[2];
  }

  // 정밀 입력 탭
  const tabs = Array.from({ length: NB }, (_, k) => document.getElementById(`pt-${k}`) as HTMLButtonElement);
  const setTab = (k: number) => tabs.forEach((t, j) => {
    t.setAttribute("aria-selected", String(j === k)); t.tabIndex = j === k ? 0 : -1;
    (document.getElementById(`pp-${j}`) as HTMLElement).hidden = j !== k;
  });
  tabs.forEach((t, k) => {
    t.addEventListener("click", () => setTab(k));
    t.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
      const n = (k + (e.key === "ArrowRight" ? 1 : NB - 1)) % NB; setTab(n); tabs[n].focus();
    });
  });

  $("sample").addEventListener("click", () => {
    const S = C.SAMPLE;
    state = { ship: String(S.ship), ret: String(S.ret), blocks: S.blocks.map((rows: any[]) => rows.map((r) => [r[0], r[1] === null ? "" : String(r[1]), r[2] === null ? "" : String(r[2])])) };
    hidden = [{}, { power: "모름", legal: "모름", oneoff: "모름", fuel: "모름" }, {}];
    window.__calc = { state, hidden };
    $("sample-note").hidden = false;
    paint(); update();
  });
  $("clear").addEventListener("click", () => {
    state = blank(); hidden = C.BLOCKS.map(() => ({}));
    window.__calc = { state, hidden };
    $("sample-note").hidden = true;
    paint(); update();
  });
  const say = (s: string) => ($("status").textContent = s);
  const copy = (text: string, ok: string) => {
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(() => say(ok), () => say("복사가 막혀 있습니다. 주소창의 주소를 직접 복사해 주세요."));
    else say("이 브라우저는 복사 단추를 지원하지 않습니다.");
  };
  $("share").addEventListener("click", () => {
    const url = new URL(location.href);
    url.searchParams.set("s", C.encode(state, hidden));
    copy(url.toString(), "공유 링크를 복사했습니다 — 입력값은 이 주소 안에만 있습니다.");
  });
  $("copyq").addEventListener("click", () => {
    const text = C.questions(C.compute(state), hidden).filter((q: any) => q.list.length)
      .map((q: any) => `[${q.name}]\n${q.list.map((s: string, i: number) => `${i + 1}. ${s}`).join("\n")}`).join("\n\n");
    copy(text, "복사했습니다. 업체에 보낼 메시지에 붙여 넣으세요.");
  });

  paint();
  update();
}

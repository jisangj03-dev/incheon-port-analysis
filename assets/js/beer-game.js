/* 맥주 게임 엔진(2026-10-14 · 정체성 전환 정본 §3-1). 규칙 상수는 data/sim/beer-game.json 하나에서만 받는다.
 *
 * 한 주의 순서(네 단계가 동시에):
 *   ① 도착한 배송(공장은 생산 완료분)을 재고에 넣는다
 *   ② 들어온 주문을 읽는다(소매 = 소비자 수요 · 나머지 = 아래 단계가 order 주 전에 낸 주문)
 *   ③ 밀린 주문(백오더)까지 합쳐 재고만큼 보낸다 — 보낸 것은 shipping 주 뒤 아래 단계에 닿는다
 *   ④ 비용 = 재고 × holding + 백오더 × backlog
 *   ⑤ 주문을 낸다 — 내가 맡은 단계는 내가 넣은 수, 나머지는 고정·조정 식(autoPolicy).
 *      공장의 주문은 생산 요청이라 production 주 뒤 공장 재고로 들어온다.
 * 같은 규칙·같은 씨앗·같은 내 주문이면 같은 결과(재현 · G2). 서버·저장·쿠키 0 — 공유는 주소 값으로만(G4).
 * 브라우저 window.BeerGame · node module.exports.
 */
(function (root) {
  "use strict";

  // mulberry32 — 작은 결정적 난수(재현용). 암호용 아님. cost-sim.js 와 같은 식.
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      var t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // 소비자 수요 열 — 'step'(논문의 계단) 또는 'random'(씨앗 고정 균등 정수)
  function demandSeries(rules, mode, seed) {
    var n = rules.weeks, out = [], d = rules.demand;
    if (mode === "random") {
      var r = rng(seed || 1), lo = d.random.min, hi = d.random.max;
      for (var i = 0; i < n; i++) out.push(lo + Math.floor(r() * (hi - lo + 1)));
    } else {
      for (var w = 1; w <= n; w++) out.push(w < d.step.changeWeek ? d.step.before : d.step.after);
    }
    return out;
  }

  function fill(n, v) { var a = []; for (var i = 0; i < n; i++) a.push(v); return a; }

  // 새 판. role = 내가 맡은 단계 번호(0 소매 … 3 공장), 없으면 넷 다 자동.
  function create(rules, opt) {
    opt = opt || {};
    var S = rules.stages.length, init = rules.initial, dl = rules.delays;
    var g = {
      rules: rules, role: opt.role == null ? -1 : opt.role, mode: opt.demand || "step", seed: opt.seed || 1,
      week: 0, demand: demandSeries(rules, opt.demand || "step", opt.seed || 1), stages: []
    };
    for (var s = 0; s < S; s++) {
      var factory = s === S - 1;
      g.stages.push({
        inventory: init.inventory, backlog: init.backlog,
        // 아래로 가는 배송 줄(이 단계가 받을 것) — 공장은 생산 줄
        inbound: fill(factory ? dl.production : dl.shipping, init.pipeline),
        // 위로 가는 주문 줄(이 단계가 낸 주문이 위 단계에 닿기까지) — 공장은 없다
        orderLine: factory ? [] : fill(dl.order, init.pipeline),
        expected: init.pipeline, onOrder: 0,
        hist: { order: [], incoming: [], shipped: [], inventory: [], backlog: [], cost: [] }
      });
      g.stages[s].onOrder = sum(g.stages[s].inbound) + sum(g.stages[s].orderLine);
    }
    return g;
  }

  function sum(a) { var t = 0; for (var i = 0; i < a.length; i++) t += a[i]; return t; }

  // 고정·조정 주문식(Sterman 1989): 주문 = max(0, E + α(S' − 순재고 − β·운송중))
  function autoOrder(rules, st, incoming) {
    var p = rules.autoPolicy;
    st.expected = p.theta * incoming + (1 - p.theta) * st.expected;
    var net = st.inventory - st.backlog;
    return Math.max(0, Math.round(st.expected + p.alpha * (p.targetStock - net - p.beta * st.onOrder)));
  }

  // 한 주 진행. myOrder = 내가 맡은 단계의 주문(정수 ≥ 0). 끝난 판이면 그대로 돌려준다.
  function step(g, myOrder) {
    var R = g.rules, S = g.stages.length;
    if (g.week >= R.weeks) return g;
    var w = g.week, incoming = [], shipped = [];
    // ① 도착
    for (var s = 0; s < S; s++) {
      var st = g.stages[s], arrived = st.inbound.shift();
      st.inventory += arrived; st.onOrder -= arrived;
    }
    // ② 들어온 주문
    for (s = 0; s < S; s++) incoming.push(s === 0 ? g.demand[w] : g.stages[s - 1].orderLine.shift());
    // ③ 보내기 · ④ 비용
    for (s = 0; s < S; s++) {
      st = g.stages[s];
      var want = incoming[s] + st.backlog, out = Math.min(st.inventory, want);
      st.inventory -= out; st.backlog = want - out; shipped.push(out);
      var c = R.cost.holding * st.inventory + R.cost.backlog * st.backlog;
      st.hist.incoming.push(incoming[s]); st.hist.shipped.push(out);
      st.hist.inventory.push(st.inventory); st.hist.backlog.push(st.backlog); st.hist.cost.push(c);
    }
    // 보낸 것은 아래 단계의 배송 줄 끝으로(소매가 보낸 것은 소비자에게 — 줄 없음)
    for (s = 1; s < S; s++) g.stages[s - 1].inbound.push(shipped[s]);
    // ⑤ 주문
    for (s = 0; s < S; s++) {
      st = g.stages[s];
      var o = s === g.role ? Math.max(0, Math.floor(Number(myOrder) || 0)) : autoOrder(R, st, incoming[s]);
      if (s === g.role) autoOrder(R, st, incoming[s]); // 내 단계도 예상수요는 같은 식으로 갱신(기록용)
      st.hist.order.push(o); st.onOrder += o;
      if (s === S - 1) st.inbound.push(o); else st.orderLine.push(o);
    }
    g.week = w + 1;
    return g;
  }

  function variance(a) {
    if (!a.length) return 0;
    var m = sum(a) / a.length, v = 0;
    for (var i = 0; i < a.length; i++) v += (a[i] - m) * (a[i] - m);
    return v / a.length;
  }

  // 끝난 판의 숫자(G3): 단계별 주문 증폭비 = 그 단계 주문 분산 ÷ 소비자 수요 분산 · 단계별·전체 비용
  function summary(g) {
    var weeks = g.week, dv = variance(g.demand.slice(0, weeks));
    var rows = g.stages.map(function (st, i) {
      return {
        stage: g.rules.stages[i].id, label: g.rules.stages[i].label,
        amplification: dv > 0 ? variance(st.hist.order) / dv : null,
        cost: sum(st.hist.cost), maxBacklog: Math.max.apply(null, st.hist.backlog.concat([0]))
      };
    });
    return { weeks: weeks, demandVariance: dv, stages: rows, totalCost: sum(rows.map(function (r) { return r.cost; })) };
  }

  // 처음부터 다시 — 주소에 담긴 값(역할·수요·씨앗·내 주문 목록)만으로 같은 판을 되살린다
  function replay(rules, opt) {
    var g = create(rules, opt), mine = opt.orders || [];
    for (var i = 0; i < rules.weeks && (g.role < 0 || i < mine.length); i++) step(g, mine[i]);
    return g;
  }

  // 주소 값 ↔ 판 설정. 예: r=0&d=step&s=1&o=4.4.8 — 서버 0 · 쿠키 0(G4)
  function encode(opt) {
    return "r=" + opt.role + "&d=" + (opt.demand || "step") + "&s=" + (opt.seed || 1) + "&o=" + (opt.orders || []).join(".");
  }
  function decode(qs, rules) {
    var p = {};
    String(qs || "").replace(/^\?/, "").split("&").forEach(function (kv) { var i = kv.indexOf("="); if (i > 0) p[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1)); });
    var role = Math.min(rules.stages.length - 1, Math.max(0, parseInt(p.r, 10) || 0));
    var orders = (p.o || "").split(".").filter(function (x) { return x !== ""; }).slice(0, rules.weeks)
      .map(function (x) { return Math.max(0, Math.floor(Number(x) || 0)); });
    return { role: role, demand: p.d === "random" ? "random" : "step", seed: Math.max(1, parseInt(p.s, 10) || 1), orders: orders };
  }

  var api = { create: create, step: step, summary: summary, replay: replay, encode: encode, decode: decode, variance: variance, demandSeries: demandSeries, rng: rng };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.BeerGame = api;
})(this);

/* 셀러 물류비 몬테카를로(2026-10-12 · 개편 2단계 시뮬레이션 1). 계산은 cost-check.js 의 split()·perUnitAt() 을 그대로 쓴다.
 *
 * 무엇을 흔드나 — 쓰는 사람이 넣은 숫자만, 쓰는 사람이 고른 폭으로:
 *   ① 월 출고 건수: 지금 값 × (1 ± 변동폭) 안에서 고르게
 *   ② '모름' 칸: 블록마다 '모름' 칸들의 합(건당)이 [0, 상한] 안에서 고르게. 상한을 비우면
 *      그 블록이 순위가 뒤집히는 금액(compute().flip)의 두 배 — 금액 상수 0(갈래 기준 C3).
 * 무엇을 안 하나 — 업계 평균·요율 같은 바깥 숫자를 넣지 않는다. 결과는 「내가 모르는 폭이 이만하면」의 답이다.
 * 같은 씨앗이면 같은 결과(재현). 브라우저 window.CostSim · node module.exports.
 */
(function (root) {
  "use strict";

  // mulberry32 — 작은 결정적 난수(재현용). 암호용 아님.
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

  function quantile(sorted, q) {
    if (!sorted.length) return null;
    var i = (sorted.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
  }

  /* opts = { runs, seed, volSwing(0~1), unknownMax: [건당 상한 | null, ×3] } */
  function simulate(C, state, opts) {
    opts = opts || {};
    var runs = opts.runs || 4000, swing = opts.volSwing || 0, rand = rng(opts.seed || 1);
    var ship = C.num(state.ship);
    var base = C.compute(state), sp = C.split(state);
    var live = sp.map(function (s, b) { return s.filled > 0 && ship > 0 ? b : -1; }).filter(function (b) { return b >= 0; });
    var caps = sp.map(function (s, b) {
      var u = opts.unknownMax && opts.unknownMax[b];
      if (u !== null && u !== undefined && u !== "" && isFinite(Number(u))) return Number(u);
      var f = base[b].flip;
      return base[b].unknown.length && f ? f.perUnit * 2 : 0;
    });
    var draws = sp.map(function () { return []; });
    var wins = sp.map(function () { return 0; });
    for (var k = 0; k < runs; k++) {
      var n = ship * (1 + swing * (2 * rand() - 1));
      var best = -1, bestV = Infinity;
      for (var j = 0; j < live.length; j++) {
        var b = live[j];
        var v = C.perUnitAt(sp[b], n) + (base[b].unknown.length ? caps[b] * rand() : 0);
        draws[b].push(v);
        if (v < bestV) { bestV = v; best = b; }
      }
      if (best >= 0) wins[best] += 1;
    }
    return sp.map(function (s, b) {
      var d = draws[b].slice().sort(function (x, y) { return x - y; });
      return {
        name: s.name, live: live.indexOf(b) >= 0, cap: caps[b], unknown: base[b].unknown.length,
        pBest: live.length ? wins[b] / runs : null,
        p10: quantile(d, 0.1), p50: quantile(d, 0.5), p90: quantile(d, 0.9), draws: draws[b]
      };
    });
  }

  var api = { rng: rng, quantile: quantile, simulate: simulate };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.CostSim = api;
})(this);

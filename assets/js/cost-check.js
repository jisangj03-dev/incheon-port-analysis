/* 셀러 물류비 자가진단 — 3PL 견적 비교 계산 (2026-10-09).
 *
 * 뼈대는 무료 엑셀 「3PL 견적 비교표」와 같다(jota products/3PL견적비교표/build.py):
 * 청구 항목 10칸 × 표기 넷(별도 · 단가에 포함 · 없음 · 모름) × 블록 셋(지금 방식 · 견적 A · 견적 B).
 * 칸 목록이 바뀌면 엑셀 생성기와 이 파일을 같은 날 고친다.
 *
 * 기준: docs/물류사업_갈래_판정기준_선커밋_20261009.md §1.
 *   C2 — 외부 호출 0. 이 파일은 네트워크를 쓰지 않는다. 입력값은 브라우저 밖으로 나가지 않는다.
 *   C3 — 금액·요율 상수 0. 숫자가 미리 들어가는 길은 아래 SAMPLE(가상값) 하나뿐이다.
 * 대조: python analysis/check_cost_tool.py (엑셀 가상 샘플과 같은 답인지 node 로 돌려 본다).
 *
 * 브라우저에서는 window.CostCheck, node 에서는 module.exports 로 같은 계산을 쓴다.
 */
(function (root) {
  "use strict";

  var OPTS = ["별도", "단가에 포함", "없음", "모름"];
  var BLOCKS = ["지금 방식", "견적 A", "견적 B"];

  // (이름, 청구 단위, 월 수량 기본값, 견적 때 물어볼 질문)
  // 기본값: "ship" = 월 출고 건수, "ret" = 월 반품 건수, "one" = 한 달에 한 번, "" = 직접 입력
  var ITEMS = [
    ["출고 기본 단가(택배비 포함 여부)", "건당", "ship",
      "이 단가에 택배비·포장재·피킹이 다 들어 있나요? 빠진 것이 있으면 무엇인가요?"],
    ["입고비·검수비", "입고 박스·회당", "",
      "입고는 박스·파레트·SKU 중 무엇 기준으로 받나요? 검수는 따로인가요?"],
    ["보관비(파레트·CBM·월 보관료)", "월", "",
      "보관비는 파레트·CBM·면적 중 무엇으로 재나요? 월 중간 입출고는 어떻게 셈하나요?"],
    ["포장재·부자재비", "건당", "ship",
      "박스·완충재는 제공인가요, 실비 청구인가요? 제 상품 크기면 어느 박스인가요?"],
    ["합포장·동봉 등 추가 작업비", "작업 건당", "",
      "합포장·사은품 동봉·스티커 작업은 건당 얼마인가요?"],
    ["반품 회수·재입고비", "반품 건당", "ret",
      "반품 회수 택배비와 재입고 검수비는 따로인가요? 불량 판정은 누가 하나요?"],
    ["월 기본료·시스템 이용료", "월", "one",
      "물량과 상관없이 매달 나가는 기본료·시스템 이용료가 있나요?"],
    ["최소 물량 미달 할증", "월", "one",
      "월 최소 물량이 있나요? 못 채우면 얼마가 붙나요?"],
    ["도서산간·유류·규격 초과 할증", "해당 건당", "",
      "도서산간·제주, 규격 초과, 유류비 연동 할증은 어떻게 붙나요?"],
    ["기타 배분·1회성 비용(수광비·폐기 부담금·세트 작업 등)", "월", "one",
      "수도광열비를 면적으로 나눠 청구하나요? 폐기 부담금·세트 작업 같은 비용은 누가 내나요?"]
  ];

  // 숨은 비용 4종 — 3PL 운영 실무자 답신(2026-10-07)의 구조만. 금액·비율은 받지 않았고 쓰지 않는다.
  // slot = 금액을 넣을 청구 칸 번호(1부터).
  var HIDDEN = [
    { key: "power", name: "수광비(수도광열비) 면적 배분", slot: 10,
      how: "월 고정액이 아니라 창고 전체 수도광열비를 쓰는 면적 비율로 나눠 청구하는 방식이면, 내 물량과 상관없이 달마다 금액이 바뀝니다.",
      ask: "수도광열비를 따로 청구하나요? 그렇다면 무엇을 기준으로 나누나요(면적·파레트 수 등)?" },
    { key: "legal", name: "법적 비용(예: 폐기 부담금)", slot: 10,
      how: "법에 따라 생기는 비용을 화주가 내도록 계약에 들어 있는 경우가 있습니다. 견적 단계에서는 잘 안 보입니다.",
      ask: "폐기 부담금처럼 법으로 생기는 비용은 누가 내나요? 계약서 어느 조항에 있나요?" },
    { key: "oneoff", name: "1회성 유통가공(세트 작업 등)", slot: 10,
      how: "세트 구성·라벨 교체처럼 가끔 한 번씩 붙는 작업비입니다. 한 달 청구서만 보면 매달 드는 돈으로 착각하기 쉬워, 1회성인지 따로 표시해 두는 게 좋습니다.",
      ask: "세트 작업·라벨 교체 같은 가공 작업은 건당 얼마이고, 최소 수량이 있나요?" },
    { key: "fuel", name: "유류비 연동", slot: 9,
      how: "배송 요금이 유가에 연동되는 계약이면 기름값이 오를 때 청구액도 따라 오릅니다. 견적 받은 날의 금액이 계속 가지 않습니다.",
      ask: "배송 요금이 유류비에 연동되나요? 어떤 기준으로, 얼마나 자주 바뀌나요?" }
  ];
  var HIDDEN_OPTS = ["있음", "없음", "모름"];

  /* SAMPLE:BEGIN — 가상값(실제 업체 견적 아님). 엑셀 가상 샘플과 같은 값이다. */
  var SAMPLE = {
    ship: 1000, ret: 30,
    blocks: [
      [["별도", 2800, null], ["없음", null, null], ["없음", null, null], ["별도", 300, null],
       ["없음", null, null], ["별도", 2800, null], ["없음", null, null], ["없음", null, null],
       ["별도", 3000, 20], ["별도", 800000, null]],
      [["별도", 2200, null], ["별도", 1000, 50], ["별도", 30000, 4], ["별도", 200, null],
       ["별도", 300, 100], ["별도", 3500, null], ["별도", 100000, null], ["모름", null, null],
       ["모름", null, null], ["모름", null, null]],
      [["별도", 2700, null], ["단가에 포함", null, null], ["별도", 25000, 4], ["단가에 포함", null, null],
       ["별도", 200, 100], ["별도", 3000, null], ["없음", null, null], ["없음", null, null],
       ["별도", 2500, 20], ["없음", null, null]]
    ]
  };
  /* SAMPLE:END */

  function num(v) {
    if (v === null || v === undefined || v === "") return null;
    var n = typeof v === "number" ? v : Number(String(v).replace(/[,\s원건]/g, ""));
    return isFinite(n) ? n : null;
  }

  function defaultQty(kind, ship, ret) {
    if (kind === "ship") return ship;
    if (kind === "ret") return ret;
    if (kind === "one") return 1;
    return null;
  }

  /* 한 칸의 월 금액 — 엑셀 식과 같다:
     IF(OR(표기="단가에 포함", 표기="없음"), 0, IFERROR(단가 × 수량, 0)) */
  function rowAmount(mark, price, qty) {
    if (mark === "단가에 포함" || mark === "없음") return 0;
    var p = num(price), q = num(qty);
    if (p === null || q === null) return 0;
    return p * q;
  }

  /* state = { ship, ret, blocks: [ [ [표기, 단가, 수량(빈칸이면 기본값)], ... 10 ], ... 3 ] } */
  function compute(state) {
    var ship = num(state.ship), ret = num(state.ret);
    var out = BLOCKS.map(function (name, b) {
      var rows = state.blocks[b] || [];
      var sum = 0, unknown = [], filled = 0;
      ITEMS.forEach(function (it, i) {
        var r = rows[i] || [];
        var mark = r[0] || "";
        var q = num(r[2]);
        if (q === null) q = defaultQty(it[2], ship, ret);
        sum += rowAmount(mark, r[1], q);
        if (mark === "모름") unknown.push(i);
        if (mark) filled += 1;
      });
      return {
        name: name, monthly: sum, filled: filled, unknown: unknown,
        perUnit: ship && ship > 0 ? sum / ship : null
      };
    });
    var base = out[0];
    out.forEach(function (r, b) {
      r.diff = b > 0 && r.perUnit !== null && base.perUnit !== null && base.filled > 0 ? r.perUnit - base.perUnit : null;
    });
    // 순위가 뒤집히는 선 — '모름'이 있는 블록이 다른 블록보다 싸 보이면, 그 차이가 '모름' 칸이 넘으면 안 되는 금액이다.
    out.forEach(function (r) {
      r.flip = null;
      if (!r.unknown.length || r.perUnit === null || !r.filled) return;
      var above = out.filter(function (o) { return o !== r && o.filled && o.perUnit !== null && o.perUnit > r.perUnit; });
      if (!above.length) return;
      above.sort(function (a, c) { return a.perUnit - c.perUnit; });
      r.flip = { against: above[0].name, perUnit: above[0].perUnit - r.perUnit, monthly: (above[0].perUnit - r.perUnit) * ship };
    });
    return out;
  }

  /* 견적 때 물어볼 것 — '모름' 칸과 숨은 비용 4종의 '모름'을 블록별로 모은다.
     hidden = [ { power: "있음"|"없음"|"모름"|"", ... }, ... 3 ] */
  function questions(result, hidden) {
    return result.map(function (r, b) {
      var qs = r.unknown.map(function (i) { return (i + 1) + "번 " + ITEMS[i][0] + " — " + ITEMS[i][3]; });
      var h = (hidden && hidden[b]) || {};
      HIDDEN.forEach(function (x) { if (h[x.key] === "모름") qs.push("계약 전 확인 · " + x.name + " — " + x.ask); });
      return { name: r.name, list: qs };
    });
  }

  /* 숨은 비용을 '있음'으로 골랐는데 그 금액이 들어갈 칸이 비어 있으면 알린다. */
  function hiddenGaps(state, hidden) {
    return BLOCKS.map(function (name, b) {
      var h = (hidden && hidden[b]) || {};
      var rows = state.blocks[b] || [];
      return HIDDEN.filter(function (x) {
        if (h[x.key] !== "있음") return false;
        var r = rows[x.slot - 1] || [];
        return !(r[0] === "별도" && num(r[1]) !== null);
      }).map(function (x) { return x.name + " → " + x.slot + "번 칸에 금액이 없습니다"; });
    });
  }

  /* 손익분기(2026-10-12 · 개편 기준 5) — 월 출고 건수 N 이 바뀌면 건당 비용이 어떻게 바뀌나.
     칸마다 월 금액 = 단가 × 수량이다. 수량 칸을 비워 기본값을 쓰면:
       출고 건수 기본값 → N 에 비례(건당 변동비) · 반품 건수 기본값 → (반품/출고 비율) × N 에 비례
       월 1회·직접 적은 수량 → N 과 무관한 고정비.
     N = 지금 출고 건수일 때 fixed + perShip × N 은 compute() 의 월 합계와 같다(시험이 맞댄다). */
  function split(state) {
    var ship = num(state.ship), ret = num(state.ret);
    var retRate = ship && ship > 0 && ret !== null ? ret / ship : 0;
    return BLOCKS.map(function (name, b) {
      var rows = state.blocks[b] || [];
      var fixed = 0, perShip = 0, filled = 0;
      ITEMS.forEach(function (it, i) {
        var r = rows[i] || [];
        var mark = r[0] || "";
        if (mark) filled += 1;
        if (!mark || mark === "단가에 포함" || mark === "없음") return;
        var p = num(r[1]);
        if (p === null) return;
        var q = num(r[2]);
        if (q === null && it[2] === "ship") perShip += p;
        else if (q === null && it[2] === "ret") perShip += p * retRate;
        else {
          if (q === null) q = defaultQty(it[2], ship, ret);
          if (q !== null) fixed += p * q;
        }
      });
      return { name: name, fixed: fixed, perShip: perShip, filled: filled };
    });
  }

  /* 월 N건일 때 건당 비용. */
  function perUnitAt(s, n) { return n > 0 ? s.fixed / n + s.perShip : null; }

  /* 두 블록의 월 비용이 같아지는 출고 건수 — 그 위에서 어느 쪽이 싼가. 교차가 없으면(평행·음수) 빼고 돌려준다. */
  function crossings(splits) {
    var out = [];
    for (var a = 0; a < splits.length; a++) {
      for (var b = a + 1; b < splits.length; b++) {
        var A = splits[a], B = splits[b];
        if (!A.filled || !B.filled) continue;
        var dv = A.perShip - B.perShip;
        if (dv === 0) continue;
        var n = (B.fixed - A.fixed) / dv;
        if (!(n > 0) || !isFinite(n)) continue;
        out.push({ a: A.name, b: B.name, n: n, cheaperAbove: dv < 0 ? A.name : B.name, cheaperBelow: dv < 0 ? B.name : A.name });
      }
    }
    return out.sort(function (x, y) { return x.n - y.n; });
  }

  /* 입력값 ↔ 주소(개편 기준 8 · 서버 저장 없음). 표기는 OPTS 의 순번, 숨은 비용은 HIDDEN_OPTS 의 순번으로 줄인다. */
  function encode(state, hidden) {
    var o = { v: 1, s: state.ship || "", r: state.ret || "", b: [], h: [] };
    for (var b = 0; b < BLOCKS.length; b++) {
      var rows = state.blocks[b] || [];
      o.b.push(ITEMS.map(function (it, i) {
        var r = rows[i] || [];
        return [OPTS.indexOf(r[0] || ""), r[1] || "", r[2] || ""];
      }));
      var h = (hidden && hidden[b]) || {};
      o.h.push(HIDDEN.map(function (x) { return HIDDEN_OPTS.indexOf(h[x.key] || ""); }));
    }
    var json = JSON.stringify(o);
    var b64 = typeof btoa === "function" ? btoa(json) : Buffer.from(json, "utf-8").toString("base64");
    return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function decode(str) {
    try {
      var b64 = String(str).replace(/-/g, "+").replace(/_/g, "/");
      var json = typeof atob === "function" ? atob(b64) : Buffer.from(b64, "base64").toString("utf-8");
      var o = JSON.parse(json);
      if (!o || o.v !== 1) return null;
      var cell = function (v) { return v === null || v === undefined ? "" : String(v).replace(/[^0-9.,]/g, ""); };
      var state = { ship: cell(o.s), ret: cell(o.r), blocks: [] };
      var hidden = [];
      for (var b = 0; b < BLOCKS.length; b++) {
        var rows = (o.b && o.b[b]) || [];
        state.blocks.push(ITEMS.map(function (it, i) {
          var r = rows[i] || [];
          return [OPTS[r[0]] || "", cell(r[1]), cell(r[2])];
        }));
        var h = {};
        var hh = (o.h && o.h[b]) || [];
        HIDDEN.forEach(function (x, k) { if (HIDDEN_OPTS[hh[k]]) h[x.key] = HIDDEN_OPTS[hh[k]]; });
        hidden.push(h);
      }
      return { state: state, hidden: hidden };
    } catch (e) {
      return null;
    }
  }

  var api = {
    OPTS: OPTS, BLOCKS: BLOCKS, ITEMS: ITEMS, HIDDEN: HIDDEN, HIDDEN_OPTS: HIDDEN_OPTS, SAMPLE: SAMPLE,
    num: num, rowAmount: rowAmount, compute: compute, questions: questions, hiddenGaps: hiddenGaps,
    split: split, perUnitAt: perUnitAt, crossings: crossings, encode: encode, decode: decode
  };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.CostCheck = api;
})(this);

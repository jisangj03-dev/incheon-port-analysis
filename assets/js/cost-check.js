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

  var api = {
    OPTS: OPTS, BLOCKS: BLOCKS, ITEMS: ITEMS, HIDDEN: HIDDEN, HIDDEN_OPTS: HIDDEN_OPTS, SAMPLE: SAMPLE,
    num: num, rowAmount: rowAmount, compute: compute, questions: questions, hiddenGaps: hiddenGaps
  };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.CostCheck = api;
})(this);

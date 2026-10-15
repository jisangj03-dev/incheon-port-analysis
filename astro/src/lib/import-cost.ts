// 수입원가 어림(실무 도구 · Q5) — 과세가격(CIF × 관세환율) → 관세 → 개별소비세·주세·교육세·농어촌특별세 → 부가가치세 → 합계. 참고용 · 법률·세무·관세 자문 아님.
// [2026-10-15 P1 ②] 내국세 넷과 끝수 규칙을 넣었다(같은 식 = tools-build/v3/fx_derive.py landed — 바꾸면 둘 다).
//  · 과세가격 = CIF × 관세환율(수입신고일이 속한 주의 관세청 고시 환율 · 관세법 제18조) — 원 미만 버림
//  · 관세 = 과세가격 × 관세율
//  · 개별소비세 = (과세가격 + 관세) × 개별소비세율(개별소비세법 — 수입물품 과세표준 = 관세 과세가격 + 관세)
//  · 주세 = (과세가격 + 관세) × 주세율(종가세 주류만 · 맥주·탁주 같은 종량세는 이 식 밖)
//  · 교육세 = 개별소비세 × 교육세율(기본 30% · 일부 품목 15%) + 주세 × 주세분 교육세율(기본 10% · 주세율 70% 초과 주류 30%)
//  · 농어촌특별세 = 개별소비세 × 농특세율(대상 품목만 · 기본 0)
//  · 부가가치세 = (과세가격 + 관세 + 개별소비세 + 주세 + 교육세 + 농특세) × 10%(부가가치세법 제29조)
//  · 세액마다 10원 미만 버림(국고금 관리법 제47조 끝수 계산) — 원문은 이 세션에서 열지 못해 검색 근거(지면 「한계」에 적는다)
export type CostIn = {
  goods: number; freight: number; insurance: number; incoterm: "FOB" | "CIF"; fx: number; duty_pct: number; vat_pct?: number; inland_krw?: number;
  /** 개별소비세율 % · 교육세율 %(개소세분) · 농특세율 %(개소세분) · 주세율 % · 교육세율 %(주세분) — 없으면 0(일반 공산품) */
  excise_pct?: number; edu_pct?: number; rural_pct?: number; liquor_pct?: number; liquor_edu_pct?: number;
};
// landed = 납부 합계(과세가격 + 세금 전부) · cost = 원가(부가세 제외 — 사업자는 수입 부가세를 매입세액으로 공제받는다)
export type CostOut = { cif_usd: number; customs_value: number; duty: number; excise: number; liquor: number; edu: number; rural: number; vat: number; landed: number; cost: number; per_usd: number };

/** 세액 끝수 — 10원 미만 버림 */
export const tax10 = (v: number) => Math.floor(v / 10 + 1e-9) * 10;

export function landedCost(i: CostIn): CostOut {
  // FOB 면 운임·보험을 더해 CIF 로(우리나라 관세 과세가격은 CIF 기준) · CIF 면 이미 들어 있다
  const cif = i.incoterm === "FOB" ? i.goods + i.freight + i.insurance : i.goods;
  const cv = Math.floor(cif * i.fx + 1e-6);
  const duty = tax10((cv * i.duty_pct) / 100);
  const base = cv + duty;
  const excise = tax10((base * (i.excise_pct || 0)) / 100);
  const liquor = tax10((base * (i.liquor_pct || 0)) / 100);
  const edu = tax10((excise * (i.edu_pct ?? 30)) / 100) + tax10((liquor * (i.liquor_edu_pct ?? 10)) / 100);
  const rural = tax10((excise * (i.rural_pct || 0)) / 100);
  const vat = tax10(((base + excise + liquor + edu + rural) * (i.vat_pct ?? 10)) / 100);
  const taxes = duty + excise + liquor + edu + rural;
  const landed = cv + taxes + vat + (i.inland_krw || 0);
  const cost = cv + taxes + (i.inland_krw || 0);
  return { cif_usd: cif, customs_value: cv, duty, excise, liquor, edu, rural, vat, landed, cost, per_usd: i.goods ? cost / i.goods : 0 };
}

/** 같은 물건을 다른 환율·운임으로 들였을 때의 차이(원) — 「환율이 이만큼 바뀌면」 */
export function delta(base: CostIn, change: Partial<CostIn>) { const a = landedCost(base), b = landedCost({ ...base, ...change }); return { a, b, diff: b.landed - a.landed, pct: a.landed ? (100 * (b.landed - a.landed)) / a.landed : 0 }; }

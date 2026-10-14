// 수입원가 어림(실무 도구 · Q5) — 과세가격(CIF × 관세환율) → 관세 → 부가가치세 → 합계. 참고용 · 법률·세무·관세 자문 아님.
// 규칙(관세법 제30조 과세가격 · 부가가치세법 제29조 수입재화 과세표준 = 관세 과세가격 + 관세 + 개별소비세 등): 개별소비세·교육세·주세는 넣지 않는다(지면에 적는다).
export type CostIn = { goods: number; freight: number; insurance: number; incoterm: "FOB" | "CIF"; fx: number; duty_pct: number; vat_pct?: number; inland_krw?: number };
export type CostOut = { cif_usd: number; customs_value: number; duty: number; vat: number; landed: number; per_usd: number };

export function landedCost(i: CostIn): CostOut {
  // FOB 면 운임·보험을 더해 CIF 로(우리나라 관세 과세가격은 CIF 기준) · CIF 면 이미 들어 있다
  const cif = i.incoterm === "FOB" ? i.goods + i.freight + i.insurance : i.goods;
  const cv = Math.round(cif * i.fx);
  const duty = Math.floor((cv * i.duty_pct) / 100);
  const vat = Math.floor(((cv + duty) * (i.vat_pct ?? 10)) / 100);
  const landed = cv + duty + vat + (i.inland_krw || 0);
  return { cif_usd: cif, customs_value: cv, duty, vat, landed, per_usd: i.goods ? landed / i.goods : 0 };
}

/** 같은 물건을 다른 환율·운임으로 들였을 때의 차이(원) — 「환율이 이만큼 바뀌면」 */
export function delta(base: CostIn, change: Partial<CostIn>) { const a = landedCost(base), b = landedCost({ ...base, ...change }); return { a, b, diff: b.landed - a.landed, pct: a.landed ? (100 * (b.landed - a.landed)) / a.landed : 0 }; }

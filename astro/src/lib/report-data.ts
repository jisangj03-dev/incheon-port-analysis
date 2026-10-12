// 보고서 ② 층 데이터 — 저장소의 원시 CSV 를 빌드 때 읽어 위젯용 계열로(실행 중 API 0 · 확장 기준 18).
// 계산은 발행본이 쓴 것과 같은 정의다. 어긋나지 않음은 tests/report-charts.spec.mjs 가 발행 수치로 맞댄다
// (예: 2025 수출 방향 공컨 843,838 TEU · 수입 139,418 · 2022 배율 27.32).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot, lastUpdated } from "./content";

function csv(rel: string): Record<string, string>[] {
  const txt = readFileSync(join(repoRoot(), rel), "utf-8").replace(/^﻿/, "");
  const lines = txt.split(/\r?\n/).filter((l) => l && !l.startsWith("#"));
  const head = lines[0].split(",").map((h) => h.trim());
  return lines.slice(1).map((l) => {
    const cells = l.match(/("([^"]|"")*"|[^,]*)(,|$)/g)!.map((c) => c.replace(/,$/, "").replace(/^"|"$/g, "").trim());
    return Object.fromEntries(head.map((h, i) => [h, cells[i] ?? ""]));
  });
}
const num = (s: string) => (s === "" || s === undefined ? null : Number(String(s).replace(/[,\s]/g, "")));

/** 공컨테이너 방향별 월 TEU(외국적+한국적) — 모집단 ocCt=1(외항) · GInOut 1=수입 · 2=수출 · 3·4=환적(docs/GInOut_코드규명.md). */
export function emptyDirection() {
  const files = ["analysis/container_2005_2021_direction.csv", ...[2022, 2023, 2024, 2025, 2026].map((y) => `analysis/container_${y}_direction.csv`)];
  const m = new Map<string, { ym: string; imp: number; exp: number; tr: number }>();
  for (const f of files) {
    for (const r of csv(f)) {
      if (r.ocCt !== "1") continue;
      const ym = `${r.yyyy}-${String(r.mm).padStart(2, "0")}`;
      const t = (num(r.forEmpTeu) || 0) + (num(r.korEmpTeu) || 0);
      const o = m.get(ym) || { ym, imp: 0, exp: 0, tr: 0 };
      if (r.GInOut === "1") o.imp += t; else if (r.GInOut === "2") o.exp += t; else o.tr += t;
      m.set(ym, o);
    }
  }
  const series = [...m.values()].sort((a, b) => a.ym.localeCompare(b.ym)).map((o) => ({ ...o, imp: Math.round(o.imp * 100) / 100, exp: Math.round(o.exp * 100) / 100, tr: Math.round(o.tr * 100) / 100 }));
  return { series, updated: lastUpdated("analysis/container_2026_direction.csv"), source: "공공데이터포털 인천항만공사 공컨테이너 화물 통계 API", unit: "TEU" };
}

/** 공컨 규격×방향 — 월별 40ft 비중(박스 수 기준 · #06·#07). */
export function sizeDirection() {
  const rel = "analysis/size_direction_monthly.csv";
  const series = csv(rel).map((r) => ({
    ym: `${r["연도"]}-${String(r["월"]).padStart(2, "0")}`,
    impShare: num(r["수입_40ft비중_pct"]), expShare: num(r["수출_40ft비중_pct"]), gap: num(r["격차_pp"]),
    impBox: num(r["수입_총박스"]), lowVolume: r["저볼륨"] || "",
  }));
  return { series, updated: lastUpdated(rel), source: "공공데이터포털 인천항만공사 공컨테이너 화물 통계 API(규격별)", unit: "%" };
}

/** 터미널별 월 처리량(천TEU) — 인천지방해양수산청 월별 항만운영통계(#11·#12·물동량). */
export function terminals() {
  const rel = "analysis/terminal_monthly_long.csv";
  const rows = csv(rel).filter((r) => r["계층"] === "터미널" && r["당월_천TEU"] !== "");
  const names = [...new Set(rows.map((r) => r["터미널"]))];
  const series = rows.map((r) => ({ ym: r["기준연월"], name: r["터미널"], group: r["부두군"], v: num(r["당월_천TEU"]), yoy: num(r["전년대비_당월_%"]) }));
  return { names, series, updated: lastUpdated(rel), source: "인천지방해양수산청 월별 항만운영통계", unit: "천TEU" };
}

/** 인천 품목(HS 2단위 류)별 월 수출입 금액(천 달러 · #13 이 명세의 「달러」를 천 달러로 바로잡았다). */
export function items() {
  const rel = "analysis/incheon_sido_item.csv";
  const rows = csv(rel).filter((r) => r.hsSgn && r.hsSgn !== "");
  const series = rows.map((r) => ({ ym: `${r.reqYymm.slice(0, 4)}-${r.reqYymm.slice(4, 6)}`, hs: r.hsSgn, name: r.korePrlstNm, exp: num(r.expUsdAmt) || 0, imp: num(r.impUsdAmt) || 0 }));
  return { series, months: [...new Set(series.map((s) => s.ym))].sort(), updated: lastUpdated(rel), source: "관세청 시도별 품목별 수출입실적(공공데이터포털 15101641)", unit: "천 달러" };
}

/** 보고서 id → 위젯 종류와 기본 보기. 없는 편은 「준비 중」. */
export const REPORT_WIDGET: Record<string, { kind: "direction" | "size" | "terminal" | "item"; from?: string; to?: string; view?: "teu" | "ratio" }> = {
  "report_01_공컨테이너_물동량": { kind: "direction", from: "2025-01", to: "2025-12", view: "teu" },
  "report_02_공컨테이너_비율": { kind: "direction", from: "2025-01", to: "2025-12", view: "teu" },
  "report_03_공컨테이너_수출입방향": { kind: "direction", from: "2025-01", to: "2025-12", view: "teu" },
  "report_04_공컨테이너_연도별추세": { kind: "direction", from: "2022-01", to: "2025-12", view: "ratio" },
  "report_06_공컨테이너_규격방향": { kind: "size", from: "2022-01", to: "2025-12" },
  "report_07_공컨테이너_표본외검증": { kind: "size", from: "2022-01", to: "2026-06" },
  "report_09_공컨테이너_시계열연장": { kind: "direction", from: "2005-01", to: "2021-12", view: "ratio" },
  "report_11_터미널별_처리량": { kind: "terminal", from: "2025-10", to: "2026-07" },
  "report_12_터미널별_장기창": { kind: "terminal", from: "2023-03", to: "2026-07" },
  "report_13_인천_품목별_수출입": { kind: "item" },
  "물동량": { kind: "terminal", from: "2025-08", to: "2026-07" },
};

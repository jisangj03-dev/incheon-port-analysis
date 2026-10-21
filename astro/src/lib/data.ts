// 빌드 시 스냅샷 — 저장소의 공개 CSV 를 읽어 화면용 계열을 만든다(실행 중 API 호출 0 · 기준 20 경계).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot, lastUpdated } from "./content";

function csv(rel: string): Record<string, string>[] {
  const txt = readFileSync(join(repoRoot(), rel), "utf-8").replace(/^﻿/, "");
  const lines = txt.split(/\r?\n/).filter((l) => l && !l.startsWith("#"));
  const head = lines[0].split(",");
  return lines.slice(1).map((l) => {
    const cells = l.match(/("([^"]|"")*"|[^,]*)(,|$)/g)!.map((c) => c.replace(/,$/, "").replace(/^"|"$/g, "").trim());
    return Object.fromEntries(head.map((h, i) => [h, cells[i] ?? ""]));
  });
}

/** 인천항 컨테이너 월별 처리량(천TEU) — 인천지방해양수산청 월별 항만운영통계 「컨테이너 합계」 행. */
/** 공표 전년비와 처리량으로 잰 전년비의 차이 최댓값(%p) — tools-build/flows_derive.py 가 home_flows.json checks 에 계산해 둔다(2026-10-21 · 손으로 적은 「최대 0.8%p」를 걷음). */
export function teuYoyGap(): number | null {
  try { return JSON.parse(readFileSync(join(repoRoot(), "data/derived/home_flows.json"), "utf-8")).checks?.teu_yoy_gap_pp ?? null; } catch { return null; }
}

export function portMonthly() {
  const rel = "analysis/terminal_monthly_long.csv";
  const rows = csv(rel).filter((r) => r["계층"] === "합계" && r["당월_천TEU"]);
  const series = rows.map((r) => ({ ym: r["기준연월"], v: Number(r["당월_천TEU"]), yoy: r["전년대비_당월_%"] === "" ? null : Number(r["전년대비_당월_%"]) }));
  return { series, updated: lastUpdated(rel), source: "인천지방해양수산청 월별 항만운영통계" };
}

/** 3D 지도용 — 부두군·터미널별 월별 처리량(천TEU) + 자리표(data/derived/places.json · 개략 좌표). */
export function mapSeries() {
  const rel = "analysis/terminal_monthly_long.csv";
  const rows = csv(rel);
  const places = JSON.parse(readFileSync(join(repoRoot(), "data/derived/places.json"), "utf-8")).places;
  const months = [...new Set(rows.filter((r) => r["계층"] === "합계").map((r) => r["기준연월"]))].sort();
  const pick = (spec: string | null) => {
    if (!spec) return null;
    const [layer, name] = spec.split(":");
    return months.map((m) => {
      const r = rows.find((x) => x["기준연월"] === m && x["계층"] === layer && (layer === "부두군" ? x["부두군"] : x["터미널"]) === name);
      return r && r["당월_천TEU"] !== "" ? Number(r["당월_천TEU"]) : null;
    });
  };
  return {
    months,
    places: places.map((p: any) => ({ ...p, values: pick(p.series) })),
    updated: lastUpdated(rel),
    placesUpdated: lastUpdated("data/derived/places.json"),
    source: "인천지방해양수산청 월별 항만운영통계",
  };
}

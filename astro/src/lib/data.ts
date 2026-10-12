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
export function portMonthly() {
  const rel = "analysis/terminal_monthly_long.csv";
  const rows = csv(rel).filter((r) => r["계층"] === "합계" && r["당월_천TEU"]);
  const series = rows.map((r) => ({ ym: r["기준연월"], v: Number(r["당월_천TEU"]), yoy: r["전년대비_당월_%"] === "" ? null : Number(r["전년대비_당월_%"]) }));
  return { series, updated: lastUpdated(rel), source: "인천지방해양수산청 월별 항만운영통계" };
}

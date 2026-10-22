// 갱신 무인화 ②(docs/측심_갱신무인화_판정기준_선커밋_20261022.md) — 빌드된 **모든 공개 지면**의 보이는 숫자가 데이터 파일에 있다(전수).
// 지면별 시험(tools-v3 · ds · beer-game …)은 그 지면의 데이터 묶음으로 더 좁게 대고, 이 시험은 빠진 지면이 없게 전부를 한 번에 훑는다.
// 뺀 것: /docs · /analysis = 날짜를 박은 판정·방법 기록(그날 원자료로 쓴 글 · 갱신 대상 아님) · 검색엔진 확인 파일. 공유 카드 틀은 og-cards.mjs 가 찍기 전에 같은 검사를 한다.
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join } from "node:path";
import { check } from "../tools-build/check-data-numbers.mjs";

const walk = (d) => readdirSync(d).flatMap((f) => { const p = join(d, f); return statSync(p).isDirectory() ? walk(p) : [p]; });
const SKIP = /^astro\/dist\/(docs|analysis|_a)\/|^astro\/dist\/google[0-9a-f]+\.html$/;

test("갱신 무인화 ② — 모든 공개 지면 숫자 = 데이터 파일", ({}, info) => {
  test.skip(info.project.name !== "desktop-1440", "빌드 결과 판정은 한 번만");
  const DATA = walk("data").filter((f) => /\.(json|csv)$/.test(f) && statSync(f).size < 8e6).map((f) => readFileSync(f, "utf-8"));
  const pages = walk("astro/dist").filter((f) => f.endsWith(".html") && !SKIP.test(f));
  expect(pages.length, "빌드된 지면이 없다").toBeGreaterThan(10);
  const bad = pages.map((p) => [p, check(readFileSync(p, "utf-8"), DATA).bad]).filter(([, b]) => b.length).map(([p, b]) => `${p}: ${b.slice(0, 8).join(" ")}`);
  expect(bad, "데이터 파일에 없는 숫자가 보이는 지면").toEqual([]);
});

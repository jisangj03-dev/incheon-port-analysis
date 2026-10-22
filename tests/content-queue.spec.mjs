// 콘텐츠 큐(B10 · 전권 위임 ④) — 초안 속 숫자는 파생 데이터 파일에만 있다 · 「게시 = 선장님」 · 채널 셋 · 실명·키 0.
// 선커밋 ④-상세: 데이터 밖 숫자가 있는 초안은 버린다(생성기 tools-build/content_queue.py 가 쓰지 않는다 — 여기서 한 번 더 본다).
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { check } from "../tools-build/check-data-numbers.mjs";

const Q = "content-queue";
// [2026-10-22 갱신 무인화 ①] 숫자 대조는 **live/**(refresh 가 원천 갱신 때마다 다시 만드는 판)만 — 날짜 폴더는 그날 데이터로 만든 기록(보관)이라 숫자가 어긋나는 것이 맞다.
//   홍보 초안은 틀(templates/ · 숫자 0)에서 drafts.py 가 만든다 — live 판이 지금 데이터로 다시 만든 것과 같은지도 본다.
const drafts = existsSync(join(Q, "live")) ? readdirSync(join(Q, "live")).filter((f) => f.endsWith(".md")).map((f) => join(Q, "live", f)) : [];
const DATA = [...readdirSync("data/derived").filter((f) => f.endsWith(".json")).map((f) => `data/derived/${f}`), "data/rooms.json", "data/sources.json"].map((f) => readFileSync(f, "utf-8"));
const profile = JSON.parse(readFileSync("data/profile.json", "utf-8"));

test("B10 콘텐츠 큐 — 초안 숫자 = 데이터 · 게시 0 · 채널 셋 · 실명 0", ({}, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  expect(drafts.length, "초안이 없다").toBeGreaterThan(0);
  for (const f of drafts) {
    const md = readFileSync(f, "utf-8"), body = md.split("\n---\n").slice(1).join("\n---\n");
    expect(check(body, DATA).bad, f).toEqual([]);
    expect(md, f).toContain("게시 = 선장님");
    // 채널 하나짜리 게시 파일(drafts.py posts — 머리에 channel:)은 절이 없다 · 대기열 검사가 그 꼴을 요구한다
    if (/^channel:/m.test(md.split("\n---\n")[0])) expect(md, `${f} 채널 머리`).toMatch(/^target: https:\/\/\S+/m);
    else for (const ch of ["## LinkedIn", "## 블로그", "## Threads"]) expect(md, `${f} ${ch}`).toContain(ch);
    if (profile.name) expect(md.includes(profile.name), `${f} 실명`).toBe(false);
    expect(md).not.toMatch(/serviceKey|DATA_GO_KR_KEY=/);
  }
});

test("갱신 무인화 ① — 홍보 초안 = 틀 + 데이터(손으로 적은 숫자 0 · live 판이 지금 데이터와 같다)", ({}, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  for (const a of [["tools-build/facts.py"], ["tools-build/drafts.py", "--check"]]) {
    const r = spawnSync("python3", a, { encoding: "utf-8" });
    expect(r.status, `${a.join(" ")}\n${r.stdout}${r.stderr}`).toBe(0);
  }
});

// 콘텐츠 큐(B10 · 전권 위임 ④) — 초안 속 숫자는 파생 데이터 파일에만 있다 · 「게시 = 선장님」 · 채널 셋 · 실명·키 0.
// 선커밋 ④-상세: 데이터 밖 숫자가 있는 초안은 버린다(생성기 tools-build/content_queue.py 가 쓰지 않는다 — 여기서 한 번 더 본다).
import { test, expect } from "@playwright/test";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { check } from "../tools-build/check-data-numbers.mjs";

const Q = "content-queue";
const drafts = existsSync(Q) ? readdirSync(Q).filter((d) => /^\d{4}-\d{2}-\d{2}$/.test(d)).flatMap((d) => readdirSync(join(Q, d)).filter((f) => f.endsWith(".md")).map((f) => join(Q, d, f))) : [];
const DATA = [...readdirSync("data/derived").filter((f) => f.endsWith(".json")).map((f) => `data/derived/${f}`), "data/rooms.json", "data/sources.json"].map((f) => readFileSync(f, "utf-8"));
const profile = JSON.parse(readFileSync("data/profile.json", "utf-8"));

test("B10 콘텐츠 큐 — 초안 숫자 = 데이터 · 게시 0 · 채널 셋 · 실명 0", ({}, info) => {
  test.skip(info.project.name !== "desktop-1440", "한 번이면 된다");
  expect(drafts.length, "초안이 없다").toBeGreaterThan(0);
  for (const f of drafts) {
    const md = readFileSync(f, "utf-8"), body = md.split("\n---\n").slice(1).join("\n---\n");
    expect(check(body, DATA).bad, f).toEqual([]);
    expect(md, f).toContain("게시 = 선장님");
    for (const ch of ["## LinkedIn", "## 블로그", "## Threads"]) expect(md, `${f} ${ch}`).toContain(ch);
    if (profile.name) expect(md.includes(profile.name), `${f} 실명`).toBe(false);
    expect(md).not.toMatch(/serviceKey|DATA_GO_KR_KEY=/);
  }
});

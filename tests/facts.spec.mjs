// 갱신 무인화 ②③(docs/측심_갱신무인화_판정기준_선커밋_20261022.md) — 이름 붙은 핵심 숫자는 **값이 같아야** 지면에 보이고(있는지가 아니라),
// 해석 문장은 지금 갈래 = 승인 갈래(data/claims.json)여야 한다. 뒤집히면 빨강 — refresh 는 배포 대신 문장 확인 PR 을 연다.
import { test, expect } from "@playwright/test";
import { readFileSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { visibleText } from "../tools-build/check-data-numbers.mjs";

const dist = (p) => `astro/dist${p === "/" ? "/index.html" : p}`;
const text = (p) => visibleText(readFileSync(dist(p), "utf-8")).replace(/\s+/g, " ");

test.describe("갱신 무인화 — 핵심 숫자 · 해석 문장", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "desktop-1440", "빌드 결과 판정은 한 번만"));
  test("facts.json = 지금 데이터(다시 만들어도 같다)", () => {
    const before = readFileSync("data/derived/facts.json", "utf-8");
    const r = spawnSync("python3", ["tools-build/facts.py"], { encoding: "utf-8" });
    expect(r.status, r.stdout + r.stderr).toBe(0);
    expect(readFileSync("data/derived/facts.json", "utf-8"), "facts.json 이 데이터보다 낡았다 — python tools-build/facts.py").toBe(before);
  });
  test("핵심 숫자 — 지면에 같은 값", () => {
    const F = JSON.parse(readFileSync("data/derived/facts.json", "utf-8")).facts;
    const miss = [];
    // 값은 앞뒤가 숫자가 아닌 자리에서만 센다(「5」가 「52주」 안에서 통과하지 않게) · ctx 가 있으면 그 꼴로(10/22 사실 대조 C4)
    const esc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const pat = (f) => f.ctx ? new RegExp(f.ctx.split("{v}").map(esc).join(`\\s*${esc(f.v)}\\s*`)) : new RegExp(`(?<![\\d.])${esc(f.v)}(?![\\d])`);
    for (const [k, f] of Object.entries(F)) for (const p of f.pages) if (existsSync(dist(p)) && !pat(f).test(text(p))) miss.push(`${k}=${f.v}${f.ctx ? ` 「${f.ctx}」` : ""} @ ${p}`);
    expect(miss, "핵심 숫자가 지면에 그 값으로 안 보인다(기준이 다르거나 지면이 다른 값을 낸다)").toEqual([]);
  });
  test("해석 문장 — 지금 갈래 = 승인 갈래 · 승인 문장이 지면에 있다", () => {
    const r = spawnSync("python3", ["tools-build/facts.py", "--check"], { encoding: "utf-8" });
    expect(r.status, `해석 문장이 뒤집혔다 — 문장 확인 PR 대상\n${r.stdout}${r.stderr}`).toBe(0);
    const C = JSON.parse(readFileSync("data/claims.json", "utf-8")).claims;
    for (const c of C.filter((c) => c.page)) {
      const t = c.variants[c.approved].text;
      if (t) expect(text(c.page), `${c.id} 승인 문장 @ ${c.page}`).toContain(t);
      for (const [k, v] of Object.entries(c.variants)) if (k !== c.approved && v.text && !t.includes(v.text)) expect(text(c.page), `${c.id} 승인 안 된 갈래 「${v.text}」가 지면에 있다`).not.toContain(v.text);
    }
  });
});

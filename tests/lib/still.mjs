// 정지 화면이 필요한 시험(배치·겹침·눈 검사) — 2026-10-20 부터 동작 줄이기에서도 데이터 흐름은 느리게 움직인다(docs/품질기준.md Q7).
// 그래서 「동작 줄이기」만으로는 화면이 멈추지 않는다 → 사람이 「멈춤」을 고른 상태(lib/motion.ts · localStorage sc:motion)로 연다.
export async function still(page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => { try { localStorage.setItem("sc:motion", "paused"); } catch {} });
}
export const STILL_INIT = () => { try { localStorage.setItem("sc:motion", "paused"); } catch {} };

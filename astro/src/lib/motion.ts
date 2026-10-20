// 움직임 규칙 하나(2026-10-20 · docs/품질기준.md Q7) — 모든 움직이는 지면이 이것만 읽는다.
//  · 동작 줄이기(prefers-reduced-motion: reduce) = 데이터 흐름(점·달 넘김)은 **느리게 계속** · 카메라·줌·패닝·튀는 효과만 끈다.
//    (Windows 「애니메이션 효과」 꺼짐이 흔하다 — 그 노트북에서 홈 지도가 통째로 멈췄다 · 선장님 실측 10/20)
//  · 멈춤 = 사람이 단추로 고른 것. 지면을 옮겨도 기억한다(localStorage · 막혀 있으면 기억만 못 한다).
const KEY = "sc:motion";

/** 동작 줄이기 설정인가 */
export const reduced = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
/** 동작 줄이기일 때 데이터 흐름 속도 배율 */
export const SLOW = 0.4;
/** 지금 속도 배율 — 동작 줄이기면 SLOW, 아니면 1 */
export const pace = () => (reduced() ? SLOW : 1);

/** 사람이 멈춤을 골랐나(지면을 옮겨도 그대로) */
export function paused(): boolean {
  try { return localStorage.getItem(KEY) === "paused"; } catch { return false; }
}
export function setPaused(p: boolean) {
  try { if (p) localStorage.setItem(KEY, "paused"); else localStorage.removeItem(KEY); } catch { /* 저장 막힘 — 이 지면에서만 멈춘다 */ }
}

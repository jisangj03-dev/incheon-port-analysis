// Astro 최소 구성 — 빌드·검사가 도는지 확인하는 자리(2026-10-10). **공개 사이트에 연결하지 않는다.**
// Jekyll 빌드에서는 _config.yml exclude 로 빠진다. 개편(이전)은 다음 세션 판단이다.
import { defineConfig } from "astro/config";

export default defineConfig({
  output: "static",
  // 외부 요청 0 — 글꼴·텔레메트리 없이 빌드 산출물만 쓴다.
  devToolbar: { enabled: false },
});

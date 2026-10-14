# site_qa — 인천 지면의 헤드리스 검사 (2026-09-07)

미리보기(`render_preview.py --site . --serve`)나 실물 주소를 **눈으로 확인 못 하는 자리를 기계로** 본다.
전부 형제 저장소 `../sounding/tools/node_modules` 의 playwright 를 빌려 쓴다(`tools/npm install` 이 먼저).

| 스크립트 | 무엇 | 쓰는 법 |
|---|---|---|
| `crawl.mjs` | 첫 화면에서 닿는 같은 출처 지면 전부 — 콘솔·페이지 오류 · 요청 실패 · HTTP ≥400 · 가로 넘침 · 깨진 그림 · 내부 링크 상태 | `node analysis/site_qa/crawl.mjs http://127.0.0.1:8800` |
| `shots.mjs` | 6지면 × 밝음/어둠 × 데스크톱/모바일 전체 페이지 PNG + 첫 화면 행 링크 착지 9/9 | `node analysis/site_qa/shots.mjs <주소> <출력 폴더>` |
| `printcheck.mjs` | 인쇄 미디어 에뮬레이션 — 종이 흰색·글자 검정·바/푸터/차례 숨김·리빌 표시 | `node analysis/site_qa/printcheck.mjs <지면 주소> <출력 접두>` |
| `audit_apple.mjs` | 애플 두 지면·측심·인천에서 같은 항목(바·제목·본문·열·강조색·컨트롤·모션·다크) 실측 | `node analysis/site_qa/audit_apple.mjs` |

**닿지 않는 곳.** 크로미움 헤드리스다 — iOS Safari 는 못 본다. 미리보기는 Jekyll 이 아니다(사고 20) — 실물 지문은 `docs/렌더_기준선.md`.
axe 는 측심 `tools/a11y.mjs <주소>` 를 그대로 쓴다.

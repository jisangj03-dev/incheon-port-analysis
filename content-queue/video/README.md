# 도구 시연 영상 — 콘텐츠 큐(게시 = 선장님)

> 기준: `docs/측심_전권위임_단계기준_선커밋_20261015.md` ⑤-상세 · 만드는 법: `.github/workflows/reels.yml`(Actions 렌더 · 돈 0)
> 이 폴더의 어떤 영상도 자동으로 올라가지 않는다. 게시 상태 정본은 `docs/채널대기열.md` 다.

## 받는 곳

- 최신 렌더: Actions **reels** 실행 https://github.com/jisangj03-dev/incheon-port-analysis/actions/runs/38688785985(2026-10-15 · c0801a0) → 산출물 `reels`(mp4 여섯 · `manifest.json` · 30일 보관)
- 다시 만들기: Actions → reels → Run workflow(`only` 를 비우면 셋 · 한 편만이면 `chokepoint`/`import-cost`/`bid-radar`). 데이터가 갱신된 뒤 돌리면 자막 숫자도 따라 바뀐다.

## 세 편

| 편 | 릴스(9:16 · 1080×1920) | LinkedIn(1:1 · 1080×1080) | 같이 쓸 글 초안 |
|---|---|---|---|
| 초크포인트 충격 | `chokepoint-portrait.mp4` | `chokepoint-square.mp4` | `content-queue/2026-10-15/chokepoint.md` |
| 환율 파도 · 수입원가 | `import-cost-portrait.mp4` | `import-cost-square.mp4` | `content-queue/2026-10-15/import-cost.md` |
| 공공입찰 레이더 | `bid-radar-portrait.mp4` | `bid-radar-square.mp4` | `content-queue/2026-10-15/bid-radar.md` |

- 한 편 = 머리(질문 · 큰 숫자 · 2.5초) → 도구 화면 조작(자막 = 조작한 순간의 숫자 · 아래 띠 = 출처 · 기준일) → 끝 카드(주소 · 3초) · 18~22초.
- 화면 글의 숫자는 `og/cards.json`(지면에서 읽은 값)과 `data/derived` 에서만 온다. 렌더 전에 숫자 검사를 해서 밖의 숫자가 있으면 그 편은 만들지 않는다(`manifest.json` 의 `skipped`).
- 영상은 AI 가 만들었고 검수 전이다 — 게시 전에 한 번 보고, 본 만큼만 검수 표기를 단다.
- 미리보기(로컬 렌더 · GIF 270px): 검수 그림 브랜치 `claude/busy-lovelace-e073jj-public-shots` 의 `reels/`.

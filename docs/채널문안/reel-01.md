---
id: reel-01
channel: instagram
target: https://jisangj03-dev.github.io/incheon-port-analysis/tools/logistics-cost.html?utm_source=instagram&utm_medium=reel&utm_campaign=reel-01
status: 초안(2026-10-12) — 개편 공개 뒤 공개 주 묶음. 게시는 조타 콘텐츠 큐 PR 머지가 승인이다.
---
# reel-01 — 3PL 견적서, 안 적힌 칸 3개 (도구 시연형 · 18초)

> 영상 = `.github/workflows/reels.yml` 이 계산기 실사용 화면을 녹화해 Remotion 으로 9:16 편집(artifact `reels-N`). 장면·자막 정본 = `reels/reel-01.json`.
> 소리 없음(Edge TTS·배경음악 안 씀) · AI 생성 장면 없음 · 숫자는 전부 계산기의 **가상 예시**(실제 업체 견적 아님).
> 게시는 조타 콘텐츠 큐 PR 머지로만 — 이 파일은 초안이다. 홍보는 개편 공개 뒤(공개 주에 5~10편 묶음).

## 캡션 (인스타그램 · Threads · LinkedIn 공통)

견적 A가 건당 1,239원 싸 보여도, 견적서에 안 적힌 칸이 3개면 아직 모릅니다.

3PL 견적서에 잘 안 보이는 비용 4가지
① 수도광열비를 면적으로 나눠 받는 방식
② 폐기 부담금 같은 법적 비용
③ 세트 작업 같은 1회성 가공비
④ 유가에 연동되는 배송 요금

견적서 3장을 5칸에 옮기면 건당 총비용, 「모름」 칸 경고, 월 몇 건부터 어느 쪽이 싼지까지 한 화면에 나옵니다. 입력값은 서버로 가지 않습니다.

▶ 프로필 링크 — 측심 3PL 견적 비교 계산기
(영상 속 숫자는 가상 예시입니다. 실제 업체 견적이 아닙니다.)

## 링크
https://jisangj03-dev.github.io/incheon-port-analysis/tools/logistics-cost.html?utm_source=instagram&utm_medium=reel&utm_campaign=reel-01
(LinkedIn·Threads 는 utm_source 만 바꾼다 — 기준 30 측정)

## 사실 검증 — 숫자마다 출처
| 화면·캡션의 말 | 출처(저장소) |
|---|---|
| 건당 4,044 / 2,805 / 2,960원 | `tests/fixtures/cost-sample.json` expect.perUnit(엑셀 가상 샘플) |
| 견적 A 가 건당 1,239원 쌈 | `analysis/check_cost_tool.py` EXPECT diff = −1,239 |
| 안 적힌 칸 3개 | fixture expect.unknown = [0, 3, 0] |
| 모름 칸이 건당 155원을 넘으면 순위가 뒤집힘 | `check_cost_tool.py` C1 「뒤집히는 선 155원」 |
| 숨은 비용 4가지 | `assets/js/cost-check.js` HIDDEN — 3PL 운영 실무자 답신(2026-10-07)의 구조만 · 금액 없음 |
| 월 457건부터 A 가 B 보다 쌈(영상 화면) | `cost-check.js` crossings() — 같은 가상 예시 |

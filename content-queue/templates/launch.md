---
id: launch
state: 초안(게시 = 선장님 · 올리는 손은 채팅 · 이 파일은 어디에도 게시되지 않았다)
note: AI 초안 · 틀(숫자 0) — 숫자·해석 문장은 tools-build/drafts.py 가 data/derived/facts.json · data/claims.json 에서 채워 content-queue/live/launch.md 로 낸다. refresh 가 매 회 다시 만든다(갱신 무인화 ①). 게시 직전 live 판을 쓴다.
posts: li-12 linkedin LinkedIn | th-01 threads Threads | tb-01 tistory 블로그 | nl-01 beehiiv 뉴스레터
---

# 측심을 공개했습니다

## LinkedIn

인천에서 수도권까지, 물류·무역·유통을 숫자·지도·시뮬레이션으로 푸는 SCM 작업실 「측심」을 열었습니다. 3PL·풀필먼트, 수출입 담당·구매, 유통 MD·셀러가 일하면서 다시 열어 볼 도구를 공공 통계와 공개 지도로 만들었습니다.

{{gate.ym}} 금액 기준(관세청 항구·공항별 · 입·출항지 기준)으로 한국 수입의 {{gate.imp_share}}%가 인천 관문(인천공항 + 인천항)으로 들어오고, 수출은 {{gate.exp_share}}%가 인천에서 나갑니다. {{claim:gate.air_most.li}} — 인천 관문 수입 가운데 인천공항이 {{gate.air_imp}}억 달러, 인천항이 {{gate.port_imp}}억 달러입니다. 홈의 「최신 공표분으로 잰 숫자」 절 지도는 인천공항을 오간 나라별 항공화물 무게({{air.window}} 월평균 · 반기 공표분)를 흐름으로 그립니다. 공표 통계를 움직여 보인 것이라 실시간 위치는 아닙니다. 같은 달 한국 수입의 {{sudo.imp_share}}%는 수도권(서울·인천·경기)에 소재지를 둔 화주가 들여왔습니다(물건이 내린 곳이 아니라 화주 소재지 기준).

일하면서 다시 찾을 만한 도구도 같이 올렸습니다.
· 수입원가 계산기 — 관세청 주간 과세환율로 같은 물건의 원가를 다시 계산합니다({{cost.goods}} 달러 물건, {{cost.ago_weeks}}주 전보다 {{cost.pct}}%)
· 초크포인트 충격 — 호르무즈 해협 경유 나라와의 교역이 한국 수입의 {{choke.hormuz_imp}}%입니다
· 외항선 입항 추이 — {{vessel.ym}} 인천 외항선 입항 {{vessel.incheon}}척, 작년 같은 달보다 {{vessel.yoy}}%
· 품목 트리맵 레이스 — {{race.year}}년 관세청이 인천으로 집계한 업체 수출 1위 {{race.top_name}}의 몫 {{race.top_pct}}%
· 수도권 도달 등시선 — {{reach.origin}}에서 서울시청까지 승용차로 {{reach.seoul_car}}분({{reach.slot}} 시간대 · 평일 {{reach.slot_at}} 출발 기준)

지면마다 출처·기준일을 같은 화면에 두었고, 판정 기준을 먼저 적은 뒤 독립 판정을 거쳐 올렸습니다. 법률·세무·관세 자문은 아닙니다. 물동량·원가 계산을 귀사 숫자로 다시 돌려 보고 싶으시거나, 틀린 곳이 보이면 메일로 알려 주세요.

https://jisangj03-dev.github.io/incheon-port-analysis/

#물류 #SCM #인천 #공공데이터

## 블로그

제목: {{gate.ym}} 한국 수입의 {{gate.imp_share}}%가 인천으로 — 공공 통계로 다시 읽는 수도권 공급망

물류 실무에서는 「인천이 얼마나 큰 문인가」를 숫자 하나로 말해야 할 때가 있습니다. 감으로 답하기 쉬운 질문이라, 공공 통계로 직접 재 볼 수 있는 작업실을 따로 만들었습니다. 이름은 「측심」입니다. 물류·무역·유통 세 축으로 수도권 공급망을 숫자·지도·시뮬레이션으로 풉니다.

### 이번 달 숫자

- **관문** — {{gate.ym}} 금액 기준 한국 수입의 {{gate.imp_share}}%가 인천 관문(인천공항 + 인천항)으로 들어왔습니다. {{claim:gate.air_most.blog}}(인천공항 {{gate.air_imp}}억 달러 · 인천항 {{gate.port_imp}}억 달러). 관세청 항구·공항별 통계이고 입항지 기준입니다.
- **화주** — 같은 달 한국 수입의 {{sudo.imp_share}}%는 수도권(서울·인천·경기)에 소재지를 둔 화주가 들여왔습니다. 물건이 내린 곳이 아니라 관세청이 신고 업체를 시도로 나눈 기준입니다.
- **소매** — {{retail.ym}} 수도권 백화점·대형마트(대형소매점) 판매액은 {{retail.large_jo}}조 원으로 작년 같은 달보다 {{retail.large_yoy}}%, 같은 달 전국 온라인쇼핑 거래액은 {{retail.online_jo}}조 원({{retail.online_yoy}}%)입니다. 범위가 서로 달라(수도권 매장 · 전국 온라인) 두 숫자를 나눠 보지는 않았습니다. 출처는 국가통계포털(KOSIS)입니다.

### 열어 둔 것

실무 도구 {{site.n_tools}}개(수입원가 · 초크포인트 · 외항선 입항 추이 · 품목 트리맵 · 도달 등시선 · 채용·지원사업 레이더)와 시뮬레이션 {{site.n_sims}}개(맥주 게임 · 수요예측 실험실)가 있습니다. 예를 들어 수도권 도달 등시선에서는 {{reach.origin}}에서 서울시청까지 승용차로 {{reach.seoul_car}}분({{reach.slot}} 시간대 · 평일 {{reach.slot_at}} 출발)이 나옵니다.

### 어떻게 만들었나

관세청·해양수산부·인천국제공항공사·국가통계포털·OpenStreetMap 같은 공공 통계와 공개 지도를 씁니다(도달 시간 보정에는 카카오 길찾기를 대조용으로 썼습니다). 지면 숫자는 데이터 파일에 있는 값만 쓰고, 원천이 새 달을 내면 매일 아침 도는 자동 갱신이 시험을 통과한 숫자로 지면을 바꿉니다. 지면의 틀이나 문장을 바꿀 때는 판정 기준을 먼저 적고, 만든 맥락을 모르는 AI 심사관 둘(화면 · 원자료 대조)의 판정을 거칩니다. 법률·세무·관세 자문은 아닙니다. 이 글은 AI가 초안을 쓰고 숫자는 측심 데이터 파일에서 자동으로 채웠습니다.

출처와 기준일은 각 지면 아래에 있습니다.
https://jisangj03-dev.github.io/incheon-port-analysis/?utm_source=tistory&utm_medium=blog&utm_campaign=tb-01

— 물류로그

## 뉴스레터

제목: 물류로그 창간호 — 관문·화주·소매, 이번 달 숫자 셋

안녕하세요, 물류로그입니다. 공공 통계로 수도권 공급망을 재는 작업실 「측심」의 숫자가 새로 공표될 때 그 달의 요점만 짧게 보내 드리려고 합니다.

이번 달 숫자 셋입니다.

① 관문 — {{gate.ym}} 한국 수입의 {{gate.imp_share}}%가 인천 관문(인천공항 + 인천항)으로 들어왔습니다. {{claim:gate.air_most.li}}(관세청 항구·공항별 · 입항지 기준).
② 화주 — 같은 달 수입의 {{sudo.imp_share}}%는 수도권에 소재지를 둔 화주가 들여왔습니다(관세청 시도별 · 신고 업체 소재지 기준).
③ 소매 — {{retail.ym}} 수도권 백화점·대형마트 판매액 {{retail.large_jo}}조 원(작년 같은 달 {{retail.large_yoy}}%), 전국 온라인쇼핑 거래액 {{retail.online_jo}}조 원({{retail.online_yoy}}%)(국가통계포털 · 범위가 달라 서로 나누지 않습니다).

숫자마다 출처·정의·기준일은 측심 지면 아래에 적어 두었습니다. 틀린 곳이 보이면 이 메일에 답장 주세요. (이 메일은 AI가 초안을 쓰고 숫자는 측심 데이터 파일에서 자동으로 채웠습니다.)
https://jisangj03-dev.github.io/incheon-port-analysis/?utm_source=beehiiv&utm_medium=email&utm_campaign=nl-01

— 물류로그

## Threads

한국 수입의 {{gate.imp_share}}%가 인천 관문(인천공항 + 인천항)으로 들어옵니다({{gate.ym}} 금액 · 관세청 항구·공항별). {{claim:gate.air_most.th}}. 물류·무역·유통을 숫자·지도·시뮬레이션으로 푸는 SCM 작업실 「측심」을 열었습니다 — 수입원가·초크포인트·외항선·등시선 도구도 같이요.

https://jisangj03-dev.github.io/incheon-port-analysis/

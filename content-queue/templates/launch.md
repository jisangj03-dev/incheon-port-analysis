---
id: launch
state: 초안(게시 = 선장님 · 올리는 손은 채팅 · 이 파일은 어디에도 게시되지 않았다)
note: AI 초안 · 틀(숫자 0) — 숫자·해석 문장은 tools-build/drafts.py 가 data/derived/facts.json · data/claims.json 에서 채워 content-queue/live/launch.md 로 낸다. refresh 가 매 회 다시 만든다(갱신 무인화 ①). 게시 직전 live 판을 쓴다.
posts: li-12 linkedin LinkedIn | th-01 threads Threads
---

# 측심을 공개했습니다

## LinkedIn

인천에서 수도권까지, 물류·무역·유통을 숫자·지도·시뮬레이션으로 푸는 SCM 작업실 「측심」을 열었습니다. 3PL·풀필먼트, 수출입 담당·구매, 유통 MD·셀러가 일하면서 다시 열어 볼 도구를 공공 통계와 공개 지도로 만들었습니다.

{{gate.ym}} 금액 기준(관세청 항구·공항별 · 입·출항지 기준)으로 한국 수입의 {{gate.imp_share}}%가 인천 관문(인천공항 + 인천항)으로 들어오고, 수출은 {{gate.exp_share}}%가 인천에서 나갑니다. {{claim:gate.air_most.li}} — 인천 관문 수입 가운데 인천공항이 {{gate.air_imp}}억 달러, 인천항이 {{gate.port_imp}}억 달러입니다. 홈의 「최신 공표분으로 잰 숫자」 절 지도는 인천공항을 오간 나라별 항공화물 무게({{air.window}} 월평균 · 반기 공표분)를 흐름으로 그립니다. 공표 통계를 움직여 보인 것이라 실시간 위치는 아닙니다. 같은 달 한국 수입의 {{sudo.imp_share}}%는 수도권(서울·인천·경기)에 소재지를 둔 화주가 들여왔습니다(물건이 내린 곳이 아니라 화주 소재지 기준).

일하면서 다시 찾을 만한 도구 {{site.n_tools}}개도 같이 올렸습니다.
· 수입원가 계산기 — 관세청 주간 과세환율로 같은 물건의 원가를 다시 계산합니다({{cost.goods}} 달러 물건, {{cost.ago_weeks}}주 전보다 {{cost.pct}}%)
· 초크포인트 충격 — 호르무즈 해협 경유 나라와의 교역이 한국 수입의 {{choke.hormuz_imp}}%입니다
· 외항선 입항 추이 — {{vessel.ym}} 인천 외항선 입항 {{vessel.incheon}}척, 작년 같은 달보다 {{vessel.yoy}}%
· 품목 트리맵 레이스 — {{race.year}}년 관세청이 인천으로 집계한 업체 수출 1위 {{race.top_name}}의 몫 {{race.top_pct}}%
· 수도권 도달 등시선 — {{reach.origin}}에서 서울시청까지 승용차로 {{reach.seoul_car}}분({{reach.slot}} 시간대 · 평일 {{reach.slot_at}} 출발 기준)

지면마다 출처·기준일을 같은 화면에 두었고, 판정 기준을 먼저 적은 뒤 독립 판정을 거쳐 올렸습니다. 법률·세무·관세 자문은 아닙니다. 물동량·원가 계산을 귀사 숫자로 다시 돌려 보고 싶으시거나, 틀린 곳이 보이면 메일로 알려 주세요.

https://jisangj03-dev.github.io/incheon-port-analysis/

#물류 #SCM #인천 #공공데이터

## 블로그

제목안 — {{claim:gate.half.title}}, 공공 데이터로 읽기

측심은 인천에서 수도권까지, 물류·무역·유통을 숫자·지도·시뮬레이션으로 푸는 SCM 작업실입니다. {{gate.ym}} 금액 기준 한국 수입의 {{gate.imp_share}}%가 인천 관문으로 들어오고, {{claim:gate.air_most.blog}}(인천공항 {{gate.air_imp}}억 달러 · 인천항 {{gate.port_imp}}억 달러).

### 열어 둔 것
홈(누가 무엇을 얻는지 · 아래 「최신 공표분으로 잰 숫자」 절에 세 축 숫자와 관문 지도) · 실무 도구 {{site.n_tools}}개(수입원가 · 초크포인트 · 외항선 입항 추이 · 품목 트리맵 · 도달 등시선) · 연습용 시뮬레이션 {{site.n_sims}}개(맥주 게임 · 수요예측 실험실) · 노트.

### 어떻게 만들었나
관세청·해양수산부·인천국제공항공사·IMF PortWatch·OpenStreetMap 같은 공개 원천만 씁니다. 지면 숫자는 데이터 파일에 있는 값만 쓰고, 판정 기준을 먼저 커밋한 뒤 맥락 없는 심사관 둘(화면 · 원자료 대조)의 판정을 거쳐 올립니다. 기준에 못 미친 지면은 내렸습니다. 법률·세무·관세 자문이 아닙니다.

출처는 각 지면 아래에 있습니다 → https://jisangj03-dev.github.io/incheon-port-analysis/

## Threads

한국 수입의 {{gate.imp_share}}%가 인천 관문(인천공항 + 인천항)으로 들어옵니다({{gate.ym}} 금액 · 관세청 항구·공항별). {{claim:gate.air_most.th}}. 물류·무역·유통을 숫자·지도·시뮬레이션으로 푸는 SCM 작업실 「측심」을 열었습니다 — 수입원가·초크포인트·외항선·등시선 도구도 같이요.

https://jisangj03-dev.github.io/incheon-port-analysis/

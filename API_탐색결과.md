# 인천항만공사 물동량 API 탐색 결과 (2026-07-08)

## 핵심 구조
- 공통 경로: `https://apis.data.go.kr/B551504/ipaGtqyProcessAcmslt/{오퍼레이션}`
- 우리 인증키로 **이 서비스 폴더(ipaGtqyProcessAcmslt) 하나만** 호출 가능.
  다른 폴더명은 전부 HTTP 500(미승인/경로없음).
- 게이트웨이 응답 신호:
  - HTTP 500 `Unexpected errors` → 폴더(서비스) 자체가 우리 키에 없음
  - HTTP 404 `API not found` → 오퍼레이션 이름이 없음
  - HTTP 200 `resultCode=00` → 정상
  - HTTP 200 `resultCode=99 Invalid parameter` → 오퍼레이션은 있으나 요청 파라미터가 틀림

## 존재하는 오퍼레이션 3개 (실측)
| 오퍼레이션 | 상태 | 파라미터 | 반환 내용 | 수출입/환적 구분 |
|---|---|---|---|---|
| `getGtqyProcessAcmsltMnby` | ✅ 정상 | `yyyy` | 월별 **연안(coastal)** 물동량 12행 (톤 추정) | ❌ 연안만 나옴 |
| `getAllFrghtGtqyMnthng` | ✅ 정상 | `yyyy` (+`mm`?) | **전체 화물 물동량** 총계, 최신 1개월만 반환 | ❌ 총량만, 방향 없음 |
| `getCntanrLandngLoading` | ⚠️ 파라미터 미상 | 미상(rc=99) | 컨테이너 **양/적하** 추정 | 미확인(가능성 있음) |

### getGtqyProcessAcmsltMnby 필드
`ym, inoutgbnm(=연안), selYearSelMonth(당월), selYear(누적), preYearSelMonth(전년동월), preYear(전년누적)` 등.
구분 파라미터(inoutGbn/ioGbn/gbn 등) 다수 시도 → 전부 무시되고 연안만 반환.

### getAllFrghtGtqyMnthng 필드
`yyyy, mm, sumToday(당월), sumPre(전월), sumVsslTot, sumPreTot, rate...`
yyyy=2023 단독 호출 시 mm=11 한 행만 옴(최신월 스냅샷).

### getCntanrLandngLoading
날짜/기간/터미널/구분 계열 파라미터 30여 종 시도 → 전부 rc=99.
→ data.go.kr 활용가이드(참고문서)에서 정확한 요청변수명 확인 필요.

## 결론
현재 승인된 3개 오퍼레이션 중 **월별 수출입/환적 컨테이너 물동량**을 그대로 주는 것은 없음.
- `getCntanrLandngLoading`가 유일한 컨테이너 레벨 → 요청변수만 확보하면 가장 유망.
- 확실한 수출입/환적 TEU가 필요하면 컨테이너 전용 데이터셋 추가 활용신청 검토:
  - data.go.kr 15003936 (인천항 컨테이너 정보)
  - data.go.kr 15130235 (인천항 공컨테이너 화물 통계) — 월별 수출입 구분·TEU 포함으로 알려짐

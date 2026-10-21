# IMF PortWatch 이용 문의 — 초안 (2026-10-21)

> **보내는 것은 선장님 몫(외부 발송).** 채팅이 나중에 넘긴다. 급하지 않다 — 지금은 사업 문의 동선을 초크포인트 지면에서 떼어 위험을 없앤 상태다(`data/sources.json` imf-portwatch · `tests/license.spec.mjs`).
> 실명·메일은 저장소에 두지 않는다 — 보낼 때 `data/profile.json` 에서 채운다(〈실명〉 · 〈소속〉 · 〈회신 메일〉).
> 받는 곳 [미확인]: PortWatch 사이트의 문의 경로(About/Contact)나 IMF 저작권 문의처 — 보내기 전에 사이트에서 확인한다(이 세션은 imf.org 약관 본문을 못 읽었다 · terms-check 추출 0자).

## 무엇을 묻나 (한 줄)

비영리 개인 사이트가 PortWatch 초크포인트 일별 통항을 가공·표시하는 지금 방식이 약관 안인지, 그리고 같은 사이트에 개인 분석 문의 창구(유료 가능성)가 있을 때 별도 허락이 필요한지.

## 영문 본문

Subject: Permission inquiry — use of IMF PortWatch chokepoint transit data on a personal analysis site

Dear PortWatch team,

I run a small personal website, "측심 (Sounding)", that explains how the Seoul metropolitan supply chain passes through the port and airport of Incheon, Korea, using public primary data. One page ("Chokepoint shock") uses the IMF PortWatch Daily Chokepoints Data:

- what we use: daily transit counts for Hormuz, Red Sea/Bab-el-Mandeb, Malacca and Taiwan Strait, which we average over 28 days and compare with the same month of 2023;
- how it is shown: as a derived figure and a weekly chart, labelled "IMF PortWatch (AIS-based estimate)", with a link to portwatch.imf.org and a CSV of the derived values;
- what we do not do: we do not redistribute the raw daily files, sell the data, or place advertising on the site.

Two questions:

1. Is this display, which is attributed and derived, permitted under the IMF terms for PortWatch data?
2. The site also lists contact details for people who want a similar analysis run on their own company figures, and such work could be paid. We have removed that contact link from the PortWatch page for now. Would using PortWatch-derived figures in that kind of work, or keeping the link on the page, require separate permission? If so, how should we request it?

If you prefer different attribution wording, we will change it.

Thank you,
〈실명〉 · 〈소속〉
〈회신 메일〉
Site: https://jisangj03-dev.github.io/incheon-port-analysis/tools/chokepoint.html

## 답을 받으면

- 허락(또는 「약관 안」) → `data/sources.json` imf-portwatch 의 `commercial` 을 고치고 `tests/license.spec.mjs` 의 대상에서 뺀 뒤, 초크포인트 지면의 `ask={false}` 를 되돌린다(같은 PR · 독립 판정).
- 거절 또는 조건부 → 조건을 대장에 적고 지면은 지금처럼 둔다.

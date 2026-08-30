# -*- coding: utf-8 -*-
"""프로브 14 — **공컨 API 의 시작 경계를 아래에서 친다.**

왜 있는가
---------
`STATUS.md` 가 장기 시계열을 이렇게 닫아 뒀다 — **「원천이 2022~다. 설계 문제가 아니라
자료 문제」.** 부산항만공사가 2010년부터 내는 것을 보고 우리는 못 한다고 적은 자리다.

**그런데 그것이 확인된 적이 없다.** `probe_02b_range.py` 는 **2022~2026 만** 쳤다.
2022 가 시작이라는 것은 **거기서부터 봤기 때문**이지 아래를 쳐 본 결과가 아니다.

  · 사고 58 — 「지도를 못 그린다」가 사실은 **「출처를 안 찾았다」**였다.
  · 사고 63 — 「추정하지 말라」가 **「아무것도 하지 말라」**로 굳어 있었다.

**같은 얼굴이 세 번째다.** 「자료가 없다」와 「없는지 안 봤다」는 다른 말이고,
그 둘을 한 문장에 적어 두면 다음 사람은 앞엣것으로 읽는다.

이 프로브가 하는 일 / 안 하는 일
--------------------------------
**존재 여부와 월 목록만 본다.** 값을 계산하지 않고 파일로 저장하지도 않는다 —
선커밋 규율(§3-7) 때문이다. **데이터를 보면 그 구간으로 선커밋 편을 못 연다.**
그래서 여기서 보는 것은 「행이 있는가 · 몇 월이 있는가」뿐이고, 숫자는 안 읽는다.

**실패를 「실패」로 세지 않는다**(사고 61). 인증 실패 · 파라미터 오류 · 데이터 없음은
서로 다른 사실이고, 그것을 안 가르면 **「자료가 없다」와 「우리가 잘못 물었다」가 섞인다.**
그래서 판정을 넷으로 가른다 — 있음 / 없음 / 물음이 틀림 / 모름.

**0 패딩을 지킨다.** `searchStartM="1"` 로 넣으면 API 가 10·11·12월만 준다
(`probe_02b_range.py` 가 2026-07-13에 겪은 함정). 이 프로브도 같은 함정에 걸리면
「그 해에는 3개월만 있다」는 거짓을 낼 수 있다.

  python analysis/probe/probe_14_year_floor.py
  python analysis/probe/probe_14_year_floor.py --selftest   # 망 없이 판정 논리만
"""

import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ANALYSIS = os.path.dirname(HERE)
sys.path.insert(0, ANALYSIS)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

URL = "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo"

# 아래로 내려가며 친다. 2022 는 **대조군**이다 — 그 해가 「있음」으로 나와야
# 이 프로브가 제대로 물어보고 있다는 뜻이다(사고 61: 대조군이 단계를 갈라 준다).
# [2026-08-30 1차 실측] 2015~2021 이 **전부 12개월 다 있었다.** 바닥이 더 아래라는 뜻이라
# 끝까지 내려간다. **「있음」에서 멈추면 그 자리가 또 「거기서부터 봤기 때문」이 된다.**
YEARS = tuple(range(2022, 2004, -1))

HAVE, NONE, ASKBAD, UNK = "있음", "없음", "**물음이 틀림**", "**모름**"

# 공공데이터포털이 인증 단계에서 내는 코드 — 이 경우는 「자료 없음」이 아니다.
AUTH_CODES = {"20", "22", "30", "31", "32"}


def classify(rc, total, months, err=None, years=None, want=None):
    """판정 넷. **「실패」를 한 덩어리로 세지 않는다**(사고 61).

    반환 (판정, 사유). 인증·파라미터에서 막힌 것을 「자료 없음」으로 세면
    **없는 것과 못 물어본 것이 섞인다.**
    """
    if err is not None:
        return UNK, err
    if rc is None:
        return UNK, "응답에 resultCode 가 없다"
    if rc in AUTH_CODES:
        return ASKBAD, "인증·권한 단계에서 막혔다 (rc=%s)" % rc
    if rc != "00":
        return ASKBAD, "정상 코드가 아니다 (rc=%s)" % rc
    if months:
        # **응답이 다른 해를 주고 있으면 「있음」이 아니다.** 물음이 안 먹은 것이다.
        if years and want is not None and [str(want)] != list(years):
            return ASKBAD, ("응답의 연도가 %s 다 — 요청은 %s. **연도 파라미터가 안 먹는다**"
                            % (years, want))
        return HAVE, "월 %s" % months
    # rc=00 인데 행이 없다 — **이것이 진짜 「그 해 자료가 없다」**이다.
    return NONE, "정상 응답인데 행이 0 (totalCount=%s)" % total


def call_year(year, session=None):
    import requests
    from config import SERVICE_KEY
    params = {"serviceKey": SERVICE_KEY, "searchYear": str(year),
              # **0 패딩을 지킨다.** "1" 로 넣으면 10·11·12월만 온다.
              "searchStartM": "01", "searchEndM": "12",
              "numOfRows": "300", "pageNo": "1"}
    get = (session or requests).get
    r = get(URL, params=params, timeout=25)
    root = ET.fromstring(r.content)
    rc = root.findtext(".//resultCode")
    total = root.findtext(".//totalCount")
    items = root.findall(".//item")
    months = sorted({int(it.findtext("mm")) for it in items if it.findtext("mm")})
    # **응답이 실제로 그 해인지 본다.** `yyyy` 는 값이 아니라 좌표라 읽어도 §3-7 에
    # 걸리지 않는다 — 그리고 이걸 안 보면 「연도를 무시하고 최근 것을 준 것」과
    # 「그 해 자료가 있는 것」이 구분되지 않는다.
    years = sorted({it.findtext("yyyy") for it in items if it.findtext("yyyy")})
    return rc, total, months, years


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 실패를 한 덩어리로 세지 않는가 (사고 61) ──")
    chk("행이 있으면 있음", classify("00", "60", [1, 2, 3])[0], HAVE)
    chk("정상인데 행 0 이면 없음", classify("00", "0", [])[0], NONE)
    chk("인증에서 막히면 물음이 틀림", classify("30", None, [])[0], ASKBAD)
    chk("다른 오류도 물음이 틀림", classify("99", None, [])[0], ASKBAD)
    chk("망이 안 되면 모름", classify(None, None, [], err="Timeout")[0], UNK)
    chk("코드가 없어도 모름", classify(None, "0", [])[0], UNK)
    # **인증 실패를 「자료 없음」으로 세지 않는다** — 이 둘을 섞으면 결론이 뒤집힌다.
    chk("인증 실패는 없음이 아니다", classify("30", None, [])[0] == NONE, False)

    print("── 인수시험: 응답이 다른 해면 「있음」이 아니다 ──")
    chk("요청 연도와 응답 연도가 같으면 있음",
        classify("00", "60", [1], years=["2020"], want=2020)[0], HAVE)
    chk("응답이 다른 해면 물음이 틀림",
        classify("00", "60", [1], years=["2026"], want=2020)[0], ASKBAD)
    chk("여러 해가 섞여 와도 물음이 틀림",
        classify("00", "60", [1], years=["2025", "2026"], want=2020)[0], ASKBAD)

    print("── 인수시험: 0 패딩 규율 ──")
    src = open(__file__, encoding="utf-8").read()
    chk('searchStartM 을 "01" 로 넣는다', '"searchStartM": "01"' in src, True)
    chk("대조군 연도가 목록에 있다", 2022 in YEARS, True)
    chk("2022 아래를 친다", min(YEARS) < 2022, True)

    print("── 인수시험: 값을 안 읽는다 (§3-7) ──")
    # 이 프로브는 **존재 여부만** 본다. 값을 읽으면 그 구간으로 선커밋 편을 못 연다.
    for tag in ("forEmpTeu", "korEmpTeu", "to_csv", "DataFrame"):
        chk("%s 를 안 쓴다" % tag, tag in src.replace('"%s"' % tag, ""), False)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()

    try:
        import requests  # noqa: F401
        from config import SERVICE_KEY  # noqa: F401
    except Exception as e:
        print("[중단] %s: %s" % (type(e).__name__, e))
        print("  **모름으로 남는다** — 못 돌린 것을 「자료 없음」으로 세지 않는다(사고 26).")
        return 2

    print("=" * 70)
    print(" 프로브 14 — 공컨 API 시작 경계를 **아래에서** 친다")
    print(" 존재 여부·월 목록만 본다. 값은 안 읽는다(§3-7).")
    print("=" * 70)

    rows = []
    for y in YEARS:
        try:
            rc, total, months, years = call_year(y)
            verdict, why = classify(rc, total, months, years=years, want=y)
        except Exception as e:
            verdict, why = classify(None, None, [], err="%s: %s" % (type(e).__name__, e))
        rows.append((y, verdict, why))
        print("  %d  %-14s %s" % (y, verdict, why))

    # ── 아래쪽 대조군 ────────────────────────────────────────────────
    # **있을 수 없는 해를 친다.** 여기서 「있음」이 나오면 API 가 연도를 안 보는 것이고,
    # 그러면 위의 「2005년에도 있다」는 전부 무효다.
    # 대조군을 한쪽에만 세우면 대조가 안 된다 — 위(2022)와 아래(1990) 둘 다 필요하다.
    print("-" * 70)
    print(" [아래쪽 대조군] 있을 수 없는 해로 같은 물음을 친다")
    floor_ok = None
    for probe_y in (1990, 1970):
        try:
            rc, total, months, years = call_year(probe_y)
            v, w = classify(rc, total, months, years=years, want=probe_y)
        except Exception as e:
            v, w = classify(None, None, [], err="%s: %s" % (type(e).__name__, e))
        print("  %d  %-14s %s" % (probe_y, v, w))
        if v == HAVE:
            floor_ok = False
        elif floor_ok is None:
            floor_ok = True

    if floor_ok is False:
        print()
        print(" **연도 파라미터가 안 먹는다.** 있을 수 없는 해에도 자료가 왔다 —")
        print(" 그러므로 위의 결과는 **「그 해에 자료가 있다」가 아니다.** 전부 무효로 읽는다.")
        print(" (사고 61 — 대조군은 단계를 가를 때만 대조군이다.)")
        return 1
    if floor_ok is None:
        print()
        print(" **아래쪽 대조군을 못 쳤다.** 위 결과의 신뢰도를 여기서 확정할 수 없다 —")
        print(" **모름으로 남긴다**(사고 26).")
        return 1

    print(" -> 있을 수 없는 해에는 자료가 없다. **연도 파라미터가 먹는다.**")
    print("-" * 70)
    ctrl = [r for r in rows if r[0] == 2022]
    if ctrl and ctrl[0][1] != HAVE:
        print(" **대조군 2022 가 「있음」이 아니다.** 이 프로브가 제대로 물어보고 있지 않다 —")
        print(" 아래 결과를 「자료가 없다」로 읽으면 안 된다(사고 61).")
        return 1

    have = [r[0] for r in rows if r[1] == HAVE]
    none = [r[0] for r in rows if r[1] == NONE]
    bad = [r for r in rows if r[1] in (ASKBAD, UNK)]
    if have:
        print(" 있음: %s" % ", ".join(str(y) for y in sorted(have)))
    if none:
        print(" 없음: %s" % ", ".join(str(y) for y in sorted(none)))
    if bad:
        print(" **판별 못 함**: %s" % ", ".join("%d(%s)" % (y, v) for y, v, _ in bad))
        print(" 판별 못 한 해는 **「없다」로 세지 않는다.**")
    below = [y for y in have if y < 2022]
    print()
    if below:
        print(" ▶ **2022 아래에도 자료가 있다: %s**" % ", ".join(str(y) for y in sorted(below)))
        print("   STATUS 의 「원천이 2022~다」는 **틀렸다.** 다년 축이 그만큼 넓어진다.")
        print("   **다만 이 프로브는 값을 안 읽었다** — 수집은 별도이고,")
        print("   선커밋 편을 열려면 **아직 안 본 구간에 질문 3개를 먼저 커밋**해야 한다(§3-7).")
    elif none and not bad:
        print(" ▶ **2022 가 실제 시작 경계다.** 아래는 정상 응답에 행이 0 이었다.")
        print("   「자료 문제」라는 기록이 이제 **확인된 사실**이 된다 — 종전에는 추정이었다.")
    else:
        print(" ▶ **경계를 확정하지 못했다.** 위 「판별 못 함」을 보라.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

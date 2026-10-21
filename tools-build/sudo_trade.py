"""수도권 무역·유통 축(2026-10-21 선장님 과제 1 「수도권의 물류·무역·유통을 한 번에」) — 관세청 시도별 품목별 수출입실적(공공데이터포털 15101641)을
시도마다 · 달마다 받아 쌓는다. 인천만 받던 것(collect.json sido-item-incheon)을 수도권(서울 11 · 인천 28 · 경기 41)과 전국 분모로 넓힌다.
  - 수도권 세 시도 = 품목(HS 2단위)까지 · 나머지 시도 = 총계 한 줄만(전국 분모 = 시도 합).
  - 시도 코드는 고정 목록을 「시험」한다 — 행정 개편으로 코드가 바뀌면(2026-07 인천 사례) 빈 응답이 기록에 남는다(codes_seen).
  - 시도 코드 없이 묻는 판도 한 번 시험한다(nosido) — 전국 총계를 주면 분모 대조에 쓴다.
쌓기: 이미 받은 달은 다시 받지 않는다 — 마지막 두 달만 다시(수정 공표). 처음에는 13달(전년 같은 달 대조).
금액 = 천 달러(원천 그대로). 키 = DATA_GO_KR_KEY — 로그·산출물에 찍지 않는다(common.scrub). Actions 에서만 돈다(사고 120).
  python tools-build/sudo_trade.py [--months 13]
  python tools-build/sudo_trade.py --selftest
"""
import datetime, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "v3"))

OUT = "data/collected/v3/sudo_trade.json"
URL = "https://apis.data.go.kr/1220000/sidoitemtrade/getSidoitemtradeList"
SUDO = {"11": "서울", "28": "인천", "41": "경기"}
# 관세청 조회코드표의 시도 — 개편으로 바뀐 코드는 빈 응답으로 드러난다(codes_seen 에 남는다)
OTHERS = ["26", "27", "29", "30", "31", "36", "42", "43", "44", "45", "46", "47", "48", "50", "51", "52"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def num(v):
    try: return float(str(v).replace(",", "").strip() or 0)
    except ValueError: return 0.0


def fold(rows, detail):
    """응답 행 → {tot: {imp, exp}, hs: {HS2: {imp, exp, name}}}. 총계 줄은 priodTitle=총계(hsSgn 없음)."""
    tot, hs = None, {}
    for r in rows:
        h = (r.get("hsSgn") or "").strip()
        imp, exp = num(r.get("impUsdAmt")), num(r.get("expUsdAmt"))
        if not h and (r.get("priodTitle") or "").strip() == "총계": tot = {"imp": imp, "exp": exp}
        elif h: hs[h[:2]] = {"imp": imp, "exp": exp, "name": (r.get("korePrlstNm") or "").strip()}
    if tot is None and hs: tot = {"imp": sum(v["imp"] for v in hs.values()), "exp": sum(v["exp"] for v in hs.values())}
    return {"tot": tot, **({"hs": hs} if detail else {})}


def months_upto(last, n):
    out, d = [], last
    for _ in range(n): out.append(d.strftime("%Y%m")); d = (d - datetime.timedelta(days=1)).replace(day=1)
    return sorted(out)


def fetch(ym, sido, tries=4):
    from common import KEY, get, scrub
    from collect import parse
    p = {"serviceKey": KEY, "strtYymm": ym, "endYymm": ym}
    if sido: p["sidoCd"] = sido
    for k in range(tries):  # 포털이 연결을 끊는 일이 잦다(kr_apis 실측) — 쉬었다 다시
        st, b = get(URL, p, timeout=60, tries=2)
        rc, msg, rows = parse(scrub(b))
        if rows: return st, rc, rows
        time.sleep(3 * (k + 1))
    return st, rc, []


def run(n):
    from common import write, say
    from kr_apis import last_month
    p = os.path.join(ROOT, OUT)
    old = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"months": {}}
    M = old.get("months", {})
    last = last_month()
    want = months_upto(last, n)
    redo = set(want[-2:])  # 마지막 두 달은 다시(수정 공표)
    seen = old.get("codes_seen", {})
    got, dead = 0, set()
    for ym in want:
        if ym in M and ym not in redo and all(c in M[ym] for c in SUDO): continue
        rec = {}
        for c in list(SUDO) + OTHERS:
            if c in dead: continue  # 이번 실행에서 이미 빈 코드(개편으로 없어진 코드) — 달마다 다시 기다리지 않는다
            st, rc, rows = fetch(ym, c, 4 if c in SUDO else 2)
            seen[c] = {"last_try": ym, "rows": len(rows), "resultCode": rc}
            if rows: rec[c] = fold(rows, c in SUDO)
            elif c not in SUDO and str(st) == "200": dead.add(c)
        st, rc, rows = fetch(ym, None, 1)  # 시도 코드 없이 — 전국 총계를 주는지
        if rows: rec["nosido"] = fold(rows, False)
        if all(c in rec for c in SUDO):
            M[ym] = rec; got += 1
            say(ym, "시도", len([c for c in rec if c != "nosido"]), "· 수도권 수입(천 달러)", int(sum(rec[c]["tot"]["imp"] for c in SUDO)))
        else:
            say(ym, "수도권 시도 빈 응답 — 이 달은 지난 기록 유지")
    keep = {ym: M[ym] for ym in sorted(M) if ym >= want[0]}
    if not keep or not all(ym in keep for ym in want[-1:]):
        say("마지막 달", want[-1], "을 못 받았다 — 덮어쓰지 않는다"); return 1
    write(OUT, {"source": "관세청 시도별 품목별 수출입실적(공공데이터포털 15101641 · 1220000/sidoitemtrade) · 시도 = 신고인(화주) 소재지 · 금액 = 천 달러",
                "fetched": datetime.date.today().isoformat(), "sudo": SUDO, "codes_seen": seen, "months": keep})
    say("수도권 시도별", len(keep), "달 · 새로 받음", got)
    return 0


def selftest():
    rows = [{"priodTitle": "총계", "impUsdAmt": " 18,992,473", "expUsdAmt": "6,126,630"},
            {"priodTitle": "2026", "hsSgn": "01", "impUsdAmt": "122", "expUsdAmt": "50", "korePrlstNm": "살아 있는 동물"}]
    f = fold(rows, True)
    assert f["tot"] == {"imp": 18992473.0, "exp": 6126630.0} and f["hs"]["01"]["imp"] == 122.0, f
    assert fold(rows, False) == {"tot": {"imp": 18992473.0, "exp": 6126630.0}}
    assert fold(rows[1:], False)["tot"]["imp"] == 122.0  # 총계 줄이 없으면 품목 합
    assert months_upto(datetime.date(2026, 9, 1), 13)[0] == "202509" and months_upto(datetime.date(2026, 1, 1), 2) == ["202512", "202601"]
    print("selftest 4/4 ok"); return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv: sys.exit(selftest())
    n = int(sys.argv[sys.argv.index("--months") + 1]) if "--months" in sys.argv else 13
    sys.exit(run(n))

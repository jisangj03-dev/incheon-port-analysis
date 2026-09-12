# -*- coding: utf-8 -*-
"""#11 판정 — 항 전체에서 터미널 층으로 내려간다.

**선커밋 `docs/11_주제검증.md`(blob `e8789fb0311ef6b804f23459c3373a0217805373`)의 기준으로만
판정한다.** 이 파일은 기준을 해석하지 않는다 — T1~T4 와 게이트 여섯을 그대로 옮긴 것뿐이다.

  python analysis/judge_11_terminal.py            # 판정
  python analysis/judge_11_terminal.py --selftest

무엇을 보나
-----------
· 물동량 `terminal_monthly.csv` — 2025-10~2026-07 · 10개월 · 계층 합계/부두군/터미널
· 부두 제원 `port_container_berths.csv` — 안벽 길이 m
· 출처 대장 `terminal_monthly_sources.csv` — 소스 실재(게이트 1)

닿지 않는 곳
------------
· **인과를 안 낸다.** 왜 그런 값인지는 이 데이터에 없다(선커밋 표기 규칙).
· **안벽 1m당 처리량은 「효율」이 아니다** — 선석 수·장비·선형·운영 시간이 전부 빠져 있다.
  이 파일이 내는 것은 **1m당 천TEU 와 그 순위**뿐이다.
· **판정 불가를 통과에도 미성립에도 안 넣는다**(사고 26·77). 「검사 M」을 늘 같이 낸다.
· **2026 구간은 잠정치다**(§4). 이 파일은 값을 그대로 내고, 지위는 결론 문서가 적는다.
"""
import argparse
import collections
import csv
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MONTHLY = os.path.join(HERE, "terminal_monthly.csv")
BERTHS = os.path.join(HERE, "port_container_berths.csv")
SOURCES = os.path.join(HERE, "terminal_monthly_sources.csv")

PRECOMMIT = "e8789fb0311ef6b804f23459c3373a0217805373"
# 부두현황의 `주요취급화물` — **어긋남을 설명하는 것이 원문 안에 있다.**
# SICT 는 `- (폐쇄)` 다. 이름 집합이 다른 것은 표가 틀려서가 아니라 그 부두가 닫혀서다.
# **그 사실을 코드가 들고 다닌다** — 다음 세션이 다시 캐지 않도록(FACTS 「SICT」 행도 같은 말을 든다).
CARGO = {}
GROUPS = ("신항", "남항", "국제여객부두")   # T1 이 요구하는 순서
SHARE_FLOOR = 50.0                          # T2 — 선언값이다(관측 최소가 아니다)
T3_MIN_MONTHS = 6                           # T3 — 10개월 중


def rd(path):
    return list(csv.DictReader(io.open(path, encoding="utf-8-sig", newline="")))


def num(s):
    s = (s or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def sign(v):
    """양(+) · 음(-) · 영(0). **0 은 양에도 음에도 안 넣는다**(선커밋 T3)."""
    if v is None:
        return None
    return "+" if v > 0 else "-" if v < 0 else "0"


def load():
    rows = rd(MONTHLY)
    months = sorted({r["기준연월"] for r in rows})
    total, group, term = {}, collections.defaultdict(dict), collections.defaultdict(dict)
    yoy_total, yoy_term = {}, collections.defaultdict(dict)
    for r in rows:
        m, lay = r["기준연월"], r["계층"]
        v, y = num(r["당월_천TEU"]), num(r["전년대비_당월_%"])
        if lay == "합계":
            total[m], yoy_total[m] = v, y
        elif lay == "부두군":
            group[m][r["부두군"]] = v
        elif lay == "터미널":
            term[m][r["터미널"]] = v
            yoy_term[m][r["터미널"]] = y
    # 국제여객부두는 소계 행이 없다 — 터미널 IPT 가 그 자체로 한 칸이다(FACTS 68).
    for m in months:
        if "국제여객부두" not in group[m] and "IPT" in term[m]:
            group[m]["국제여객부두"] = term[m]["IPT"]
    berth = collections.defaultdict(float)
    for r in rd(BERTHS):
        berth[r["명칭"]] += num(r["부두길이_m"]) or 0.0
        CARGO.setdefault(r["명칭"], (r.get("주요취급화물") or "").strip())
    return months, total, dict(group), dict(term), yoy_total, dict(yoy_term), dict(berth)


def gates(months, total, group, term, berth):
    """반환 (정지 사유 목록, 기록 목록). **정지 사유가 있으면 판정에 안 간다.**"""
    stop, notes = [], []

    # 1. 소스 실재
    src = rd(SOURCES)
    smonths = {r["기준연월"] for r in src}
    missing_sha = [r["기준연월"] for r in src if not (r.get("SHA256_앞16") or "").strip()]
    if smonths != set(months):
        stop.append("게이트1 — 출처 대장의 달 %s 가 물동량 표의 달 %s 와 다르다"
                    % (sorted(smonths), months))
    if missing_sha:
        stop.append("게이트1 — SHA256 이 빈 달: %s" % missing_sha)
    notes.append("게이트1 통과 — 출처 대장 %d달 · SHA256 전부 있음" % len(src))

    # 2. 완전성
    for m in months:
        if total.get(m) is None:
            stop.append("게이트2 — %s 에 계층 `합계` 가 없다" % m)
        if len([g for g in group.get(m, {}) if g in ("신항", "남항")]) < 2:
            stop.append("게이트2 — %s 의 부두군 행이 2 미만" % m)
        if len(term.get(m, {})) != 5:
            stop.append("게이트2 — %s 의 터미널 행이 %d (5 여야 한다)" % (m, len(term.get(m, {}))))
    if not stop:
        notes.append("게이트2 통과 — 10개월 각각 합계 1 · 부두군 2 · 터미널 5")

    # 3. 결합 게이트 — 이름 대응. **정지하지 않는다**(선커밋 게이트 3)
    names_flow = set().union(*[set(term[m]) for m in months]) if months else set()
    names_berth = set(berth)
    matched = sorted(names_flow & names_berth)
    only_flow = sorted(names_flow - names_berth)
    only_berth = sorted(names_berth - names_flow)
    why = ["%s(%s)" % (t, CARGO.get(t) or "취급화물 표시 없음") for t in only_berth]
    notes.append("게이트3 — 대응 %d곳 %s · 물동량에만 %s · 부두현황에만 %s"
                 % (len(matched), matched, only_flow, why))

    # 4. 분모 0·부재
    zero_total = [m for m in months if not total.get(m)]
    no_len = [t for t in matched if not berth.get(t)]
    if zero_total:
        notes.append("게이트4 — 공표 합계가 0/부재인 달(T1·T2 판정 불가): %s" % zero_total)
    if no_len:
        notes.append("게이트4 — 안벽 길이가 없는 터미널(T4 판정 불가): %s" % no_len)

    # 5. 항등식 — 무결성 확인이지 결론 근거가 아니다
    diffs = []
    for m in months:
        s = sum(v for v in term[m].values() if v is not None)
        if total.get(m) is not None:
            diffs.append((m, s - total[m]))
    notes.append("게이트5 — 다섯 곳 합 − 공표 합계: %s"
                 % ", ".join("%s %+g" % (m, d) for m, d in diffs))
    return stop, notes, matched, only_flow, only_berth, zero_total


def judge():
    months, total, group, term, yoy_total, yoy_term, berth = load()
    stop, notes, matched, only_flow, only_berth, zero_total = gates(
        months, total, group, term, berth)
    out = {"months": months, "notes": notes, "stop": stop, "matched": matched,
           "only_flow": only_flow, "only_berth": only_berth}
    if stop:
        return out

    judged = [m for m in months if m not in zero_total]

    # T1 — 몫 순위 신항 > 남항 > 국제여객부두
    shares, t1_bad = {}, []
    for m in judged:
        shares[m] = {g: (group[m].get(g) or 0.0) / total[m] * 100.0 for g in GROUPS}
        s = shares[m]
        if not (s["신항"] > s["남항"] > s["국제여객부두"]):
            t1_bad.append(m)
    out["T1"] = {"성립": len(judged) - len(t1_bad), "검사": len(judged),
                 "미성립": t1_bad, "판정": "PASS" if not t1_bad else "FAIL"}
    out["shares"] = shares

    # T2 — 신항 몫 ≥ 50.0
    t2_bad = [m for m in judged if shares[m]["신항"] < SHARE_FLOOR]
    out["T2"] = {"성립": len(judged) - len(t2_bad), "검사": len(judged),
                 "미성립": t2_bad, "판정": "PASS" if not t2_bad else "FAIL"}

    # T3 — 합계 부호와 터미널 다섯 부호가 모두 같은 달이 6개월 이상
    signs, agree, agree5 = {}, [], []
    for m in months:
        row = {"합계": sign(yoy_total.get(m))}
        for t in sorted(term[m]):
            row[t] = sign(yoy_term[m].get(t))
        signs[m] = row
        vals = list(row.values())
        if None not in vals and len(set(vals)) == 1:
            agree.append(m)
        five = [v for k, v in row.items() if k != "합계"]
        if None not in five and len(set(five)) == 1:
            agree5.append(m)
    # **기준의 사전 난이도** — 판정에 안 쓴다. T2 의 「선언값」과 같은 자리의 자기비판이다.
    # 부호가 서로 무관하고 +/− 가 반반이라면 **터미널 다섯이 모두 같을 확률**은 2·(1/2)^5.
    # **합계는 동전으로 안 센다** — 다섯의 합이라 독립이 아니다. 여섯 조건 ≈ 다섯 조건이고,
    # 이 창에서는 `동행`(여섯)과 `다섯만 동행`이 실제로 같은 수다.
    n_terms = max(len(signs[m]) - 1 for m in months) if months else 0
    p_null = 2 * (0.5 ** n_terms) if n_terms else 0.0
    out["T3"] = {"동행": len(agree), "검사": len(months), "기준": T3_MIN_MONTHS,
                 "동행한 달": agree,
                 "다섯만 동행": len(agree5),
                 "귀무확률": p_null, "귀무기대": p_null * len(months),
                 "판정": "PASS" if len(agree) >= T3_MIN_MONTHS else "FAIL"}
    # **[2026-09-13 정정] 이 수를 손으로 셌다가 발행본에 틀리게 나갔다**(사고 117).
    # 「합계 부호가 6번 바뀐다」로 적었는데 **바뀐 횟수는 5이고 구간(런)이 6**이다.
    # **판정에 안 쓰는 참고 통계여도 사람이 나르면 안 된다**(§3 — 수치는 사람이 나르지 않는다).
    # 그래서 코드가 센다. 인수시험이 두 값을 고정한다.
    tseq = [signs[m]["합계"] for m in months]
    flips = sum(1 for a, b in zip(tseq, tseq[1:]) if a != b)
    out["합계부호"] = {"차례": tseq, "바뀐 횟수": flips, "구간 수": flips + 1}
    out["signs"] = signs

    # T4 — 안벽 1m당 처리량 순위 지속 (대응되는 터미널만)
    if len(matched) < 2:
        out["T4"] = {"판정": "판정 불가", "사유": "대응 터미널 %d곳" % len(matched)}
    else:
        perm, orders = {}, []
        for m in months:
            p = {t: (term[m].get(t) or 0.0) / berth[t] for t in matched if berth.get(t)}
            perm[m] = p
            orders.append(tuple(sorted(p, key=lambda t: -p[t])))
        same = len(set(orders)) == 1
        out["T4"] = {"판정": "PASS" if same else "FAIL", "검사": len(months),
                     "순위 종류": len(set(orders)), "순위": sorted(set(orders)),
                     "판정 불가": only_flow}
        out["perm"] = perm
    return out


def report():
    r = judge()
    print("== #11 판정 — 터미널 층 ==")
    print("선커밋 blob %s · 기준 그대로" % PRECOMMIT)
    print()
    for n in r["notes"]:
        print("  " + n)
    if r["stop"]:
        print()
        print("**정지** — 게이트가 걸렸다. 판정에 가지 않는다.")
        for s in r["stop"]:
            print("  · " + s)
        return 1

    print()
    print("── 몫 (분모 = 공표 합계) ──")
    print("  %-9s %8s %8s %8s" % ("달", *GROUPS))
    for m in r["months"]:
        s = r["shares"][m]
        print("  %-9s %7.1f%% %7.1f%% %7.1f%%" % (m, s["신항"], s["남항"], s["국제여객부두"]))

    print()
    print("── 전년대비 부호 ──")
    cols = sorted(next(iter(r["signs"].values())))
    print("  %-9s %s" % ("달", " ".join("%-5s" % c for c in cols)))
    for m in r["months"]:
        print("  %-9s %s" % (m, " ".join("%-5s" % r["signs"][m][c] for c in cols)))

    if "perm" in r:
        print()
        print("── 안벽 1m당 천TEU (대응 터미널만) ──")
        ts = sorted(r["matched"])
        print("  %-9s %s" % ("달", " ".join("%-8s" % t for t in ts)))
        for m in r["months"]:
            print("  %-9s %s" % (m, " ".join("%-8.4f" % r["perm"][m][t] for t in ts)))

    print()
    print("── 판정 ──")
    for k in ("T1", "T2", "T3", "T4"):
        v = r[k]
        extra = ""
        if k in ("T1", "T2"):
            extra = "성립 %d / 검사 %d · 미성립 %s" % (v["성립"], v["검사"], v["미성립"] or "없다")
        elif k == "T3":
            extra = "동행 %d / 검사 %d (기준 %d 이상) · %s" % (v["동행"], v["검사"], v["기준"], v["동행한 달"] or "없다")
        elif k == "T4" and "순위" in v:
            extra = "순위 종류 %d / 검사 %d · 판정 불가 %s" % (v["순위 종류"], v["검사"], v["판정 불가"] or "없다")
        else:
            extra = v.get("사유", "")
        print("  %-4s %-10s %s" % (k, v["판정"], extra))
    v3 = r["T3"]
    print()
    print("── T3 의 사전 난이도 (판정에 안 쓴다) ──")
    print("  부호가 무관하고 반반이면 다섯이 모두 같을 확률 %.4f (= 2·(1/2)^5)" % v3["귀무확률"])
    print("  %d개월 기대치 %.2f개월 · 관측 %d개월 · 기준은 %d개월 이상이었다"
          % (v3["검사"], v3["귀무기대"], v3["동행"], v3["기준"]))
    print("  다섯만 동행 %d개월 — 합계를 빼도 같은 수다(합계는 다섯의 합이라 동전이 아니다)"
          % v3["다섯만 동행"])
    tf = r["합계부호"]
    print("  합계 부호 차례 %s — **바뀐 횟수 %d · 구간 %d**  (이 둘을 섞지 않는다 · 사고 117)"
          % (",".join(tf["차례"]), tf["바뀐 횟수"], tf["구간 수"]))
    print("  **가정은 이 데이터로 검증하지 않았다.** 기준이 얼마나 빡빡했는지의 자[尺]일 뿐이다")
    n_fail = sum(1 for k in ("T1", "T2", "T3", "T4") if r[k]["판정"] == "FAIL")
    print()
    print("PASS %d · FAIL %d · 판정 불가 %d"
          % (sum(1 for k in ("T1", "T2", "T3", "T4") if r[k]["판정"] == "PASS"),
             n_fail,
             sum(1 for k in ("T1", "T2", "T3", "T4") if r[k]["판정"] == "판정 불가")))
    print("**FAIL 도 기준 그대로 발행한다**(§3-7).")
    return 0


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 부호 규칙 (0 은 양에도 음에도 안 넣는다) ──")
    chk("양", sign(1.2), "+")
    chk("음", sign(-0.1), "-")
    chk("영은 따로", sign(0.0), "0")
    chk("없는 값은 None", sign(None), None)

    print("── 인수시험: 파서 ──")
    chk("빈 칸은 None", num(""), None)
    chk("쉼표를 지운다", num("1,234"), 1234.0)

    print("── 인수시험: 실물 ──")
    months, total, group, term, yt, yterm, berth = load()
    chk("10개월", len(months), 10)
    chk("창이 2025-10~2026-07", (months[0], months[-1]), ("2025-10", "2026-07"))
    chk("달마다 터미널 5", {len(term[m]) for m in months}, {5})
    chk("국제여객부두를 IPT 로 채웠다", all("국제여객부두" in group[m] for m in months), True)
    chk("안벽 길이 다섯", sorted(berth), ["E1CT", "HJIT", "ICT", "SICT", "SNCT"])
    chk("SNCT 는 300+500", berth["SNCT"], 800.0)

    print("── 인수시험: 판정이 기준을 안 넘는다 ──")
    r = judge()
    chk("정지 없음", r["stop"], [])
    chk("대응 4곳", r["matched"], ["E1CT", "HJIT", "ICT", "SNCT"])
    chk("물동량에만 IPT", r["only_flow"], ["IPT"])
    chk("부두현황에만 SICT", r["only_berth"], ["SICT"])
    chk("T1 검사 분모가 0 이 아니다", r["T1"]["검사"] > 0, True)
    chk("T2 하한이 선언값 50.0", SHARE_FLOOR, 50.0)
    chk("T3 기준이 6개월", r["T3"]["기준"], 6)

    print("── 인수시험: T3 사전 난이도는 판정을 안 바꾼다 ──")
    chk("귀무확률 = 2·(1/2)^5", round(r["T3"]["귀무확률"], 6), 0.0625)
    chk("10개월 기대치", round(r["T3"]["귀무기대"], 4), 0.625)
    chk("기준은 기대치보다 크다 — 빡빡했다", r["T3"]["기준"] > r["T3"]["귀무기대"], True)
    chk("합계를 빼도 같은 수다", r["T3"]["다섯만 동행"], r["T3"]["동행"])
    # **발행본에 틀리게 나간 수다**(사고 117) — 코드가 세고 여기서 고정한다.
    chk("합계 부호가 바뀐 횟수 5", r["합계부호"]["바뀐 횟수"], 5)
    chk("구간(런) 수 6 — 「6번 바뀐다」가 아니었다", r["합계부호"]["구간 수"], 6)
    chk("둘은 늘 1 차이다", r["합계부호"]["구간 수"] - r["합계부호"]["바뀐 횟수"], 1)
    chk("판정은 관측과 기준만으로 난다",
        r["T3"]["판정"], "PASS" if r["T3"]["동행"] >= r["T3"]["기준"] else "FAIL")
    chk("판정 넷이 다 났다",
        sorted(k for k in ("T1", "T2", "T3", "T4") if "판정" in r[k]), ["T1", "T2", "T3", "T4"])

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="#11 판정 — 터미널 층")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else report())

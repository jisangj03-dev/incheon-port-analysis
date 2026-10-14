# -*- coding: utf-8 -*-
"""#12 판정 — 터미널 층을 41개월 창에서.

**선커밋 `docs/12_주제검증.md`(blob `894439103c58ec4da3d8794a1f43f9b2e0aee2ab`)의 기준으로만
판정한다.** 이 파일은 기준을 해석하지 않는다 — S1~S3 과 게이트 여섯을 그대로 옮긴 것뿐이다.

  python analysis/judge_12_terminal_long.py            # 판정
  python analysis/judge_12_terminal_long.py --selftest

무엇을 보나
-----------
· 물동량 `terminal_monthly_long.csv` — 2023-03~2026-07 · **창 41개월 · 관측 39개월**
· 출처 대장 `terminal_monthly_long_sources.csv` — 소스 실재(게이트 1)
· **#11 의 `terminal_monthly.csv` 는 열지 않는다.** 그 편의 재현 자산이고 이 편과 파일이 다르다.

닿지 않는 곳
------------
· **인과를 안 낸다.** 왜 그런 값인지는 이 데이터에 없다(선커밋 표기 규칙).
· **「계절성」·「상관」이라는 말을 안 쓴다** — 재는 것은 **같은 역월의 편차 부호 반복**과
  **쌍의 부호 일치율**이다. 그 둘은 계절성·상관의 한 조각이지 그것 자체가 아니다.
· **사전 난이도(귀무기대)는 판정에 안 쓴다.** 기준이 얼마나 어려웠는지의 자[尺]다.
  귀무모형은 「부호·순서가 서로 무관하고 등확률」 하나로 고정하고, **그 가정은 검증하지 않는다.**
· **판정 불가를 통과에도 미성립에도 안 넣는다**(사고 26·77). 「창 41 / 관측 39 / 판정 불가 2」를 늘 같이 낸다.
· **2026 구간은 잠정치다**(§4). 이 파일은 값을 그대로 내고 지위는 결론 문서가 적는다.
"""
import argparse
import collections
import csv
import io
import itertools
import os
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
MONTHLY = os.path.join(HERE, "terminal_monthly_long.csv")
SOURCES = os.path.join(HERE, "terminal_monthly_long_sources.csv")

PRECOMMIT = "894439103c58ec4da3d8794a1f43f9b2e0aee2ab"
WINDOW = ("2023-03", "2026-07")     # 선커밋 §2 — 창 41개월
# 못 읽은 달. **첨부가 `.hwp` 다**(원문 확인 2026-09-12) — 「원문에 없다」가 아니다.
UNREADABLE = ("2023-12", "2024-01")
GROUPS = ("신항", "남항", "국제여객부두")
TERMS = ("E1CT", "HJIT", "ICT", "IPT", "SNCT")

S1_MIN_MONTHS = 7        # S1 — 역월 12개 중
S2_MEDIAN_FLOOR = 0.50   # S2 — 쌍 10개 일치율의 중앙값이 이것을 **넘어야** 성립
S3_MONTHS = (3, 4, 5, 6, 7)   # S3 — 네 해가 전부 갖는 정합 창


def rd(path):
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def num(s):
    s = (s or "").strip().replace(",", "")
    if not s or s == "-":
        return None
    if s.startswith("△"):
        return -float(s[1:])
    try:
        return float(s)
    except ValueError:
        return None


def sign(v):
    """양(+) · 음(-) · 영(0). **0 은 양에도 음에도 안 넣는다**(선커밋 S1·S2)."""
    if v is None:
        return None
    return "+" if v > 0 else ("-" if v < 0 else "0")


def window_months():
    """창 41개월 전체 — 관측 여부와 무관하게 자리를 만든다(선커밋 판정 규칙)."""
    (y0, m0), (y1, m1) = [tuple(int(x) for x in w.split("-")) for w in WINDOW]
    out, y, m = [], y0, m0
    while (y, m) <= (y1, m1):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def load():
    rows = rd(MONTHLY)
    months = sorted({r["기준연월"] for r in rows})
    total, group, term = {}, collections.defaultdict(dict), collections.defaultdict(dict)
    yoy_total, yoy_term = {}, collections.defaultdict(dict)
    other = {}
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
        elif lay == "그 외":
            other[m] = v
    # 국제여객부두는 소계 행이 없다 — 터미널 IPT 가 그 자체로 한 칸이다(FACTS 68 · #11 과 같다).
    for m in months:
        if "국제여객부두" not in group[m] and "IPT" in term[m]:
            group[m]["국제여객부두"] = term[m]["IPT"]
    return months, total, dict(group), dict(term), yoy_total, dict(yoy_term), other


def gates(months, total, group, term, other):
    """반환 (정지 사유, 기록). **정지 사유가 있으면 판정에 안 간다.**"""
    stop, notes = [], []
    win = window_months()

    # 1 소스 실재
    src = rd(SOURCES)
    src_months = {r["기준연월"] for r in src}
    no_sha = [r["기준연월"] for r in src if not (r.get("SHA256_앞16") or "").strip()]
    if no_sha:
        stop.append("게이트1 — SHA256 없는 달 %s" % no_sha)
    elif src_months != set(months):
        stop.append("게이트1 — 출처 대장과 물동량 표의 달 집합이 다르다: %s"
                    % sorted(src_months ^ set(months)))
    else:
        notes.append("1 소스 실재 · **통과** — 출처 대장 %d달 · SHA256 전부 있음 · 달 집합 일치"
                     % len(src))

    # 2 완전성
    bad = [m for m in months
           if total.get(m) is None or len(group.get(m, {})) < 2 or len(term.get(m, {})) != 5]
    if bad:
        stop.append("게이트2 — 완전성 미달 %s (파싱·키를 먼저 의심한다)" % bad)
    else:
        notes.append("2 완전성 · **통과** — 관측 %d개월 각각 합계 1 · 부두군 %d · 터미널 5"
                     % (len(months), len(group[months[0]])))

    # 3 부두군 소계 행 — **선커밋의 전제가 틀렸다. 틀린 그대로 적는다.**
    gsets = {tuple(sorted(group[m])) for m in months}
    osets = sorted(m for m in months if m in other)
    notes.append("3 결합·구조 · **기록** — 계층 `부두군` 이름 집합이 %d종: %s "
                 "(국제여객부두는 소계 행이 없어 IPT 로 채운다 · FACTS 68)"
                 % (len(gsets), " / ".join("·".join(g) for g in sorted(gsets))))
    notes.append("   **갈리는 것은 계층 `그 외` 다** — %d개월에만 있다: %s. "
                 "선커밋 §0-1 은 이것을 「부두군 소계 행 수 3↔4」로 적었는데, "
                 "그 수는 프로브가 `그 외` 를 같이 센 것이었다. **부두군 자체는 창 내내 같다.**"
                 % (len(osets), " ".join(osets)))

    # 4 판정 불가
    missing = [m for m in win if m not in months]
    zero_total = [m for m in months if not total.get(m)]
    notes.append("4 판정 불가 · **기록** — **창 %d / 관측 %d / 판정 불가 %d**  (%s) — "
                 "첨부가 `.hwp` 라 우리 파서가 못 읽는다. **「원문에 없다」가 아니다**"
                 % (len(win), len(months), len(missing), " ".join(missing) or "없다"))
    if zero_total:
        notes.append("   공표 합계가 0·부재인 달 %s — 몫 판정에서 뺀다" % zero_total)
    if sorted(missing) != sorted(UNREADABLE):
        notes.append("   **[주의] 못 읽은 달이 선커밋이 적은 %s 와 다르다** — 수집을 다시 본다"
                     % list(UNREADABLE))

    # 5 항등식 — **무결성 확인이지 결론의 근거가 아니다**
    diff = {}
    for m in months:
        five = sum(term[m][t] for t in TERMS if term[m].get(t) is not None)
        diff[m] = round(five - total[m], 1)
    big = {m: d for m, d in diff.items() if abs(d) > 2}
    notes.append("5 항등식 · **기록** — 다섯 곳 합 − 공표 합계: 최대 %+g · 최소 %+g · "
                 "±2 초과 달 %s"
                 % (max(diff.values()), min(diff.values()), (sorted(big) or "없다")))

    # 6 지위
    notes.append("6 지위 · 2026 구간은 **잠정치**다(§4). S3 은 2023~2025 와 2026 을 한 표에 놓으므로 각주를 단다")
    return stop, notes, missing, zero_total, diff


def judge():
    months, total, group, term, yoy_total, yoy_term, other = load()
    stop, notes, missing, zero_total, diff = gates(months, total, group, term, other)
    out = {"months": months, "notes": notes, "stop": stop, "missing": missing,
           "window": len(window_months()), "diff": diff}
    if stop:
        return out

    judged = [m for m in months if m not in zero_total]
    shares = {m: {g: (group[m].get(g) or 0.0) / total[m] * 100.0 for g in GROUPS}
              for m in judged}
    out["shares"] = shares

    # ── S1 계절성 — 같은 역월의 편차 부호가 관측된 모든 해에서 같은가 ──
    year_mean = {}
    for y in sorted({m[:4] for m in judged}):
        ms = [m for m in judged if m.startswith(y)]
        year_mean[y] = sum(shares[m]["신항"] for m in ms) / len(ms)
    dev, s1_rows, s1_hit, s1_undet = {}, {}, [], []
    for m in judged:
        dev[m] = shares[m]["신항"] - year_mean[m[:4]]
    for mm in range(1, 13):
        ys = sorted(m[:4] for m in judged if int(m[5:7]) == mm)
        sg = [sign(dev["%s-%02d" % (y, mm)]) for y in ys]
        s1_rows[mm] = {"해": ys, "부호": sg}
        if len(ys) < 2:
            s1_undet.append(mm)
        elif "0" not in sg and len(set(sg)) == 1:
            s1_hit.append(mm)
    s1_checked = 12 - len(s1_undet)
    # **사전 난이도** — 무관·등확률이면 역월 하나가 전부 같을 확률 2^(1-해수).
    s1_null = sum(2 ** (1 - len(s1_rows[mm]["해"])) for mm in range(1, 13)
                  if mm not in s1_undet)
    out["S1"] = {"성립": len(s1_hit), "검사": s1_checked, "기준": S1_MIN_MONTHS,
                 "성립 역월": s1_hit, "판정 불가 역월": s1_undet,
                 "귀무기대": s1_null, "표": s1_rows, "연평균": year_mean, "편차": dev,
                 "판정": "PASS" if len(s1_hit) >= S1_MIN_MONTHS else "FAIL"}

    # ── S2 쌍 동행 — 쌍 10개 부호 일치율의 중앙값 ──
    rates = {}
    for a, b in itertools.combinations(TERMS, 2):
        den = num_ok = 0
        for m in months:
            sa, sb = sign(yoy_term[m].get(a)), sign(yoy_term[m].get(b))
            if sa in (None, "0") or sb in (None, "0"):
                continue
            den += 1
            num_ok += (sa == sb)
        rates[(a, b)] = (num_ok, den, (num_ok / den if den else None))
    vals = sorted(v[2] for v in rates.values() if v[2] is not None)
    med = statistics.median(vals) if vals else None
    out["S2"] = {"쌍": rates, "중앙값": med, "기준": S2_MEDIAN_FLOOR,
                 "귀무기대": 0.5,
                 "판정": "PASS" if (med is not None and med > S2_MEDIAN_FLOOR) else "FAIL"}

    # ── S3 몫의 연도별 단조성 — 3~7월 정합 창 ──
    ymeans, missing_y = {}, []
    for y in sorted({m[:4] for m in judged}):
        ms = ["%s-%02d" % (y, mm) for mm in S3_MONTHS]
        if all(m in shares for m in ms):
            ymeans[y] = sum(shares[m]["신항"] for m in ms) / len(ms)
        else:
            missing_y.append(y)
    seq = [ymeans[y] for y in sorted(ymeans)]
    up = all(b > a for a, b in zip(seq, seq[1:]))
    down = all(b < a for a, b in zip(seq, seq[1:]))
    out["S3"] = {"연평균": ymeans, "정합창": list(S3_MONTHS), "빠진 해": missing_y,
                 "단조": "증가" if up else ("감소" if down else "아니다"),
                 "귀무기대": 2 / 24,
                 "판정": "PASS" if (up or down) and len(seq) >= 2 else "FAIL"}

    # ── 참고 통계 (검증 아님 — 결론 자리 금지) ──
    ext = {}
    for t in TERMS:
        vs = [(term[m][t], m) for m in months if term[m].get(t) is not None]
        ext[t] = {"최대": max(vs), "최소": min(vs)}
    out["참고"] = {"터미널 최대최소": ext,
                 "부두군 몫 폭": {g: (min(shares[m][g] for m in judged),
                                max(shares[m][g] for m in judged)) for g in GROUPS}}
    return out


def report():
    r = judge()
    print("== #12 판정 — 터미널 층 · 창 41개월 ==")
    print("  선커밋 blob %s" % PRECOMMIT)
    print("  창 %d개월(%s~%s) · 관측 %d개월 · 판정 불가 %d개월"
          % (r["window"], WINDOW[0], WINDOW[1], len(r["months"]), len(r["missing"])))
    print("\n── 게이트 ──")
    for n in r["notes"]:
        print("  " + n)
    if r["stop"]:
        print("\n**정지**")
        for s in r["stop"]:
            print("  " + s)
        return 2

    s1, s2, s3 = r["S1"], r["S2"], r["S3"]
    print("\n── S1 계절성 — 같은 역월의 편차 부호 (신항 몫 − 그 해 관측월 평균) ──")
    print("  해 평균: " + " · ".join("%s %.2f%%" % (y, v) for y, v in sorted(s1["연평균"].items())))
    print("  역월  해수  부호")
    for mm in range(1, 13):
        row = s1["표"][mm]
        mark = "  **같다**" if mm in s1["성립 역월"] else ("  판정 불가" if mm in s1["판정 불가 역월"] else "")
        print("  %2d월  %d     %s%s" % (mm, len(row["해"]), " ".join(row["부호"]), mark))
    print("  **성립 %d / 검사 %d (기준 %d 이상) · 판정 불가 역월 %s** → %s"
          % (s1["성립"], s1["검사"], s1["기준"], s1["판정 불가 역월"] or "없다", s1["판정"]))

    print("\n── S2 쌍 동행 — 전년대비 부호 일치율 (쌍 10개) ──")
    for (a, b), (n, d, rate) in sorted(s2["쌍"].items(), key=lambda kv: -(kv[1][2] or 0)):
        print("  %-5s ↔ %-5s  %2d / %2d = %.3f" % (a, b, n, d, rate))
    print("  **중앙값 %.3f (기준 > %.2f)** → %s" % (s2["중앙값"], s2["기준"], s2["판정"]))

    print("\n── S3 몫의 연도별 단조성 — 3~7월 정합 창 ──")
    for y, v in sorted(s3["연평균"].items()):
        print("  %s  신항 몫 3~7월 평균 %.2f%%" % (y, v))
    print("  **단조: %s** → %s" % (s3["단조"], s3["판정"]))

    print("\n── 판정 ──")
    for k in ("S1", "S2", "S3"):
        print("  %-3s %s" % (k, r[k]["판정"]))
    n_pass = sum(1 for k in ("S1", "S2", "S3") if r[k]["판정"] == "PASS")
    print("  PASS %d · FAIL %d" % (n_pass, 3 - n_pass))

    print("\n── 사전 난이도 (판정에 안 쓴다 · 선커밋 §3 이 미리 적은 것) ──")
    print("  S1  귀무기대 %.3f개월 / 검사 %d · 기준 %d → 기대치의 약 %.1f배 (어림 — 한 해 안의 편차는 독립이 아니다)"
          % (s1["귀무기대"], s1["검사"], s1["기준"], s1["기준"] / s1["귀무기대"]))
    print("  S2  귀무기대 중앙값 %.2f · 기준 > %.2f → **동전이다**" % (s2["귀무기대"], s2["기준"]))
    print("  S3  귀무확률 %.4f (= 2/4!) → 사전 통과 가능성이 낮다" % s3["귀무기대"])
    print("  **가정은 이 데이터로 검증하지 않았다.** 기준이 얼마나 빡빡했는지의 자[尺]다")

    print("\n── 참고 통계 (결론 자리 금지) ──")
    for g, (lo, hi) in r["참고"]["부두군 몫 폭"].items():
        print("  %s 몫 %.1f~%.1f%% (폭 %.1f%%p)" % (g, lo, hi, hi - lo))
    for t, e in sorted(r["참고"]["터미널 최대최소"].items()):
        print("  %-5s 최대 %g(%s) · 최소 %g(%s)"
              % (t, e["최대"][0], e["최대"][1], e["최소"][0], e["최소"][1]))
    print("\n**FAIL 도 기준 그대로 발행한다**(§3-7).")
    return 0


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-50s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 파서 ──")
    chk("△ 는 음수", num("△12.0"), -12.0)
    chk("'-' 는 값 없음", num("-"), None)
    chk("0 은 양도 음도 아니다", sign(0.0), "0")
    chk("창 41개월", len(window_months()), 41)
    chk("창의 양 끝", (window_months()[0], window_months()[-1]), WINDOW)

    print("── 인수시험: 실물 ──")
    months, total, group, term, yt, yterm, other = load()
    chk("관측 39개월", len(months), 39)
    chk("못 읽은 달 둘", sorted(set(window_months()) - set(months)), sorted(UNREADABLE))
    chk("달마다 터미널 5", {len(term[m]) for m in months}, {5})
    chk("부두군은 창 내내 신항·남항", {tuple(sorted(x for x in group[m] if x != "국제여객부두"))
                                for m in months}, {("남항", "신항")})
    chk("국제여객부두를 IPT 로 채웠다", all("국제여객부두" in group[m] for m in months), True)
    chk("`그 외` 는 일부 달만", 0 < len(other) < len(months), True)

    print("── 인수시험: 판정이 기준을 안 넘는다 ──")
    r = judge()
    chk("정지 없음", r["stop"], [])
    chk("S1 기준 7개월", r["S1"]["기준"], 7)
    chk("S2 기준 중앙값 > 0.50", r["S2"]["기준"], 0.50)
    chk("S3 정합 창은 3~7월", r["S3"]["정합창"], [3, 4, 5, 6, 7])
    chk("S3 는 네 해를 본다", sorted(r["S3"]["연평균"]), ["2023", "2024", "2025", "2026"])
    chk("판정 셋이 다 났다",
        sorted(k for k in ("S1", "S2", "S3") if "판정" in r[k]), ["S1", "S2", "S3"])
    chk("판정은 관측과 기준만으로 난다 (S1)",
        r["S1"]["판정"], "PASS" if r["S1"]["성립"] >= r["S1"]["기준"] else "FAIL")
    chk("쌍은 열이다", len(r["S2"]["쌍"]), 10)

    print("── 인수시험: 사전 난이도는 판정을 안 바꾼다 ──")
    chk("S3 귀무확률 = 2/4!", round(r["S3"]["귀무기대"], 6), round(2 / 24, 6))
    chk("S2 귀무 중앙값 0.5", r["S2"]["귀무기대"], 0.5)
    chk("S1 기준이 귀무기대보다 크다", r["S1"]["기준"] > r["S1"]["귀무기대"], True)

    print("── 인수시험: #11 의 파일을 열지 않는다 ──")
    # **글자를 찾지 않는다** — 이 시험 자신이 그 글자를 들고 있어서 **자기를 찾았다**(첫 판이 그랬다).
    # **경로 상수를 본다.** 명제는 「이 편은 `_long` 파일만 연다」이고 그것은 상수에 있다.
    chk("물동량 경로가 `_long`", os.path.basename(MONTHLY), "terminal_monthly_long.csv")
    chk("출처 대장도 `_long`", os.path.basename(SOURCES),
        "terminal_monthly_long_sources.csv")

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="#12 판정 — 터미널 층 · 창 41개월")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else report())

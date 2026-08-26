"""무역 라인 첫 판정 — 게이트 ② 질문 3개 + 게이트 ③ 기준 A·B·C.

기준은 `docs/무역라인_개시게이트.md`에 **데이터를 받기 전에** 커밋했다.
선커밋 blob = df28c251d12570595b8944d7ee28e5618af0e3a4.
이 스크립트는 그 기준을 그대로 집행한다. **기준을 여기서 고치지 않는다.**

Q1  관세청 신고 기준으로 인천항은 수입 우위인가 수출 우위인가 (금액·건수 각각)
Q2  그 방향이 확인된 창에서 몇 개월 연속 성립하는가
Q3  건수 기준 방향과 금액 기준 방향이 어긋나는 달이 있는가

B   명세 합 = 총계 검산. 안 맞으면 발행 보류
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "analysis" / "porttrade_202412_202607.csv"
VALS = ["expCnt", "expDlr", "impCnt", "impDlr", "balPayments"]


def num(s):
    s = (s or "").replace(",", "").strip()
    if s in ("", "-"):
        return 0
    return int(float(s))


def main():
    if not SRC.exists():
        print("[중단] 원시 CSV가 없다. collect_porttrade.py 를 먼저 돌린다.")
        sys.exit(2)

    rows = list(csv.DictReader(open(SRC, encoding="utf-8")))
    if "reqYymm" not in (rows[0] if rows else {}):
        print("[중단] reqYymm 컬럼이 없다. collect_porttrade.py 를 다시 돌린다.")
        sys.exit(2)
    # 월 축은 **요청값**으로 잡는다. 응답의 year는 총계행에서 「총계」로 덮인다(사고 37).
    months = sorted({r["reqYymm"] for r in rows})

    detail = defaultdict(lambda: defaultdict(int))   # 월 → 값 합 (명세행만)
    total = defaultdict(dict)                        # 월 → 총계행
    inc = defaultdict(lambda: defaultdict(int))      # 월 → 인천항 합
    for r in rows:
        m = r["reqYymm"]
        if r["portCd"] == "-":
            total[m] = {v: num(r[v]) for v in VALS}
            continue
        for v in VALS:
            detail[m][v] += num(r[v])
        if r["portCd"] == "KRINC":
            for v in VALS:
                inc[m][v] += num(r[v])

    # ── 기준 B — 명세 합 = 총계 ──────────────────────────────
    print("── 기준 B  명세 합 = 총계 검산 ──")
    bad = []
    for m in months:
        for v in VALS:
            d, t = detail[m][v], total[m].get(v)
            if t is None or d != t:
                bad.append((m, v, d, t))
    if bad:
        print(f"  불일치 {len(bad)}건 / {len(months) * len(VALS)}건")
        for m, v, d, t in bad[:12]:
            diff = "-" if t is None else f"{d - t:+,}"
            print(f"    {m} {v:<12} 명세합 {d:>15,}  총계 {t if t is None else format(t, ',')}  차 {diff}")
        if len(bad) > 12:
            print(f"    … 외 {len(bad) - 12}건")
    else:
        print(f"  일치 — {len(months)}개월 × 값 {len(VALS)}종 전부.")

    # ── 내적 검산 — balPayments = expDlr - impDlr ────────────
    print("\n── 내적 검산  balPayments = expDlr − impDlr (인천항) ──")
    off = [m for m in months
           if inc[m]["balPayments"] != inc[m]["expDlr"] - inc[m]["impDlr"]]
    print(f"  어긋난 달 {len(off)}건" + (f" → {off}" if off else " — 전 구간 성립."))

    # ── Q1·Q2·Q3 ─────────────────────────────────────────────
    print("\n── 인천항(KRINC) 월별 방향 ──")
    print(f"  {'월':<8}{'수출건':>10}{'수입건':>10}  {'건수방향':<9}"
          f"{'수출액(USD)':>17}{'수입액(USD)':>17}  {'금액방향':<9}{'어긋남'}")
    sign_d, sign_c, clash = [], [], []
    for m in months:
        ec, ic = inc[m]["expCnt"], inc[m]["impCnt"]
        ed, idl = inc[m]["expDlr"], inc[m]["impDlr"]
        dc = "수출우위" if ec > ic else ("수입우위" if ic > ec else "동률")
        dd = "수출우위" if ed > idl else ("수입우위" if idl > ed else "동률")
        sign_c.append(dc)
        sign_d.append(dd)
        x = "●" if dc != dd else ""
        if x:
            clash.append(m)
        print(f"  {m:<8}{ec:>10,}{ic:>10,}  {dc:<9}{ed:>17,}{idl:>17,}  {dd:<9}{x}")

    def run(seq):
        """마지막 값 기준 연속 성립 개월. 창 전체면 len(seq)."""
        k = 1
        for a, b in zip(reversed(seq), list(reversed(seq))[1:]):
            if a == b:
                k += 1
            else:
                break
        return k

    print(f"\n  Q1  금액 기준 {sorted(set(sign_d))}  ·  건수 기준 {sorted(set(sign_c))}")
    print(f"  Q2  금액 방향 연속 {run(sign_d)}개월 / {len(months)}개월 창"
          f"  ·  건수 방향 연속 {run(sign_c)}개월")
    print(f"  Q3  두 기준이 어긋난 달 {len(clash)}건" + (f" → {clash}" if clash else ""))

    # 전국 합계를 함께 낸다 — 관세청 공표 무역통계와 맞대면 단위·완결성을 밖에서 검산할 수 있다.
    # 지금은 대조 상대를 출처로 확보하지 않았다. [미확인] · 다음 검산 후보.
    print()
    print("── 전국 합계 (외부 대조용. 대조 상대 미확보 [미확인]) ──")
    for m in months[:1] + months[-1:]:
        d = detail[m]
        print(f"  {m}  수출 {d['expDlr']:>17,} USD   수입 {d['impDlr']:>17,} USD")

    print("\n── 게이트 ③ ──")
    a_ok = True
    print(f"  A  Q1·Q2·Q3 전부 답 나옴          {'통과' if a_ok else '미달'}")
    print(f"  B  명세 합 = 총계                 {'통과' if not bad else '미달 — 발행 보류'}")
    print("  C  FACTS 등재·린터                 판정 대상 아님(본문 작성 단계)")
    sys.exit(0 if (a_ok and not bad) else 1)


if __name__ == "__main__":
    main()

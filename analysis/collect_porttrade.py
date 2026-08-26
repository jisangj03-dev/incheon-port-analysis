"""관세청 항구·공항별 수출입실적 수집 — 선커밋 창 그대로.

왜 이 창인가
------------
`docs/무역라인_개시게이트.md` 게이트 ②가 **값을 보기 전에** 2024-12 ~ 2026-07로 못 박았다.
선커밋 blob = df28c251d12570595b8944d7ee28e5618af0e3a4.
**창을 넓히려면 새 선커밋이 필요하다.** 값을 본 뒤에 넓히면 그것이 사후 조정이다.

무엇을 저장하는가
-----------------
**월 응답 전량**이다. 인천항(KRINC) 행만 남기지 않는다 — 이유는 둘이다.
  1. 게이트 ③-B 검산(명세 합 = 총계)이 전 항구 행을 요구한다.
  2. 이 API는 페이징이 없어 어차피 월 전량이 한 번에 온다. 버리면 재수집 비용만 늘어난다.

파싱 원칙
---------
**태그명 기준.** 위치 인덱스 금지(사고 1). 이 소스는 **행마다 태그 구성이 다르다** —
총계행에는 `cstmSgn` 태그가 아예 없다. 위치로 읽으면 조용히 밀린다.

완결성
------
`totalCount` 태그가 없는 서비스다. **행 수를 직접 세고**, 월별 행 수를 함께 기록한다.
`code=00`은 데이터 존재를 뜻하지 않는다(사고 3·5).

사용
----
  python analysis/collect_porttrade.py            # 수집 → CSV
  python analysis/collect_porttrade.py --dry      # 호출만. 파일 안 쓴다
"""

import argparse
import csv
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import config
except ImportError:
    print("[중단] analysis/config.py 가 없다.")
    sys.exit(2)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

URL = "https://apis.data.go.kr/1220000/porttrade/getPorttradeList"
OUT = ROOT / "analysis" / "porttrade_202412_202607.csv"

# 선커밋 창. 고치려면 게이트 문서를 먼저 고치고 새로 커밋한다.
MONTHS = [f"{y}{m:02d}" for y, m in
          ([(2024, 12)] + [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 8)])]

# 응답 태그. `year`는 응답값 그대로 둔다 — **총계행은 year 값이 「총계」다**(사고 37).
TAGS = ["year", "cstmSgn", "portCd", "statKor",
        "expCnt", "expDlr", "impCnt", "impDlr", "balPayments"]
# 저장 컬럼. 맨 앞에 **요청한 달**을 박는다. 응답이 축을 덮어써도 월을 잃지 않는다.
COLS = ["reqYymm"] + TAGS


def fetch(month):
    p = {"strtYymm": month, "endYymm": month, "serviceKey": config.SERVICE_KEY}
    q = URL + "?" + urllib.parse.urlencode(p, safe="%")
    req = urllib.request.Request(q, headers={"User-Agent": "collect"})
    with urllib.request.urlopen(req, timeout=40, context=CTX) as r:
        return r.status, r.read().decode("utf-8", "replace")


def parse(body, month):
    """<item> 블록을 태그명으로 뜯는다. 없는 태그는 빈 문자열.

    `reqYymm`은 응답이 아니라 **요청**에서 온다. 총계행은 `year`가 「총계」로 와서
    월 라벨이 사라지기 때문이다 — 순서로 복원하면 사고 1(위치 인덱스)이다.
    """
    rows = []
    for blk in re.findall(r"<item>(.*?)</item>", body, re.S):
        d = dict(re.findall(r"<([A-Za-z_][\w]*)>([^<]*)</\1>", blk))
        r = {t: d.get(t, "").strip() for t in TAGS}
        r["reqYymm"] = month
        rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    all_rows, report = [], []
    for m in MONTHS:
        try:
            st, body = fetch(m)
        except urllib.error.HTTPError as e:
            print(f"  [중단] {m} HTTP {e.code}")
            sys.exit(1)
        code = re.search(r"<(?:resultCode|returnReasonCode)>([^<]*)<", body)
        code = code.group(1) if code else "-"
        rows = parse(body, m)
        inc = sum(1 for r in rows if r["portCd"] == "KRINC")
        tot = sum(1 for r in rows if r["portCd"] == "-")
        report.append((m, st, code, len(rows), inc, tot))
        if code not in ("00", "0") or not rows:
            print(f"  [중단] {m} code={code} 행={len(rows)} — 응답 성공이 데이터 존재가 아니다(사고 3·5)")
            sys.exit(1)
        all_rows.extend(rows)

    print("── 수집 (선커밋 창 2024-12 ~ 2026-07) ──")
    print(f"  {'월':<8}{'HTTP':<6}{'code':<6}{'행':>6}{'KRINC':>7}{'총계행':>7}")
    for m, st, code, n, inc, tot in report:
        print(f"  {m:<8}{st:<6}{code:<6}{n:>6}{inc:>7}{tot:>7}")
    print(f"\n  합계 {len(all_rows)}행 · {len(MONTHS)}개월")

    if a.dry:
        print("  --dry — 파일을 쓰지 않았다.")
        return

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(all_rows)
    print(f"  기록 {OUT.relative_to(ROOT)}  ({OUT.stat().st_size} B)")


if __name__ == "__main__":
    main()

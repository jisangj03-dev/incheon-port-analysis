"""운영자 검수 도구 — 무작위 수치 1건을 뽑아 대조 절차를 출력한다.

왜 있는가
---------
저작 구조 B(AI가 생성하고 사람이 운영한다)에서 「검수·발행: 운영자」라는 표기가
거짓이 되지 않으려면, 검수가 실제로 일어나고 그 흔적이 남아야 한다.
그리고 검수가 무거우면 안 지켜지고, 안 지켜지면 표기가 거짓이 된다.

그래서 운영자 역할을 셋으로 고정하고 편당 10분 안에 끝나게 설계했다.
  ① 발행 전 통독            — 결론 자리(H1·한 줄 결론·§1·§3)만. 3~4분
  ② 숫자 1건 무작위 출처 대조 — 이 스크립트가 뽑아준다. 3분
  ③ push                    — 1분

②를 운영자가 직접 고르면 쉬운 것만 고르게 된다. 그래서 기계가 뽑는다.

사용
----
  python analysis/review_pick.py reports/report_07_....md
  python analysis/review_pick.py reports/report_07_....md --pick=12 --log   # 그 번호로 기록

--log 는 --pick=N 을 요구한다. 대조한 값과 기록된 값이 같아야 하기 때문이다.

--log는 docs/검수기록.md에 한 줄을 붙인다. 이 기록이 「검수했다」는 표기의 근거다.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "검수기록.md"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_publish import TOKEN, is_claim, load_facts, norm, strip_noise  # noqa: E402


def collect(md: str):
    """문서 전체에서 주장 수치를 모은다. 결론 자리에 한정하지 않는다 —
    린터가 못 보는 본문·표를 사람이 보게 하는 것이 이 도구의 목적이다."""
    out = []
    for i, line in enumerate(md.splitlines(), 1):
        # 표 구분선/이미지/헤딩 번호(### 2.1)는 주장 수치가 아니다.
        if line.startswith("|---") or line.startswith("![") or line.startswith("#"):
            continue
        for m in TOKEN.finditer(strip_noise(line)):
            value, unit = m.group(1), m.group(2) or ""
            if not is_claim(value, unit):
                continue
            out.append((i, re.sub(r"\s+", "", m.group(0)), line.strip()[:110]))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("사용: python analysis/review_pick.py <보고서.md> [--log]")
    path = Path(args[0])
    md = path.read_text(encoding="utf-8")
    facts = load_facts()

    items = collect(md)
    if not items:
        sys.exit("주장 수치를 찾지 못했다.")

    # 운영자가 고르면 쉬운 것만 고른다. 기계가 뽑는다.
    # --pick N 이 있으면 그 번호를 그대로 쓴다. 왜 필요한가:
    # 검수는 「뽑기 -> 사람이 원본 대조 -> 기록」 순인데, 기록 단계에서 다시 뽑으면
    # **대조한 값과 기록된 값이 달라진다.** 그러면 검수기록이 일어나지 않은 검수를
    # 증언하게 되고, 그 기록을 근거로 다는 표기 블록이 거짓이 된다(지침 2.2).
    # 무작위성은 「운영자가 고르지 못하게」 하려는 것이지 매 실행 재추첨이 목적이 아니다.
    pick = None
    for a in sys.argv[1:]:
        if a.startswith("--pick="):
            pick = int(a.split("=", 1)[1])
    if pick is not None:
        if not (0 <= pick < len(items)):
            sys.exit(f"[중단] --pick={pick} 범위 밖 (0~{len(items) - 1})")
        idx = pick
    else:
        idx = int.from_bytes(os.urandom(4), "big") % len(items)
    line_no, token, context = items[idx]
    f = facts.get(norm(TOKEN.search(token).group(1)))

    print("=" * 62)
    print(f"검수 대상: {path.name}")
    print(f"후보 수치 {len(items)}건 중 무작위 1건 (추첨 번호 {idx})")
    print("=" * 62)
    print(f"\n  값      : {token}")
    print(f"  위치    : {path.name}:{line_no}")
    print(f"  문맥    : {context}")
    if f:
        print(f"\n  대장 등재: {f['표기']}")
        print(f"  창       : {f['창']}")
        print(f"  지위     : {f['지위']}")
    else:
        print("\n  대장 미등재 - 본문/표 수치는 등재 대상이 아닐 수 있다.")
        print("  결론 자리(H1/한 줄 결론/1절/3절) 수치라면 대조 후 FACTS.md에 등재할 것.")

    print("\n" + "-" * 62)
    print("운영자가 할 일 (약 3분)")
    print("-" * 62)
    print("""
  1) 이 값이 어디서 나왔는지 원본을 연다.
       docs/07_판정결과.md  또는  analysis/container_*_direction.csv
  2) 화면의 값과 보고서의 값이 같은지 눈으로 대조한다.
  3) 값이 아니라 '창'도 본다 — 기간·모집단·단위가 문맥과 맞는가.
       (2026-08-25 사고 A가 정확히 이 지점이었다: 값은 맞고 기간이 틀렸다)
  4) 어긋나면 발행하지 않는다. 맞으면 --log 로 기록을 남긴다.
""")

    if "--log" in sys.argv and pick is None:
        # stderr는 cp949라 한글이 깨진다. 읽히지 않는 중단 사유는 없는 것과 같다(사고 15).
        print("\n[중단] --log 는 --pick=N 과 함께 쓴다.")
        print("       재추첨된 값을 기록하면 대조한 값과 기록된 값이 달라진다.")
        print(f"       이번 추첨을 기록하려면: --pick={idx} --log")
        sys.exit(2)

    if "--log" in sys.argv:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        if not LOG.exists():
            LOG.write_text(
                "# 검수 기록\n\n"
                "> 저작 구조 B의 「검수·발행: 운영자」 표기를 뒷받침하는 기록이다.\n"
                "> `python analysis/review_pick.py <보고서> --log` 가 한 줄씩 붙인다.\n"
                "> 기록이 없는 편은 검수 표기를 달 수 없다.\n\n"
                "| 일시 | 문서 | 추첨 | 대조한 값 | 위치 |\n|---|---|---|---|---|\n",
                encoding="utf-8",
            )
        with LOG.open("a", encoding="utf-8") as fp:
            fp.write(f"| {stamp} | {path.name} | {idx}/{len(items)} | {token} | :{line_no} |\n")
        print(f"기록됨 -> {LOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

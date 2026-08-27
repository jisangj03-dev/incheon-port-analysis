"""지침 분량 트리거 감시 — §0.2 ①을 사람 기억에서 코드로 내린다.

§0.2는 「이 파일이 상한을 넘으면 감축 라운드를 연다」고 정하고
**「여유분은 적지 않는다 — `wc -c` 한 줄로 읽는다」**고 덧붙였다.
값을 안 박은 것은 옳았는데, **그 한 줄을 누가 언제 치는지는 아무 데도 없었다.**
사람이 기억해서 재는 규칙은 유실된다(사고 22) — 그래서 이 검사기가 대신 잰다.

2026-08-27 실측: 정정 2회 만에 여유가 **206 B**로 줄었다. 먹은 것은 **개정 이력**이고,
그것은 `docs/STATUS.md`가 이미 「§0.2이 예측하지 못한 증가 경로」로 적어 둔 그 경로다.
**예측돼 있었는데 아무도 안 재고 있었다.** 이 파일이 그 자리를 메운다.

  python analysis/check_guideline_size.py            # 재고 판정한다
  python analysis/check_guideline_size.py --selftest # 세 구간이 실제로 갈리는가

종료코드 0 = 여유 있음 / 1 = 임박(경고) / 2 = 트리거 도달.
**임박을 따로 둔 이유:** 넘은 뒤에 알면 이미 넘은 채로 개정이 쌓인다.
§0.2 ③이 「늘린 뒤에 줄이면 늘어난 채로 남는다」고 말한 것과 같은 논리다.
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# §0.2 ①. 이 값은 지침 조항이므로 여기 박는다 — 낡는 값이 아니라 기준이다.
#
# [2026-08-28 v6.0] 48,000 -> 38,000. **감축을 여기서 고정한다.**
#   v6.0 감축 라운드가 47,794 -> 35,999 B(-24.7%)로 줄였다. 상한을 그대로 두면
#   **줄인 만큼이 그대로 다시 채울 여유가 된다** — 12 KB짜리 빈칸을 남기는 것과 같다.
#   38,000은 실측치 위 약 2 KB다. §0.2 제로섬 규칙이 다음 조항부터 곧바로 문다.
LIMIT = 38000
NEAR = 1500  # 임박 구간. 개정 이력 한 행이 대략 이 크기라 「한 행 더 쓰면 넘는다」가 경고 시점이다.

PATH = os.path.join(os.path.expanduser("~"), "OneDrive", "문서", "본부", "프로젝트지침.md")


def verdict(size):
    if size > LIMIT:
        return 2, "트리거 ① 도달 — §0.2 감축 라운드 조건이다"
    if LIMIT - size <= NEAR:
        return 1, "임박 — 개정 이력 한 행이면 넘는다"
    return 0, "여유 있음"


def main():
    if not os.path.isfile(PATH):
        # 지침은 비공개 본부에 있다. 없는 기계에서는 **검사 불성립**이지 통과가 아니다.
        print("[불성립] 지침 파일을 못 찾았다: %s" % PATH)
        print("  이 저장소만 clone한 기계에서는 잴 수 없다. 통과로 치지 않는다.")
        return 2
    size = os.path.getsize(PATH)
    code, why = verdict(size)
    print("== 지침 분량 (§0.2 트리거 ①) ==")
    print("  현재 %d B / 상한 %d B / 여유 %d B" % (size, LIMIT, LIMIT - size))
    print("판정: %s" % why)
    if code:
        print("  -> 감축 방법은 §0.2 — 조항마다 「이 조항이 실제로 어떤 결정을 바꿨는가」를 묻는다.")
        print("  -> 감축 라운드 착수는 운영자 판단이다. §0.2 제로섬 규칙이 걸린다 — 늘린 만큼 회수한다.")
    return code


def selftest():
    print("── 인수시험: 구간 판정 ──")
    # 픽스처는 LIMIT 상대값으로만 쓴다. 절대값을 박으면 상한을 내릴 때 시험이 먼저 깨진다
    # (실제로 깨졌다 — v6.0에서 48,000 -> 38,000으로 내리자 「40000 B -> 여유」 픽스처가 FAIL했다).
    cases = [(LIMIT // 2, 0), (LIMIT - NEAR - 1, 0), (LIMIT - NEAR, 1), (LIMIT, 1), (LIMIT + 1, 2)]
    ok = True
    for size, want in cases:
        got, _ = verdict(size)
        hit = got == want
        ok = ok and hit
        print("  %s %7d B -> %d (기대 %d)" % ("OK  " if hit else "FAIL", size, got, want))
    print("통과" if ok else "실패")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

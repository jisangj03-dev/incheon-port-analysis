# -*- coding: utf-8 -*-
"""생성물 신선도 — **CSV 는 새 것인데 지면이 옛 것인** 상태를 push 순간에 말한다.

왜 있는가
---------
이 저장소에는 「손으로 옮겨 적지 않는다」를 걸고 **생성되는 산출물**이 넷 있다 —
`/terminals/` 지면 · 첫 화면 터미널 구획 · `_og/card.html` 표 · `/berths/` 지면.
전부 CSV 하나에서 만들어진다.

**그런데 생성은 사람이 부른다.** 다음 달 `collect_terminal_monthly.py` 를 돌려 CSV 가
바뀌었는데 `build_terminals_page.py` 를 잊으면, **지면은 지난달 숫자를 든 채로 남는다.**
그리고 그것은 **깨져 보이지 않는다** — 숫자가 있고 표가 그려지고 린터도 통과한다.

  사고 31 · 55 · 56 이 전부 같은 얼굴이었다 — **같은 값이 두 자리에 있고 한쪽만 갱신된다.**
  56의 처분이 「생성기로 옮긴다」였는데, **생성기를 부르는 일 자체는 여전히 손이다.**

그래서 push 순간에 한 번 친다. `check_review_log.py` 가 같은 자리에서 같은 일을 한다.

무엇을 보는가
-------------
각 생성기의 `--check` 를 돌린다. 그 안에서 **다시 생성해 현재 파일과 대조**하므로,
「CSV 가 바뀌었는가」가 아니라 **「지금 CSV 로 만들면 다른 것이 나오는가」**를 본다.
후자가 진짜 물음이다 — CSV 를 안 건드리고 생성기 코드만 고쳐도 갈라진다.

  python analysis/check_generated.py            # 경고. 종료 0
  python analysis/check_generated.py --strict   # 낡았으면 종료 1
  python analysis/check_generated.py --hook     # pre-push 에서 부른다 (조용히)
  python analysis/check_generated.py --selftest

**기본이 경고인 이유.** 여기서 막히는 것은 운영자의 손이고,
`check_status_fresh.py`·`check_review_log.py` 가 같은 자리에서 같은 선택을 했다.
차단 승격은 운영자 판단이다.

**§4 정지선표에 안 넣는다.** 이 검사가 집행하는 것은 §4가 아니라
「손으로 옮겨 적지 않는다」는 이 저장소의 작업 규율이다. `stopline_table.py` 의 표는
§4 조항 ↔ 기전 짝이므로 여기 끼우면 그 표가 거짓이 된다.

닿지 않는 곳
------------
1. **허브 저장소에서는 안 돈다.** 생성기가 인천 저장소에 있어서, 허브만 push 하면
   이 검사가 건너뛰어진다. 다만 **갈라짐의 원인은 CSV 변경**이고 CSV 는 인천에 있으므로,
   인천을 push 할 때 걸린다. **완전하지 않다는 것을 적어 둔다.**
2. **생성기가 없거나 죽으면 「모른다」로 센다.** 통과로 세지 않는다 —
   검사기가 안 돈 것을 통과로 읽는 것이 사고 26이다.
3. **생성기가 만들지 않는 손 편집 지면은 안 본다**(`/about/` 등). 그쪽은 애초에 원본이 하나다.
"""

import argparse
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (이름, 스크립트, 그 스크립트가 만드는 것)
GENERATORS = [
    ("터미널 지면 · 첫 화면 구획 · 링크 카드 표",
     "analysis/build_terminals_page.py",
     "허브 /terminals/ · index.md 생성 구획 · _og/card.html"),
    ("부두 지면",
     "analysis/build_berths_page.py",
     "허브 /berths/"),
    ("데이터 카탈로그",
     "analysis/build_datasets_page.py",
     "허브 /datasets/ — **CSV 가 늘거나 바뀌면 여기가 먼저 낡는다**"),
    ("첫 화면 스카이라인",
     "analysis/build_skyline.py",
     "허브 _includes/skyline.html — **데이터에서 오지 않는다.** "
     "낡을 일은 없지만 코드를 고치고 안 돌리면 갈라진다"),
    ("첫 화면 252개월 시계열",
     "analysis/build_series_chart.py",
     "허브 _includes/series252.html — **데이터에서 온다.** 원시 CSV 가 바뀌면 "
     "여기가 낡고, **장식과 달리 값을 지므로 낡으면 지면이 틀린 값을 말한다**"),
]

FRESH, STALE, UNKNOWN = "최신", "**낡았다**", "**모른다**"


def run_check(script):
    """(지위, 비고). **못 돌린 것을 통과로 세지 않는다**(사고 26)."""
    path = os.path.join(ROOT, script)
    if not os.path.exists(path):
        return UNKNOWN, "스크립트가 없다"
    try:
        p = subprocess.run([sys.executable, path, "--check"], cwd=ROOT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace", timeout=180)
    except Exception as e:
        return UNKNOWN, "%s: %s" % (type(e).__name__, e)
    out = (p.stdout or "").strip().replace("\n", " · ")
    if p.returncode == 0:
        return FRESH, out[-90:]
    if p.returncode == 1:
        # **터진 것을 판정으로 읽지 않는다.**
        #
        # 2026-09-02 실측: `build_series_chart.py --check` 가 cp949 콘솔에서
        # 통과 문장의 `—` 하나에 터졌다. 종료코드는 1 이고, 그것을 여기서
        # **「낡았다」**로 읽어 「다시 만들어라」를 냈다 — 지면은 멀쥰했다.
        #
        # 사고 26 은 「못 돌린 것을 통과로 세지 마라」였고 이 함수는 그쪽은
        # 지키고 있었다. **거꾸로가 비어 있었다** — 못 돌린 것을 **판정으로**
        # 세는 것. 통과가 아닌 것이 곰 판정인 것은 아니다.
        #
        # **닿지 않는 곳:** 파이썬 역추적이 없는 실패(생성기가 스스로
        # `sys.exit(1)` 을 부르며 조용히 죽는 경우)는 여전히 「낡았다」와 못 가른다.
        if "Traceback (most recent call last)" in (p.stdout or ""):
            return UNKNOWN, "생성기가 터졌다 — 낡음이 아니다 · %s" % out[-60:]
        return STALE, out[-90:]
    return UNKNOWN, "종료코드 %d · %s" % (p.returncode, out[-70:])


def verdicts():
    return [(name, script, made) + run_check(script)
            for name, script, made in GENERATORS]


# ── 인수시험 ────────────────────────────────────────────────────────────────

def selftest() -> int:
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 없는 스크립트를 통과로 세지 않는다 (사고 26) ──")
    st, why = run_check("analysis/없는생성기.py")
    chk("없으면 모른다", st, UNKNOWN)
    chk("이유를 적는다", why, "스크립트가 없다")
    chk("모른다는 최신이 아니다", st == FRESH, False)

    print("── 인수시험: 터진 것을 「낡았다」로 읽지 않는다 ──")
    # 2026-09-02 실측으로 생겼다. `build_series_chart.py --check` 가 cp949
    # 콘솔에서 터졌고, 종료코드 1 을 이 함수가 **「낡았다」로** 읽었다.
    # 지면은 멀쥰했다. **원인을 고치는 것으로는 다음 생성기에서 또 난다.**
    tmp_dir = os.path.join(ROOT, "analysis")
    boom = os.path.join(tmp_dir, "_selftest_boom.py")
    quiet = os.path.join(tmp_dir, "_selftest_quiet.py")
    try:
        with open(boom, "w", encoding="utf-8") as fh:
            fh.write("raise RuntimeError('boom')\n")
        with open(quiet, "w", encoding="utf-8") as fh:
            fh.write("import sys\nsys.exit(1)\n")
        st, why = run_check("analysis/_selftest_boom.py")
        chk("역추적을 남기고 터지면 모른다", st, UNKNOWN)
        chk("모른다는 낡은 것이 아니다", st == STALE, False)
        # **한계를 같이 박는다** — 조용히 죽는 것은 여전히 못 가른다.
        st2, _ = run_check("analysis/_selftest_quiet.py")
        chk("역추적 없이 죽으면 여전히 낡음으로 읽는다(한계)", st2, STALE)
    finally:
        for f in (boom, quiet):
            if os.path.exists(f):
                os.remove(f)

    print("── 인수시험: 실물 생성기 ──")
    vs = verdicts()
    # **수를 손에 들지 않는다** — 생성기가 늘 때마다 이 줄이 낡는다(사고 83·87).
    # 묻는 것은 「몇 개인가」가 아니라 **「등록된 것을 빠짐없이 보는가」**다.
    chk("등록된 생성기를 빠짐없이 본다", len(vs), len(GENERATORS))
    chk("시계열도 등록돼 있다",
        any("build_series_chart" in g[1] for g in GENERATORS), True)
    for name, script, made, st, why in vs:
        good = st in (FRESH, STALE, UNKNOWN)
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", name[:52], st))
    chk("지금은 전부 최신이어야 한다 (방금 생성했으므로)",
        sorted({v[3] for v in vs}), [FRESH])

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


# ── 본체 ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="생성되는 지면이 지금 CSV 와 어긋나는지 본다.")
    ap.add_argument("--strict", action="store_true", help="낡았으면 종료코드 1")
    ap.add_argument("--hook", action="store_true", help="pre-push 용 — 문제 있을 때만 말한다")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    vs = verdicts()
    bad = [v for v in vs if v[3] != FRESH]

    if a.hook and not bad:
        return 0

    if not a.hook:
        print("== 생성물 신선도 ==")
        for name, script, made, st, why in vs:
            print("  %-10s %s" % (st, name))
            print("             %s" % made)
            if st != FRESH:
                print("             %s" % why)

    if not bad:
        if not a.hook:
            print("\n생성물이 전부 지금 데이터와 맞는다.")
        return 0

    out = sys.stderr
    print("", file=out)
    print("생성물 %d건이 지금 데이터와 어긋난다." % len(bad), file=out)
    for name, script, made, st, why in bad:
        print("  · %s — %s" % (name, st), file=out)
        print("    다시 만든다:  python %s" % script, file=out)
    print("", file=out)
    print("  **깨져 보이지 않는 종류의 어긋남이다** — 숫자가 있고 표가 그려지고", file=out)
    print("  린터도 통과한다. 값만 지난달 것이다.", file=out)
    if a.strict:
        print("  --strict 라 여기서 멈춘다.", file=out)
        return 1
    print("  경고만 하고 통과시킨다. 막으려면 --strict.", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

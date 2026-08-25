"""유통 파일럿 계측기 — 실소요를 그때그때 찍는다.

왜 있는가
---------
`docs/유통파일럿.md`가 「사후 회상으로 채우지 않는다」고 선커밋했다(사고 18 —
롤링 지표는 당일 캡처가 아니면 영구 소실이다). 그런데 그 규칙이 문장으로만 있으면
결국 나중에 기억으로 채우게 된다. 사고 28의 구조 그대로다.

그래서 시각을 사람이 아니라 기계가 찍는다. 이 스크립트는 **시간만** 다룬다 —
게시물 문안은 만들지도 저장하지도 않는다. 그것이 측정 대상 자체이기 때문이다.

무엇을 재는가 (유통파일럿.md 선커밋)
------------------------------------
  구간 ① summary  요약 문안 작성
  구간 ② image    이미지·카드 제작   ← **편당 1회.** 채널마다 다시 만들지 않는다
  구간 ③ post     게시·렌더 확인
  채널 : github / site / linkedin

사용
----
  python analysis/pilot_timer.py start linkedin summary
  python analysis/pilot_timer.py stop
  python analysis/pilot_timer.py report          # 채널×구간 분 단위 집계
  python analysis/pilot_timer.py report --md     # 유통파일럿.md 표에 붙일 형태로

기록은 `docs/유통파일럿_기록.tsv`에 append-only로 쌓인다. 지우지 않는다.
"""

import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "docs" / "유통파일럿_기록.tsv"

CHANNELS = {"github": "GitHub 프로필 README", "site": "자체 사이트(허브)", "linkedin": "링크드인"}
PHASES = {"summary": "① 요약 작성", "image": "② 이미지 제작", "post": "③ 게시·확인"}
FMT = "%Y-%m-%d %H:%M:%S"


def rows():
    if not LOG.exists():
        return []
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("\t")
        if len(p) >= 4:
            out.append(p[:4])
    return out


def append(kind, channel, phase, stamp):
    new = not LOG.exists()
    with LOG.open("a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("# 유통 파일럿 실측 로그. append-only. 지우지 않는다.\n")
            f.write("# kind\tchannel\tphase\ttimestamp\n")
        f.write(f"{kind}\t{channel}\t{phase}\t{stamp}\n")


def open_run():
    """열려 있는 start가 있으면 (channel, phase, when) 반환."""
    last = None
    for kind, ch, ph, ts in rows():
        last = (ch, ph, ts) if kind == "start" else None
    return last


def cmd_start(argv):
    if len(argv) < 2:
        print("사용: start <github|site|linkedin> <summary|image|post>")
        sys.exit(2)
    ch, ph = argv[0], argv[1]
    # stderr는 cp949라 한글이 깨진다. 읽히지 않는 중단 사유는 없는 것과 같다(사고 15).
    if ch not in CHANNELS:
        print(f"[중단] 채널은 {list(CHANNELS)} 중 하나다. 받은 값: {ch}")
        sys.exit(2)
    if ph not in PHASES:
        print(f"[중단] 구간은 {list(PHASES)} 중 하나다. 받은 값: {ph}")
        sys.exit(2)
    o = open_run()
    if o:
        print(f"[중단] 이미 열려 있다 — {CHANNELS[o[0]]} / {PHASES[o[1]]} (시작 {o[2]})")
        print("       먼저 stop 하거나, 그 구간을 이어서 재려면 그대로 두고 stop 한다.")
        sys.exit(2)
    now = datetime.now()
    append("start", ch, ph, now.strftime(FMT))
    print(f"▶ 시작  {CHANNELS[ch]} / {PHASES[ph]}   {now.strftime('%H:%M:%S')}")
    if ph == "image":
        print("  ※ ②는 편당 1회다. 채널마다 다시 만들지 않는다(유통파일럿.md 정의).")


def cmd_stop():
    o = open_run()
    if not o:
        print("[중단] 열려 있는 구간이 없다. 먼저 start 한다.")
        sys.exit(2)
    ch, ph, started = o
    now = datetime.now()
    append("stop", ch, ph, now.strftime(FMT))
    mins = (now - datetime.strptime(started, FMT)).total_seconds() / 60
    print(f"■ 종료  {CHANNELS[ch]} / {PHASES[ph]}   {mins:.1f}분")


def totals():
    acc, open_at = {}, {}
    for kind, ch, ph, ts in rows():
        t = datetime.strptime(ts, FMT)
        if kind == "start":
            open_at[(ch, ph)] = t
        elif (ch, ph) in open_at:
            acc[(ch, ph)] = acc.get((ch, ph), 0.0) + (t - open_at.pop((ch, ph))).total_seconds() / 60
    return acc, open_at


def cmd_report(md=False):
    acc, still = totals()
    if not acc and not still:
        print("기록 없음. start 부터 한다.")
        return
    print("── 유통 파일럿 실측 ──")
    print(f"{'채널':<22}{'① 요약':>9}{'② 이미지':>10}{'③ 게시':>9}{'합계':>9}")
    grand = 0.0
    img_total = 0.0
    for ch, label in CHANNELS.items():
        vals = [acc.get((ch, p), 0.0) for p in PHASES]
        img_total += vals[1]
        s = sum(vals)
        grand += s
        print(f"{label:<22}{vals[0]:>9.1f}{vals[1]:>10.1f}{vals[2]:>9.1f}{s:>9.1f}")
    print("-" * 59)
    print(f"{'편당 합계(착수 포함)':<22}{'':>9}{'':>10}{'':>9}{grand:>9.1f}")
    print()
    print("판정 분모는 「편당 합계(반복분)」= 위에서 템플릿 착수 시간을 뺀 값이다.")
    print("템플릿 착수분은 사람이 판단해 뺀다 — 기계가 「이번이 착수였는지」를 알 수 없다.")
    if img_total:
        print(f"참고: ② 이미지 총계 {img_total:.1f}분. §7 상한은 카드 1건 1시간이다.")
    if still:
        for (ch, ph), t in still.items():
            print(f"⚠ 아직 열려 있음 — {CHANNELS[ch]} / {PHASES[ph]} (시작 {t.strftime('%H:%M:%S')})")
    if md:
        print()
        print("| 채널 | ① 요약 작성 | ② 이미지 제작 | ③ 게시·확인 | 합계 | 비고 |")
        print("|---|---|---|---|---|---|")
        for ch, label in CHANNELS.items():
            v = [acc.get((ch, p), 0.0) for p in PHASES]
            print(f"| {label} | {v[0]:.1f} | {v[1]:.1f} | {v[2]:.1f} | {sum(v):.1f} | |")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    c = sys.argv[1]
    if c == "start":
        cmd_start(sys.argv[2:])
    elif c == "stop":
        cmd_stop()
    elif c == "report":
        cmd_report("--md" in sys.argv)
    else:
        print(f"[중단] 알 수 없는 명령: {c}. start / stop / report")
        sys.exit(2)


if __name__ == "__main__":
    main()

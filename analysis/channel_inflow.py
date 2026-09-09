# -*- coding: utf-8 -*-
"""채널 유입 집계 — **게시한 뒤 어느 채널에서 읽혔는가.**

왜 있는가
---------
채널을 여닫는 판단이 감으로 가면 §1.4 3층이 무너진다. 3층은 **「기록만 하고 판정에 안 쓴다」**인데,
**기록조차 없으면 「안 쓴다」가 아니라 「모른다」다.** 둘은 다르다.

측심이 `channel_views` 에 날짜별·채널별 수를 쌓는다(식별자 없음 · 버킷 이름과 수뿐).
이 파일은 그것을 읽어 표로 낸다.

  python analysis/channel_inflow.py              # 채널별 합계
  python analysis/channel_inflow.py --days 14    # 최근 N일
  python analysis/channel_inflow.py --write      # 본부에 적는다
  python analysis/channel_inflow.py --selftest

**이 수는 공개 저장소에 안 들어간다** — 지침 §4.1-3(채널 성과 원자료는 비공개).
`--write` 는 `본부\채널유입.md` 에 쓴다. **판정에 안 쓰는 숫자를 공개하면 판정에 쓰게 된다.**

닿지 않는 곳
------------
· **이것은 방문자 수가 아니다.** 탭 세션당 1, 자동 브라우저 제외, DNT 존중,
  `?src=` 나 referrer 가 있을 때만 채널이 갈린다. **referrer 는 자주 비어 온다** —
  링크드인 앱, 메신저, 사내 프록시에서 그렇다. 그 몫은 전부 `direct` 로 샌다.
· 그러므로 **채널 사이 비율은 읽되, 절대 수를 성과로 읽지 않는다.**
· 배포 전 게시물의 유입은 `other` 로 들어온다(그 판에 이 집계가 없었다).
· `higgsfield` CLI 와 로그인에 기댄다. 만료면 **[미확인]이지 0이 아니다.**
"""

import argparse
import io
import json
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HQ = os.path.join(os.path.expanduser("~"), "OneDrive", "문서", "본부")
OUT = os.path.join(HQ, "채널유입.md")

SITE = "56527534-163d-43d6-a160-b30862c6e5a1"   # 측심
NAMES = {"li": "링크드인", "gn": "GeekNews", "dq": "디스콰이엇",
         "other": "그 밖", "direct": "직접·불명"}


def cli():
    """`higgsfield` 실행 파일. **윈도에서는 `.cmd` 셔임이라 이름만으로는 안 잡힌다** —
    `shutil.which` 가 PATHEXT 를 본다. 못 찾으면 None 이고, 그때는 **없는 것**이다."""
    import shutil
    return shutil.which("higgsfield")


def query(sql, site=SITE, timeout=90):
    """(행, 오류). **못 읽은 것을 0으로 세지 않는다** — 오류면 행이 None 이다."""
    exe = cli()
    if not exe:
        return None, "higgsfield CLI 가 PATH 에 없다"
    try:
        p = subprocess.run(
            [exe, "website", "db", "query", site, "--sql", sql, "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError:
        return None, "higgsfield CLI 를 못 실행했다"
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)
    out = (p.stdout or "").strip()
    if p.returncode != 0:
        return None, out.splitlines()[-1][:160] if out else "종료코드 %d" % p.returncode
    try:
        return json.loads(out).get("rows", []), None
    except Exception:
        # 테이블이 아직 없으면(배포 전) 여기로 온다 — 그것도 0이 아니라 「모름」이다.
        return None, out.splitlines()[-1][:160] if out else "JSON 이 아니다"


def tally(days=None):
    where = ""
    if days:
        where = " WHERE day >= date('now', '-%d day')" % int(days)
    rows, err = query(
        "SELECT src, SUM(count) AS n, MIN(day) AS a, MAX(day) AS b "
        "FROM channel_views%s GROUP BY src ORDER BY n DESC" % where)
    return rows, err


def render(rows, days):
    lines = []
    span = "최근 %d일" % days if days else "전 구간"
    if rows is None:
        lines.append("**[미확인]** — 읽지 못했다. **0이 아니다.**")
        return lines, 0
    total = sum(int(r.get("n") or 0) for r in rows)
    lines.append("| 채널 | 수 | 비중 | 처음 | 마지막 |")
    lines.append("|---|---:|---:|---|---|")
    for r in rows:
        n = int(r.get("n") or 0)
        pct = ("%.1f%%" % (100.0 * n / total)) if total else "—"
        lines.append("| %s | %d | %s | %s | %s |"
                     % (NAMES.get(r.get("src"), r.get("src")), n, pct,
                        r.get("a") or "", r.get("b") or ""))
    lines.append("| **합계** | **%d** | | | |" % total)
    lines.append("")
    lines.append("창: %s · **탭 세션당 1 · 자동 브라우저 제외 · DNT 존중**." % span)
    lines.append("**`direct` 에는 referrer 를 안 보내는 앱·메신저 유입이 섞인다** — "
                 "채널 사이 비율은 읽되 절대 수를 성과로 읽지 않는다.")
    return lines, total


def main(days=None, write=False):
    rows, err = tally(days)
    print("== 채널 유입 (측심) ==")
    if err:
        print("**[미확인]** %s" % err)
        print("  **0으로 읽지 않는다.** 로그인 만료면 운영자가 자기 터미널에서 다시 로그인한다.")
        print("  테이블이 아직 없으면 배포 전이다 — `migrations/0004_channel.sql` 이 배포 때 선다.")
        return 2
    lines, total = render(rows, days)
    for l in lines:
        print(l)
    if not total:
        print("\n아직 0이다 — 게시 전이거나 배포 직후다.")
    if write:
        if not os.path.isdir(HQ):
            print("\n본부 폴더가 없다 — 안 썼다.")
            return 0
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(
            "# 채널 유입 (측심)\n\n"
            "> **비공개다**(지침 §4.1-3 · 채널 성과 원자료). 공개 저장소에 안 옮긴다.\n"
            "> **§1.4 3층** — 기록만 한다. 어떤 결정도 이 숫자로 정당화하지 않는다.\n"
            "> 생성 `python analysis/channel_inflow.py --write` · 갱신 %s\n\n"
            % time.strftime("%Y-%m-%d %H:%M") + "\n".join(lines) + "\n")
        print("\n적었다: %s" % OUT)
    return 0


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 못 읽은 것을 0으로 안 세는가 (사고 26) ──")
    lines, total = render(None, None)
    chk("None 은 [미확인]로 낸다", any("[미확인]" in l for l in lines), True)
    chk("None 은 0이 아니라고 적는다", any("0이 아니다" in l for l in lines), True)
    chk("합계를 0으로 안 만든다", total, 0)

    print("── 인수시험: 표 ──")
    rows = [{"src": "li", "n": 30, "a": "2026-09-10", "b": "2026-09-12"},
            {"src": "direct", "n": 10, "a": "2026-09-10", "b": "2026-09-12"}]
    lines, total = render(rows, 7)
    chk("합계를 낸다", total, 40)
    chk("한글 채널명을 쓴다", any("링크드인" in l for l in lines), True)
    chk("비중을 낸다", any("75.0%" in l for l in lines), True)
    chk("창을 적는다", any("최근 7일" in l for l in lines), True)
    chk("direct 의 한계를 적는다", any("referrer 를 안 보내는" in l for l in lines), True)

    print("── 인수시험: 채널 이름이 측심 쪽과 같은가 ──")
    p = os.path.join(ROOT, "..", "sounding", "app", "src", "lib", "api", "views.functions.ts")
    if os.path.exists(p):
        src = io.open(p, encoding="utf-8", errors="replace").read()
        import re
        m = re.search(r"CHANNEL_SOURCES\s*=\s*\[(.*?)\]", src, re.S)
        got = sorted(re.findall(r'"([a-z]+)"', m.group(1))) if m else []
        chk("측심이 쓰는 버킷과 이 파일의 이름표가 같다", got, sorted(NAMES))
    else:
        print("  (측심 폴더가 없다 — 이 시험은 **미실행**이지 통과가 아니다)")

    print("── 인수시험: SQL 에 창이 붙는가 ──")
    import re as _re
    # `--days` 가 실제로 WHERE 를 만드는지. 안 붙으면 「최근 N일」이 거짓말이 된다.
    src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
    chk("days 가 WHERE 를 만든다", bool(_re.search(r"day >= date\('now', '-%d day'\)", src)), True)

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="채널 유입 집계 (측심 D1)")
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--write", action="store_true", help="본부에 적는다")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else main(a.days, a.write))

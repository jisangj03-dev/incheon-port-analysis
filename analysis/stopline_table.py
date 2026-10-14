"""정지선 ↔ 기전 대조표 — 조항 문면과 「그것이 실제로 집행하는 명제」를 나란히 놓는다.

왜 있는가
---------
2026-08-27, `hook_stopline.py`를 만들며 **「push 정지선을 코드로 내렸다」**고 적었다.
§4 문면은 **「push는 운영자만」 — 주체 규정**인데, 그 훅의 기전은 **경로 규정**이었다.
거기서 내가 낸 교훈이 이것이다 —

  **정지선을 코드로 내릴 때 「이 코드가 집행하는 명제」를 조항 문면과 나란히 놓는다.**

**그런데 그 교훈을 훅 주석 한 곳에만 적었다.** 나란히가 아니었다.
§4 표를 읽는 쪽은 그 주석까지 안 연다(운영자 지적, 2026-08-27).

무엇을 하는가
-------------
가드 파일이 **자기 명제와 한계를 스스로 선언**하고(`정지선-집행/명제/한계` 3줄),
이 스크립트가 그것을 모아 표로 낸다. **표는 손으로 안 쓴다 — 생성한다.**
두 자리에 손으로 적으면 반드시 갈라진다(사고 31).

  python analysis/stopline_table.py            # 표를 낸다
  python analysis/stopline_table.py --check    # STATUS의 생성 블록이 최신인가 (종료코드로 답한다)
  python analysis/stopline_table.py --write    # STATUS의 생성 블록을 갱신한다

`--check`가 잡는 것: **가드를 새로 만들고 짝을 안 지은 경우.** 이번에 실제로 그랬다.

닿지 않는 곳
------------
선언 3줄이 **맞는지는 안 본다.** 파일이 자기 한계를 정직하게 적었는지는 사람이 읽어야 한다.
이 도구가 보장하는 것은 **「빈칸이 없다」와 「표가 파일과 같다」**뿐이다.
"""

import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(ROOT, "docs", "STATUS.md")
BEGIN = "<!-- 정지선표:시작 (생성됨. 손으로 고치지 마라 — analysis/stopline_table.py) -->"
END = "<!-- 정지선표:끝 -->"

FIELDS = ("집행", "명제", "한계")
PAT = {f: re.compile(r"^#?\s*정지선-%s:\s*(.+?)\s*$" % f, re.M) for f in FIELDS}


def scan():
    """analysis/ 의 파일에서 선언 3줄을 모은다. 하나라도 빠지면 그 자리를 비워 둔다."""
    rows = []
    d = os.path.join(ROOT, "analysis")
    for name in sorted(os.listdir(d)):
        if not name.endswith((".py", ".sh")):
            continue
        path = os.path.join(d, name)
        try:
            text = io.open(path, encoding="utf-8").read()
        except Exception:
            continue
        # **substring이 아니라 선언 형태로 판정한다.** 처음엔 `"정지선-집행" in text`로 걸렀더니
        # **이 생성기 자신의 설명문**이 걸려 빈칸 행이 나왔다(2026-08-27). 낱말을 언급하는 것과
        # 선언하는 것은 다르다 — `hook_stopline`이 따옴표 안을 지우는 것과 같은 구분이다.
        if not PAT["집행"].search(text):
            continue
        got = {}
        for f, pat in PAT.items():
            m = pat.search(text)
            got[f] = m.group(1).strip() if m else ""
        rows.append((name, got))
    return rows


def render(rows):
    out = [BEGIN, "",
           "**정지선 ↔ 기전 대조표.** 지침 §4의 조항 문면과 **그것을 실제로 집행하는 코드의 명제**를",
           "나란히 놓는다. **문면과 기전은 같지 않다** — 다르면 다르다고 적는 것이 이 표의 목적이다(사고 46).",
           "",
           "> **이 블록은 생성된다. 손으로 고치지 마라.** 정본은 각 가드 파일의 `정지선-집행/명제/한계` 3줄이다.",
           "> `python analysis/stopline_table.py --check` (부트블록 3번) · 갱신은 `--write`.",
           "",
           "| 집행 파일 | §4 조항 (문면) | **이 코드가 집행하는 명제** | **닿지 않는 곳** |",
           "|---|---|---|---|"]
    for name, g in rows:
        out.append("| `%s` | %s | %s | %s |" % (
            name, g["집행"] or "**[빈칸]**", g["명제"] or "**[빈칸]**", g["한계"] or "**[빈칸]**"))
    out += ["",
            "**정지선 중 코드가 집행하지 않는 것은 이 표에 없다** — 데이터 지위·공개 경계·문서 규율 일부가 그렇다.",
            "**없다는 것이 곧 「사람이 지킨다」는 뜻이고, 그것도 사실이므로 적어 둔다.**",
            "", END]
    return "\n".join(out)


def current_block():
    s = io.open(STATUS, encoding="utf-8").read()
    if BEGIN not in s or END not in s:
        return None, s
    i = s.index(BEGIN)
    j = s.index(END) + len(END)
    return s[i:j], s


def main(argv):
    rows = scan()
    blanks = [(n, f) for n, g in rows for f in FIELDS if not g[f]]
    want = render(rows)

    if "--write" in argv:
        cur, s = current_block()
        if cur is None:
            print("STATUS에 생성 블록 표지가 없다. 아래를 원하는 자리에 한 번 붙여라:\n")
            print(want)
            return 2
        io.open(STATUS, "w", encoding="utf-8", newline="\n").write(s.replace(cur, want))
        print("갱신: docs/STATUS.md (행 %d건)" % len(rows))
        return 0

    if "--check" in argv:
        ok = True
        print("── 정지선 대조표 ──")
        print("  선언한 가드 %d건" % len(rows))
        if blanks:
            ok = False
            for n, f in blanks:
                print("  FAIL %s 의 「정지선-%s」가 비어 있다" % (n, f))
        cur, _ = current_block()
        if cur is None:
            ok = False
            print("  FAIL STATUS에 생성 블록이 없다 — 표가 어디에도 없다")
        elif cur != want:
            ok = False
            print("  FAIL STATUS의 표가 파일 선언과 다르다 (가드를 만들고 짝을 안 지었거나 낡았다)")
            print("       -> python analysis/stopline_table.py --write")
        else:
            print("  OK   STATUS의 표가 파일 선언과 일치한다")
        print("통과" if ok else "실패")
        return 0 if ok else 1

    print(want)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# -*- coding: utf-8 -*-
"""사이트 상수 ↔ 대장 — 측심(`../sounding`)이 화면에 박은 수치가 `docs/FACTS.md`·판정결과 문서와 같은가.

왜 있는가
---------
측심의 지표 타일·부두 막대·판정표·챕터 문안은 **값을 코드에 적어 둔다**(TSX 상수). 대장이 바뀌면
사이트는 아무 소리 없이 낡는다 — 같은 값이 두 자리에 있고 한쪽만 갱신되는 사고 31 의 얼굴이다.
발행본은 `lint_publish.py` 가 대장과 맞대는데, 사이트는 아무도 안 맞대고 있었다(2026-09-03 자평).

무엇을 보는가
-------------
1. 지표 타일 넷(`metrics.tsx`) — 값+단위가 대장 첫 칸에 있고, 타일이 적은 지위(검증/관측)가 대장 지위와 같다.
   타일이 가리키는 **대장 행 번호**(`row`)가 정확히 그 값의 행인가.
2. 부두 막대(`berths.tsx`) — 합계 282 와 소계 184·66·32 천TEU 가 대장에 있다.
3. 252개월 그래프의 최소·최대(`data/series252.json`) — 대장의 1.9435배(2005-07)·179.2678배(2020-05)와 같다.
4. 판정표(`verdicts.tsx`) — #09 V1~V4 · #10 W1~W4 의 PASS/FAIL 과 결과 문구의 숫자가 `docs/09_판정결과.md`·`10_판정결과.md` 표와 같다.
5. 챕터 문안(`scroll-scrub-scenes.ts`)의 숫자가 전부 대장 값 안에 있다.
6. [2026-09-08] **자료 창 하나** — `src/data/window.ts` 의 `DATA_WINDOW` 가 대장의 가장 새 「단월」 창과 같고,
   사이트가 「YYYY-MM 단월」·「YYYY년 M월」로 적은 단월 창(지표 타일·부두·챕터·푸터)이 전부 그 값이다.
   푸터의 「자료 기준」이 손으로 적힌 채 낡던 자리다(사고 31). 부두 막대의 몫 셋(65.2·23.4·11.3%)도 §2 가 대장에서 찾는다.

7. [2026-09-11] **공유 카드의 선언 ↔ 실물** — `__root.tsx` 가 글자로 적은 `og:image:width/height` 와
   `app-meta.json` 의 `og_image_url` 이 가리키는 **파일의 실제 화소**가 같은가. **망을 안 탄다.**
   둘이 갈려도 화면에서는 안 보인다 — 보는 것은 크롤러뿐이다. 2026-09-10 실측: 선언 1200×630 ·
   실물 1600×1073(마켓플레이스 커버가 `og_image_url` 자리에 들어가 있었다).

닿지 않는 곳
------------
· 값이 **맞는지**는 안 본다 — 대장과 **같은지**만 본다. 대장이 틀리면 같이 틀린다(대장은 `check_facts.py` 가 본다).
· 문장이 맞는지는 안 본다. 숫자만 본다.
· 측심 저장소가 없는 기계에서는 「모름」이다 — 통과로 세지 않는다.
· **카드가 실제로 어떻게 보이는지는 안 본다** — 크기가 선언과 같은지만 본다.
  링크드인·슬랙이 그것을 어떻게 자르는지는 붙여넣어 봐야 안다(사고 73).

  python analysis/check_site_facts.py             # 판정
  python analysis/check_site_facts.py --hook      # pre-push 용 — 문제 있을 때만 말한다
  python analysis/check_site_facts.py --selftest
"""

import argparse
import io
import json
import os
import re
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = os.path.normpath(os.path.join(ROOT, "..", "sounding", "app"))
FACTS = os.path.join(ROOT, "docs", "FACTS.md")
JUDGE = {"#09": os.path.join(ROOT, "docs", "09_판정결과.md"), "#10": os.path.join(ROOT, "docs", "10_판정결과.md")}


def read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


# ── 대장 ────────────────────────────────────────────────────────────────────
def facts_rows(text):
    """행 번호(1부터) → (값 칸, 창 칸, 지위 칸). 표 행만."""
    out = {}
    for i, line in enumerate(text.splitlines(), 1):
        if not line.startswith("| "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("값", "---", "지위"):
            continue
        out[i] = (cells[0], cells[1], cells[2])
    return out


def find_value(rows, value):
    """값 칸이 정확히 `value` 인 행들."""
    return [n for n, (v, _, _) in rows.items() if v == value]


# ── 사이트 ──────────────────────────────────────────────────────────────────
def site_metrics(src):
    """metrics.tsx 의 { value, unit, label, window, row } 목록."""
    out = []
    for m in re.finditer(r'\{\s*value:\s*"([^"]+)",\s*unit:\s*"([^"]*)",\s*label:\s*"[^"]*",\s*window:\s*"([^"]*)"(?:,\s*row:\s*(\d+))?', src):
        out.append({"value": m.group(1), "unit": m.group(2), "window": m.group(3), "row": int(m.group(4)) if m.group(4) else None})
    return out


def site_berths(src):
    total = re.search(r"const total = (\d+);", src)
    cells = re.findall(r'name:\s*"([^"]+)",\s*teu:\s*(\d+)', src)
    return (int(total.group(1)) if total else None), [(n, int(t)) for n, t in cells]


def site_verdicts(src):
    rows = []
    for m in re.finditer(r'id:\s*"([^"]+)",\s*rule:\s*"([^"]+)",\s*window:\s*"([^"]+)",\s*result:\s*"([^"]+)",\s*verdict:\s*"(PASS|FAIL)"', src):
        rows.append({"id": m.group(1), "rule": m.group(2), "window": m.group(3), "result": m.group(4), "verdict": m.group(5)})
    return rows


def judge_rows(text):
    """판정결과 표에서 (V1|W1 …) → (결과 칸, PASS/FAIL)."""
    out = {}
    for line in text.splitlines():
        m = re.match(r"\|\s*([VW]\d)\b[^|]*\|[^|]*\|[^|]*\|([^|]*)\|\s*\*\*(PASS|FAIL)\*\*", line)
        if m:
            out[m.group(1)] = (m.group(2).strip(), m.group(3))
    return out


def numbers(s):
    """문자열 안의 수(정수·소수·분수) 집합. 「7/7」은 그대로 한 토큰."""
    return set(re.findall(r"\d+(?:[.,]\d+)?(?:/\d+)?", s))


# ── 판정 ────────────────────────────────────────────────────────────────────
def check(site=SITE, facts_path=FACTS, judge_paths=JUDGE, window_path=None):
    """(문제 목록, 검사 건수, 모름 사유)."""
    if not os.path.isdir(site):
        return [], 0, "측심 저장소가 없다: %s" % site
    problems, n = [], 0
    rows = facts_rows(read(facts_path))
    values = {v for v, _, _ in rows.values()}

    # 1. 지표 타일
    for m in site_metrics(read(os.path.join(site, "src", "components", "site", "metrics.tsx"))):
        n += 1
        key = m["value"] + m["unit"]
        if m["unit"] == "/252":                      # 252 + /252 ↔ 대장 「252개월 … 252/252」
            hit = [r for r in find_value(rows, "252개월") if "252/252" in rows[r][1]]
        else:
            hit = find_value(rows, key)
        if not hit:
            problems.append("지표 %s — 대장에 그 값이 없다" % key)
            continue
        status = "검증" if m["window"].endswith("검증") else "관측" if m["window"].endswith("관측") else "?"
        if rows[hit[0]][2] != status:
            problems.append("지표 %s — 사이트는 「%s」, 대장 %d행은 「%s」" % (key, status, hit[0], rows[hit[0]][2]))
        if m["row"] is not None and m["row"] not in hit:
            problems.append("지표 %s — 사이트가 가리키는 대장 %d행에 그 값이 없다(실제 %s행)" % (key, m["row"], ",".join(map(str, hit))))

    # 2. 부두
    total, cells = site_berths(read(os.path.join(site, "src", "components", "site", "berths.tsx")))
    for label, teu in [("합계", total)] + cells:
        n += 1
        if not find_value(rows, "%d 천TEU" % teu):
            problems.append("부두 %s %d천TEU — 대장에 없다" % (label, teu))
    # 막대가 찍는 몫(teu ÷ 합계 · 소수 첫째)도 대장 행이어야 한다 — 2026-09-08 까지 65.2% 만 등재돼 있었다.
    for label, teu in cells:
        n += 1
        share = "%.1f%%" % (teu / total * 100)
        if not find_value(rows, share):
            problems.append("부두 %s 몫 %s — 대장에 없다" % (label, share))

    # 3. 시계열 최소·최대
    pts = json.load(io.open(os.path.join(site, "src", "data", "series252.json"), encoding="utf-8"))
    lo = min(pts, key=lambda p: p["r"]); hi = max(pts, key=lambda p: p["r"])
    for tag, p in (("최소", lo), ("최대", hi)):
        n += 1
        hit = find_value(rows, "%s배" % p["r"])
        if not hit or p["m"] not in rows[hit[0]][1]:
            problems.append("시계열 %s %s배(%s) — 대장과 다르다" % (tag, p["r"], p["m"]))
    n += 1
    if len(pts) != 252:
        problems.append("시계열 점이 %d개다(252 이어야 한다)" % len(pts))

    # 4. 판정표
    site_rows = site_verdicts(read(os.path.join(site, "src", "components", "site", "verdicts.tsx")))
    judged = {}
    for rep, path in judge_paths.items():
        for k, v in judge_rows(read(path)).items():
            judged[rep + " " + k] = v
    for r in site_rows:
        n += 1
        j = judged.get(r["id"])
        if not j:
            problems.append("판정 %s — 판정결과 문서에 없다" % r["id"])
            continue
        if j[1] != r["verdict"]:
            problems.append("판정 %s — 사이트 %s, 문서 %s" % (r["id"], r["verdict"], j[1]))
        missing = numbers(r["result"]) - numbers(j[0])
        if missing:
            problems.append("판정 %s — 결과의 수 %s 가 문서 결과 칸에 없다" % (r["id"], sorted(missing)))

    # 5. 챕터 문안의 수
    scenes = read(os.path.join(site, "src", "scroll-scrub-scenes.ts"))
    for m in re.finditer(r'(?:body|headline|title):\s*"([^"]+)"', scenes):
        for num in re.findall(r"\d+(?:\.\d+)?(?=%|천TEU|개월|/)", m.group(1)):
            n += 1
            if not any(v.startswith(num) for v in values) and num not in ("252",):
                problems.append("챕터 문안의 %s — 대장 값에 없다" % num)
    # 6. 자료 창 하나
    wpath = window_path or os.path.join(site, "src", "data", "window.ts")
    wm = re.search(r'DATA_WINDOW\s*=\s*"(\d{4}-\d{2})"', read(wpath)) if os.path.exists(wpath) else None
    n += 1
    if not wm:
        problems.append("src/data/window.ts 의 DATA_WINDOW 를 못 읽었다")
    else:
        win = wm.group(1)
        newest = max(re.findall(r"(\d{4}-\d{2}) 단월", "\n".join(w for _, w, _ in rows.values())) or ["0000-00"])
        if newest != win:
            problems.append("DATA_WINDOW %s — 대장의 가장 새 단월 창은 %s" % (win, newest))
        for fn in ("components/site/metrics.tsx", "components/site/berths.tsx", "components/site/footer.tsx", "scroll-scrub-scenes.ts"):
            src = read(os.path.join(site, "src", fn))
            for lit in site_windows(src):
                n += 1
                if lit != win:
                    problems.append("%s 의 단월 창 %s — DATA_WINDOW %s 와 다르다" % (fn, lit, win))
    # 7. **공유 카드 — 선언한 크기와 파일의 실제 화소가 같은가** [2026-09-11]
    #    `__root.tsx` 가 `og:image:width/height` 를 **글자로 적어 두고**, 실제 이미지는
    #    `app-meta.json` 의 `og_image_url` 이 가리킨다. **둘이 갈려도 화면에서는 안 보인다** —
    #    보는 것은 크롤러뿐이다. 2026-09-10 실측: 선언 1200×630 · 실물 1600×1073(마켓플레이스
    #    커버가 `og_image_url` 자리에 들어가 있었다). 링크드인이 미리보기를 못 만들던 자리다.
    #    **조심으로 안 되는 것은 장치로 막는다**(사고 75).
    problems2, n2 = og_card(site)
    problems += problems2
    n += n2
    return problems, n, None


def og_card(site):
    """공유 카드의 **선언 ↔ 실물**. 반환 (문제 목록, 검사 건수).

    **망을 안 탄다** — 선언도 이미지도 저장소 안에 있다.
    **Pillow 가 없으면 「못 쟀다」를 문제로 올린다** — 0 건이 「맞다」로 읽히면 안 된다(사고 26).
    """
    problems, n = [], 0
    root = read(os.path.join(site, "src", "routes", "__root.tsx"))
    metaf = os.path.join(site, "src", "app-meta.json")
    if not root or not os.path.exists(metaf):
        return ["공유 카드 — `__root.tsx` 나 `app-meta.json` 을 못 읽었다"], 1
    w = re.search(r'"og:image:width",\s*content:\s*"(\d+)"', root)
    h = re.search(r'"og:image:height",\s*content:\s*"(\d+)"', root)
    if not (w and h):
        return ["공유 카드 — `og:image:width/height` 선언을 못 찾았다"], 1
    want = (int(w.group(1)), int(h.group(1)))
    try:
        url = (json.load(io.open(metaf, encoding="utf-8")).get("og_image_url") or "")
    except Exception as e:
        return ["공유 카드 — `app-meta.json` 을 못 읽었다: %s" % type(e).__name__], 1
    rel = url.split("/assets/", 1)[-1] if "/assets/" in url else None
    if not rel:
        return ["공유 카드 — `og_image_url` 이 이 사이트의 `/assets/` 를 안 가리킨다: %s" % url[:60]], 1
    path = os.path.join(site, "public", "assets", *rel.split("/"))
    n += 1
    if not os.path.exists(path):
        return ["공유 카드 — `og_image_url` 이 가리키는 파일이 없다: %s" % rel], n
    try:
        from PIL import Image
        got = Image.open(path).size
    except ImportError:
        return ["공유 카드 — **Pillow 가 없어 못 쟀다.** 통과가 아니다"], n
    except Exception as e:
        return ["공유 카드 — 이미지를 못 열었다(%s): %s" % (type(e).__name__, rel)], n
    if got != want:
        problems.append("공유 카드 — 선언 %d×%d 인데 실물은 %d×%d 다 (%s). "
                        "크롤러만 보는 자리라 화면으로는 안 드러난다"
                        % (want[0], want[1], got[0], got[1], rel))
    return problems, n


def site_windows(src):
    """사이트 문안의 단월 창 — 「YYYY-MM 단월」과, 범위(부터·까지)가 아닌 「YYYY년 M월」. YYYY-MM 꼴로 낸다."""
    out = re.findall(r"(\d{4}-\d{2}) 단월", src)
    for y, m in re.findall(r"(\d{4})년 (\d{1,2})월(?!부터|까지)", src):
        out.append("%s-%02d" % (y, int(m)))
    return out


def report(hook=False, strict=False):
    problems, n, unknown = check()
    if unknown:
        msg = "**모름** — %s. 통과로 세지 않는다." % unknown
        print(msg, file=sys.stderr if hook else sys.stdout)
        return 2
    if not problems:
        if not hook:
            print("사이트 상수 %d건이 대장·판정결과와 같다." % n)
            print("**값이 맞는지는 안 본다** — 대장과 같은지만 본다. 대장은 check_facts 가 본다.")
        return 0
    out = sys.stderr if hook else sys.stdout
    print("\n사이트 상수가 대장과 어긋난다 — %d건 (검사 %d건)." % (len(problems), n), file=out)
    for p in problems:
        print("  · " + p, file=out)
    print("  **사이트는 조용히 낡는다** — 값이 있고 표가 그려지고 린터도 통과한다(사고 31).", file=out)
    if hook and not strict:
        print("  경고만 하고 통과시킨다. 막으려면 --strict.", file=out)
        return 0
    return 1


# ── 인수시험 ────────────────────────────────────────────────────────────────
def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-46s %s" % ("OK  " if good else "FAIL", label, "" if good else "-> %r" % (got,)))

    print("── 인수시험: 파서 ──")
    rows = facts_rows("| 값 | 창 | 지위 |\n|---|---|---|\n| 85.1% | 2025년 · 비중 | 관측 |\n| 252개월 | 2005-01~2025-12 · 252/252 | 검증 |\n")
    chk("표 행만 읽는다", sorted(rows), [3, 4])
    chk("값으로 행을 찾는다", find_value(rows, "85.1%"), [3])
    chk("판정 표를 읽는다", judge_rows("| V3 수출 비중 | 연간 ≥ 85.0% | 7개 연도 | 6/7 성립 · **2013 미성립(84.1%)** | **FAIL** |"),
        {"V3": ("6/7 성립 · **2013 미성립(84.1%)**", "FAIL")})
    chk("수를 뽑는다", numbers("6/7 성립, 2013 미성립(84.1%)"), {"6/7", "2013", "84.1"})
    chk("지표 상수를 읽는다", site_metrics('{ value: "85.1", unit: "%", label: "x", window: "2025년 · 관측", row: 29 },'),
        [{"value": "85.1", "unit": "%", "window": "2025년 · 관측", "row": 29}])
    chk("단월 창을 읽는다(범위는 뺀다)", site_windows("2026-07 단월 · 2026년 7월 한 달 · 2005년 1월부터 2025년 12월까지"),
        ["2026-07", "2026-07"])

    print("── 인수시험: 실물 ──")
    problems, n, unknown = check()
    chk("측심을 찾는다(없으면 모름)", unknown is None or "없다" in unknown, True)
    if unknown is None:
        chk("지금 실물이 어긋나지 않는다", problems, [])
        chk("검사 건수가 0 이 아니다", n > 0, True)
        # **잡는 쪽도 친다** — 값 하나를 바꾼 대장 사본으로 돌리면 걸려야 한다(사고 26).
        with tempfile.TemporaryDirectory() as d:
            fake = os.path.join(d, "FACTS.md")
            io.open(fake, "w", encoding="utf-8").write(read(FACTS).replace("| 85.1% |", "| 85.2% |", 1))
            p2, _, _ = check(facts_path=fake)
            chk("대장 값이 바뀌면 잡는다", any("85.1%" in p for p in p2), True)
            fake_j = dict(JUDGE)
            jf = os.path.join(d, "09.md")
            io.open(jf, "w", encoding="utf-8").write(read(JUDGE["#09"]).replace("| **PASS** |", "| **FAIL** |", 1))
            fake_j["#09"] = jf
            p3, _, _ = check(judge_paths=fake_j)
            chk("판정이 바뀌면 잡는다", any("판정 #09" in p for p in p3), True)
            wf = os.path.join(d, "window.ts")
            io.open(wf, "w", encoding="utf-8").write('export const DATA_WINDOW = "2026-06";\n')
            p4, _, _ = check(window_path=wf)
            chk("자료 창이 어긋나면 잡는다", any("DATA_WINDOW" in p for p in p4), True)
            # **공유 카드도 잡는 쪽을 친다** — 화면으로는 안 드러나는 자리라 더 그렇다.
            # 2026-09-10 에 실제로 일어난 꼴 그대로 짓는다: 선언 1200×630 · 실물 1600×1073.
            from PIL import Image as _Im
            site2 = os.path.join(d, "site")
            os.makedirs(os.path.join(site2, "src", "routes"))
            os.makedirs(os.path.join(site2, "public", "assets", "og"))
            io.open(os.path.join(site2, "src", "routes", "__root.tsx"), "w", encoding="utf-8").write(
                '{ property: "og:image:width", content: "1200" },\n'
                '{ property: "og:image:height", content: "630" },\n')
            def _meta(name):
                io.open(os.path.join(site2, "src", "app-meta.json"), "w", encoding="utf-8").write(
                    '{"og_image_url": "https://x/assets/og/%s"}' % name)
            _Im.new("RGB", (1600, 1073)).save(os.path.join(site2, "public", "assets", "og", "cover.jpg"))
            _Im.new("RGB", (1200, 630)).save(os.path.join(site2, "public", "assets", "og", "card.jpg"))
            _meta("cover.jpg")
            p5, n5 = og_card(site2)
            chk("선언과 실물이 갈리면 잡는다", any("1600×1073" in x for x in p5), True)
            _meta("card.jpg")
            chk("맞으면 조용하다", og_card(site2)[0], [])
            _meta("없는파일.jpg")
            chk("가리키는 파일이 없으면 잡는다", any("파일이 없다" in x for x in og_card(site2)[0]), True)
            io.open(os.path.join(site2, "src", "app-meta.json"), "w", encoding="utf-8").write(
                '{"og_image_url": "https://cdn.example.com/somewhere/x.jpg"}')
            chk("`/assets/` 를 안 가리키면 잡는다",
                any("안 가리킨다" in x for x in og_card(site2)[0]), True)
    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="측심의 화면 상수가 대장·판정결과와 같은가.")
    ap.add_argument("--hook", action="store_true", help="pre-push 용 — 문제 있을 때만 말한다")
    ap.add_argument("--strict", action="store_true", help="어긋나면 종료코드 1")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return report(hook=a.hook, strict=a.strict)


if __name__ == "__main__":
    sys.exit(main())

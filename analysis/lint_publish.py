"""발행 린터 — 결론 자리 수치의 등재·지위를 기계로 강제한다.

배경
----
2026-08-25에 사고가 둘 났다.
  A) 챗이 배율 8.642의 창을 상반기로 오판했다. 실제는 2026-06 단월이다.
  B) Claude Code가 반기 배율 7.754를 부제 후보로 올렸다. 6개월 중 5개월이 강등 구간이다.
둘 다 능력 문제가 아니라 정보 격차 문제였다 — 값의 창과 지위가 사람의 기억 속에만 있었다.
정지선이 사람이 나르는 형태로만 존재하면, 나르는 사람이 바뀔 때마다 떨어진다.

이 린터가 하는 일
-----------------
  1. 보고서 md에서 '결론 자리'만 잘라낸다. (H1 / 한 줄 결론 / §1 핵심 요약 / §3 해석)
  2. 그 안의 '주장 수치'를 뽑는다. 단위가 붙었거나 · 소수점이 있거나 · 천단위 쉼표가 있는 것.
     맨 정수(연도 2025, 절 번호 3)는 주장이 아니므로 제외된다.
  3. docs/FACTS.md 정본 대장과 대조한다.
       미등재            -> WARN  (창을 적지 않은 채 주장하고 있다)
       지위 참고/미확인  -> FAIL  (사고 B 유형)
       단위 불일치       -> WARN  (동음이의 수치일 수 있다)
  4. 부수 가드: 인과·목적 서술(FAIL), 2026 잠정치에 '확정/확인됐다'(WARN).

사용
----
  python analysis/lint_publish.py                    # reports/*.md 전체
  python analysis/lint_publish.py <경로> [<경로>...]  # 지정
  python analysis/lint_publish.py --selftest         # 내장 인수시험(사고 재현)

종료코드 1 = FAIL 존재 = 발행 금지.
"""

import re
import sys
import tempfile
from pathlib import Path

try:  # Windows 콘솔(cp949)에서 한글·기호가 깨지지 않게 강제한다.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "docs" / "FACTS.md"

CONCLUSION_OK = {"검증", "관측"}
UNITS = r"%p|%|배|개월|TEU|박스"

TOKEN = re.compile(r"(?<![\w.\-])([+\-−]?\d[\d,]*(?:\.\d+)?)\s*(" + UNITS + r")?")

CAUSAL = [(r"때문에", "인과 서술"), (r"를\s*위해", "목적 서술"), (r"으로\s*인해", "인과 서술")]
OVERCLAIM = [(r"확정(?:됐|되었|됨)", "2026 잠정치에 '확정'"), (r"확인됐다", "2026 잠정치에 '확인됐다'")]


def norm(v: str) -> str:
    v = v.replace(",", "").replace("−", "-").lstrip("+")
    neg = v.startswith("-")
    if neg:
        v = v[1:]
    v = v.lstrip("0") or "0"
    if v.startswith("."):
        v = "0" + v
    if "." in v:
        v = v.rstrip("0").rstrip(".") or "0"
    return ("-" + v) if neg else v


def is_claim(value: str, unit: str) -> bool:
    """주장 수치인가. 맨 정수는 연도·번호일 가능성이 높아 제외한다."""
    return bool(unit) or "." in value or "," in value


def load_facts():
    if not FACTS.exists():
        sys.exit(f"[중단] 정본 대장 없음: {FACTS}")
    seg = FACTS.read_text(encoding="utf-8")
    seg = seg.split("<!-- LINT-TABLE-START -->")[-1].split("<!-- LINT-TABLE-END -->")[0]
    facts = {}
    for line in seg.splitlines():
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 4 or cols[0] == "값":
            continue
        m = TOKEN.search(cols[0])
        if not m:
            continue
        facts[norm(m.group(1))] = {
            "표기": cols[0],
            "단위": m.group(2) or "",
            "창": cols[1],
            "지위": cols[2].replace("**", "").strip(),
        }
    return facts


def strip_noise(text: str) -> str:
    # 절 번호(§2.1)·편 번호(#07)는 수치가 아니다. 수치로 세면 오탐이 나온다.
    for pat in (r"<!--.*?-->", r"`[^`]*`", r"\[[^\]]*\]\([^)]*\)", r"<sub>.*?</sub>",
                r"§\s*\d+(?:[.\-]\d+)*", r"#\d+"):
        text = re.sub(pat, " ", text, flags=re.S)
    return text


def excerpt(s: str, a: int, b: int) -> str:
    return re.sub(r"\s+", " ", s[max(0, a):b]).strip()


def conclusion_zones(md: str):
    """결론 자리만 반환: (구역명, 텍스트, 시작줄)"""
    lines = md.splitlines()
    zones = []
    for i, ln in enumerate(lines, 1):
        if ln.startswith("# "):
            zones.append(("H1", ln, i))
        elif ln.startswith("- **한 줄 결론**"):
            zones.append(("한 줄 결론", ln, i))
    for title, pat in (("§1 핵심 요약", r"^##\s*1[.\s]"), ("§3 해석", r"^##\s*3[.\s]")):
        start = None
        for i, ln in enumerate(lines):
            if start is None:
                if re.match(pat, ln):
                    start = i
            elif ln.startswith("## "):
                zones.append((title, "\n".join(lines[start:i]), start + 1))
                start = None
                break
        if start is not None:
            zones.append((title, "\n".join(lines[start:]), start + 1))
    return zones


def lint(path: Path, facts):
    md = path.read_text(encoding="utf-8")
    fails, warns = [], []

    for zone, text, ln in conclusion_zones(md):
        for m in TOKEN.finditer(strip_noise(text)):
            value, unit = m.group(1), m.group(2) or ""
            if not is_claim(value, unit):
                continue
            token = re.sub(r"\s+", "", m.group(0))
            f = facts.get(norm(value))
            if f is None:
                warns.append(f"L{ln} [{zone}] 미등재 '{token}' — FACTS.md에 창과 함께 등재하라")
            elif f["단위"] and unit and f["단위"] != unit:
                warns.append(
                    f"L{ln} [{zone}] '{token}' 단위 불일치 (대장 '{f['표기']}') — 동음이의 수치 확인 필요"
                )
            elif f["지위"] not in CONCLUSION_OK:
                fails.append(
                    f"L{ln} [{zone}] '{token}' 지위={f['지위']} — 결론 자리 금지. 창: {f['창']}"
                )

    whole = strip_noise(md)
    for pat, why in CAUSAL:
        for m in re.finditer(pat, whole):
            fails.append(f"[문안] {why}: …{excerpt(whole, m.start() - 35, m.end() + 20)}…")
    # 잠정치 과대주장은 '2026 데이터를 말하는 문맥'에서만 잡는다.
    # 작성일에 붙은 2026까지 잡으면 오탐이 나고, 오탐이 나오는 린터는 무시당한다.
    for pat, why in OVERCLAIM:
        for m in re.finditer(pat, whole):
            if re.search(r"2026[-년]", whole[max(0, m.start() - 120):m.end() + 60]):
                warns.append(f"[문안] {why}: …{excerpt(whole, m.start() - 35, m.end() + 15)}…")

    return fails, warns


SELFTEST = """# #99 인수시험 — 수출입 배율은 7.754배로 벌어졌다 (2026년 1~6월)

- **한 줄 결론**: 반기 배율이 5.506배에서 7.754배로 확대됐다.

## 1. 핵심 요약

- 수입은 -21.4% 줄고 수출은 +10.7% 늘었다.
- 6월 배율은 8.642배이고 격차는 +34.4%p다.

## 2. 분석 결과

표 생략.

## 3. 해석

배율 확대는 구조 변화 때문에 나타난 것으로 보인다. 2026년 상반기 수치로 확정됐다.
"""

# 인수시험이 반드시 FAIL로 잡아야 하는 것 — 지위 '참고'인 값 + 인과 서술.
MUST_FAIL = ["7.754", "-21.4", "+10.7", "인과 서술"]
# 반대로 절대 잡으면 안 되는 것 — 결론 자리에 정당하게 쓸 수 있는 값.
#   8.642·+34.4%p = [검증]
#   5.506         = [관측] (2025 확정치 구간. 사고는 이 값이 아니라 짝지어진 7.754 쪽이었다)
MUST_PASS = ["8.642", "34.4", "5.506"]


def selftest(facts):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "fixture.md"
        p.write_text(SELFTEST, encoding="utf-8")
        fails, warns = lint(p, facts)
    print("── 인수시험: 2026-08-25 사고 재현 픽스처 ──")
    for f in fails:
        print(f"    ✗ {f}")
    for w in warns:
        print(f"    · {w}")
    blob = "\n".join(fails)
    missed = [k for k in MUST_FAIL if k not in blob]
    overcaught = [k for k in MUST_PASS if k in blob]
    print()
    if missed or overcaught:
        print(f"인수시험 실패 — 미검출 {missed} / 오탐 {overcaught}")
        return False
    print(f"인수시험 통과 — 금지 대상 {len(MUST_FAIL)}종 전부 FAIL, [검증] 값 {MUST_PASS}는 통과")
    return True


def main():
    facts = load_facts()
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    if "--selftest" in sys.argv:
        print(f"대장 등재 수치 {len(facts)}건\n")
        sys.exit(0 if selftest(facts) else 1)

    targets = [Path(a) for a in args] or sorted((ROOT / "reports").glob("*.md"))
    tf = tw = 0
    print(f"대장 등재 수치 {len(facts)}건 · 검사 대상 {len(targets)}건\n")
    for p in targets:
        fails, warns = lint(p, facts)
        tf += len(fails)
        tw += len(warns)
        mark = "FAIL" if fails else ("WARN" if warns else "PASS")
        print(f"[{mark}] {p.name}  (FAIL {len(fails)} / WARN {len(warns)})")
        for f in fails:
            print(f"    ✗ {f}")
        for w in warns:
            print(f"    · {w}")
    print(f"\n합계  FAIL {tf}  WARN {tw}")
    if tf:
        print("FAIL이 있으므로 발행하지 않는다.")
        sys.exit(1)


if __name__ == "__main__":
    main()

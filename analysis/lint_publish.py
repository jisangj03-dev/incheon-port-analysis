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
  python analysis/lint_publish.py <경로> --channel    # 채널 문안(전문을 결론 자리로)
  python analysis/lint_publish.py --selftest         # 내장 인수시험(사고 재현)

모드는 셋이고 **채널만 손으로 켠다.** 나머지는 파일이 정한다 —
front matter 에 `layout:` 이 있으면 **지면**(머리말 + 표 밖 산문), 없으면 **발행본**(보고서 골격).
매 줄에 어느 모드로 봤는지 찍는다. **모드가 자동이면 그만큼 「무엇이 검사됐나」가 안 보인다.**

종료코드 1 = FAIL 존재 = 발행 금지.

정지선-집행: §4 — 데이터 지위(강등 구간·잠정치·박스 수 기준·`_99`·PASS) / §3 결론 자리
정지선-명제: 발행본·지면·채널 문안의 결론 자리에서 지위 위반·인과 서술·FACTS 미등재를 잡는다
정지선-한계: **발행본은 골격을 못 찾으면 `[구조]` WARN만 낸다**(사고 26) · **지면은 표·그림 안을 안 본다** — 강등 값을 표에만 넣고 산문에서 안 부르면 지나간다
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

# 쉼표는 **세 자리 묶음일 때만** 천 단위 구분으로 본다.
#
# [2026-08-29 실측] 직전 판은 `\d[\d,]*` 라 목록의 쉼표까지 삼켰다. 그래서
# **「성립되지 않은 6개월은 2, 3, 5, 7, 8, 9월이다」의 월 번호가 전부 주장 수치로 잡혔다** —
# `is_claim()` 이 「쉼표가 있으면 천 단위」로 판정하는데 그 쉼표가 목록 쉼표였다.
# #06 미등재 7건 중 4건이 그것이었다. **대장에 월 번호를 등재할 수는 없다.**
#
# 좁히는 것이지 약해지는 것이 아니다 — `62,115`·`3,444,000`·`90,346.25` 는 그대로 잡힌다.
# 바뀌는 것은 `2,` 가 `2`(맨 정수)로 읽혀 §맨 정수 제외 규칙에 걸린다는 것뿐이다.
# **오탐이 나오는 린터는 무시당한다**(§3-5가 인과 축에서 적은 그대로다).
TOKEN = re.compile(
    r"(?<![\w.\-])([+\-−]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s*(" + UNITS + r")?")

# 인과·목적 표현.
# 2026-08-25 실측: 직전 판은 어미 3종만 봤고 #01~#07 전편에서 단 한 번도 발화하지 않았다.
# 즉 그때의 'FAIL 0'은 검사를 통과한 것이 아니라 검사가 닿지 않은 것이었다.
CAUSAL = [
    (r"때문(?:에|이다|이라|인)", "인과 서술"),
    (r"탓(?:에|으로|이다)", "인과 서술"),
    (r"[으]?로\s*인(?:해|한|하여|해서)", "인과 서술"),
    (r"영향(?:으로|을\s*받아)", "인과 서술"),
    (r"[을를]\s*위해", "목적 서술"),
    (r"하기\s*위[해한]", "목적 서술"),
]

# 방법론 논리 예외 (지침 v5.0 §3-5).
#   데이터 인과   "수입이 줄어서 배율이 벌어졌다"            → 금지. 이 데이터로 판별할 수 없는 주장이다.
#   방법론 논리   "손질을 차단하기 위한 장치다"              → 허용. 저작 행위의 서술이지 데이터 주장이 아니다.
#   인과 부인문   "…라는 인과는 본 데이터로 증명되지 않는다"  → 허용. 인과를 부인하는 문장이다.
# 판별 축은 인과 표현이 '무엇을 설명하는가'다. 현상을 설명하면 주장, 절차·장치를 설명하면 서술이다.
METHOD = re.compile(
    r"설계|기준|게이트|린터|판정|검증|선커밋|커밋|앵커|해시|blob|재현|코드|대장|표기|검수|"
    r"스크립트|절차|장치|조치|대조|복원|산출|수집|정의|차단|보존|순환|전제|반올림|모집단|각주|보고서"
)
PHENOM = re.compile(
    r"늘어|늘었|늘고|줄어|줄었|줄고|증가|감소|확대|축소|벌어졌|벌어진|나타났|나타난|"
    r"발생|쏠렸|쏠린|쏠림|급감|급증|상승|하락|악화|개선"
)
# 인과를 부인하는 문장은 인과 주장이 아니다.
# 시제가 빠지면 같은 문장이 과거형일 때만 FAIL 난다 — 2026-08-26에 실제로 났다
# (「미승인 때문인지 경로 차이인지 가르지 못했다」). 부인 어미를 시제째 넣는다.
NEG = re.compile(
    r"않는다|않았다|않으며|아니다|아니라|없다|없었다|"
    r"못한다|못했다|못하며|못하고|"
    r"증명되지|단정하지|확인하지|밝히지|가르지|금지"
)
# 작성일·기록일 형태의 완전한 날짜. OVERCLAIM 문맥 판정에서 제거한다.
# 이걸 안 빼면 「[2026-08-26 갱신 — 이름이 확정됐다]」 같은 문장이 전부 걸린다 —
# OVERCLAIM 바로 위 주석이 금지한 그 오탐을, 코드가 그대로 내고 있었다(사고 39).
FULLDATE = re.compile(r"2026[-.]\s?\d{1,2}[-.]\s?\d{1,2}|2026년\s*\d{1,2}월\s*\d{1,2}일")

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
        # **숫자 하나에 여러 양이 붙을 수 있다.** 단위별로 담는다.
        #
        # [2026-08-29 실측] 직전 판은 `facts[norm] = {...}` 라 **나중 행이 앞 행을 덮었다.**
        # `4%p`(#02 비중 폭)를 등재한 뒤 `4배`(#03 배율 하한)를 등재하자 앞이 사라졌고,
        # #02 가 「'4%p' 단위 불일치 (대장 '4배')」로 경고를 냈다.
        # **린터는 동음이의를 탐지하면서 저장은 못 하고 있었다** — 탐지만 하고 담지 못하면
        # 둘 중 하나는 영원히 등재할 수 없다.
        facts.setdefault(norm(m.group(1)), {})[m.group(2) or ""] = {
            "표기": cols[0],
            "단위": m.group(2) or "",
            "창": cols[1],
            "지위": cols[2].replace("**", "").strip(),
        }
    return facts


def lookup(facts, value: str, unit: str):
    """대장에서 (값, 단위)를 찾는다. 반환: (항목, 사유) — 항목이 None 이면 사유가 이유다.

    **단위가 없는 토큰의 관대한 매칭을 그대로 둔다.** 직전 판은 대장 쪽 단위가 비었거나
    본문 쪽 단위가 비면 불일치를 안 냈다. 그 동작을 바꾸면 이번 변경이 조용히
    새 경고를 만들어 낸다 — **고치는 김에 다른 것을 바꾸지 않는다.**
    """
    bucket = facts.get(norm(value))
    if not bucket:
        return None, "미등재"
    if unit in bucket:
        return bucket[unit], ""
    if "" in bucket:                       # 대장 쪽 단위가 빈 행 — 옛 동작대로 통과
        return bucket[""], ""
    if not unit:                           # 본문 쪽 단위가 없다 — 옛 동작대로 통과
        return next(iter(bucket.values())), ""
    return None, "단위 불일치 (대장 %s)" % " · ".join(
        "'%s'" % e["표기"] for e in bucket.values())


def keep_lines(m) -> str:
    """걷어낸 자리에 **줄바꿈 개수를 남긴다.**

    종전에는 공백 하나로 바꿨다. 그래서 표 한 덩어리를 지우면 그 안의 줄이 통째로
    사라지고, **뒤에 나오는 모든 경고의 줄번호가 앞으로 밀렸다.** `/berths/` 의 경고 5건이
    전부 `L12`(머리말 끝 줄)로 찍혔다 — 본문 240줄 아래에 있는 문장인데.

    **검사기가 잡아 놓고 어디인지 안 알려 주면 그만큼은 안 잡은 것과 같다.**
    같은 문장을 파일 이름 표기에 대해 이미 한 번 적었고(같은 날 오전), 줄번호에는 안 썼다.
    """
    s = m.group(0)
    return "\n" * s.count("\n") if "\n" in s else " "


def strip_noise(text: str) -> str:
    # 절 번호(§2.1)·편 번호(#07)는 수치가 아니다. 수치로 세면 오탐이 나온다.
    #
    # [2026-08-28 추가] HTML 태그와 맨 URL도 걷어낸다. **오탐이 실제로 났다** —
    # 허브 `index.md`를 마크다운 링크에서 `<a href="...">`로 바꾸자 WARN 18이 떴고,
    # 전부 퍼센트 인코딩(`%EA%B4%80%EC%84%B8`)의 16진수를 백분율로 읽은 것이었다.
    # 마크다운 링크만 걷어내고 있어서, **표기법을 바꾸는 순간 같은 URL이 수치가 됐다.**
    # 사이트가 HTML을 쓰기 시작하면 이 구멍은 계속 벌어진다.
    #
    # [2026-08-29 추가] **파일 메타는 주장 수치가 아니다.** 크기(B·KB·MB)·행수·열수는
    # 우리 산출물이나 원본 파일을 묘사하는 값이지 **인천항에 대한 주장이 아니다.**
    # 지면 모드를 켜자마자 `/datasets/` 에서 15건이 떴는데 전부 그것이었다
    # (`5.1 KB` · `66행 · 16열` · `696.4 KB`). 대장에 넣으면 **대장이 파일 목록이 된다.**
    # `§2.1` · `#07` 을 빼는 것과 같은 종류의 제외지, 검사를 약하게 하는 것이 아니다 —
    # **인천항 물동량은 B·KB·행·열로 세지 않는다.** 셀 일이 생기면 그때 다시 판단한다.
    for pat in (r"<!--.*?-->", r"`[^`]*`", r"\[[^\]]*\]\([^)]*\)", r"<sub>.*?</sub>",
                r"</?[a-zA-Z][^>]*>", r"https?://\S+",
                r"\d[\d,]*(?:\.\d+)?\s*(?:B|KB|MB|GB)\b", r"\d[\d,]*\s*[행열]",
                r"§\s*\d+(?:[.\-]\d+)*", r"#\d+"):
        text = re.sub(pat, keep_lines, text, flags=re.S)
    return text


def classify_causal(text: str, start: int, end: int):
    """인과 표현 1건을 판정한다. 반환 ("FAIL", "") 또는 ("예외", 사유)."""
    # 문장 경계에서 자른다. 옆 문장의 부인·현상 어휘가 넘어오면 오판이 된다.
    before = re.split(r"[.!?]\s", text[max(0, start - 90):start])[-1]
    after = re.split(r"[.!?]\s", text[end:end + 70])[0]
    if NEG.search(after) or NEG.search(before[-25:]):
        return "예외", "인과 부인문"
    if PHENOM.search(after):
        return "FAIL", ""          # 현상을 설명하고 있다 = 데이터 인과 주장
    if METHOD.search(before) or METHOD.search(after):
        return "예외", "방법론 문맥"
    return "FAIL", ""              # 판별 불가는 통과시키지 않는다


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


# **제목이 본문보다 넓게 말하는 자리**(사고 116). 두 번 났다 —
# #11 「합계 한 줄은 다섯 곳을 **대표**하지 않는다」(잰 것은 부호 동행 하나였다) ·
# #12 선커밋 「창을 **되찾**는다」(220개월 중 39개월이었다). 둘 다 본문은 정직했고 제목만 넓었다.
#
# **낱말로 겨눈다.** 넓이를 주장하는 말이 제목에 있으면, **그 제목이 재지 않은 것**을
# 리드나 §1 이 한 줄로 들어야 한다. 낱말이 없으면 아무 말도 안 한다 —
# **오탐을 내는 린터는 무시당한다**(§3-5). 2026-09-12 실측: #01~#10 은 하나도 안 걸리고 #11 만 걸린다.
SCOPE_WORDS = ("되찾", "대표", "전부", "전체", "모두")
# 범위를 적었다는 표시. **형식이 아니라 문장**이라 두 낱말이 한 문장에 같이 있는 것으로 본다.
SCOPE_MARK = re.compile(r"제목[^.\n]{0,60}범위|범위[^.\n]{0,60}제목")


def scope_warn(md: str, zones):
    """제목이 넓이를 주장하면 **그 제목이 재지 않은 것**을 리드·§1 이 들어야 한다."""
    h1 = next((t for z, t, _ in zones if z == "H1"), "")
    if not any(w in h1 for w in SCOPE_WORDS):
        return []
    head = md.split("## 2.")[0] if "## 2." in md else md[:4000]
    if SCOPE_MARK.search(head):
        return []
    hit = [w for w in SCOPE_WORDS if w in h1]
    return [f"[범위] 제목이 넓이를 주장한다({'·'.join(hit)}) — "
            f"**이 제목이 재지 않은 것**을 리드나 §1 이 한 줄로 들어야 한다(사고 116)"]


FRONT_CLAIM_KEYS = ("title", "kicker", "standfirst", "description", "subject")

# 지면에서 **관측이 들어 있는 덩어리**. 이것만 걷어내면 남는 것이 산문이다.
SITE_STRIP = (
    r"```.*?```",                     # 코드블록
    r"<table\b.*?</table>",           # HTML 표 — 셀 안 숫자는 관측이다
    r"<svg\b.*?</svg>",               # 그림 — 좌표와 눈금이 전부 숫자다
    r"(?m)^[ \t]*\|.*$",              # 마크다운 표 행
)

FRONT_RE = re.compile(r"---\s*\n(.*?)\n---\s*\n", re.S)


def site_zones(md: str):
    """지면(허브) 결론 자리 — **front matter 문안 + 표 밖 산문.**

    왜 보고서 골격을 못 쓰는가
    --------------------------
    `conclusion_zones()` 는 `# ` · `한 줄 결론` · `## 1.` · `## 3.` 을 찾는다.
    **허브 지면에는 그 넷이 하나도 없다** — 제목은 front matter 에 있고 절은 표 번호로 나간다.
    그래서 지면을 겨누면 `[구조]` WARN 넷만 뜨고 **수치는 하나도 검사되지 않았다.**

    **이 결함은 이미 한 번 발견돼 있었다.** 2026-08-26에 채널 문안에서 같은 것을 실측해
    `--channel` 을 만들었고, 그 주석이 「겨눌 수는 있으나 검사가 되지 않았다」로 적는다.
    **그 판단을 지면에는 안 옮겼다.** 그 사이 지면이 아홉 개로 늘고 표가 열 개 넘게 붙었다.
    한 도구에서 세운 원칙을 다음 도구에서 안 쓰는 것 — 사고 61과 같은 얼굴이다.

    무엇을 결론 자리로 보는가
    -------------------------
    **표 안은 관측이고 표 밖 산문은 주장이다.** 이 경계가 이 함수의 전부다.

      · front matter 의 `title`·`kicker`·`standfirst`·`description`
        — **지면에서 가장 크게 읽히고, 링크 카드와 검색 결과에 그대로 나간다.**
          지면을 안 연 사람도 이것은 읽는다. 결론 자리가 아니면 무엇이 결론 자리인가.
      · 본문에서 표·그림·코드블록을 뺀 나머지
        — 표는 공표자료를 옮긴 것이라 그 안의 숫자는 관측이다. 거기까지 등재를 걸면
          **월별 원자료 수백 건을 대장에 넣으라는 말**이 되고, 그러면 대장이 대장이 아니게 된다.

    닿지 않는 곳
    ------------
    · **표 안의 지위 위반은 못 잡는다.** 강등 구간 값을 표에 넣고 산문에서 안 부르면 지나간다.
      그 자리는 생성기와 `check_facts.py` 가 받는다 — **완전하지 않다는 것을 적어 둔다.**
    · front matter 를 YAML 로 파싱하지 않는다. `키: 값` 한 줄짜리만 읽는다.
    · **`site_zones` 는 「이 파일이 지면인가」를 판정하지 않는다.** 그 판정은 `is_site()` 다.
    """
    zones = []
    body = md
    off = 1
    m = FRONT_RE.match(md)
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if k.strip() in FRONT_CLAIM_KEYS and v.strip():
                zones.append(("머리말 " + k.strip(), v.strip(), 1))
        body = md[m.end():]
        off = md[:m.end()].count("\n") + 1
    for pat in SITE_STRIP:
        body = re.sub(pat, keep_lines, body, flags=re.S)
    zones.append(("지면 산문", body, off))
    return zones


def is_site(md: str) -> bool:
    """지면인가. **모드를 사람이 고르게 두지 않는다.**

    `--channel` 은 플래그일 수밖에 없었다 — 채널 문안에는 구별 표지가 없다.
    **그런데 지면에는 있다.** front matter 의 `layout:` 이 그것이고, 그것이 있다는 것은
    Jekyll 이 레이아웃으로 감싸 내보내는 지면이라는 뜻이다. 발행본 8편에는 없다.

    **플래그로 뒀으면 잊는 경로가 남는다.** 그리고 이 검사에서 잊는다는 것은
    「검사했는데 아무것도 안 걸렸다」로 보인다는 뜻이다 — 침묵하는 실패다(사고 26).
    """
    m = FRONT_RE.match(md)
    return bool(m) and re.search(r"(?m)^layout\s*:", m.group(1)) is not None


def lint(path: Path, facts, channel: bool = False, site: bool = False):
    md = path.read_text(encoding="utf-8")
    # **모드는 파일이 정한다.** 채널 모드만 손으로 켠다 — 채널 문안에는 표지가 없다.
    if not channel and not site:
        site = is_site(md)
    fails, warns, exempt = [], [], []

    if channel:
        # 채널 문안 모드 — 파일 전체를 결론 자리로 본다.
        #
        # 지침 §3은 결론 자리에 **채널 게시물 헤드라인**을 포함한다. 그런데
        # conclusion_zones() 는 보고서 골격(H1 / 한 줄 결론 / ## 1. / ## 3.)을 찾으므로,
        # 채널 문안에 그대로 겨누면 [구조] WARN 넷만 내고 **값은 하나도 검사하지 않는다.**
        # 2026-08-26 실측으로 확인했다 — 겨눌 수는 있으나 검사가 되지 않았다.
        #
        # 채널 문안에는 절 구조가 없고 짧다. 그래서 「어디가 결론 자리인가」를 찾는 대신
        # **전부 결론 자리로 취급한다.** 게시물에서 결론이 아닌 수치를 쓸 일이 없기도 하다.
        zones = [("채널 문안", md, 1)]
    elif site:
        # 지면 모드 — 골격 WARN 을 내지 않는다. **낼 이유가 없다.**
        # 허브 지면이 보고서 골격을 안 따르는 것은 정상이고, 못 찾았다는 경고를
        # 아홉 지면에 영구히 띄우면 **그 경고가 배경 소음이 된다.**
        zones = site_zones(md)
    else:
        # 결론 자리를 하나도 못 찾으면 린터는 아무것도 검사하지 않은 채 PASS를 낸다.
        # 절 번호가 바뀐 보고서(새 라인)에서 조용히 무력화되는 경로다. 침묵시키지 않는다.
        zones = conclusion_zones(md)
        found = {z[0] for z in zones}
        for need in ("H1", "한 줄 결론", "§1 핵심 요약", "§3 해석"):
            if need not in found:
                warns.append(
                    f"[구조] 결론 자리 '{need}'를 찾지 못했다 — 이 구역은 **검사되지 않았다.** "
                    f"보고서 골격(지침 §2.5)을 따르거나 conclusion_zones()를 고쳐라"
                )
        warns += scope_warn(md, zones)

    for zone, text, ln in zones:
        clean = strip_noise(text)
        for m in TOKEN.finditer(clean):
            value, unit = m.group(1), m.group(2) or ""
            if not is_claim(value, unit):
                continue
            token = re.sub(r"\s+", "", m.group(0))
            # 구역 안 위치를 더한다. `keep_lines()` 가 줄을 보존하므로 이 셈이 맞는다.
            ln_here = ln + clean[:m.start()].count("\n")
            f, why = lookup(facts, value, unit)
            if f is None and why == "미등재":
                warns.append(f"L{ln_here} [{zone}] 미등재 '{token}' — FACTS.md에 창과 함께 등재하라")
            elif f is None:
                warns.append(
                    f"L{ln_here} [{zone}] '{token}' {why} — 동음이의 수치 확인 필요"
                )
            elif f["지위"] not in CONCLUSION_OK:
                fails.append(
                    f"L{ln_here} [{zone}] '{token}' 지위={f['지위']} — 결론 자리 금지. 창: {f['창']}"
                )

    whole = strip_noise(md)
    for pat, why in CAUSAL:
        for m in re.finditer(pat, whole):
            verdict, reason = classify_causal(whole, m.start(), m.end())
            line = f"…{excerpt(whole, m.start() - 35, m.end() + 20)}…"
            if verdict == "FAIL":
                fails.append(f"[문안] {why}: {line}")
            else:
                exempt.append(f"[{reason}] {why}: {line}")
    # 잠정치 과대주장은 '2026 데이터를 말하는 문맥'에서만 잡는다.
    # 작성일에 붙은 2026까지 잡으면 오탐이 나고, 오탐이 나오는 린터는 무시당한다.
    for pat, why in OVERCLAIM:
        for m in re.finditer(pat, whole):
            ctx = whole[max(0, m.start() - 120):m.end() + 60]
            ctx = FULLDATE.sub("", ctx)   # 작성일·기록일은 문맥에서 뺀다. 그것은 데이터의 2026이 아니다
            if re.search(r"2026[-년]", ctx):
                warns.append(f"[문안] {why}: …{excerpt(whole, m.start() - 35, m.end() + 15)}…")

    return fails, warns, exempt


SELFTEST = """# #99 인수시험 — 수출입 배율은 7.754배로 벌어졌다 (2026년 1~6월)

- **한 줄 결론**: 반기 배율이 5.506배에서 7.754배로 확대됐다.

## 1. 핵심 요약

- 수입은 -21.4% 줄고 수출은 +10.7% 늘었다.
- 6월 배율은 8.642배이고 격차는 +34.4%p다.

## 2. 분석 결과

기준을 데이터보다 먼저 커밋한 것은 결과를 본 뒤의 손질을 차단하기 위한 장치다.
미승인 때문인지 경로 차이인지 가르지 못했다.
회귀 앵커를 동일 코드 경로로 다시 수집한 것은, 기존 파일 재합산이 그 파일을 전제로
그 파일을 검증하는 순환이기 때문이다.
한쪽이 다른 쪽을 위해 발생했다는 인과는 본 데이터로 증명되지 않는다.

## 3. 해석

배율 확대는 구조 변화 때문에 나타난 것으로 보인다. 2026년 상반기 수치로 확정됐다.
"""

# 인수시험이 반드시 FAIL로 잡아야 하는 것 — 지위 '참고'인 값 + 인과 서술.
MUST_FAIL = ["7.754", "-21.4", "+10.7", "인과 서술"]
# 반대로 절대 잡으면 안 되는 것 — 결론 자리에 정당하게 쓸 수 있는 값.
#   8.642·+34.4%p = [검증]
#   5.506         = [관측] (2025 확정치 구간. 사고는 이 값이 아니라 짝지어진 7.754 쪽이었다)
MUST_PASS = ["8.642", "34.4", "5.506"]
# 방법론 논리·인과 부인문은 FAIL로 잡히면 안 된다. 오탐이 나오는 린터는 무시당한다.
MUST_EXEMPT = ["위한 장치", "순환이기 때문", "다른 쪽을 위해", "가르지 못했다"]


CHANNEL_FIXTURE = """반기 수출입 배율이 7.754배로 벌어졌습니다. 수입은 -21.4% 줄었습니다.
6월 단월 배율은 8.642배입니다. 격차는 45개월째 유지됩니다.
"""


# 퍼센트 인코딩된 URL은 수치가 아니다. **2026-08-28에 실제로 오탐이 났다** —
# 허브 index를 마크다운 링크에서 `<a href>`로 바꾸자 WARN 18이 떴고 전부 이것이었다.
# 양방향으로 시험한다: URL의 %는 안 잡히고, **본문의 진짜 %는 그대로 잡혀야 한다.**
HTMLURL_FIXTURE = """<a class="report" href="https://x.io/reports/report_08_%EA%B4%80%EC%84%B8%EC%B2%AD.html">
<span class="no">#08</span><h3>다른 기관 소스로 다시 봤다</h3></a>
맨 URL도 본다: https://x.io/a_%ED%91%9C%EB%B3%B8%EC%99%B8.html
그리고 이 문장의 수입은 -21.4% 줄었습니다.
"""


def selftest_htmlurl(facts):
    """HTML href·맨 URL의 퍼센트 인코딩을 수치로 읽지 않는가 (오탐 방지·양방향)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "hub.md"
        p.write_text(HTMLURL_FIXTURE, encoding="utf-8")
        fails, warns, _ = lint(p, facts, channel=True)
    blob = "\n".join(list(fails) + list(warns))
    # 오탐: 인코딩 조각이 수치로 올라오면 안 된다
    ghosts = [g for g in ("80%", "84%", "95%", "88%", "98%", "85%", "91%", "99%", "96%") if g in blob]
    # 반대 방향: 본문의 진짜 값은 여전히 잡혀야 한다. 안 잡히면 다 지운 것이다
    real = "-21.4" in blob
    print("── 인수시험: URL 퍼센트 인코딩 (양방향) ──")
    print(f"    ① URL 조각 오탐 {len(ghosts)}건 (0이어야 한다){' -> ' + ', '.join(ghosts) if ghosts else ''}")
    print(f"    ② 본문의 진짜 '-21.4%' 검출 {'O' if real else 'X'} (O여야 한다 — X면 전부 지운 것이다)")
    ok = not ghosts and real
    print("    통과" if ok else "    실패")
    return ok


def selftest_channel(facts):
    """채널 문안 모드 — 절 구조가 없는 문안에서도 지위를 강제하는가."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "channel.md"
        p.write_text(CHANNEL_FIXTURE, encoding="utf-8")
        plain_f, _, _ = lint(p, facts, channel=False)
        ch_f, _, _ = lint(p, facts, channel=True)
    blob = "\n".join(ch_f)
    print("── 인수시험: 채널 문안 모드 ──")
    for f in ch_f:
        print(f"    ✗ {f}")
    caught = [k for k in ("7.754", "-21.4") if k in blob]
    over = [k for k in ("8.642", "45") if k in blob]
    ok = len(plain_f) == 0 and len(caught) == 2 and not over
    print(f"    (일반 모드에서는 FAIL {len(plain_f)}건 — 절 구조가 없어 검사되지 않는다)")
    if not ok:
        print(f"채널 모드 실패 — 검출 {caught} / 오탐 {over} / 일반모드 {len(plain_f)}")
    else:
        print("채널 모드 통과 — 지위 '참고' 2종 FAIL, [검증] 값은 통과")
    return ok


def selftest_overclaim(facts):
    """잠정치 과대주장 규칙 — 양방향으로 확인한다(사고 39).

    ① 작성일에 붙은 2026은 **안 잡아야** 한다.  ② 데이터 문맥의 2026은 **잡아야** 한다.
    한쪽만 시험하면 규칙을 껐는지 고쳤는지 구분이 안 된다.
    """
    def warns_of(body):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "f.md"
            head = ["# t", "- **한 줄 결론**: x", "## 1. 요약"]
            tail = ["## 3. 해석", ""]
            p.write_text(chr(10).join(head + [body] + tail), encoding="utf-8")
            return [w for w in lint(p, facts)[1] if "잠정치" in w]

    date_only = warns_of("[2026-08-26 갱신 — 이름이 확정됐다]")
    data_ctx = warns_of("2026년 상반기 배율이 확정됐다.")
    print("── 인수시험: 잠정치 과대주장 (양방향) ──")
    print(f"  ① 작성일 문맥 2026-08-26 → 경고 {len(date_only)}건 (0이어야 한다)")
    print(f"  ② 데이터 문맥 2026년   → 경고 {len(data_ctx)}건 (1 이상이어야 한다)")
    ok = not date_only and bool(data_ctx)
    print("  통과" if ok else "  실패 — 규칙이 한쪽으로 무너졌다")
    print()
    return ok


def selftest_homonym():
    """대장이 **같은 숫자의 다른 양**을 둘 다 담는가. 그리고 **여전히 불일치를 잡는가.**

    2026-08-29: 직전 판은 숫자만으로 키를 잡아 `4%p` 를 등재한 뒤 `4배` 를 등재하자
    앞이 사라졌다. **탐지는 하면서 저장은 못 하는 구조**였고, 그래서 둘 중 하나는
    영원히 등재할 수 없었다.

    **고치면서 탐지를 약하게 하지 않았는지가 이 시험의 절반이다**(사고 26).
    """
    print("── 인수시험: 동음이의 (양방향) ──")
    ok = True
    F = {
        "4": {"%p": {"표기": "4%p", "단위": "%p", "창": "비중 폭", "지위": "관측"},
              "배": {"표기": "4배", "단위": "배", "창": "배율 하한", "지위": "관측"}},
        "7": {"": {"표기": "7", "단위": "", "창": "단위 없는 행", "지위": "관측"}},
        "9": {"TEU": {"표기": "9TEU", "단위": "TEU", "창": "물동량", "지위": "관측"}},
    }

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("    %s %-46s %s" % ("OK  " if good else "FAIL", label,
                                   "" if good else "-> %r (기대 %r)" % (got, want)))

    chk("`4%p` 를 찾는다", lookup(F, "4", "%p")[0]["창"], "비중 폭")
    chk("**같은 숫자의 `4배` 도 따로 찾는다** (덮이지 않는다)",
        lookup(F, "4", "배")[0]["창"], "배율 하한")
    chk("**등록 안 된 단위는 여전히 불일치로 잡는다**",
        lookup(F, "4", "TEU")[0], None)
    chk("불일치 사유에 등재된 표기를 전부 보여 준다",
        "'4%p'" in lookup(F, "4", "TEU")[1] and "'4배'" in lookup(F, "4", "TEU")[1], True)
    chk("대장 쪽 단위가 비면 통과 (옛 동작 유지)", lookup(F, "7", "배")[0]["창"], "단위 없는 행")
    chk("본문 쪽 단위가 없으면 통과 (옛 동작 유지)", lookup(F, "9", "")[0]["창"], "물동량")
    chk("아예 없으면 미등재", lookup(F, "5", "배"), (None, "미등재"))
    print("    " + ("통과" if ok else "**실패**"))
    return ok


def selftest_listcomma():
    """목록의 쉼표를 천 단위 구분으로 읽지 않는가. **양방향으로 친다.**

    2026-08-29 실측: 「성립되지 않은 6개월은 2, 3, 5, 7, 8, 9월이다」의 월 번호가
    전부 주장 수치로 잡혀 #06 미등재 7건 중 4건이 오탐이었다.
    **좁히는 김에 진짜 수치까지 지우지 않았는지도 같이 본다** — 그게 이 시험의 절반이다.
    """
    print("── 인수시험: 목록 쉼표 (양방향) ──")
    ok = True

    def toks(s):
        return [(m.group(1), m.group(2) or "") for m in TOKEN.finditer(s)
                if is_claim(m.group(1), m.group(2) or "")]

    # `6개월`은 단위가 붙은 **진짜 주장**이라 잡히는 것이 맞다. 잡히면 안 되는 것은
    # 그 뒤의 월 번호 목록뿐이다 — 그래서 목록 부분만 떼어 친다.
    # (처음엔 문장 전체로 「0건」을 기대했다가 `6개월` 때문에 시험이 틀렸다. 시험이 낡았던 것이다.)
    got = toks("2, 3, 5, 7, 8, 9월이다.")
    ok &= (got == [])
    print("    ① 월 번호 목록 오탐 %d건 (0이어야 한다)" % len(got))
    whole = toks("성립되지 않은 6개월은 모두 2022년으로 2, 3, 5, 7, 8, 9월이다.")
    ok &= (whole == [("6", "개월")])
    print("    ①' 같은 문장에서 `6개월`은 남는다 -> %s (단위가 붙은 진짜 주장이다)" % whole)

    keep = ["62,115TEU", "3,444,000", "90,346.25", "-31.2%", "+38.7%p", "1,081", "8.642배"]
    lost = [s for s in keep if not toks(s)]
    ok &= (not lost)
    print("    ② 진짜 수치 %d/%d 유지 (전부 남아야 한다)%s"
          % (len(keep) - len(lost), len(keep), "" if not lost else " — 잃음: %s" % lost))
    print("    " + ("통과" if ok else "**실패**"))
    return ok


# **대장에 없는 값만 쓴다.** 등재된 값을 쓰면 시험이 대장 내용에 걸리고,
# 대장이 바뀔 때마다 시험이 먼저 깨진다 — 사고 65가 정확히 그 얼굴이었다.
# 여기서 보는 것은 「지위 판정」이 아니라 **「어느 구역을 잘라 냈는가」**다.
SITE_FIXTURE = """---
layout: page
title: 인수시험 지면 — 99,991 이 머리말 제목에 있다
standfirst: 이 문장은 머리말이고 지면에서 가장 크게 읽힌다. 여기 99,992 가 있다.
permalink: /selftest/
---

표 밖 산문이다. 여기 있는 99,993 은 결론 자리 수치다.

| 월 | 값 |
|---|---|
| 1월 | 99,994 |

<table><tr><td>99,995</td></tr></table>

<svg viewBox="0 0 100 45"><text x="10" y="20">99,996</text></svg>

파일은 696.4 KB · 66행 · 16열이다.
"""

REPORT_FIXTURE = """# 발행본이다 — layout 이 없다

- **한 줄 결론**: 배율이 7.754배다.

## 1. 핵심 요약
7.754배.

## 3. 해석
7.754배.
"""


def selftest_site(facts):
    """지면 모드 — **표 안은 관측, 표 밖은 주장**이라는 경계가 실제로 그어지는가.

    양방향으로 친다. 한쪽만 치면 규칙을 껐는지 그었는지 구분이 안 된다(사고 39·65).
      ① 머리말과 표 밖 산문의 수치는 **잡아야** 한다.
      ② 표·그림 안의 수치는 **안 잡아야** 한다.
      ③ 파일 메타(KB·행·열)는 **안 잡아야** 한다.
      ④ `is_site()` 가 발행본을 지면으로 오인하면 **안 된다.**
      ⑤ 줄번호가 **실제 줄과 맞아야** 한다 — 덩어리를 걷어내며 줄이 밀리면 무용지물이다.

    **저장소나 대장의 현재 상태를 안 박는다**(사고 65). 픽스처만 본다.
    """
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 지면 모드 ──")
    with tempfile.TemporaryDirectory() as d:
        sp = Path(d) / "site.md"
        sp.write_text(SITE_FIXTURE, encoding="utf-8")
        rp = Path(d) / "report.md"
        rp.write_text(REPORT_FIXTURE, encoding="utf-8")

        chk("layout 이 있으면 지면", is_site(SITE_FIXTURE), True)
        chk("layout 이 없으면 지면이 아니다", is_site(REPORT_FIXTURE), False)

        # 골격이 아예 없는 발행본 — **지면 모드가 골격 경고를 삼키지 않았는지** 본다.
        bp = Path(d) / "broken.md"
        bp.write_text("골격이 없는 문서다. 99,997 이 있다.", encoding="utf-8")

        _, sw, _ = lint(sp, facts)
        rf, rw, _ = lint(rp, facts)
        _, bw, _ = lint(bp, facts)

    def seen(v):
        return [w for w in sw if v in w]

    chk("머리말 title 의 값을 잡는다",
        bool([w for w in seen("99,991") if "머리말 title" in w]), True)
    chk("머리말 standfirst 의 값을 잡는다",
        bool([w for w in seen("99,992") if "머리말 standfirst" in w]), True)
    chk("표 밖 산문의 값을 잡는다",
        bool([w for w in seen("99,993") if "지면 산문" in w]), True)
    chk("마크다운 표 안은 안 센다", seen("99,994"), [])
    chk("HTML 표 안은 안 센다", seen("99,995"), [])
    chk("SVG 안은 안 센다", seen("99,996"), [])
    chk("파일 메타(KB·행·열)는 주장이 아니다",
        [w for w in sw if "696.4" in w], [])
    chk("골격 WARN 을 내지 않는다", [w for w in sw if "[구조]" in w], [])

    # 줄번호 — 픽스처에서 실제 줄을 세어 비교한다. **숫자를 손으로 안 박는다.**
    lines = SITE_FIXTURE.splitlines()
    want_ln = next(i for i, l in enumerate(lines, 1) if "99,993" in l)
    got = [w for w in sw if "99,993" in w]
    chk("산문 경고의 줄번호가 실제 줄과 맞는다",
        bool(got) and got[0].startswith("L%d " % want_ln), True)

    chk("발행본은 종전 경로 그대로 — 골격을 찾아 검사한다", len(rf), 3)
    chk("골격 갖춘 발행본에는 골격 WARN 이 없다",
        [w for w in rw if "[구조]" in w], [])
    # **지면 모드를 만들면서 이 경고를 죽이지 않았는지가 핵심이다.**
    # 골격 없는 발행본이 조용히 통과하면 그것이 사고 26이다.
    chk("골격 없는 발행본은 여전히 골격 WARN 4건",
        len([w for w in bw if "[구조]" in w]), 4)

    print("── 인수시험: 제목이 본문보다 넓게 말하는가 (사고 116) ──")
    # **장치의 존재는 검사의 수행이 아니다**(사고 26) — 발화하는지를 여기서 친다.
    wide = "# 편 — 창을 되찾는다\n\n> 리드.\n\n- **한 줄 결론**: 값.\n\n## 1. 핵심 요약\n\n가.\n\n## 2. 분석 결과\n"
    chk("넓이 주장에 범위가 없으면 잡는다",
        len(scope_warn(wide, conclusion_zones(wide))), 1)
    ok_md = wide.replace("> 리드.", "> **제목이 말하는 「되찾는다」의 범위는 하나다** — 읽을 수 있는 구간뿐이다.")
    chk("범위를 적으면 안 잡는다", scope_warn(ok_md, conclusion_zones(ok_md)), [])
    plain = wide.replace("창을 되찾는다", "45개월째 깨지지 않았다")
    chk("넓이를 주장 안 하는 제목은 아무 말도 안 한다",
        scope_warn(plain, conclusion_zones(plain)), [])
    # **오탐 분모를 같이 친다** — 발행본 전부에서 이 경고가 몇 건인가.
    live = [p for p in sorted((ROOT / "reports").glob("*.md"))]
    n_scope = sum(len([w for w in lint(p, facts)[1] if "[범위]" in w]) for p in live)
    chk("지금 발행본 %d편에서 범위 경고 0건" % len(live), n_scope, 0)

    print("지면 모드 통과" if ok else "지면 모드 실패")
    return ok


def selftest(facts):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "fixture.md"
        p.write_text(SELFTEST, encoding="utf-8")
        fails, warns, exempt = lint(p, facts)
    print("── 인수시험: 2026-08-25 사고 재현 픽스처 ──")
    for f in fails:
        print(f"    ✗ {f}")
    for w in warns:
        print(f"    · {w}")
    for e in exempt:
        print(f"    ~ {e}")
    blob = "\n".join(fails)
    exblob = "\n".join(exempt)
    missed = [k for k in MUST_FAIL if k not in blob]
    overcaught = [k for k in MUST_PASS if k in blob]
    leaked = [k for k in MUST_EXEMPT if k in blob or k not in exblob]
    print()
    if missed or overcaught or leaked:
        print(f"인수시험 실패 — 미검출 {missed} / 오탐 {overcaught} / 예외 실패 {leaked}")
        return False
    print(f"인수시험 통과 — 금지 {len(MUST_FAIL)}종 FAIL, [검증] 값 {MUST_PASS} 통과, 방법론·부인문 {len(MUST_EXEMPT)}종 예외")
    print()
    return (selftest_overclaim(facts) and selftest_channel(facts)
            and selftest_htmlurl(facts) and selftest_listcomma()
            and selftest_homonym() and selftest_site(facts))


def main():
    facts = load_facts()
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    if "--selftest" in sys.argv:
        print(f"대장 등재 수치 {len(facts)}건\n")
        sys.exit(0 if selftest(facts) else 1)

    show_exempt = "--show-exempt" in sys.argv
    channel = "--channel" in sys.argv
    args = [a for a in args if a not in ("--show-exempt", "--channel")]
    if channel and not args:
        sys.exit(0)
    # **[2026-09-12] `--hub` 모드를 없앴다.** 사고 69 가 만든 지면 모드는 옳았는데
    # **그 지면이 죽었다** — 한 번도 push 된 적 없는 저장소였다(사고 115).
    # 살아 있는 지면은 측심 하나이고 그것은 마크다운이 아니다 —
    # `check_claims.py` 와 `check_site_facts.py` 가 그쪽을 본다.
    targets = [Path(a) for a in args] or sorted((ROOT / "reports").glob("*.md"))
    tf = tw = te = 0
    mode = " · 채널 문안 모드(전문을 결론 자리로 본다)" if channel else ""
    print(f"대장 등재 수치 {len(facts)}건 · 검사 대상 {len(targets)}건{mode}\n")
    for p in targets:
        fails, warns, exempt = lint(p, facts, channel)
        kind = ("채널" if channel else
                ("지면" if is_site(p.read_text(encoding="utf-8")) else "발행본"))
        tf += len(fails)
        tw += len(warns)
        te += len(exempt)
        mark = "FAIL" if fails else ("WARN" if warns else "PASS")
        # **이름이 겹치면 부모까지 붙인다.** 허브에 `index.md` 가 넷이라
        # (홈·터미널·데이터·보고서) 이름만 찍으면 FAIL 이 어느 지면인지 안 갈린다 —
        # 2026-08-29에 실제로 한 번 헷갈렸다. 검사기가 잡아 놓고 어디인지 안 알려 주면
        # 그만큼은 안 잡은 것과 같다.
        label = f"{p.parent.name}/{p.name}" if p.name == "index.md" else p.name
        # **어느 모드로 검사했는지 매 줄에 찍는다.** 모드가 자동이면 그만큼
        # 「무엇이 검사됐나」가 안 보이게 되고, 안 보이는 검사는 사고 26이다.
        print(f"[{mark}] {label}  ({kind} · FAIL {len(fails)} / WARN {len(warns)} / 예외 {len(exempt)})")
        for f in fails:
            print(f"    ✗ {f}")
        for w in warns:
            print(f"    · {w}")
        if show_exempt:
            for e in exempt:
                print(f"    ~ {e}")
    print(f"\n합계  FAIL {tf}  WARN {tw}  인과 예외 {te}건"
          + ("" if show_exempt else "  (--show-exempt 로 열람)"))
    if tf:
        print("FAIL이 있으므로 발행하지 않는다.")
        sys.exit(1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""채널 규칙 정본 — **채널이 정한 것과 우리가 정한 것을 갈라 둔다.**

왜 있는가
---------
채널마다 형식·길이·되돌릴 수 있는가가 다르고, **그 차이가 게시 사고의 자리다.**
GeekNews 는 두 시간 뒤 삭제가 안 되고, 자기 것을 News 에 올리면 지워진다.
링크드인은 3,000자를 받지만 독자가 보는 것은 앞 140자다.
디스콰이엇은 프로덕트를 먼저 등록해야 글이 피드에 뜬다.

**이 셋을 사람이 기억하면 유실된다**(사고 22). 그래서 파일로 꺼낸다.

  python analysis/channels.py --list        # 규칙 전문
  python analysis/channels.py --selftest

**「채널이 정한 것」과 「우리가 정한 것」을 갈라 적는다.**
앞엣것은 어기면 글이 지워지고, 뒤엣것은 어기면 우리 규율이 깨진다. 처분이 다르다.

닿지 않는 곳
------------
· **채널 규칙은 낡는다.** 각 항목에 `확인일`과 `출처`를 붙였다 — 확인일이 오래됐으면
  다시 본다. **이 파일이 최신이라는 보장은 아무 데도 없다.**
· **길이 상한 일부는 [미확인]이다.** 관측값(실제 게시물에서 잰 것)과 공표된 상한을
  구별해 적었다. **관측은 상한이 아니다.**
· 형식만 본다. **문안이 좋은지는 안 본다.**
"""

import argparse
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FAIL, WARN, INFO = "FAIL", "WARN", "INFO"

# ── 채널 규칙 ───────────────────────────────────────────────────────────────
#
# 「하드」 = 채널이 정한 것(어기면 글이 잘리거나 지워진다)
# 「관측」 = 실제 게시물에서 잰 것(상한이 아니다)
# 「우리」 = 이 프로젝트가 정한 것(지침 §3·§7)

CHANNELS = {
    "linkedin": {
        "utm": ("linkedin", "social"),           # 측심 링크 UTM(source, medium) — 우리 규칙(2026-10-22 · li-12·th-01 이 UTM 없이 나감)
        "이름": "링크드인",
        "주소": "https://www.linkedin.com/feed/",
        "확인일": "2026-09-09",
        "출처": "공표 문서·업계 집계(3,000자 상한 · 「…더 보기」 절단점)",
        "제목": False,                      # 게시물에 제목 칸이 없다
        "본문상한": 3000,                   # 하드
        "훅": 140,                          # 모바일 절단점. 데스크톱은 약 210
        "되돌릴수있나": True,               # 수정·삭제 가능
        "자기것허용": True,
        "링크카드": "**마지막으로 입력된** URL 하나에 붙는다. 본문 위치가 아니라 **입력 순서**다",
        "사람이할일": "로그인 · 게시 버튼 · 카드 미리보기 확인",
        "메모": [
            "**앞 140자가 전부다.** 그 뒤는 「…더 보기」를 눌러야 보인다 — 결론을 앞에 둔다.",
            "URL 이 여럿이면 **마지막으로 입력된 것**에 카드가 붙는다. **본문 어디 있는지는 상관없다.**",
            "  *2026-09-10 확정. 종전에 관측 둘이 갈려 [미확인]으로 뒀는데, 운영자가 li-01 을 올릴 때의"
            "  조작 순서를 주자 **한 기전으로 둘 다 설명됐다** — ①측심 URL 만 침 → 측심 카드"
            "  ②본문과 인천 링크를 뒤에 침 → 카드가 인천으로 바뀜 ③카드 우측 X 로 인천 카드를 지움"
            "  ④본문 첫 줄의 측심 URL 을 지웠다 **다시 타이핑** → 측심 카드."
            "  그래서 본문 순서는 [측심, 인천] 인데 카드는 측심이다. **위치가 아니라 입력 순서다.**"
            "  li-02 는 전문을 **한 번에** 넣었으므로 입력 순서 = 본문 순서였고, 그래서 마지막이 카드였다.)*",
            "**한 번에 붙여넣는 우리 경로에서는 「입력 순서 = 본문 순서」다** — 카드로 띄울 것을 **맨 끝**에 둔다.",
            "카드를 바꾸려면 **X 로 지우고 원하는 URL 을 다시 타이핑**한다(위 ③④).",
            "**그래도 붙여넣은 뒤 미리보기를 눈으로 본다**(사고 73) — 규칙을 알아도 확인은 확인이다.",
            "한글 경로는 퍼센트 인코딩된다. 붙여넣은 뒤 **미리보기가 뜨는지 눈으로 본다.**",
            "**링크는 게시 뒤 `lnkd.in` 으로 바뀐다**(링크드인이 자기 단축기를 쓴다). "
            "우리가 단축 URL 을 넣는 것과 다르다 — 질의 문자열(`?src=`)은 그대로 따라간다.",
        ],
    },
    "geeknews": {
        "utm": ("geeknews", "social"),           # 측심 링크 UTM(source, medium) — 우리 규칙(2026-10-22 · li-12·th-01 이 UTM 없이 나감)
        "이름": "GeekNews",
        "주소": "https://news.hada.io/new",
        "확인일": "2026-09-09",
        "출처": "news.hada.io/guidelines · /faq · /show 실측",
        "제목": True,
        "제목접두": "Show GN: ",           # 자기 것은 Show 로 간다
        "제목관측": (29, 85),               # 2026-09-09 · /show 20건 실측 (중앙 52)
        "본문상한": None,                   # [미확인] — 공표된 상한을 못 찾았다
        "훅": None,
        "되돌릴수있나": False,              # **두 시간 안에만 삭제. 수정은 없다**
        "삭제유예": "2시간",
        "자기것허용": "Show 만",            # News 에 올리면 삭제 대상
        "링크카드": None,
        "사람이할일": "로그인 · 최종 문안 승인 · 등록 버튼",
        "메모": [
            "**자기 것은 Show 로 간다.** 본인·소속이 만든 서비스·도구를 News 에 올리면 삭제 대상이다.",
            "**두 시간이 지나면 못 지운다.** 수정 기능은 없다 — 게시 전 전문 승인이 필수다.",
            "제목에 **사이트명을 넣지 않는다**(주소가 따로 뜬다). 단축 URL 금지. 낚시 제목 금지.",
            "본문은 **원글 요약**을 담는다. **충분히 검토하지 않은 AI 요약은 제한 대상**이라고 지침이 적는다.",
            "같은 출처를 반복해 올리는 것이 제한된다 — **한 번에 몰지 않는다.**",
        ],
    },
    "email": {
        "utm": ("email", "email"),           # 측심 링크 UTM(source, medium) — 우리 규칙(2026-10-22 · li-12·th-01 이 UTM 없이 나감)
        "이름": "메일(1:1 서신)",
        "주소": "—",
        "확인일": "2026-09-10",
        "출처": "—",
        "제목": True,                       # 메일 제목
        "제목접두": None,
        "제목관측": None,
        "본문상한": None,
        "훅": None,
        "게시지면": False,                  # **열어 볼 지면이 없다** — 1:1 서신이라 「주소」가 성립 안 한다
        "되돌릴수있나": False,              # **보낸 메일은 회수 못 한다**
        "삭제유예": "없다",                 # GeekNews 의 두 시간조차 없다
        "자기것허용": True,
        "링크카드": None,
        "사람이할일": "수신자 확인 · 최종 문안 승인 · 발송",
        "메모": [
            "**회수가 안 된다.** GeekNews 의 두 시간 유예조차 없다 — **게시 전 전문 승인이 필수다.**",
            "**이것은 §7 의 「채널」이 아니다.** 1:1 서신이라 허브-스포크(원문은 자체 사이트)와 무관하다.",
            "**다만 수치는 결론 자리와 같은 규율을 받는다**(§3) — 밖으로 나가는 주장이기 때문이다.",
            "**수신자 주소·이름은 문안 파일에 안 넣는다**(§4.1 · 공개 저장소에 안 옮기는 것과 같은 이유).",
        ],
    },
    # [2026-10-12 53차] 릴스 채널 둘. **수치는 세션 지식이고 공식 문서와 아직 대조하지 않았다** — 이 세션 망이
    #   instagram.com·threads.net 도움말을 막는다. 그래서 상한은 「하드」가 아니라 WARN 으로만 쓰고(아래 「상한확인」),
    #   다음에 공식 문서를 본 세션이 확인일·출처를 고친다.
    "instagram": {
        "utm": ("instagram", "social"),           # 측심 링크 UTM(source, medium) — 우리 규칙(2026-10-22 · li-12·th-01 이 UTM 없이 나감)
        "이름": "인스타그램(릴스)",
        "주소": "https://www.instagram.com/",
        "확인일": "2026-10-12",
        "출처": "[미확인] 세션 지식 — 공식 도움말 대조 전",
        "상한확인": False,                  # 상한을 확인 못 했다 → 넘어도 FAIL 이 아니라 WARN
        "제목": False,
        "본문상한": 2200,                   # 캡션 상한(세션 지식)
        "훅": 125,                          # 피드에서 「…더 보기」 앞(세션 지식)
        "되돌릴수있나": True,               # 게시물 수정·삭제 가능
        "자기것허용": True,
        "캡션링크클릭": False,              # 캡션 안의 URL 은 눌리지 않는다 → 프로필 링크로
        "링크카드": None,
        "사람이할일": "로그인 · 영상 올리기 · 표지 고르기 · 게시 버튼",
        "메모": [
            "**캡션의 링크는 안 눌린다.** 측심 주소는 프로필 링크(UTM `utm_source=instagram`)로 보내고, 캡션에는 「프로필 링크」라고만 적는다.",
            "**첫 3초가 전부다**(확장 기준 31 · 홍보 방침) — 결과를 먼저 보이고 설명은 뒤에.",
            "영상은 `reels.yml` 이 Actions 에서 렌더한 artifact 를 쓴다. 소리 없음(Edge TTS·기본 배경음악 안 씀).",
            "상한 수치(캡션 2,200자 · 앞 125자)는 **[미확인]** — 공식 도움말을 본 세션이 확인일과 같이 고친다.",
        ],
    },
    "threads": {
        "utm": ("threads", "social"),           # 측심 링크 UTM(source, medium) — 우리 규칙(2026-10-22 · li-12·th-01 이 UTM 없이 나감)
        "이름": "스레드",
        "주소": "https://www.threads.net/",
        "확인일": "2026-10-12",
        "출처": "[미확인] 세션 지식 — 공식 도움말 대조 전",
        "상한확인": False,
        "제목": False,
        "본문상한": 500,                    # 게시물 상한(세션 지식)
        "훅": None,
        "되돌릴수있나": True,
        "자기것허용": True,
        "링크카드": "링크 미리보기 카드가 붙는다(세션 지식 · [미확인])",
        "사람이할일": "로그인 · 게시 버튼 · 카드 미리보기 확인",
        "메모": [
            "**짧다.** 상한(세션 지식 500자)을 넘으면 이어 쓰기(스레드)로 나뉜다 — 결론을 첫 글에.",
            "링크는 UTM `utm_source=threads` 로 가른다(확장 기준 30).",
            "상한 수치는 **[미확인]** — 공식 도움말을 본 세션이 고친다.",
        ],
    },
    "tistory": {
        "utm": ("tistory", "blog"),
        "이름": "티스토리 블로그 「물류의 모든 것」",
        "주소": "https://logisticsforeveryone.tistory.com/",
        "확인일": "2026-10-22",
        "출처": "선장님 지정(10/22 채팅 · 게시처 · 필명) · 형식 상한은 [미확인] 세션 지식",
        "상한확인": False,
        "제목": True,
        "제목접두": None,
        "제목관측": None,
        "본문상한": None,                   # [미확인]
        "훅": None,
        "되돌릴수있나": True,               # 수정·삭제 가능(세션 지식)
        "자기것허용": True,
        "필명": "물류로그",                 # **실명 금지** — 본문·제목에 data/profile.json 이름이 있으면 FAIL
        "링크카드": "본문 링크는 눌린다 · 미리보기 카드 여부는 [미확인]",
        "사람이할일": "로그인 · 글쓰기 화면에 붙여넣기 · 발행 버튼",
        "메모": [
            "**필명 「물류로그」로만 쓴다 — 실명·학교·자격 줄 0**(선장님 10/22). 실명은 data/profile.json 한 곳에만 산다.",
            "원문은 측심에 둔다 — 블로그는 요약과 링크(§7 허브-스포크). 측심 링크는 UTM `utm_source=tistory&utm_medium=blog`.",
            "본문 상한·카드 동작은 **[미확인]** — 첫 게시 뒤 실측해 고친다.",
        ],
    },
    "beehiiv": {
        "utm": ("beehiiv", "email"),
        "이름": "뉴스레터(Beehiiv · 물류로그)",
        "주소": "https://app.beehiiv.com/",
        "확인일": "2026-10-22",
        "출처": "선장님 지정(10/22 채팅 · 뉴스레터 = Beehiiv · 필명) · 형식은 [미확인] 세션 지식",
        "상한확인": False,
        "제목": True,                       # 메일 제목
        "제목접두": None,
        "제목관측": None,
        "본문상한": None,
        "훅": None,
        "되돌릴수있나": False,              # **메일로 나간 것은 회수 못 한다**(웹 판은 고칠 수 있어도 받은편지함은 남는다)
        "삭제유예": "없다(발송분)",
        "자기것허용": True,
        "필명": "물류로그",
        "링크카드": None,
        "사람이할일": "로그인 · 구독자 확인 · 최종 문안 승인 · 발송",
        "메모": [
            "**발송은 되돌릴 수 없다** — 메일과 같다. 게시 전 전문 승인이 필수다.",
            "**필명 「물류로그」로만 — 실명 0.** 구독 신청 주소(구독 페이지)는 선장님이 계정을 연 뒤 대기열·지면에 단다.",
            "측심 링크는 UTM `utm_source=beehiiv&utm_medium=email`.",
        ],
    },
    "disquiet": {
        "utm": ("disquiet", "social"),           # 측심 링크 UTM(source, medium) — 우리 규칙(2026-10-22 · li-12·th-01 이 UTM 없이 나감)
        "이름": "디스콰이엇",
        "주소": "https://disquiet.io/",
        "확인일": "2026-09-09",
        "출처": "disquiet.io/articles/Brs7Dy(메이커로그 소개) · 공식 안내",
        "제목": True,
        "제목접두": None,
        "제목관측": None,                   # [미확인]
        "본문상한": None,                   # [미확인]
        "훅": None,
        "되돌릴수있나": True,
        "자기것허용": True,                 # **자기 것만** 등록된다
        "링크카드": "첫 줄 이미지가 피드 썸네일이 된다",
        "선행조건": "프로덕트 등록",        # 등록 안 하면 메인 피드에 안 뜬다
        "사람이할일": "로그인 · 프로덕트 1회 등록 · 게시 버튼",
        "메모": [
            "**프로덕트를 먼저 등록한다.** 메인 피드에는 **프로덕트에 연결된 글만** 뜬다.",
            "**본인이 만든 프로덕트만** 등록된다.",
            "글은 **메이커로그** — 결과물이 아니라 **만드는 과정**을 적는 자리다.",
            "**첫 줄에 이미지**를 넣으면 그것이 피드 미리보기 썸네일이 된다.",
            "길이 상한은 **[미확인]** — 공표된 값을 못 찾았다.",
        ],
    },
}

# 우리가 정한 것 (지침 §3 · §7) — 채널을 안 가린다.
OURS = [
    "채널 헤드라인은 **결론 자리**다(§3). 결론 자리 수치는 FACTS 등재 + 지위 `검증`/`관측`.",
    "**원문은 자체 사이트에 둔다. 채널은 링크만.**(§7 허브-스포크)",
    "**낡는 값을 넣지 않는다** — 편수 · 「가장 최근」 · 잔액(사고 31·83).",
    "**이미 게시된 것은 그때의 기록이다 — 낡은 값을 현재로 고치지 않는다.**"
    " 게시물에는 시각이 붙어 있고 그것이 창을 말한다. 지금 값으로 다시 쓰면"
    " **기록을 현재에 맞춰 계속 고치는 습관**이 되고, 그것은 이 브랜드가 파는 것의 반대다"
    "(§3-11 · #01~#06 소급 정정 안 함). **아직 안 낡은 것은 미리 뺀다** — 그 둘은 다르다.",
    "**인과를 쓰지 않는다**(§3-5 예외 말고는).",
]

# 낡는 값 — 문장에 박으면 다음 편에서 틀린다(사고 31·83).
STALE = [
    # 「9편」·「아홉 편」. 앞에 수가 오면 그것은 편수다 — 편수는 다음 편에서 틀린다.
    # 앞이 한글이면 세는 말이 아니다 — 「확인**한** 편입니다」의 「한」이 그것이다(실측 오탐).
    (re.compile(r"(?<![0-9가-힣])([0-9]{1,3}|[한두세네다섯여섯일곱여덟아홉열]{1,3})\s*편"),
     "편수(「N편」)"),
    (re.compile(r"가장\s*(최근|최신)"), "「가장 최근」"),
    (re.compile(r"현재\s*[0-9]"), "「현재 N」"),
    (re.compile(r"오늘|어제|이번\s*주|지난주"), "상대 날짜"),
]

SITE = re.compile(r"https?://jisangj03-dev\.github\.io/incheon-port-analysis(?:[/?#]|$)", re.I)  # 측심 공개판


def real_name():
    """실명 — data/profile.json 한 곳에서만 읽는다(필명 채널 검사용 · 저장소의 다른 곳에 실명을 두지 않는다)."""
    try:
        import json, os
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "profile.json")
        return (json.load(open(p, encoding="utf-8")).get("name") or "").strip() or None
    except Exception:
        return None


def utm_problems(channel, body, rid=None):
    """측심 링크마다 UTM 이 채널 값과 같은가 — [(레벨, 메시지)]. 우리 규칙(2026-10-22 선장님 「모든 측심 링크에 UTM 필수」)."""
    c = rules(channel)
    want = c.get("utm")
    out = []
    if not want:
        return out
    from urllib.parse import urlsplit, parse_qs
    for u in urls(body):
        if not SITE.match(u):
            continue
        q = {k: v[0] for k, v in parse_qs(urlsplit(u).query).items()}
        miss = []
        if q.get("utm_source") != want[0]: miss.append("utm_source=%s" % want[0])
        if q.get("utm_medium") != want[1]: miss.append("utm_medium=%s" % want[1])
        if not q.get("utm_campaign") or (rid and q.get("utm_campaign") != rid): miss.append("utm_campaign=%s" % (rid or "<대기열 id>"))
        if miss:
            out.append((FAIL, "측심 링크에 UTM 이 없거나 다르다 — %s 필요: %s" % (" · ".join(miss), u)))
    return out


def withdrawn_problems(body, dist=None):
    """측심 링크가 내린 지면(옮긴 주소 · Redirect)이나 빌드에 없는 지면을 가리키나 — [(레벨, 메시지)].
    내린 지면도 200 을 돌려주므로 `--net` 링크 검사로는 안 잡힌다(사고 139 · li-08·09·10 이 10/20 내림 뒤에도 내린 보고서를 가리킨 채 「준비」였다).
    빌드(astro/dist)가 없으면 아무 말도 안 한다 — 판정 못 한 것을 통과로 세지 않도록 호출자가 INFO 를 낸다."""
    import os
    from urllib.parse import urlsplit, unquote
    dist = dist or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "astro", "dist")
    if not os.path.isdir(dist):
        return None
    out = []
    for u in urls(body):
        if not SITE.match(u):
            continue
        path = unquote(urlsplit(u).path).split("/incheon-port-analysis", 1)[-1].lstrip("/")
        f = os.path.join(dist, path, "index.html") if (not path or path.endswith("/")) else os.path.join(dist, path)
        if not os.path.isfile(f):
            out.append((FAIL, "측심 링크가 빌드에 없는 지면을 가리킨다: %s" % u))
        elif "data-redirect=" in open(f, encoding="utf-8", errors="ignore").read():
            out.append((FAIL, "측심 링크가 내린 지면(옮긴 주소 안내)을 가리킨다 — 독자는 「옮겼습니다」 쪽에 떨어진다: %s" % u))
    return out


SHORTENER = re.compile(r"https?://(bit\.ly|tinyurl\.com|t\.co|lnkd\.in|han\.gl|buly\.kr|url\.kr)/", re.I)
URL = re.compile(r"https?://[^\s<>\"')\]]+")


def rules(channel):
    key = channel.strip().lower()
    if key not in CHANNELS:
        raise KeyError("모르는 채널: %s (아는 것: %s)" % (channel, " · ".join(sorted(CHANNELS))))
    return CHANNELS[key]


def urls(text):
    return [u.rstrip(".,)") for u in URL.findall(text or "")]


def check_format(channel, body, title=None, rid=None):
    """채널 형식만 본다. 반환 [(레벨, 메시지)]. **수치·링크 생존은 여기서 안 본다.** rid = 대기열 id(UTM campaign 대조)."""
    c = rules(channel)
    out = []
    body = body or ""
    n = len(body)

    # ── 제목 ──
    if c["제목"]:
        if not (title or "").strip():
            out.append((FAIL, "이 채널은 제목이 필요하다 — 비어 있다"))
        else:
            t = title.strip()
            pre = c.get("제목접두")
            if pre and not t.startswith(pre):
                out.append((FAIL, "자기 것은 `%s` 로 시작한다 — News 에 올리면 삭제 대상이다" % pre.strip()))
            obs = c.get("제목관측")
            if obs and len(t) > obs[1]:
                out.append((WARN, "제목 %d자 — 관측 최장 %d자를 넘는다(하드 상한은 [미확인])"
                            % (len(t), obs[1])))
            if SHORTENER.search(t):
                out.append((FAIL, "제목에 단축 URL — 금지"))
    elif (title or "").strip():
        out.append((INFO, "이 채널에는 제목 칸이 없다 — 제목은 안 나간다"))

    # ── 본문 길이 ──
    if not body.strip():
        out.append((FAIL, "본문이 비어 있다"))
    cap = c.get("본문상한")
    sure = c.get("상한확인", True)          # 확인 못 한 상한은 FAIL 이 아니라 WARN(53차 · 릴스 채널)
    if cap and n > cap:
        out.append((FAIL if sure else WARN, "본문 %d자 — 상한 %d자%s를 넘는다. 잘린다"
                    % (n, cap, "" if sure else "([미확인] 세션 지식)")))
    elif cap and n > cap * 0.9:
        out.append((WARN, "본문 %d자 — 상한 %d자의 90%%를 넘었다" % (n, cap)))
    elif cap is None:
        out.append((INFO, "본문 %d자 — 이 채널의 상한은 [미확인]이다" % n))

    # ── 훅 ──
    hook = c.get("훅")
    if hook:
        head = body[:hook]
        out.append((INFO, "앞 %d자(모바일 절단점)에 들어가는 것: 「%s」"
                    % (hook, head.replace("\n", " ")[:hook])))
        if not urls(head) and len(body) > hook and "\n" in body[:hook]:
            pass  # 링크가 앞에 없는 것은 정상이다
        first = body.strip().split("\n")[0]
        if len(first) > hook:
            out.append((WARN, "첫 줄이 %d자 — 절단점 %d자를 넘는다. 첫 줄에서 끊긴다"
                        % (len(first), hook)))

    # ── 링크 ──
    us = urls(body)
    if not us:
        out.append((WARN, "본문에 링크가 없다 — 채널은 링크만 든다(§7)"))
    for u in us:
        if SHORTENER.search(u):
            out.append((FAIL, "단축 URL: %s" % u))
    if us and c.get("캡션링크클릭") is False:
        out.append((WARN, "이 채널은 본문 링크가 **안 눌린다** — 프로필 링크로 보내고 본문에는 「프로필 링크」라고 적는다"))
    if c.get("링크카드") and len(us) > 1 and channel.lower() == "linkedin":
        # 카드는 **마지막으로 입력된** URL 에 붙는다. 한 번에 붙여넣으면 그것이 마지막 URL 이다.
        out.append((INFO, "URL %d개 — 한 번에 붙여넣으면 카드는 **마지막** URL(%s)에 붙는다"
                          % (len(us), us[-1])))

    # ── 되돌릴 수 있는가 ──
    if not c.get("되돌릴수있나"):
        out.append((WARN, "**되돌릴 수 없는 채널이다** — 삭제 유예 %s · 수정 없음. "
                    "게시 전 전문 승인이 필수다" % c.get("삭제유예", "[미확인]")))
    if c.get("선행조건"):
        out.append((WARN, "선행 조건: **%s** — 안 되어 있으면 글이 피드에 안 뜬다" % c["선행조건"]))

    # ── 우리 규율 ──
    out += utm_problems(channel, body, rid)
    wd = withdrawn_problems(body)
    if wd is None:
        if any(SITE.match(u) for u in urls(body)):
            out.append((INFO, "내린 지면 링크는 안 봤다 — 빌드(astro/dist)가 없다(`npm run site:build` 뒤 다시)"))
    else:
        out += wd
    if c.get("필명"):
        nm = real_name()
        if nm and (nm in body or nm in (title or "")):
            out.append((FAIL, "필명 채널(「%s」)에 실명이 들었다 — 실명 금지(선장님 10/22)" % c["필명"]))
    for pat, what in STALE:
        m = pat.search(body) or (pat.search(title) if title else None)
        if m:
            out.append((WARN, "낡는 값 — %s: 「%s」(사고 31·83)" % (what, m.group(0))))
    return out


def worst(findings):
    if any(l == FAIL for l, _ in findings):
        return FAIL
    if any(l == WARN for l, _ in findings):
        return WARN
    return "PASS"


def show():
    print("== 채널 규칙 ==")
    print("**「채널이 정한 것」을 어기면 글이 지워지고, 「우리가 정한 것」을 어기면 규율이 깨진다.**\n")
    for key in sorted(CHANNELS):
        c = CHANNELS[key]
        print("── %s (`%s`) ──" % (c["이름"], key))
        print("   주소 %s" % c["주소"])
        print("   확인일 %s · 출처: %s" % (c["확인일"], c["출처"]))
        cap = c.get("본문상한")
        print("   제목 %s · 본문 상한 %s · 훅 %s"
              % ("있다" + (" (접두 `%s`)" % c["제목접두"] if c.get("제목접두") else "")
                 if c["제목"] else "없다",
                 ("%d자" % cap) if cap else "[미확인]",
                 ("앞 %d자" % c["훅"]) if c.get("훅") else "—"))
        print("   되돌릴 수 있나: %s%s"
              % ("예" if c["되돌릴수있나"] else "**아니다**",
                 ("(삭제 유예 %s · 수정 없음)" % c["삭제유예"]) if not c["되돌릴수있나"] else ""))
        print("   사람이 할 일: %s" % c["사람이할일"])
        for m in c["메모"]:
            print("     · %s" % m)
        print()
    print("── 우리가 정한 것 (채널을 안 가린다) ──")
    # (메일은 §7 채널이 아니지만 수치 규율은 같이 받는다 — 위 `email` 메모.)
    for m in OURS:
        print("   · %s" % m)
    return 0


def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    def levels(f):
        return [l for l, _ in f]

    print("── 인수시험: 채널을 가리는가 ──")
    chk("아는 채널 여덟", sorted(CHANNELS),
        ["beehiiv", "disquiet", "email", "geeknews", "instagram", "linkedin", "threads", "tistory"])
    chk("메일은 회수가 안 된다", CHANNELS["email"]["되돌릴수있나"], False)
    chk("메일은 유예조차 없다", CHANNELS["email"]["삭제유예"], "없다")
    chk("메일은 게시 지면이 없다", CHANNELS["email"].get("게시지면"), False)
    chk("나머지 셋은 지면이 있다",
        [CHANNELS[c].get("게시지면", True) for c in ("linkedin", "geeknews", "disquiet", "instagram", "threads")],
        [True, True, True, True, True])

    print("── 인수시험: 측심 링크 UTM (2026-10-22) ──")
    S = "https://jisangj03-dev.github.io/incheon-port-analysis/"
    f = check_format("linkedin", "글\n" + S)
    chk("UTM 없는 측심 링크는 FAIL", any("UTM" in m for l, m in f if l == FAIL), True)
    f = check_format("linkedin", "글\n" + S + "?utm_source=linkedin&utm_medium=social&utm_campaign=li-13", rid="li-13")
    chk("맞는 UTM 은 통과", any("UTM" in m for _, m in f), False)
    f = check_format("linkedin", "글\n" + S + "?utm_source=threads&utm_medium=social&utm_campaign=li-13", rid="li-13")
    chk("다른 채널 UTM 은 FAIL", any("utm_source=linkedin" in m for l, m in f if l == FAIL), True)
    f = check_format("linkedin", "글\n" + S + "?utm_source=linkedin&utm_medium=social&utm_campaign=li-99", rid="li-13")
    chk("campaign 이 대기열 id 와 다르면 FAIL", any("utm_campaign=li-13" in m for l, m in f if l == FAIL), True)
    f = check_format("linkedin", "글\nhttps://example.org/")
    chk("측심 밖 링크는 UTM 을 안 본다", any("UTM" in m for _, m in f), False)
    print("── 인수시험: 내린 지면 링크 (2026-10-23 · 사고 139) ──")
    import tempfile, os as _os
    with tempfile.TemporaryDirectory() as D:
        _os.makedirs(_os.path.join(D, "reports")); _os.makedirs(_os.path.join(D, "tools"))
        open(_os.path.join(D, "reports", "물동량.html"), "w", encoding="utf-8").write('<div data-redirect="/notes.html">옮겼습니다</div>')
        open(_os.path.join(D, "tools", "radar.html"), "w", encoding="utf-8").write("<h1>레이더</h1>")
        open(_os.path.join(D, "index.html"), "w", encoding="utf-8").write("<h1>홈</h1>")
        q = "?utm_source=linkedin&utm_medium=social&utm_campaign=li-10"
        chk("내린 지면 링크는 FAIL", levels(withdrawn_problems(S + "reports/%EB%AC%BC%EB%8F%99%EB%9F%89.html" + q, D)), [FAIL])
        chk("빌드에 없는 지면은 FAIL", levels(withdrawn_problems(S + "tools/nope.html" + q, D)), [FAIL])
        chk("살아 있는 지면·홈은 통과", withdrawn_problems(S + "tools/radar.html" + q + "\n" + S + q, D), [])
        chk("빌드가 없으면 판정 안 함(None)", withdrawn_problems(S, _os.path.join(D, "없음")), None)
    f = check_format("tistory", "본문\n" + S + "?utm_source=tistory&utm_medium=blog&utm_campaign=tb-01", title="제목", rid="tb-01")
    chk("티스토리 정상 문안은 FAIL 없다", FAIL in levels(f), False)
    nm = real_name()
    if nm:
        f = check_format("tistory", "글쓴이 " + nm + "\n" + S + "?utm_source=tistory&utm_medium=blog&utm_campaign=tb-01", title="제목", rid="tb-01")
        chk("필명 채널에 실명이 있으면 FAIL", any("실명" in m for l, m in f if l == FAIL), True)
    chk("뉴스레터 발송은 되돌릴 수 없다", CHANNELS["beehiiv"]["되돌릴수있나"], False)

    print("── 인수시험: 릴스 채널(상한 [미확인]) ──")
    f = check_format("instagram", "가" * 2300 + "\nhttps://a.b/c")
    chk("인스타 상한은 확인 전이라 FAIL 아닌 WARN", FAIL in levels(f), False)
    chk("인스타 상한 초과는 WARN 으로 말한다", any("2200" in m for l, m in f if l == WARN), True)
    chk("인스타 캡션 링크는 안 눌린다고 경고", any("안 눌린다" in m for _, m in f), True)
    f = check_format("threads", "짧은 글\nhttps://a.b/c")
    chk("스레드 정상 문안은 FAIL 없다", FAIL in levels(f), False)
    f = check_format("linkedin", "가" * 3100 + "\nhttps://a.b")
    chk("확인된 상한(링크드인)은 여전히 FAIL", FAIL in levels(f), True)
    try:
        rules("브런치")
        chk("모르는 채널은 막는다", True, False)
    except KeyError:
        chk("모르는 채널은 막는다", True, True)

    print("── 인수시험: 링크드인 ──")
    f = check_format("linkedin", "짧은 글.\nhttps://sounding.higgsfield.app")
    chk("정상 문안은 FAIL 없다", FAIL in levels(f), False)
    f = check_format("linkedin", "가" * 3100 + "\nhttps://a.b")
    chk("3,000자 넘으면 FAIL", FAIL in levels(f), True)
    f = check_format("linkedin", "가" * 200 + "\n둘째 줄\nhttps://a.b")
    chk("첫 줄이 절단점을 넘으면 WARN", any("절단점" in m for _, m in f), True)
    f = check_format("linkedin", "글 https://bit.ly/x")
    chk("단축 URL 은 FAIL", FAIL in levels(f), True)
    f = check_format("linkedin", "링크 없는 글")
    chk("링크 없으면 WARN", WARN in levels(f), True)

    print("── 인수시험: GeekNews — 되돌릴 수 없는 채널 ──")
    f = check_format("geeknews", "요약 본문. https://sounding.higgsfield.app",
                     title="측심 - 인천항을 공공 1차 데이터로 잽니다")
    chk("Show GN 접두가 없으면 FAIL", FAIL in levels(f), True)
    f = check_format("geeknews", "요약 본문. https://sounding.higgsfield.app",
                     title="Show GN: 측심 - 인천항을 공공 1차 데이터로 잽니다")
    chk("접두가 있으면 FAIL 없다", FAIL in levels(f), False)
    chk("되돌릴 수 없다고 말한다", any("되돌릴 수 없는" in m for _, m in f), True)
    f = check_format("geeknews", "본문", title=None)
    chk("제목 없으면 FAIL", FAIL in levels(f), True)
    f = check_format("geeknews", "본문 https://a.b", title="Show GN: " + "가" * 90)
    chk("관측 최장을 넘으면 WARN", any("관측 최장" in m for _, m in f), True)

    print("── 인수시험: 디스콰이엇 — 선행 조건 ──")
    f = check_format("disquiet", "메이커로그 본문. https://sounding.higgsfield.app", title="측심을 만들며")
    chk("프로덕트 등록을 선행 조건으로 말한다",
        any("프로덕트 등록" in m for _, m in f), True)
    chk("상한이 미확인이라고 말한다", any("[미확인]" in m for _, m in f), True)

    print("── 인수시험: 낡는 값 (사고 31·83) ──")
    for bad, what in (("보고서 9편을 묶었습니다. https://a.b", "편수"),
                      ("가장 최근 편은 이것입니다. https://a.b", "가장 최근"),
                      ("오늘 공개했습니다. https://a.b", "상대 날짜")):
        f = check_format("linkedin", bad)
        chk("%s 를 잡는다" % what, any("낡는 값" in m for _, m in f), True)
    f = check_format("linkedin", "252개월 동안 뒤집히지 않았습니다. https://a.b")
    chk("창이 붙은 수치는 안 잡는다", any("낡는 값" in m for _, m in f), False)

    print("── 인수시험: 판정 ──")
    chk("FAIL 이 있으면 FAIL", worst([(WARN, ""), (FAIL, "")]), FAIL)
    chk("WARN 만이면 WARN", worst([(INFO, ""), (WARN, "")]), WARN)
    chk("INFO 만이면 PASS", worst([(INFO, "")]), "PASS")

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="채널 규칙 정본")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else show())

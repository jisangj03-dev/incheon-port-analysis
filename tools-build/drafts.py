"""홍보 초안 = 틀 + 데이터(갱신 무인화 ① · docs/측심_갱신무인화_판정기준_선커밋_20261022.md).

  content-queue/templates/<id>.md 는 숫자를 적지 않는다 — {{이름}}(data/derived/facts.json) · {{claim:id.형}}(data/claims.json 의 승인 갈래 문장)만 부른다.
  이 스크립트가 채워 content-queue/live/<id>.md 로 낸다. refresh 가 원천 갱신 때마다 facts.py 다음에 다시 돌린다 — 게시 직전에도 live 판이 지면과 같은 숫자다.
  (10/22: 손으로 적은 초안 「51분」과 띠 그림 「52분」이 서로 다른 기준이었다 — 숫자를 사람이 옮겨 적지 않는다.)

  python tools-build/drafts.py            live 판을 쓴다
  python tools-build/drafts.py --check    틀에 숫자 글자가 없는가 · 이름이 다 있는가 · live 판이 지금 데이터로 다시 만든 것과 같은가(아니면 종료 1)
  python tools-build/drafts.py --selftest

  틀 머리에 `posts: <대기열 id> <채널> <절 제목> | …` 가 있으면 그 절 본문만 떼어 content-queue/live/<대기열 id>.md 로도 낸다 —
  채널 대기열(docs/채널대기열.md)이 요구하는 모양(머리 id·channel·target + 게시할 본문만)이라 `channel_queue.py --check`·`--clip` 이 그 파일을 그대로 쓴다.
  (10/22 대기열 검사 FAIL 2 — 세 채널을 한 파일에 담아 머리에 channel 이 없고, th-01 은 「파일 안의 절」을 가리킬 수 없었다.)
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "content-queue", "templates")
LIVE = os.path.join(ROOT, "content-queue", "live")
WORDS = ("3PL", "1위")  # 숫자 글자가 든 낱말(업종 이름 · 정의상 순위) — 데이터 주장이 아니다
PH = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def load():
    F = json.load(open(os.path.join(ROOT, "data/derived/facts.json"), encoding="utf-8"))["facts"]
    C = {c["id"]: c for c in json.load(open(os.path.join(ROOT, "data/claims.json"), encoding="utf-8"))["claims"]}
    return F, C


def digits_outside(text):
    """틀의 본문(머리 빼고)에서 자리표·주소·해시태그 밖 숫자 글자 — 있으면 손으로 적은 숫자다."""
    body = text.split("\n---\n", 1)[-1]
    body = PH.sub(" ", body)
    body = re.sub(r"https?://\S+", " ", body)
    for w in WORDS: body = body.replace(w, " ")
    return re.findall(r"\d+", body)


def render(text, F, C):
    miss = []
    def sub(m):
        k = m.group(1)
        if k.startswith("claim:"):
            cid, _, form = k[6:].rpartition(".")
            c = C.get(cid)
            v = c and c["variants"].get(c["approved"], {}).get(form)
            if v is None: miss.append(k); return m.group(0)
            return v
        if k not in F: miss.append(k); return m.group(0)
        return F[k]["v"]
    out = PH.sub(sub, text)
    head, _, body = out.partition("\n---\n")
    head = head.replace("note: AI 초안 · 틀(숫자 0)", "note: AI 초안 · 자동 생성(틀 content-queue/templates · 숫자 = data/derived/facts.json)", 1)
    return head + "\n---\n" + body, miss


def posts(out, name):
    """렌더한 틀에서 채널별 게시 파일을 뗀다 — [(파일 이름, 내용)]."""
    head, _, body = out.partition("\n---\n")
    m = re.search(r"^posts:\s*(.+)$", head, re.M)
    if not m: return []
    res = []
    for spec in m.group(1).split("|"):
        qid, ch, title = spec.split(None, 2)
        sec = re.search(rf"^## {re.escape(title.strip())}\s*\n(.*?)(?=^## |\Z)", body, re.M | re.S)
        if not sec: raise KeyError(f"틀 {name}: posts 의 절 「{title.strip()}」 이 본문에 없다")
        text = sec.group(1).strip() + "\n"
        # 절 첫 줄이 「제목: …」이면 게시 파일 머리의 title 로 옮긴다(제목 칸이 있는 채널 — 티스토리 · 뉴스레터 · 2026-10-22 B10)
        tm = re.match(r"제목:\s*(.+)\n+", text)
        head_title = f"title: {tm.group(1).strip()}\n" if tm else ""
        if tm: text = text[tm.end():]
        url = (re.findall(r"https?://\S+", text) or [""])[-1]
        res.append((f"{qid}.md", f"---\nid: {qid}\nchannel: {ch}\n{head_title}target: {url}\nstatus: 자동 생성 초안 — 틀 content-queue/templates/{name} 의 「{title.strip()}」 절(숫자 = data/derived/facts.json) · 게시 = 선장님\n---\n{text}"))
    return res


def main():
    if "--selftest" in sys.argv: return selftest()
    F, C = load()
    bad = 0
    os.makedirs(LIVE, exist_ok=True)
    for name in sorted(os.listdir(TPL)) if os.path.isdir(TPL) else []:
        if not name.endswith(".md"): continue
        src = open(os.path.join(TPL, name), encoding="utf-8").read()
        d = digits_outside(src)
        if d: print(f"✗ 틀 {name}: 손으로 적은 숫자 {d[:8]}"); bad += 1
        out, miss = render(src, F, C)
        if miss: print(f"✗ 틀 {name}: 없는 이름 {miss}"); bad += 1; continue
        for fn, text in [(name, out), *posts(out, name)]:
            dst = os.path.join(LIVE, fn)
            if "--check" in sys.argv:
                cur = open(dst, encoding="utf-8").read() if os.path.exists(dst) else None
                if cur != text: print(f"✗ live/{fn} 가 지금 데이터로 만든 판과 다르다 — python tools-build/drafts.py"); bad += 1
                else: print(f"✓ live/{fn}")
            else:
                open(dst, "w", encoding="utf-8").write(text); print(f"초안 live/{fn}")
    return 1 if bad else 0


def selftest():
    F = {"a.b": {"v": "50.5"}}
    C = {"x": {"approved": "most", "variants": {"most": {"li": "대부분"}}}}
    out, miss = render("---\nid: t\n---\n몫 {{a.b}}% · {{claim:x.li}} · {{nope}}", F, C)
    assert out.endswith("몫 50.5% · 대부분 · {{nope}}") and miss == ["nope"], (out, miss)
    assert digits_outside("---\nmade: 2026\n---\n{{a.b}}% · https://x.io/2 · 52주") == ["52"]
    P = posts("---\nid: t\nposts: li-1 linkedin LinkedIn | th-1 threads Threads\n---\n# 제목\n\n## LinkedIn\n\n본문 가\n\nhttps://x.io/\n\n## Threads\n\n짧은 판 https://x.io/\n", "t.md")
    assert [f for f, _ in P] == ["li-1.md", "th-1.md"] and "channel: linkedin\ntarget: https://x.io/\n" in P[0][1] and P[0][1].endswith("---\n본문 가\n\nhttps://x.io/\n") and "## Threads" not in P[0][1], P
    P = posts("---\nid: t\nposts: tb-1 tistory 블로그\n---\n## 블로그\n\n제목: 글 제목\n\n본문 https://x.io/\n", "t.md")
    assert "title: 글 제목\n" in P[0][1] and "제목:" not in P[0][1].split("---\n")[-1], P
    print("drafts selftest OK (4)"); return 0


if __name__ == "__main__":
    sys.exit(main())

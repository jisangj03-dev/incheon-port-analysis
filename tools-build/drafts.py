"""홍보 초안 = 틀 + 데이터(갱신 무인화 ① · docs/측심_갱신무인화_판정기준_선커밋_20261022.md).

  content-queue/templates/<id>.md 는 숫자를 적지 않는다 — {{이름}}(data/derived/facts.json) · {{claim:id.형}}(data/claims.json 의 승인 갈래 문장)만 부른다.
  이 스크립트가 채워 content-queue/live/<id>.md 로 낸다. refresh 가 원천 갱신 때마다 facts.py 다음에 다시 돌린다 — 게시 직전에도 live 판이 지면과 같은 숫자다.
  (10/22: 손으로 적은 초안 「51분」과 띠 그림 「52분」이 서로 다른 기준이었다 — 숫자를 사람이 옮겨 적지 않는다.)

  python tools-build/drafts.py            live 판을 쓴다
  python tools-build/drafts.py --check    틀에 숫자 글자가 없는가 · 이름이 다 있는가 · live 판이 지금 데이터로 다시 만든 것과 같은가(아니면 종료 1)
  python tools-build/drafts.py --selftest
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
        dst = os.path.join(LIVE, name)
        if "--check" in sys.argv:
            cur = open(dst, encoding="utf-8").read() if os.path.exists(dst) else None
            if cur != out: print(f"✗ live/{name} 가 지금 데이터로 만든 판과 다르다 — python tools-build/drafts.py"); bad += 1
            else: print(f"✓ live/{name}")
        else:
            open(dst, "w", encoding="utf-8").write(out); print(f"초안 live/{name}")
    return 1 if bad else 0


def selftest():
    F = {"a.b": {"v": "50.5"}}
    C = {"x": {"approved": "most", "variants": {"most": {"li": "대부분"}}}}
    out, miss = render("---\nid: t\n---\n몫 {{a.b}}% · {{claim:x.li}} · {{nope}}", F, C)
    assert out.endswith("몫 50.5% · 대부분 · {{nope}}") and miss == ["nope"], (out, miss)
    assert digits_outside("---\nmade: 2026\n---\n{{a.b}}% · https://x.io/2 · 52주") == ["52"]
    print("drafts selftest OK (2)"); return 0


if __name__ == "__main__":
    sys.exit(main())

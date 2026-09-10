# -*- coding: utf-8 -*-
"""표식 검사 — **내보내는 것에 안 보이는 문자와 파일 메타데이터가 남아 있는가.**

왜 있는가
---------
2026-09-10 운영자 판단. **표식 제거를 상시 자리로 만든다** — 채널 문안 · 이미지 · 문서 ·
사이트 자산, **예외를 두지 않는다.** 측심·인천 산출물도 뺀 곳이 없다.

**그리고 이것이 「AI 를 썼다」는 우리 고지와 어긋나지 않는다** — 운영자가 그렇게 정했다.
**표식은 기계용 흔적이고, 고지는 사람용 문장이다.** 둘은 별개다:
고지는 **독자에게 무엇을 밝히는가**의 문제이고(§2.2), 표식은 **파일에 무엇이 묻어 나가는가**의
문제다. 우리는 밝히는 쪽을 그대로 두고 묻는 쪽을 지운다. **감추려고 지우는 것이 아니다** —
안 보이는 문자는 우리가 넣은 적 없고, 무엇을 하는지 모르는 것을 산출물에 실어 보내지 않는다.

  python analysis/check_marks.py            # 경고. 종료 0
  python analysis/check_marks.py --strict   # 표식이 있으면 종료 1
  python analysis/check_marks.py --clean    # **사본으로** 정리하고 전후를 대조
  python analysis/check_marks.py --selftest

무엇을 보나
-----------
**A층(글자)** — 안 보이는 유니코드·양방향 제어·태그 문자·공백 동형자.
  `~/tools/watermarks-remover` 의 `inspect_text.py` / `clean_text.py` 를 부른다.
**메타데이터** — 이미지·PDF·동영상은 `audit_dir.py` 가 **연다**. 글자 도구에 안 넣는다 —
  그쪽이 형식을 갈라 이미지·컨테이너(PDF·SVG)·동영상 경로로 따로 보낸다.

닿지 않는 곳
------------
· **B층(통계적 워터마크)은 못 잡는다.** 그건 다시 쓰기(`rewrite_text.py`)의 자리이고,
  **자동으로 안 돌린다** — 부를 때만 부른다(운영자 판단 2026-09-10).
· **원본을 안 덮는다.** `--clean` 은 `.cleaned` 사본을 만들고 **전후 내용을 대조**한다.
  **대조가 안 되면 그 파일은 건너뛰고 보고한다**(경계).
· **이미지·PDF 를 글자 도구에 안 넣는다.** 넣으면 바이너리가 망가진다 —
  상류 저장소가 그 사고를 README 에 적어 뒀다. 그래서 `audit_dir.py` 로 연다.
· **C2PA 는 `c2patool` v0.27.21 로 연다**(`~/tools/c2patool` · 이 파일이 PATH 앞에 붙인다).
  **없으면 「부분 검사 N개」로 나온다** — 0 이 「없다」가 아니라 「안 봤다」인 자리다(사고 26).
  인수시험이 **C2PA 가 든 표본을 잡는지**까지 본다 — 0 건이 눈 감은 결과가 아님을 보이려고.
· **형식을 못 가린 것은 두 번 더 묻는다** — ①UTF-8 로 읽히고 NUL 이 없으면 **글자 도구**로
  (이름이 아니라 바이트로 가른다) ②`wOF2` 머리말이면 **길이 칸 둘**을 본다(압축을 안 푼다).
  **남는 것은 `.ico` 하나다** — 이 형식엔 메타데이터 칸이 없고 이 파일은 그것을 안 판정한다.
· **exiftool 이 없다.** 감사기는 PDF 에서만 그것을 쓰는데 우리 대상에 PDF 가 0 이라 지금은 안 걸린다.
  **PDF 가 생기면 그 자리는 [미확인]이 된다.**
· **바이너리는 지우는 쪽을 자동으로 안 돈다.** 걸린 것이 나오면 명령을 찍고 멈춘다 —
  0 건인 채로 만든 정리 경로는 **전후 대조를 해 본 적이 없는 경로**다(경계).
· 도구가 없는 기계에서는 **불성립**이지 통과가 아니다.
"""

import argparse
import glob
import io
import json
import os
import struct
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HQ = os.path.join(os.path.expanduser("~"), "OneDrive", "문서", "본부")
WR = os.path.join(os.path.expanduser("~"), "tools", "watermarks-remover", "service", "scripts")
INSPECT = os.path.join(WR, "inspect_text.py")
CLEAN = os.path.join(WR, "clean_text.py")

# **내보내는 것.** 독자·편집자·채널에 나가는 자리다. 예외를 두지 않는다.
TEXT_TARGETS = [
    ("발행본", os.path.join(ROOT, "reports", "*.md")),
    ("사이트 지면", os.path.join(ROOT, "*.md")),
    ("사이트 조각", os.path.join(ROOT, "_includes", "*.html")),
    ("사이트 레이아웃", os.path.join(ROOT, "_layouts", "*.html")),
    ("공개 문서", os.path.join(ROOT, "docs", "*.md")),
    ("채널 문안", os.path.join(HQ, "채널문안", "*.md")),
    ("측심 카피", os.path.join(ROOT, "..", "sounding", "app", "src", "landing-content.ts")),
]
# **글자 도구에 안 넣는다.** 있다는 것만 세고 사람에게 넘긴다.
BINARY_TARGETS = [
    ("발행본 이미지", os.path.join(ROOT, "reports", "images", "*")),
    ("사이트 자산", os.path.join(ROOT, "assets", "**", "*")),
    ("측심 공개 자산", os.path.join(ROOT, "..", "sounding", "app", "public", "**", "*")),
]
# **바이너리를 여는 자리.** `audit_dir.py` 가 확장자·매직으로 갈라
# 이미지·컨테이너(PDF·SVG)·동영상 경로로 보낸다. 글자 도구를 안 탄다.
AUDIT = os.path.join(WR, "audit_dir.py")
# **C2PA 를 여는 자리.** `c2patool` v0.27.21 (`contentauth/c2pa-rs` · 태그 고정 ·
# sha256 ff2f711b…). 없으면 감사기가 「c2patool unavailable」을 달고, 그 수를 아래가 낸다.
C2PA_DIR = os.path.join(os.path.expanduser("~"), "tools", "c2patool")
BINARY_ROOTS = [
    ("발행본 이미지", os.path.join(ROOT, "reports", "images")),
    ("사이트 자산", os.path.join(ROOT, "assets")),
    ("측심 공개 자산", os.path.join(ROOT, "..", "sounding", "app", "public")),
]
BIN_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".pdf", ".mp4", ".webm", ".ico", ".woff", ".woff2")


def have_tool():
    return os.path.exists(INSPECT) and os.path.exists(CLEAN) and os.path.exists(AUDIT)


def files(patterns):
    out = []
    for label, pat in patterns:
        for p in sorted(glob.glob(pat, recursive=True)):
            if os.path.isfile(p):
                out.append((label, p))
    return out


def run(script, args, timeout=90):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env)
        return p.returncode, p.stdout or ""
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def inspect_one(path):
    """반환 (표식 수, 원문). **못 돌린 것은 0 이 아니라 None 이다**(사고 26)."""
    code, out = run(INSPECT, [path])
    if code is None:
        return None, out
    for line in out.split("\n"):
        if line.startswith("Suspicious:"):
            try:
                return int(line.split(":", 1)[1].strip()), out
            except Exception:
                return None, out
    return None, out


def tool_env():
    """감사기에게 넘길 환경. **`c2patool` 자리를 PATH 앞에 붙인다.**

    감사기는 `shutil.which("c2patool")` 로 찾는다. 기계의 PATH 를 안 고치는 이유는
    그것이 **이 저장소 밖의 변경**이기 때문이다 — 장치가 자기 의존물의 자리를 들고 다닌다.
    **없으면 없다고 나온다**(`c2patool unavailable`) — 그것도 산출에 남는다.
    """
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if os.path.isdir(C2PA_DIR):
        env["PATH"] = C2PA_DIR + os.pathsep + env.get("PATH", "")
    return env


def woff2_meta(path):
    """WOFF2 서체가 **메타데이터를 싣고 있는가.** 반환 (열었나, 무엇이 걸렸나).

    WOFF2 는 감사기가 형식을 안 가려 92개가 통째로 [미확인]이었다. 그런데 이 형식에서
    무언가를 실을 수 있는 칸은 **머리말의 둘뿐**이다 — 확장 메타데이터(XML)와 비공개 블록.
    둘 다 머리말 48바이트 안에 길이가 적혀 있어 **압축을 안 풀고도 읽힌다**(stdlib).
    **못 읽으면 「안 열림」이지 「깨끗함」이 아니다.**
    """
    try:
        with io.open(path, "rb") as fh:
            b = fh.read(48)
        if len(b) < 44 or b[:4] != b"wOF2":
            return False, None
        _, meta_len, _, _, priv_len = struct.unpack(">IIIII", b[24:44])
        why = []
        if meta_len:
            why.append("확장 메타데이터 %d B" % meta_len)
        if priv_len:
            why.append("비공개 블록 %d B" % priv_len)
        return True, (" · ".join(why) if why else None)
    except Exception:
        return False, None


def looks_text(path):
    """**이름이 아니라 바이트로 묻는다** — UTF-8 로 읽히고 NUL 이 없으면 글자다.

    확장자로 가르면 `.woff2` 는 걸러지지만 확장자 없는 설정 파일도 같이 걸러진다.
    실제로 `_headers`·`_redirects`·`.webmanifest` 넷이 그 이유로 안 열리고 있었다.
    """
    try:
        with io.open(path, "rb") as fh:
            b = fh.read(1 << 20)
        if b"\x00" in b:
            return False
        b.decode("utf-8")
        return True
    except Exception:
        return False


def run_json(script, args, timeout=600):
    """stdout 과 stderr 를 **안 섞는다** — 섞으면 JSON 이 안 읽힌다."""
    env = tool_env()
    try:
        p = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout, env=env)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return None, "", "%s: %s" % (type(e).__name__, e)


def audit_roots():
    """이미지·PDF·동영상을 **연다.** 반환 (연 것, 못 연 것{확장자:수}, 걸린 것, 부분검사 수).

    **못 돌린 것은 「걸린 것 0」이 아니다** — 그 사실 자체를 걸린 것으로 올린다(사고 26).
    """
    opened, unrouted, hits, partial = 0, {}, [], 0
    for label, root in BINARY_ROOTS:
        if not os.path.isdir(root):
            continue
        code, out, err = run_json(AUDIT, [root, "--json"])
        if code is None or not out.strip():
            hits.append(("(%s 전체)" % label, "**못 돌렸다** — %s" % (err.strip()[:60] or "산출 없음")))
            continue
        try:
            d = json.loads(out)
        except Exception:
            hits.append(("(%s 전체)" % label, "**JSON 이 아니다** — 통과로 치지 않는다"))
            continue
        for f in d.get("files", []):
            rel = str(f.get("path", "?")).replace(chr(92), "/")
            notes = " ".join(f.get("notes") or [])
            if "unrecognized format" in notes:
                # **형식을 못 가린 것 중 「글자인 것」은 글자 도구로 보낸다.**
                # 가르는 기준은 **확장자가 아니라 내용**이다 — UTF-8 로 읽히고 NUL 이 없으면 글자다.
                # `.woff2`·`.ico` 는 여기서 걸러진다(압축 바이너리·NUL). 경계는 그대로다:
                # **바이너리를 글자 도구에 안 넣는다.** 다만 「글자냐」를 이름이 아니라 바이트로 묻는다.
                fp = os.path.join(root, os.path.relpath(rel, "").replace("/", os.sep)) \
                    if not os.path.isabs(rel) else rel
                fp = fp if os.path.exists(fp) else os.path.join(ROOT, rel)
                if looks_text(fp):
                    n, _ = inspect_one(fp)
                    if n is None:
                        hits.append((rel, "**글자로 봤는데 못 돌렸다** — 0 이 아니다"))
                    else:
                        opened += 1
                        if n:
                            hits.append((rel, "안 보이는 문자 %d건" % n))
                    continue
                ok, why = woff2_meta(fp)
                if ok:
                    opened += 1
                    if why:
                        hits.append((rel, why))
                    continue
                ext = os.path.splitext(rel)[1].lower()
                unrouted[ext] = unrouted.get(ext, 0) + 1
                continue
            opened += 1
            if "c2patool unavailable" in notes:
                partial += 1
            why = []
            if f.get("has_c2pa"):
                why.append("C2PA")
            if f.get("has_ai_metadata"):
                why.append("AI 메타데이터")
            if f.get("suspicious_total"):
                why.append("안 보이는 문자 %s건" % f["suspicious_total"])
            if why:
                hits.append((rel, " · ".join(why)))
    return opened, unrouted, hits, partial


def main(strict=False, do_clean=False):
    if not have_tool():
        print("[불성립] 표식 도구를 못 찾았다: %s" % WR)
        print("  `~/tools/watermarks-remover`(v0.7.0) 가 있어야 한다. **통과로 치지 않는다.**")
        return 2

    tf = files(TEXT_TARGETS)
    print("== 표식 검사 ==")
    print("  글자 대상 %d개 · 도구 = watermarks-remover A층(안 보이는 문자)" % len(tf))

    hits, unknown = [], []
    for label, p in tf:
        n, out = inspect_one(p)
        rel = os.path.relpath(p, ROOT).replace("\\", "/")
        if n is None:
            unknown.append((label, rel, out.strip().split("\n")[-1][:70]))
        elif n:
            hits.append((label, rel, n, p))

    if hits:
        print("\n  **표식이 있다 %d개 파일**" % len(hits))
        for label, rel, n, _ in hits:
            print("    [%s] %-52s %d건" % (label, rel[:52], n))
    if unknown:
        print("\n  **[미확인] %d개 — 못 돌렸다. 0 이 아니다**" % len(unknown))
        for label, rel, why in unknown:
            print("    [%s] %s — %s" % (label, rel, why))

    if do_clean and hits:
        print("\n  ── 정리 (**원본을 안 덮는다** · 사본을 만들고 전후를 대조한다) ──")
        for label, rel, n, p in hits:
            outp = p + ".cleaned"
            code, out = run(CLEAN, [p, "-o", outp, "--stats"])
            if code is None or not os.path.exists(outp):
                print("    **건너뜀** %s — 정리를 못 돌렸다" % rel)
                continue
            a = io.open(p, encoding="utf-8", errors="replace").read()
            b = io.open(outp, encoding="utf-8", errors="replace").read()
            import re as _re
            strip = lambda s: _re.sub(r"[​-‏⁠-⁯­﻿\U000e0000-\U000e007f]", "", s).replace(" ", " ")
            same = strip(a) == b
            after, _ = inspect_one(outp)
            print("    %-52s %d → %s · 내용 같은가 %s" % (rel[:52], n, after, "예" if same else "**아니오**"))
            if not same or after:
                print("      **건너뛴다 — 확인이 안 됐다.** 사본은 남긴다: %s" % (rel + ".cleaned"))
            else:
                os.replace(outp, p)
                print("      정리해 넣었다(전후 대조 통과).")

    # **바이너리도 연다** — 다만 글자 도구가 아니라 `audit_dir.py` 가 연다(머리말).
    opened, unrouted, hits2, partial = audit_roots()
    print()
    print("  이미지·PDF·동영상 — 연 것 %d개 · 형식을 못 가려 안 연 것 %d개"
          % (opened, sum(unrouted.values())))
    if unrouted:
        print("    안 연 것: %s" % " · ".join("%s %d" % (k or "(확장자 없음)", v)
                                              for k, v in sorted(unrouted.items())))
    if partial:
        print("    **부분 검사 %d개** — C2PA 를 다 못 봤다. 0 이 「없다」가 아니다" % partial)
        print("      `c2patool` 자리: %s (%s)"
              % (C2PA_DIR, "있다" if os.path.isdir(C2PA_DIR) else "**없다**"))
    if hits2:
        print("    **걸린 것 %d개**" % len(hits2))
        for rel, why in hits2:
            print("      %-52s %s" % (rel[:52], why))
        print("    지우려면 — **원본을 안 덮는다**. 사본을 만들고 사람이 대 본다:")
        print("      python ~/tools/watermarks-remover/service/scripts/clean_file.py <파일> -o <파일>.cleaned")

    print()
    if not hits and not unknown and not hits2:
        print("표식 0건 / 글자 %d개 · 바이너리 %d개 검사." % (len(tf), opened))
        return 0
    if unknown:
        print("**[미확인]이 있다 — 통과가 아니다.**")
        return 1 if strict else 0
    print("**표식 — 글자 %d개 파일 · 바이너리 %d개.** 글자는 `--clean` 이 사본으로 정리하고 전후를 대조한다."
          % (len(hits), len(hits2)))
    return 1 if strict else 0


def selftest():
    ok = True
    import tempfile

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-52s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 인수시험: 도구가 없으면 통과가 아니다 (사고 26) ──")
    global INSPECT
    keep = INSPECT
    INSPECT = os.path.join(keep, "없는파일.py")
    chk("도구 없으면 불성립(2)", main(), 2)
    INSPECT = keep

    if not have_tool():
        print("  (도구가 없는 기계 — 나머지는 **미실행**이지 통과가 아니다)")
        print("\n통과" if ok else "\n실패")
        return 0 if ok else 1

    print("── 인수시험: 심은 것을 찾아내는가 ──")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.txt")
        io.open(p, "w", encoding="utf-8").write("인천항​ 공컨테이너⁠ 252개월\U000e0041\n")
        n, _ = inspect_one(p)
        chk("심은 3종을 센다", n, 3)
        q = os.path.join(d, "clean.txt")
        io.open(q, "w", encoding="utf-8").write("인천항 공컨테이너 252개월\n")
        chk("깨끗한 것은 0", inspect_one(q)[0], 0)
        chk("없는 파일은 [미확인] — 0 이 아니다", inspect_one(os.path.join(d, "없다.txt"))[0], None)

    print("── 인수시험: 바이너리를 글자 도구에 안 넣는가 (경계) ──")
    bf = [p for _, p in files(BINARY_TARGETS)]
    tf = [p for _, p in files(TEXT_TARGETS)]
    overlap = set(bf) & set(tf)
    chk("글자 대상과 바이너리 대상이 안 겹친다", overlap, set())
    chk("글자 대상에 이미지가 없다",
        any(p.lower().endswith(BIN_EXT) for p in tf), False)

    print("── 인수시험: 대상이 실제로 잡히는가 (분모가 0이 아니다 · 사고 77) ──")
    chk("글자 대상이 여럿", len(tf) >= 20, True)
    print("     지금: 글자 %d · 바이너리 %d" % (len(tf), len(bf)))

    print("── 인수시험: 글자·서체·C2PA 를 이름이 아니라 바이트로 가르는가 ──")
    with tempfile.TemporaryDirectory() as d:
        t = os.path.join(d, "설정없는이름")
        io.open(t, "w", encoding="utf-8").write("/*  헤더\n")
        chk("확장자가 없어도 글자면 글자다", looks_text(t), True)
        z = os.path.join(d, "b.bin")
        io.open(z, "wb").write(b"ab\x00cd")
        chk("NUL 이 있으면 글자가 아니다", looks_text(z), False)

        # WOFF2 머리말을 손으로 짓는다 — 압축 본문 없이 길이 칸만 본다
        def _woff(meta_len, priv_len):
            p = os.path.join(d, "f%d_%d.woff2" % (meta_len, priv_len))
            head = (b"wOF2" + b"\x00" * 20
                    + struct.pack(">IIIII", 0, meta_len, meta_len, 0, priv_len)
                    + b"\x00" * 4)
            io.open(p, "wb").write(head)
            return p
        chk("서체에 메타데이터가 없으면 깨끗", woff2_meta(_woff(0, 0)), (True, None))
        chk("확장 메타데이터가 있으면 걸린다", woff2_meta(_woff(120, 0))[1] is not None, True)
        chk("비공개 블록이 있으면 걸린다", woff2_meta(_woff(0, 64))[1] is not None, True)
        chk("서체가 아니면 안 열었다고 한다", woff2_meta(z), (False, None))

    # **양성 대조** — 0 건이 「도구가 눈을 감아서」가 아님을 보인다(사고 26)
    sample = os.path.join(C2PA_DIR, "sample", "C.jpg")
    if os.path.exists(sample):
        code, out, _ = run_json(os.path.join(WR, "inspect_image.py"), [sample])
        chk("C2PA 가 든 표본을 잡는다", "C2PA: True" in out and "c2patool" in out, True)
    else:
        print("  (표본 %s 이 없다 — **미실행**이지 통과가 아니다)" % sample)

    print("── 인수시험: 바이너리를 실제로 여는가 (분모가 0이 아니다 · 사고 77) ──")
    op2, unr2, h2, pt2 = audit_roots()
    chk("바이너리를 연다 — 0 이면 「없다」가 아니라 「못 봤다」", op2 > 0, True)
    chk("못 돌린 것이 「걸린 것 0」으로 안 숨는다",
        all("못 돌렸다" not in w and "JSON 이 아니다" not in w for _, w in h2), True)
    chk("C2PA 를 여는 도구가 자리에 있다", os.path.isdir(C2PA_DIR), True)
    chk("부분 검사가 0 이다 — 0 이 아니면 C2PA 를 그만큼 못 본 것이다", pt2, 0)
    print("     지금: 연 것 %d · 안 연 것 %d · 부분검사 %d · 걸린 것 %d"
          % (op2, sum(unr2.values()), pt2, len(h2)))

    print("\n통과" if ok else "\n실패")
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="내보내는 것의 표식 검사")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--clean", action="store_true", help="사본으로 정리하고 전후 대조")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    sys.exit(selftest() if a.selftest else main(a.strict, a.clean))

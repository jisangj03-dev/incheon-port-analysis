# -*- coding: utf-8 -*-
"""예약 수집기(확장 기준 14) — tools-build/collect.json 의 원천을 달마다 받아 data/collected/ 에 쌓는다.

GitHub Actions 에서만 돈다(키 = 저장소 시크릿 DATA_GO_KR_KEY · 사고 120). 이 세션·하위 에이전트는 키를 안 다룬다.
키는 화면·파일에 안 찍는다: 응답 본문에서 키(원문·URL 인코딩)를 지우고, 끝에 산출물 전체를 다시 훑는다(guard).
받기만 한다 — 판정·지수 계산은 각 선커밋 문서와 그 코드가 한다.

  python tools-build/collect.py            # 수집 → data/collected/
  python tools-build/collect.py --guard    # 산출물에 키가 있으면 종료 1(값은 안 찍는다)
  python tools-build/collect.py --selftest
"""
import csv
import datetime as dt
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "tools-build" / "collect.json"
OUT = ROOT / "data" / "collected"
SUMMARY = os.environ.get("GITHUB_STEP_SUMMARY")


def say(line=""):
    print(line)
    if SUMMARY:
        with open(SUMMARY, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def months_back(today, lag, n):
    y, m = today.year, today.month
    out = []
    for i in range(lag, lag + n):
        yy, mm = y, m - i
        while mm <= 0:
            yy, mm = yy - 1, mm + 12
        out.append(f"{yy}{mm:02d}")
    return sorted(out)


def secrets(key):
    return [s for s in {key, urllib.parse.quote(key, safe=""), urllib.parse.quote_plus(key)} if s]


def scrub(text, key):
    for s in secrets(key):
        text = text.replace(s, "***")
    return text


def parse(body):
    """data.go.kr 응답(XML·JSON) → (결과코드, 메시지, 행 목록). 태그 이름 기준(위치 인덱스 금지 · 사고 1)."""
    b = body.strip()
    if b.startswith("{"):
        try:
            d = json.loads(b)
        except ValueError:
            return "?", "JSON 해석 실패", []
        head = d.get("response", {}).get("header", {}) or d.get("header", {})
        items = (d.get("response", {}).get("body", {}) or {}).get("items") or {}
        items = items.get("item", items) if isinstance(items, dict) else items
        if isinstance(items, dict):
            items = [items]
        return str(head.get("resultCode", "?")), str(head.get("resultMsg", "")), [
            {k: ("" if v is None else str(v)) for k, v in it.items()} for it in (items or []) if isinstance(it, dict)]
    rc = (re.findall(r"<resultCode>([^<]*)", b) or re.findall(r"<returnReasonCode>([^<]*)", b) or ["?"])[0]
    msg = (re.findall(r"<resultMsg>([^<]*)", b) or re.findall(r"<returnAuthMsg>([^<]*)", b) or re.findall(r"<errMsg>([^<]*)", b) or [""])[0]
    rows = []
    for it in re.findall(r"<item>(.*?)</item>", b, re.S):
        rows.append({t: html.unescape(v.strip()) for t, v in re.findall(r"<(\w+)>([^<]*)</\1>", it)})
    return rc.strip(), msg.strip(), rows


def fetch(url, params, key):
    q = url + "?" + urllib.parse.urlencode(params)
    q += "&" + urllib.parse.urlencode({"serviceKey": key})  # Decoding 판 키 → 한 번만 인코딩
    r = subprocess.run(["curl", "-s", "-m", "90", "--retry", "3", "--retry-all-errors", "-w", "\n%{http_code}", q],
                       capture_output=True, text=True)
    body, _, code = r.stdout.rpartition("\n")
    return code.strip() or "000", scrub(body, key)


def spec_hint(portal):
    """결과코드가 00 이 아니면 포털 명세의 요청 변수 절을 요약에 찍는다(키 없이 · 공개 페이지)."""
    r = subprocess.run(["curl", "-sL", "-m", "60", f"https://www.data.go.kr/data/{portal}/openapi.do"], capture_output=True, text=True)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.stdout, flags=re.S)
    t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
    i = t.find("요청변수")
    return t[i:i + 1500] if i >= 0 else f"(명세 절을 못 찾음 · 페이지 {len(r.stdout)}B)"


def run():
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        say("[멈춤] 환경 변수 없음: DATA_GO_KR_KEY")
        return 2
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    kst = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)
    window = months_back(kst.date(), cfg.get("lag_months", 1), cfg.get("window_months", 3))
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = OUT / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    say(f"## 예약 수집 {kst:%Y-%m-%d %H:%M} KST · 창 {window[0]}~{window[-1]}")
    say("| 원천 | 포털 | 달 | 묶음 | HTTP | 결과 | 행 |")
    say("|---|---|---|---|---|---|---|")
    ok_any, hints = False, {}
    for s in cfg["sources"]:
        each = s.get("each") or {"": [""]}
        (ek, evs), = each.items()
        rows_by_key, meta = {}, manifest.setdefault(s["id"], {})
        for ym in window:
            for ev in evs:
                p = dict(s.get("params", {}))
                for mp in s.get("month_params", []):
                    p[mp] = ym
                if ek:
                    p[ek] = ev
                code, body = fetch(s["url"], p, key)
                rc, msg, rows = parse(body)
                kw = s.get("keep_if_any_field_contains")
                if kw:
                    rows = [r for r in rows if any(kw in v for v in r.values())]
                tag = f"{ym}{'·' + ev if ev else ''}"
                meta[tag] = {"http": code, "resultCode": rc, "resultMsg": msg[:120], "rows": len(rows),
                             "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(), "fetched_kst": f"{kst:%Y-%m-%d %H:%M}"}
                say(f"| {s['id']} | {s['portal']} | {ym} | {ev or '—'} | {code} | {rc} {msg[:40]} | {len(rows)} |")
                if rc in ("00", "0", "000", "INFO-000") and code == "200":
                    ok_any = True
                    rows_by_key[(ym, ev)] = rows
                elif s["portal"] not in hints:
                    hints[s["portal"]] = body[:400]
        if rows_by_key:
            write_rows(s, ek, rows_by_key)
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for portal, body in hints.items():
        say(f"\n### {portal} — 00 이 아닌 응답(키 지움 · 앞 400자)\n```\n{body}\n```")
        say(f"포털 명세 요청 변수 절(앞 1500자):\n```\n{spec_hint(portal)}\n```")
    return 0 if ok_any else 1


def write_rows(s, ek, rows_by_key):
    """요청한 달(과 묶음 값)을 맨 앞 열에 박고, 창 안의 달은 새 응답으로 갈아 끼운다(원천의 정정 반영 · 창 밖은 그대로)."""
    path = OUT / f"{s['id']}.csv"
    old = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            old = [r for r in csv.DictReader(f) if (r.get("reqYm"), r.get(ek, "") if ek else "") not in rows_by_key]
    new = [{"reqYm": ym, **({ek: ev} if ek else {}), **r} for (ym, ev), rs in rows_by_key.items() for r in rs]
    allrows = old + new
    cols = ["reqYm"] + ([ek] if ek else [])
    for r in allrows:
        cols += [c for c in r if c not in cols]
    allrows.sort(key=lambda r: (r.get("reqYm", ""), r.get(ek, "") if ek else ""))
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(allrows)


def guard():
    key = os.environ.get("DATA_GO_KR_KEY", "").strip()
    if not key:
        print("[guard] 키 없음 — 검사 생략 아님: 실패로 친다")
        return 1
    bad = []
    files = list(OUT.rglob("*")) + ([Path(SUMMARY)] if SUMMARY else [])
    for p in files:
        if p.is_file():
            t = p.read_text(encoding="utf-8", errors="ignore")
            if any(s in t for s in secrets(key)):
                bad.append(str(p))
    print(f"[guard] 키 흔적 {len(bad)}건 (파일 {sum(p.is_file() for p in files)}개 검사)" + (f": {bad}" if bad else ""))
    return 1 if bad else 0


def selftest():
    assert months_back(dt.date(2026, 1, 16), 1, 3) == ["202510", "202511", "202512"]
    k = "ab+c/d=="
    assert scrub(f"x{k}y{urllib.parse.quote(k, safe='')}z", k) == "x***y***z"
    rc, msg, rows = parse("<response><header><resultCode>00</resultCode><resultMsg>OK</resultMsg></header><body><items>"
                          "<item><a>1</a><b>인천&amp;</b></item><item><a>2</a></item></items></body></response>")
    assert (rc, msg, len(rows), rows[0]["b"]) == ("00", "OK", 2, "인천&"), (rc, msg, rows)
    rc, _, rows = parse('{"response":{"header":{"resultCode":"00","resultMsg":"OK"},"body":{"items":{"item":{"x":3}}}}}')
    assert (rc, rows) == ("00", [{"x": "3"}])
    rc, msg, _ = parse("<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>30</returnReasonCode><returnAuthMsg>SERVICE_KEY_IS_NOT_REGISTERED_ERROR</returnAuthMsg></cmmMsgHeader></OpenAPI_ServiceResponse>")
    assert (rc, msg) == ("30", "SERVICE_KEY_IS_NOT_REGISTERED_ERROR")
    print("collect selftest OK (5)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--guard" in sys.argv:
        sys.exit(guard())
    sys.exit(run())

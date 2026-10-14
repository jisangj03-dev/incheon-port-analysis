# -*- coding: utf-8 -*-
"""셀러 물류 도구 검사 — 계산기·창고 배치도가 선커밋 기준을 넘는지 (2026-10-09).

기준 = docs/물류사업_갈래_판정기준_선커밋_20261009.md
  C1 같은 답   : assets/js/cost-check.js 를 node 로 돌려, 엑셀 「3PL 견적 비교표」 가상 샘플과 같은 값이 나오는가
  C2 외부 호출 0: 계산 JS·도구 지면에 fetch·XHR·sendBeacon·외부 <script src>·외부 stylesheet 가 없는가
  C3 금액 상수 0: 계산 JS 의 SAMPLE(가상값) 밖에 세 자리 이상 숫자가 없는가
  M1 합계 일치 : 창고 배치도 데이터(_data/warehouse_gu.json)의 합 = analysis/warehouse_by_gu.csv 의 합
  M2 원본 행 0 : 배치도 데이터·지면에 주소·상호·좌표 열이 없는가

    python analysis/check_cost_tool.py            # 검사
    python analysis/check_cost_tool.py --selftest # 검사기 자신이 틀린 입력을 잡는지

node 가 없으면 C1 은 「모름」이다 — 통과로 세지 않는다(사고 26).
"""
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, "assets", "js", "cost-check.js")
PAGES = [os.path.join(ROOT, "tools", "logistics-cost.html"), os.path.join(ROOT, "tools", "warehouse-map.html")]
WH_JSON = os.path.join(ROOT, "_data", "warehouse_gu.json")
WH_GU = os.path.join(ROOT, "analysis", "warehouse_by_gu.csv")
WH_DONG = os.path.join(ROOT, "analysis", "warehouse_by_dong.csv")

# 엑셀 가상 샘플(jota products/3PL견적비교표 README §검증 · LibreOffice 재계산 2026-10-08)의 답.
EXPECT = {"monthly": [4044000, 2805000, 2960000], "perUnit": [4044, 2805, 2960], "unknown": [0, 3, 0], "diff": [None, -1239, -1084]}

NODE_PROG = r"""
const C = require(process.argv[1]);
const S = C.SAMPLE;
const st = { ship: S.ship, ret: S.ret, blocks: S.blocks.map(b => b.map(r => [r[0], r[1], r[2]])) };
const r = C.compute(st);
console.log(JSON.stringify({
  monthly: r.map(x => x.monthly), perUnit: r.map(x => x.perUnit), unknown: r.map(x => x.unknown.length),
  diff: r.map(x => x.diff === null ? null : Math.round(x.diff)), flip: r.map(x => x.flip),
  items: C.ITEMS.length, hidden: C.HIDDEN.map(h => h.key)
}));
"""


def c1(js=JS):
    node = shutil.which("node")
    if not node:
        return "모름", "node 가 없다 — 계산을 돌려 보지 못했다"
    p = subprocess.run([node, "-e", NODE_PROG, js], capture_output=True, text=True, encoding="utf-8")
    if p.returncode:
        return "실패", p.stderr.strip()[:300]
    got = json.loads(p.stdout)
    bad = [f"{k}: {got[k]} ≠ {v}" for k, v in EXPECT.items() if got[k] != v]
    if got["items"] != 10:
        bad.append(f"칸 수 {got['items']} ≠ 10")
    if got["hidden"] != ["power", "legal", "oneoff", "fuel"]:
        bad.append(f"숨은 비용 {got['hidden']}")
    flip = got["flip"][1]
    if not flip or round(flip["perUnit"]) != 155 or flip["against"] != "견적 B":
        bad.append(f"뒤집히는 선 {flip} ≠ 견적 B 대비 건당 155원(블로그 사례)")
    return ("실패", "; ".join(bad)) if bad else ("통과", "가상 샘플 월 4,044,000/2,805,000/2,960,000 · 모름 0/3/0 · 뒤집히는 선 155원")


NET = re.compile(r"\bfetch\s*\(|XMLHttpRequest|sendBeacon|new\s+WebSocket|navigator\.sendBeacon")
EXT_TAG = re.compile(r"<(?:script|link|img|iframe)\b[^>]*(?:src|href)\s*=\s*[\"']https?://", re.I)


def c2(paths=None):
    bad = []
    for p in [JS] + (paths or PAGES):
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding="utf-8").read()
        s_code = re.sub(r"<!--.*?-->", "", s, flags=re.S)
        for m in NET.finditer(s_code):
            bad.append(f"{os.path.basename(p)}: 네트워크 호출 '{m.group(0)}'")
        for m in EXT_TAG.finditer(s_code):
            bad.append(f"{os.path.basename(p)}: 외부 자원 '{m.group(0)[:60]}'")
        if p.endswith(".html") and "no_cdn: true" not in s.split("---", 2)[1 if s.startswith("---") else 0]:
            bad.append(f"{os.path.basename(p)}: front matter 에 no_cdn: true 가 없다(글꼴 CDN 이 붙는다)")
    return ("실패", "; ".join(bad)) if bad else ("통과", "fetch·XHR·외부 script/link/img 0")


def c3(js=JS):
    s = io.open(js, encoding="utf-8").read()
    if "SAMPLE:BEGIN" not in s or "SAMPLE:END" not in s:
        return "실패", "SAMPLE 표지가 없다 — 가상값 경계를 못 찾는다"
    body = re.sub(r"/\* SAMPLE:BEGIN.*?SAMPLE:END \*/", "", s, flags=re.S)
    body = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)         # 주석
    body = re.sub(r"\"(?:\\.|[^\"\\])*\"", "\"\"", body)                # 문자열
    hits = re.findall(r"(?<![\w.])\d{3,}(?![\w])", body)
    return ("실패", f"가상값 밖의 세 자리 이상 숫자 {hits}") if hits else ("통과", "SAMPLE 밖 금액 상수 0")


def read_gu(path=WH_GU):
    with io.open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def m1(js_path=WH_JSON, gu_path=WH_GU):
    if not os.path.exists(js_path):
        return "모름", "배치도 데이터가 없다"
    d = json.load(io.open(js_path, encoding="utf-8"))
    rows = read_gu(gu_path)
    want_n = sum(int(r["개소"]) for r in rows)
    want_a = sum(int(r["면적합_m2"]) for r in rows)
    got_n = sum(g["count"] for g in d["gu"])
    got_a = sum(g["area"] for g in d["gu"])
    bad = []
    if (got_n, got_a) != (want_n, want_a):
        bad.append(f"구 합 {got_n}곳·{got_a}m² ≠ CSV {want_n}곳·{want_a}m²")
    if d.get("total", {}).get("count") != want_n or d.get("total", {}).get("area") != want_a:
        bad.append(f"total {d.get('total')} ≠ {want_n}·{want_a}")
    by = {r["이름"]: r for r in rows}
    for g in d["gu"]:
        r = by.get(g["name"])
        if not r or int(r["개소"]) != g["count"] or int(r["면적합_m2"]) != g["area"] or int(r["냉동냉장면적_m2"]) != g["cold"]:
            bad.append(f"{g['name']} 값이 CSV 와 다르다")
    if os.path.exists(WH_DONG):
        with io.open(WH_DONG, encoding="utf-8") as f:
            dong = {(r["구"], r["이름"]): r for r in csv.DictReader(f)}
        for x in d.get("dong", []):
            r = dong.get((x["gu"], x["name"]))
            if not r or int(r["개소"]) != x["count"] or int(r["면적합_m2"]) != x["area"]:
                bad.append(f"{x['gu']} {x['name']} 값이 동 CSV 와 다르다")
    return ("실패", "; ".join(bad)) if bad else ("통과", f"{want_n}곳 · {want_a:,}m² · 구 {len(d['gu'])}곳 일치")


ROW_KEYS = re.compile(r"주소|상호|소재지|업체|대표|전화|위도|경도|lat|lng|lon|addr", re.I)


def m2(js_path=WH_JSON):
    if not os.path.exists(js_path):
        return "모름", "배치도 데이터가 없다"
    keys = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                keys.add(k)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.load(io.open(js_path, encoding="utf-8")))
    bad = sorted(k for k in keys if ROW_KEYS.search(k))
    return ("실패", f"원본 행으로 보이는 열 {bad}") if bad else ("통과", "주소·상호·좌표 열 0")


def run():
    rows = [("C1 같은 답", c1()), ("C2 외부 호출 0", c2()), ("C3 금액 상수 0", c3()),
            ("M1 배치도 합계", m1()), ("M2 원본 행 0", m2())]
    worst = 0
    for name, (v, why) in rows:
        print(f"  {v:<4}  {name:<14} {why}")
        worst = max(worst, {"통과": 0, "모름": 2, "실패": 1}[v])
    return worst


def selftest():
    fails = []
    d = tempfile.mkdtemp()
    try:
        # C1: 계산식을 망가뜨린 사본은 실패해야 한다
        bad_js = os.path.join(d, "bad.js")
        s = io.open(JS, encoding="utf-8").read().replace("return p * q;", "return p * q + 1;")
        io.open(bad_js, "w", encoding="utf-8").write(s)
        if shutil.which("node") and c1(bad_js)[0] != "실패":
            fails.append("C1 이 망가진 계산식을 못 잡았다")
        # C2: fetch 가 든 지면은 실패해야 한다
        page = os.path.join(d, "p.html")
        io.open(page, "w", encoding="utf-8").write("---\nno_cdn: true\n---\n<script>fetch('/x')</script>")
        if c2([page])[0] != "실패":
            fails.append("C2 가 fetch 를 못 잡았다")
        io.open(page, "w", encoding="utf-8").write("---\nno_cdn: true\n---\n<script src=\"https://cdn.example/x.js\"></script>")
        if c2([page])[0] != "실패":
            fails.append("C2 가 외부 script 를 못 잡았다")
        # C3: SAMPLE 밖 금액은 실패해야 한다
        js3 = os.path.join(d, "c3.js")
        io.open(js3, "w", encoding="utf-8").write("/* SAMPLE:BEGIN */ var S=[2800]; /* SAMPLE:END */ var fee = 2500;")
        if c3(js3)[0] != "실패":
            fails.append("C3 가 SAMPLE 밖 2500 을 못 잡았다")
        io.open(js3, "w", encoding="utf-8").write("/* SAMPLE:BEGIN */ var S=[2800]; /* SAMPLE:END */ var a = \"1,000건\"; // 300\n")
        if c3(js3)[0] != "통과":
            fails.append("C3 가 문자열·주석 안 숫자를 잘못 셌다")
        # M1·M2: 합이 다르거나 주소 열이 있으면 실패해야 한다
        gu = os.path.join(d, "gu.csv")
        io.open(gu, "w", encoding="utf-8").write("코드,이름,개소,면적합_m2,냉동냉장면적_m2\n1,가구,2,10,0\n")
        wj = os.path.join(d, "w.json")
        json.dump({"total": {"count": 3, "area": 10}, "gu": [{"name": "가구", "count": 3, "area": 10, "cold": 0}]}, io.open(wj, "w", encoding="utf-8"))
        if m1(wj, gu)[0] != "실패":
            fails.append("M1 이 합 불일치를 못 잡았다")
        json.dump({"gu": [{"name": "가구", "주소": "x"}]}, io.open(wj, "w", encoding="utf-8"))
        if m2(wj)[0] != "실패":
            fails.append("M2 가 주소 열을 못 잡았다")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    for f in fails:
        print("  실패 ", f)
    print("selftest:", "통과" if not fails else f"실패 {len(fails)}건")
    return 1 if fails else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(run())

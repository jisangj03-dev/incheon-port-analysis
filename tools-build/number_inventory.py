"""지면 숫자 전수 분류 — 흔들어 보기(2026-10-21 선장님 질문 「지면마다 최신화해야 할 숫자가 많은데 어떻게 할 건가」).

숫자가 「어느 파일에 들어 있나」로는 못 가른다(원자료가 커서 모든 숫자가 어딘가 있다). 그래서 파일 묶음마다 숫자를
일부러 흔든(자리마다 다른 배율) 사본으로 다시 빌드하고, 공개 지면 본문에서 **실제로 바뀐 숫자**를 그 묶음의 것으로 센다.
  ① 자동   = refresh 워크플로가 다시 받아 쓰는 파일(refresh.py STEPS·DERIVE 산출 · data/collected)
  ② 기록   = 갱신하지 않는 게 맞는 파일(고정 기간 자료 · 모형·거리 상수 · 노트 날짜)
  ③ 사람 손 = 수동 실행·수동 스냅샷 파일 / 어느 묶음을 흔들어도 안 바뀐 숫자(틀에 박힘)
작업 사본에서만 흔든다(저장소 파일은 건드리지 않는다).
  python tools-build/number_inventory.py <작업 사본 경로> <출력 json>     (작업 사본 = git worktree · node_modules 링크)
  python tools-build/number_inventory.py --selftest
"""
import csv, difflib, hashlib, io, json, os, re, shutil, subprocess, sys

AUTO = ["analysis/terminal_monthly_long.csv", "data/forecast/incheon_container_teu.csv",
        "data/derived/home_flows.json", "data/derived/air_cargo.json", "data/derived/vessel_replay.json", "data/derived/supply_hs85.json",
        "data/derived/chokepoints.json", "data/derived/home_axes.json", "data/derived/trade_race.json", "data/derived/import_cost.json", "data/derived/freshness.json", "data/collected"]
RECORD = {"data/sim/beer-game.json": "모형 상수(Sterman 1989)", "data/derived/choke_detour.json": "해상 우회 거리(경로망 · 지리)",
          "data/derived/ship_density.json": "선박 밀도 2015-01~2021-02(고정 기간)", "data/forecast/lab.json": "수요예측 실험실 방법(선커밋)",
          "data/hs2_short.json": "HS 이름", "data/questions.json": "질문 목록", "data/rooms.json": "노트 날짜·단계"}
MANUAL = {"data/derived/isochrones.json": "OSM 도로망 등시선(data-v3 osm 수동)", "data/derived/navi_check.json": "카카오 내비 대조(navi-check 수동)",
          "data/derived/reach_slots.json": "시간대 배율(내비 대조에서 수동 파생)", "data/derived/tariff_codes.json": "관세율표(tariff-probe 수동)",
          "data/derived/places.json": "OSM 자리표(places-fetch 수동)", "data/derived/ops_stats.json": "운영 통계(ops_stats.py 수동)",
          "data/sources.json": "출처 대장(사람이 적음)", "data/profile.json": "소개(사람이 적음)"}

YEARISH = re.compile(r"^(19|20)\d{2}(\d{2})?(\d{2})?$")


def factor(key):
    h = int(hashlib.md5(key.encode()).hexdigest()[:6], 16)
    return 1.13 + (h % 37) / 100  # 1.13~1.49 — 자리마다 달라 비율로 계산한 값도 바뀐다


def shake_num(v, key):
    if isinstance(v, bool) or v == 0: return v
    if isinstance(v, int):
        if YEARISH.match(str(abs(v))): return v
        return int(round(v * factor(key))) or v + 1
    if isinstance(v, float):
        s = repr(v); d = len(s.split(".")[1]) if "." in s else 0
        return round(v * factor(key), max(d, 1))
    return v


def shake_json(o, path=""):
    if isinstance(o, dict): return {k: shake_json(v, f"{path}.{k}") for k, v in o.items()}
    if isinstance(o, list): return [shake_json(v, f"{path}[{i}]") for i, v in enumerate(o)]
    if isinstance(o, (int, float)): return shake_num(o, path)
    if isinstance(o, str) and re.fullmatch(r"-?\d+(\.\d+)?", o) and not YEARISH.match(o.lstrip("-")):
        return str(shake_num(float(o) if "." in o else int(o), path))
    return o


def shake_csv(text, name):
    r = list(csv.reader(io.StringIO(text)))
    for i, row in enumerate(r[1:], 1):
        for j, c in enumerate(row):
            t = c.replace(",", "")
            if re.fullmatch(r"-?\d+(\.\d+)?", t) and not YEARISH.match(t.lstrip("-")):
                v = float(t) if "." in t else int(t)
                row[j] = str(shake_num(v, f"{name}:{i}:{j}"))
    b = io.StringIO(); csv.writer(b, lineterminator="\n").writerows(r); return b.getvalue()


def files_of(root, rel):
    p = os.path.join(root, rel)
    if os.path.isdir(p):
        return [os.path.join(dp, f) for dp, _, fs in os.walk(p) for f in fs if f.endswith((".json", ".csv")) and os.path.getsize(os.path.join(dp, f)) < 40e6]
    return [p] if os.path.exists(p) else []


def shake_group(root, rels):
    for rel in rels:
        for f in files_of(root, rel):
            t = open(f, encoding="utf-8-sig").read()
            try:
                out = json.dumps(shake_json(json.loads(t)), ensure_ascii=False) if f.endswith(".json") else shake_csv(t, f)
            except Exception:
                continue
            open(f, "w", encoding="utf-8").write(out)


NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?(?!\d)|\d+(?:\.\d+)?")


def tokens(html):
    i = re.search(r"data-(sim|content)=", html)
    if i:
        s = html.rfind("<", 0, i.start()); e = html.find("<footer", i.start()); html = html[s:e if e > 0 else None]
    for tag in ("script", "style", "head"): html = re.sub(rf"<{tag}[\s\S]*?</{tag}>", " ", html)
    html = re.sub(r"<(\w+)\b[^>]*\bdata-furniture\b[^>]*>[\s\S]*?</\1>", " ", html)
    t = re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ")
    t = re.sub(r"\b\d{4}-\d{2}(-\d{2})?\b", " ", t)
    return [m.group(0) for m in NUM.finditer(t) if not YEARISH.match(m.group(0))]


def pages(dist):
    sm = open(os.path.join(dist, "sitemap.xml"), encoding="utf-8").read()
    return [p for p in re.findall(r"<loc>https://[^<]*?/incheon-port-analysis([^<]*)</loc>", sm)]


def read_page(dist, p):
    f = os.path.join(dist, p.lstrip("/") + ("index.html" if p.endswith("/") else ""))
    return tokens(open(f, encoding="utf-8").read()) if os.path.exists(f) else []


def build(root):
    env = dict(os.environ, SOUNDING_LAB="1")
    r = subprocess.run("npm run site:build", shell=True, cwd=root, env=env, capture_output=True, text=True)
    if r.returncode: raise SystemExit("빌드 실패:\n" + r.stdout[-1500:] + r.stderr[-1500:])


def changed(base, now):
    """순서 정렬(difflib)로 맞춘 뒤, 짝이 맞지 않는 base 자리 = 바뀐 숫자. 숫자 개수가 달라져도 자리가 어긋나지 않는다."""
    sm = difflib.SequenceMatcher(a=base, b=now, autojunk=False)
    same = set()
    for blk in sm.get_matching_blocks():
        same.update(range(blk.a, blk.a + blk.size))
    return [i for i in range(len(base)) if i not in same]


def main(root, out):
    dist = os.path.join(root, "astro/dist")
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=root, check=True)
    build(root); P = pages(dist); base = {p: read_page(dist, p) for p in P}
    kind = {p: [None] * len(base[p]) for p in P}
    for label, group in (("①", AUTO), ("②", list(RECORD)), ("③", list(MANUAL))):
        subprocess.run(["git", "checkout", "-q", "--", "."], cwd=root, check=True)
        shake_group(root, group); build(root)
        shaken = {p: read_page(dist, p) for p in P}
        json.dump(shaken, open(out + f".{label}.json", "w", encoding="utf-8"), ensure_ascii=False)
        for p in P:
            for i in changed(base[p], shaken[p]):
                if kind[p][i] is None: kind[p][i] = label
        print(label, "done", flush=True)
    subprocess.run(["git", "checkout", "-q", "--", "."], cwd=root, check=True)
    res = []
    for p in P:
        rows = [{"n": n, "kind": k or "③틀"} for n, k in zip(base[p], kind[p])]
        res.append({"page": p, "total": len(rows), **{k: sum(r["kind"] == k for r in rows) for k in ("①", "②", "③", "③틀")}, "rows": rows})
    json.dump({"pages": res, "groups": {"①": AUTO, "②": RECORD, "③": MANUAL}}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def selftest():
    a = shake_json({"y": 2025, "v": 100, "p": 50.5, "ym": "202609", "s": "12"})
    assert a["y"] == 2025 and a["ym"] == "202609" and a["v"] != 100 and a["p"] != 50.5 and a["s"] != "12"
    assert tokens('<main data-content="x"><p>2026-09 50.5% · 1,165.0 · 2025</p></main><footer>9</footer>') == ["50.5", "1,165.0"]
    assert changed(["1", "2"], ["1", "3"]) == [1]
    assert changed(["5", "3.2", "9"], ["5", "7", "4.1", "9"]) == [1]
    print("selftest 4/4 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main(sys.argv[1], sys.argv[2]))

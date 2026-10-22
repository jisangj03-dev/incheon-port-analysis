"""달마다 다시 계산하는 바탕 층(2026-10-21 · docs/숫자전수_20261021.md 「③을 0으로」) — refresh 가 매일 부르고, 때가 된 층만 돈다.
종전에는 사람이 워크플로를 손으로 돌려야 바뀌던 파일(③)이다. 이제 원천 확인일(data/derived/freshness.json)이 주기보다 오래되면 다시 받는다.

  iso     — 도달 등시선: OSM 대한민국 추출 → v3/osm_iso.py · 카카오 내비 대조 navi_check.py(시크릿 KAKAO_REST_KEY · 25일 상한 · 60회) · 시간대 배율 reach_slots.py
  tariff  — 관세율표(공공데이터포털 파일 15051179): tariff_fetch.py --build — 새 판이 아니면 결과가 같아 커밋이 생기지 않는다(refresh --changed)

종료 코드: 0 = 돌았다(원천 확인) · 75 = 때가 아니라 건너뜀(확인일을 바꾸지 않는다 · refresh.py 가 「안 돌림」으로 센다) · 그 밖 = 실패(지난 파일 유지).
  python tools-build/periodic.py iso|tariff [--force]
  python tools-build/periodic.py --due iso    # 때가 됐으면 0 · 아니면 1(refresh.yml 이 무거운 의존을 깔지 정한다)
  python tools-build/periodic.py --selftest
"""
import datetime, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = 75
# 층 → (freshness 원천 id, 주기 일, 차례로 돌릴 명령[(명령, 작업 폴더)])
LAYERS = {
    "iso": ("osm-reach", 28, [([sys.executable, "osm_iso.py"], "tools-build/v3"),
                              ([sys.executable, "tools-build/navi_check.py", "--force"], "."),
                              ([sys.executable, "tools-build/reach_slots.py"], ".")]),
    "tariff": ("kcs-tariff", 28, [([sys.executable, "tools-build/tariff_fetch.py", "--build"], ".")]),
}


def last_checked(sid):
    p = os.path.join(ROOT, "data/derived/freshness.json")
    if not os.path.exists(p): return None
    return ((json.load(open(p, encoding="utf-8")).get("sources") or {}).get(sid) or {}).get("checked")


def due(sid, days, today, checked=None):
    c = checked if checked is not None else last_checked(sid)
    if not c: return True
    return (today - datetime.date.fromisoformat(c[:10])).days >= days


def main(layer, force):
    sid, days, cmds = LAYERS[layer]
    today = datetime.date.today()
    if not force and not due(sid, days, today):
        print(f"{layer}: 마지막 확인 {last_checked(sid)} — {days}일이 안 지났다 · 건너뜀"); return SKIP
    for cmd, cwd in cmds:
        r = subprocess.run(cmd, cwd=os.path.join(ROOT, cwd))
        if r.returncode != 0:
            print(f"{layer}: {' '.join(cmd[1:])} 실패 rc={r.returncode} — 지난 파일 유지"); return r.returncode
    print(f"{layer}: 다시 계산함({today})"); return 0


def selftest():
    t = datetime.date(2026, 11, 20)
    assert due("x", 28, t, "") is True
    assert due("x", 28, t, "2026-10-20") is True and due("x", 28, t, "2026-10-25") is False
    assert set(LAYERS) == {"iso", "tariff"}
    print("selftest 3/3 ok"); return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv: sys.exit(selftest())
    if "--due" in sys.argv:
        sid, days, _ = LAYERS[sys.argv[sys.argv.index("--due") + 1]]
        sys.exit(0 if due(sid, days, datetime.date.today()) else 1)
    sys.exit(main(sys.argv[1], "--force" in sys.argv))

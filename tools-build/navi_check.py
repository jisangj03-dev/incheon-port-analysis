"""등시선 내비 대조 — 카카오모빌리티 미래 운행 정보 길찾기와 우리 모델(OSM 자유 흐름) 도착 분을 견준다(2026-10-15 · 선커밋 = 공개전개편 판정기준 「① 내비 대조」).

약관(호출 전 판단): 카카오 운영정책은 길찾기 결과의 저장·캐싱을 막는 쪽이다 → **경로·OD별 시간·거리는 파일에도 로그에도 남기지 않는다.**
한 실행 안에서 메모리로만 견주고, 오차 통계(표본 수 · 중앙값 · 최소~최대 · 10~90%)만 data/derived/navi_check.json 에 쓴다.
호출 상한: 한 실행 MAX_CALLS(60) · 마지막 결과가 FRESH_DAYS(25) 안이면 0(--force 아니면) · 인증·쿼터 오류가 나면 바로 멈춘다.
키: 환경 변수 KAKAO_REST_KEY(Actions 비밀) — 머리글로만 보낸다(주소에 없다) · 오류 문구에서 지운다 · 찍지 않는다.
  python tools-build/navi_check.py [--force] [--selftest]
(v3 폴더 밖에 둔다 — 거기 두면 data-v3 워크플로 전체가 이 파일 변경에 돌기 때문)
"""
import datetime, json, os, statistics, sys, urllib.error, urllib.parse, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "v3"))
from common import ROOT, write, say  # noqa: E402

API = "https://apis-navi.kakaomobility.com/v1/future/directions"
MAX_CALLS = 60          # 공개된 무료 일 쿼터(미래 운행 정보 길찾기 5,000건)의 1.2% — 코드 상한(넘으면 부르지 않는다)
FRESH_DAYS = 25
N_PAIRS = 30
MIN_OK = 25             # 시간대마다 유효 쌍이 이보다 적으면 미달(지면은 「내비 대조 미실시」)
SLOTS = {"출근 08:00": "0800", "낮 14:00": "1400"}
OUT = "data/derived/navi_check.json"
KST = datetime.timezone(datetime.timedelta(hours=9))


def pairs(iso):
    """출발지 × 도시에서 고정 규칙으로 N_PAIRS 쌍 — 출발지를 번갈아(도시 순서는 osm_iso CITIES 순) · 모델 값이 없는(None) 쌍은 뺀다."""
    O = iso["origins"]; C = list(iso["cities"].keys())
    out = []
    for k in range(len(O) * len(C)):
        o = O[k % len(O)]; c = C[(k // len(O) + k) % len(C)]
        m = o["cities"].get(c)
        if m is None or any(p[0] == o["name"] and p[1] == c for p in out): continue
        out.append((o["name"], c, (o["lon"], o["lat"]), tuple(iso["cities"][c]), m))
        if len(out) >= N_PAIRS: break
    return out


def next_weekday(now, hhmm):
    """다음 화요일(공휴일 피함 아님 · 평일 하루) hhmm — 미래 출발시각."""
    d = now.date() + datetime.timedelta(days=1)
    while d.weekday() != 1: d += datetime.timedelta(days=1)
    return d.strftime("%Y%m%d") + hhmm


def stats(errs):
    e = sorted(errs)
    q = lambda p: e[min(len(e) - 1, max(0, round(p * (len(e) - 1))))]
    return {"n": len(e), "median_pct": round(statistics.median(e), 1), "min_pct": round(e[0], 1), "max_pct": round(e[-1], 1),
            "p10_pct": round(q(0.1), 1), "p90_pct": round(q(0.9), 1)}


class Stop(Exception):
    pass


def call(key, o, d, dep, budget):
    if budget[0] >= MAX_CALLS: raise Stop("호출 상한")
    budget[0] += 1
    q = urllib.parse.urlencode({"origin": f"{o[0]},{o[1]}", "destination": f"{d[0]},{d[1]}", "departure_time": dep, "priority": "RECOMMEND", "car_type": 1, "summary": "true"})
    req = urllib.request.Request(f"{API}?{q}", headers={"Authorization": f"KakaoAK {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r: J = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429): raise Stop(f"HTTP {e.code}")
        return None
    except Exception as e:
        raise Stop(type(e).__name__)
    R = (J.get("routes") or [{}])[0]
    if R.get("result_code") != 0: return None
    return R["summary"]["duration"] / 60  # 분 — 이 함수 밖으로 나가 통계에만 쓰인다(저장 안 함)


def main():
    force = "--force" in sys.argv
    prev = os.path.join(ROOT, OUT)
    if os.path.exists(prev) and not force:
        P = json.load(open(prev, encoding="utf-8"))
        made = datetime.date.fromisoformat(P.get("made", "2000-01-01"))
        if (datetime.date.today() - made).days < FRESH_DAYS and P.get("status") == "ok":
            say("지난 대조가", P["made"], "— 25일 안이라 부르지 않는다(호출 0)"); return 0
    key = os.environ.get("KAKAO_REST_KEY", "").strip()
    iso = json.load(open(os.path.join(ROOT, "data/derived/isochrones.json"), encoding="utf-8"))
    PR = pairs(iso)
    base = {"_설명": "등시선(우리 모델 · OSM 자유 흐름) 도착 분을 카카오모빌리티 미래 운행 정보 길찾기(승용 · 추천 경로)와 견준 오차 통계. "
                     "오차 = (우리 값 − 내비 값) ÷ 내비 값 × 100. 음수 = 우리가 짧게 잡음. 경로·OD별 시간은 약관(저장·캐싱 금지)대로 남기지 않는다.",
            "source": "카카오모빌리티 길찾기 API(미래 운행 정보) — 통계만", "made": datetime.date.today().isoformat(),
            "model_made": iso.get("made"), "pairs": [{"from": p[0], "to": p[1]} for p in PR], "max_calls": MAX_CALLS}
    if not key:
        write(OUT, {**base, "status": "skipped", "reason": "키 없음(KAKAO_REST_KEY)", "calls": 0}); say("키 없음 — 내비 대조 미실시"); return 0
    now = datetime.datetime.now(KST)
    budget, res, stopped = [0], {}, None
    for slot, hhmm in SLOTS.items():
        dep = next_weekday(now, hhmm); errs = []
        try:
            for (_, _, o, d, m) in PR:
                n = call(key, o, d, dep, budget)
                if n and n > 0: errs.append((m - n) / n * 100)
        except Stop as e:
            stopped = str(e).replace(key, "***")
        res[slot] = {"departure": f"{dep[:4]}-{dep[4:6]}-{dep[6:8]} {dep[8:10]}:{dep[10:]} KST", **(stats(errs) if errs else {"n": 0})}
        say(slot, "유효", len(errs), "쌍")
        if stopped: break
    ok = not stopped and all(r["n"] >= MIN_OK for r in res.values()) and len(res) == len(SLOTS)
    write(OUT, {**base, "status": "ok" if ok else "short", "reason": stopped or ("" if ok else f"유효 쌍 < {MIN_OK}"), "calls": budget[0], "slots": res})
    say("호출", budget[0], "/", MAX_CALLS, "· 상태", "ok" if ok else "short", "·", {k: v.get("median_pct") for k, v in res.items()})
    return 0


def selftest():
    iso = {"cities": {f"c{i}": [127 + i / 100, 37.5] for i in range(18)},
           "origins": [{"name": f"o{j}", "lon": 126.6, "lat": 37.4, "cities": {f"c{i}": (None if (i, j) == (0, 0) else 30 + i) for i in range(18)}} for j in range(4)]}
    P = pairs(iso)
    assert len(P) == N_PAIRS and len({(p[0], p[1]) for p in P}) == N_PAIRS and all(p[4] is not None for p in P), P
    assert len({p[0] for p in P}) == 4, "출발지가 고루 들어가야 한다"
    s = stats([-30, -10, 0, 10, 50])
    assert s["median_pct"] == 0 and s["min_pct"] == -30 and s["max_pct"] == 50 and s["n"] == 5, s
    dep = next_weekday(datetime.datetime(2026, 10, 15, 12, tzinfo=KST), "0800")
    assert dep == "202610200800", dep  # 10/15(목) → 다음 화요일 10/20
    # 상한: 예산을 다 쓰면 부르지 않는다
    try: call("k", (0, 0), (0, 0), dep, [MAX_CALLS]); raise AssertionError("상한을 넘어 불렀다")
    except Stop: pass
    print("selftest 4/4 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

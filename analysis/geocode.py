# -*- coding: utf-8 -*-
"""주소 → 좌표(WGS84 위경도). 결과는 저장소 캐시에 남기고 같은 주소는 다시 안 부른다.

왜 이 구조인가
--------------
**저장하는 좌표의 원천은 행정안전부 도로명주소 API 다 — 브이월드가 아니다.**
오너 위임문(2026-09-30)은 브이월드 지오코더를 주력으로 적었는데, 브이월드 지오코더 2.0
레퍼런스가 「API 요청은 실시간으로 사용하셔야 하며 별도의 저장장치나 데이터베이스에
저장할 수 없습니다」를 든다. **캐시를 커밋한다는 요구와 정면으로 부딪힌다.**
그래서 두 단계로 간다(선커밋 `docs/주소좌표_판정기준_선커밋_20260930.md` 끝 절).

  1. 도로명주소 **검색 API** — 원주소를 정제한다(도로명·지번·시도·건물 식별자).
  2. 도로명주소 **좌표제공 API** — 그 건물 식별자로 출입구 좌표(UTM-K · EPSG:5179)를 받는다.
  3. UTM-K → WGS84 는 **이 파일이 계산한다**(외부 패키지 없음 · pyproj 와 1e-7° 안에서 맞췄다).

**브이월드는 대조용으로만 부른다**(`--crosscheck-vworld`). 거리만 화면에 찍고
**좌표를 어디에도 쓰지 않는다** — 파일에도, 캐시에도.

키
--
환경 변수 `JUSO_SEARCH_KEY` · `JUSO_COORD_KEY` · `VWORLD_KEY`(선택).
저장소 뿌리의 `.env` 가 있으면 읽는다(이미 있는 환경 변수를 덮지 않는다). `.env` 는
`.gitignore` 에 있고 틀은 `.env.example` 이다. **키는 화면에 안 찍는다** — 오류 문구에
키가 섞여 나오면 `***` 로 가린다.

키가 없어도 도는 것 — 캐시 조회 · `--dry-run`(몇 건이 캐시에 있고 몇 건을 부를지) ·
`--summary`(검증 요약) · `--sample`(채팅 대조용 무작위 10건) · `--selftest`.
`--refine-only` 는 `JUSO_SEARCH_KEY` 하나로 돈다 — 정제만 하고 상태 `REFINED` 로 캐시에 남긴다.
좌표 키가 들어온 뒤 보통 실행이 그 행들의 좌표만 받는다(검색은 다시 안 부른다).

닿지 않는 곳
------------
· **인천 경계는 다각형이 아니다.** 시도명(`인천광역시`) + 외곽 사각형 둘로 본다.
  사각형만으로는 김포·시흥 일부가 안에 든다 — 그 구멍은 시도명이 막는다.
· **좌표는 건물 출입구 한 점이다.** 부지가 넓은 창고는 대조 지도의 핀과 수백 m 갈릴 수 있다.
· 검색 API 가 후보를 여럿 내면 **첫 후보를 쓰고 `후보수` 에 남긴다.** 맞는 후보인지는 대조가 본다.
· 두 API 의 요청·응답 필드는 **공식 문서를 이 컨테이너에서 못 열었다**(`*.go.kr` 차단 · 2026-09-30).
  필드명은 널리 쓰이는 형태로 적었고, **첫 실호출이 확인이다** — 필드가 다르면 여기서 멈추고 말한다.

  python analysis/geocode.py --in analysis/incheon_warehouses.csv --col 소재지 --dry-run
  python analysis/geocode.py --in analysis/incheon_warehouses.csv --col 소재지
  python analysis/geocode.py --in analysis/incheon_warehouses.csv --col 소재지 --summary
  python analysis/geocode.py --in analysis/incheon_warehouses.csv --col 소재지 --sample 10
  python analysis/geocode.py --selftest
"""

import argparse
import csv
import datetime
import io
import json
import math
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, "geocode_cache.csv")

FIELDS = ["원주소", "검색어", "정제주소", "지번주소", "시도", "위도", "경도",
          "상태", "후보수", "건물식별", "출처API", "조회일"]
# 좌표제공 API 가 받는 건물 식별자. 정제만 한 행(REFINED)은 이것을 캐시에 남겨
# 좌표 단계가 검색 API 를 다시 안 부르게 한다(개발 키 만료 뒤에도 좌표 단계가 돈다).
BLD_KEYS = ("admCd", "rnMgtSn", "udrtYn", "buldMnnm", "buldSlno")

JUSO_SEARCH_URL = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
JUSO_COORD_URL = "https://business.juso.go.kr/addrlink/addrCoordApi.do"
VWORLD_URL = "https://api.vworld.kr/req/address"
SOURCE = "행정안전부 도로명주소 검색API+좌표제공API"

# 인천 외곽 사각형 — 옹진 도서(백령·연평·덕적)까지. **경계가 아니다**(위 「닿지 않는 곳」).
INCHEON_BOX = (124.5, 126.9, 36.9, 38.0)  # 경도 min, max, 위도 min, max
INCHEON_SIDO = "인천광역시"
SAMPLE_SEED = 20260930  # 선커밋에서 고정했다. 바꾸지 않는다.

KEY_NAMES = ("JUSO_SEARCH_KEY", "JUSO_COORD_KEY", "VWORLD_KEY")


class StopError(Exception):
    """캐시에 실패로 적으면 안 되는 실패 — 키·한도·응답 형식. 멈추고 말한다."""


# ── 키 ─────────────────────────────────────────────────────────────

def load_env(path=None):
    """`.env` 의 KEY=VALUE 를 os.environ 에 얹는다. 이미 있는 값은 안 덮는다."""
    path = path or os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in io.open(path, encoding="utf-8-sig"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v


def get_keys():
    return {k: os.environ.get(k, "").strip() for k in KEY_NAMES}


def mask(text, keys):
    """문구에 섞인 키를 가린다. 짧은 값(빈 값)은 건드리지 않는다."""
    text = str(text)
    for v in keys.values():
        if v and len(v) >= 6:
            text = text.replace(v, "***").replace(urllib.parse.quote(v, safe=""), "***")
    return text


# ── 좌표계 — UTM-K(EPSG:5179) → WGS84 ────────────────────────────────
# GRS80 · 원점 38°N 127.5°E · 축척 0.9996 · 가산 (1,000,000 , 2,000,000).
# 횡메르카토르 역변환(Snyder 1987 식 8-18~8-25). GRS80 과 WGS84 의 차이는 mm 단위라 무시한다.

_A = 6378137.0
_F = 1 / 298.257222101
_K0 = 0.9996
_LAT0 = math.radians(38.0)
_LON0 = math.radians(127.5)
_FE, _FN = 1000000.0, 2000000.0


def _meridian(phi, e2):
    e4, e6 = e2 * e2, e2 * e2 * e2
    return _A * ((1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
                 - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
                 + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
                 - (35 * e6 / 3072) * math.sin(6 * phi))


def utmk_to_wgs84(x, y):
    """(entX, entY) 미터 → (위도, 경도) 도."""
    e2 = _F * (2 - _F)
    ep2 = e2 / (1 - e2)
    m = _meridian(_LAT0, e2) + (y - _FN) / _K0
    mu = m / (_A * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
            + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    s, c, t = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    c1 = ep2 * c * c
    t1 = t * t
    n1 = _A / math.sqrt(1 - e2 * s * s)
    r1 = _A * (1 - e2) / (1 - e2 * s * s) ** 1.5
    d = (x - _FE) / (n1 * _K0)
    lat = phi1 - (n1 * t / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = _LON0 + (d - (1 + 2 * t1 + c1) * d ** 3 / 6
                   + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / c
    return math.degrees(lat), math.degrees(lon)


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ── 주소 정제(호출 전) ───────────────────────────────────────────────

def norm_key(addr):
    """캐시 열쇠 — 공백만 고른다. 뜻을 바꾸는 정제는 여기서 안 한다."""
    return re.sub(r"\s+", " ", (addr or "").replace("　", " ")).strip()


_SPECIAL = re.compile(r"[%=><\[\]{}\"'`;:|^~!@#$*+?\\]")


def keyword_variants(addr):
    """검색어 후보를 좁히는 순서로 낸다. 앞이 찾으면 뒤는 안 친다.

    ① 괄호·특수문자·「외 N필지」만 걷은 것
    ② 거기에 번지 뒤의 동·층·호·건물명 꼬리를 자른 것
    ③ 시·구·동·번지까지만 남긴 것(지번 핵심)
    """
    s = norm_key(addr)
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", s)
    s = re.sub(r"\s*외\s*\d+\s*(필지|개\s*필지|筆地)?", " ", s)
    s = re.sub(r",.*$", " ", s)          # 쉼표 뒤는 상세주소다
    s = _SPECIAL.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    out = [s]
    # 도로명: 「…로 123」「…길 12-3」 / 지번: 「…동 123-4」「…가 7-1」「…리 산12」
    m = re.match(r"^(.*?(?:로|길)\s*\d+(?:-\d+)?)(?=\s|$)", s)
    if not m:
        m = re.match(r"^(.*?(?:동|가|리)\s*(?:산\s*)?\d+(?:-\d+)?)(?=\s|$)", s)
    if m and m.group(1).strip() != s:
        out.append(m.group(1).strip())
    m = re.match(r"^(.*?(?:동|가|리)\d*\s*(?:산\s*)?\d+(?:-\d+)?)(?=\s|$)", s)
    if m and m.group(1).strip() not in out:
        out.append(m.group(1).strip())
    return [v for v in out if v]


# ── HTTP ────────────────────────────────────────────────────────────

def http_get_json(url, params, timeout=20):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(url + "?" + q, headers={"User-Agent": "sounding-geocode/1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ── 도로명주소 API ───────────────────────────────────────────────────

def juso_search(keyword, key, fetch):
    """→ (후보 목록, 총건수). 키·한도 오류는 StopError."""
    d = fetch(JUSO_SEARCH_URL, {"confmKey": key, "currentPage": 1, "countPerPage": 10,
                                "keyword": keyword, "resultType": "json"})
    try:
        common = d["results"]["common"]
        code = str(common.get("errorCode", ""))
    except (KeyError, TypeError):
        raise StopError("검색 API 응답 형식이 예상과 다르다 — 필드명을 확인하라")
    if code != "0":
        msg = common.get("errorMessage", "")
        # 검색어 문제(주소를 상세히·너무 많음·특수문자 등)는 이 주소의 실패다.
        # 그 밖(E0001 키 · E0014 개발키 만료 · -999 시스템)은 멈춘다.
        # 코드 목록은 기억에서 적었다 — [공식 문서 대조 미확인]. 모르는 코드는 멈추는 쪽으로 간다.
        if code in ("E0005", "E0006", "E0008", "E0009", "E0010", "E0011", "E0012", "E0013", "E0015"):
            return [], 0
        raise StopError("검색 API 오류 %s: %s" % (code, msg))
    juso = d["results"].get("juso") or []
    return juso, int(common.get("totalCount") or len(juso))


def juso_coord(item, key, fetch):
    """검색 후보 하나 → (entX, entY) 또는 None."""
    need = BLD_KEYS
    if any(k not in item for k in need):
        raise StopError("검색 후보에 좌표 조회용 필드가 없다: %s" % ",".join(k for k in need if k not in item))
    p = {k: item[k] for k in need}
    p.update({"confmKey": key, "resultType": "json"})
    d = fetch(JUSO_COORD_URL, p)
    try:
        common = d["results"]["common"]
        code = str(common.get("errorCode", ""))
    except (KeyError, TypeError):
        raise StopError("좌표제공 API 응답 형식이 예상과 다르다 — 필드명을 확인하라")
    if code != "0":
        raise StopError("좌표제공 API 오류 %s: %s" % (code, common.get("errorMessage", "")))
    rows = d["results"].get("juso") or []
    if not rows or not rows[0].get("entX") or not rows[0].get("entY"):
        return None
    return float(rows[0]["entX"]), float(rows[0]["entY"])


def bld_pack(item):
    return "|".join(str(item.get(k, "")) for k in BLD_KEYS)


def bld_unpack(text):
    parts = (text or "").split("|")
    return dict(zip(BLD_KEYS, parts)) if len(parts) == len(BLD_KEYS) and all(parts[:2]) else None


def geocode_one(addr, keys, fetch, today, refine_only=False, prev=None):
    """refine_only — 검색만 하고 REFINED 로 남긴다.
    prev 가 REFINED 이고 건물식별이 있으면 검색을 건너뛰고 좌표만 받는다."""
    if prev and prev.get("상태") == "REFINED" and not refine_only:
        item = bld_unpack(prev.get("건물식별"))
        if item:
            row = dict(prev, 조회일=today)
            xy = juso_coord(item, keys["JUSO_COORD_KEY"], fetch)
            if xy is None:
                row["상태"] = "NO_COORD"
                return row
            lat, lon = utmk_to_wgs84(*xy)
            row.update({"위도": "%.7f" % lat, "경도": "%.7f" % lon, "상태": "OK"})
            return row
    base = {"원주소": norm_key(addr), "검색어": "", "정제주소": "", "지번주소": "", "시도": "",
            "위도": "", "경도": "", "상태": "NOT_FOUND", "후보수": "0", "건물식별": "",
            "출처API": SOURCE, "조회일": today}
    for kw in keyword_variants(addr):
        cands, total = juso_search(kw, keys["JUSO_SEARCH_KEY"], fetch)
        if not cands:
            continue
        top = cands[0]
        base.update({"검색어": kw, "정제주소": top.get("roadAddr", ""),
                     "지번주소": top.get("jibunAddr", ""), "시도": top.get("siNm", ""),
                     "후보수": str(total), "건물식별": bld_pack(top)})
        if refine_only:
            base["상태"] = "REFINED"
            return base
        xy = juso_coord(top, keys["JUSO_COORD_KEY"], fetch)
        if xy is None:
            base["상태"] = "NO_COORD"
            return base
        lat, lon = utmk_to_wgs84(*xy)
        base.update({"위도": "%.7f" % lat, "경도": "%.7f" % lon, "상태": "OK"})
        return base
    base["검색어"] = " | ".join(keyword_variants(addr))
    return base


# ── 캐시 ────────────────────────────────────────────────────────────

def read_cache(path=CACHE):
    if not os.path.exists(path):
        return {}
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        return {r["원주소"]: r for r in csv.DictReader(f)}


def write_cache(cache, path=CACHE):
    rows = sorted(cache.values(), key=lambda r: r["원주소"])
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    os.replace(tmp, path)


def read_input(path, col):
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        if col not in (rd.fieldnames or []):
            raise SystemExit("열 %r 가 없다. 있는 열: %s" % (col, ", ".join(rd.fieldnames or [])))
        seen, out = set(), []
        for r in rd:
            k = norm_key(r[col])
            if k and k not in seen:
                seen.add(k)
                out.append(k)
    return out


def pending(addrs, cache, retry_failed=False, refine_only=False):
    """부를 것. 정제 모드에서 REFINED 는 끝난 것이고, 보통 모드에서는 좌표를 받을 것이다."""
    def need(a):
        if a not in cache:
            return True
        st = cache[a]["상태"]
        if st == "REFINED":
            return not refine_only
        return retry_failed and st != "OK" and not (refine_only and st == "NO_COORD")
    return [a for a in addrs if need(a)]


def run(addrs, cache, keys, fetch, dry_run=False, retry_failed=False, sleep=0.1,
        today=None, save=None, refine_only=False):
    """캐시에 없는 것만 부른다. 돌려주는 값 = (부른 수, 적중 수, 부를 수)."""
    today = today or datetime.date.today().isoformat()
    todo = pending(addrs, cache, retry_failed, refine_only)
    hit = len(addrs) - len(todo)
    if dry_run:
        return 0, hit, len(todo)
    if todo:
        need = ["JUSO_SEARCH_KEY"] if refine_only else ["JUSO_COORD_KEY"]
        if not refine_only and any(not (a in cache and cache[a]["상태"] == "REFINED") for a in todo):
            need.append("JUSO_SEARCH_KEY")
        missing = [k for k in need if not keys[k]]
        if missing:
            raise StopError("키가 없다 — %s (docs/주소좌표_키발급안내.md)" % " · ".join(missing))
    called = 0
    for i, a in enumerate(todo, 1):
        try:
            prev = None if retry_failed and a in cache and cache[a]["상태"] != "REFINED" else cache.get(a)
            cache[a] = geocode_one(a, keys, fetch, today, refine_only=refine_only, prev=prev)
        except StopError:
            if save:
                save(cache)
            raise
        except Exception as e:  # 망 오류 — 캐시에 안 적는다(다음에 다시 부른다)
            print("  망 오류(캐시 안 함) %s: %s" % (a, mask(e, keys)))
            continue
        called += 1
        if save and i % 50 == 0:
            save(cache)
        time.sleep(sleep)
    if save:
        save(cache)
    return called, hit, len(todo)


# ── 검증 요약 ────────────────────────────────────────────────────────

def summarize(addrs, cache):
    rows = [cache[a] for a in addrs if a in cache]
    missing = [a for a in addrs if a not in cache]
    ok = [r for r in rows if r["상태"] == "OK"]
    fail = [r for r in rows if r["상태"] != "OK"]
    lo1, lo2, la1, la2 = INCHEON_BOX
    outside = []
    for r in ok:
        lat, lon = float(r["위도"]), float(r["경도"])
        why = []
        if r["시도"] != INCHEON_SIDO:
            why.append("시도=%s" % (r["시도"] or "빈칸"))
        if not (lo1 <= lon <= lo2 and la1 <= lat <= la2):
            why.append("사각형 밖")
        if why:
            outside.append((r, "·".join(why)))
    by_xy = {}
    for r in ok:
        k = "%.5f,%.5f" % (float(r["위도"]), float(r["경도"]))
        by_xy.setdefault(k, []).append(r["원주소"])
    dup = {k: v for k, v in by_xy.items() if len(v) > 1}
    refined = [r for r in rows if r["정제주소"]]
    multi = [r for r in refined if int(r["후보수"] or 0) > 1]
    # 정제 단계만의 판정 — 좌표가 없어도 잴 수 있는 것(경계는 ① 시도명만).
    refine_out = [r for r in refined if r["시도"] != INCHEON_SIDO]
    return {"분모": len(addrs), "미조회": missing, "성공": ok, "실패": fail,
            "경계밖": outside, "중복좌표": dup, "다중후보": multi,
            "정제": refined, "정제실패": [r for r in rows if not r["정제주소"]],
            "정제시도밖": refine_out,
            "좌표대기": [r for r in rows if r["상태"] == "REFINED"]}


def print_summary(s):
    n = s["분모"]
    done = n - len(s["미조회"])
    rate = (100.0 * len(s["성공"]) / n) if n else 0.0
    print("── 검증 요약 ──")
    print("  고유 원주소 %d · 조회됨 %d · 미조회 %d" % (n, done, len(s["미조회"])))
    print("  [정제] 성공 %d / %d = %.1f%% · 실패 %d · 다중 후보 %d · 시도≠인천광역시 %d · 좌표 대기 %d"
          % (len(s["정제"]), n, (100.0 * len(s["정제"]) / n) if n else 0.0, len(s["정제실패"]),
             len(s["다중후보"]), len(s["정제시도밖"]), len(s["좌표대기"])))
    print("  성공 %d / %d = %.1f%%  (기준 95%% · 재시도 하한 80%%)" % (len(s["성공"]), n, rate))
    print("  실패 %d · 인천 경계 밖 %d (기준 0) · 중복 좌표 %d묶음 · 다중 후보 %d"
          % (len(s["실패"]), len(s["경계밖"]), len(s["중복좌표"]), len(s["다중후보"])))
    if not n:
        print("  **분모 0 — 통과가 아니다.**")
    for r in s["실패"]:
        if r["상태"] != "REFINED":
            print("  [실패 %s] %s" % (r["상태"], r["원주소"]))
    for r in s["정제시도밖"]:
        print("  [정제 시도 밖 %s] %s → %s" % (r["시도"] or "빈칸", r["원주소"], r["정제주소"]))
    for r, why in s["경계밖"]:
        print("  [경계 밖 %s] %s → %s" % (why, r["원주소"], r["정제주소"]))
    for k, v in sorted(s["중복좌표"].items()):
        print("  [중복 %s] %s" % (k, " / ".join(v)))
    for r in s["다중후보"]:
        print("  [후보 %s] %s → %s" % (r["후보수"], r["원주소"], r["정제주소"]))
    if n and s["미조회"]:
        print("  **미조회가 남아 있다 — 이 성공률은 판정값이 아니다.**")
    return rate


def pick_sample(s, k=10, seed=SAMPLE_SEED):
    ok = sorted(s["성공"], key=lambda r: r["원주소"])
    return random.Random(seed).sample(ok, min(k, len(ok)))


# ── 브이월드 대조 — 저장하지 않는다 ────────────────────────────────────

def vworld_point(addr, key, fetch):
    for typ in ("road", "parcel"):
        d = fetch(VWORLD_URL, {"service": "address", "request": "getcoord", "version": "2.0",
                               "crs": "epsg:4326", "address": addr, "refine": "true",
                               "simple": "false", "format": "json", "type": typ, "key": key})
        resp = d.get("response", {})
        if resp.get("status") == "OK":
            p = resp["result"]["point"]
            return float(p["y"]), float(p["x"])
        if resp.get("status") == "ERROR":
            raise StopError("브이월드 오류: %s" % resp.get("error", {}).get("text", ""))
    return None


def crosscheck_vworld(sample, keys, fetch):
    """거리만 찍는다. 브이월드 좌표는 변수 밖으로 안 나간다(약관 — 저장 금지)."""
    if not keys["VWORLD_KEY"]:
        raise StopError("VWORLD_KEY 가 없다 — 대조는 선택이다")
    dists = []
    for r in sample:
        q = r["정제주소"] or r["원주소"]
        try:
            pt = vworld_point(q, keys["VWORLD_KEY"], fetch)
        except StopError:
            raise
        except Exception as e:
            print("  망 오류 %s: %s" % (q, mask(e, keys)))
            continue
        if pt is None:
            print("  [브이월드 못 찾음] %s" % q)
            continue
        dm = haversine_m(float(r["위도"]), float(r["경도"]), pt[0], pt[1])
        dists.append(dm)
        print("  %7.0f m  %s" % (dm, q))
    if dists:
        print("  100m 이내 %d / %d" % (sum(d <= 100 for d in dists), len(dists)))
    return dists


# ── 인수시험 ─────────────────────────────────────────────────────────

def selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok = ok and good
        print("  %s %-54s %s" % ("OK  " if good else "FAIL", label,
                                 "" if good else "-> %r (기대 %r)" % (got, want)))

    print("── 좌표계: pyproj 3.7.2 (EPSG:5179→4326) 값과 1e-7° 안 ──")
    ref = [((916000, 1937000), (37.428346996, 126.550584993)),
           ((945000, 1945000), (37.502630623, 126.877739552)),
           ((1000000, 2000000), (38.0, 127.5)),
           ((781000, 1990000), (37.883520862, 125.009747457)),
           ((955000, 1905000), (37.142629122, 126.993299821))]
    for (x, y), (la, lo) in ref:
        got = utmk_to_wgs84(x, y)
        chk("utmk(%d,%d)" % (x, y), abs(got[0] - la) < 1e-7 and abs(got[1] - lo) < 1e-7, True)

    print("── 검색어 정제 ──")
    chk("괄호·외필지·쉼표", keyword_variants("인천광역시 중구 신흥동3가 7-1 외 2필지 (창고동), 2층")[0],
        "인천광역시 중구 신흥동3가 7-1")
    v = keyword_variants("인천광역시 서구 북항로 120 B동 3층")
    chk("도로명 꼬리 자르기", v[:2], ["인천광역시 서구 북항로 120 B동 3층", "인천광역시 서구 북항로 120"])
    chk("특수문자 제거", keyword_variants("인천 연수구 송도동 %=< 12")[0], "인천 연수구 송도동 12")
    chk("공백 열쇠", norm_key("  인천광역시　중구   항동7가 1 "), "인천광역시 중구 항동7가 1")

    print("── 흐름: 가짜 API(망 없음) ──")
    calls = []
    # 좌표 API 는 늘 인천 중구 부근 한 점(916000,1937000 → 37.428, 126.551)을 준다
    def fake(url, p):
        calls.append(url)
        if url == JUSO_SEARCH_URL:
            if "없는주소" in p["keyword"]:
                return {"results": {"common": {"errorCode": "0", "totalCount": "0"}, "juso": []}}
            if "키오류" in p["keyword"]:
                return {"results": {"common": {"errorCode": "E0001", "errorMessage": "승인되지 않은 KEY"}}}
            sido = "경기도" if "김포" in p["keyword"] else "인천광역시"
            n = "2" if "두후보" in p["keyword"] else "1"
            item = {"roadAddr": sido + " 가상로 1", "jibunAddr": sido + " 가상동 1", "siNm": sido,
                    "admCd": "2811010100", "rnMgtSn": "281103000001", "udrtYn": "0",
                    "buldMnnm": "1", "buldSlno": "0"}
            return {"results": {"common": {"errorCode": "0", "totalCount": n}, "juso": [item] * int(n)}}
        if url == JUSO_COORD_URL:
            return {"results": {"common": {"errorCode": "0"}, "juso": [{"entX": "916000", "entY": "1937000"}]}}
        raise AssertionError(url)

    keys = {"JUSO_SEARCH_KEY": "s" * 20, "JUSO_COORD_KEY": "c" * 20, "VWORLD_KEY": ""}
    cache = {}
    addrs = ["인천 중구 가상로 1", "인천 중구 없는주소 9", "경기 김포시 가상로 1", "인천 서구 두후보로 3"]
    c, h, t = run(addrs, cache, keys, fake, sleep=0, today="2026-09-30")
    chk("첫 실행 — 넷 다 부름", (c, h, t), (4, 0, 4))
    chk("원천 표기", cache[addrs[0]]["출처API"], SOURCE)
    chk("좌표 변환됨", cache[addrs[0]]["위도"], "37.4283470")
    chk("없는 주소 = NOT_FOUND (캐시에 남긴다)", cache[addrs[1]]["상태"], "NOT_FOUND")
    n0 = len(calls)
    c, h, t = run(addrs, cache, {k: "" for k in keys}, fake, sleep=0)
    chk("둘째 실행 — 키 없이도 캐시로 끝남 · 호출 0", (c, h, t, len(calls) - n0), (0, 4, 0, 0))
    chk("드라이런 — 부를 수만 센다", run(addrs + ["새 주소 1"], cache, keys, fake, dry_run=True), (0, 4, 1))
    try:
        run(["새 주소 1"], cache, {k: "" for k in keys}, fake)
        chk("키 없이 부를 것이 있으면 멈춘다", False, True)
    except StopError:
        chk("키 없이 부를 것이 있으면 멈춘다", True, True)
    try:
        run(["인천 키오류 1"], cache, keys, fake, sleep=0)
        chk("키 오류는 멈춘다", False, True)
    except StopError:
        chk("키 오류는 멈춘다", True, True)
    chk("키 오류는 캐시에 실패로 안 남는다", "인천 키오류 1" in cache, False)

    s = summarize(addrs, cache)
    chk("성공 3 · 실패 1", (len(s["성공"]), len(s["실패"])), (3, 1))
    chk("경계 밖 = 김포(시도로 잡는다)", [r["원주소"] for r, _ in s["경계밖"]], ["경기 김포시 가상로 1"])
    chk("중복 좌표 1묶음(셋이 같은 점)", [len(v) for v in s["중복좌표"].values()], [3])
    chk("다중 후보 1", [r["원주소"] for r in s["다중후보"]], ["인천 서구 두후보로 3"])
    chk("표본은 시드로 고정", [r["원주소"] for r in pick_sample(s, 2)],
        [r["원주소"] for r in pick_sample(s, 2)])
    far = dict(cache[addrs[0]], 원주소="먼곳", 위도="37.40", 경도="124.30", 시도=INCHEON_SIDO)
    chk("사각형 밖을 잡는다", summarize(["먼곳"], {"먼곳": far})["경계밖"][0][1], "사각형 밖")
    chk("분모 0 은 0%", summarize([], {})["분모"], 0)

    print("── 정제만(좌표 키 없음) → 좌표 키 들어온 뒤 ──")
    rc, n1 = {}, len(calls)
    skey = dict(keys, JUSO_COORD_KEY="")
    ra = ["인천 중구 가상로 1", "인천 중구 없는주소 9", "인천 서구 두후보로 3"]
    chk("정제 — 좌표 키 없이 돈다", run(ra, rc, skey, fake, sleep=0, refine_only=True), (3, 0, 3))
    chk("정제 — 좌표 API 안 부름", JUSO_COORD_URL in calls[n1:], False)
    chk("정제 — 상태", [rc[a]["상태"] for a in ra], ["REFINED", "NOT_FOUND", "REFINED"])
    rs = summarize(ra, rc)
    chk("정제 요약 — 성공 2 · 실패 1 · 다중 1 · 좌표 대기 2",
        (len(rs["정제"]), len(rs["정제실패"]), len(rs["다중후보"]), len(rs["좌표대기"]), len(rs["성공"])),
        (2, 1, 1, 2, 0))
    chk("정제 재실행 — 부를 것 0", run(ra, rc, skey, fake, dry_run=True, refine_only=True), (0, 3, 0))
    try:
        run(ra, rc, dict(keys, JUSO_COORD_KEY=""), fake, sleep=0)
        chk("좌표 단계에 좌표 키 없으면 멈춘다", False, True)
    except StopError as e:
        chk("좌표 단계에 좌표 키 없으면 멈춘다", "JUSO_COORD_KEY" in str(e), True)
    n2 = len(calls)
    ckey = dict(keys, JUSO_SEARCH_KEY="")   # 개발 검색 키가 만료된 뒤를 흉내 낸다
    chk("좌표 단계 — 검색 키 없이 REFINED 둘만", run(ra, rc, ckey, fake, sleep=0)[0], 2)
    chk("좌표 단계 — 검색 API 안 부름", JUSO_SEARCH_URL in calls[n2:], False)
    chk("좌표 단계 — OK 로 바뀜", [rc[a]["상태"] for a in ra], ["OK", "NOT_FOUND", "OK"])
    chk("좌표 단계 — 정제주소 보존", rc[ra[0]]["정제주소"], "인천광역시 가상로 1")

    print("── 키를 안 흘린다 ──")
    k = {"JUSO_SEARCH_KEY": "devU01TX0FVVEgyMDI2", "JUSO_COORD_KEY": "", "VWORLD_KEY": ""}
    chk("오류 문구의 키 가림", mask("url?confmKey=devU01TX0FVVEgyMDI2&x=1", k), "url?confmKey=***&x=1")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "c.csv")
        write_cache(cache, p)
        body = io.open(p, encoding="utf-8").read()
        chk("캐시에 키 없음", ("s" * 20) in body or ("c" * 20) in body, False)
        chk("캐시 왕복", read_cache(p)[addrs[0]]["경도"], cache[addrs[0]]["경도"])
        e = os.path.join(d, ".env")
        io.open(e, "w", encoding="utf-8").write("# 주석\nGEOCODE_SELFTEST_X='abc'\n")
        load_env(e)
        chk(".env 읽기", os.environ.pop("GEOCODE_SELFTEST_X", ""), "abc")

    print("── 브이월드 대조는 아무것도 쓰지 않는다 ──")
    before = dict(cache[addrs[0]])
    def vfake(url, p):
        return {"response": {"status": "OK", "result": {"point": {"x": "126.5510", "y": "37.4285"}}}}
    ds = crosscheck_vworld([cache[addrs[0]]], dict(keys, VWORLD_KEY="v" * 20), vfake)
    chk("거리만 낸다(수십 m)", 0 < ds[0] < 100, True)
    chk("캐시 행 불변", cache[addrs[0]], before)

    print("\n인수시험 %s" % ("통과" if ok else "**실패**"))
    return 0 if ok else 1


# ── 입구 ────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", help="주소가 든 CSV")
    ap.add_argument("--col", default="소재지", help="주소 열 이름")
    ap.add_argument("--dry-run", action="store_true", help="부르지 않고 몇 건을 부를지만")
    ap.add_argument("--retry-failed", action="store_true", help="캐시의 실패 행도 다시 부른다")
    ap.add_argument("--refine-only", action="store_true",
                    help="검색 API 로 정제만(JUSO_SEARCH_KEY 하나) — 상태 REFINED")
    ap.add_argument("--limit", type=int, default=0, help="이번에 부를 최대 수(0=전부)")
    ap.add_argument("--summary", action="store_true", help="검증 요약만")
    ap.add_argument("--sample", type=int, default=0, help="채팅 대조용 무작위 N건(시드 고정)")
    ap.add_argument("--crosscheck-vworld", type=int, default=0,
                    help="무작위 N건을 브이월드와 거리 대조(좌표는 저장하지 않는다)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.inp:
        ap.error("--in 이 필요하다")

    load_env()
    keys = get_keys()
    addrs = read_input(a.inp, a.col)
    cache = read_cache()
    fetch = http_get_json

    try:
        if not (a.summary or a.sample or a.crosscheck_vworld):
            todo_addrs = addrs
            if a.limit:
                pend = pending(addrs, cache, a.retry_failed, a.refine_only)
                todo_addrs = [x for x in addrs if x not in pend] + pend[:a.limit]
            c, h, t = run(todo_addrs, cache, keys, fetch, dry_run=a.dry_run,
                          retry_failed=a.retry_failed, save=None if a.dry_run else write_cache,
                          refine_only=a.refine_only)
            print("고유 원주소 %d · 캐시 적중 %d · %s %d"
                  % (len(addrs), h, "부를 것" if a.dry_run else "부른 것", t if a.dry_run else c))
            print("키: %s" % " · ".join("%s=%s" % (k, "있음" if v else "없음") for k, v in keys.items()))
        s = summarize(addrs, cache)
        print_summary(s)
        if a.sample:
            print("── 채팅 대조용 무작위 %d건 (시드 %d) ──" % (a.sample, SAMPLE_SEED))
            for i, r in enumerate(pick_sample(s, a.sample), 1):
                print("  %2d. %s | %s | %s, %s" % (i, r["원주소"], r["정제주소"], r["위도"], r["경도"]))
        if a.crosscheck_vworld:
            print("── 브이월드 거리 대조 (저장 안 함) ──")
            crosscheck_vworld(pick_sample(s, a.crosscheck_vworld), keys, fetch)
    except StopError as e:
        print("멈춤: %s" % mask(e, keys))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

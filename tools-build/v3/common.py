"""v3 수집 공통 — HTTP(재시도 · 정직한 UA) · 키 가리기 · JSON 쓰기. 키 값은 어디에도 찍지 않는다."""
import json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = "Mozilla/5.0 (X11; Linux x86_64) sounding-v3-collect/1.0 (+https://github.com/jisangj03-dev/incheon-port-analysis)"
KEY = os.environ.get("DATA_GO_KR_KEY", "")
DART_KEY = os.environ.get("OPENDART_KEY", "")  # OpenDART(③-나) — 이것도 어디에도 찍지 않는다


def scrub(s):
    s = str(s)
    for K in (KEY, DART_KEY):
        if K:
            for k in {K, urllib.parse.quote(K, safe=""), urllib.parse.quote_plus(K)}:
                s = s.replace(k, "***")
    return re.sub(r"((?:serviceKey|crtfc_key)=)[^&\s\"']+", r"\1***", s, flags=re.I)


def get(url, params=None, tries=3, timeout=60, binary=False, headers=None):
    if params: url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko,en", **(headers or {})})
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                return r.status, (b if binary else b.decode("utf-8", "replace"))
        except Exception as e:
            err = getattr(e, "code", None) or scrub(str(e))[:160]
            time.sleep(2 * (i + 1))
    return err, (b"" if binary else "")


def jget(url, params=None, **kw):
    st, body = get(url, params, **kw)
    try: return st, json.loads(body)
    except Exception: return st, None


def write(rel, obj):
    p = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1 if not isinstance(obj, dict) or len(json.dumps(obj)) < 400000 else None)
    print(f"→ {rel} ({os.path.getsize(p) // 1024}KB)")


def say(*a):
    print(scrub(" ".join(str(x) for x in a)), flush=True)

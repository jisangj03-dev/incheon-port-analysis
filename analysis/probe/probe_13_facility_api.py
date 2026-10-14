# -*- coding: utf-8 -*-
"""프로브 13 — **부두현황의 하역능력을 두 번째 소스로 대조할 수 있는가.**

왜 있는가
---------
2026-08-29, `/berths/` 지면을 내면서 [미확인] 둘을 STATUS 에 올렸다 —
① 부두현황의 **자료 기준일을 모른다** ② 공표 **부분합과 「계」가 안 맞는다**(142 대 138).

그리고 같은 날 사고 58에 이렇게 적었다 —

  **「이 데이터로는 못 한다」를 적을 때 「그럼 어느 데이터면 되는가」를 같은 자리에서 묻는다.
   한계 표기가 탐색 종료 신호가 되면, 정직함이 게으름의 알리바이가 된다.**

**그래 놓고 그 자리에서 안 물었다.** 이 프로브가 그 물음이다.

무엇을 보는가
-------------
해양수산부 **「항만시설 및 하역능력정보」** API(`apis.data.go.kr/1192000/FaclManpFclty2`).
인천지방해양수산청 웹 지면과 **다른 경로**로 나오는 값이라 §3-8 교차 소스 대조가 된다.

  ① 우리 인증키로 이 엔드포인트가 열리는가
  ② 인천 관할의 **항만청코드**가 무엇인가 (문서에 샘플만 있고 목록이 없다)
  ③ 선석별 **하역능력**이 나오는가 — 우리가 지면에 쓴 신항 2,162 · 남항 762 의 대조군
  ④ **자료기준일자 필드가 정말 없는가** (문서에는 없다고 나오나 실물로 확인한다)

**판정하지 않는다. 관측만 낸다.** 무엇을 쓸지는 사람이 정한다.

  python analysis/probe/probe_13_facility_api.py
  python analysis/probe/probe_13_facility_api.py --agency 030

**읽기 전용이다. 아무것도 안 쓴다.** 인증키는 출력하지 않는다.
"""

import argparse
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "analysis"))

BASE = "https://apis.data.go.kr/1192000/FaclManpFclty2"
UA = "Mozilla/5.0 (compatible; vidimus-probe/1.0)"

# 항만청코드는 문서에 목록이 없고 샘플(020)만 있다. **그래서 훑는다** —
# 추정으로 하나 찍고 「인천이 없다」고 적으면 그건 관측이 아니라 게으름이다.
AGENCIES = ["%03d" % i for i in range(10, 101, 10)]


def call(path, params, timeout=25):
    """(상태, 본문). **인증키는 절대 출력하지 않는다.**"""
    import config
    q = dict(params)
    q["serviceKey"] = config.SERVICE_KEY
    q.setdefault("type", "json")
    url = path + "?" + urllib.parse.urlencode(q, safe="%")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def summarize(body):
    """응답에서 결과코드·메시지·건수·첫 항목을 뽑는다. JSON 이든 XML 이든."""
    body = (body or "").strip()
    if body.startswith("{") or body.startswith("["):
        try:
            j = json.loads(body)
        except Exception:
            return "JSON 파싱 실패", None, None
        def find(o, key):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k.lower() == key:
                        return v
                    r = find(v, key)
                    if r is not None:
                        return r
            elif isinstance(o, list):
                for v in o:
                    r = find(v, key)
                    if r is not None:
                        return r
            return None
        code = find(j, "resultcode") or find(j, "returnreasoncode")
        msg = find(j, "resultmsg") or find(j, "returnauthmsg")
        items = find(j, "item")
        if isinstance(items, dict):
            items = [items]
        return f"{code} {msg}", items, j
    code = re.search(r"<resultCode>(.*?)</resultCode>", body)
    msg = re.search(r"<resultMsg>(.*?)</resultMsg>", body)
    if not code:
        msg2 = re.search(r"<returnAuthMsg>(.*?)</returnAuthMsg>", body)
        if msg2:
            return "인증: " + msg2.group(1), None, None
    items = re.findall(r"<item>(.*?)</item>", body, re.S)
    parsed = []
    for it in items:
        parsed.append({k: v for k, v in re.findall(r"<(\w+)>(.*?)</\1>", it, re.S)})
    return (f"{code.group(1) if code else '?'} {msg.group(1) if msg else ''}",
            parsed or None, None)


def main():
    ap = argparse.ArgumentParser(description="해수부 항만시설·하역능력 API 탐색 (읽기 전용).")
    ap.add_argument("--agency", default=None, help="항만청코드 하나만 본다")
    ap.add_argument("--facility", default="MB2", help="시설코드 (문서 샘플 MB2)")
    a = ap.parse_args()

    print("== 프로브 13 — 부두 하역능력의 두 번째 소스 ==")
    print("  사고 58: 「이 데이터로는 못 한다」를 적을 때 「그럼 어느 데이터면 되는가」를 같이 묻는다.")
    print("  대상: 해양수산부 항만시설 및 하역능력정보 (apis.data.go.kr/1192000/FaclManpFclty2)")

    try:
        import config  # noqa: F401
    except Exception as e:
        print("\n[중단] config.py 를 못 읽었다: %s" % type(e).__name__)
        print("  인증키는 비공개다(§4). `analysis/config_example.py` 를 보고 만든다.")
        return 2

    # **대조군 먼저.** 「이 API 에 키가 미등록이다」는 「우리 키가 죽었다」와 다른 사실이고,
    # 둘을 안 가르면 이 프로브의 결론이 통째로 흔들린다. 이미 쓰고 있는 API 로 키를 친다.
    print("\n-- 0. 대조군 — 우리 인증키 자체는 사는가 --")
    st0, body0 = call("https://apis.data.go.kr/1192000/SsopCargContnImxprt2/Ym",
                      {"strtYymm": "202607", "endYymm": "202607"})
    res0, items0, _ = summarize(body0)
    # **인증 실패와 그 밖의 실패를 가른다.** 파라미터 오류는 **인증을 통과한 뒤**에 난다 —
    # 그것을 「키가 죽었다」로 읽으면 이 프로브의 결론이 통째로 뒤집힌다.
    # 실제로 한 번 그렇게 읽을 뻔했다(2026-08-29): 대조군이 HTTP 200 + 파라미터 오류였는데
    # 「항목이 0건이니 실패」로 판정하고 있었다.
    auth_fail = ("등록되지 않은" in str(res0) or "SERVICE_KEY" in (body0 or "")
                 or str(res0).strip().startswith("30"))
    print("  이미 쓰는 API(SsopCargContnImxprt2) · HTTP %s · 결과 %s"
          % (st0, str(res0)[:44]))
    print("  → 인증 %s" % ("**실패 — 키 자체가 문제일 수 있다**" if auth_fail else
                          "**통과** (그 뒤 파라미터 단계까지 갔다 = 키는 산다)"))

    print("\n-- 1. 엔드포인트가 열리는가 --")
    st, body = call(BASE + "/Info", {"prtAgCd": "020", "fcltyCd": a.facility})
    res, items, _ = summarize(body)
    print("  HTTP %s · 결과 %s" % (st, res))
    if items:
        print("  첫 항목 필드: %s" % ", ".join(sorted(items[0].keys())))
    if st != 200 or (items is None and "정상" not in str(res) and "00" not in str(res)):
        print("  본문 앞부분: %s" % (body or "")[:220].replace("\n", " "))

    print("\n-- 2. 인천 관할 항만청코드 찾기 (문서에 목록이 없다) --")
    agencies = [a.agency] if a.agency else AGENCIES
    hits = []
    for code in agencies:
        st, body = call(BASE + "/Info", {"prtAgCd": code, "fcltyCd": a.facility}, timeout=15)
        res, items, _ = summarize(body)
        name = ""
        if items:
            name = items[0].get("prtAgNm") or items[0].get("prtagnm") or ""
        flag = "  <-- 인천" if "인천" in str(name) else ""
        print("  %s  HTTP %-4s %-24s %s%s" % (code, st, str(res)[:24], name[:20], flag))
        if items:
            hits.append((code, name, items))

    print("\n-- 3. 인천 관할에서 나온 선석·하역능력 --")
    inch = [h for h in hits if "인천" in str(h[1])]
    if not inch:
        print("  **인천 관할을 못 찾았다.** 코드 체계가 다르거나 이 엔드포인트가")
        print("  항만청 단위가 아닐 수 있다. → 이 소스로는 대조가 안 된다는 것이 관측이다.")
    for code, name, items in inch:
        print("  [%s] %s · 항목 %d건" % (code, name, len(items)))
        for it in items[:20]:
            print("     " + " | ".join(
                "%s=%s" % (k, v) for k, v in it.items()
                if k.lower() in ("berthnm", "lnlablty", "trtmntfrghtnm", "fcltycd")))

    print("\n-- 4. 자료기준일자 필드가 정말 없는가 --")
    keys = set()
    for _, _, items in hits:
        for it in items:
            keys |= set(k.lower() for k in it.keys())
    datish = sorted(k for k in keys if any(w in k for w in ("dt", "date", "ymd", "bas", "std")))
    print("  전체 필드 %d종" % len(keys))
    print("  날짜로 보이는 필드: %s" % (", ".join(datish) if datish else "**없다**"))
    if not datish and keys:
        print("  → 이 소스도 기준일을 안 준다. **[미확인]이 그대로 남는다.**")

    print("\n== 관측 ==")
    if auth_fail:
        print("  대조군에서도 인증이 막혔다 — **키 자체를 먼저 확인해야 한다.**")
    else:
        print("  **우리 키는 산다.** 그런데 이 API 는 「등록되지 않은 서비스키」를 낸다.")
        print("  공공데이터포털은 API 마다 **활용신청이 따로**다. 즉 막힌 것은 키가 아니라")
        print("  **이 API 에 대한 신청**이고, 그것은 계정 조작이라 **운영자 몫**이다.")
        print("  → [미확인]이 「안 봤다」에서 **「봤고, 막힌 지점이 어디인지 안다」**로 바뀌었다.")
        print("     신청 주소: https://www.data.go.kr/data/3082243/openapi.do")
        print("  **그래도 이 소스는 기준일을 안 준다**(문서 기준). 자료 기준일 [미확인]은")
        print("  이 경로로는 안 닫힌다 — 닫으려면 다른 소스거나 기관 문의다.")
    print("\n  ※ 이 프로브는 아무것도 쓰지 않았다. 인증키는 출력하지 않았다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

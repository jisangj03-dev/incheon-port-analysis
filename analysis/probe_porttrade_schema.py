"""관세청 항구·공항별 수출입실적 — 스키마 프로브. 값은 마스킹한다.

왜 있는가
---------
게이트 ①이 열린 직후, 게이트 ②(개시 선커밋)를 쓰려면 **실제로 어떤 필드가 오는지**를
알아야 한다. 개시 게이트 문서가 이미 그렇게 적었다 —
*「어떤 필드가 실제로 오는지, 항만 코드가 인천을 어떻게 가리키는지, 월별 입도가 되는지
전부 실호출로만 알 수 있다.」*

동시에 **값을 보면 안 된다.** 값을 본 뒤에 쓰는 질문은 선커밋이 아니다(사고 8·21).

그래서 이 프로브는 **축은 보여 주고 값은 가린다.**
  * 태그명 · 태그 개수 · 행 수 · 월별 도달 여부  → 그대로 출력
  * 필드 내용                                     → 길이와 종류(숫자/문자)만 출력
  * 차원 라벨(항만 코드·항만명 등 DIMENSION 지정분) → 그대로 출력. 이것은 값이 아니라 축이다

**마스킹은 스크립트가 한다.** 사람이 "안 보겠다"고 다짐하는 방식은 방어가 아니다(사고 30).

사용
----
  python analysis/probe_porttrade_schema.py            # 1행 스키마 + 월 입도
  python analysis/probe_porttrade_schema.py --dims     # 차원 라벨 수집(항만 코드 축)
  python analysis/probe_porttrade_schema.py --structure # 응답 골격·페이징·집계행 확인

종료코드 0 = 응답 정상 / 1 = 응답 이상 / 2 = config 없음.
"""

import argparse
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import config
except ImportError:
    print("[중단] analysis/config.py 가 없다.")
    sys.exit(2)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

URL = "https://apis.data.go.kr/1220000/porttrade/getPorttradeList"

# 축(차원) 라벨로 취급해 그대로 출력할 태그. 값이 아니라 이름·코드다.
# 첫 실행(2026-08-26)에서 태그 9종을 확인한 뒤 지정했다.
# year·portCd·cstmSgn·statKor 는 축 라벨이다 — 기간과 대상을 가리키지, 실적값이 아니다.
# 나머지 5종(expCnt·expDlr·impCnt·impDlr·balPayments)이 값이고, 계속 가린다.
DIMENSION = {"year", "portCd", "cstmSgn", "statKor"}


def fetch(params):
    p = dict(params)
    p["serviceKey"] = config.SERVICE_KEY
    q = URL + "?" + urllib.parse.urlencode(p, safe="%")
    try:
        req = urllib.request.Request(q, headers={"User-Agent": "probe"})
        with urllib.request.urlopen(req, timeout=25, context=CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def mask(tag, val):
    """값을 가린다. 축으로 지정된 태그만 그대로 낸다."""
    if tag in DIMENSION:
        return val
    v = val.strip()
    if v == "":
        return "(빈값)"
    kind = "숫자" if re.fullmatch(r"-?[\d,\.]+", v) else "문자"
    return f"···{kind} {len(v)}자"


def items(body):
    """<item>…</item> 블록을 태그명 기준으로 뜯는다. 위치 인덱스 금지(사고 1)."""
    out = []
    for blk in re.findall(r"<item>(.*?)</item>", body, re.S):
        out.append(re.findall(r"<([A-Za-z_][\w]*)>([^<]*)</\1>", blk))
    return out


def head(body):
    code = re.search(r"<(?:resultCode|returnReasonCode)>([^<]*)<", body)
    msg = re.search(r"<(?:resultMsg|returnAuthMsg|errMsg)>([^<]*)<", body)
    tot = re.search(r"<totalCount>([^<]*)<", body)
    return (code.group(1) if code else "-",
            msg.group(1) if msg else "-",
            tot.group(1) if tot else "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dims", action="store_true", help="차원 라벨 수집")
    ap.add_argument("--structure", action="store_true", help="페이징·집계행·잔여범주 확인")
    ap.add_argument("--month", default="202601")
    ap.add_argument("--rows", default="1")
    a = ap.parse_args()

    print("── 항구·공항별 수출입실적 스키마 프로브 (값 마스킹) ──")
    st, body = fetch({"strtYymm": a.month, "endYymm": a.month, "numOfRows": a.rows})
    code, msg, tot = head(body)
    print(f"  요청  strtYymm={a.month} endYymm={a.month} numOfRows={a.rows}  (portCd 미지정)")
    print(f"  응답  HTTP {st}   code={code}   msg={msg}   totalCount={tot}")

    rows = items(body)
    if not rows:
        print("  <item> 없음 — 응답 골격을 확인해야 한다. 상위 태그만 출력한다:")
        for t in dict.fromkeys(re.findall(r"<([A-Za-z_][\w]*)>", body)):
            print(f"    <{t}>")
        sys.exit(1)

    print(f"\n  태그 {len(rows[0])}종 (첫 행 기준. 값은 마스킹)")
    for tag, val in rows[0]:
        print(f"    {tag:<24} {mask(tag, val)}")

    if a.dims:
        print("\n  ── 차원 라벨 수집 ──")
        seen = {}
        for r in items(fetch({"strtYymm": a.month, "endYymm": a.month,
                              "numOfRows": "200"})[1]):
            d = dict(r)
            key = tuple(d.get(t, "") for t in sorted(DIMENSION))
            seen.setdefault(key, 0)
            seen[key] += 1
        print(f"    DIMENSION={sorted(DIMENSION) or '(미지정)'} · 조합 {len(seen)}종")
        for k, n in sorted(seen.items())[:60]:
            print(f"      {' | '.join(k)}   ({n}행)")

    if a.structure:
        print()
        print("  ── 페이징 (numOfRows가 먹는가) ──")
        for n in ("1", "10", "200", "99999"):
            b = fetch({"strtYymm": a.month, "endYymm": a.month, "numOfRows": n})[1]
            print(f"    numOfRows={n:<6} 반환 행 {len(items(b))}")
        print("    ※ totalCount 태그가 응답에 없다 — 완결성 확인(사고 3)을 다른 방법으로 해야 한다")

        rows = items(fetch({"strtYymm": a.month, "endYymm": a.month, "numOfRows": "99999"})[1])
        ds = [dict(r) for r in rows]
        print()
        print("  ── 집계행·잔여범주 (합산 전에 걸러야 할 것) ──")
        agg = [d for d in ds if d.get("cstmSgn") == "-" or d.get("portCd") == "-"]
        print(f"    전체 {len(ds)}행 중 축이 '-'인 행 {len(agg)}건")
        for d in agg[:10]:
            print(f"      cstmSgn={d.get('cstmSgn')} portCd={d.get('portCd')} statKor={d.get('statKor')}")
        resid = sorted({d.get("statKor") or "" for d in ds
                        if any(k in (d.get("statKor") or "") for k in ("기타", "총계", "미상"))})
        print(f"    잔여·집계 라벨: {resid}")

        print()
        print("  ── 인천항(KRINC) 분해 ──")
        inc = [d for d in ds if d.get("portCd") == "KRINC"]
        seals = sorted({d["cstmSgn"] for d in inc})
        print(f"    KRINC 행 {len(inc)}건 · 세관부호 {len(seals)}종 → {seals}")
        print("    ※ 인천국제공항(ICN)·경인항(KRGIN)은 별개 코드다. 인천항은 KRINC 하나다")

    print("\n  ── 월별 도달 (행 수만 본다) ──")
    # code=00 이 데이터 존재를 뜻하지 않는다(사고 3·5). 행 수와 인천항 유무를 함께 본다.
    for m in ("202412", "202512", "202601", "202603", "202606", "202607"):
        s2, b2 = fetch({"strtYymm": m, "endYymm": m, "numOfRows": "1"})
        c2, _, t2 = head(b2)
        rs = [dict(r) for r in items(b2)]
        inc = sum(1 for d in rs if d.get("portCd") == "KRINC")
        print(f"    {m}  HTTP {s2}  code={c2}  totalCount={t2}  행 {len(rs):>4}  KRINC {inc:>3}")


if __name__ == "__main__":
    main()

"""무역 라인 소스 프로브 — 값 비노출. 개통 여부만 본다.

왜 있는가
---------
지침 §5.0 게이트 ①은 **실파일 원칙**이다 — 정의문·소개 페이지·"자동승인" 표기를
신뢰하지 않고 실제로 호출해 본다(사고 8). 무역 라인은 관세청 API 2종에 걸려 있고,
2026-08-25·08-26 두 번의 실측에서 모두 막혀 있었다.

이 스크립트는 **활용신청이 승인되면 바로 돌려 게이트 ①을 판정**하기 위한 것이다.
출력은 도달 여부·응답 코드·행 수까지다. **값은 찍지 않는다**(사고 21 프로브 원칙) —
값을 보는 순간 그 구간에 선커밋을 걸 수 없게 된다.

대조군을 함께 호출한다. 이미 개통된 인천항 공컨 API가 정상이면
「키·네트워크는 멀쩡하고 관세청만 막혀 있다」가 성립한다. 대조군이 없으면
실패 원인을 키 탓인지 서비스 탓인지 가를 수 없다.

사용
----
  python analysis/probe_customs.py

종료코드 0 = 2종 모두 개통(게이트 ① 통과) / 1 = 아직 막힘 / 2 = 대조군까지 실패.
"""

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
    print("[중단] analysis/config.py 가 없다. 인증키 파일은 .gitignore 대상이다.")
    sys.exit(2)

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

TARGETS = [
    ("관세청 항구·공항별 수출입실적",
     "https://apis.data.go.kr/1220000/porttrade/getPorttradeList",
     {"strtYymm": "202601", "endYymm": "202601", "portCd": "020", "numOfRows": "1"}),
    ("관세청 세관장확인대상물품",
     "https://apis.data.go.kr/1220000/retrieveCcctLworCd/getRetrieveCcctLworCd",
     {"hsSgn": "8471300000", "numOfRows": "1"}),
]
CONTROL = ("대조군 · 인천항 공컨(개통 확인됨)",
           "https://apis.data.go.kr/B551504/ipaEmpConCargoInfo/getEmpConCargoInfo",
           {"searchYear": "2025", "searchStartM": "01", "searchEndM": "01", "numOfRows": "1"})


def call(url, params):
    """반환: (상태문자열, 응답코드, totalCount). 값은 절대 반환하지 않는다."""
    p = dict(params)
    p["serviceKey"] = config.SERVICE_KEY
    q = url + "?" + urllib.parse.urlencode(p, safe="%")
    try:
        req = urllib.request.Request(q, headers={"User-Agent": "probe"})
        with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
            body = r.read().decode("utf-8", "replace")
            status = f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}", "-", "-"
    except Exception as e:
        return f"{type(e).__name__}", "-", "-"

    code = re.search(r"<(?:resultCode|returnReasonCode)>([^<]*)<", body)
    total = re.search(r"<totalCount>([^<]*)<", body)
    return status, (code.group(1) if code else "-"), (total.group(1) if total else "-")


def main():
    print("── 무역 라인 소스 프로브 (값 비노출) ──")
    ok = 0
    for name, url, params in TARGETS:
        st, code, total = call(url, params)
        good = st == "HTTP 200" and code in ("00", "0")
        ok += good
        print(f"  [{'개통' if good else '막힘'}] {name:<28} {st:<12} code={code:<4} rows={total}")

    name, url, params = CONTROL
    st, code, total = call(url, params)
    ctrl_ok = st == "HTTP 200" and code in ("00", "0")
    print(f"  [{'정상' if ctrl_ok else '실패'}] {name:<28} {st:<12} code={code:<4} rows={total}")

    print()
    if not ctrl_ok:
        print("대조군이 실패했다. 키·네트워크부터 확인한다 — 관세청 결과는 판정 불가다.")
        sys.exit(2)
    if ok == len(TARGETS):
        print("게이트 ① 통과 — 2종 모두 실호출 성공. 무역 라인 착수 조건 하나가 풀렸다.")
        print("다음: docs/무역라인_개시게이트.md 의 게이트 ②~⑤를 채운다.")
        sys.exit(0)
    print(f"게이트 ① 미통과 — {len(TARGETS) - ok}/{len(TARGETS)}종이 막혀 있다.")
    print("대조군이 정상이므로 키·네트워크 문제가 아니다. 활용신청 승인이 선행이다.")
    print("**실호출이 성공하기 전에는 주제를 확정하지 않는다**(설계 §5.3).")
    sys.exit(1)


if __name__ == "__main__":
    main()

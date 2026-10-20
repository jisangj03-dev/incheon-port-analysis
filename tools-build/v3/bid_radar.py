"""입찰 레이더 — 조달청 나라장터 입찰공고(용역) 중 물류·무역 공고를 빌드 때 스냅샷으로(선커밋 docs/측심_전권위임_단계기준_선커밋_20261015.md ③-가).
키 = DATA_GO_KR_KEY(Actions 빌드 때만 · 지면 실행 중 0). 담당자 이름·전화·메일은 받지도 싣지도 않는다(개인정보).
결과: data/derived/bid_radar.json
  python tools-build/v3/bid_radar.py [--selftest]
"""
import datetime, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import ROOT, KEY, get, scrub, say

URL = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
OUT = os.path.join(ROOT, "data/derived/bid_radar.json")
WINDOW = 21
GROUPS = [("운송·배송", ["운송", "화물", "택배", "배송", "물류"]), ("보관·창고", ["보관", "창고", "풀필먼트", "콜드체인", "냉장창고", "냉동창고", "냉동 컨테이너", "냉동컨테이너", "하역"]),
          ("통관·무역", ["통관", "보세", "수출", "수입", "무역", "원산지", "FTA", "공급망", "SCM", "포워딩"]), ("항만·해운·항공", ["항만", "해운", "컨테이너", "항공화물"])]
INCLUDE = [w for _, ws in GROUPS for w in ws]
# [2026-10-20 사실 대조] 「HSCMT」(전자파 시험) 이 「SCM」 부분 일치로 통관·무역에 들어갔고, 「통관대행」 용역이 앞 묶음(운송)에 먼저 걸렸다 →
#   영문 낱말은 앞뒤가 영문이 아닐 때만 맞는다 · 통관·무역의 고유 낱말(통관·보세·원산지·FTA·포워딩)은 다른 묶음보다 먼저 본다
import re as _re
FIRST = ("통관·무역", ["통관", "보세", "원산지", "FTA", "포워딩"])
def has(nm, w):
    return bool(_re.search(rf"(?<![A-Za-z]){_re.escape(w)}(?![A-Za-z])", nm)) if w.isascii() else w in nm
def group_of(nm):
    if any(has(nm, w) for w in FIRST[1]): return FIRST[0]
    return next((gn for gn, ws in GROUPS if any(has(nm, w) for w in ws)), None)
EXCLUDE = ["통학", "여객", "관광", "수학여행", "셔틀", "전세버스", "급식", "폐기물", "음식물", "장애인", "환자", "시신", "운구",
           # 바꿈 2026-10-15(첫 스냅샷을 본 뒤 · 선커밋 ③-가 폐기 규칙): 「홍보관」의 보관 · 제설장비 「창고구간」 · 화물차 임차·리스 · 헬륨냉동 · 방사선감시기
           "홍보관", "제설", "임차", "리스", "헬륨", "방사선",
           # 바꿈 2026-10-15(둘째 · 같은 스냅샷을 다시 본 뒤): 「금속수소화물」의 화물 · 「해운대」의 해운 · 「정보관리」의 보관 · 「수출용신형연구로」 · 수출입은행 유튜브 · 시험 문제지 운송
           "수소화물", "해운대", "정보관", "연구로", "유튜브", "문제지",
           "선거물품"]  # 바꿈 셋째(10/15 채팅 최종 검수 · 데이터 본 뒤): 선거물품 집중보관 3건이 「보관」으로 걸렸다
KEEP = ["bidNtceNo", "bidNtceOrd", "bidNtceNm", "ntceInsttNm", "dminsttNm", "bidNtceDt", "bidClseDt", "presmptPrce", "bidNtceDtlUrl"]


def pick(rows, now):
    out, seen = [], set()
    for r in rows:
        nm = str(r.get("bidNtceNm", ""))
        if group_of(nm) is None or any(w in nm for w in EXCLUDE): continue
        close = str(r.get("bidClseDt") or "")
        if not close or close[:16] <= now.strftime("%Y-%m-%d %H:%M"): continue
        key = r.get("bidNtceNo")  # 같은 공고의 다른 차수는 하나로(뒤 차수가 남는다 — 아래에서 덮어쓴다)
        if key in seen: out = [x for x in out if x["bidNtceNo"] != key]
        seen.add(key)
        g = group_of(nm)
        item = {k: r.get(k) for k in KEEP}
        try: item["presmptPrce"] = int(float(item["presmptPrce"])) if item.get("presmptPrce") not in (None, "") else None
        except ValueError: item["presmptPrce"] = None
        item["group"] = g
        out.append(item)
    return sorted(out, key=lambda x: x["bidClseDt"])


def fetch(now):
    rows = []
    for k in range(0, WINDOW, 7):
        b = (now - datetime.timedelta(days=k + 7)).strftime("%Y%m%d%H%M"); e = (now - datetime.timedelta(days=k)).strftime("%Y%m%d%H%M")
        page = 1
        while True:
            for t in range(4):
                st, body = get(URL, {"serviceKey": KEY, "numOfRows": "999", "pageNo": str(page), "inqryDiv": "1", "inqryBgnDt": b, "inqryEndDt": e, "type": "json"}, timeout=60, tries=1)
                try: d = json.loads(body); break
                except Exception: d = None; time.sleep(3 * (t + 1))
            if not d: say("빈 응답", b, e, page, st); return None
            bd = d.get("response", {}).get("body", {}); items = bd.get("items") or []
            if isinstance(items, dict): items = items.get("item", [])
            rows += items
            if page * 999 >= int(bd.get("totalCount") or 0): break
            page += 1
    return rows


def main():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(tzinfo=None)
    rows = fetch(now)
    # 원천에 못 닿으면(시간 초과 등) 빨강이 아니라 경고 — 지난 파일을 지키고 끝낸다(portwatch·iiac 와 같은 규칙)
    if rows is None: say("::warning::나라장터 원천 질의 실패 — 지난 파일을 지킨다"); return 0
    items = pick(rows, now)
    say("공고", len(rows), "→ 물류·무역", len(items))
    if len(items) < 5: say("5건 미만 — 싣지 않는다(선커밋 폐기 규칙) · 지난 파일 유지"); return 1
    d = {"_설명": "나라장터 입찰공고(용역) 중 물류·무역 공고 — 빌드 때 스냅샷. 고르는 규칙 = 선커밋 ③-가. 담당자 개인정보 칸은 받지 않는다. 목록은 사람이 검수하지 않는다.",
         "source": "조달청 나라장터 입찰공고정보서비스(공공데이터포털 · 용역)", "snapshot": now.strftime("%Y-%m-%d %H:%M"), "window_days": WINDOW,
         "scanned": len(rows), "n": len(items), "group_counts": {g: sum(1 for x in items if x["group"] == g) for g, _ in GROUPS},
         "groups": [g for g, _ in GROUPS], "include": INCLUDE, "exclude": EXCLUDE, "items": items}
    s = json.dumps(d, ensure_ascii=False, indent=1)
    if KEY and KEY in s: say("키가 산출물에 있다 — 쓰지 않는다"); return 1
    open(OUT, "w", encoding="utf-8").write(s)
    return 0


def selftest():
    now = datetime.datetime(2026, 10, 15, 12, 0)
    rows = [{"bidNtceNo": "1", "bidNtceOrd": "000", "bidNtceNm": "2026 수출입 화물 운송 용역", "bidClseDt": "2026-10-20 10:00:00", "presmptPrce": "1000000", "ntceInsttOfclNm": "홍길동"},
            {"bidNtceNo": "2", "bidNtceOrd": "000", "bidNtceNm": "초등학교 통학 버스 운송", "bidClseDt": "2026-10-20 10:00:00"},
            {"bidNtceNo": "3", "bidNtceOrd": "000", "bidNtceNm": "냉동 창고 보관 용역", "bidClseDt": "2026-10-14 10:00:00"},
            {"bidNtceNo": "1", "bidNtceOrd": "001", "bidNtceNm": "2026 수출입 화물 운송 용역", "bidClseDt": "2026-10-21 10:00:00", "presmptPrce": "1000000"},
            {"bidNtceNo": "4", "bidNtceOrd": "000", "bidNtceNm": "해운대 정보관리 시스템 유지보수", "bidClseDt": "2026-10-20 10:00:00"}]
    p = pick(rows, now)
    assert [x["bidNtceNo"] for x in p] == ["1"] and p[0]["group"] == "운송·배송" and "ntceInsttOfclNm" not in p[0] and p[0]["presmptPrce"] == 1000000 and p[0]["bidNtceOrd"] == "001", p
    print("selftest 1/1 ok"); return 0


def regroup():
    """지난 스냅샷을 새 규칙으로 다시 묶는다(원천을 다시 부르지 않는다 — 공고 이름만 쓴다)"""
    d = json.load(open(OUT, encoding="utf-8"))
    d["items"] = [dict(x, group=group_of(x["bidNtceNm"])) for x in d["items"] if group_of(x["bidNtceNm"])]
    d["n"] = len(d["items"]); d["group_counts"] = {g: sum(1 for x in d["items"] if x["group"] == g) for g, _ in GROUPS}
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("다시 묶음", d["group_counts"]); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else regroup() if "--regroup" in sys.argv else main())

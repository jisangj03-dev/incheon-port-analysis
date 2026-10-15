"""인천 물류기업 카드(③-나) — OpenDART 공시 수치만. 고르는 규칙 = 선커밋 docs/측심_전권위임_단계기준_선커밋_20261015.md 「③-나 상세」(여기서 바꾸지 않는다).

모집단 = 지난 12개월 사업보고서(A001)를 낸 법인 → 기업개황 본점 「인천」 ∩ 업종코드 앞 두 자리 49·50·51·52 → 최근 사업보고서 주요계정 넷.
싣지 않는 칸(대표자·임원·전화·홈페이지·상세 주소·등록번호)은 받은 즉시 버린다. 5곳 미만이면 곳 수만 적고 싣지 않는다(ok=false).
키 = 환경 변수 OPENDART_KEY(Actions 비밀) · 어디에도 찍지 않는다. 하루 5천 회 안.
  python dart_firms.py            수집(Actions)
  python dart_firms.py --selftest 규칙 시험(키·네트워크 없이)
"""
import datetime, json, os, re, sys, time
from common import ROOT, DART_KEY, jget, scrub, say

API = "https://opendart.fss.or.kr/api"
OUT = os.path.join(ROOT, "data/derived/incheon_firms.json")
CAP = 5000  # 하루 호출 상한(선커밋 — 한도 2만의 4분의 1)
MIN_N = 5
DIV = {"49": "육상 운송 및 파이프라인 운송업", "50": "수상 운송업", "51": "항공 운송업", "52": "창고 및 운송관련 서비스업"}
CLS = {"Y": "유가증권시장", "K": "코스닥", "N": "코넥스", "E": "비상장(사업보고서 제출)"}
ACCTS = [("revenue", ("매출액", "영업수익", "수익(매출액)")), ("op", ("영업이익",)), ("net", ("당기순이익",)), ("assets", ("자산총계",))]
calls = 0


class Stop(Exception):
    pass


def call(path, **p):
    global calls
    if calls >= CAP: raise Stop("하루 호출 상한(5천) — 멈춘다")
    calls += 1
    st, d = jget(f"{API}/{path}", {"crtfc_key": DART_KEY, **p}, timeout=40)
    if not isinstance(d, dict): raise Stop(f"응답 없음 {path} {st}")
    s = d.get("status")
    if s in ("010", "011", "012", "020", "021", "800", "901"): raise Stop(f"OpenDART 상태 {s} {d.get('message', '')}")  # 키·한도·점검
    time.sleep(0.12)
    return d


def windows(now, months=12, step=90):
    """지난 12개월을 3개월(90일) 창으로 — 회사를 정하지 않은 공시 검색은 3개월까지만 된다"""
    end, start, out = now.date(), now.date() - datetime.timedelta(days=365), []
    while end > start:
        b = max(start, end - datetime.timedelta(days=step - 1)); out.append((b, end)); end = b - datetime.timedelta(days=1)
    return out


def filers(now):
    """지난 12개월 사업보고서 접수 — 법인마다 가장 최근 하나"""
    last = {}
    for b, e in windows(now):
        page = 1
        while True:
            d = call("list.json", bgn_de=b.strftime("%Y%m%d"), end_de=e.strftime("%Y%m%d"), pblntf_detail_ty="A001", last_reprt_at="Y", page_no=page, page_count=100)
            if d.get("status") == "013": break  # 자료 없음
            for x in d.get("list", []):
                if not re.match(r"사업보고서", x.get("report_nm", "").replace("[기재정정]", "").strip()): continue
                c = x["corp_code"]
                if c not in last or x["rcept_dt"] > last[c]["rcept_dt"]: last[c] = x
            if page >= int(d.get("total_page") or 1): break
            page += 1
    return last


def keep(info):
    """기업개황 → 고르는 규칙 · 싣는 칸만(대표자·전화·홈페이지·상세 주소·등록번호는 여기서 버린다)"""
    adres, code = (info.get("adres") or "").strip(), (info.get("induty_code") or "").strip()
    if not adres.startswith("인천") or code[:2] not in DIV: return None
    m = re.match(r"인천(?:광역시)?\s+(\S+?[구군])(?:\s|$)", adres)
    return {"corp_code": info["corp_code"], "name": info.get("corp_name", "").strip(), "cls": CLS.get(info.get("corp_cls"), info.get("corp_cls")),
            "stock_code": (info.get("stock_code") or "").strip() or None, "induty_code": code, "division": DIV[code[:2]],
            "gu": m.group(1) if m else None, "acc_mt": info.get("acc_mt")}


def num(v):
    v = (v or "").replace(",", "").strip()
    return int(v) if re.fullmatch(r"-?\d+", v) else None


def accounts(rows):
    """주요계정 — 연결(CFS)이 있으면 연결, 없으면 별도(OFS). 이름 그대로 옮긴다(계산하지 않는다)"""
    fs = "CFS" if any(r.get("fs_div") == "CFS" for r in rows) else "OFS"
    rows = [r for r in rows if r.get("fs_div") == fs]
    out = {"fs": "연결" if fs == "CFS" else "별도"}
    for k, names in ACCTS:
        r = next((r for n in names for r in rows if (r.get("account_nm") or "").replace(" ", "").startswith(n)), None)
        out[k] = None if r is None else {"label": r["account_nm"].strip(), "now": num(r.get("thstrm_amount")), "prev": num(r.get("frmtrm_amount")),
                                         "now_term": r.get("thstrm_nm"), "prev_term": r.get("frmtrm_nm")}
    return out


def year_of(report_nm):
    m = re.search(r"\((\d{4})\.(\d{2})\)", report_nm or "")
    return (int(m.group(1)) if m else None), (m.group(2) if m else None)


def build(now, last, infos, fin):
    firms = []
    for c, x in last.items():
        k = infos.get(c) and keep(infos[c])
        if not k: continue
        y, mm = year_of(x.get("report_nm"))
        k.update({"bsns_year": y, "period_end": f"{y}.{mm}" if y else None, "report": x.get("report_nm", "").strip(), "rcept_no": x["rcept_no"],
                  "rcept_dt": f"{x['rcept_dt'][:4]}-{x['rcept_dt'][4:6]}-{x['rcept_dt'][6:]}", "url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={x['rcept_no']}",
                  "accounts": fin.get(c)})
        firms.append(k)
    firms.sort(key=lambda f: f["name"])
    ok = len(firms) >= MIN_N
    d = {"_설명": "인천 물류기업 카드(③-나) — OpenDART 공시 수치를 옮긴 것. 투자 권유 아님 · 정본은 공시 원문. 고르는 규칙 = 선커밋 ③-나 상세. 대표자·임원·전화·홈페이지·상세 주소는 받은 즉시 버렸다.",
         "source": "금융감독원 전자공시 OpenDART(기업개황 · 공시검색 · 단일회사 주요계정)", "snapshot": now.strftime("%Y-%m-%d %H:%M"),
         "universe": "지난 12개월 사업보고서(A001) 제출 법인", "filers": len(last), "rule": {"sido": "인천", "ksic2": DIV}, "n": len(firms), "min_n": MIN_N, "ok": ok}
    if ok: d["firms"] = firms
    else: d["reason"] = f"인천·물류에 걸린 법인 {len(firms)}곳 — {MIN_N}곳 미만이라 싣지 않는다(선커밋 폐기 규칙)"
    return d


def main():
    if not DART_KEY: say("::warning::OPENDART_KEY 없음 — 지난 파일을 지킨다"); return 0
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).replace(tzinfo=None)
    try:
        last = filers(now); say("사업보고서 제출 법인", len(last), "· 호출", calls)
        infos = {}
        for c in last:
            d = call("company.json", corp_code=c)
            if d.get("status") == "000": infos[c] = {k: d.get(k) for k in ("corp_code", "corp_name", "corp_cls", "stock_code", "adres", "induty_code", "acc_mt")}  # 싣는 칸에 쓸 것만 남긴다
        hit = [c for c in last if infos.get(c) and keep(infos[c])]
        say("인천·물류", len(hit), "· 호출", calls)
        fin = {}
        for c in hit:
            y, _ = year_of(last[c].get("report_nm"))
            if not y: continue
            # 결산월이 12월이 아니면 사업연도 표기가 보고서 이름의 해와 다를 수 있다 [미확인] → 비면 한 해 앞을 한 번 더
            for yy in (y, y - 1):
                d = call("fnlttSinglAcnt.json", corp_code=c, bsns_year=yy, reprt_code="11011")
                rows = d.get("list", []) if d.get("status") == "000" else []
                if rows: fin[c] = {**accounts(rows), "bsns_year": yy, "rcept_no": rows[0].get("rcept_no")}; break
    except Stop as e:
        say(f"::warning::OpenDART 수집 중단 — {scrub(e)} · 지난 파일을 지킨다"); return 0
    d = build(now, last, infos, fin)
    s = json.dumps(d, ensure_ascii=False, indent=1)
    if DART_KEY in s: say("키가 산출물에 있다 — 쓰지 않는다"); return 1
    open(OUT, "w", encoding="utf-8").write(s)
    say(f"→ data/derived/incheon_firms.json · {d['n']}곳 · ok={d['ok']} · 호출 {calls}")
    return 0


def selftest():
    now = datetime.datetime(2026, 10, 15, 12, 0)
    w = windows(now); assert len(w) == 5 and all((e - b).days < 90 for b, e in w) and w[-1][0] == (now.date() - datetime.timedelta(days=365)), w
    base = {"corp_cls": "Y", "stock_code": "000000", "acc_mt": "12", "ceo_nm": "홍길동", "phn_no": "032-000-0000", "hm_url": "x", "jurir_no": "1", "bizr_no": "2"}
    infos = {str(i): {**base, "corp_code": str(i), "corp_name": f"회사{i}", "adres": "인천광역시 중구 서해대로 1", "induty_code": "52941"} for i in range(5)}
    infos["9"] = {**base, "corp_code": "9", "corp_name": "서울물류", "adres": "서울특별시 중구", "induty_code": "52941"}
    infos["8"] = {**base, "corp_code": "8", "corp_name": "인천제조", "adres": "인천광역시 남동구", "induty_code": "29"}
    k = keep(infos["0"]); assert k["gu"] == "중구" and k["division"] == "창고 및 운송관련 서비스업" and not any(x in json.dumps(k, ensure_ascii=False) for x in ("홍길동", "032-", "서해대로")), k
    assert keep(infos["9"]) is None and keep(infos["8"]) is None
    last = {c: {"corp_code": c, "report_nm": "사업보고서 (2025.12)", "rcept_no": f"2026031400{c}", "rcept_dt": "20260314"} for c in infos}
    rows = [{"fs_div": "OFS", "account_nm": "매출액", "thstrm_amount": "1,000", "frmtrm_amount": "900"}, {"fs_div": "CFS", "account_nm": "매출액", "thstrm_amount": "2,000", "frmtrm_amount": "1,800"},
            {"fs_div": "CFS", "account_nm": "당기순이익(손실)", "thstrm_amount": "-5", "frmtrm_amount": "3"}]
    a = accounts(rows); assert a["fs"] == "연결" and a["revenue"]["now"] == 2000 and a["net"]["now"] == -5 and a["op"] is None, a
    d = build(now, last, infos, {"0": a}); assert d["ok"] and d["n"] == 5 and d["firms"][0]["url"].endswith("rcpNo=20260314000") and d["firms"][0]["bsns_year"] == 2025, d
    d2 = build(now, {c: last[c] for c in ("0", "1", "2", "9")}, infos, {}); assert not d2["ok"] and d2["n"] == 3 and "firms" not in d2, d2
    s = json.dumps(d, ensure_ascii=False); assert not any(x in s for x in ("홍길동", "032-", "hm_url", "jurir", "bizr", "서해대로")), "싣지 않는 칸"
    for bad in ("우량", "유망", "상위", "추천"): assert bad not in s
    print("selftest 5/5 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

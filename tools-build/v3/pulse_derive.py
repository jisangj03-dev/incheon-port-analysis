"""인천항 일일 맥박 파생 — data/collected/v3/portwatch_ports.json(IMF PortWatch 일별) → data/derived/port_pulse.json.
「평소」 정의는 선커밋 문서 §4(최근 7일 ÷ 그 앞 91일 일평균 · 문턱 ±10%)를 그대로 따른다 — 여기서 바꾸지 않는다.
품질(§3)이 「품질 부족」이면 파생하지 않고 멈춘다(지면은 해양수산부 월 통계로 대체).
  python tools-build/v3/pulse_derive.py [--selftest]
"""
import datetime, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IN = os.path.join(ROOT, "data/collected/v3/portwatch_ports.json")
QUAL = os.path.join(ROOT, "data/collected/v3/portwatch_quality.json")
OUT = os.path.join(ROOT, "data/derived/port_pulse.json")
TYPES = [("container", "컨테이너"), ("dry_bulk", "건화물"), ("general_cargo", "일반화물"), ("roro", "자동차선"), ("tanker", "탱커")]
KO = {"Incheon": "인천", "Busan": "부산", "Pyeongtaek": "평택"}
RECENT, BASE, THR = 7, 91, 10.0
KEEP = 365


def series(rows):
    """날짜 → 행. 빈 날은 0 으로 채운다(PortWatch 는 입항 0 인 날을 빼고 내는 일이 있다)."""
    by = {str(r.get("date"))[:10]: r for r in rows if r.get("date")}
    if not by: return []
    d0, d1 = datetime.date.fromisoformat(min(by)), datetime.date.fromisoformat(max(by))
    out = []
    for i in range((d1 - d0).days + 1):
        d = (d0 + datetime.timedelta(i)).isoformat(); r = by.get(d, {})
        out.append({"d": d, "calls": int(r.get("portcalls") or 0), **{k: int(r.get(f"portcalls_{k}") or 0) for k, _ in TYPES},
                    "imp": round(float(r.get("import") or 0)), "exp": round(float(r.get("export") or 0))})
    return out


def judge(s):
    if len(s) < RECENT + BASE: return None
    rec, base = s[-RECENT:], s[-(RECENT + BASE):-RECENT]
    r = sum(x["calls"] for x in rec) / RECENT; b = sum(x["calls"] for x in base) / BASE
    pct = round(100 * (r / b - 1), 1) if b else 0.0
    word = "평소보다 많다" if pct > THR else "평소보다 적다" if pct < -THR else "평소 수준"
    by_type = {k: round(sum(x[k] for x in rec) / RECENT, 1) for k, _ in TYPES}
    base_type = {k: round(sum(x[k] for x in base) / BASE, 1) for k, _ in TYPES}
    return {"recent_from": rec[0]["d"], "recent_to": rec[-1]["d"], "base_from": base[0]["d"], "base_to": base[-1]["d"],
            "recent_avg": round(r, 1), "base_avg": round(b, 1), "pct": pct, "word": word, "by_type": by_type, "base_by_type": base_type,
            "imp_avg": round(sum(x["imp"] for x in rec) / RECENT), "exp_avg": round(sum(x["exp"] for x in rec) / RECENT)}


def derive(src, qual):
    if qual.get("verdict") != "사용": return None
    ports = {}
    for name, rows in src.get("ports", {}).items():
        if name not in KO: continue
        s = series(rows)
        if not s: continue
        ports[name] = {"ko": KO[name], "judge": judge(s), "days": s[-KEEP:]}
    inc = ports.get("Incheon")
    if not inc or not inc["judge"]: return None
    return {"_설명": "IMF PortWatch 일별 입항(AIS 기반 추정) — 인천·부산·평택. 「평소」 = 최근 7일 ÷ 그 앞 91일(선커밋 §4). 교역량은 모델 추정치(톤).",
            "source": src.get("source"), "fetched": src.get("fetched"), "asof": inc["days"][-1]["d"],
            "quality": qual, "rule": {"recent": RECENT, "base": BASE, "threshold_pct": THR},
            "types": [{"id": k, "ko": v} for k, v in TYPES], "ports": ports}


def main():
    q = json.load(open(QUAL, encoding="utf-8"))
    d = derive(json.load(open(IN, encoding="utf-8")), q)
    if not d:
        print("파생 안 함 — 품질:", q.get("verdict"), q.get("pct")); return 0
    json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    j = d["ports"]["Incheon"]["judge"]
    print(f"{d['asof']} 기준 · 인천 최근7일 {j['recent_avg']} / 평소 {j['base_avg']} → {j['pct']}% {j['word']} → {OUT}")
    return 0


def selftest():
    day = lambda i: (datetime.date(2025, 1, 1) + datetime.timedelta(i)).isoformat()
    rows = [{"date": day(i), "portcalls": 10, "portcalls_container": 4} for i in range(91)] + [{"date": day(91 + i), "portcalls": 12, "portcalls_container": 5} for i in range(7)]
    rows = [r for r in rows if r["date"] != day(5)]  # 빈 날 하나 → 0 으로 채운다
    d = derive({"ports": {"Incheon": rows}}, {"verdict": "사용"})
    j = d["ports"]["Incheon"]["judge"]
    assert j["base_avg"] == round(900 / 91, 1) and j["recent_avg"] == 12.0 and j["word"] == "평소보다 많다", j
    assert derive({"ports": {"Incheon": rows}}, {"verdict": "품질 부족"}) is None
    flat = [{"date": day(i), "portcalls": 10} for i in range(98)]
    assert derive({"ports": {"Incheon": flat}}, {"verdict": "사용"})["ports"]["Incheon"]["judge"]["word"] == "평소 수준"
    print("selftest 3/3 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

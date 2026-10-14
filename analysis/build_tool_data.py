# -*- coding: utf-8 -*-
"""창고 배치도 데이터 — 공개 집계 CSV 두 개에서 `_data/warehouse_gu.json` 을 만든다 (2026-10-09).

    python analysis/build_tool_data.py

입력은 이미 공개된 집계뿐이다: analysis/warehouse_by_gu.csv · analysis/warehouse_by_dong.csv.
원본 행(상호·주소)은 읽지 않는다 — nlic 행 단위 이용조건 확인 전(docs/물류사업_갈래_판정기준_선커밋_20261009.md §2).
지면 `tools/warehouse-map.html` 이 Jekyll `site.data.warehouse_gu` 로 이 파일을 읽는다(네트워크 호출 없음).
검사: python analysis/check_cost_tool.py (M1 합계 일치 · M2 원본 행 0).
"""
import csv
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GU = os.path.join(ROOT, "analysis", "warehouse_by_gu.csv")
DONG = os.path.join(ROOT, "analysis", "warehouse_by_dong.csv")
OUT = os.path.join(ROOT, "_data", "warehouse_gu.json")

# 개략 배치(열, 행) — 구·군의 대략적인 방향만 맞춘 칸이다. 실제 경계·면적·거리가 아니다.
# 행정경계 파일은 출처·이용허락을 확인하지 못해 쓰지 않는다(범위 확장 문서와 같은 판단).
# 구 이름은 2026-07-01 개편 뒤 이름(정제 주소의 법정동코드 기준 — reports/물류창고.md).
TILE = {
    "강화군": (1, 0),
    "검단구": (2, 1), "계양구": (3, 1),
    "영종구": (0, 2), "서해구": (2, 2), "부평구": (3, 2),
    "제물포구": (1, 3), "미추홀구": (2, 3), "남동구": (3, 3),
    "옹진군": (0, 4), "연수구": (2, 4),
}


def main():
    with io.open(GU, encoding="utf-8") as f:
        gu_rows = list(csv.DictReader(f))
    with io.open(DONG, encoding="utf-8") as f:
        dong_rows = list(csv.DictReader(f))
    gu = []
    for r in gu_rows:
        laws = {k.split("·", 1)[1]: int(v) for k, v in r.items() if k.startswith("개소·") and int(v)}
        x, y = TILE[r["이름"]]
        gu.append({"code": r["코드"], "name": r["이름"], "count": int(r["개소"]), "area": int(r["면적합_m2"]),
                   "cold": int(r["냉동냉장면적_m2"]), "laws": laws, "x": x, "y": y})
    dong = [{"gu": r["구"], "name": r["이름"], "count": int(r["개소"]), "area": int(r["면적합_m2"])} for r in dong_rows]
    total = {"count": sum(g["count"] for g in gu), "area": sum(g["area"] for g in gu), "cold": sum(g["cold"] for g in gu)}
    if sum(d["count"] for d in dong) != total["count"]:
        raise SystemExit("동 합계와 구 합계가 다르다 — 집계 CSV 부터 확인")
    out = {"_출처": "analysis/warehouse_by_gu.csv · warehouse_by_dong.csv (국토교통부 물류창고업 등록 자료, 자료 기준일 2026-10-01)",
           "_배치": "x·y 는 개략 배치 칸 — 실제 경계·거리 아님", "basis": "2026-10-01", "total": total, "gu": gu, "dong": dong}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"만듦: _data/warehouse_gu.json — 구 {len(gu)} · 동 {len(dong)} · {total['count']}곳 · {total['area']:,}m²")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()

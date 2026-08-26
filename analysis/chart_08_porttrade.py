# -*- coding: utf-8 -*-
"""#08 관세청 인천항 수출입 신고 — 차트 2종 렌더

- 입력: porttrade_202412_202607.csv (2024-12~2026-07, 월 응답 전량)
- 모집단: portCd=KRINC(인천항). 월별로 cstmSgn(신고 세관)을 가로질러 합산
- 단위: USD · 신고 건수. **TEU·박스 수가 아니다**
- 총계행(portCd='-')은 제외한다. 월 축은 reqYymm(요청한 달) — 응답의 year는 총계행에서 「총계」로 덮인다(사고 37)
- 파서는 헤더명 기준. 위치 인덱스 금지

실행: cd analysis && python chart_08_porttrade.py
산출물:
  - ../reports/images/porttrade_incheon_dlr_20m.png
  - ../reports/images/porttrade_incheon_ratio_20m.png
"""
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

_avail = {f.name for f in font_manager.fontManager.ttflist}
for _cand in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP"):
    if _cand in _avail:
        plt.rcParams["font.family"] = _cand
        break
plt.rcParams["axes.unicode_minus"] = False

SRC = "porttrade_202412_202607.csv"
IMG = "../reports/images"
os.makedirs(IMG, exist_ok=True)

inc = defaultdict(lambda: defaultdict(int))
with open(SRC, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["portCd"] != "KRINC":
            continue
        for v in ("expCnt", "impCnt", "expDlr", "impDlr"):
            inc[r["reqYymm"]][v] += int(r[v] or 0)

ms = sorted(inc)
lbl = [f"{m[2:4]}.{m[4:]}" for m in ms]
exp = [inc[m]["expDlr"] / 1e9 for m in ms]
imp = [inc[m]["impDlr"] / 1e9 for m in ms]
rd = [inc[m]["impDlr"] / inc[m]["expDlr"] for m in ms]
rc = [inc[m]["impCnt"] / inc[m]["expCnt"] for m in ms]

# ── 차트 1 — 수출액 vs 수입액 ────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 5))
x = range(len(ms))
ax.bar([i - 0.2 for i in x], exp, width=0.4, label="수출 신고액", color="#4C78A8")
ax.bar([i + 0.2 for i in x], imp, width=0.4, label="수입 신고액", color="#E45756")
ax.set_xticks(list(x))
ax.set_xticklabels(lbl, fontsize=8)
ax.set_ylabel("십억 USD")
ax.set_title("인천항 월별 수출입 신고액 — 관세청 (2024-12 ~ 2026-07, 잠정치)")
ax.legend(frameon=False)
ax.grid(axis="y", alpha=.3)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.subplots_adjust(left=0.075)
fig.savefig(f"{IMG}/porttrade_incheon_dlr_20m.png", dpi=150)
plt.close(fig)

# ── 차트 2 — 수입÷수출 배율 (금액·건수) ──────────────────────
fig, ax = plt.subplots(figsize=(11, 5))
ax.plot(x, rd, marker="o", ms=4, label="금액 기준 (USD)", color="#4C78A8")
ax.plot(x, rc, marker="s", ms=4, label="건수 기준 (신고 건수)", color="#F58518")
ax.axhline(1.0, color="#888", lw=1, ls="--")
ax.text(len(ms) - 1, 1.05, "1.0 = 방향 균형", ha="right", fontsize=8, color="#666")
ax.set_xticks(list(x))
ax.set_xticklabels(lbl, fontsize=8)
ax.set_ylabel("수입 ÷ 수출 (배)")
ax.set_title("인천항 수입÷수출 배율 — 20개월 전 구간 1.0 위 (관세청, 잠정치)")
ax.legend(frameon=False)
ax.grid(axis="y", alpha=.3)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.subplots_adjust(left=0.075)
fig.savefig(f"{IMG}/porttrade_incheon_ratio_20m.png", dpi=150)
plt.close(fig)

print(f"렌더 완료 · {len(ms)}개월")
print(f"  금액 배율 {min(rd):.3f} ~ {max(rd):.3f}")
print(f"  건수 배율 {min(rc):.3f} ~ {max(rc):.3f}")

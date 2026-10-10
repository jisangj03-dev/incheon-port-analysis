# -*- coding: utf-8 -*-
"""webapp-testing 스킬 실동 확인 — with_server.py 가 띄운 로컬 빌드에서 계산기를 연다(2026-10-10).

  python .claude/skills/webapp-testing/scripts/with_server.py \
      --server "python3 -m http.server 4173 --bind 127.0.0.1 --directory _site" --port 4173 \
      -- python tests/py/calc_smoke.py

「가상 예시 넣기」를 눌러 첫 카드가 4,044원인지 본다. 손 입력 회귀는 tests/cost.spec.mjs 가 맡는다 —
이 파일은 **스킬의 경로(파이썬 Playwright + with_server.py)가 실제로 도는지**만 본다.
"""
import os
import sys

from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

URL = "http://127.0.0.1:4173/incheon-port-analysis/tools/logistics-cost.html"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=os.environ.get("PW_CHROMIUM_PATH") or None)
    page = b.new_page()
    page.goto(URL)
    page.wait_for_load_state("networkidle")
    page.click("#cc-sample")
    first = page.locator("#cc-cards .cc-card .cc-big").first.inner_text()
    b.close()

print("첫 카드:", first)
if first.replace(",", "").replace("원", "").strip() != "4044":
    print("실패 — 4,044원이 아니다")
    sys.exit(1)
print("통과")

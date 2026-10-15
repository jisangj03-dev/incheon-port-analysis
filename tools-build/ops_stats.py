"""AI 운영실 공개 사례 1쪽의 숫자 — 이 저장소 main 의 git 기록에서만 센다(정체성 §3-5 O2 · 2026-10-14).

내부 노출 0(O1): 사람 이름·이메일·경로·과제 번호·결재 내용은 세지도 적지도 않는다. 커밋 제목·작성자는 출력하지 않고 개수만.
  python tools-build/ops_stats.py [--ref origin/main] [--selftest]
결과: data/derived/ops_stats.json (집계 명령과 기준 커밋·기준일을 같이 적는다)
**얕은 복제(git clone --depth)면 앞 기록이 빠진다** — 그때는 실패한다(2026-10-14 실측: 깊이 50 복제에서 486 중 163 만 셌다).
세는 것
  · commits_total      main 의 커밋 수(병합 커밋 제외)
  · ai_coauthored      본문에 「Co-Authored-By: Claude」 꼬리가 있는 커밋 — AI 세션이 만든 것
  · bot_routine        github-actions[bot] 이 만든 커밋 — 예약·자동 루틴(수집·추출)
  · human_only         둘 다 아닌 커밋 — 사람이 직접 만든 것
  · prs_merged         제목 끝 「(#번호)」 커밋 수(스쿼시 머지) + 「Merge pull request #」 병합 커밋 수
  · first_day / last_day  기간
"""
import json, os, re, subprocess, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data/derived/ops_stats.json")
SEP = "\x1e"


def count(log_text):
    commits = [c for c in log_text.split(SEP) if c.strip()]
    s = {"commits_total": 0, "ai_coauthored": 0, "bot_routine": 0, "human_only": 0, "prs_merged": 0, "days": set()}
    for c in commits:
        head, _, body = c.strip().partition("\n")
        parts = head.split("\x1f")
        if len(parts) < 4: continue
        _sha, date, author_kind, subject = parts[0], parts[1], parts[2], parts[3]
        parents = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
        if re.match(r"Merge pull request #\d+", subject):
            s["prs_merged"] += 1
        if parents > 1:
            continue  # 병합 커밋은 일의 단위가 아니다
        s["commits_total"] += 1
        s["days"].add(date)
        if re.search(r"\(#\d+\)\s*$", subject): s["prs_merged"] += 1
        ai = bool(re.search(r"^Co-Authored-By:\s*Claude", body, re.M | re.I))
        bot = author_kind == "bot"
        s["ai_coauthored"] += ai
        s["bot_routine"] += bot and not ai
        s["human_only"] += (not ai and not bot)
    days = sorted(s.pop("days"))
    s["first_day"], s["last_day"] = (days[0], days[-1]) if days else ("", "")
    s["active_days"] = len(days)
    return s


def main():
    ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else "origin/main"
    if subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, capture_output=True, text=True).stdout.strip() == "true":
        print("얕은 복제 — 전체 기록이 아니다. `git fetch --unshallow` 뒤에 다시."); return 1
    # 작성자 이름은 출력하지 않는다 — 봇 여부만 가른다
    raw = subprocess.run(["git", "log", ref, "--format=" + SEP + "%H%x1f%cs%x1f%ae%x1f%s%x1f%p%n%b"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    lines = []
    for c in raw.split(SEP):
        if not c.strip(): continue
        head, _, body = c.partition("\n")
        p = head.split("\x1f")
        kind = "bot" if p[2].endswith("[bot]@users.noreply.github.com") or "github-actions" in p[2] else "person"
        nparents = len(p[4].split()) if len(p) > 4 else 1
        lines.append("\x1f".join([p[0], p[1], kind, p[3], str(nparents)]) + "\n" + body)
    s = count(SEP + SEP.join(lines))
    sha = subprocess.run(["git", "rev-parse", "--short", ref], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    s.update({"ref": ref, "ref_sha": sha, "counted": datetime.date.today().isoformat(),
              "command": f"python tools-build/ops_stats.py --ref {ref}",
              "human_share_pct": round(100 * s["human_only"] / s["commits_total"], 1) if s["commits_total"] else None,
              "ai_share_pct": round(100 * s["ai_coauthored"] / s["commits_total"], 1) if s["commits_total"] else None})
    json.dump(s, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(s, ensure_ascii=False))
    return 0


def selftest():
    t = SEP.join([
        "", "a\x1f2026-10-01\x1fperson\x1f지도 고침 (#30)\x1f1\n\nCo-Authored-By: Claude Opus <x>\n",
        "b\x1f2026-10-02\x1fbot\x1f수집 결과\x1f1\n",
        "c\x1f2026-10-02\x1fperson\x1f오타\x1f1\n",
        "d\x1f2026-10-03\x1fperson\x1fMerge pull request #31 from x\x1f2\n",
    ])
    s = count(t)
    assert (s["commits_total"], s["ai_coauthored"], s["bot_routine"], s["human_only"], s["prs_merged"], s["active_days"]) == (3, 1, 1, 1, 2, 2), s
    print("selftest 1/1 ok"); return 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())

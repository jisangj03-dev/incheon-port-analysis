// 품목 트리맵 레이스(실무 도구 · 2026-10-14) — 해마다 인천의 수출·수입 품목 구성(HS 2단위)이 칸 넓이로 다시 배치되며 흐른다.
// 칸은 HTML 상자(절대 위치) — 자리·크기를 CSS 전환으로 옮겨 부드럽게 움직인다(캔버스·라이브러리 0). 배치 = 정사각형에 가까운 트리맵(squarify).
export type Year = { y: string; through: string; total: number; items: { hs: string; name: string; v: number }[] };
type Rect = { x: number; y: number; w: number; h: number };

/** squarify — 넓이 비례 · 가로세로비 최소(Bruls 등 2000). 입력은 큰 것부터. */
export function squarify(vals: number[], box: Rect): Rect[] {
  const out: Rect[] = new Array(vals.length);
  const sum = vals.reduce((a, b) => a + b, 0) || 1;
  const scale = (box.w * box.h) / sum;
  const areas = vals.map((v) => v * scale);
  let i = 0, r = { ...box };
  const worst = (row: number[], side: number) => { const s = row.reduce((a, b) => a + b, 0), mx = Math.max(...row), mn = Math.min(...row); return Math.max((side * side * mx) / (s * s), (s * s) / (side * side * mn)); };
  while (i < areas.length) {
    const side = Math.min(r.w, r.h), row: number[] = [areas[i]];
    let j = i + 1;
    while (j < areas.length && worst([...row, areas[j]], side) <= worst(row, side)) { row.push(areas[j]); j++; }
    const s = row.reduce((a, b) => a + b, 0);
    if (r.w >= r.h) { // 왼쪽에 세로 줄
      const cw = s / r.h; let y = r.y;
      row.forEach((a, k) => { const h = a / cw; out[i + k] = { x: r.x, y, w: cw, h }; y += h; });
      r = { x: r.x + cw, y: r.y, w: r.w - cw, h: r.h };
    } else { // 위에 가로 줄
      const ch = s / r.w; let x = r.x;
      row.forEach((a, k) => { const w = a / ch; out[i + k] = { x, y: r.y, w, h: ch }; x += w; });
      r = { x: r.x, y: r.y + ch, w: r.w, h: r.h - ch };
    }
    i = j;
  }
  return out;
}

// HS 2단위 → 묶음(색) — 관세율표 부(部) 경계를 따른다
export const GROUPS: { id: string; label: string; from: number; to: number; c: string }[] = [
  { id: "agri", label: "농축수산·식품", from: 1, to: 24, c: "#9db08a" },
  { id: "mineral", label: "광물·연료", from: 25, to: 27, c: "#8a8170" },
  { id: "chem", label: "화학·플라스틱·고무", from: 28, to: 40, c: "#7ea0ad" },
  { id: "light", label: "가죽·목재·종이·섬유·신발", from: 41, to: 67, c: "#c2a98a" },
  { id: "stone", label: "석재·유리·귀금속", from: 68, to: 71, c: "#b7aa95" },
  { id: "metal", label: "철강·금속", from: 72, to: 83, c: "#7a6f62" },
  { id: "mach", label: "기계류(84)", from: 84, to: 84, c: "#4f6a78" },
  { id: "elec", label: "전기기기(85)", from: 85, to: 85, c: "#b3361e" },
  { id: "trans", label: "수송기기", from: 86, to: 89, c: "#3e8a8c" },
  { id: "prec", label: "정밀·광학·기타", from: 90, to: 99, c: "#a08c7a" },
];
/** 칸 색 위 글자 — 밝기로 고른다(어두운 칸에 검은 글자가 명암비 4.5 를 못 넘었다 · 2026-10-14 Lighthouse) */
export const inkOn = (hex: string) => { const n = parseInt(hex.slice(1), 16), c = [n >> 16, (n >> 8) & 255, n & 255].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  const L = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; return (1.05 / (L + 0.05)) >= ((L + 0.05) / 0.0587) ? "#fff" : "#191714"; };
export const groupOf = (hs: string) => { const n = Number(hs); return GROUPS.find((g) => n >= g.from && n <= g.to) || GROUPS[GROUPS.length - 1]; };

// 칸이 좁을 때 쓰는 아주 짧은 이름(2~4자) — 「HS 90」처럼 코드만 남으면 무엇인지 안 읽혔다(4차 화면 판정)
export const ALIAS: Record<string, string> = { "85": "전기", "27": "연료", "84": "기계", "87": "자동차", "72": "철강", "30": "의료용품", "29": "유기화학", "90": "광학", "26": "광석",
  "33": "화장품", "39": "플라스틱", "44": "목재", "73": "철강품", "71": "귀금속", "76": "알루미늄", "74": "구리", "17": "당류", "12": "종자", "82": "공구", "03": "수산",
  "10": "곡물", "38": "화학품", "94": "가구", "88": "항공기", "32": "도료", "62": "의류", "28": "무기화학", "81": "비금속", "83": "금속품", "23": "사료", "40": "고무", "48": "종이", "22": "음료", "21": "조제식품", "02": "육류" };
/** 칸 이름 — 긴 이름 → 괄호 뺀 이름 → 짧은 이름 → 「HS 00」 → 빈 칸(글자 하나 ≈ 13px) */
export function tileLabel(it: { hs: string; name: string }, r: { w: number; h: number }) {
  const big = r.w > 84 && r.h > 40, mid = r.w > 46 && r.h > 26, fit = (t: string) => t.length * 13 + 14 < r.w;
  if (it.hs === "etc") return r.h > 22 && fit("그 밖") ? (big && fit(it.name) ? it.name : "그 밖") : "";
  const short = it.name.replace(/\s*\(.*\)$/, ""), alias = ALIAS[it.hs] || "", code = `HS ${it.hs}`;
  if (big && fit(it.name)) return it.name;
  if ((big || mid) && fit(short)) return short;
  if (r.h > 22 && alias && fit(alias)) return alias;
  if (r.h > 22 && fit(code)) return code;
  return "";
}
/** % 줄을 붙일 높이 — 이름 아래 둘째 줄이라 두 줄(약 16px × 2) + 위아래 여백이 들어가야 한다(6차 화면 판정: 1280 「플라스틱 1.6%」가 아래 칸에 반쯤 가렸다) */
export const pctFits = (r: { h: number }) => r.h >= 46;
/** 이름이 다 들어가는 만큼만 칸을 두고 나머지는 「그 밖」 — 남길 품목은 **그 해 금액이 큰 순**(모바일에서 의료용품 10.9% 가 접히고 철강 5.8% 가 남았다 · 4차 화면 판정) ·
 *  칸 자리 순서는 전 기간 순위(rank)로 고정해 해마다 칸이 뛰지 않게 한다 */
export function layout(items: { hs: string; name: string; v: number }[], rank: Map<string, number>, top: number, W: number, H: number) {
  const bySize = [...items].sort((a, b) => b.v - a.v);
  const mk = (N: number) => {
    const keep = new Set(bySize.slice(0, N).map((x) => x.hs));
    const head = items.filter((x) => keep.has(x.hs)).sort((a, b) => (rank.get(a.hs) ?? 999) - (rank.get(b.hs) ?? 999));
    const restN = items.length - head.length, rest = items.filter((x) => !keep.has(x.hs)).reduce((s, x) => s + x.v, 0);
    const list = rest > 0 ? [...head, { hs: "etc", name: `그 밖 ${restN}개 류`, v: rest }] : head;
    return { list, R: squarify(list.map((x) => x.v), { x: 0, y: 0, w: W, h: H }) };
  };
  let N = Math.min(top, items.length), L = mk(N);
  while (N > 3 && L.list.some((it, k) => !tileLabel(it, L.R[k]))) L = mk(--N);
  return L;
}

export type RaceOpts = { top: number; onYear?: (y: Year, i: number) => void; onPick?: (hs: string) => void };

export class TreemapRace {
  host: HTMLElement; years: Year[]; o: RaceOpts; i = 0; timer: any = null;
  tiles = new Map<string, HTMLButtonElement>(); rank = new Map<string, number>();
  constructor(host: HTMLElement, years: Year[], o: RaceOpts) {
    this.host = host; this.years = years; this.o = o; addEventListener("resize", () => this.render(false));
    // 칸 순서를 해마다 바꾸지 않는다 — 전 기간 합 순으로 고정해 두면 칸이 제자리에서 커지고 줄어 눈이 따라간다(해마다 정렬하면 칸이 뛰어다녔다)
    const tot = new Map<string, number>(); for (const y of years) for (const it of y.items) tot.set(it.hs, (tot.get(it.hs) || 0) + it.v / (y.total || 1));
    [...tot.entries()].sort((a, b) => b[1] - a[1]).forEach(([hs], i) => this.rank.set(hs, i));
  }
  set(i: number, anim = true) { this.i = Math.max(0, Math.min(this.years.length - 1, i)); this.render(anim); this.o.onYear?.(this.years[this.i], this.i); }
  render(anim = true) {
    const Y = this.years[this.i], W = this.host.clientWidth, H = this.host.clientHeight;
    const L = layout(Y.items, this.rank, this.o.top, W, H);
    const { list, R } = L;
    const live = new Set<string>();
    list.forEach((it, k) => {
      live.add(it.hs);
      let el = this.tiles.get(it.hs);
      if (!el) {
        el = document.createElement("button"); el.type = "button"; el.className = "tm-tile"; el.dataset.hs = it.hs;
        el.style.background = it.hs === "etc" ? "#d9d1c0" : groupOf(it.hs).c;
        el.style.opacity = "0"; el.addEventListener("click", () => this.o.onPick?.(el!.dataset.hs!));
        this.host.append(el); this.tiles.set(it.hs, el);
        const r0 = R[k]; el.style.transform = `translate(${r0.x + r0.w / 2}px,${r0.y + r0.h / 2}px)`; el.style.width = el.style.height = "0px";
      }
      const r = R[k], share = (100 * it.v) / (Y.total || 1);
      el.style.transition = anim ? "" : "none";
      requestAnimationFrame(() => {
        el!.style.opacity = "1";
        el!.style.transform = `translate(${r.x.toFixed(1)}px,${r.y.toFixed(1)}px)`;
        el!.style.width = `${Math.max(0, r.w - 2).toFixed(1)}px`; el!.style.height = `${Math.max(0, r.h - 2).toFixed(1)}px`;
      });
      const tiny = r.w < 24 || r.h < 24;
      // 보이는 글자 = 낭독 이름(이름이 안 보이는 칸만 aria-label) · 아주 작은 칸은 누르지 않는다(누름 자리 24px 미만 · 값은 CSV 에)
      const nm = tileLabel(it, r);
      el.innerHTML = nm ? `<b>${nm}</b>${pctFits(r) ? ` <i>${share.toFixed(1)}%</i>` : ""}` : "";
      if (nm === it.name) el.removeAttribute("aria-label"); else el.setAttribute("aria-label", `${it.name} ${share.toFixed(1)}%`);
      el.title = `${it.name} ${share.toFixed(1)}%`;
      el.disabled = tiny;
      el.style.color = inkOn(it.hs === "etc" ? "#d9d1c0" : groupOf(it.hs).c);
    });
    for (const [hs, el] of this.tiles) if (!live.has(hs)) { el.style.opacity = "0"; el.style.width = el.style.height = "0px"; }
  }
  play(sec = 1.4) { this.stop(); this.timer = setInterval(() => this.set(this.i + 1 >= this.years.length ? 0 : this.i + 1), sec * 1000); }
  stop() { clearInterval(this.timer); this.timer = null; }
}

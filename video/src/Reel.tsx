// 한 편 — 머리(질문·큰 숫자 · 2.5초) → 도구 녹화(조작 시각에 맞춘 자막 · 아래 출처·기준일 띠) → 끝 카드(주소 · 3초).
// 숫자는 props 에서만 온다(render.mjs 가 og/cards.json · data/derived 에서 만들고 숫자 검사를 통과한 것만 넘긴다).
import React, { useEffect, useState } from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig, delayRender, continueRender } from "remotion";

export const FPS = 30, INTRO = 75, OUTRO = 90;
export type ReelProps = { id: string; fmt: "portrait" | "square"; w: number; h: number; clip: string; clipMs: number; q: string; num: string; unit: string; eb: string; source: string; asof: string; url: string;
  callouts: { at: number; text: string; pos?: "top" | "bottom" }[]; cam?: number[][] /* 녹화 프레임마다 [x0, y0, z] — render.mjs 가 초점 기록으로 만든 따라가기 카메라 */ };
// 자막 상자 자리(render.mjs 의 대비 시험이 같은 값을 쓴다)
export const CAP = { portrait: { bottom: 210, top: 120, font: 46 }, square: { bottom: 120, top: 60, font: 40 } };

const C = { paper: "#f5f2eb", ink: "#191714", ink2: "#3a352e", ink3: "#5b554c", signal: "#b3361e", rule: "#d9d3c7" };
const FONT = '"Pretendard Variable", Pretendard, "Noto Sans CJK KR", sans-serif';

const useFonts = (texts: string[]) => {
  const [h] = useState(() => delayRender("글꼴"));
  useEffect(() => {
    const css = document.createElement("link"); css.rel = "stylesheet"; css.href = staticFile("fonts/pretendard/pretendard.css"); document.head.appendChild(css);
    css.onload = () => Promise.all([400, 600, 800].map((w) => document.fonts.load(`${w} 40px "Pretendard Variable"`, texts.join(" ")))).then(() => document.fonts.ready).then(() => continueRender(h), () => continueRender(h));
    css.onerror = () => continueRender(h);
  }, []);
};

const Intro: React.FC<ReelProps> = (p) => {
  const f = useCurrentFrame(), { fps } = useVideoConfig(), sq = p.fmt === "square";
  const k = spring({ frame: f - 8, fps, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ background: C.paper, borderTop: `14px solid ${C.signal}`, padding: sq ? "90px 84px" : "200px 84px", fontFamily: FONT, color: C.ink, wordBreak: "keep-all" }}>
      <div style={{ fontSize: 34, fontWeight: 600, color: C.ink3, opacity: interpolate(f, [0, 10], [0, 1]) }}>측심 도구 · {p.eb}</div>
      <div style={{ fontSize: sq ? 64 : 76, lineHeight: 1.22, fontWeight: 800, letterSpacing: "-0.03em", marginTop: 26, opacity: interpolate(f, [4, 18], [0, 1]), transform: `translateY(${interpolate(f, [4, 18], [24, 0], { extrapolateRight: "clamp" })}px)` }}>{p.q}</div>
      <div style={{ marginTop: sq ? 44 : 90, fontSize: sq ? 150 : 190, fontWeight: 800, letterSpacing: "-0.04em", color: C.signal, lineHeight: 1, transform: `scale(${0.9 + 0.1 * k})`, transformOrigin: "left center", opacity: k }}>{p.num}</div>
      <div style={{ marginTop: 18, fontSize: sq ? 34 : 40, fontWeight: 600, color: C.ink2, opacity: k }}>{p.unit}</div>
    </AbsoluteFill>
  );
};

const Clip: React.FC<ReelProps> = (p) => {
  const f = useCurrentFrame(), ms = (f / FPS) * 1000, sq = p.fmt === "square", C2 = CAP[p.fmt];
  const cur = [...p.callouts].reverse().find((c) => c.at <= ms);
  // [채팅 검수 #55] 자막은 처음부터 불투명 상자 · 바뀔 때는 상자 통째로 4프레임(0.13초) 미끄러져 들어온다(반투명 글자 겹침 0)
  const fin = cur ? Math.min(1, ((ms - cur.at) / 1000) * FPS / 4) : 1;
  const [x0, y0, z] = p.cam?.[Math.min(f, (p.cam?.length || 1) - 1)] || [0, 0, 1];
  const bottom = (cur?.pos || "bottom") === "bottom";
  return (
    <AbsoluteFill style={{ background: C.paper, fontFamily: FONT, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: p.w, height: p.h, transformOrigin: "0 0", transform: `scale(${z}) translate(${-x0}px, ${-y0}px)` }}>
        <OffthreadVideo src={staticFile(p.clip)} style={{ width: p.w, height: p.h }} />
      </div>
      {cur && (
        <div data-cap style={{ position: "absolute", left: 40, right: 40, ...(bottom ? { bottom: C2.bottom } : { top: C2.top }), background: C.ink, color: "#fff", padding: "22px 30px", fontSize: C2.font, fontWeight: 700, lineHeight: 1.35,
          boxShadow: "0 10px 30px rgba(0,0,0,.25)", transform: `translateY(${(1 - fin) * (bottom ? 24 : -24)}px)`, wordBreak: "keep-all" }}>{cur.text}</div>
      )}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, background: C.paper, borderTop: `2px solid ${C.rule}`, padding: sq ? "18px 40px" : "26px 40px", fontSize: sq ? 24 : 28, color: C.ink2, lineHeight: 1.4 }}>
        출처 {p.source} · <b style={{ color: C.signal }}>{p.asof}</b>
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC<ReelProps> = (p) => {
  const f = useCurrentFrame(), sq = p.fmt === "square";
  return (
    <AbsoluteFill style={{ background: C.ink, color: C.paper, fontFamily: FONT, padding: sq ? "120px 84px" : "260px 84px", justifyContent: "center", wordBreak: "keep-all" }}>
      <div style={{ fontSize: sq ? 56 : 66, fontWeight: 800, lineHeight: 1.25, opacity: interpolate(f, [0, 12], [0, 1]) }}>직접 조작해 보기</div>
      <div style={{ marginTop: 30, fontSize: sq ? 34 : 38, fontWeight: 600, color: "#f0b9a8", wordBreak: "break-all", opacity: interpolate(f, [6, 18], [0, 1]) }}>{p.url.replace(/^https:\/\//, "")}</div>
      <div style={{ marginTop: sq ? 70 : 120, fontSize: sq ? 30 : 34, color: "#cfc8bb", lineHeight: 1.5 }}>측심 · 공공 1차 데이터로 움직이는 SCM 작업실<br />계산은 참고용이며 자문이 아닙니다</div>
    </AbsoluteFill>
  );
};

export const Reel: React.FC<ReelProps> = (p) => {
  useFonts([p.q, p.num, p.unit, p.eb, p.source, p.asof, p.url, "직접 조작해 보기 측심 공공 1차 데이터로 움직이는 SCM 작업실 계산은 참고용이며 자문이 아닙니다 출처 도구", ...p.callouts.map((c) => c.text)]);
  const clipF = Math.ceil((p.clipMs / 1000) * FPS);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Sequence durationInFrames={INTRO}><Intro {...p} /></Sequence>
      <Sequence from={INTRO} durationInFrames={clipF}><Clip {...p} /></Sequence>
      <Sequence from={INTRO + clipF}><Outro {...p} /></Sequence>
    </AbsoluteFill>
  );
};

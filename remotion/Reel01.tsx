import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, staticFile, useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";
import spec from "../reels/reel-01.json";

// 도구 시연형 릴스 1 — 화면 녹화(계산기 실사용) 위에 큰 자막. 소리 없음(Edge TTS·배경음악 안 씀).
// 첫 3초에 결과부터(「견적 A가 건당 1,239원 싸다?」) · 장면별 숫자는 reels/reel-01.json 의 「사실_검증」이 출처를 든다.
const Caption: React.FC<{ big: string; small?: string }> = ({ big, small }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: f, fps, config: { damping: 200 } });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-start", alignItems: "center", paddingTop: 70 }}>
      <div style={{ transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)`, opacity: s, background: "rgba(5,9,15,.86)", borderRadius: 36, padding: "38px 46px", margin: "0 60px", textAlign: "center", border: "3px solid #3fd3e6" }}>
        <div style={{ color: "#fff", fontSize: 66, fontWeight: 800, lineHeight: 1.2, whiteSpace: "pre-line", letterSpacing: -2, wordBreak: "keep-all" }}>{big}</div>
        {small && <div style={{ color: "#ffb547", fontSize: 34, fontWeight: 700, marginTop: 16, wordBreak: "keep-all" }}>{small}</div>}
      </div>
    </AbsoluteFill>
  );
};

export const Reel01: React.FC<{ video?: string }> = ({ video = "reel-01-calc.webm" }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: "#0b1a26", fontFamily: "'Pretendard Variable', 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, sans-serif" }}>
      <div style={{ position: "absolute", left: 120, top: 360, width: 840, height: 1493, borderRadius: 40, overflow: "hidden", boxShadow: "0 30px 80px rgba(0,0,0,.55)", border: "2px solid rgba(170,210,235,.3)" }}>
        <OffthreadVideo src={staticFile(video)} muted playbackRate={0.72} style={{ width: 840, height: 1493, objectFit: "cover" }} />
      </div>
      {spec["장면"].map((sc: any) => (
        <Sequence key={sc.s} from={Math.round(sc.s * fps)} durationInFrames={Math.round((sc.e - sc.s) * fps)}>
          <Caption big={sc["자막"]} small={sc["작게"]} />
        </Sequence>
      ))}
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 40 }}>
        <div style={{ color: "#a3b9c9", fontSize: 30 }}>측심 · 가상 예시(실제 업체 견적 아님) · 화면 녹화</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

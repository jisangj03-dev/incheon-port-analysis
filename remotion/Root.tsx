import React from "react";
import { Composition, AbsoluteFill, useCurrentFrame, interpolate } from "remotion";

// 시험값 — 실제 통계 아님. 실제 릴스는 data/derived 의 스냅샷을 props 로 받는다.
const Proof: React.FC = () => {
  const f = useCurrentFrame();
  const w = interpolate(f, [0, 30], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: "#0b1a26", color: "#eef5fa", fontFamily: "system-ui, sans-serif", padding: 60, justifyContent: "center" }}>
      <div style={{ fontSize: 34, color: "#3fd3e6", letterSpacing: 4 }}>측심 · SOUNDING</div>
      <div style={{ fontSize: 72, fontWeight: 800, marginTop: 20 }}>Remotion 실행 증명</div>
      <div style={{ height: 18, width: `${w * 80}%`, background: "#ffb547", borderRadius: 9, marginTop: 40 }} />
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <>
    <Composition id="Proof" component={Proof} durationInFrames={60} fps={30} width={1080} height={1080} />
    <Composition id="Reel" component={Proof} durationInFrames={90} fps={30} width={1080} height={1920} />
  </>
);

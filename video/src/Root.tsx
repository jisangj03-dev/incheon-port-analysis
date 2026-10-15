// 측심 도구 시연 영상(⑤) — 편 × 판(세로 9:16 · 정사각 1:1). 자막 묶음은 render.mjs 가 데이터에서 만들어 inputProps 로 넣는다(숫자 = 데이터 파일).
import React from "react";
import { Composition } from "remotion";
import { Reel, ReelProps, INTRO, OUTRO, FPS } from "./Reel";

const blank: ReelProps = { id: "x", fmt: "portrait", w: 1080, h: 1920, clip: "", clipMs: 1000, q: "", num: "", unit: "", eb: "", source: "", asof: "", url: "", callouts: [] };
const dur = (p: ReelProps) => INTRO + Math.ceil((p.clipMs / 1000) * FPS) + OUTRO;

export const Root: React.FC = () => (
  <>
    {(["portrait", "square"] as const).map((fmt) => (
      <Composition key={fmt} id={`reel-${fmt}`} component={Reel} fps={FPS} width={1080} height={fmt === "portrait" ? 1920 : 1080} durationInFrames={dur(blank)}
        defaultProps={{ ...blank, fmt, h: fmt === "portrait" ? 1920 : 1080 }}
        calculateMetadata={({ props }) => ({ durationInFrames: dur(props), width: props.w, height: props.h })} />
    ))}
  </>
);

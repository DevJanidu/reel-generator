import React from "react";
import {Composition, registerRoot} from "remotion";
import {OddFrameReel, type ReelProps} from "./composition";
export {OddFrameReel, type ReelProps} from "./composition";
const empty: ReelProps = {
  episode_id: "",
  width: 1080,
  height: 1920,
  fps: 30,
  durationInFrames: 30,
  scenes: [],
  captions: [],
  narration: "",
  instrumental: "",
  audioSources: ["narration", "instrumental"],
};
registerRoot(() => (
  <Composition
    id="OddFrameReel"
    component={OddFrameReel}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={30}
    defaultProps={empty}
    calculateMetadata={({ props }) => ({
      durationInFrames: props.durationInFrames,
    })}
  />
));

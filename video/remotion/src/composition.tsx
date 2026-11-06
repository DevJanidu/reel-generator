import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  useCurrentFrame,
  delayRender,
  continueRender,
  cancelRender,
} from "remotion";

/*
 * ODD FRAME composition. Supports two pinned editing profiles:
 *   classic   - ODD_FRAME_CLASSIC_V1_0: hard cuts + Quick Pop captions (unchanged look)
 *   cinematic - ODD_FRAME_CINEMATIC_FLOW_V1_1: crossfades / dips to charcoal, wave + glow captions
 * Story stills are ALWAYS completely static. Transitions are layered over unchanged scene boundaries, so the
 * overall duration and the narration synchronization never change. No sound is produced here beyond the
 * two supplied audio sources.
 */

export type Transition = "cut" | "crossfade" | "dip_to_dark";
const TRANSITIONS: Transition[] = ["cut", "crossfade", "dip_to_dark"];
export type Preset =
  | "quick_pop"
  | "immediate_reveal"
  | "gentle_emphasis"
  | "wave_reveal"
  | "glow_pop"
  | "smooth_replace"
  | "immediate_impact"
  | "soft_fade";
const PRESETS: Preset[] = [
  "quick_pop",
  "immediate_reveal",
  "gentle_emphasis",
  "wave_reveal",
  "glow_pop",
  "smooth_replace",
  "immediate_impact",
  "soft_fade",
];

export type Shot = {
  id: string;
  start: number;
  end: number;
  image: string;
  caption_y: number;
  motion: "static";
  transition: Transition;
  transition_frames?: number;
};
export type Caption = {
  start: number;
  end: number;
  text: string;
  y: number;
  preset: Preset;
  emphasis?: "none" | "gold";
  enter_frames?: number;
  exit_frames?: number;
  glow?: boolean;
  size?: number;
  glow_strength?: number;
};
export type StyleProps = {
  profile_id: string;
  version: string;
  renderer: "classic" | "cinematic";
  renderer_dir?: string;
  allowed_transitions: string[];
  dip_color?: string;
  wave?: {
    entrance_frames: number;
    stagger_total_frames: number;
    rise_px: number;
    exit_frames: number;
  };
  glow?: {
    white: number[];
    gold: number[];
    base_alpha: number;
    base_blur_px: number;
    peak_alpha: number;
    peak_blur_px: number;
    gold_alpha: number;
    rise_frames: number;
    settle_frames: number;
  };
  min_glow_frames?: number;
};
export type ReelProps = {
  episode_id: string;
  width: number;
  height: number;
  fps: number;
  durationInFrames: number;
  scenes: Shot[];
  captions: Caption[];
  narration: string;
  instrumental: string;
  audioSources: string[];
  style?: StyleProps;
  /** True only for disposable demonstration assets used by Preview Style. */
  sample?: boolean;
  editor_version?: number;
  audio?: {narration_gain: number; music_gain: number; fade_in: number; fade_out: number; ducking: number; envelope: number[]};
  audition?: {narration_muted: boolean; music_muted: boolean};
};

const CLASSIC_STYLE: StyleProps = {
  profile_id: "ODD_FRAME_CLASSIC_V1_0",
  version: "1.0.0",
  renderer: "classic",
  allowed_transitions: ["cut"],
};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const easeOut = Easing.out(Easing.cubic);

const rgba = (rgb: number[], alpha: number) =>
  `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${Math.max(0, alpha).toFixed(3)})`;

const splitLines = (text: string) => {
  const words = text.trim().split(/\s+/);
  return words.length > 2
    ? [
        words.slice(0, Math.ceil(words.length / 2)).join(" "),
        words.slice(Math.ceil(words.length / 2)).join(" "),
      ]
    : [text.trim()];
};

const fitSize = (lines: string[], limit = 830) => {
  const context =
    typeof document === "undefined"
      ? null
      : document.createElement("canvas").getContext("2d");
  if (context) context.font = '800 82px "Barlow Condensed"';
  const maxWidth = Math.max(
    ...lines.map((line) => context?.measureText(line.toUpperCase()).width || 0),
  );
  // Cinematic uses a 3% margin: per-letter spans lose a little kerning versus the canvas measurement.
  const size = maxWidth > limit ? (82 * limit) / maxWidth : 82;
  if (size < 56)
    throw new Error(
      "Caption is too wide for readable mobile text; correct phrase boundaries",
    );
  return size;
};

const baseTextStyle = (size: number): React.CSSProperties => ({
  fontFamily: "Barlow Condensed",
  fontWeight: 800,
  fontSize: size,
  lineHeight: 1.05,
  color: "#FFFFFF",
  WebkitTextStroke: "7px #000000",
  paintOrder: "stroke fill",
  textTransform: "uppercase",
});

/* ---------------------------- Classic caption ---------------------------- */
const ClassicCaption: React.FC<{ caption: Caption }> = ({ caption }) => {
  const frame = useCurrentFrame();
  const instant = caption.preset === "immediate_reveal";
  const scale = instant
    ? 1
    : interpolate(
        frame,
        [0, 5],
        [caption.preset === "gentle_emphasis" ? 0.97 : 0.94, 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
      );
  const opacity = instant
    ? 1
    : interpolate(frame, [0, 2], [0, 1], { extrapolateRight: "clamp" });
  const lines = splitLines(caption.text);
  const size = fitSize(lines, 850) * (caption.size ?? 1);
  return (
    <div
      data-caption
      style={{
        position: "absolute",
        left: 98,
        width: 884,
        top: caption.y * 1920,
        transform: `translateY(-50%) scale(${scale})`,
        opacity,
        textAlign: "center",
        ...baseTextStyle(size),
        textShadow: "0 4px 8px #0009",
      }}
    >
      {lines.map((line, i) => (
        <div key={i} style={{ whiteSpace: "nowrap" }}>
          {line}
        </div>
      ))}
    </div>
  );
};

/* --------------------------- Cinematic caption --------------------------- */
const CinematicCaption: React.FC<{
  caption: Caption;
  style: StyleProps;
}> = ({ caption, style }) => {
  const frame = useCurrentFrame();
  const total = caption.end - caption.start;
  const wave = style.wave!;
  const glow = style.glow!;
  const preset = caption.preset;
  const gold = caption.emphasis === "gold";
  const lines = splitLines(caption.text);
  const size = fitSize(lines) * (caption.size ?? 1);

  const enter = Math.max(0, caption.enter_frames ?? wave.entrance_frames);
  const exit = Math.max(0, caption.exit_frames ?? wave.exit_frames);
  const letters = lines.reduce((n, l) => n + l.length, 0);
  const stagger = Math.min(wave.stagger_total_frames, Math.max(0, enter - 2));
  const perLetter = Math.max(2, enter - stagger);

  // Rise height per preset (the wave settles in a stable, perfectly readable position).
  const rise =
    preset === "wave_reveal"
      ? wave.rise_px
      : preset === "smooth_replace"
        ? wave.rise_px * 0.6
        : preset === "glow_pop"
          ? wave.rise_px * 0.45
          : 0;
  const animated = enter > 0 && preset !== "immediate_impact";

  // Exit: short fade (+ tiny upward drift) inside the last `exit` frames of the phrase window.
  const exitProgress =
    exit > 0 && preset !== "immediate_impact" && preset !== "glow_pop"
      ? clamp01((frame - (total - exit)) / exit)
      : 0;

  // Glow rises briefly as the phrase lands, then settles. No pulsing: monotonic rise then a smooth settle.
  const landing = Math.max(1, enter);
  const settleEnd = landing + glow.settle_frames;
  const strong = preset === "glow_pop" || gold;
  const glowScale =
    total < (style.min_glow_frames ?? 14) && !strong ? 0 : strong ? 1 : 0.45;
  const boost =
    preset === "immediate_impact"
      ? 0
      : interpolate(frame, [0, landing, settleEnd], [0.45, 1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.inOut(Easing.quad),
        });
  const alpha = (glow.base_alpha + (glow.peak_alpha - glow.base_alpha) * boost * glowScale) * (caption.glow_strength ?? 1);
  const blur = glow.base_blur_px + (glow.peak_blur_px - glow.base_blur_px) * boost * glowScale;
  // Golden emphasis: strong while landing, then a restrained residual.
  const goldAlpha = gold ? glow.gold_alpha * (0.4 + 0.6 * boost) * (caption.glow_strength ?? 1) : 0;
  const filters = [
    `drop-shadow(0 0 ${(blur * 0.5).toFixed(1)}px ${rgba(glow.white, alpha)})`,
    `drop-shadow(0 0 ${(blur * 1.4).toFixed(1)}px ${rgba(glow.white, alpha * 0.55)})`,
    ...(gold
      ? [
          `drop-shadow(0 0 ${(blur * 1.2).toFixed(1)}px ${rgba(glow.gold, goldAlpha)})`,
          `drop-shadow(0 0 ${(blur * 2.2).toFixed(1)}px ${rgba(glow.gold, goldAlpha * 0.5)})`,
        ]
      : []),
  ].join(" ");

  const scale =
    preset === "glow_pop"
      ? interpolate(frame, [0, Math.max(1, enter)], [0.94, 1], {
          extrapolateRight: "clamp",
          easing: easeOut,
        })
      : 1;

  const softFade = preset === "soft_fade";
  const wholeOpacity = softFade
    ? interpolate(frame, [0, Math.max(4, enter)], [0, 1], {
        extrapolateRight: "clamp",
      })
    : 1;

  let index = 0;
  return (
    <div
      data-caption
      data-preset={preset}
      style={{
        position: "absolute",
        left: 98,
        width: 884,
        top: caption.y * 1920,
        transform: `translateY(-50%) scale(${scale})`,
        opacity: wholeOpacity * (1 - exitProgress),
        textAlign: "center",
        filter: caption.glow === false ? undefined : filters,
        ...baseTextStyle(size),
      }}
    >
      {lines.map((line, li) => (
        <div key={li} style={{ whiteSpace: "nowrap", height: size * 1.05 }}>
          {Array.from(line).map((ch, ci) => {
            const i = index++;
            const delay = letters > 1 ? (i / (letters - 1)) * stagger : 0;
            const p = animated
              ? easeOut(clamp01((frame - delay) / perLetter))
              : 1;
            // A gentle sine in the starting offset gives the rise its wave-like shape.
            const amplitude = rise * (0.82 + 0.18 * Math.sin(i * 1.1));
            const y = animated ? (1 - p) * amplitude - exitProgress * 8 : 0;
            const opacity = animated && !softFade ? clamp01(p * 1.7) : 1;
            return (
              <span
                key={ci}
                style={{
                  display: "inline-block",
                  whiteSpace: "pre",
                  transform: `translateY(${y.toFixed(2)}px)`,
                  opacity,
                }}
              >
                {ch === " " ? " " : ch}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export const AnimatedCaption: React.FC<{
  caption: Caption;
  style: StyleProps;
}> = ({ caption, style }) =>
  style.renderer === "cinematic" && caption.preset !== "quick_pop" ? (
    <CinematicCaption caption={caption} style={style} />
  ) : (
    <ClassicCaption caption={caption} />
  );

/* ------------------------------ Scene layers ------------------------------ */
export const FadeIn: React.FC<{ frames: number; children: React.ReactNode }> = ({
  frames,
  children,
}) => {
  const frame = useCurrentFrame();
  const opacity =
    frames > 0
      ? interpolate(frame, [0, frames], [0, 1], {
          extrapolateRight: "clamp",
          easing: Easing.inOut(Easing.quad),
        })
      : 1;
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};

export const DipOverlay: React.FC<{ frames: number; color: string }> = ({
  frames,
  color,
}) => {
  const frame = useCurrentFrame();
  const out = Math.floor(frames / 2);
  // Fully charcoal exactly on the boundary frame, where the hidden hard cut happens underneath.
  const opacity =
    frame < out
      ? interpolate(frame, [0, out], [0, 1], {
          easing: Easing.in(Easing.quad),
        })
      : interpolate(frame, [out, frames], [1, 0], {
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.quad),
        });
  return <AbsoluteFill style={{ background: color, opacity }} />;
};

export const useCaptionFonts = () => {
  const [fontHandle] = useState(() =>
    delayRender("Load licensed caption and supporting fonts"),
  );
  useEffect(() => {
    Promise.all([
      document.fonts.load('800 82px "Barlow Condensed"'),
      document.fonts.load('600 60px "Atkinson Hyperlegible Next"'),
    ])
      .then((fonts) => {
        if (fonts.some((f) => !f.length))
          throw new Error("Required font unavailable; fallback prohibited");
        continueRender(fontHandle);
      })
      .catch(cancelRender);
  }, [fontHandle]);
};

export const OddFrameReel: React.FC<ReelProps> = (props) => {
  useCaptionFonts();
  if (props.audioSources.join(",") !== "narration,instrumental")
    throw new Error("Exactly narration + instrumental required");
  if (!props.captions.length) throw new Error("Center captions are mandatory");
  const style = props.style ?? CLASSIC_STYLE;
  const allowed = style.allowed_transitions;
  const dipColor = style.dip_color ?? "#14171C";
  props.scenes.forEach((shot, i) => {
    if (shot.motion !== "static")
      throw new Error("Illustrations must stay static");
    if (!TRANSITIONS.includes(shot.transition) || !allowed.includes(shot.transition))
      throw new Error("Transition not permitted by the pinned style: " + shot.transition);
    if (i === 0 && shot.transition !== "cut")
      throw new Error("The first scene cannot have a transition");
  });
  props.captions.forEach((caption) => {
    if (!PRESETS.includes(caption.preset))
      throw new Error("Unknown caption preset: " + caption.preset);
  });
  if (style.renderer === "cinematic" && (!style.wave || !style.glow))
    throw new Error("Cinematic style is missing wave/glow parameters");
  return (
    <AbsoluteFill style={{ background: "#14171C" }}>
      {props.scenes.map((shot, i) => {
        const next = props.scenes[i + 1];
        const frames = shot.transition_frames ?? 0;
        let from = shot.start;
        let to = shot.end;
        let fadeIn = 0;
        if (i > 0 && shot.transition === "crossfade") {
          from = shot.start - Math.floor(frames / 2);
          fadeIn = frames;
        }
        if (next && next.transition === "crossfade")
          to = shot.end + Math.ceil((next.transition_frames ?? 0) / 2);
        return (
          <Sequence key={shot.id} from={from} durationInFrames={to - from}>
            <FadeIn frames={fadeIn}>
              <Img
                src={shot.image}
                style={{ width: 1080, height: 1920, objectFit: "contain" }}
              />
            </FadeIn>
          </Sequence>
        );
      })}
      {props.scenes.map((shot) =>
        shot.transition === "dip_to_dark" && (shot.transition_frames ?? 0) > 1 ? (
          <Sequence
            key={"dip-" + shot.id}
            from={shot.start - Math.floor((shot.transition_frames ?? 0) / 2)}
            durationInFrames={shot.transition_frames ?? 0}
          >
            <DipOverlay frames={shot.transition_frames ?? 0} color={dipColor} />
          </Sequence>
        ) : null,
      )}
      {props.captions.map((caption, i) => (
        <Sequence
          key={i}
          from={caption.start}
          durationInFrames={caption.end - caption.start}
        >
          <AnimatedCaption caption={caption} style={style} />
        </Sequence>
      ))}
      {props.sample && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 70,
            textAlign: "center",
            fontFamily: "Atkinson Hyperlegible Next",
            fontWeight: 600,
            fontSize: 34,
            color: "#F1EBDD",
            background: "rgba(20,23,28,.82)",
            padding: "14px 0",
          }}
        >
          SAMPLE ASSETS FOR STYLE DEMONSTRATION — NOT THIS EPISODE
        </div>
      )}
      <Audio src={props.narration} muted={props.audition?.narration_muted} volume={props.audio?.narration_gain ?? 1} />
      <Audio src={props.instrumental} muted={props.audition?.music_muted} volume={(f) => {
        const audio = props.audio;
        if (!audio) return 1;
        const fadeIn = audio.fade_in ? Math.min(1, f / audio.fade_in) : 1;
        const fadeOut = audio.fade_out ? Math.min(1, (props.durationInFrames - 1 - f) / audio.fade_out) : 1;
        return Math.max(0, audio.music_gain * fadeIn * fadeOut * (1 - audio.ducking * (audio.envelope[f] ?? 0)));
      }} />
    </AbsoluteFill>
  );
};


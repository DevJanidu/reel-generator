import React, {useEffect, useState} from "react";
import {AbsoluteFill, Audio, Easing, Img, Sequence, cancelRender, continueRender, delayRender, staticFile, useVideoConfig} from "remotion";
import {linearTiming} from "@remotion/transitions";
import type {TransitionPresentation, TransitionPresentationComponentProps, TransitionTiming} from "@remotion/transitions";
import {fade, type FadeProps} from "@remotion/transitions/fade";
import {
  AnimatedCaption,
  DipOverlay,
  FadeIn,
  type Caption,
  type Preset,
  type StyleProps,
} from "./composition";

/*
 * ODD FRAME shared effect components for Remotion Studio compositions.
 * Everything here is frame-based (no timers), static for the artwork, and has no sound effects.
 * Episode compositions are generated from these building blocks so each scene, caption and audio track
 * shows up as its own named Sequence in the official Studio timeline.
 */
export type {Caption, Preset, StyleProps};

export const BACKGROUND = "#14171C";

/** Stills never move. `fadeInFrames` > 0 is the crossfade-in over the previous still. */
export const StaticStoryScene: React.FC<{
  src: string;
  fadeInFrames?: number;
}> = ({src, fadeInFrames = 0}) => (
  <FadeIn frames={fadeInFrames}>
    <Img src={src} style={{width: 1080, height: 1920, objectFit: "contain"}} />
  </FadeIn>
);

/** A hard cut needs no overlay: the next scene's Sequence simply starts. Kept as an explicit, named no-op. */
export const HardCutTransition: React.FC<{children?: React.ReactNode}> = ({
  children,
}) => <>{children}</>;

/** Crossfade: wrap the incoming scene. */
export const CrossfadeTransition: React.FC<{
  frames: number;
  children: React.ReactNode;
}> = ({frames, children}) => <FadeIn frames={frames}>{children}</FadeIn>;

/** Dip to charcoal: rendered in its own Sequence centred on the scene boundary (projects generated before v1). */
export const DipToDarkTransition: React.FC<{color?: string}> = ({
  color = BACKGROUND,
}) => {
  const {durationInFrames} = useVideoConfig();
  return <DipOverlay frames={durationInFrames} color={color} />;
};

/*
 * ODD_FRAME_CINEMATIC_TRANSITIONS_V1 — presentations for the official @remotion/transitions TransitionSeries.
 * Only opacity and a flat colour layer: no slides, wipes, zooms, flips or any movement of the artwork, and silent.
 * A TransitionSeries overlaps neighbouring scenes by the transition length; the generated Episode.tsx gives every
 * still half of each neighbouring transition as a handle, so the visual midpoint of every transition sits exactly on
 * the narration-grounded scene boundary and the total duration never changes.
 */
const smooth = Easing.inOut(Easing.quad);

/** Frame-exact timing for a transition of `frames` frames (eased, deterministic). */
export const transitionTiming = (frames: number): TransitionTiming =>
  linearTiming({durationInFrames: frames, easing: smooth});

/** Short / emotional crossfade: the incoming still fades in over the outgoing one (no luminance dip, no black). */
export const crossfade = (): TransitionPresentation<FadeProps> => fade();

type DipProps = {color: string};

const DipPresentation: React.FC<TransitionPresentationComponentProps<DipProps>> = ({
  children,
  presentationDirection,
  presentationProgress,
  passedProps,
}) => {
  const p = presentationProgress;
  const exiting = presentationDirection === "exiting";
  // First half: outgoing still sinks into charcoal. Second half: incoming still rises out of it.
  const visible = exiting ? p < 0.5 : p >= 0.5;
  const veil = exiting ? Math.min(1, p * 2) : Math.min(1, Math.max(0, (1 - p) * 2));
  return (
    <AbsoluteFill style={{opacity: visible ? 1 : 0}}>
      {children}
      <AbsoluteFill style={{backgroundColor: passedProps.color, opacity: veil}} />
    </AbsoluteFill>
  );
};

/** Dip to charcoal (#14171C by default): out to the colour, then in from it, centred on the boundary. */
export const dipToCharcoal = (color: string = BACKGROUND): TransitionPresentation<DipProps> => ({
  component: DipPresentation,
  props: {color},
});

type CaptionBase = {
  text: string;
  y: number;
  style: StyleProps;
  size?: number;
  glow?: boolean;
  glow_strength?: number;
  enter_frames?: number;
  exit_frames?: number;
};

const CaptionInSequence: React.FC<CaptionBase & {
  preset: Preset;
  emphasis?: "none" | "gold";
}> = ({preset, emphasis = "none", style, ...rest}) => {
  const {durationInFrames} = useVideoConfig();
  const caption: Caption = {
    start: 0,
    end: durationInFrames,
    preset,
    emphasis,
    ...rest,
  };
  return <AnimatedCaption caption={caption} style={style} />;
};

/** Letters rise in a smooth wave, then hold perfectly still. */
export const WaveCaption: React.FC<CaptionBase> = (p) => (
  <CaptionInSequence {...p} preset="wave_reveal" />
);
/** Short glow rise as the phrase lands; `gold` adds the restrained golden emphasis. */
export const GlowCaption: React.FC<CaptionBase & {gold?: boolean}> = ({
  gold,
  ...p
}) => <CaptionInSequence {...p} preset="glow_pop" emphasis={gold ? "gold" : "none"} />;
/** Continuous phrases: a gentler rise so one phrase flows into the next. */
export const SmoothPhraseCaption: React.FC<CaptionBase> = (p) => (
  <CaptionInSequence {...p} preset="smooth_replace" />
);
const ImpactCaption: React.FC<CaptionBase> = (p) => (
  <CaptionInSequence {...p} preset="immediate_impact" />
);
const SoftCaption: React.FC<CaptionBase> = (p) => (
  <CaptionInSequence {...p} preset="soft_fade" />
);
const ClassicQuickPop: React.FC<CaptionBase> = (p) => (
  <CaptionInSequence {...p} preset="quick_pop" />
);

/** Picks the component for a preset name (used when a caption's preset is changed in props/source). */
export const CaptionSwitcher: React.FC<
  CaptionBase & {preset: Preset; emphasis?: "none" | "gold"}
> = ({preset, emphasis = "none", ...p}) => {
  switch (preset) {
    case "wave_reveal":
      return <WaveCaption {...p} />;
    case "glow_pop":
      return <GlowCaption {...p} gold={emphasis === "gold"} />;
    case "smooth_replace":
      return <SmoothPhraseCaption {...p} />;
    case "immediate_impact":
      return <ImpactCaption {...p} />;
    case "soft_fade":
      return <SoftCaption {...p} />;
    default:
      return <ClassicQuickPop {...p} />;
  }
};

export type AudioControls = {
  narration_gain: number;
  music_gain: number;
  fade_in: number;
  fade_out: number;
  ducking: number;
};

/** Narration: independent source, full length, only its gain is adjustable. */
export const NarrationTrack: React.FC<{src: string; gain: number}> = ({
  src,
  gain,
}) => <Audio src={src} volume={gain} />;

/** Signature instrumental: independent, continuous; fades and narration-priority ducking from the envelope. */
export const MusicTrack: React.FC<{
  src: string;
  audio: AudioControls;
  envelope: number[];
  totalFrames: number;
}> = ({src, audio, envelope, totalFrames}) => (
  <Audio
    src={src}
    volume={(f) => {
      const fadeIn = audio.fade_in ? Math.min(1, f / audio.fade_in) : 1;
      const fadeOut = audio.fade_out
        ? Math.min(1, (totalFrames - 1 - f) / audio.fade_out)
        : 1;
      return Math.max(
        0,
        audio.music_gain * fadeIn * fadeOut * (1 - audio.ducking * (envelope[f] ?? 0)),
      );
    }}
  />
);

/** Both sources as named Sequences, exactly the two intended sources and nothing else. */
export const SignatureAudioMix: React.FC<{
  narrationSrc: string;
  instrumentalSrc: string;
  audio: AudioControls;
  envelope: number[];
  totalFrames: number;
}> = ({narrationSrc, instrumentalSrc, audio, envelope, totalFrames}) => (
  <>
    <Sequence name="NARRATION — ElevenLabs" from={0} durationInFrames={totalFrames} layout="none">
      <NarrationTrack src={narrationSrc} gain={audio.narration_gain} />
    </Sequence>
    <Sequence name="MUSIC — Signature Instrumental" from={0} durationInFrames={totalFrames} layout="none">
      <MusicTrack src={instrumentalSrc} audio={audio} envelope={envelope} totalFrames={totalFrames} />
    </Sequence>
  </>
);

/**
 * Fonts come from the episode's own public/fonts folder (staticFile) so Studio, previews and the final render all load
 * exactly the same licensed Barlow Condensed ExtraBold + Atkinson files. No fallback font is ever substituted.
 */
export const useStudioFonts = () => {
  const [handle] = useState(() => delayRender("Load ODD FRAME caption fonts"));
  useEffect(() => {
    const faces = [
      new FontFace("Barlow Condensed", `url(${staticFile("fonts/barlow-condensed-800.woff2")})`, {weight: "800"}),
      new FontFace("Atkinson Hyperlegible Next", `url(${staticFile("fonts/atkinson-hyperlegible-next-600.woff2")})`, {weight: "600"}),
    ];
    Promise.all(faces.map((f) => f.load()))
      .then((loaded) => {
        loaded.forEach((f) => (document.fonts as unknown as {add(f: FontFace): void}).add(f));
        continueRender(handle);
      })
      .catch(cancelRender);
  }, [handle]);
};

export const StudioStage: React.FC<{children: React.ReactNode}> = ({children}) => {
  useStudioFonts();
  return <AbsoluteFill style={{background: BACKGROUND}}>{children}</AbsoluteFill>;
};

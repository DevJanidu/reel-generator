"""Owner-authorized source refactor; never invoked by production workers."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'video/remotion/src/index.tsx'
original=path.read_text(encoding='utf-8')
if 'from "./composition"' in original:
    if not (root/'video/remotion/src/composition.tsx').is_file():
        raise SystemExit('Refactored entry point has no shared composition; restore it before proceeding')
    raise SystemExit(0)
component=original[:original.index('const empty: ReelProps')]
component=component.replace('  Composition,\n','').replace('  registerRoot,\n','')
component=component.replace('type Shot = {','export type Shot = {').replace('type Caption = {','export type Caption = {')
component=component.replace('  glow?: boolean;','  glow?: boolean;\n  size?: number;\n  glow_strength?: number;')
component=component.replace('  sample?: boolean;','  sample?: boolean;\n  editor_version?: number;\n  audio?: {narration_gain: number; music_gain: number; fade_in: number; fade_out: number; ducking: number; envelope: number[]};\n  audition?: {narration_muted: boolean; music_muted: boolean};')
component=component.replace('const size = fitSize(lines, 850);','const size = fitSize(lines, 850) * (caption.size ?? 1);').replace('const size = fitSize(lines);','const size = fitSize(lines) * (caption.size ?? 1);')
component=component.replace('filter: filters,','filter: caption.glow === false ? undefined : filters,')
component=component.replace('const alpha = glow.base_alpha + (glow.peak_alpha - glow.base_alpha) * boost * glowScale;','const alpha = (glow.base_alpha + (glow.peak_alpha - glow.base_alpha) * boost * glowScale) * (caption.glow_strength ?? 1);')
component=component.replace('const goldAlpha = gold ? glow.gold_alpha * (0.4 + 0.6 * boost) : 0;','const goldAlpha = gold ? glow.gold_alpha * (0.4 + 0.6 * boost) * (caption.glow_strength ?? 1) : 0;')
component=component.replace('<Audio src={props.narration} />','<Audio src={props.narration} muted={props.audition?.narration_muted} volume={props.audio?.narration_gain ?? 1} />')
component=component.replace('<Audio src={props.instrumental} />','''<Audio src={props.instrumental} muted={props.audition?.music_muted} volume={(f) => {
        const audio = props.audio;
        if (!audio) return 1;
        const fadeIn = audio.fade_in ? Math.min(1, f / audio.fade_in) : 1;
        const fadeOut = audio.fade_out ? Math.min(1, (props.durationInFrames - 1 - f) / audio.fade_out) : 1;
        return Math.max(0, audio.music_gain * fadeIn * fadeOut * (1 - audio.ducking * (audio.envelope[f] ?? 0)));
      }} />''')
(root/'video/remotion/src/composition.tsx').write_text(component,encoding='utf-8')
path.write_text('import React from "react";\nimport {Composition, registerRoot} from "remotion";\nimport {OddFrameReel, type ReelProps} from "./composition";\nexport {OddFrameReel, type ReelProps} from "./composition";\n'+original[original.index('const empty: ReelProps'):],encoding='utf-8')

// Quick checks of an episode's OFFICIAL Remotion Studio project without exporting a full MP4.
// Usage: node preview-studio.mjs <studioDir> <compositionId> <outDir> [--frames 10,11,12] [--range 200-260]
//   --frames  renders individual PNG stills (frame-exact inspection around scene transitions)
//   --range   renders a short H.264/AAC clip of only those frames (e.g. one transition with its audio)
// Bundles once and reuses the bundle for every frame. Writes only inside <outDir>.
import { bundle } from "@remotion/bundler";
import { renderStill, renderMedia, selectComposition, ensureBrowser } from "@remotion/renderer";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const [studioArg, compositionId, outArg, ...rest] = process.argv.slice(2);
if (!studioArg || !compositionId || !outArg)
  throw new Error("Usage: node preview-studio.mjs <studioDir> <compositionId> <outDir> [--frames a,b] [--range a-b]");
const studioDir = path.resolve(studioArg);
const outDir = path.resolve(outArg);
const arg = (name) => {
  const i = rest.indexOf(name);
  return i >= 0 ? rest[i + 1] : undefined;
};
const frames = (arg("--frames") || "").split(",").filter(Boolean).map(Number);
const range = arg("--range") ? arg("--range").split("-").map(Number) : null;
if (frames.some((f) => !Number.isInteger(f) || f < 0)) throw new Error("--frames must be non-negative integers");
const appRoot = process.env.ODD_APP_ROOT || process.cwd();
await mkdir(outDir, { recursive: true });
const t0 = performance.now();
const browser = await ensureBrowser();
const serveUrl = await bundle({
  enableCaching: false, // never writes a webpack cache into the episode folder
  entryPoint: path.join(studioDir, "src/index.ts"),
  publicDir: path.join(studioDir, "public"),
  outDir: path.join(outDir, "bundle"),
  webpackOverride: (config) => ({
    ...config,
    cache: false,
    resolve:{ ...config.resolve, modules: [path.join(appRoot, "node_modules"), "node_modules"] },
  }),
});
const bundled = performance.now();
const composition = await selectComposition({ serveUrl, id: compositionId, inputProps: {}, browserExecutable: browser.path });
const timings = [];
for (const frame of frames) {
  const started = performance.now();
  await renderStill({
    serveUrl,
    composition,
    frame,
    inputProps: {},
    output: path.join(outDir, `frame-${String(frame).padStart(5, "0")}.png`),
    browserExecutable: browser.path,
  });
  timings.push({ frame, ms: Math.round(performance.now() - started) });
}
let clip = null;
if (range) {
  const started = performance.now();
  const output = path.join(outDir, `range-${range[0]}-${range[1]}.mp4`);
  await renderMedia({
    serveUrl,
    composition,
    inputProps: {},
    codec: "h264",
    audioCodec: "aac",
    frameRange: [range[0], range[1]],
    outputLocation: output,
    browserExecutable: browser.path,
    binariesDirectory: path.join(appRoot, "video/remotion/runtime-binaries"),
  });
  clip = { output, frames: range[1] - range[0] + 1, ms: Math.round(performance.now() - started) };
}
const result = {
  composition: { id: composition.id, width: composition.width, height: composition.height, fps: composition.fps, durationInFrames: composition.durationInFrames },
  bundle_ms: Math.round(bundled - t0),
  stills: timings,
  clip,
};
await writeFile(path.join(outDir, "preview.json"), JSON.stringify(result, null, 2));
console.log("PREVIEW " + JSON.stringify(result));

// Final render of the episode's OFFICIAL Remotion Studio project (the exact source the owner reviewed in Studio).
// Usage: node render-studio.mjs <studioDir> <compositionId> <output.mp4> [meta.json]
// No inputProps are passed: the composition's saved defaultProps (edited in Studio) are authoritative.
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition, ensureBrowser } from "@remotion/renderer";
import { writeFile } from "node:fs/promises";
import path from "node:path";

const [studioDir, compositionId, output, metaPath] = process.argv.slice(2);
if (!studioDir || !compositionId || !output)
  throw new Error("Usage: node render-studio.mjs <studioDir> <compositionId> <output.mp4> [meta.json]");
const appRoot = process.env.ODD_APP_ROOT || process.cwd();
const episodeRoot = process.env.EPISODE_WRITE_ROOT;
if (!episodeRoot) throw new Error("Rendering requires an assigned isolated episode root");
const tempRoot = path.join(episodeRoot, ".production/temp", process.env.ODD_JOB_ID || "studio-render");

const browser = await ensureBrowser();
const serveUrl = await bundle({
  enableCaching: false,
  entryPoint: path.join(studioDir, "src/index.ts"),
  publicDir: path.join(studioDir, "public"),
  outDir: path.join(tempRoot, "studio-bundle"),
  webpackOverride: (config) => ({
    ...config,
    cache: false,
    resolve: { ...config.resolve, modules: [path.join(appRoot, "node_modules"), "node_modules"] },
  }),
});
const composition = await selectComposition({
  serveUrl,
  id: compositionId,
  inputProps: {},
  browserExecutable: browser.path,
});
if (composition.width !== 1080 || composition.height !== 1920 || composition.fps !== 30)
  throw new Error("The Studio composition is not 1080x1920 at 30 fps");
const meta = {
  id: composition.id,
  width: composition.width,
  height: composition.height,
  fps: composition.fps,
  durationInFrames: composition.durationInFrames,
  props: composition.props,
};
if (metaPath) await writeFile(metaPath, JSON.stringify(meta, null, 2));
console.log("META " + JSON.stringify({ durationInFrames: meta.durationInFrames }));
let last = -1;
await renderMedia({
  serveUrl,
  composition,
  inputProps: {},
  codec: "h264",
  audioCodec: "aac",
  pixelFormat: "yuv420p",
  outputLocation: output,
  crf: 18,
  concurrency: 2,
  disallowParallelEncoding: true,
  disableSharedMemoryCapture: true,
  binariesDirectory: path.join(appRoot, "video/remotion/runtime-binaries"),
  logLevel: "verbose",
  browserExecutable: browser.path,
  onProgress: ({ progress, renderedFrames, encodedFrames }) => {
    const p = Math.floor(progress * 100);
    if (p !== last) {
      last = p;
      process.stdout.write(`PROGRESS ${progress}\n`);
      process.stdout.write(`RENDER_EVENT ${JSON.stringify({ renderedFrames, encodedFrames })}\n`);
    }
  },
});
console.log("DONE " + output);

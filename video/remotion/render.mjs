import { bundle } from "@remotion/bundler";
import {
  renderMedia,
  selectComposition,
  ensureBrowser,
} from "@remotion/renderer";
import { readFile } from "node:fs/promises";
import path from "node:path";
const [propsPath, output, mode] = process.argv.slice(2);
if (!propsPath || !output)
  throw new Error(
    "Usage: node video/remotion/render.mjs props.json output.mp4 [preview|final]",
  );
const props = JSON.parse(await readFile(propsPath, "utf8"));
const appRoot = process.env.ODD_APP_ROOT || process.cwd();
const episodeRoot = process.env.EPISODE_WRITE_ROOT;
if (!episodeRoot)
  throw new Error("Rendering requires an assigned isolated episode root");
const tempRoot = path.join(
  episodeRoot,
  ".production/temp",
  process.env.ODD_JOB_ID || "render",
);
if (props.width !== 1080 || props.height !== 1920 || props.fps !== 30)
  throw new Error("Invalid output profile");
const allowedTransitions = props.style?.allowed_transitions ?? ["cut"];
if (
  props.scenes.some(
    (s) => s.motion !== "static" || !allowedTransitions.includes(s.transition),
  )
)
  throw new Error("Image movement or a transition outside the pinned style is prohibited");
const rendererDir = props.style?.renderer_dir || "remotion";
const browser = await ensureBrowser();
const serveUrl = await bundle({
  enableCaching: false,
  // "@app" is only used by Preview Style to show a profile this episode has not pinned (shared code, read-only).
  entryPoint:
    props.editor_version === 1 ? path.join(episodeRoot, "06_edit/remotion/editor-v1/src/index.tsx") : rendererDir === "@app"
      ? path.join(appRoot, "video/remotion/src/index.tsx")
      : path.join(
          episodeRoot,
          ".production/input_snapshot",
          rendererDir,
          "src/index.tsx",
        ),
  outDir: path.join(tempRoot, "remotion-bundle"),
  webpackOverride: (config) => ({
    ...config,
    cache: false,
    resolve: {
      ...config.resolve,
      modules: [path.join(appRoot, "node_modules"), "node_modules"],
    },
  }),
});
const composition = await selectComposition({
  serveUrl,
  id: "OddFrameReel",
  inputProps: props,
  browserExecutable: browser.path,
});
let last = -1;
await renderMedia({
  serveUrl,
  composition,
  inputProps: props,
  codec: "h264",
  audioCodec: "aac",
  pixelFormat: "yuv420p",
  outputLocation: output,
  ...(Array.isArray(props.render_range)
    ? { frameRange: [props.render_range[0], props.render_range[1]] }
    : {}),
  scale: mode === "preview" ? 0.5 : 1,
  crf: mode === "preview" ? 28 : 18,
  concurrency: 2,
  disallowParallelEncoding: true,
  disableSharedMemoryCapture: true,
  binariesDirectory: path.join(appRoot, "video/remotion/runtime-binaries"),
  logLevel: "verbose",
  browserExecutable: browser.path,
  onProgress: ({ progress, renderedFrames, encodedFrames }) => {
    let p = Math.floor(progress * 100);
    if (p !== last) {
      last = p;
      process.stdout.write(`PROGRESS ${progress}\n`);
      process.stdout.write(`RENDER_EVENT ${JSON.stringify({renderedFrames, encodedFrames})}\n`);
    }
  },
});
console.log("DONE " + output);

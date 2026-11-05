import { ensureBrowser } from "@remotion/renderer";
const result = await ensureBrowser();
console.log("Remotion browser: " + result.path);

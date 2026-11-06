// Development only: no production database, credentials or native workers are copied.
import { spawn } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { createServer } from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const store = path.join(root, "artifacts", "preview-data");
for (const port of [5174, 8124])
  await new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once("error", () =>
      reject(
        Error(
          `Port ${port} is occupied. Stop only the previous preview processes before restarting.`,
        ),
      ),
    );
    probe.listen(port, "127.0.0.1", () => probe.close(resolve));
  });
await mkdir(store, { recursive: true });
const python =
  process.env.ODD_DEV_PYTHON || "E:/facebook/.venv/Scripts/python.exe";
const backend = spawn(
  python,
  [
    "-m",
    "uvicorn",
    "services.api.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8124",
  ],
  {
    cwd: root,
    env: {
      ...process.env,
      ODD_DATA_ROOT: store,
      ODD_AI_PROVIDER: "manual",
      ODD_PORT: "5174",
    },
    windowsHide: true,
    stdio: "inherit",
  },
);
const frontend = spawn(
  process.execPath,
  [
    path.join(root, "node_modules/vite/bin/vite.js"),
    "--config",
    "vite.config.ts",
  ],
  {
    cwd: path.join(root, "apps/dashboard"),
    windowsHide: true,
    stdio: "inherit",
  },
);
let stopping = false;
function stop() {
  if (stopping) return;
  stopping = true;
  backend.kill();
  frontend.kill();
}
process.on("SIGINT", stop);
process.on("SIGTERM", stop);
backend.on("exit", stop);
frontend.on("exit", stop);
console.log(
  "Disposable development preview: http://127.0.0.1:5174 • backend 8124 • manual provider. Ctrl+C stops both.",
);

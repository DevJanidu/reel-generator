import React, { useEffect, useState } from "react";
import { mountStudio, queryClient } from "./router";
import { StudioPanel } from "./studio";
import { IdeasStudio } from "./ideas";
import { Paged } from "./paging";
import { ExportsPanel } from "./exports";
import {
  LayoutDashboard,
  BookOpen,
  Sparkles,
  FileText,
  FolderOpen,
  Image,
  Film,
  Download,
  Settings,
  BarChart3,
  Plus,
  ArrowRight,
  Check,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  Clapperboard,
  Upload,
  Search,
  ShieldCheck,
  Clock,
} from "lucide-react";
import "./style.css";
import "./select.css";

const controllerFromLaunch = new URLSearchParams(
  window.location.hash.slice(1),
).get("controller");
if (controllerFromLaunch) {
  sessionStorage.setItem("odd-frame-controller", controllerFromLaunch);
  localStorage.setItem("odd-frame-controller", controllerFromLaunch);
  history.replaceState(null, "", window.location.pathname);
}

type Data = Record<string, any>;
const pages = [
  ["Home", LayoutDashboard],
  ["Master Prompt", BookOpen],
  ["Ideas", Sparkles],
  ["Script Studio", FileText],
  ["Episode Workspace", FolderOpen],
  ["Google Flow Prompts", Image],
  ["Asset Manager", Upload],
  ["Edit Studio", Film],
  ["Exports", Download],
  ["Analytics", BarChart3],
  ["Settings", Settings],
] as const;
async function api(path: string, method = "GET", body?: any) {
  const res = await fetch("/api" + path, {
    method,
    headers:
      body instanceof FormData
        ? {
            "X-Odd-Controller":
              (localStorage.getItem("odd-frame-controller") || sessionStorage.getItem("odd-frame-controller") || ""),
          }
        : {
            "Content-Type": "application/json",
            "X-Odd-Controller":
              (localStorage.getItem("odd-frame-controller") || sessionStorage.getItem("odd-frame-controller") || ""),
          },
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok)
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail),
    );
  return data;
}
const assetTodo = (errors: string[] = []) => {
  const missing = (e: string) => /found 0/.test(e);
  const images = errors.filter((e) => /^S\d+:/.test(e) && missing(e)).length;
  const narration = errors.some((e) => e.startsWith("narration:") && missing(e));
  const music = errors.some((e) => e.startsWith("music:") && missing(e));
  const subtitles = errors.some((e) => e.startsWith("subtitles:") && missing(e));
  const confirmMusic = errors.some((e) => e.startsWith("Music: confirm"));
  const other = errors.filter(
    (e) => !missing(e) && !e.startsWith("Music: confirm"),
  );
  return { images, narration, music, subtitles, confirmMusic, other };
};
const Badge = ({ value }: { value: string }) => (
  <span
    className={
      "badge " +
      (value === "COMPLETE" || value === "LOADED" || value === "SUCCEEDED"
        ? "green"
        : value.includes("FAIL") ||
            (value.includes("BLOCK") && value !== "ASSETS_BLOCKED") ||
            value === "MISSING"
          ? "red"
          : "")
    }
  >
    {value === "ASSETS_BLOCKED" ? "NEEDS ASSETS" : value.replaceAll("_", " ")}
  </span>
);
const Empty = ({ text }: { text: string }) => (
  <div className="empty">
    <Clapperboard size={34} />
    <p>{text}</p>
  </div>
);

function App() {
  const [page, setPage] = useState("Home"),
    [status, setStatus] = useState<Data>(),
    [episodes, setEpisodes] = useState<Data[]>([]),
    [selected, setSelected] = useState<number>(),
    [ep, setEp] = useState<Data>(),
    [runs, setRuns] = useState<Data[]>([]),
    [ideas, setIdeas] = useState<Data[]>([]),
    [master, setMaster] = useState(""),
    [busy, setBusy] = useState(""),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all"),
    [script, setScript] = useState(""),
    [brief, setBrief] = useState(""),
    [importText, setImportText] = useState(""),
    [runId, setRunId] = useState(""),
    [custom, setCustom] = useState({
      title: "",
      genre: "Mystery",
      premise: "",
    }),
    [prefs, setPrefs] = useState<Data>(),
    [rights, setRights] = useState(""),
    [instrumental, setInstrumental] = useState(false),
    [metrics, setMetrics] = useState(""),
    [metricRows, setMetricRows] = useState<Data[]>([]);
  const [providerInfo, setProviderInfo] = useState<Data>();
  const [credentials, setCredentials] = useState<Data[]>([]);
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [testing, setTesting] = useState<string>("");
  const runTest = async (provider: string) => {
    setTesting(provider);
    setConnectionResults((v) => ({ ...v, [provider]: undefined as any }));
    try {
      const r = await api("/providers/" + provider + "/test", "POST");
      setConnectionResults((v) => ({ ...v, [provider]: r }));
      return r;
    } catch (e: any) {
      const r = { success: false, code: "NOT_RUN", message: e.message };
      setConnectionResults((v) => ({ ...v, [provider]: r }));
      return r;
    } finally {
      setTesting("");
      api("/providers").then(setProviderInfo).catch(() => {});
    }
  };
  const [accessKey, setAccessKey] = useState("");
  const checkAuthorization = () =>
    api("/controller/status").then((r) => setAuthorized(!!r.authorized)).catch(() => setAuthorized(null));
  const [tokenDraft, setTokenDraft] = useState<Record<string, string>>({});
  const [connectionResults, setConnectionResults] = useState<
    Record<string, Data>
  >({});
  const reload = async () => {
    const [s, e, r] = await Promise.all([
      queryClient.fetchQuery({queryKey:["status"],queryFn:()=>api("/status")}),
      queryClient.fetchQuery({queryKey:["episodes"],queryFn:()=>api("/episodes")}),
      queryClient.fetchQuery({queryKey:["runs"],queryFn:()=>api("/runs")}),
    ]);
    setStatus(s);
    setEpisodes(e);
    setRuns(r);
    if (selected) {
      setEp(await queryClient.fetchQuery({queryKey:["episode",selected],queryFn:()=>api("/episodes/" + selected)}));
    }
  };
  useEffect(() => {
    reload().catch((e) => setError(e.message));
    const t = setInterval(() => reload().catch(() => {}), 5000);
    return () => clearInterval(t);
  }, [selected]);
  const [nowMs, setNowMs] = useState(Date.now());
  const [musicDb, setMusicDb] = useState(0);
  const [previewMix, setPreviewMix] = useState<Data | null>(null);
  const [styleSel, setStyleSel] = useState("");
  const [rerenderOnSave, setRerenderOnSave] = useState(false);
  const [trDraft, setTrDraft] = useState<Record<string, string> | null>(null);
  useEffect(() => {
    setStyleSel("");
    setRerenderOnSave(false);
    setTrDraft(null);
  }, [selected]);
  useEffect(() => {
    if (ep && ep.id === selected)
      setMusicDb(Number(ep.data?.music_mix?.offset_db ?? 0));
  }, [ep?.id, ep?.data?.music_mix?.offset_db]);
  useEffect(() => setPreviewMix(null), [selected]);
  const anyActiveRun = runs.some((r) =>
    ["QUEUED", "RUNNING"].includes(r.status),
  );
  useEffect(() => {
    if (!anyActiveRun) return;
    const fast = setInterval(() => {
      setNowMs(Date.now());
      reload().catch(() => {});
    }, 1500);
    return () => clearInterval(fast);
  }, [anyActiveRun, selected]);
  useEffect(() => {
    api("/master").then((v) => setMaster(v.content));
    api("/settings").then(setPrefs);
    api("/metrics").then(setMetricRows);
    api("/providers").then(setProviderInfo);
    api("/providers/credentials").then((r) => setCredentials(r.credentials));
    checkAuthorization();
  }, []);
  useEffect(() => {
    const run = runs.find((r) => r.id === runId);
    if (run?.task === "ideas" && run.status === "SUCCEEDED")
      api("/runs/" + runId + "/result").then((r) => {
        if (r.result?.ideas) setIdeas(r.result.ideas);
      });
  }, [runs, runId]);
  useEffect(() => {
    if (ep && ep.id === selected) {
      setScript(ep.data.script?.narration || "");
      setBrief(ep.data.script?.brief || "");
      setRights(ep.data.music_rights?.evidence || "");
      setInstrumental(ep.data.music_rights?.instrumental_confirmed || false);
    }
  }, [ep?.id, ep?.data.script?.narration]);
  const act = async (label: string, fn: () => Promise<any>) => {
    setBusy(label);
    setError("");
    setNotice("");
    try {
      const result = await fn();
      await reload();
      setNotice(result?.message || label + " completed");
      return result;
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  };
  const choose = async (idea: Data) => {
    const result = await act("Select story", () =>
      api("/episodes", "POST", idea),
    );
    if (result) {
      setSelected(result.id);
      setPage("Script Studio");
      if (status?.settings?.provider !== "manual") {
        const generated = await act("Queue script and retention review", () =>
          api("/episodes/" + result.id + "/script", "POST"),
        );
        if (generated?.run_id) setRunId(generated.run_id);
      }
    }
  };
  const generate = () => {setPage("Ideas");setError("");};
  const liveIdeasRun = runs.find((r) => r.id === runId && r.task === "ideas");
  const liveRun =
    runs.find(
      (r) =>
        r.episode_id === selected &&
        ["QUEUED", "RUNNING"].includes(r.status),
    ) || runs.find((r) => r.id === runId);
  const taskLabel = (t?: string) =>
    t === "ideas"
      ? "your ideas"
      : t === "script"
        ? "the story brief and narration"
        : t === "retention"
          ? "the retention review"
          : t === "prepare"
            ? "the production package: characters, storyboard, Flow image prompts, captions and music direction"
            : "your request";
  const STEPS = [
    "Script",
    "Approve",
    "Prepare",
    "Assets",
    "Validate",
    "Render",
    "Export",
  ];
  const stepInfo = (e: Data): { step: number; text: string; warn?: boolean } => {
    const s = e.status;
    const err = e.data?.error;
    switch (s) {
      case "DRAFT":
      case "AWAITING_MANUAL":
        return {
          step: 0,
          text: "Write or generate the story brief and narration in Script Studio.",
        };
      case "SCRIPT_REVIEW":
      case "AWAITING_APPROVAL":
        return {
          step: 1,
          text: "Script is ready. Read it, edit if you like, then press APPROVE SCRIPT & CONTINUE. Approval freezes the exact wording.",
        };
      case "PREPARING":
        return {
          step: 2,
          text: "Script approved. The AI is now building the production package (characters, storyboard, Google Flow image prompts, captions, music direction). Nothing for you to do — this takes a few minutes.",
        };
      case "AWAITING_ASSETS":
        return {
          step: 3,
          text: "Preproduction is complete. Next: open Google Flow Prompts, generate the still images in Flow, then upload stills, narration audio, SRT captions and one instrumental in Asset Manager.",
        };
      case "ASSETS_BLOCKED": {
        const t = assetTodo(e.data?.asset_errors);
        return t.other.length
          ? {
              step: 3,
              warn: true,
              text:
                "Some uploaded files have a problem: " +
                String(t.other[0]) +
                " Fix it in Asset Manager.",
            }
          : {
              step: 3,
              text: "Preproduction is done. Add the files below. Valid assets automatically become an editable draft for review.",
            };
      }
      case "QUEUED":
        return {
          step: 5,
          text: "Production work is queued. Open AI Activity for the current task and verified milestones.",
        };
      case "RENDERING":
        return {
          step: 5,
          text: "Rendering the saved timeline and checking the encoded output. Keep the local station running.",
        };
      case "COMPLETE":
        return {
          step: 7,
          text: "Export complete. Open Exports to download the video.",
        };
      case "EDIT_READY":
        return {step:5,text:"Automatic edit ready. Open it in Remotion Studio from Edit Studio, make small adjustments, then render the final video."};
      case "FAILED":
        return {
          step: 5,
          warn: true,
          text:
            "The render stopped with an error: " +
            (err || "see Production history") +
            " Press Refresh Assets to retry. Your files and approved script are untouched.",
        };
      case "BLOCKED":
        return {
          step: 2,
          warn: true,
          text: "Blocked: " + (err || "see the error below") + ". You can retry once fixed.",
        };
      default:
        return { step: 0, text: String(s) };
    }
  };
  const HISTORY_TEXT: Record<string, string> = {
    DRAFT: "Story selected. Script waiting to be written and approved.",
    SCRIPT_REVIEW: "Script drafted by AI and reviewed. Ready for you to read.",
    AWAITING_APPROVAL: "Script reviewed. Waiting for your approval.",
    PREPARING: "Script approved. AI is building the production package.",
    AWAITING_ASSETS:
      "Preproduction complete. Waiting for your stills, narration, SRT and music.",
    ASSETS_BLOCKED:
      "Waiting for your files: stills, narration audio, SRT captions and music.",
    QUEUED: "Production job queued. See AI Activity for details.",
    EDIT_READY: "Automatic edit ready. Open it in Remotion Studio.",
    RENDERING: "Rendering the video.",
    COMPLETE: "Export complete.",
    BLOCKED: "Blocked. See the error shown on this page.",
  };
  const historyText = (h: Data, e: Data) => {
    const raw = String(h.message || "");
    const text =
      !raw || raw === h.stage ? HISTORY_TEXT[h.stage] || raw : raw;
    const latest = e.history?.[e.history.length - 1]?.id === h.id;
    const first = e.data?.asset_errors?.[0];
    return h.stage === "ASSETS_BLOCKED" && latest && first &&
      assetTodo(e.data?.asset_errors).other.length
      ? text + " First issue: " + String(assetTodo(e.data?.asset_errors).other[0])
      : text;
  };
  const AssetChecklist = () => {
    const total = ep?.data?.package?.scenes?.length || 18;
    const t = assetTodo(ep?.data?.asset_errors);
    const fresh = !ep?.data?.asset_errors;
    const rows: [boolean, string, string][] = [
      [
        !fresh && t.images === 0,
        `Generate ${total} still images in Google Flow (S001…)`,
        `Google Flow Prompts → download the Flow JSON, generate, then upload. ${fresh ? "" : total - t.images + " of " + total + " uploaded."}`,
      ],
      [
        !fresh && !t.narration,
        "Record or create the narration audio file",
        "Asset Manager → narration (one file)",
      ],
      [
        !fresh && !t.subtitles,
        "Create the SRT caption file (1–4 words per cue)",
        "Asset Manager → subtitles (one .srt)",
      ],
      [
        !fresh && !t.music,
        "Add one instrumental background track",
        "Asset Manager → music; confirm it is instrumental and record the license",
      ],
    ];
    return (
      <ul className="todo">
        {rows.map(([done, title, hint]) => (
          <li key={title} className={done ? "done" : ""}>
            <span>{done ? "✓" : "○"}</span>
            <div>
              <strong>{title}</strong>
              <div className="muted">{hint}</div>
            </div>
          </li>
        ))}
      </ul>
    );
  };
  const PipelineTracker = () => {
    if (!ep || !selected || ep.id !== selected) return null;
    const info = stepInfo(ep);
    const jobs = (ep.jobs || []).filter((j: Data) =>
      ["QUEUED", "RUNNING"].includes(j.status),
    );
    return (
      <section className="panel pipeline" aria-label="Production status">
        <ol className="steps">
          {STEPS.map((name, i) => (
            <li
              key={name}
              className={
                i < info.step ? "done" : i === info.step ? "current" : ""
              }
            >
              <span>{i < info.step ? "✓" : i + 1}</span>
              {name}
            </li>
          ))}
        </ol>
        <p className={info.warn ? "error" : "muted"}>{info.text}</p>
        {ep.status==='EDIT_READY'&&<button onClick={()=>setPage("Edit Studio")}>Open in Remotion Studio</button>}
        {["AWAITING_ASSETS", "ASSETS_BLOCKED"].includes(ep.status) &&
          AssetChecklist()}
        {LiveIdeasPanel()}
        {!liveRun &&
          ["PREPARING", "QUEUED", "RENDERING"].includes(ep.status) && (
            <div className="loading" role="status">
              <RefreshCw className="spin" size={16} />
              Working… this page updates automatically.
              <div className="indeterminate" aria-hidden="true" />
            </div>
          )}
        {jobs.map((j: Data) => (
          <div className="job" key={j.id}>
            <strong>
              {j.stage}
            </strong>
            {['QUEUED','RUNNING'].includes(j.status) && <progress aria-label={j.stage} />}
          </div>
        ))}
      </section>
    );
  };
  const ideasRunning = Boolean(
    liveIdeasRun && ["QUEUED", "RUNNING"].includes(liveIdeasRun.status),
  );
  const elapsedText = (created?: string) => {
    if (!created) return "";
    const s = Math.max(0, Math.floor((nowMs - Date.parse(created)) / 1000));
    return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0");
  };
  const LiveIdeasPanel = (override?: Data) => {
    const r = override || liveRun;
    if (!r) return null;
    const active = ["QUEUED", "RUNNING"].includes(r.status);
    const who = r.provider === "codex_cli" ? "Codex" : r.provider === "claude_cli" ? "Claude" : r.provider;
    return (
      <section className="panel live-run" role="status" aria-live="polite">
        <div className="section-heading">
          <h3>
            {active && <RefreshCw className="spin" size={16} />}{" "}
            {active
              ? who + " · " + (r.stage || 'Waiting to start')
              : r.status === "SUCCEEDED"
                ? "Ready: " + taskLabel(r.task)
                : "Generation " + r.status.toLowerCase()}
          </h3>
          <span className="muted">
            {active ? "Elapsed " + elapsedText(r.created) : ""}
          </span>
        </div>
        <p className="muted">
          {active
            ? "Reading all four skill documents and the master prompt first. This can take a few minutes — please keep this page open. The fields below fill in automatically when it finishes."
            : r.status === "SUCCEEDED"
              ? r.task === "ideas"
                ? "Scroll down to review the ten concepts."
                : "The story brief and narration are filled in below. Review and edit them before approving."
              : ""}
        </p>
        <strong>
          {r.provider || "manual"} · {r.stage || r.status}
        </strong>
        {active && <progress aria-label={r.stage || r.status} />}
        {active && <div className="indeterminate" aria-hidden="true" />}
        {r.error && <p className="error">{r.error}</p>}
      </section>
    );
  };
  const selectedPath = "/episodes/" + selected;
  const valid = Boolean(status?.skills?.valid);
  const validForEpisode = Boolean(ep?.pinned_inputs_valid);
  const fileURL = (relative: string) =>
    "/api/episodes/" +
    selected +
    "/file/" +
    relative.split("/").map(encodeURIComponent).join("/");
  const selectEp = (e: Data, destination = "Episode Workspace") => {
    setSelected(e.id);
    setPage(destination);
  };
  const activeRuns = runs.filter(
    (r) => !selected || r.episode_id === selected || !r.episode_id,
  );
  const episodeList = episodes.filter(
    (e) =>
      (e.title + " " + e.code).toLowerCase().includes(query.toLowerCase()) &&
      (filter === "all" || e.status === filter),
  );
  const AIProgress = () => (
    <section className="panel">
      <h3>AI generation progress</h3>
      {activeRuns.slice(0, 6).map((r) => (
        <div className="job" key={r.id}>
          <strong>
            {r.task} · {r.provider || "manual"} · {r.stage || r.status}
          </strong>
          {['QUEUED','RUNNING'].includes(r.status) && <progress aria-label={r.stage || r.status} />}
          <Badge value={r.status} />
          {r.error && <p className="error">{r.error}</p>}
          {["QUEUED", "RUNNING"].includes(r.status) && (
            <button
              className="secondary small"
              onClick={() =>
                act("Cancel AI job", () =>
                  api("/runs/" + r.id + "/cancel", "POST"),
                )
              }
            >
              Cancel job
            </button>
          )}
          {["FAILED", "CANCELLED"].includes(r.status) && (
            <button
              className="secondary small"
              onClick={() =>
                act("Retry AI job", async () => {
                  const retry = await api("/runs/" + r.id + "/retry", "POST");
                  if (retry.run_id) setRunId(retry.run_id);
                  return retry;
                })
              }
            >
              Retry generation
            </button>
          )}
        </div>
      ))}
    </section>
  );
  const ManualPanel = () =>
    status?.settings?.provider !== "manual" ? (
      AIProgress()
    ) : (
      <section className="panel manual">
        <div className="section-heading">
          <h3>Manual AI handoff</h3>
          <span className="muted">
            Full instruction bundles · no simulated generation
          </span>
        </div>
        <p>
          Download the request, give its complete system and user messages to
          your AI tool, and import the JSON response. Long responses may need a
          model with a larger output budget.
        </p>
        <div className="row">
          <select
            aria-label="Generation run"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
          >
            <option value="">
              {activeRuns.some((r) => r.task !== "genre_ideas" && r.status === "AWAITING_MANUAL")
                ? "Select a run waiting for your AI response"
                : "No runs waiting — press Generate first"}
            </option>
            {activeRuns
              .filter((r) => r.task !== "genre_ideas" && (r.status === "AWAITING_MANUAL" || r.id === runId || (r.task === "ideas" && r.status === "SUCCEEDED")))
              .map((r) => (
                <option value={r.id} key={r.id}>
                  {r.task} ·{" "}
                  {r.status === "AWAITING_MANUAL"
                    ? "waiting for response"
                    : r.status.toLowerCase()}{" "}
                  · {new Date(r.created).toLocaleTimeString()}
                </option>
              ))}
          </select>
          {runId && (
            <a
              className="button secondary"
              href={"/api/runs/" + runId + "/request"}
              download
            >
              <Download size={15} />
              Full request
            </a>
          )}
        </div>
        {runId && (
          <>
            <textarea
              aria-label="AI JSON response"
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
              placeholder="Paste the model's JSON response here"
              rows={5}
            />
            <div className="row">
              <label className="button secondary">
                Load JSON file
                <input
                  hidden
                  type="file"
                  accept=".json"
                  onChange={async (e) => {
                    const f = e.target.files?.[0];
                    if (f) setImportText(await f.text());
                  }}
                />
              </label>
              <button
                disabled={!!busy || !importText}
                onClick={() =>
                  act("Import AI result", async () => {
                    const r = await api(
                      "/runs/" + runId + "/import",
                      "POST",
                      JSON.parse(importText),
                    );
                    if (r.result?.ideas) setIdeas(r.result.ideas);
                    if (r.run_id) setRunId(r.run_id);
                    setImportText("");
                    return r;
                  })
                }
              >
                Validate & import JSON
              </button>
              <button
                className="secondary"
                onClick={() =>
                  act("Load saved result", async () => {
                    const r = await api("/runs/" + runId + "/result");
                    if (r.result?.ideas) setIdeas(r.result.ideas);
                    return r;
                  })
                }
              >
                Load saved result
              </button>
            </div>
          </>
        )}
      </section>
    );
  const skillsPanel = (
    <section className="panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">CREATIVE FOUNDATION</span>
          <h3>ODD FRAME AI Skills</h3>
        </div>
        <button
          className="secondary small"
          disabled={!!busy}
          onClick={() =>
            act("Validate skills", async () => {
              const s = await api("/skills/validate", "POST");
              setStatus((v) => ({ ...v, skills: s }));
              if (!s.valid) throw Error(s.error);
              return {
                message:
                  "All four complete documents validated by byte length and SHA-256",
              };
            })
          }
        >
          <RefreshCw size={14} />
          Validate skills
        </button>
      </div>
      <div className="skill-list">
        {status?.skills?.documents?.map((d: Data, i: number) => (
          <div className="skill-row" key={d.id}>
            <span className="stepnum">0{i + 1}</span>
            <div>
              <strong>
                {
                  [
                    "Official Content Bible",
                    "Fanbase & Growth Psychology",
                    "2D Still Graphic Design",
                    "Typography & Motion",
                  ][i]
                }
              </strong>
              <small title={d.sha256}>
                v{d.version} · SHA-256{" "}
                {d.actual_sha256?.slice(0, 12) || "unavailable"} ·{" "}
                {d.actual_sha256 === d.sha256
                  ? "unchanged"
                  : "changed / missing"}
              </small>
            </div>
            <Badge value={d.status} />
          </div>
        ))}
      </div>
      <p className="footnote">
        <ShieldCheck size={14} />
        Full content is reread before each creative call. Last validation:{" "}
        {status?.skills?.checked_at
          ? new Date(status.skills.checked_at).toLocaleTimeString()
          : "pending"}
      </p>
      {!valid && (
        <p className="error">
          {status?.skills?.error || "Waiting for skill validation"}
        </p>
      )}
    </section>
  );

  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("Home");
          }}
        >
          <span className="brand-symbol">
            O<span>F</span>
          </span>
          <div>
            ODD FRAME<small>REEL WORKFLOW STATION</small>
          </div>
        </a>
        <div className="nav-label">PRODUCTION</div>
        <nav>
          {pages.map(([name, Icon]) => (
            <button
              className={"nav-item " + (page === name ? "active" : "")}
              key={name}
              onClick={() => setPage(name)}
            >
              <Icon size={18} />
              {name}
              {page === name && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-dot" />
          Local workspace<small>E:\facebook · Station v1.0</small>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="crumb">
            Workspace <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>
          <div className="top-status">
            <span className="local-dot" />
            {status?.settings?.provider === "manual"
              ? "Manual AI mode"
              : "AI provider configured"}
            <span className="avatar">OF</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <span className="eyebrow">SMALL STORIES. BIG EMOTIONS.</span>
              <h1>{page === "Home" ? "Your next story starts here." : page === "Ideas" ? "What Kind of Story Are We Creating?" : page}</h1>
              <p>
                {page === "Home"
                  ? "One workspace. From the first spark to the final frame."
                  : page === "Ideas" ? "Choose your genre. Discover five original story ideas."
                  : selected && ep
                    ? ep.code + " / " + ep.title
                    : "Create, prepare and produce original ODD FRAME stories."}
              </p>
            </div>
            <button disabled={!!busy || !valid} onClick={generate}>
              <Plus size={17} />
              Create New Reel
            </button>
          </div>
          {busy && (
            <div className="loading" role="status">
              <RefreshCw className="spin" size={16} />
              {busy}…
            </div>
          )}
          {authorized === false && (
            <div className="error" role="alert">
              <AlertCircle size={17} />
              <div>
                <strong>This browser window is not authorized to make changes.</strong>{" "}
                Open the dashboard with <code>scriptsstart.ps1</code>, or paste the
                access key from <code>datantroller-access.json</code> (the
                "token" value) here. It is kept in this browser only.
                <div className="row">
                  <input
                    type="password"
                    autoComplete="off"
                    aria-label="Controller access key"
                    placeholder="Paste access key"
                    value={accessKey}
                    onChange={(e) => setAccessKey(e.target.value)}
                  />
                  <button
                    disabled={!accessKey.trim()}
                    onClick={() => {
                      localStorage.setItem("odd-frame-controller", accessKey.trim());
                      setAccessKey("");
                      checkAuthorization();
                    }}
                  >
                    Authorize
                  </button>
                </div>
              </div>
            </div>
          )}
          {error && (
            <div className="error" role="alert">
              <AlertCircle size={17} />
              {error}
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <Check size={17} />
              {notice}
            </div>
          )}
          {page === "Home" && (
            <>
              <section className="hero">
                <div className="hero-art">
                  <span className="frame-corner tl" />
                  <span className="frame-corner br" />
                  <span className="hero-orb" />
                  <span className="hero-line" />
                  <span className="hero-small-square" />
                </div>
                <div className="hero-copy">
                  <span className="eyebrow gold">THE NEXT FRAME IS YOURS</span>
                  <h2>
                    Find the story.
                    <br />
                    Make them feel it.
                  </h2>
                  <p>
                    Original 2D stories. A purposeful golden detail.
                    <br />
                    One script approval, then a clear path to export.
                  </p>
                  <button disabled={!!busy || !valid} onClick={generate}>
                    Start story creation <ArrowRight size={17} />
                  </button>
                </div>
                <span className="hero-caption">MIDNIGHT GOLD / 01</span>
              </section>
              <div className="stats">
                {[
                  ["Total Reels", episodes.length],
                  [
                    "Awaiting script",
                    episodes.filter((e) =>
                      ["DRAFT", "SCRIPT_REVIEW", "AWAITING_APPROVAL"].includes(
                        e.status,
                      ),
                    ).length,
                  ],
                  [
                    "Preparing",
                    episodes.filter((e) =>
                      ["PREPARING", "AWAITING_MANUAL"].includes(e.status),
                    ).length,
                  ],
                  [
                    "Waiting for assets",
                    episodes.filter((e) =>
                      ["AWAITING_ASSETS", "ASSETS_BLOCKED"].includes(e.status),
                    ).length,
                  ],
                  [
                    "In render queue",
                    episodes.filter((e) =>
                      ["QUEUED", "RENDERING"].includes(e.status),
                    ).length,
                  ],
                  [
                    "Completed",
                    episodes.filter((e) => e.status === "COMPLETE").length,
                  ],
                  [
                    "Failed / blocked",
                    episodes.filter((e) =>
                      ["FAILED", "BLOCKED", "ASSETS_BLOCKED"].includes(
                        e.status,
                      ),
                    ).length,
                  ],
                ].map(([label, n]) => (
                  <div className="stat" key={label}>
                    <span>{label}</span>
                    <strong>{String(n).padStart(2, "0")}</strong>
                  </div>
                ))}
              </div>
              <div className="columns">
                <section className="panel">
                  <div className="section-heading">
                    <h3>Recent Reels</h3>
                    <span className="muted">Your production shelf</span>
                  </div>
                  {!episodes.length ? (
                    <Empty text="Your first story is waiting to be told." />
                  ) : (
                    <Paged
                      items={episodes}
                      size={5}
                      label="reels"
                      getText={(e: Data) => e.title + " " + e.code + " " + e.status}
                    >
                      {(rows) =>
                        rows.map((e) => (
                          <button
                            className="episode-row"
                            key={e.id}
                            onClick={() => selectEp(e)}
                          >
                            <span className="mini-frame">
                              <Film size={21} />
                            </span>
                            <div>
                              <strong>{e.title}</strong>
                              <small>
                                {e.code} ·{" "}
                                {new Date(e.updated).toLocaleDateString()}
                              </small>
                            </div>
                            <Badge value={e.status} />
                            <ChevronRight size={16} />
                          </button>
                        ))
                      }
                    </Paged>
                  )}
                </section>
                {skillsPanel}
              </div>
              <section className="panel">
                <div className="section-heading">
                  <h3>Production queue</h3>
                  <span className="muted">
                    One render at a time · resumes on restart
                  </span>
                </div>
                {!status?.jobs?.length ? (
                  <p className="muted">
                    No jobs yet. Assets that pass validation will enter the
                    queue automatically.
                  </p>
                ) : (
                  <Paged
                    items={status.jobs as Data[]}
                    size={5}
                    label="jobs"
                    getText={(j: Data) => `#${j.id} episode ${j.episode_id} ${j.kind || ""} ${j.stage} ${j.status} ${j.error || ""}`}
                  >
                    {(rows) =>
                      rows.map((j: Data) => (
                        <div className="job" key={j.id}>
                          <span>
                            #{j.id} · Episode {j.episode_id}
                          </span>
                          <strong>{j.stage}</strong>
                          {['QUEUED','RUNNING'].includes(j.status) && <progress aria-label={j.stage} />}
                          <Badge value={j.status} />
                          {j.error && <p className="error">{j.error}</p>}
                        </div>
                      ))
                    }
                  </Paged>
                )}
              </section>
            </>
          )}
          {page === "Master Prompt" && (
            <>
              {skillsPanel}
              <section className="panel">
                <div className="section-heading">
                  <h3>Creative Director · current source version</h3>
                  <button disabled={!!busy || !valid} onClick={generate}>
                    Start Story Creation <ArrowRight size={15} />
                  </button>
                </div>
                <p>
                  Provider: <strong>{status?.settings?.provider}</strong> ·
                  Model:{" "}
                  {status?.settings?.model ||
                    "not configured / external manual tool"}
                </p>
                <pre className="document">{master}</pre>
              </section>
            </>
          )}
          {page === "Ideas" && (
            <IdeasStudio legacyHandoff={<>{ManualPanel()}{ideas.length > 0 && <section className="panel"><h3>Saved general story concepts · legacy format</h3><p>These earlier concepts keep their original titles and metadata.</p><div className="cards">{ideas.map((idea, index) => <article className="panel" key={index}><h3>{idea.title}</h3><span className="tag">{idea.genre}</span><p>{idea.premise}</p><p><strong>Opening hook:</strong> {idea.visual_hook}</p><p><strong>Conflict:</strong> {idea.conflict}</p><button disabled={!!busy} onClick={() => choose(idea)}>Select Legacy Story</button></article>)}</div></section>}</>} onSelected={(eid, pendingRun) => {
              setSelected(eid);setPage("Script Studio");if(pendingRun)setRunId(pendingRun);reload().catch(e=>setError(e.message));
            }}/>
          )}
          {![
            "Home",
            "Master Prompt",
            "Ideas",
            "Settings",
            "Analytics",
          ].includes(page) && (
            <div className="episode-picker">
              <label>
                ACTIVE REEL
                <select
                  aria-label="Active Reel"
                  value={selected || ""}
                  onChange={(e) => setSelected(Number(e.target.value))}
                >
                  <option value="">Choose an episode</option>
                  {episodes.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.code} — {e.title}
                    </option>
                  ))}
                </select>
              </label>
              {ep && selected && <Badge value={ep.status} />}
            </div>
          )}
          {![
            "Home",
            "Master Prompt",
            "Ideas",
            "Settings",
            "Analytics",
          ].includes(page) && PipelineTracker()}
          {[
            "Script Studio",
            "Episode Workspace",
            "Google Flow Prompts",
            "Asset Manager",
            "Edit Studio",
            "Exports",
          ].includes(page) &&
            !selected && (
              <section className="panel">
                <div className="row">
                  <Search size={16} />
                  <input
                    placeholder="Search projects"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                  <select
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    <option value="all">All statuses</option>
                    {[...new Set(episodes.map((e) => e.status))].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </div>
                <Paged
                  items={episodeList}
                  label="projects"
                  resetKey={query + "|" + filter}
                  empty={
                    <Empty
                      text={
                        episodes.length
                          ? "No project matches this search or status."
                          : "Select or create a story to open its workspace."
                      }
                    />
                  }
                >
                  {(rows) =>
                    rows.map((e) => (
                      <button
                        className="episode-row"
                        key={e.id}
                        onClick={() => selectEp(e, page)}
                      >
                        <strong>
                          {e.code} · {e.title}
                        </strong>
                        <Badge value={e.status} />
                        <ChevronRight size={15} />
                      </button>
                    ))
                  }
                </Paged>
              </section>
            )}
          {page === "Script Studio" && selected && ep && (
            <>
              <section className="panel">
                <div className="section-heading">
                  <h3>The story, in your words</h3>
                  <button
                    className="secondary"
                    disabled={
                      !!busy ||
                      !validForEpisode ||
                      !!ep.data.approval ||
                      ep.runs?.some((r: Data) =>
                        ["QUEUED", "RUNNING"].includes(r.status),
                      )
                    }
                    onClick={() =>
                      act("Write and self-review script", async () => {
                        const r = await api(selectedPath + "/script", "POST");
                        if (r.run_id) setRunId(r.run_id);
                        return r;
                      })
                    }
                  >
                    <Sparkles size={15} />
                    Generate Script
                  </button>
                </div>
                <label>
                  Story brief
                  <textarea
                    value={brief}
                    onChange={(e) => setBrief(e.target.value)}
                    disabled={!!ep.data.approval}
                    rows={3}
                  />
                </label>
                <label>
                  Full narration
                  <textarea
                    className="script"
                    aria-label="Full narration"
                    value={script}
                    disabled={!!ep.data.approval}
                    onChange={(e) => setScript(e.target.value)}
                    rows={12}
                    placeholder="Generate or paste the complete narration. Its exact wording is frozen at approval."
                  />
                </label>
                <p className="muted">
                  {script.split(/\s+/).filter(Boolean).length} words · duration
                  is provisional until real audio is uploaded.
                </p>
                {ep.data.script?.findings?.map((f: string, i: number) => (
                  <p className="finding" key={i}>
                    <Check size={14} />
                    {f}
                  </p>
                ))}
                <div className="row">
                  {!ep.data.approval ? (
                    <>
                      <button
                        className="secondary"
                        disabled={
                          !!busy ||
                          script.length < 30 ||
                          brief.length < 10 ||
                          !validForEpisode
                        }
                        onClick={() =>
                          act("Save owner draft", () =>
                            api(selectedPath + "/draft", "POST", {
                              narration: script,
                              brief,
                              findings: [
                                "Owner-imported/edited draft. AI review is not claimed unless a successful review run exists.",
                              ],
                            }),
                          )
                        }
                      >
                        Save / Import Draft
                      </button>
                      <button
                        disabled={
                          !!busy ||
                          !ep.data.script ||
                          script.length < 30 ||
                          !validForEpisode ||
                          ep.status !== "AWAITING_APPROVAL"
                        }
                        onClick={() =>
                          act("Approve script & prepare episode", async () => {
                            const r = await api(
                              selectedPath + "/approve",
                              "POST",
                              { narration: script, brief },
                            );
                            if (r.run_id) setRunId(r.run_id);
                            return r;
                          })
                        }
                      >
                        <ShieldCheck size={16} />
                        APPROVE SCRIPT & CONTINUE
                      </button>
                    </>
                  ) : (
                    <div className="approval">
                      <ShieldCheck size={18} />
                      {ep.data.approval.revoked?'Export authorization revoked':<>Approved · {ep.data.approval.sha256.slice(0, 16)} · automatic export authorized</>}
                    </div>
                  )}
                </div>
              </section>
              {ManualPanel()}
            </>
          )}
          {page === "Episode Workspace" && selected && ep && (
            <>
              <div className="columns">
                <section className="panel">
                  <h3>{ep.title}</h3>
                  <p>{ep.data.idea.premise}</p>
                  <div className="stages">
                    {[
                      ["Story selected", true],
                      ["Script approved", !!ep.data.approval],
                      ["Preproduction documents", !!ep.data.package],
                      ["User assets valid", !!ep.asset_report?.valid],
                      ["Preview & export", ep.status === "COMPLETE"],
                    ].map(([label, done], i) => (
                      <div className="skill-row" key={i}>
                        <span className={"stepnum " + (done ? "done" : "")}>
                          {done ? <Check size={15} /> : i + 1}
                        </span>
                        <strong>{label}</strong>
                        <Badge value={done ? "COMPLETE" : "PENDING"} />
                      </div>
                    ))}
                  </div>
                  {ep.data.error && <p className="error">{ep.data.error}</p>}
                  <div className="row">
                    <button
                      className="secondary"
                      disabled={!!busy || !ep.data.approval}
                      onClick={() =>
                        act("Retry failed stage", async () => {
                          const r = await api(selectedPath + "/retry", "POST");
                          if (r.run_id) setRunId(r.run_id);
                          return r;
                        })
                      }
                    >
                      <RefreshCw size={15} />
                      Retry / Resume
                    </button>
                    <button
                      className="secondary"
                      disabled={!!busy}
                      onClick={() =>
                        act("Validate pinned inputs", () =>
                          api(selectedPath + "/reconcile-skills", "POST"),
                        )
                      }
                    >
                      Validate pinned inputs
                    </button>
                    <button
                      className="secondary"
                      disabled={!ep.data.approval || !!busy}
                      onClick={() =>
                        act("Revoke export authorization", () =>
                          api(selectedPath + "/cancel-export", "POST"),
                        )
                      }
                    >
                      Revoke export authorization
                    </button>
                  </div>
                </section>
                <section className="panel">
                  <h3>Skill-loading evidence</h3>
                  <h3>Episode Isolation</h3>
                  <Badge
                    value={
                      ep.isolation?.verified
                        ? "VERIFIED WINDOWS MXC"
                        : "NOT YET VERIFIED"
                    }
                  />
                  <p className="muted">
                    {ep.isolation?.verified
                      ? "The native process boundary passed actual write-denial checks. Workers write only into this episode."
                      : "Automatic workers must pass the episode-specific OS boundary probe before execution."}
                  </p>
                  <button
                    className="secondary small"
                    disabled={!!busy}
                    onClick={() =>
                      act("Verify episode isolation", () =>
                        api(selectedPath + "/isolation/verify", "POST"),
                      )
                    }
                  >
                    Verify Episode Isolation
                  </button>
                  {ep.input_snapshot && (
                    <p className="finding">
                      Pinned master v{ep.input_snapshot.master_prompt_version} ·
                      four skill versions · Remotion{" "}
                      {ep.input_snapshot.remotion_template_version}
                      <br />
                      Signature instrumental:{" "}
                      {ep.input_snapshot.signature_music.status}
                      {ep.input_snapshot.signature_music.sha256
                        ? " · " +
                          ep.input_snapshot.signature_music.sha256.slice(0, 12)
                        : ""}
                      <br />
                      Global upgrades do not change these episode inputs.
                    </p>
                  )}
                  {ep.provenance?.runs?.length ? (
                    <>
                      <p className="notice">
                        {ep.provenance.runs.length} validated instruction loads
                        recorded
                      </p>
                      {ep.provenance.runs.slice(-3).map((r: Data) => (
                        <p className="finding" key={r.run_id}>
                          {r.task} · {r.provider}/{r.model || "manual"}
                          <br />
                          {r.timestamp}
                          <br />
                          Master {r.master_prompt.sha256.slice(0, 12)} · all
                          four skills delivered in full
                        </p>
                      ))}
                    </>
                  ) : (
                    <p className="muted">
                      No AI generation has occurred for this episode.
                    </p>
                  )}
                  <p className="footnote">
                    Document delivery is verified. Model creative compliance is
                    assessed separately.
                  </p>
                </section>
              </div>
              <section className="panel">
                <h3>Episode files</h3>
                <Paged
                  items={(ep.files || []) as string[]}
                  size={10}
                  label="files"
                  placeholder="Search files by name or folder"
                  getText={(f: string) => f}
                >
                  {(rows) => (
                    <div className="files">
                      {rows.map((f: string) => (
                        <a
                          key={f}
                          href={fileURL(f)}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <FileText size={15} />
                          {f}
                          <Download size={13} />
                        </a>
                      ))}
                    </div>
                  )}
                </Paged>
              </section>
              <section className="panel">
                <h3>Production history</h3>
                <Paged
                  items={(ep.history || []) as Data[]}
                  size={10}
                  label="history"
                  placeholder="Search production history"
                  getText={(h: Data) => h.stage + " " + historyText(h, ep)}
                >
                  {(rows) =>
                    rows.map((h: Data) => (
                      <p className="history" key={h.id}>
                        <Clock size={14} />
                        {new Date(h.at).toLocaleString()} <Badge value={h.stage} />
                        {historyText(h, ep)}
                      </p>
                    ))
                  }
                </Paged>
              </section>
              {ManualPanel()}
            </>
          )}
          {page === "Google Flow Prompts" && selected && ep && (
            <section className="panel">
              <div className="section-heading">
                <h3>Still-image queue</h3>
                {ep.data.package && (
                  <a
                    className="button"
                    href={fileURL("04_google_flow/IMAGE_JOBS.json")}
                    download
                  >
                    <Download size={15} />
                    Download Flow JSON
                  </a>
                )}
              </div>
              <p className="muted">
                Generate these stills in Google Flow, then import files named
                S001.png, S002.jpg, etc. No website automation or video jobs.
              </p>
              <Paged
                items={((ep.files || []) as string[]).filter((f) => f.startsWith("04_google_flow/batches/"))}
                size={10}
                label="prompt batches"
                getText={(f: string) => f}
                empty={<></>}
              >
                {(rows) => (
                  <div className="row">
                    {rows.map((f: string) => (
                      <a className="button secondary small" key={f} href={fileURL(f)} download>
                        {f.split("/").pop()}
                      </a>
                    ))}
                  </div>
                )}
              </Paged>
              <Paged
                items={(ep.data.package?.scenes || []) as Data[]}
                size={10}
                label="scenes"
                placeholder="Search scenes (S005, a word from the story...)"
                getText={(s: Data) => s.scene_id + " " + s.beat + " " + s.narration_text}
                empty={<></>}
              >
                {(rows) =>
                  rows.map((s: Data) => (
                    <details key={s.scene_id}>
                      <summary>
                        <span className="gold">{s.scene_id}</span> {s.beat}
                      </summary>
                      <p>{s.narration_text}</p>
                      <p>
                        Focal point: {s.focus} · {s.yellow_placement}
                      </p>
                      <pre>
                        {
                          ep.flow?.jobs?.find(
                            (j: Data) => j.scene_id === s.scene_id,
                          )?.prompt
                        }
                      </pre>
                      <a
                        href={fileURL("04_google_flow/IMAGE_PROMPTS.md")}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Read complete self-contained prompts
                      </a>
                    </details>
                  ))
                }
              </Paged>
              {!ep.data.package && (
                <Empty text="Approve the script and complete preproduction to create real prompt jobs." />
              )}
            </section>
          )}
          {page === "Asset Manager" && selected && ep && (
            <>
              <section className="panel">
                <div className="section-heading">
                  <h3>Bring your story to life</h3>
                  <button
                    className="secondary"
                    disabled={!!busy || !ep.data.package}
                    onClick={() =>
                      act("Refresh assets", () =>
                        api(selectedPath + "/assets/refresh", "POST"),
                      )
                    }
                  >
                    <RefreshCw size={15} />
                    Refresh Assets
                  </button>
                </div>
                <p className="muted">
                  Folders are scanned every 10 seconds. Matching is isolated to
                  this episode. All valid assets automatically enter the edit
                  queue.
                </p>
                <div className="asset-grid">
                  {[
                    ["images", "Still illustrations", "S001.png · 9:16"],
                    ["narration", "Narration", "One ElevenLabs audio file"],
                    ["subtitles", "Subtitles", "SRT · 1–4 words per cue"],
                    ["music", "Instrumental music", "One background track"],
                  ].map(([kind, label, help]) => (
                    <div className="asset-card" key={kind}>
                      <Upload size={22} />
                      <h3>{label}</h3>
                      <p>{help}</p>
                      <label
                        className={
                          "button secondary " +
                          (!ep.data.package ? "disabled" : "")
                        }
                      >
                        Import {kind}
                        <input
                          aria-label={"Import " + kind}
                          hidden
                          type="file"
                          multiple={kind === "images"}
                          disabled={!!busy || !ep.data.package}
                          accept={
                            kind === "images"
                              ? ".png,.jpg,.jpeg,.webp"
                              : kind === "subtitles"
                                ? ".srt"
                                : ".wav,.mp3,.m4a,.aac,.flac,.ogg"
                          }
                          onChange={(e) => {
                            if (e.target.files) {
                              const fd = new FormData();
                              Array.from(e.target.files).forEach((f) =>
                                fd.append("files", f),
                              );
                              act("Import " + kind, () =>
                                api(
                                  selectedPath + "/assets/" + kind,
                                  "POST",
                                  fd,
                                ),
                              );
                              e.target.value = "";
                            }
                          }}
                        />
                      </label>
                      <Paged
                        items={((ep.files || []) as string[]).filter((f) =>
                          f.startsWith("05_assets/" + kind + "/"),
                        )}
                        size={5}
                        label={kind + " files"}
                        getText={kind === "images" ? (f: string) => f : undefined}
                        resetKey={kind}
                        empty={<></>}
                      >
                        {(rows) =>
                          rows.map((f: string) => (
                            <div className="asset-file" key={f}>
                              <a href={fileURL(f)}>{f.split("/").pop()}</a>
                              <button
                                className="text-button"
                                onClick={() =>
                                  act("Remove asset", () =>
                                    api(
                                      selectedPath +
                                        "/assets/" +
                                        kind +
                                        "/" +
                                        encodeURIComponent(f.split("/").pop()!),
                                      "DELETE",
                                    ),
                                  )
                                }
                              >
                                Remove
                              </button>
                            </div>
                          ))
                        }
                      </Paged>
                    </div>
                  ))}
                </div>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={instrumental}
                    onChange={(e) => setInstrumental(e.target.checked)}
                  />
                  I confirm this track is instrumental, without competing
                  vocals.
                </label>
                <label>
                  Music rights evidence / license reference
                  <input
                    value={rights}
                    onChange={(e) => setRights(e.target.value)}
                    placeholder="License URL, receipt or ownership note (missing evidence is flagged)"
                  />
                </label>
                <button
                  className="secondary"
                  onClick={() =>
                    act("Save music declaration", () =>
                      api(selectedPath + "/music-rights", "POST", {
                        instrumental_confirmed: instrumental,
                        evidence: rights,
                      }),
                    )
                  }
                >
                  Save music declaration
                </button>
              </section>
              <section className="panel">
                <h3>Asset validation</h3>
                {ep.asset_report ? (
                  <>
                    <Badge
                      value={
                        ep.asset_report.valid ? "COMPLETE" : "ASSETS_BLOCKED"
                      }
                    />
                    {ep.asset_report.errors?.map((s: string, i: number) => (
                      <p className="error" key={i}>
                        {s}
                      </p>
                    ))}
                    {ep.asset_report.warnings?.map((s: string, i: number) => (
                      <p className="finding" key={i}>
                        {s}
                      </p>
                    ))}
                    <div className="scene-chips">
                      {ep.data.package?.scenes.map((s: Data) => (
                        <span
                          className={
                            ep.asset_report.images[s.scene_id]
                              ? "ready"
                              : "missing"
                          }
                          key={s.scene_id}
                        >
                          {s.scene_id}{" "}
                          {ep.asset_report.images[s.scene_id] ? "✓" : "missing"}
                        </span>
                      ))}
                    </div>
                  </>
                ) : (
                  <Empty text="Import assets, then refresh for an exact missing-file report." />
                )}
              </section>
            </>
          )}
          {page === "Edit Studio" && selected && ep && (
            <>
              <StudioPanel
                episodeId={selected}
                hasDraft={ep.files.includes("06_edit/editor_state.json")}
                status={ep.status}
                jobs={ep.jobs}
                act={act}
                busy={busy}
                onChanged={() => void reload()}
              />
              <section className="panel">
                <div className="section-heading">
                  <h3>Timeline & render</h3>
                  <button
                    className="secondary"
                    disabled={
                      !!busy ||
                      !ep.data.package ||
                      ep.status === "RENDERING" ||
                      ep.status === "QUEUED"
                    }
                    onClick={() =>
                      act("Validate & queue render", () =>
                        api(selectedPath + "/editor/prepare", "POST"),
                      )
                    }
                  >
                    Validate & prepare draft
                  </button>
                </div>
                {(() => {
                  const jobs: Data[] = ep.jobs || [];
                  const newestOk = Math.max(
                    0,
                    ...jobs
                      .filter((j) => j.status !== "FAILED")
                      .map((j) => j.id),
                  );
                  const shown = jobs.filter(
                    (j) => j.status !== "FAILED" || j.id > newestOk,
                  );
                  const old = jobs.filter((j) => !shown.includes(j));
                  const row = (j: Data) => (
                    <div className="job" key={j.id}>
                      <strong>
                        {j.status === "FAILED" ? "Render attempt failed" : j.stage}
                      </strong>
                      {['QUEUED','RUNNING'].includes(j.status) && <progress aria-label={j.stage} />}
                      <Badge value={j.status} />
                      {j.status === "RUNNING" && (
                        <div className="indeterminate" aria-hidden="true" />
                      )}
                      {j.error && <p className="error">{j.error}</p>}
                    </div>
                  );
                  return (
                    <>
                      <Paged items={shown} size={5} label="jobs" empty={<></>}>
                        {(rows) => rows.map(row)}
                      </Paged>
                      {old.length > 0 && (
                        <details>
                          <summary>
                            Earlier failed attempts ({old.length}) — already
                            superseded
                          </summary>
                          <Paged items={old} size={5} label="earlier attempts" empty={<></>}>
                            {(rows) => rows.map(row)}
                          </Paged>
                        </details>
                      )}
                    </>
                  );
                })()}
                {ep.timeline ? (
                  <>
                    <p>
                      {(ep.timeline.durationInFrames / 30).toFixed(2)}s ·{" "}
                      {ep.timeline.scenes.length} static scenes ·{" "}
                      {ep.timeline.captions.length} SRT-grounded captions
                    </p>
                    <div className="timeline">
                      {ep.timeline.scenes.map((s: Data) => (
                        <div
                          key={s.id}
                          style={{ flex: s.end - s.start }}
                          title={`${s.id}: ${(s.start / 30).toFixed(2)}–${(s.end / 30).toFixed(2)}s`}
                        >
                          {s.id}
                        </div>
                      ))}
                    </div>
                    <p className="footnote">
                      Static images · typography only animation · narration +
                      instrumental · hard cuts
                    </p>
                  </>
                ) : (
                  <Empty text="The measured timeline appears after assets pass validation." />
                )}
                {ep.data.exports?.at(-1) && (
                  <video
                    className="preview"
                    controls
                    src={"/api/media/" + ep.data.exports.at(-1).preview}
                  />
                )}
                {ep.data.package && ep.style_info && (
                  <section className="panel style-panel">
                    <h3>Editing style</h3>
                    <p className="muted">
                      Stills stay completely static in every style; styles only
                      change scene transitions and caption animation. This
                      episode is pinned to{" "}
                      <strong>
                        {ep.style_info.label} {ep.style_info.version}
                      </strong>{" "}
                      (
                      {ep.style_info.source === "global_default"
                        ? "inherited when the episode was created"
                        : ep.style_info.source === "legacy"
                          ? "original style"
                          : ep.style_info.source === "owner_adopted"
                            ? "adopted by you"
                            : "chosen by you"}
                      ). Changing the global default never changes this
                      episode.
                    </p>
                    <div className="row">
                      <select
                        aria-label="Editing style profile"
                        value={styleSel || ep.style_info.profile_id}
                        onChange={(e) => setStyleSel(e.target.value)}
                      >
                        {ep.style_info.pinned.map((p: Data) => (
                          <option key={p.id} value={p.id}>
                            {p.label} · pinned in this episode
                          </option>
                        ))}
                        {ep.style_info.adoptable.map((p: Data) => (
                          <option key={p.id} value={p.id}>
                            {p.label} · adopt for this episode
                          </option>
                        ))}
                      </select>
                      {["COMPLETE", "FAILED", "AWAITING_ASSETS", "ASSETS_BLOCKED"].includes(
                        ep.status,
                      ) && (
                        <label className="inline">
                          <input
                            type="checkbox"
                            checked={rerenderOnSave}
                            onChange={(e) => setRerenderOnSave(e.target.checked)}
                          />{" "}
                          Re-render as a new export version
                        </label>
                      )}
                      <button
                        disabled={
                          !!busy ||
                          ["QUEUED", "RENDERING"].includes(ep.status) ||
                          (styleSel || ep.style_info.profile_id) ===
                            ep.style_info.profile_id
                        }
                        onClick={() =>
                          act("Apply editing style", () =>
                            api(selectedPath + "/style", "PUT", {
                              profile_id: styleSel,
                              adopt: ep.style_info.adoptable.some(
                                (p: Data) => p.id === styleSel,
                              ),
                              rerender: rerenderOnSave,
                            }),
                          )
                        }
                      >
                        Apply style
                      </button>
                    </div>
                    {ep.style_info.adoptable.some(
                      (p: Data) => p.id === styleSel,
                    ) && (
                      <p className="muted">
                        Adopting adds the newer renderer and profile to this
                        episode's pinned inputs. Your approved script, stills,
                        narration and earlier exports are not touched, and
                        nothing re-renders unless you tick the box.
                      </p>
                    )}
                    <div className="row">
                      <button
                        className="secondary"
                        disabled={
                          !!busy || ["QUEUED", "RENDERING"].includes(ep.status)
                        }
                        onClick={() =>
                          act("Render style preview (about 1–3 minutes)", () =>
                            api(selectedPath + "/style-preview", "POST", {
                              profiles: [
                                "ODD_FRAME_CLASSIC_V1_0",
                                "ODD_FRAME_CINEMATIC_TRANSITIONS_V1",
                              ],
                            }),
                          )
                        }
                      >
                        Preview style: Classic vs Cinematic Transitions
                      </button>
                      <span className="muted">
                        Renders about 7 seconds of your real footage in both
                        styles. Never overwrites your export.
                      </span>
                    </div>
                    {ep.style_info.preview && (
                      <div className="style-compare">
                        {ep.style_info.preview.notes?.map((n: string) => (
                          <p className="muted" key={n}>
                            {n}
                          </p>
                        ))}
                        <div className="audio-grid">
                          {ep.style_info.preview.profiles.map((p: Data) => (
                            <div key={p.profile_id}>
                              <strong>
                                {p.label} {p.version}
                              </strong>
                              <video
                                className="preview"
                                controls
                                preload="metadata"
                                src={
                                  "/api/media/" +
                                  p.file +
                                  "?v=" +
                                  encodeURIComponent(ep.style_info.preview.created)
                                }
                              />
                              <p className="muted">
                                {p.seconds}s · captions: {p.presets.join(", ")} ·
                                transitions:{" "}
                                {p.transitions.length
                                  ? p.transitions
                                      .map(
                                        (t: Data) =>
                                          t.scene +
                                          " " +
                                          t.transition.replaceAll("_", " ") +
                                          " (" +
                                          t.frames +
                                          "f)",
                                      )
                                      .join(", ")
                                  : "hard cuts only"}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <details>
                      <summary>Scene transitions</summary>
                      <p className="muted">
                        Hard cut is the default. Use a crossfade for gentle
                        continuous moments and a dip to charcoal sparingly.
                        The pinned style limits how many are used; anything
                        over the limit becomes a hard cut and is reported.
                      </p>
                      {ep.timeline?.style?.notes?.length > 0 && (
                        <p className="muted">
                          Last render notes: {ep.timeline.style.notes.join(" · ")}
                        </p>
                      )}
                      <div className="transition-list">
                        {ep.data.package.scenes.slice(1).map((s: Data) => {
                          const current =
                            trDraft?.[s.scene_id] ??
                            ep.style_info.overrides?.[s.scene_id] ??
                            s.transition_in ??
                            "cut";
                          return (
                            <label key={s.scene_id}>
                              <span>
                                {s.scene_id}
                                {s.transition_reason && (
                                  <span className="muted"> — {s.transition_reason}</span>
                                )}
                              </span>
                              <select
                                value={current}
                                onChange={(e) =>
                                  setTrDraft({
                                    ...(trDraft || {}),
                                    [s.scene_id]: e.target.value,
                                  })
                                }
                              >
                                <option value="cut">Hard cut</option>
                                <option value="crossfade">Smooth crossfade</option>
                                <option value="dip_to_dark">Dip to dark</option>
                              </select>
                            </label>
                          );
                        })}
                      </div>
                      <button
                        className="secondary"
                        disabled={
                          !!busy ||
                          !trDraft ||
                          ["QUEUED", "RENDERING"].includes(ep.status)
                        }
                        onClick={() =>
                          act("Save scene transitions", async () => {
                            const full: Record<string, string> = {};
                            ep.data.package.scenes.slice(1).forEach((s: Data) => {
                              full[s.scene_id] =
                                trDraft?.[s.scene_id] ??
                                ep.style_info.overrides?.[s.scene_id] ??
                                s.transition_in ??
                                "cut";
                            });
                            const r = await api(
                              selectedPath + "/transitions",
                              "PUT",
                              { transitions: full, rerender: rerenderOnSave },
                            );
                            setTrDraft(null);
                            return r;
                          })
                        }
                      >
                        Save transitions
                      </button>
                    </details>
                  </section>
                )}
                {ep.data.package && (
                  <section className="panel music-level">
                    <h3>Background music level</h3>
                    <p className="muted">
                      The app balances the music automatically (narration about
                      21 dB above it, music ducks under the voice). Move the
                      slider to make the music quieter or louder, then save —
                      the next render uses it. Currently saved:{" "}
                      {Number(ep.data.music_mix?.offset_db ?? 0).toFixed(1)} dB.
                    </p>
                    <div className="row">
                      <span>Quieter</span>
                      <input
                        type="range"
                        aria-label="Music level offset in dB"
                        min={-12}
                        max={6}
                        step={0.5}
                        value={musicDb}
                        onChange={(e) => setMusicDb(Number(e.target.value))}
                      />
                      <span>Louder</span>
                      <strong>
                        {musicDb > 0 ? "+" : ""}
                        {musicDb.toFixed(1)} dB
                      </strong>
                      <button
                        className="secondary small"
                        onClick={() => setMusicDb(0)}
                        disabled={musicDb === 0}
                      >
                        Reset
                      </button>
                      <button
                        disabled={
                          !!busy ||
                          ["QUEUED", "RENDERING"].includes(ep.status) ||
                          musicDb === Number(ep.data.music_mix?.offset_db ?? 0)
                        }
                        onClick={() =>
                          act("Save music level", () =>
                            api(selectedPath + "/music-level", "PUT", {
                              offset_db: musicDb,
                            }),
                          )
                        }
                      >
                        Save music level
                      </button>
                    </div>
                    <div className="audio-test">
                      <h4>Listen before you render</h4>
                      {(() => {
                        const f: string[] = ep.files || [];
                        const nar = f.find((x) => x.startsWith("05_assets/narration/"));
                        const mus = f.find((x) => x.startsWith("05_assets/music/"));
                        return (
                          <div className="audio-grid">
                            <label>
                              Narration only (your uploaded file)
                              {nar ? (
                                <audio controls preload="none" src={fileURL(nar)} />
                              ) : (
                                <span className="muted">No narration uploaded</span>
                              )}
                            </label>
                            <label>
                              Background music only (your uploaded file)
                              {mus ? (
                                <audio controls preload="none" src={fileURL(mus)} />
                              ) : (
                                <span className="muted">No music uploaded</span>
                              )}
                            </label>
                          </div>
                        );
                      })()}
                      <div className="row">
                        <button
                          className="secondary"
                          disabled={
                            !!busy ||
                            ["QUEUED", "RENDERING"].includes(ep.status)
                          }
                          onClick={() =>
                            act("Build audio preview (narration + music)", async () => {
                              const r = await api(
                                selectedPath + "/audio-preview",
                                "POST",
                                { offset_db: musicDb },
                              );
                              setPreviewMix(r);
                              return r;
                            })
                          }
                        >
                          Preview mix at {musicDb > 0 ? "+" : ""}
                          {musicDb.toFixed(1)} dB
                        </button>
                        <span className="muted">
                          Takes a few seconds. Nothing is saved and no video is
                          rendered.
                        </span>
                      </div>
                      {previewMix && (
                        <div>
                          <audio
                            controls
                            autoPlay
                            src={previewMix.url}
                            key={previewMix.url}
                          />
                          <p className="muted">
                            Mix at {previewMix.offset_db > 0 ? "+" : ""}
                            {previewMix.offset_db} dB — narration is about{" "}
                            {Number(previewMix.gap_db).toFixed(1)} dB above the
                            music. Happy? Press “Save music level”, then render.
                          </p>
                        </div>
                      )}
                    </div>
                    {["QUEUED", "RENDERING"].includes(ep.status) && (
                      <p className="muted">
                        A render is in progress. You can change the level after
                        it finishes; saving then re-renders automatically.
                      </p>
                    )}
                  </section>
                )}
                {ep.data.package && (
                  <details>
                    <summary>Adjust caption-safe regions</summary>
                    <p>
                      Coordinates are normalized 0–1. Protect faces and clues in
                      the actual uploaded artwork. Only caption placement
                      changes; approved narration and stills stay fixed.
                    </p>
                    <form
                      key={ep.id}
                      onSubmit={(event) => {
                        event.preventDefault();
                        const raw = new FormData(event.currentTarget).get(
                          "regions",
                        );
                        act("Save caption-safe regions", () =>
                          api(
                            selectedPath + "/caption-regions",
                            "PUT",
                            JSON.parse(String(raw)),
                          ),
                        );
                      }}
                    >
                      <textarea
                        aria-label="Caption-safe regions JSON"
                        name="regions"
                        rows={12}
                        defaultValue={JSON.stringify(
                          ep.data.package.scenes.map((s: Data) => ({
                            scene_id: s.scene_id,
                            caption_y: s.caption_y,
                            protected_regions: s.protected_regions,
                          })),
                          null,
                          2,
                        )}
                      />
                      <button
                        disabled={
                          !!busy ||
                          ep.status === "QUEUED" ||
                          ep.status === "RENDERING"
                        }
                      >
                        Save caption regions & revalidate
                      </button>
                    </form>
                  </details>
                )}
              </section>
            </>
          )}
          {page === "Exports" && selected && ep && (
            <section className="panel">
              <h3>Finished frames</h3>
              <ExportsPanel
                exports={(ep.data.exports || []) as Data[]}
                episodeId={ep.id}
                fileURL={fileURL}
                disabled={!!busy || ["QUEUED", "RENDERING"].includes(ep.status)}
                Badge={Badge}
                Empty={Empty}
                onDelete={(ids) =>
                  act("Delete exports", () =>
                    api(selectedPath + "/exports/delete", "POST", {job_ids: ids, confirm: true}),
                  )
                }
              />
            </section>
          )}
          {page === "Analytics" && (
            <section className="panel">
              <h3>Real performance, recorded by you</h3>
              <p className="muted">
                No Meta connection is implied. Import actual metrics with their
                source and reporting period.
              </p>
              <label>
                Episode
                <select
                  value={selected || ""}
                  onChange={(e) => setSelected(Number(e.target.value))}
                >
                  <option value="">Select Reel</option>
                  {episodes.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.code} — {e.title}
                    </option>
                  ))}
                </select>
              </label>
              <textarea
                rows={5}
                value={metrics}
                onChange={(e) => setMetrics(e.target.value)}
                placeholder={
                  '{"period":"first 7 days", "source":"Facebook Professional Dashboard", "views":1200, "reach":1000, "shares":15}'
                }
              />
              <div className="row">
                <label className="button secondary">
                  Load metrics JSON
                  <input
                    hidden
                    type="file"
                    accept=".json"
                    onChange={async (e) => {
                      const f = e.target.files?.[0];
                      if (f) setMetrics(await f.text());
                    }}
                  />
                </label>
                <button
                  disabled={!selected || !metrics || !!busy}
                  onClick={() =>
                    act("Record real metrics", async () => {
                      const r = await api(
                        selectedPath + "/metrics",
                        "POST",
                        JSON.parse(metrics),
                      );
                      setMetricRows(await api("/metrics"));
                      setMetrics("");
                      return r;
                    })
                  }
                >
                  Save actual metrics
                </button>
              </div>
              <Paged
                items={metricRows as Data[]}
                size={5}
                label="recorded metrics"
                getText={(m: Data) => JSON.stringify(m)}
              >
                {(rows) => rows.map((m: Data) => <pre key={m.id}>{JSON.stringify(m, null, 2)}</pre>)}
              </Paged>
            </section>
          )}
          {page === "Settings" && prefs && (
            <>
              <section className="panel">
                <h3>Controller access</h3>
                <p>
                  {authorized === null
                    ? "Checking…"
                    : authorized
                      ? "✓ Authorized — this browser is saved and can make changes."
                      : "✗ Not authorized — see the notice at the top to authorize this browser."}
                </p>
              </section>
              <section className="panel">
                <h3>AI provider</h3>
                <p className="muted">
                  Codex CLI uses its existing authenticated login without a separate API key.
                  Claude Code CLI needs CLAUDE_CODE_OAUTH_TOKEN from claude setup-token, or ANTHROPIC_API_KEY.
                  API mode requires its own credential.
                </p>
                <div className="form-grid">
                  <label>
                    Workflow
                    <select
                      aria-label="AI provider"
                      value={prefs.provider}
                      onChange={(e) =>
                        setPrefs({ ...prefs, provider: e.target.value })
                      }
                    >
                      <option value="codex_cli">
                        Codex CLI — preferred automatic provider
                      </option>
                      <option value="claude_cli">
                        Claude Code CLI — setup-token or API key
                      </option>
                      <option value="manual">
                        Manual — export request / import result
                      </option>
                      <option value="openai-compatible">
                        OpenAI-compatible API
                      </option>
                    </select>
                  </label>
                  <label>
                    Model
                    <input
                      value={prefs.model}
                      onChange={(e) =>
                        setPrefs({ ...prefs, model: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    API base URL
                    <input
                      value={prefs.base_url}
                      onChange={(e) =>
                        setPrefs({ ...prefs, base_url: e.target.value })
                      }
                    />
                  </label>
                  <label>
                    Context tokens
                    <input
                      type="number"
                      value={prefs.context_tokens}
                      onChange={(e) =>
                        setPrefs({
                          ...prefs,
                          context_tokens: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    Output token reserve
                    <input
                      type="number"
                      value={prefs.output_tokens}
                      onChange={(e) =>
                        setPrefs({
                          ...prefs,
                          output_tokens: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    AI timeout (seconds)
                    <input
                      type="number"
                      value={prefs.timeout_seconds || 300}
                      onChange={(e) =>
                        setPrefs({
                          ...prefs,
                          timeout_seconds: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    Concurrent AI jobs
                    <input
                      type="number"
                      min="1"
                      max="4"
                      value={prefs.max_concurrent_jobs || 1}
                      onChange={(e) =>
                        setPrefs({
                          ...prefs,
                          max_concurrent_jobs: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    Music preferences
                    <input
                      value={prefs.music_preferences}
                      onChange={(e) =>
                        setPrefs({
                          ...prefs,
                          music_preferences: e.target.value,
                        })
                      }
                    />
                  </label>
                </div>
                <p className="finding">
                  Optional API adapter key:{" "}
                  {prefs.api_key_configured
                    ? "configured in environment"
                    : "not configured"}{" "}
                  · Settings never expose its value.
                </p>
                <button
                  disabled={!!busy}
                  onClick={() =>
                    act("Save settings", async () => {
                      const keys = [
                        "provider",
                        "model",
                        "base_url",
                        "context_tokens",
                        "output_tokens",
                        "music_preferences",
                        "timeout_seconds",
                        "max_concurrent_jobs",
                      ];
                      const r = await api(
                        "/settings",
                        "PUT",
                        Object.fromEntries(keys.map((k) => [k, prefs[k]])),
                      );
                      setPrefs(r);
                      return r;
                    })
                  }
                >
                  Save settings
                </button>
                <div className="provider-tests credentials-panel">
                  <h3>AI credentials</h3>
                  <p className="muted">
                    Paste a token here instead of editing <code>.env</code>. It
                    is saved to this computer's <code>.env</code>, applies
                    immediately (no restart) and is never shown again, only its
                    last four characters. <strong>Codex CLI needs no token</strong>:
                    it uses your own ChatGPT sign-in (run <code>codex login</code>{" "}
                    once in a terminal, then use Test below).
                  </p>
                  {credentials.map((c: Data) => (
                    <div className="panel" key={c.name}>
                      <strong>{c.label}</strong>{" "}
                      <span className="muted">
                        {c.configured
                          ? "✓ Already saved " + c.hint + (c.stored_in_env_file ? " · in .env, ready to use" : " · from environment")
                          : "not set"}
                      </span>
                      <div className="row">
                        <input
                          type="password"
                          autoComplete="off"
                          aria-label={c.label}
                          placeholder={c.configured ? "Paste a new token to replace" : "Paste token"}
                          value={tokenDraft[c.name] || ""}
                          onChange={(e) =>
                            setTokenDraft({ ...tokenDraft, [c.name]: e.target.value })
                          }
                        />
                        <button
                          disabled={!!busy || authorized === false || !(tokenDraft[c.name] || "").trim()}
                          onClick={() =>
                            act("Save token and test " + c.provider, async () => {
                              const saved = await api(
                                "/providers/credentials/" + c.name,
                                "PUT",
                                { value: tokenDraft[c.name] },
                              );
                              setTokenDraft({ ...tokenDraft, [c.name]: "" });
                              setCredentials(saved.credentials);
                              api("/providers").then(setProviderInfo);
                              return { message: "Token saved to this computer and kept for future runs. Testing the connection…" };
                            }).then((saved) => {
                              if (saved) void runTest(c.provider);
                            })
                          }
                        >
                          Save &amp; test
                        </button>
                        {c.configured && c.stored_in_env_file && (
                          <button
                            className="secondary"
                            disabled={!!busy}
                            onClick={() =>
                              act("Remove " + c.name, async () => {
                                const r = await api(
                                  "/providers/credentials/" + c.name,
                                  "DELETE",
                                );
                                setCredentials(r.credentials);
                                api("/providers").then(setProviderInfo);
                                return r;
                              })
                            }
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="provider-tests">
                  <h3>Test AI Connection</h3>
                  <p className="muted">
                    Each automatic test sends a real short structured request
                    with the full ODD FRAME instructions. No provider or billing
                    fallback occurs on failure.
                  </p>
                  {providerInfo?.providers?.map((p: Data) => (
                    <div className="panel" key={p.provider}>
                      <div className="section-heading">
                        <strong>{p.provider}</strong>
                        <button
                          className="secondary"
                          disabled={!!busy || !!testing}
                          onClick={() => void runTest(p.provider)}
                        >
                          {testing === p.provider ? "Testing…" : "Test AI Connection · " + p.provider}
                        </button>
                      </div>
                      <p className="muted">
                        {p.version || p.auth_method} ·{" "}
                        {p.installed
                          ? "Installed / available"
                          : "Not installed"}
                        {p.auth_method ? " · " + p.auth_method : ""}
                      </p>
                      {p.eligibility_message && (
                        <p className="finding">{p.eligibility_message}</p>
                      )}
                      {testing === p.provider && (
                        <p className="notice" role="status">
                          <RefreshCw className="spin" size={14} /> Sending a real
                          short request with all four instructions to{" "}
                          {p.provider}. This usually takes 20–90 seconds; the
                          result appears here.
                        </p>
                      )}
                      {connectionResults[p.provider] && (
                        <p
                          className={
                            connectionResults[p.provider].success
                              ? "notice"
                              : "error"
                          }
                        >
                          {connectionResults[p.provider].code}:{" "}
                          {connectionResults[p.provider].message}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </section>
              <section className="panel">
                <h3>Production defaults</h3>
                <p>{prefs.output}</p>
                <p>{prefs.caption_defaults}</p>
                <p>
                  Source folders: {prefs.root}\episodes · Strict 2D stills · No
                  image motion · No SFX
                </p>
                <p className="footnote">
                  These approved rules are enforced in the backend and renderer.
                  Edit the versioned brand configuration only as an intentional
                  development change.
                </p>
              </section>
              {skillsPanel}
            </>
          )}
        </main>
        <footer>
          ODD FRAME <span>Small Stories. Big Emotions.</span>
          <span>LOCAL-FIRST PRODUCTION · v1.0</span>
        </footer>
      </div>
    </div>
  );
}
mountStudio(App);

import { Button } from "@/components/ui/button";
import React, { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { useQuery } from "@tanstack/react-query";

type Data = Record<string, any>;

const fmt = (iso?: string) => (iso ? new Date(iso).toLocaleTimeString() : "");

/**
 * Official Remotion Studio launcher. ODD FRAME stays the workflow manager; the real Studio (the installed Remotion CLI)
 * is the editing workspace. All status below comes from the backend (real events, no invented percentages).
 */
export function StudioPanel({
  episodeId,
  hasDraft,
  status,
  jobs,
  act,
  busy,
  onChanged,
}: {
  episodeId: number;
  hasDraft: boolean;
  status: string;
  jobs: Data[];
  act: (label: string, fn: () => Promise<any>) => Promise<any>;
  busy: string;
  onChanged: () => void;
}) {
  const [replaceEdits, setReplaceEdits] = useState(false);
  const path = `/episodes/${episodeId}/studio`;
  const studioQuery = useQuery<Data>({
    queryKey: ["studio", episodeId],
    queryFn: ({ signal }) => api(path, "GET", undefined, signal),
    refetchInterval: (q) =>
      q.state.data?.starting ||
      q.state.data?.launch?.status === "STARTING" ||
      ["QUEUED", "RENDERING"].includes(status)
        ? 1500
        : 8000,
  });
  const info = studioQuery.data,
    error = studioQuery.error?.message;
  const refresh = () => studioQuery.refetch();
  const launch = info?.launch as Data | undefined;
  const session = info?.session as Data | undefined;
  const ready = !!session?.running;
  const active = jobs.find((j) => ["QUEUED", "RUNNING"].includes(j.status));
  const edited: string[] = info?.owner_edited_files || [];
  const problems: string[] = info?.source_errors || [];
  const rendering = ["QUEUED", "RENDERING"].includes(status);

  return (
    <section className="panel studio-panel">
      <h3>Remotion Studio — the editor</h3>
      <p className="muted">
        ODD FRAME builds the whole edit for you (stills, captions, transitions,
        narration and music), then opens the official Remotion Studio on this
        computer so you can make small adjustments. Your Studio edits are saved
        to the episode and are what the final video is rendered from.
      </p>
      {error && <p className="error">{error}</p>}
      {active && active.kind === "draft" && (
        <p className="notice" role="status">
          Preparing the edit: {active.stage || "working"}… (live details in AI
          Activity)
        </p>
      )}
      {!info?.exists && (
        <>
          <p>{info?.hint || "No Studio project yet."}</p>
          <Button
            disabled={!!busy || rendering}
            onClick={() =>
              act("Prepare Remotion Studio project", async () => {
                if (hasDraft) {
                  await api(path + "/generate", "POST", {});
                  return {
                    message:
                      "Studio project generated. Click Open in Remotion Studio.",
                  };
                }
                await api(`/episodes/${episodeId}/editor/prepare`, "POST");
                return {
                  message:
                    "Auto Edit started. The Studio project is built when it finishes; follow AI Activity.",
                };
              }).then(refresh)
            }
          >
            {hasDraft
              ? "Generate Studio project"
              : "Auto Edit → build Studio project"}
          </Button>
        </>
      )}
      {info?.exists && (
        <>
          <p>
            <strong>{info.composition_id}</strong> · {info.scene_sequences}{" "}
            still scenes · {info.caption_sequences} caption phrases · style{" "}
            {info.style?.profile_id} · Remotion {info.remotion_version}
            {info.source_editor_revision
              ? ` · built from Auto Edit revision ${info.source_editor_revision}`
              : ""}
          </p>
          {info.valid === false && <p className="error">{info.problem}</p>}
          {problems.length > 0 && (
            <div className="error">
              {problems.map((p) => (
                <p key={p}>{p}</p>
              ))}
            </div>
          )}
          {(info.source_warnings || []).map((w: string) => (
            <p className="finding" key={w}>
              {w}
            </p>
          ))}
          {edited.length > 0 && (
            <p className="notice">
              ✓ Your Studio edits are saved ({edited.join(", ")}). They are kept
              across restarts and used for export.
            </p>
          )}
          <div className="row">
            <Button
              disabled={
                !!busy ||
                rendering ||
                info.starting ||
                info.valid === false ||
                problems.length > 0
              }
              onClick={() =>
                act("Open in Remotion Studio", () =>
                  api(path + "/open", "POST"),
                ).then(refresh)
              }
            >
              {info.starting
                ? "Starting Remotion Studio…"
                : "Open in Remotion Studio"}
            </Button>
            {ready && (
              <a
                className="open-live-editor"
                href={session!.url}
                target="_blank"
                rel="noreferrer"
              >
                Remotion Studio Ready — Open Editor
              </a>
            )}
            {ready && (
              <Button
                variant="outline"
                className="secondary"
                disabled={!!busy}
                onClick={() =>
                  act("Stop Remotion Studio", () =>
                    api(path + "/stop", "POST"),
                  ).then(refresh)
                }
              >
                Stop Studio
              </Button>
            )}
          </div>
          {launch && launch.status !== "READY" && (
            <ol className="studio-stages" aria-label="Remotion Studio start-up">
              {(launch.events || []).map((e: Data, i: number) => (
                <li key={i} className={e.stage === "Failed" ? "error" : ""}>
                  <strong>{e.stage}</strong>{" "}
                  <span className="muted">{fmt(e.at)}</span> — {e.message}
                </li>
              ))}
            </ol>
          )}
          {launch?.status === "FAILED" && (
            <div className="row">
              <Button
                onClick={() =>
                  act("Retry Remotion Studio", () =>
                    api(path + "/open", "POST"),
                  ).then(refresh)
                }
              >
                Retry
              </Button>
            </div>
          )}
          {ready && (
            <p className="muted">
              Running at {session!.url} (local only, port {session!.port}).
              {launch?.startup_seconds
                ? ` Started in ${launch.startup_seconds} s.`
                : ""}{" "}
              Edits you save in Studio persist in <code>{info.folder}</code>.
            </p>
          )}
          <hr />
          <div className="row">
            <Button
              disabled={
                !!busy ||
                rendering ||
                problems.length > 0 ||
                info.valid === false
              }
              onClick={() =>
                act("Render final MP4 from Remotion Studio", () =>
                  api(path + "/render", "POST"),
                ).then(() => {
                  void refresh();
                  onChanged();
                })
              }
            >
              Render final MP4 from this Studio project
            </Button>
            <span className="muted">
              Uses exactly the project you reviewed. Earlier exports are never
              overwritten.
            </span>
          </div>
          <details>
            <summary>
              Rebuild the Studio project from the latest Auto Edit
            </summary>
            <p className="muted">
              Your Studio edits are never overwritten without permission. The
              current source is archived under <code>studio/revisions</code>{" "}
              before any rebuild.
            </p>
            {edited.length > 0 && (
              <label className="inline">
                <input
                  type="checkbox"
                  checked={replaceEdits}
                  onChange={(e) => setReplaceEdits(e.target.checked)}
                />{" "}
                Replace my Studio edits ({edited.join(", ")})
              </label>
            )}
            <Button
              className="secondary"
              disabled={
                !!busy || rendering || (edited.length > 0 && !replaceEdits)
              }
              onClick={() =>
                act("Rebuild Studio project", () =>
                  api(path + "/generate", "POST", {
                    replace_my_edits: replaceEdits,
                  }),
                ).then(() => {
                  setReplaceEdits(false);
                  void refresh();
                })
              }
            >
              Rebuild Studio project
            </Button>
          </details>
          {info.style?.profile_id !== "ODD_FRAME_CINEMATIC_TRANSITIONS_V1" && (
            <details open>
              <summary>
                <strong>Upgrade transitions:</strong> this episode uses{" "}
                {info.style?.profile_id}. Use Cinematic Transitions v1 for
                narrative-aware cuts, crossfades and dips with wave + glow
                captions
              </summary>
              <p className="muted">
                This episode was edited with {info.style?.profile_id}. Adopting
                Cinematic Transitions v1 adds the newer style to this episode
                only, re-runs Auto Edit and rebuilds the Studio project. Your
                approved script, stills, narration and earlier exports are not
                touched.{" "}
                {edited.length > 0
                  ? 'Tick "Replace my Studio edits" above to allow replacing your current Studio edits (they are archived first).'
                  : ""}
              </p>
              <Button
                variant="outline"
                className="secondary"
                disabled={
                  !!busy || rendering || (edited.length > 0 && !replaceEdits)
                }
                onClick={() =>
                  act(
                    "Adopt Cinematic Transitions v1 and rebuild",
                    async () => {
                      await api(`/episodes/${episodeId}/style`, "PUT", {
                        profile_id: "ODD_FRAME_CINEMATIC_TRANSITIONS_V1",
                        adopt: true,
                      });
                      await api(
                        `/episodes/${episodeId}/editor/rebuild`,
                        "POST",
                        { replace_studio_edits: replaceEdits },
                      );
                      return {
                        message:
                          "Cinematic Transitions v1 adopted. Auto Edit is rebuilding the Studio project; follow AI Activity.",
                      };
                    },
                  ).then(refresh)
                }
              >
                Adopt Cinematic Transitions v1 and rebuild
              </Button>
            </details>
          )}
          <details>
            <summary>What can I change in Studio?</summary>
            <h4>Visual controls in Studio</h4>
            <ul>
              {(info.capabilities?.visual || []).map((c: string) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <h4>Needs a change in the source file</h4>
            <ul>
              {(info.capabilities?.source_only || []).map((c: string) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <h4>Not allowed</h4>
            <ul>
              {(info.capabilities?.blocked || []).map((c: string) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
            <p className="muted">
              {(info.capabilities?.not_verified || []).join(" ")}
            </p>
          </details>
        </>
      )}
    </section>
  );
}

import { useQuery } from "@tanstack/react-query";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { api } from "./api";
import { IdeaProgress } from "./idea-progress";
import "./provider-progress.css";
export function ProductionActivity({ run, now }: { run: any; now: number }) {
  const query = useQuery<any[]>({
    queryKey: ["activity"],
    queryFn: ({ signal }) => api("/activity", "GET", undefined, signal),
    refetchInterval: 15000,
  });
  const observed = query.data?.find((j) => j.job_id === run.id);
  const job =
    observed && !(run.status === "SUCCEEDED" && observed.status !== "SUCCEEDED")
      ? observed
      : run;
  const events = job.events || [];
  const has = (type: string) => events.some((e: any) => e.type === type);
  const done = job.status === "SUCCEEDED",
    failed = ["FAILED", "CANCELLED"].includes(job.status);
  const phases = [
    ["Validate pinned creative context", has("skills.validated")],
    ["Start authorized provider", has("ai.started")],
    ["Receive complete provider response", has("ai.completed")],
    ["Validate structured output", has("output.saving") || done],
    ["Save and verify production artifacts", done],
  ] as const;
  return (
    <Card className="my-5" aria-label="Live production activity">
      <CardHeader>
        <CardTitle>Live Production Activity</CardTitle>
        <CardDescription>
          {job.episode_title || "Episode production"} ·{" "}
          {job.episode_code || `Episode ${run.episode_id ?? "ideas"}`} ·{" "}
          {job.provider}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p>
          Job {run.id} · Attempt {job.attempt_number || 1} · {job.status}
        </p>
        {(job.worker_timeout_seconds || run.worker_timeout_seconds) && (
          <p>
            Isolated provider worker deadline:{" "}
            {job.worker_timeout_seconds || run.worker_timeout_seconds}s after
            launch. It remains bounded even while activity is received.
          </p>
        )}
        <p>
          Elapsed{" "}
          {Math.max(
            0,
            Math.floor(
              ((job.finished_at ? Date.parse(job.finished_at) : now) -
                Date.parse(job.started_at || run.created)) /
                1000,
            ),
          )}
          s. Connection status is shown in AI Activity; it does not confirm
          provider progress.
        </p>
        {run.task === "prepare" && (
          <ol className="production-stage-list" aria-label="Production stages">
            {phases.map(([label, complete], i) => (
              <li key={label} data-done={complete}>
                <span aria-hidden="true">{complete ? "✓" : "○"}</span> {label} —{" "}
                {complete
                  ? "Complete"
                  : failed
                    ? "Not completed"
                    : phases.slice(0, i).every((p) => p[1])
                      ? "Waiting / in progress"
                      : "Pending"}
              </li>
            ))}
          </ol>
        )}
        <IdeaProgress
          progress={job.generation_progress}
          status={job.status}
          stage={job.stage}
          now={now}
        />
        {run.task === "prepare" && !done && (
          <p>
            Character Bible, storyboard and Flow prompts are generated together.
            Individual documents are confirmed only after validation and saving.
            Recorded narration audio is supplied separately.
          </p>
        )}
        {job.failure && (
          <div role="alert" className="error">
            <strong>{job.failure.category}</strong>
            <p>{job.failure.message}</p>
            <p>
              Failed stage: {job.failure.failed_stage} ·{" "}
              {job.failure.failed_at || "Historical timestamp unavailable"} ·{" "}
              {job.failure.elapsed_seconds ?? "Unknown"}s elapsed
            </p>
          </div>
        )}
        <details>
          <summary>Recent confirmed events</summary>
          <ol>
            {events.slice(-15).map((e: any) => (
              <li key={e.event_id}>
                {new Date(e.timestamp).toLocaleTimeString()} — {e.message}
              </li>
            ))}
          </ol>
        </details>
      </CardContent>
    </Card>
  );
}

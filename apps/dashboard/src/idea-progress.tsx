export type GenerationProgress = {
  phase: string;
  message: string;
  request_sent: boolean;
  last_event_at: string | null;
  last_provider_event_at?: string | null;
  last_process_check_at?: string | null;
  milestones: { phase: string; message: string; timestamp: string }[];
};
export function IdeaProgress({
  progress,
  status,
  stage,
  now,
}: {
  progress?: GenerationProgress;
  status: string;
  stage?: string;
  now: number;
}) {
  const confirmed =
    !!progress &&
    [
      "sent",
      "connected",
      "generating",
      "validating",
      "saving",
      "complete",
    ].includes(progress.phase);
  const last = progress?.last_event_at
    ? Date.parse(progress.last_event_at)
    : NaN;
  const quiet = Number.isFinite(last)
    ? Math.max(0, Math.floor((now - last) / 1000))
    : 0;
  return (
    <div className="idea-provider-progress" data-confirmed={confirmed}>
      <p role="status">
        <span className="idea-provider-dot" aria-hidden="true" />
        <strong>
          {progress?.message || stage || "Waiting for provider checks"}
        </strong>
      </p>
      {progress?.last_provider_event_at && (
        <p>
          Last provider activity:{" "}
          {new Date(progress.last_provider_event_at).toLocaleTimeString()}.
        </p>
      )}
      {status === "RUNNING" && progress?.last_process_check_at && (
        <p>
          CLI process last verified running at{" "}
          {new Date(progress.last_process_check_at).toLocaleTimeString()}. This
          confirms process liveness, not model progress.
        </p>
      )}
      {!!progress?.milestones.length && (
        <ol aria-label="Provider milestones">
          {progress.milestones.slice(-4).map((v, i) => (
            <li key={v.timestamp + i}>
              {v.message}{" "}
              <time dateTime={v.timestamp}>
                {new Date(v.timestamp).toLocaleTimeString()}
              </time>
            </li>
          ))}
        </ol>
      )}
      {status === "RUNNING" && quiet >= 45 && (
        <p className="idea-provider-wait">
          No new provider milestone for {quiet}s.{" "}
          {confirmed
            ? "The attempt remains running; completion has not been confirmed."
            : "Sending to the provider is not yet confirmed; preflight may still be running."}{" "}
          Elapsed time alone does not establish a credit or account problem.
        </p>
      )}
    </div>
  );
}

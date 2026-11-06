export function latestAttemptIds(
  jobs: {
    id?: string;
    job_id?: string;
    job_group_id?: string;
    attempt_number?: number;
    created: string;
  }[],
) {
  const groups = new Map<string, (typeof jobs)[number]>();
  for (const job of jobs) {
    const key = job.job_group_id || job.job_id || job.id!;
    const prior = groups.get(key);
    if (
      !prior ||
      (job.attempt_number || 1) > (prior.attempt_number || 1) ||
      ((job.attempt_number || 1) === (prior.attempt_number || 1) &&
        job.created > prior.created)
    )
      groups.set(key, job);
  }
  return new Set([...groups.values()].map((j) => j.job_id || j.id));
}

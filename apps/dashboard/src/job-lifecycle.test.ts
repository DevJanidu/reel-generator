import { expect, it } from "vitest";
import { latestAttemptIds } from "./job-lifecycle";
it("keeps old failures historical even when events arrive out of order", () => {
  const old = {
    id: "one",
    job_group_id: "one",
    attempt_number: 1,
    created: "2026-01-01",
  };
  const next = {
    id: "two",
    job_group_id: "one",
    attempt_number: 2,
    created: "2026-01-02",
  };
  expect([...latestAttemptIds([next, old])]).toEqual(["two"]);
  expect([
    ...latestAttemptIds([old, next, { id: "other", created: "2026-01-01" }]),
  ]).toEqual(["two", "other"]);
});

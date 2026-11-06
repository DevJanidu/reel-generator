import { describe, expect, it } from "vitest";
import { statusTone } from "./status-badge";
describe("job status semantics", () => {
  it("only uses success for confirmed positive states", () => {
    expect(statusTone("SUCCEEDED")).toBe("success");
    expect(statusTone("RUNNING")).toBe("neutral");
    expect(statusTone("QUEUED")).toBe("neutral");
  });
  it("distinguishes actionable warnings from errors", () => {
    expect(statusTone("ASSETS_BLOCKED")).toBe("warning");
    expect(statusTone("AWAITING_APPROVAL")).toBe("warning");
    expect(statusTone("FAILED")).toBe("error");
    expect(statusTone("MISSING")).toBe("error");
  });
});

import { describe, expect, it } from "vitest";
import {
  folderEntries,
  formatSize,
  type FileEntry,
} from "./file-explorer-model";
const entry = (
  path: string,
  kind: "directory" | "file" = "file",
  size_bytes: number | null = 10,
): FileEntry => ({
  path,
  kind,
  size_bytes,
  modified_at: "2026-11-06T00:00:00Z",
});
describe("episode file explorer", () => {
  it("shows only direct children and keeps generated folders separate", () => {
    const result = folderEntries(
      [
        entry("05_assets/images", "directory", null),
        entry("05_assets/images/S001.png"),
        entry("05_assets/narration", "directory", null),
        entry("01_script/narration.txt"),
      ],
      "05_assets",
      "",
      "name",
    );
    expect(result.map((e) => e.path)).toEqual([
      "05_assets/images",
      "05_assets/narration",
    ]);
  });
  it("sorts folders before files and naturally orders scene numbers", () => {
    const entries = [
      entry("a/S10.png"),
      entry("a/S2.png"),
      entry("a/approved", "directory", null),
    ];
    expect(folderEntries(entries, "a", "", "name").map((e) => e.path)).toEqual([
      "a/approved",
      "a/S2.png",
      "a/S10.png",
    ]);
    expect(
      folderEntries(entries, "a", "", "name", true).map((e) => e.path),
    ).toEqual(["a/approved", "a/S10.png", "a/S2.png"]);
  });
  it("filters the current folder and sorts genuine sizes", () => {
    const entries = [
      entry("a/Voice.wav", "file", 400),
      entry("a/script.txt", "file", 20),
      entry("b/Voice.wav"),
    ];
    expect(
      folderEntries(entries, "a", "voice", "size").map((e) => e.path),
    ).toEqual(["a/Voice.wav"]);
    expect(
      folderEntries(entries, "a", "", "size").map((e) => e.size_bytes),
    ).toEqual([20, 400]);
  });
  it("does not invent folder sizes", () => {
    expect(formatSize(null)).toBe("—");
    expect(formatSize(0)).toBe("0 B");
    expect(formatSize(2048)).toBe("2.0 KB");
  });
});

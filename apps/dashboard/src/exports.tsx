import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import React, { useEffect, useMemo, useState } from "react";
import { Download, Trash2 } from "lucide-react";
import { Paged } from "./paging";

type Data = Record<string, any>;

/**
 * Finished exports of one episode: search, pages, multi-select and a two-step permanent delete.
 * Selection is kept across pages and searches; rows that no longer exist are dropped from it automatically.
 */
export function ExportsPanel({
  exports,
  episodeId,
  fileURL,
  disabled,
  onDelete,
  Badge,
  Empty,
}: {
  exports: Data[];
  episodeId: number;
  fileURL: (relative: string) => string;
  disabled: boolean;
  onDelete: (ids: number[]) => Promise<unknown>;
  Badge: React.FC<{ value: string }>;
  Empty: React.FC<{ text: string }>;
}) {
  const [picked, setPicked] = useState<number[]>([]);
  const [confirming, setConfirming] = useState(false);
  const newestFirst = useMemo(
    () =>
      [...exports].sort(
        (a, b) =>
          (b.created || "").localeCompare(a.created || "") ||
          b.job_id - a.job_id,
      ),
    [exports],
  );
  const existing = useMemo(
    () => new Set(exports.map((e) => e.job_id)),
    [exports],
  );
  useEffect(() => {
    setPicked((p) => p.filter((id) => existing.has(id)));
  }, [existing]);
  useEffect(() => {
    setPicked([]);
    setConfirming(false);
  }, [episodeId]);
  useEffect(() => {
    if (!picked.length) setConfirming(false);
  }, [picked.length]);
  const toggle = (id: number) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const text = (e: Data) =>
    `${e.path.split("/").pop()} ${new Date(e.created).toLocaleString()} v${e.job_id} ${e.source || ""} ${e.style?.profile_id || ""}`;
  if (!exports.length)
    return (
      <Empty text="No final exports yet. Nothing is published automatically." />
    );
  return (
    <Paged
      items={newestFirst}
      size={5}
      label="exports"
      placeholder="Search exports by file name, date or style"
      getText={text}
      toolbar={null}
    >
      {(rows, info) => {
        const pageIds = rows.map((r) => r.job_id as number);
        const allOnPage = pageIds.every((id) => picked.includes(id));
        return (
          <>
            <div
              className="export-select"
              role="group"
              aria-label="Select exports to delete"
            >
              <label>
                <input
                  type="checkbox"
                  checked={allOnPage}
                  disabled={disabled}
                  onChange={() =>
                    setPicked((p) =>
                      allOnPage
                        ? p.filter((id) => !pageIds.includes(id))
                        : [...new Set([...p, ...pageIds])],
                    )
                  }
                />{" "}
                Select all on this page
              </label>
              {info.filtered > rows.length && (
                <Button
                  type="button"
                  className="text-button"
                  disabled={disabled}
                  onClick={() => {
                    const matching = newestFirst.filter(
                      (e) =>
                        !info.query ||
                        info.query
                          .toLowerCase()
                          .split(/\s+/)
                          .filter(Boolean)
                          .every((w) => text(e).toLowerCase().includes(w)),
                    );
                    setPicked([
                      ...new Set([
                        ...picked,
                        ...matching.map((e) => e.job_id as number),
                      ]),
                    ]);
                  }}
                >
                  Select all {info.filtered}
                  {info.query ? " matching" : ""}
                </Button>
              )}
              {picked.length > 0 && (
                <>
                  <strong>{picked.length} selected</strong>
                  <Button
                    type="button"
                    className="text-button"
                    onClick={() => setPicked([])}
                  >
                    Clear
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={disabled}
                    onClick={() => setConfirming(true)}
                  >
                    <Trash2 size={16} />
                    Delete {picked.length} selected
                  </Button>
                  <AlertDialog open={confirming} onOpenChange={setConfirming}>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          Delete {picked.length} exports permanently?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          The selected final videos and preview clips will be
                          deleted. This cannot be undone. Your script, stills,
                          audio and Studio source are preserved.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={disabled}>
                          Keep them
                        </AlertDialogCancel>
                        <Button
                          variant="destructive"
                          disabled={disabled}
                          onClick={async () => {
                            await onDelete(picked);
                            setConfirming(false);
                          }}
                        >
                          Yes, delete {picked.length}
                        </Button>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </>
              )}
            </div>
            {rows.map((e) => (
              <div
                key={e.job_id}
                className={
                  "export" + (picked.includes(e.job_id) ? " selected" : "")
                }
              >
                <input
                  type="checkbox"
                  aria-label={"Select " + e.path.split("/").pop()}
                  checked={picked.includes(e.job_id)}
                  disabled={disabled}
                  onChange={() => toggle(e.job_id)}
                />
                <Badge value="COMPLETE" />
                <strong>{e.path.split("/").pop()}</strong>
                <span>{new Date(e.created).toLocaleString()}</span>
                <a className="button" download href={"/api/media/" + e.path}>
                  <Download size={15} />
                  Final MP4
                </a>
                <a
                  className="button secondary"
                  href={fileURL("07_export/QC_REPORT.md")}
                  target="_blank"
                  rel="noreferrer"
                >
                  Current episode QC report
                </a>
                <details className="export-preview">
                  <summary>Preview this export · render #{e.job_id}</summary>
                  <video
                    controls
                    preload="none"
                    aria-label={"Preview " + e.path.split("/").pop()}
                    src={"/api/media/" + (e.preview || e.path)}
                  />
                </details>
              </div>
            ))}
          </>
        );
      }}
    </Paged>
  );
}

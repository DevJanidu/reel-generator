export type FileEntry = {
  path: string;
  kind: "directory" | "file";
  size_bytes: number | null;
  modified_at: string;
};
export const fileName = (path: string) => path.split("/").at(-1) || path;
export const parentPath = (path: string) =>
  path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
export function folderEntries(
  entries: FileEntry[],
  folder: string,
  query: string,
  sort: string,
  descending = false,
) {
  const collator = new Intl.Collator(undefined, {
    numeric: true,
    sensitivity: "base",
  });
  const matching = entries.filter(
    (e) =>
      parentPath(e.path) === folder &&
      fileName(e.path).toLowerCase().includes(query.trim().toLowerCase()),
  );
  return matching.sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "directory" ? -1 : 1;
    const cmp =
      sort === "size"
        ? (a.size_bytes ?? 0) - (b.size_bytes ?? 0)
        : sort === "modified"
          ? Date.parse(a.modified_at) - Date.parse(b.modified_at)
          : sort === "type"
            ? collator.compare(
                fileName(a.path).split(".").at(-1) || "",
                fileName(b.path).split(".").at(-1) || "",
              )
            : 0;
    return (
      (descending ? -1 : 1) *
      (cmp || collator.compare(fileName(a.path), fileName(b.path)))
    );
  });
}
export function formatSize(bytes: number | null) {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Folder,
  FolderOpen,
  FileText,
  FileImage,
  FileAudio,
  FileVideo,
  File as GenericFile,
  ChevronRight,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  Upload,
  Download,
  Search,
  LayoutGrid,
  List,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from "@/components/ui/table";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import {
  folderEntries,
  fileName,
  parentPath,
  formatSize,
  type FileEntry,
} from "./file-explorer-model";

const roles = [
  ["images", "Images"],
  ["narration", "Narration"],
  ["subtitles", "Subtitles"],
  ["music", "Music"],
] as const;
const extension = (path: string) =>
  fileName(path).split(".").at(-1)?.toLowerCase() || "";
function kindName(entry: FileEntry) {
  const ext = extension(entry.path);
  return entry.kind === "directory"
    ? "Folder"
    : ext
      ? ext.toUpperCase() + " file"
      : "File";
}
function FileIcon({ entry }: { entry: FileEntry }) {
  const ext = extension(entry.path);
  const Icon =
    entry.kind === "directory"
      ? Folder
      : ["png", "jpg", "jpeg", "webp"].includes(ext)
        ? FileImage
        : ["wav", "mp3", "m4a", "aac", "flac", "ogg"].includes(ext)
          ? FileAudio
          : ["mp4", "mov", "webm"].includes(ext)
            ? FileVideo
            : ["md", "txt", "srt", "json", "csv"].includes(ext)
              ? FileText
              : GenericFile;
  return <Icon aria-hidden="true" />;
}

export function AssetExplorer({
  episodeId,
  episodeCode,
  entries,
  disabled,
  canUpload,
  fileURL,
  onUpload,
  onRemove,
}: {
  episodeId: number;
  episodeCode: string;
  entries: FileEntry[];
  disabled: boolean;
  canUpload: boolean;
  fileURL: (path: string) => string;
  onUpload: (kind: string, files: File[]) => Promise<unknown>;
  onRemove: (path: string) => Promise<unknown>;
}) {
  const [folder, setFolder] = useState("05_assets"),
    [history, setHistory] = useState<string[]>([]),
    [query, setQuery] = useState(""),
    [sort, setSort] = useState("name"),
    [descending, setDescending] = useState(false),
    [view, setView] = useState<"list" | "grid">(() =>
      localStorage.getItem("odd-file-view") === "grid" ? "grid" : "list",
    ),
    [preview, setPreview] = useState<FileEntry | null>(null),
    [removing, setRemoving] = useState<FileEntry | null>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    setFolder("05_assets");
    setHistory([]);
    setPreview(null);
    setQuery("");
    setRemoving(null);
  }, [episodeId]);
  function navigate(path: string) {
    setHistory((h) => [...h, folder]);
    setFolder(path);
    setQuery("");
  }
  const directories = entries.filter((e) => e.kind === "directory"),
    exists = (path: string) => directories.some((d) => d.path === path);
  const rows = folderEntries(entries, folder, query, sort, descending),
    role = roles.find(([id]) => folder === "05_assets/" + id)?.[0];
  const isRemovable = (entry: FileEntry) =>
    entry.kind === "file" &&
    roles.some(([id]) => parentPath(entry.path) === "05_assets/" + id);
  const selectedPreview = preview
    ? entries.find((e) => e.path === preview.path) || preview
    : null;
  const textPreview = useQuery({
    queryKey: [
      "file-preview",
      episodeId,
      selectedPreview?.path,
      selectedPreview?.modified_at,
    ],
    enabled:
      !!selectedPreview &&
      selectedPreview.kind === "file" &&
      [
        "md",
        "txt",
        "srt",
        "json",
        "csv",
        "tsx",
        "ts",
        "py",
        "yaml",
        "yml",
      ].includes(extension(selectedPreview.path)) &&
      (selectedPreview.size_bytes ?? Infinity) <= 200000,
    queryFn: async ({ signal }) => {
      const response = await fetch(fileURL(selectedPreview!.path), { signal });
      if (!response.ok)
        throw Error("This file could not be read. Retry or download it.");
      return response.text();
    },
  });
  const crumbs = folder ? folder.split("/") : [];
  function open(entry: FileEntry) {
    if (entry.kind === "directory") navigate(entry.path);
    else setPreview(entry);
  }
  function fileActions(entry: FileEntry) {
    return (
      <div className="explorer-file-actions">
        <Button variant="ghost" size="icon" asChild>
          <a
            href={fileURL(entry.path)}
            download
            aria-label={"Download " + fileName(entry.path)}
          >
            <Download />
          </a>
        </Button>
        {isRemovable(entry) && (
          <Button
            variant="ghost"
            size="icon"
            disabled={disabled}
            aria-label={"Remove " + fileName(entry.path)}
            onClick={() => setRemoving(entry)}
          >
            <Trash2 />
          </Button>
        )}
      </div>
    );
  }
  return (
    <section className="file-explorer" aria-label="Episode file explorer">
      <aside className="explorer-sidebar" aria-label="File folders" tabIndex={0}>
        <p className="explorer-section-label">Assets</p>
        <Button
          variant="ghost"
          className={!folder ? "selected" : ""}
          onClick={() => navigate("")}
        >
          <FolderOpen />
          All episode folders
        </Button>
        {exists("05_assets") && (
          <Button
            variant="ghost"
            className={folder === "05_assets" ? "selected" : ""}
            onClick={() => navigate("05_assets")}
          >
            <Folder />
            05_assets
          </Button>
        )}
        {roles
          .filter(([id]) => exists("05_assets/" + id))
          .map(([id, label]) => (
            <Button
              variant="ghost"
              className={folder === "05_assets/" + id ? "selected" : ""}
              key={id}
              onClick={() => navigate("05_assets/" + id)}
            >
              <Folder />
              {label}
            </Button>
          ))}
        <p className="explorer-section-label">Episode folders</p>
        {directories
          .filter((d) => !d.path.includes("/") && d.path !== "05_assets")
          .map((d) => (
            <Button
              variant="ghost"
              className={folder === d.path ? "selected" : ""}
              key={d.path}
              onClick={() => navigate(d.path)}
            >
              <Folder />
              {d.path}
            </Button>
          ))}
      </aside>
      <div className="explorer-main">
        <div className="explorer-toolbar">
          <div className="explorer-navigation">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Back to previous folder"
              disabled={!history.length}
              onClick={() => {
                setFolder(history.at(-1)!);
                setHistory((h) => h.slice(0, -1));
                setQuery("");
              }}
            >
              <ArrowLeft />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Up one folder"
              disabled={!folder}
              onClick={() => navigate(parentPath(folder))}
            >
              <ArrowUp />
            </Button>
          </div>
          <div className="explorer-search">
            <Search aria-hidden="true" />
            <Input
              aria-label="Search this folder"
              placeholder="Search this folder"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <Select value={sort} onValueChange={setSort}>
            <SelectTrigger aria-label="Sort files">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="type">Kind</SelectItem>
              <SelectItem value="modified">Modified</SelectItem>
              <SelectItem value="size">Size</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="icon"
            aria-label={descending ? "Sort ascending" : "Sort descending"}
            onClick={() => setDescending(!descending)}
          >
            {descending ? <ArrowDown /> : <ArrowUp />}
          </Button>
          <div className="explorer-views" role="group" aria-label="File view">
            <Button
              variant={view === "list" ? "secondary" : "ghost"}
              size="icon"
              aria-label="List view"
              aria-pressed={view === "list"}
              onClick={() => {
                setView("list");
                localStorage.setItem("odd-file-view", "list");
              }}
            >
              <List />
            </Button>
            <Button
              variant={view === "grid" ? "secondary" : "ghost"}
              size="icon"
              aria-label="Grid view"
              aria-pressed={view === "grid"}
              onClick={() => {
                setView("grid");
                localStorage.setItem("odd-file-view", "grid");
              }}
            >
              <LayoutGrid />
            </Button>
          </div>
        </div>
        <nav className="explorer-breadcrumbs" aria-label="File path">
          <Button variant="link" onClick={() => navigate("")}>
            {episodeCode}
          </Button>
          {crumbs.map((name, index) => (
            <span key={index}>
              <ChevronRight aria-hidden="true" />
              <Button
                variant="link"
                aria-current={
                  index === crumbs.length - 1 ? "location" : undefined
                }
                onClick={() => navigate(crumbs.slice(0, index + 1).join("/"))}
              >
                {name}
              </Button>
            </span>
          ))}
        </nav>
        <div className="explorer-folder-heading">
          <div>
            <h3>{folder ? fileName(folder) : "Episode files"}</h3>
            <p>
              {rows.length} {rows.length === 1 ? "item" : "items"}
              {query ? " matching your search" : ""}
            </p>
          </div>
          {role && (
            <>
              <Input
                ref={uploadRef}
                hidden
                type="file"
                aria-label={"Import " + role}
                multiple={role === "images"}
                disabled={disabled || !canUpload}
                accept={
                  role === "images"
                    ? ".png,.jpg,.jpeg,.webp"
                    : role === "subtitles"
                      ? ".srt"
                      : ".wav,.mp3,.m4a,.aac,.flac,.ogg"
                }
                onChange={async (e) => {
                  const files = Array.from(e.target.files || []);
                  e.target.value = "";
                  if (files.length) await onUpload(role, files);
                }}
              />
              <Button
                disabled={disabled || !canUpload}
                onClick={() => uploadRef.current?.click()}
              >
                <Upload />
                Import {role}
              </Button>
            </>
          )}
        </div>
        <ScrollArea className="explorer-files">
          {!rows.length ? (
            <div className="explorer-empty">
              <FolderOpen />
              <h4>{query ? "No matching files" : "This folder is empty"}</h4>
              <p>
                {query
                  ? "Try another name or clear the search."
                  : role
                    ? "Import files into this folder to get started."
                    : "Choose a folder to browse its contents."}
              </p>
              {query && (
                <Button variant="outline" onClick={() => setQuery("")}>
                  Clear search
                </Button>
              )}
            </div>
          ) : view === "list" ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Kind</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Modified</TableHead>
                  <TableHead>
                    <span className="sr-only">File actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((entry) => (
                  <TableRow key={entry.path}>
                    <TableCell>
                      <Button
                        variant="ghost"
                        className="explorer-name"
                        onClick={() => open(entry)}
                        aria-label={
                          (entry.kind === "directory"
                            ? "Open folder "
                            : "Preview ") + fileName(entry.path)
                        }
                      >
                        <FileIcon entry={entry} />
                        <span>{fileName(entry.path)}</span>
                        {entry.kind === "directory" && <ChevronRight />}
                      </Button>
                    </TableCell>
                    <TableCell>{kindName(entry)}</TableCell>
                    <TableCell>{formatSize(entry.size_bytes)}</TableCell>
                    <TableCell>
                      {new Date(entry.modified_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {entry.kind === "file" && fileActions(entry)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="explorer-grid">
              {rows.map((entry) => (
                <div className="explorer-tile" key={entry.path}>
                  <Button
                    variant="ghost"
                    onClick={() => open(entry)}
                    aria-label={
                      (entry.kind === "directory"
                        ? "Open folder "
                        : "Preview ") + fileName(entry.path)
                    }
                  >
                    {entry.kind === "file" &&
                    ["png", "jpg", "jpeg", "webp"].includes(
                      extension(entry.path),
                    ) ? (
                      <img loading="lazy" src={fileURL(entry.path)} alt="" />
                    ) : (
                      <FileIcon entry={entry} />
                    )}
                    <span>{fileName(entry.path)}</span>
                    <small>
                      {entry.kind === "directory"
                        ? "Folder"
                        : formatSize(entry.size_bytes)}
                    </small>
                  </Button>
                  {entry.kind === "file" && fileActions(entry)}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
        <p className="explorer-footer">
          {episodeCode}
          {folder ? " / " + folder : ""} · Actual episode folders
          {role ? " · Imports stay in this folder" : ""}
        </p>
      </div>
      <Sheet
        open={!!selectedPreview}
        onOpenChange={(open) => {
          if (!open) setPreview(null);
        }}
      >
        <SheetContent className="explorer-preview sm:max-w-xl overflow-y-auto p-6">
          <SheetHeader>
            <SheetTitle>
              {selectedPreview
                ? fileName(selectedPreview.path)
                : "File preview"}
            </SheetTitle>
            <SheetDescription>{selectedPreview?.path}</SheetDescription>
          </SheetHeader>
          {selectedPreview && (
            <>
              <p>
                {kindName(selectedPreview)} ·{" "}
                {formatSize(selectedPreview.size_bytes)}
              </p>
              {["png", "jpg", "jpeg", "webp"].includes(
                extension(selectedPreview.path),
              ) ? (
                <img
                  src={fileURL(selectedPreview.path)}
                  alt={fileName(selectedPreview.path)}
                />
              ) : ["wav", "mp3", "m4a", "aac", "flac", "ogg"].includes(
                  extension(selectedPreview.path),
                ) ? (
                <audio
                  controls
                  preload="metadata"
                  src={fileURL(selectedPreview.path)}
                />
              ) : ["mp4", "mov", "webm"].includes(
                  extension(selectedPreview.path),
                ) ? (
                <video
                  controls
                  preload="metadata"
                  src={fileURL(selectedPreview.path)}
                />
              ) : textPreview.isFetching ? (
                <p role="status">Loading file…</p>
              ) : textPreview.isError ? (
                <p role="alert">{textPreview.error.message}</p>
              ) : textPreview.data !== undefined ? (
                <pre>{textPreview.data}</pre>
              ) : (
                <p>
                  Download this file to open it in its associated application.
                </p>
              )}
              <Button asChild>
                <a href={fileURL(selectedPreview.path)} download>
                  <Download />
                  Download file
                </a>
              </Button>
            </>
          )}
        </SheetContent>
      </Sheet>
      <AlertDialog
        open={!!removing}
        onOpenChange={(open) => {
          if (!open) setRemoving(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Remove {removing ? fileName(removing.path) : "asset"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This removes the uploaded asset from this episode. Approved
              narration and pinned inputs remain protected. You may need to
              import a replacement and validate again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={disabled}>Keep file</AlertDialogCancel>
            <Button
              variant="destructive"
              disabled={disabled}
              onClick={async () => {
                if (removing) {
                  await onRemove(removing.path);
                  setRemoving(null);
                  if (preview?.path === removing.path) setPreview(null);
                }
              }}
            >
              Remove file
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}

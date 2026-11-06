import React, {useEffect, useMemo, useState} from "react";
import "./paging.css";

export const PAGE_SIZES = [5, 10, 25, 50];

/** Pure paging maths (exported for tests): clamps the page so deleting rows or narrowing a search never shows an empty page. */
export function pageWindow(total: number, page: number, size: number) {
  const pages = Math.max(1, Math.ceil(total / size));
  const current = Math.min(Math.max(1, page), pages);
  const from = total ? (current - 1) * size : 0;
  const to = Math.min(total, from + size);
  return {pages, current, from, to};
}

/**
 * Search + pagination for any list of rows.
 * - `getText` makes a search box appear (matches every word, case-insensitive); the page returns to 1 when the search changes.
 * - The page is clamped automatically when rows disappear (for example after deleting exports).
 * - `children(rows, info)` renders only the current page; `total` rows are always reachable through the page buttons.
 */
export function Paged<T>({
  items,
  children,
  getText,
  size = 10,
  label = "rows",
  placeholder,
  empty,
  resetKey,
  toolbar,
}: {
  items: T[];
  children: (rows: T[], info: {total: number; filtered: number; query: string}) => React.ReactNode;
  getText?: (item: T) => string;
  size?: number;
  label?: string;
  placeholder?: string;
  empty?: React.ReactNode;
  resetKey?: unknown;
  toolbar?: React.ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(size);
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  const filtered = useMemo(
    () => (getText && words.length ? items.filter((i) => {
      const text = getText(i).toLowerCase();
      return words.every((w) => text.includes(w));
    }) : items),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [items, query, getText],
  );
  useEffect(() => setPage(1), [query, pageSize, resetKey]);
  const w = pageWindow(filtered.length, page, pageSize);
  useEffect(() => {
    if (w.current !== page) setPage(w.current);
  }, [w.current, page]);
  const rows = filtered.slice(w.from, w.to);
  const showControls = filtered.length > Math.min(...PAGE_SIZES) || pageSize !== size;
  return (
    <div className="paged">
      {(getText || toolbar) && (
        <div className="paged-tools">
          {getText && (
            <input
              type="search"
              aria-label={"Search " + label}
              placeholder={placeholder || "Search " + label}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          )}
          {toolbar}
        </div>
      )}
      {rows.length ? children(rows, {total: items.length, filtered: filtered.length, query}) : (
        empty ?? <p className="muted">{words.length ? `No ${label} match “${query}”.` : `No ${label}.`}</p>
      )}
      {(showControls || words.length > 0) && filtered.length > 0 && (
        <nav className="pager" aria-label={"Pages of " + label}>
          <span className="pager-count">
            {w.from + 1}–{w.to} of {filtered.length}
            {filtered.length !== items.length ? ` (${items.length} in total)` : ""}
          </span>
          <button type="button" className="secondary small" disabled={w.current <= 1} onClick={() => setPage(1)} aria-label="First page">«</button>
          <button type="button" className="secondary small" disabled={w.current <= 1} onClick={() => setPage(w.current - 1)}>‹ Previous</button>
          <span className="pager-page">Page {w.current} of {w.pages}</span>
          <button type="button" className="secondary small" disabled={w.current >= w.pages} onClick={() => setPage(w.current + 1)}>Next ›</button>
          <button type="button" className="secondary small" disabled={w.current >= w.pages} onClick={() => setPage(w.pages)} aria-label="Last page">»</button>
          <label className="pager-size">
            Rows per page{" "}
            <select value={pageSize} onChange={(e) => setPageSize(Number(e.target.value))}>
              {[...new Set([...PAGE_SIZES, size])].sort((a, b) => a - b).map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
        </nav>
      )}
    </div>
  );
}

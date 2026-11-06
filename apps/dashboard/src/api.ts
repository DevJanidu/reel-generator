export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
export const queryKeys = {
  status: ["status"] as const,
  episodes: ["episodes"] as const,
  runs: ["runs"] as const,
  episode: (id: number | undefined) => ["episode", id] as const,
  activity: ["activity"] as const,
};
export async function api<T = any>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const multipart = body instanceof FormData;
  const res = await fetch("/api" + path, {
    method,
    signal,
    headers: {
      ...(multipart ? {} : { "Content-Type": "application/json" }),
      "X-Odd-Controller":
        sessionStorage.getItem("odd-frame-controller") ||
        localStorage.getItem("odd-frame-controller") ||
        "",
    },
    body:
      body === undefined ? undefined : multipart ? body : JSON.stringify(body),
  });
  const raw = await res.text();
  let data;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    throw new ApiError(
      res.ok
        ? "The server returned an unreadable response."
        : "Request failed. Please retry.",
      res.status,
    );
  }
  if (!res.ok)
    throw new ApiError(
      typeof data?.detail === "string"
        ? data.detail
        : JSON.stringify(data?.detail || "Request failed"),
      res.status,
    );
  return data as T;
}
export type EpisodeSummary = {
  id: number;
  code: string;
  title: string;
  status: string;
  updated: string;
  data: Record<string, any>;
};
export type Run = {
  id: string;
  episode_id: number | null;
  status: string;
  task: string;
  provider: string;
  stage?: string;
  created: string;
  error?: string;
};
export type StationStatus = {
  counts: Record<string, number>;
  jobs: Record<string, any>[];
  skills: Record<string, any>;
  settings: Record<string, any>;
  tools: Record<string, boolean>;
  isolation: Record<string, any>;
  remotion_installed: boolean;
  master_exists: boolean;
};
export const stationApi = {
  status: (signal?: AbortSignal) =>
    api<StationStatus>("/status", "GET", undefined, signal),
  episodes: (signal?: AbortSignal) =>
    api<EpisodeSummary[]>("/episodes", "GET", undefined, signal),
  runs: (signal?: AbortSignal) => api<Run[]>("/runs", "GET", undefined, signal),
  episode: (id: number, signal?: AbortSignal) =>
    api<EpisodeSummary & Record<string, any>>(
      "/episodes/" + id,
      "GET",
      undefined,
      signal,
    ),
};

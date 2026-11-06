import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createRootRoute,
  createRoute,
  createRouter,
  RouterProvider,
  useRouterState,
  useNavigate,
  redirect,
} from "@tanstack/react-router";
import { ActivityMonitor } from "./activity";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/sonner";
import "./studio.css";
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 2000 },
  },
});
export const pagePaths: Record<string, string> = {
  Home: "/",
  "Master Prompt": "/master-prompt",
  Ideas: "/ideas",
  "Script Studio": "/script",
  "Episode Workspace": "/workspace",
  "Google Flow Prompts": "/flow",
  "Asset Manager": "/assets",
  "Edit Studio": "/studio",
  Exports: "/exports",
  Analytics: "/analytics",
  Settings: "/settings",
  "Production Queue": "/queue",
  "AI Activity": "/activity",
  "System Health": "/health",
  "How to Use": "/help",
};
export function useWorkspaceRoute() {
  const location = useRouterState({ select: (s) => s.location });
  const navigate = useNavigate();
  const page =
    Object.entries(pagePaths).find(([, p]) => p === location.pathname)?.[0] ||
    "Home";
  const selected =
    Number((location.search as { episode?: number }).episode) || undefined;
  const setPage = (name: string) => {
    void navigate({
      to: pagePaths[name] || "/",
      search: (prev: Record<string, unknown>) => prev,
    } as any);
  };
  const setSelected = (id: number | undefined) => {
    void navigate({
      to: location.pathname,
      search: { episode: id || undefined },
    } as any);
  };
  const selectEpisode = (id: number, name: string) => {
    void navigate({ to: pagePaths[name], search: { episode: id } } as any);
  };
  return { page, setPage, selected, setSelected, selectEpisode };
}
function studioRouter(Dashboard: React.ComponentType) {
  const root = createRootRoute({
    validateSearch: (s: Record<string, unknown>) => ({
      episode:
        Number.isSafeInteger(Number(s.episode)) && Number(s.episode) > 0
          ? Number(s.episode)
          : undefined,
    }),
    component: () => (
      <TooltipProvider>
        <Dashboard />
        <ActivityMonitor />
        <Toaster theme="dark" richColors />
      </TooltipProvider>
    ),
    notFoundComponent: () => (
      <main>
        <h1>Page not found</h1>
        <a href="/">Return to dashboard</a>
      </main>
    ),
  });
  const children = Object.values(pagePaths).map((path) =>
    createRoute({ getParentRoute: () => root, path, component: () => null }),
  );
  const legacy = createRoute({
    getParentRoute: () => root,
    path: "/episodes/$episodeId/editor",
    beforeLoad: ({ params }) => {
      throw redirect({
        href: "/studio?episode=" + encodeURIComponent(params.episodeId),
      });
    },
  });
  return createRouter({ routeTree: root.addChildren([...children, legacy]) });
}
declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof studioRouter>;
  }
}
export function mountStudio(Dashboard: React.ComponentType) {
  createRoot(document.getElementById("root")!).render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={studioRouter(Dashboard)} />
    </QueryClientProvider>,
  );
}

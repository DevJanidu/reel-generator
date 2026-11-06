import React from 'react';
import {createRoot} from 'react-dom/client';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {createRootRoute,createRoute,createRouter,RouterProvider,Outlet} from '@tanstack/react-router';
import {ActivityMonitor,ProgressHelp} from './activity';
import './studio.css';
export const queryClient=new QueryClient({defaultOptions:{queries:{retry:1,refetchOnWindowFocus:false}}});
function studioRouter(Dashboard:React.ComponentType){
  const root=createRootRoute({component:()=> <><Outlet/><ActivityMonitor/></>});
  const dashboard=createRoute({getParentRoute:()=>root,path:'/',component:()=> <Dashboard/>});
  const editor=createRoute({getParentRoute:()=>root,path:'/episodes/$episodeId/editor',component:()=> <main className="progress-help"><a href="/">← Dashboard</a><h1>The custom Live Editor has been retired</h1><p>Editing now happens in the official Remotion Studio. In the dashboard open <strong>Edit Studio</strong>, choose your reel and click <strong>Open in Remotion Studio</strong>. Your earlier drafts and exports are untouched.</p></main>});
  const help=createRoute({getParentRoute:()=>root,path:'/help',component:ProgressHelp});
  return createRouter({routeTree:root.addChildren([dashboard,editor,help])});
}
declare module '@tanstack/react-router' {interface Register {router:ReturnType<typeof studioRouter>}}
export function mountStudio(Dashboard:React.ComponentType){
  const router=studioRouter(Dashboard);
  createRoot(document.getElementById('root')!).render(<QueryClientProvider client={queryClient}><RouterProvider router={router}/></QueryClientProvider>);
}

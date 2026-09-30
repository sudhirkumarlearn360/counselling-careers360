import type { ComponentType } from "react";
import { Navigate, createBrowserRouter, useParams, type RouteObject } from "react-router-dom";
import { useAuth } from "../api/auth";
import { defaultPath } from "../lib/nav";
import { RequireRole } from "./RequireRole";

function ConsoleIndex() {
  const { user } = useAuth();
  return <Navigate to={user ? defaultPath(user.role) : "/console/login"} replace />;
}

function RedirectToLanding() {
  const { centreSlug } = useParams();
  return <Navigate to={`/c/${centreSlug}?new=1`} replace />;
}

function NotFound() {
  return (
    <main style={{ padding: "2rem 1rem", maxWidth: "32rem", margin: "0 auto" }}>
      <h1>Page not found</h1>
      <p className="muted">Check the link or the code at the centre entrance.</p>
    </main>
  );
}

/** Lazy route: the console and board are code-split so the student pages stay small. */
const lazyNamed = <T extends Record<string, any>>(load: () => Promise<T>, name: keyof T) => ({
  lazy: async () => ({ Component: (await load())[name] as ComponentType }),
});

const deskRoutes: RouteObject[] = [
  { path: "queue", ...lazyNamed(() => import("../features/desk/MyQueue"), "MyQueue") },
  { path: "session", ...lazyNamed(() => import("../features/desk/LiveSession"), "LiveSession") },
  { path: "mine", ...lazyNamed(() => import("../features/desk/Lists"), "MyStudents") },
  { path: "roster", ...lazyNamed(() => import("../features/desk/Lists"), "MyCentres") },
];

function Loading() {
  return <p role="status" style={{ padding: "1rem" }}>Loading…</p>;
}

const appRoutes: RouteObject[] = [
  { path: "/", element: <Navigate to="/console" replace /> },
  { path: "/c/:centreSlug", ...lazyNamed(() => import("../features/student/Landing"), "Landing") },
  { path: "/c/:centreSlug/check-in", element: <RedirectToLanding /> }, // the landing page is the check-in
  { path: "/t/:accessKey", ...lazyNamed(() => import("../features/student/TokenPage"), "TokenPage") },
  { path: "/board/:centreSlug", ...lazyNamed(() => import("../features/board/HallBoard"), "HallBoard") },
  { path: "/console/login", ...lazyNamed(() => import("../features/auth/SignIn"), "SignIn") },
  {
    path: "/console",
    element: <RequireRole />,
    children: [
      {
        ...lazyNamed(() => import("../features/console/Shell"), "Shell"),
        children: [
          { index: true, element: <ConsoleIndex /> },
          { path: "live", ...lazyNamed(() => import("../features/ops/LiveCentres"), "LiveCentres") },
          { path: "centres", ...lazyNamed(() => import("../features/ops/Centres"), "Centres") },
          { path: "counsellors", ...lazyNamed(() => import("../features/ops/Counsellors"), "Counsellors") },
          { path: "students", ...lazyNamed(() => import("../features/ops/AllStudents"), "AllStudents") },
          { path: "insights", ...lazyNamed(() => import("../features/ops/Insights"), "Insights") },
          { path: "hall", ...lazyNamed(() => import("../features/hall/HallQueue"), "HallQueue") },
          { path: "add", ...lazyNamed(() => import("../features/hall/AddStudent"), "AddStudent") },
          { path: "board", ...lazyNamed(() => import("../features/board/ConsoleBoard"), "ConsoleBoard") },
          ...deskRoutes,
          { path: "desk/:counsellorId", children: deskRoutes },
        ],
      },
    ],
  },
  { path: "*", element: <NotFound /> },
];

/** One layout route carries the hydration fallback that lazy routes need on first load. */
export const routes: RouteObject[] = [{ HydrateFallback: Loading, children: appRoutes }];

export const makeRouter = () => createBrowserRouter(routes);

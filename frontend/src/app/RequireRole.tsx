import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../api/auth";
import { canOpen, defaultPath } from "../lib/nav";

/** Signed-in only; a screen outside the role returns to the role's default screen (CQ-3). */
export function RequireRole() {
  const { user, ready } = useAuth();
  const { pathname } = useLocation();
  if (!ready) return <p role="status" style={{ padding: "1rem" }}>Loading…</p>;
  if (!user) return <Navigate to="/console/login" replace />;
  if (!canOpen(user.role, pathname)) return <Navigate to={defaultPath(user.role)} replace />;
  return <Outlet />;
}

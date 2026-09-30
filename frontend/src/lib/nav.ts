/** Navigation is built from the role alone (CQ-3). Mirrors the backend matrix in counselqueue-domain. */
import { phase, type Phase2Feature } from "./phase";

export type Role = "ops_lead" | "reception" | "counsellor";
export interface NavItem {
  key: string;
  label: string;
  path: string;
}

type NavDef = NavItem & { phase2?: Phase2Feature };

const ALL_NAV: Record<Role, NavDef[]> = {
  ops_lead: [
    { key: "live", label: "Live centres", path: "/console/live" },
    { key: "centres", label: "Centres & dates", path: "/console/centres" },
    { key: "counsellors", label: "Counsellors", path: "/console/counsellors" },
    { key: "students", label: "All students", path: "/console/students" },
    { key: "insights", label: "Insights", path: "/console/insights", phase2: "insights" },
    { key: "hall", label: "Hall queue", path: "/console/hall", phase2: "opsHallQueue" },
    { key: "board", label: "Hall board", path: "/console/board", phase2: "hallBoard" },
  ],
  reception: [
    { key: "hall", label: "Hall queue", path: "/console/hall" },
    { key: "add", label: "Add a student", path: "/console/add" },
    { key: "board", label: "Hall board", path: "/console/board", phase2: "hallBoard" },
  ],
  counsellor: [
    { key: "queue", label: "My queue", path: "/console/queue" },
    { key: "session", label: "Live session", path: "/console/session" },
    { key: "mine", label: "My students", path: "/console/mine" },
    { key: "roster", label: "My centres", path: "/console/roster" },
  ],
};

/** The navigation for a role: built from the role alone, minus anything still in Phase 2 (CQ-3). */
export const navFor = (role: Role): NavItem[] =>
  ALL_NAV[role].filter((n) => !n.phase2 || phase[n.phase2]).map(({ key, label, path }) => ({ key, label, path }));

export const defaultPath = (role: Role): string => navFor(role)[0].path;

/** Desk screens an ops lead can reach for one counsellor (CQ-5); never permanent nav items. */
export const DESK_SCREENS = ["queue", "session", "mine"] as const;

export function canOpen(role: Role, pathname: string): boolean {
  if (pathname.startsWith("/console/desk/")) return role === "ops_lead";
  return navFor(role).some((n) => pathname === n.path || pathname.startsWith(`${n.path}/`));
}

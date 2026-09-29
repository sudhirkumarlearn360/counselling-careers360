/** Navigation is built from the role alone (CQ-3). Mirrors the backend matrix in counselqueue-domain. */
export type Role = "ops_lead" | "reception" | "counsellor";
export interface NavItem {
  key: string;
  label: string;
  path: string;
}

export const NAV: Record<Role, NavItem[]> = {
  ops_lead: [
    { key: "live", label: "Live centres", path: "/console/live" },
    { key: "centres", label: "Centres & dates", path: "/console/centres" },
    { key: "counsellors", label: "Counsellors", path: "/console/counsellors" },
    { key: "students", label: "All students", path: "/console/students" },
    { key: "insights", label: "Insights", path: "/console/insights" },
    { key: "hall", label: "Hall queue", path: "/console/hall" },
    { key: "board", label: "Hall board", path: "/console/board" },
  ],
  reception: [
    { key: "hall", label: "Hall queue", path: "/console/hall" },
    { key: "add", label: "Add a student", path: "/console/add" },
    { key: "board", label: "Hall board", path: "/console/board" },
  ],
  counsellor: [
    { key: "queue", label: "My queue", path: "/console/queue" },
    { key: "session", label: "Live session", path: "/console/session" },
    { key: "mine", label: "My students", path: "/console/mine" },
    { key: "roster", label: "My centres", path: "/console/roster" },
  ],
};

export const defaultPath = (role: Role): string => NAV[role][0].path;

/** Desk screens an ops lead can reach for one counsellor (CQ-5); never permanent nav items. */
export const DESK_SCREENS = ["queue", "session", "mine"] as const;

export function canOpen(role: Role, pathname: string): boolean {
  if (pathname.startsWith("/console/desk/")) return role === "ops_lead";
  return NAV[role].some((n) => pathname === n.path || pathname.startsWith(`${n.path}/`));
}

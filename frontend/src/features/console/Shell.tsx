import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../api/auth";
import { useLive } from "../../api/hooks";
import { navFor, type Role } from "../../lib/nav";
import "../../styles/console.css";

const ROLE_LABEL: Record<Role, string> = { ops_lead: "Operations lead", reception: "Front desk", counsellor: "Counsellor" };

function DeskBannerInner({ counsellorId }: { counsellorId: string }) {
  const { data } = useLive();
  const nav = useNavigate();
  const card = data?.flatMap((c) => c.counsellors).find((c) => String(c.counsellor_id) === counsellorId);
  return (
    <div className="ctxbar" role="status" aria-label="Desk context">
      <b>Viewing {card?.name ?? "this counsellor"}'s desk</b>
      <span className="muted">Anything you do here is recorded against that counsellor.</span>
      <button className="btn sm" style={{ marginLeft: "auto" }} onClick={() => nav("/console/live")}>
        Back to live centres
      </button>
    </div>
  );
}

/** Names whose desk an ops lead is viewing (CQ-5); only rendered inside /console/desk/:id/*. */
export function DeskBanner() {
  const { counsellorId } = useParams();
  const { user } = useAuth();
  if (!counsellorId || user?.role !== "ops_lead") return null;
  return <DeskBannerInner counsellorId={counsellorId} />;
}

export function Shell() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  if (!user) return null;
  const items = navFor(user.role);
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">CounselQueue</span>
        <span className="who">
          {user.name} · {ROLE_LABEL[user.role]}
          {user.centre ? ` · ${user.centre.city}` : ""}
          {user.posting ? ` · ${user.posting.desk_label}` : ""}
        </span>
        <button
          className="btn sm"
          onClick={async () => {
            await signOut();
            nav("/console/login", { replace: true }); // back button can't return (replace + cleared session)
          }}
        >
          Sign out
        </button>
      </header>
      <div className="body">
        <nav className="rail" aria-label="Main">
          {items.map((n) => (
            <NavLink key={n.key} to={n.path} aria-current={undefined} className={({ isActive }) => (isActive ? "active" : "")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div>
          <DeskBanner />
          <main className="main"><Outlet /></main>
        </div>
      </div>
    </div>
  );
}

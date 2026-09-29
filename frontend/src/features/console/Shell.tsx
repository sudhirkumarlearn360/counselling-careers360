import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../api/auth";
import { useLive } from "../../api/hooks";
import { initials, prettyDate } from "../../lib/format";
import { navFor, type Role } from "../../lib/nav";
import "../../styles/console.css";

const ROLE_LABEL: Record<Role, string> = { ops_lead: "Super admin", reception: "Front desk", counsellor: "Counsellor" };

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

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(id);
  }, []);
  return <span className="clock">{now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false })}</span>;
}

export function Shell() {
  const { user, signOut } = useAuth();
  const nav = useNavigate();
  if (!user) return null;
  const items = navFor(user.role);
  const where = user.centre ? `${user.centre.city} · ${prettyDate(user.centre.date)}` : "All centres";
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">Counsel<em>Queue</em></span>
        <span className="sep-v" />
        <span className="where">{where}</span>
        <span className="spacer" />
        <Clock />
        <span className="me">
          <span className="avatar" aria-hidden="true">{initials(user.name)}</span>
          <div>
            <b>{user.name}</b>
            <span>{ROLE_LABEL[user.role]}{user.posting ? ` · ${user.posting.desk_label}` : ""}</span>
          </div>
        </span>
        <button
          className="chip-btn"
          onClick={async () => {
            await signOut();
            nav("/console/login", { replace: true }); // back button can't return (replace + cleared session)
          }}
        >
          Sign out
        </button>
      </header>
      <div className="app">
        <nav className="rail" aria-label="Main">
          <div className="who">
            <b>{user.name}</b>
            <span>{ROLE_LABEL[user.role]}{user.centre ? `, ${user.centre.city}` : ""}</span>
          </div>
          {items.map((n) => (
            <NavLink key={n.key} to={n.path} className="navitem">
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div style={{ minWidth: 0 }}>
          <DeskBanner />
          <main className="main"><Outlet /></main>
        </div>
      </div>
    </div>
  );
}

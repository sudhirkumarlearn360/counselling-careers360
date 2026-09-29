import { Link, Navigate, useParams, useSearchParams } from "react-router-dom";
import { usePublicCentre } from "../../api/hooks";
import { prettyDate } from "../../lib/format";
import { StudentShell } from "./StudentShell";
import { savedToken } from "./schema";

export function Landing() {
  const { centreSlug = "" } = useParams();
  const [params] = useSearchParams();
  const key = params.get("new") ? null : savedToken(centreSlug);
  const { data, isLoading, error } = usePublicCentre(centreSlug, !key); // no request when we're about to redirect
  if (key) return <Navigate to={`/t/${key}`} replace />; // back to my live token, not a blank form (CQ-26)

  if (isLoading) return <StudentShell><p role="status">Loading…</p></StudentShell>;
  if (error || !data)
    return (
      <StudentShell>
        <h1>We can't find this centre</h1>
        <p className="muted">Check the code at the entrance, or ask the front desk.</p>
      </StudentShell>
    );
  const { centre, stats } = data;
  return (
    <StudentShell>
      <h1>{centre.city} counselling</h1>
      <p className="muted">
        {centre.venue} · {prettyDate(centre.date)} · {centre.opens_at}–{centre.closes_at}
      </p>

      <section className="stu-card" aria-label="How busy is the hall">
        <div className="stats">
          <div className="stat"><div className="n">{stats.waiting}</div><div className="l">waiting</div></div>
          <div className="stat"><div className="n">{stats.counsellors_on_site}</div><div className="l">counsellors on site</div></div>
          <div className="stat"><div className="n">{stats.avg_wait_label}</div><div className="l">avg wait so far</div></div>
        </div>
      </section>

      {data.open ? (
        <Link to={`/c/${centreSlug}/check-in`} className="btn cta" style={{ width: "100%", textDecoration: "none" }}>
          Check in
        </Link>
      ) : (
        <div className="notice bad" role="status">
          <b>{data.message}</b>
        </div>
      )}

      <section className="stu-card" style={{ marginTop: "1rem" }}>
        <h2>How it works</h2>
        <ol className="steps">
          {data.steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      </section>
      <section className="stu-card warm">
        <h2>What to bring</h2>
        <p style={{ margin: 0 }}>{data.bring.join(" · ")}</p>
        <p className="muted" style={{ margin: "0.25rem 0 0" }}>{data.bring_note}</p>
      </section>
      <section className="stu-card">
        <h2>Need help?</h2>
        <p style={{ margin: 0 }}>
          Front desk {centre.front_desk_phone ? <b>{centre.front_desk_phone}</b> : "at the entrance"} · {centre.venue} · open{" "}
          {centre.opens_at}–{centre.closes_at}
        </p>
      </section>
    </StudentShell>
  );
}

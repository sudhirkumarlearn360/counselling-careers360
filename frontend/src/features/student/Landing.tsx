import { Navigate, useParams, useSearchParams } from "react-router-dom";
import { usePublicCentre } from "../../api/hooks";
import { STREAMS, prettyDate } from "../../lib/format";
import { CheckInFlow } from "./CheckInFlow";
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
    <StudentShell bare>
      <div className="landing">
        <section className="land-left" aria-label="Welcome">
          <div className="land-badge">
            <span className="dot" />
            {data.open ? "Live today" : "Check-in closed"} · {centre.city}
          </div>
          <h1 className="land-h1" style={{ marginTop: 0 }}>
            Your future college <em>starts here.</em>
          </h1>
          <p className="land-sub">
            Free, expert counselling from the Careers360 team. No long lines, no chaos — fill your details and we'll message you when it's your turn.
          </p>
          <div className="land-pills" aria-hidden="true">
            {STREAMS.map((s) => (
              <span className="land-pill" key={s.code}>📚 {s.name}</span>
            ))}
          </div>
          <div className="land-stats" aria-label="How busy is the hall">
            <div className="land-stat"><div className="n">{stats.waiting}</div><div className="l">Waiting now</div></div>
            <div className="land-stat"><div className="n">{stats.counsellors_on_site}</div><div className="l">Counsellors on site</div></div>
            <div className="land-stat"><div className="n">{stats.avg_wait_label}</div><div className="l">Avg wait so far</div></div>
          </div>
          <p className="land-quote">
            “No standing in line. Sit, chill, we WhatsApp you when it's your turn.”
            <br />
            {centre.venue} · {prettyDate(centre.date)} · {centre.opens_at}–{centre.closes_at}
          </p>
        </section>

        <section className="land-right">
          <div className="land-box">
            {data.open ? (
              <div className="land-form">
                <CheckInFlow embedded slug={centreSlug} />
              </div>
            ) : (
              <div className="notice bad" role="status" style={{ marginBottom: "1rem" }}>
                <b>{data.message}</b>
              </div>
            )}

            <section className="stu-card" style={{ marginTop: "1.25rem" }}>
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
            <p className="land-foot">🔒 Your details are private and used only for counselling.</p>
          </div>
        </section>
      </div>
    </StudentShell>
  );
}

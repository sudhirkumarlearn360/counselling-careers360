import { Link } from "react-router-dom";
import { useLive } from "../../api/hooks";
import { minutesLabel, streamName } from "../../lib/format";
import { phase } from "../../lib/phase";

const DUTY: Record<string, { label: string; tone: string }> = {
  on_desk: { label: "On Desk", tone: "ok" },
  on_break: { label: "On Break", tone: "warn" },
  off_duty: { label: "Off Duty", tone: "grey" },
};

export function LiveCentres() {
  const { data, isLoading } = useLive();
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Live centres</h1>
          <p className="lede">What every desk in every city is doing this minute.</p>
        </div>
        {phase.hallBoard && <div className="right"><Link className="btn" to="/console/board">Open hall board</Link></div>}
      </div>
      {isLoading && <p role="status">Loading…</p>}
      {data && data.length === 0 && <div className="card empty"><p style={{ margin: 0 }}>No centre is live. Set one live from Centres &amp; dates.</p></div>}
      {data?.map((c) => (
        <section key={c.id} aria-label={c.city} style={{ marginBottom: 24 }}>
          <div className="centrehead">
            <div>
              <h2>{c.city}</h2>
              <div className="muted" style={{ fontSize: 13.5 }}>{c.venue} · {c.opens_at}–{c.closes_at}</div>
            </div>
            <span className="pill ok dotted">Live</span>
          </div>
          <div className="stats-row">
            <div className="kpi"><div className="n">{c.summary.checked_in}</div><div className="l">Checked in</div><div className="d">{c.summary.self_scan} self-scan, {c.summary.at_desk} at desk</div></div>
            <div className="kpi"><div className="n">{c.summary.waiting}</div><div className="l">Waiting now</div><div className={`d${c.summary.late ? " bad" : ""}`}>{c.summary.late} over {30} min</div></div>
            <div className="kpi"><div className="n">{c.summary.counselled}</div><div className="l">Counselled</div><div className="d">{c.summary.no_shows} no-shows</div></div>
            <div className="kpi"><div className="n">{c.summary.capacity_pct == null ? "—" : `${c.summary.capacity_pct}%`}</div><div className="l">Of day capacity</div><div className="d">Plan was {c.summary.planned}</div></div>
          </div>
          <div className="grid">
            {c.counsellors.map((k) => (
              <article key={k.posting_id} className="card deskcard" style={{ marginBottom: 0 }}>
                <div className="top">
                  <div>
                    <h3>{k.name}</h3>
                    <div className="sub">{k.desk_label} · {k.streams.map(streamName).join(", ")}</div>
                  </div>
                  <span className={`pill ${DUTY[k.duty]?.tone ?? ""}`}>{DUTY[k.duty]?.label ?? k.duty}</span>
                </div>
                <div className="kvrow"><span>Now with</span><b>{k.serving ? `${k.serving.token} · ${k.serving.name}` : "—"}</b></div>
                <div className="kvrow"><span>Queue</span><b>{k.queue_length}{k.queue_late ? ` · ${k.queue_late} late` : ""}</b></div>
                <div className="kvrow"><span>Done today</span><b>{k.counselled_today}</b></div>
                <div className="kvrow"><span>Avg session</span><b>{minutesLabel(k.avg_session_min)}</b></div>
                <Link className="btn sm" style={{ marginTop: 10 }} to={`/console/desk/${k.counsellor_id}/queue`}>Open this desk</Link>
              </article>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}

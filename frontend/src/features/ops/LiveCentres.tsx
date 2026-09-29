import { Link } from "react-router-dom";
import { useLive } from "../../api/hooks";
import { minutesLabel, prettyDate, streamName } from "../../lib/format";

const DUTY: Record<string, string> = { on_desk: "On desk", on_break: "On a break", off_duty: "Off duty" };

export function LiveCentres() {
  const { data, isLoading } = useLive();
  return (
    <>
      <h1>Live centres</h1>
      {isLoading && <p role="status">Loading…</p>}
      {data && data.length === 0 && <div className="card"><p>No centre is live. Set one live from Centres &amp; dates.</p></div>}
      {data?.map((c) => (
        <section key={c.id} className="card" aria-label={c.city}>
          <h2 style={{ marginTop: 0 }}>{c.city} <span className="pill ok">Live</span></h2>
          <p className="muted">{c.venue} · {prettyDate(c.date)} · {c.opens_at}–{c.closes_at}</p>
          <div className="grid">
            {c.counsellors.map((k) => (
              <article key={k.posting_id} className="card" style={{ marginBottom: 0 }}>
                <b>{k.name}</b> <span className="pill">{DUTY[k.duty] ?? k.duty}</span>
                <p className="muted" style={{ margin: "0.25rem 0" }}>{k.desk_label} · {k.streams.map(streamName).join(", ")}</p>
                <p style={{ margin: "0.25rem 0" }}>
                  Serving: <b>{k.serving?.token ?? "—"}</b> · Queue: <b>{k.queue_length}</b> · Avg {minutesLabel(k.avg_session_min)} · {k.counselled_today} done
                </p>
                <Link className="btn sm primary" to={`/console/desk/${k.counsellor_id}/queue`}>Open desk</Link>
              </article>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}

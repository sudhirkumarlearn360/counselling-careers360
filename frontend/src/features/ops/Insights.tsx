import { useState } from "react";
import { useCentres, useInsights } from "../../api/hooks";

function Bars({ rows }: { rows: { label: string; count: number }[] }) {
  const top = Math.max(1, ...rows.map((r) => r.count));
  return (
    <div>
      {rows.map((r) => (
        <div key={r.label} style={{ marginBottom: "0.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}><span>{r.label}</span><b>{r.count}</b></div>
          <div className="bar" aria-hidden="true"><span style={{ width: `${(r.count / top) * 100}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

export function Insights() {
  const [centre, setCentre] = useState("");
  const { data: d, isLoading } = useInsights(centre);
  const centres = useCentres().data ?? [];
  return (
    <>
      <h1>Insights</h1>
      <div className="field" style={{ maxWidth: "22rem" }}>
        <label htmlFor="ins-centre">Centre</label>
        <select id="ins-centre" className="select" value={centre} onChange={(e) => setCentre(e.target.value)}>
          <option value="">All centres</option>
          {centres.map((c) => <option key={c.id} value={c.id}>{c.city} · {c.date}</option>)}
        </select>
      </div>
      {isLoading && <p role="status">Loading…</p>}
      {d && (
        <>
          <div className="stats-row">
            <div className="kpi"><div className="n">{d.headline.counselled_or_queued}</div><div className="l">counselled or queued</div></div>
            <div className="kpi"><div className="n">{d.headline.avg_wait.label}</div><div className="l">avg wait · promise {d.headline.avg_wait.promise_min} min</div></div>
            <div className="kpi"><div className="n">{d.headline.avg_session.label}</div><div className="l">avg session · target {d.headline.avg_session.target_min} min</div></div>
            <div className="kpi"><div className="n">{d.headline.no_show_rate.label}</div><div className="l">no-show rate</div></div>
            <div className="kpi"><div className="n">{d.rating.label}</div><div className="l">average rating</div></div>
            <div className="kpi"><div className="n">{d.follow_ups}</div><div className="l">follow-ups scheduled</div></div>
          </div>
          <div className="grid">
            <section className="card"><h2 style={{ marginTop: 0 }}>Demand by stream</h2><Bars rows={d.demand.map((x) => ({ label: x.name, count: x.count }))} /></section>
            <section className="card"><h2 style={{ marginTop: 0 }}>What students asked for</h2><Bars rows={d.help.map((x) => ({ label: x.option, count: x.count }))} /></section>
            <section className="card"><h2 style={{ marginTop: 0 }}>How clear they were</h2><Bars rows={d.clarity.map((x) => ({ label: x.option, count: x.count }))} /></section>
            <section className="card"><h2 style={{ marginTop: 0 }}>Outcomes</h2><Bars rows={d.outcomes.map((x) => ({ label: x.label, count: x.count }))} /></section>
          </div>
        </>
      )}
    </>
  );
}

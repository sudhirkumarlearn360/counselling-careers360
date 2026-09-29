import { useState } from "react";
import { Link } from "react-router-dom";
import { useDesk, useDeskAction } from "../../api/hooks";
import { errText, useToast } from "../../app/ui";
import { prettyDate, streamName } from "../../lib/format";
import { phase } from "../../lib/phase";
import { StudentDetailsDialog } from "../ops/StudentDetails";
import { useDeskContext } from "./useDeskContext";

const DUTIES = [
  { v: "on_desk", l: "On Desk" },
  { v: "on_break", l: "On Break" },
  { v: "off_duty", l: "Off Duty" },
] as const;

export function MyQueue() {
  const { asCounsellor, base } = useDeskContext();
  const { data, isLoading } = useDesk(asCounsellor);
  const act = useDeskAction(asCounsellor);
  const toast = useToast();
  const [token, setToken] = useState("");
  const [detailsId, setDetailsId] = useState<number | null>(null);

  async function run(path: string, body?: unknown, ok?: string) {
    try {
      const res = await act.mutateAsync({ path, body });
      const warnings = (res.data?.warnings ?? []) as { message: string }[];
      warnings.forEach((w) => toast(w.message));
      if (ok) toast(ok);
      return true;
    } catch (e) {
      toast(errText(e), true);
      return false;
    }
  }

  if (isLoading || !data) return <p role="status">Loading…</p>;
  if (!data.centre)
    return (
      <>
        <h1>My queue</h1>
        <div className="card"><p>{data.message}</p></div>
      </>
    );
  const f = data.figures!;
  const busy = data.current;
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>{data.centre.city} — {prettyDate(data.centre.date)}</h1>
          <p className="lede">{data.centre.venue} · {data.centre.opens_at}–{data.centre.closes_at}. Students are routed to you by stream and by who has the shortest queue.</p>
        </div>
        <div className="right" role="group" aria-label="My status">
          {DUTIES.map((d) => (
            <button
              key={d.v} className={`btn sm${data.duty === d.v ? " primary" : ""}`} aria-pressed={data.duty === d.v}
              onClick={() => run("desk/duty", { duty: d.v }, `You're ${d.l.toLowerCase()}.`)}
            >
              {d.l}
            </button>
          ))}
        </div>
      </div>
      <div className="stats-row">
        <div className="kpi"><div className="n">{f.in_queue}</div><div className="l">In your queue</div><div className="d">{f.waiting_hall} waiting across the hall</div></div>
        <div className="kpi"><div className="n">{f.counselled_today}</div><div className="l">Counselled today</div><div className="d">{f.ready_today} ready to apply</div></div>
        <div className="kpi"><div className="n">{f.avg_session_min ?? "—"}</div><div className="l">Avg session (min)</div><div className="d">Target {f.target_session_min} min</div></div>
        <div className="kpi"><div className="n" style={{ color: f.late ? "var(--rose)" : undefined }}>{f.late}</div><div className="l">Waiting over {f.wait_promise_min} min</div><div className="d">{f.late ? "Needs attention" : "All within promise"}</div></div>
      </div>

      {busy && (
        <div className="card session-now" style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 14rem" }}>
            <div className="muted" style={{ fontSize: 13 }}>Session in progress</div>
            <div style={{ fontSize: 18, fontWeight: 500 }}>{busy.name} <span className="tok muted">· {busy.token}</span></div>
            <div className="muted" style={{ fontSize: 13 }}>{streamName(busy.stream)} · {busy.klass || "—"} · consent {busy.consent === "given" ? "received" : "pending"}</div>
          </div>
          <Link className="btn primary" to={`${base}/session`}>Open session</Link>
        </div>
      )}

      <div className="card">
        <h2>Call a student</h2>
        <div className="toolbar" style={{ marginBottom: 6 }}>
          <button className="btn primary" disabled={!!busy || !data.next_token || act.isPending} onClick={() => run("desk/call-next")}>
            {data.next_token ?? data.queue[0]?.token ? `Call next · ${data.next_token ?? data.queue[0]?.token}` : "No one to call"}
          </button>
          {phase.callFromQueue && (
            <form
              style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}
              onSubmit={async (e) => {
                e.preventDefault();
                if (await run("desk/call-token", { token })) setToken("");
              }}
            >
              <span className="muted">or type a token they read out</span>
              <input className="input" aria-label="Call a token" placeholder="ENG-06" value={token} onChange={(e) => setToken(e.target.value)} style={{ maxWidth: 150 }} />
              <button className="btn" type="submit" disabled={!token.trim()}>Call this token</button>
            </form>
          )}
        </div>
        {busy && <div className="muted" style={{ fontSize: 13 }}>Finish {busy.token} before calling the next student.</div>}
      </div>

      <h2 style={{ fontSize: 15, margin: "18px 0 10px" }}>Queue · {data.queue.length} waiting</h2>
      {data.queue.length === 0 ? (
        <div className="card empty"><p style={{ margin: 0 }}>Your queue is clear — new check-ins land here as students scan in.</p></div>
      ) : (
        <ul className="qlist" aria-label="My queue">
          {data.queue.map((r) => (
            <li key={r.id} className={`qitem${r.next ? " next" : ""}${r.late ? " late" : ""}`}>
              <span className="num">{r.token}</span>
              <div className="body">
                <div className="nm">{r.name}</div>
                <div className="meta">
                  {streamName(r.stream)} · {r.klass || "—"} · waiting {r.waited_min} min{r.late ? " · over promise" : ""} · {r.source === "desk" ? "Added at desk" : "Self check-in"}
                </div>
              </div>
              <div className="act">
                {r.next && <span className="pill ok">Next</span>}
                {r.consent_pending && <span className="pill warn">Consent pending</span>}
                {phase.pullForward && !r.next && <button className="btn sm" onClick={() => run(`desk/students/${r.id}/pull-forward`, undefined, `${r.token} is next.`)}>Pull forward</button>}
                <button className="btn sm" onClick={() => setDetailsId(r.id)}>Details</button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {detailsId != null && <StudentDetailsDialog path={`desk/students/${detailsId}${asCounsellor ? `?as_counsellor=${asCounsellor}` : ""}`} onClose={() => setDetailsId(null)} />}
    </>
  );
}

import { useState } from "react";
import { Link } from "react-router-dom";
import { useDesk, useDeskAction } from "../../api/hooks";
import { errText, useToast } from "../../app/ui";
import { minutesLabel, prettyDate, streamName } from "../../lib/format";
import { useDeskContext } from "./useDeskContext";

const DUTIES = [
  { v: "on_desk", l: "On desk" },
  { v: "on_break", l: "On a break" },
  { v: "off_duty", l: "Off duty" },
] as const;

export function MyQueue() {
  const { asCounsellor, base } = useDeskContext();
  const { data, isLoading } = useDesk(asCounsellor);
  const act = useDeskAction(asCounsellor);
  const toast = useToast();
  const [token, setToken] = useState("");

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
      <h1>My queue</h1>
      <p className="muted">
        {data.centre.city} · {data.centre.venue} · {prettyDate(data.centre.date)} · {data.centre.opens_at}–{data.centre.closes_at} ·{" "}
        <b>{data.desk}</b>
      </p>
      <div className="toolbar" role="group" aria-label="My status">
        {DUTIES.map((d) => (
          <button
            key={d.v} className={`btn sm${data.duty === d.v ? " primary" : ""}`} aria-pressed={data.duty === d.v}
            onClick={() => run("desk/duty", { duty: d.v }, `You're ${d.l.toLowerCase()}.`)}
          >
            {d.l}
          </button>
        ))}
      </div>
      <div className="stats-row">
        <div className="kpi"><div className="n">{f.in_queue}</div><div className="l">in my queue</div></div>
        <div className="kpi"><div className="n">{f.waiting_hall}</div><div className="l">waiting in the hall</div></div>
        <div className="kpi"><div className="n">{f.counselled_today}</div><div className="l">counselled today</div></div>
        <div className="kpi"><div className="n">{minutesLabel(f.avg_session_min)}</div><div className="l">avg session · target {f.target_session_min} min</div></div>
        <div className="kpi"><div className="n" style={{ color: f.late ? "var(--rose)" : undefined }}>{f.late}</div><div className="l">past {f.wait_promise_min} min</div></div>
      </div>

      <div className="card">
        {busy ? (
          <p>
            <b>Finish {busy.token} before calling the next student.</b>{" "}
            <Link to={`${base}/session`}>Open the live session</Link>
          </p>
        ) : (
          <div className="toolbar">
            <button className="btn primary" disabled={!data.next_token || act.isPending} onClick={() => run("desk/call-next")}>
              {data.next_token ? `Call ${data.next_token}` : "No one to call"}
            </button>
            <form
              style={{ display: "flex", gap: "0.5rem" }}
              onSubmit={async (e) => {
                e.preventDefault();
                if (await run("desk/call-token", { token })) setToken("");
              }}
            >
              <input className="input" aria-label="Call a token" placeholder="Token, e.g. PCM-07" value={token} onChange={(e) => setToken(e.target.value)} />
              <button className="btn" type="submit" disabled={!token.trim()}>Call</button>
            </form>
          </div>
        )}
      </div>

      {data.queue.length === 0 ? (
        <div className="card"><p>Your queue is clear — new check-ins land here as students scan in.</p></div>
      ) : (
        <div className="card table-wrap">
          <table className="t">
            <thead><tr><th>Token</th><th>Name</th><th>Stream</th><th>Class</th><th>Waited</th><th>Entry</th><th /></tr></thead>
            <tbody>
              {data.queue.map((r) => (
                <tr key={r.id} className={r.late ? "late" : ""} style={r.next ? { background: "var(--sky)" } : undefined}>
                  <td><b>{r.token}</b> {r.next && <span className="pill ok">Next</span>}</td>
                  <td>{r.name} {r.consent_pending && <span className="pill warn">consent pending</span>}</td>
                  <td>{streamName(r.stream)}</td>
                  <td>{r.klass || "—"}</td>
                  <td>{r.waited_min} min</td>
                  <td>{r.source === "desk" ? "Added at desk" : "Self check-in"}</td>
                  <td>{!r.next && <button className="btn sm" onClick={() => run(`desk/students/${r.id}/pull-forward`, undefined, `${r.token} is next.`)}>Pull forward</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

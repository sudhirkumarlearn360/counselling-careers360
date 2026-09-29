import { Link } from "react-router-dom";
import { useMyList } from "../../api/hooks";
import { StatusPill } from "../../app/ui";
import { prettyDate, streamName } from "../../lib/format";
import { phase } from "../../lib/phase";
import { useDeskContext } from "./useDeskContext";

export function MyStudents() {
  const { asCounsellor } = useDeskContext();
  const { data, isLoading } = useMyList<any>("desk/my-students", asCounsellor);
  return (
    <>
      <h1>My students</h1>
      {isLoading && <p role="status">Loading…</p>}
      {data && data.length === 0 && <div className="card"><p>No students assigned to you yet.</p></div>}
      {data && data.length > 0 && (
        <div className="card table-wrap">
          <table className="t">
            <thead><tr><th>Token</th><th>Name</th><th>Stream</th><th>Centre</th>{phase.studentTiming && <><th>Wait</th><th>Session</th></>}<th>Outcome</th>{phase.studentStatus && <th>Status</th>}</tr></thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.id}>
                  <td><b>{r.token}</b></td><td>{r.name}</td><td>{streamName(r.stream)}</td><td>{r.centre}</td>
                  {phase.studentTiming && <><td>{r.wait_min == null ? "—" : `${r.wait_min} min`}</td><td>{r.session_min == null ? "—" : `${r.session_min} min`}</td></>}
                  <td>{r.outcome ?? "Not set"}</td>{phase.studentStatus && <td><StatusPill status={r.status} /></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export function MyCentres() {
  const { asCounsellor, base } = useDeskContext();
  const { data, isLoading } = useMyList<any>("desk/my-centres", asCounsellor);
  return (
    <>
      <h1>My centres</h1>
      {isLoading && <p role="status">Loading…</p>}
      <div className="grid">
        {data?.map((c: any) => (
          <article key={c.centre.id} className="card">
            <h2 style={{ marginTop: 0 }}>{c.centre.city} {c.live ? <span className="pill ok">Live</span> : c.upcoming ? <span className="pill">Upcoming</span> : null}</h2>
            <p className="muted">{c.centre.venue} · {prettyDate(c.centre.date)} · {c.centre.opens_at}–{c.centre.closes_at}</p>
            <p><b>{c.desk}</b> · {c.students} students so far</p>
            {c.live && <Link className="btn sm primary" to={`${base}/queue`}>Open today's queue</Link>}
          </article>
        ))}
      </div>
    </>
  );
}

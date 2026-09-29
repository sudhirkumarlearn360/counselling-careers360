import { useState } from "react";
import { Link } from "react-router-dom";
import { useMyList } from "../../api/hooks";
import { StatusPill } from "../../app/ui";
import { fmtMobile, prettyDate, streamName } from "../../lib/format";
import { phase } from "../../lib/phase";
import { StudentDetailsDialog } from "../ops/StudentDetails";
import { useDeskContext } from "./useDeskContext";

export function MyStudents() {
  const { asCounsellor } = useDeskContext();
  const { data, isLoading } = useMyList<any>("desk/my-students", asCounsellor);
  const [openId, setOpenId] = useState<number | null>(null);
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>My students</h1>
          <p className="lede">Everyone routed to you at this centre, including the ones still waiting.</p>
        </div>
      </div>
      {isLoading && <p role="status">Loading…</p>}
      {data && data.length === 0 && <div className="card empty"><p style={{ margin: 0 }}>No students assigned to you yet.</p></div>}
      {data && data.length > 0 && (
        <div className="table-wrap">
          <table className="t">
            <thead>
              <tr>
                <th>Token</th><th>Student</th><th>Stream</th>
                {phase.studentTiming && <><th>Wait</th><th>Session</th></>}
                <th>Outcome</th>{phase.studentStatus && <th>Status</th>}<th />
              </tr>
            </thead>
            <tbody>
              {data.map((r: any) => (
                <tr key={r.id}>
                  <td><span className="tok">{r.token}</span></td>
                  <td><b style={{ fontWeight: 500 }}>{r.name}</b><span className="cell-sub">{fmtMobile(r.mobile)}{r.school ? ` · ${r.school}` : ""}</span></td>
                  <td>{streamName(r.stream)}{r.course && <span className="cell-sub">{r.course}</span>}</td>
                  {phase.studentTiming && <><td>{r.wait_min == null ? "—" : `${r.wait_min} min`}</td><td>{r.session_min == null ? "—" : `${r.session_min} min`}</td></>}
                  <td>{r.outcome ?? "—"}</td>{phase.studentStatus && <td><StatusPill status={r.status} /></td>}
                  <td><button className="btn sm" onClick={() => setOpenId(r.id)}>Open</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {openId != null && <StudentDetailsDialog path={`desk/students/${openId}${asCounsellor ? `?as_counsellor=${asCounsellor}` : ""}`} onClose={() => setOpenId(null)} />}
    </>
  );
}

export function MyCentres() {
  const { asCounsellor, base } = useDeskContext();
  const { data, isLoading } = useMyList<any>("desk/my-centres", asCounsellor);
  return (
    <>
      <div className="pagehead">
        <div>
          <h1>My centres</h1>
          <p className="lede">Where you're expected next, and what's already booked in.</p>
        </div>
      </div>
      {isLoading && <p role="status">Loading…</p>}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 22rem), 1fr))" }}>
        {data?.map((c: any) => (
          <article key={c.centre.id} className="card" style={{ marginBottom: 0 }}>
            <div className="centrehead">
              <div>
                <h2>{c.centre.city}</h2>
                <div className="muted" style={{ fontSize: 13.5 }}>{prettyDate(c.centre.date)} · {c.centre.opens_at}–{c.centre.closes_at}</div>
                <div className="muted" style={{ fontSize: 13.5 }}>{c.centre.venue}</div>
              </div>
              {c.live ? <span className="pill ok">Live now</span> : c.upcoming ? <span className="pill">Upcoming</span> : null}
            </div>
            <div className="kvrow"><span>Students so far</span><b>{c.students}</b></div>
            <div className="kvrow"><span>Counsellors on site</span><b>{c.counsellors_on_site}</b></div>
            <div className="kvrow"><span>Your desk</span><b>{c.desk}</b></div>
            {c.live && <Link className="btn primary" style={{ marginTop: 12 }} to={`${base}/queue`}>Open today's queue</Link>}
          </article>
        ))}
      </div>
    </>
  );
}

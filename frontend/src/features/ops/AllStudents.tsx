import { useState } from "react";
import { download } from "../../api/client";
import { useCentres, useCounsellors, useOpsStudents } from "../../api/hooks";
import { StatusPill, errText, useToast } from "../../app/ui";
import { STATUS_LABELS, STREAMS, streamName } from "../../lib/format";

const EMPTY = { q: "", counsellor: "", centre: "", stream: "", status: "" };

export function AllStudents() {
  const [f, setF] = useState(EMPTY);
  const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
  const { data, isLoading } = useOpsStudents(params);
  const counsellors = useCounsellors().data ?? [];
  const centres = useCentres().data ?? [];
  const toast = useToast();

  async function exportCsv() {
    try {
      const { blob, filename } = await download("ops/students/export", params); // respects the filters
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast(errText(e), true);
    }
  }
  const sel = (key: keyof typeof EMPTY, label: string, options: { v: string; l: string }[]) => (
    <select className="select" aria-label={label} value={f[key]} onChange={(e) => setF({ ...f, [key]: e.target.value })} style={{ maxWidth: "14rem" }}>
      <option value="">{label}</option>
      {options.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
    </select>
  );

  return (
    <>
      <h1>All students</h1>
      <div className="toolbar">
        <input className="input" type="search" aria-label="Search students" placeholder="Name, mobile or token" value={f.q} onChange={(e) => setF({ ...f, q: e.target.value })} />
        {sel("counsellor", "Counsellor", counsellors.map((c) => ({ v: String(c.id), l: c.name })))}
        {sel("centre", "Centre", centres.map((c) => ({ v: String(c.id), l: `${c.city} ${c.date}` })))}
        {sel("stream", "Stream", STREAMS.map((s) => ({ v: s.code, l: s.name })))}
        {sel("status", "Status", Object.entries(STATUS_LABELS).map(([v, l]) => ({ v, l })))}
        <button className="btn sm" onClick={() => setF(EMPTY)}>Clear all</button>
        <button className="btn sm primary" onClick={exportCsv}>Export CSV</button>
      </div>
      {data && <p role="status">{data.count} of {data.total} students</p>}
      {isLoading && <p role="status">Loading…</p>}
      {data && data.rows.length === 0 && <div className="card"><p>No students match these filters.</p></div>}
      {data && data.rows.length > 0 && (
        <div className="card table-wrap">
          <table className="t">
            <thead><tr><th>Token</th><th>Name</th><th>Mobile</th><th>School</th><th>Stream</th><th>Course</th><th>Centre</th><th>Date</th><th>Counsellor</th><th>Wait</th><th>Session</th><th>Outcome</th><th>Status</th></tr></thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.id}>
                  <td><b>{r.token}</b></td><td>{r.name}</td><td>{r.mobile}</td><td>{r.school || "—"}</td><td>{streamName(r.stream)}</td>
                  <td>{r.course || "—"}</td><td>{r.centre.city}</td><td>{r.date}</td><td>{r.counsellor}</td>
                  <td>{r.wait_min == null ? "—" : `${r.wait_min} min`}</td><td>{r.session_min == null ? "—" : `${r.session_min} min`}</td>
                  <td>{r.outcome ?? "Not set"}</td><td><StatusPill status={r.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

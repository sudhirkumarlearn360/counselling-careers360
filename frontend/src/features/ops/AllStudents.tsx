import { useMemo, useState } from "react";
import { download } from "../../api/client";
import { useCentres, useCounsellors, useOpsStudents } from "../../api/hooks";
import { StatusPill, errText, useToast } from "../../app/ui";
import { STATUS_LABELS, STREAMS, streamName } from "../../lib/format";
import { phase } from "../../lib/phase";

const EMPTY = { q: "", counsellor: "", city: "", venue: "", stream: "", status: "" };
type Filters = typeof EMPTY;

/** Filters are staged in a draft and only take effect on Apply; Clear resets both (CQ-59). */
export function AllStudents() {
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [applied, setApplied] = useState<Filters>(EMPTY);
  const params = Object.fromEntries(Object.entries(applied).filter(([, v]) => v));
  const { data, isLoading } = useOpsStudents(params);
  const counsellors = useCounsellors().data ?? [];
  const centres = useCentres().data ?? [];
  const toast = useToast();

  const cities = useMemo(() => [...new Set(centres.map((c) => c.city))].sort(), [centres]);
  // Venue options depend on the selected centre: only that centre's venues are offered.
  const venues = useMemo(
    () => (draft.city ? [...new Set(centres.filter((c) => c.city === draft.city).map((c) => c.venue))].sort() : []),
    [centres, draft.city],
  );

  async function exportCsv() {
    try {
      const { blob, filename } = await download("ops/students/export", params); // the applied filters
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
  const set = (key: keyof Filters, value: string) =>
    setDraft((d) => ({ ...d, [key]: value, ...(key === "city" ? { venue: "" } : {}) }));
  const sel = (key: keyof Filters, label: string, options: { v: string; l: string }[], disabled = false) => (
    <select className="select" aria-label={label} value={draft[key]} disabled={disabled} onChange={(e) => set(key, e.target.value)} style={{ maxWidth: "14rem" }}>
      <option value="">{label}</option>
      {options.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
    </select>
  );
  const timing = phase.studentTiming;
  const status = phase.studentStatus;

  return (
    <>
      <h1>All students</h1>
      <form
        className="toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          setApplied(draft);
        }}
      >
        <input className="input" type="search" aria-label="Search students" placeholder="Name, mobile or token" value={draft.q} onChange={(e) => set("q", e.target.value)} />
        {sel("counsellor", "Counsellor", counsellors.map((c) => ({ v: String(c.id), l: c.name })))}
        {sel("city", "Centre", cities.map((c) => ({ v: c, l: c })))}
        {sel("venue", "Venue", venues.map((v) => ({ v, l: v })), !draft.city)}
        {sel("stream", "Stream", STREAMS.map((s) => ({ v: s.code, l: s.name })))}
        {status && sel("status", "Status", Object.entries(STATUS_LABELS).map(([v, l]) => ({ v, l })))}
        <button className="btn sm primary" type="submit">Apply</button>
        <button
          className="btn sm"
          type="button"
          onClick={() => {
            setDraft(EMPTY);
            setApplied(EMPTY);
          }}
        >
          Clear
        </button>
        <button className="btn sm" type="button" onClick={exportCsv}>Export CSV</button>
      </form>
      {data && <p role="status">{data.count} of {data.total} students</p>}
      {isLoading && <p role="status">Loading…</p>}
      {data && data.rows.length === 0 && <div className="card"><p>No students match these filters.</p></div>}
      {data && data.rows.length > 0 && (
        <div className="card table-wrap">
          <table className="t">
            <thead>
              <tr>
                <th>Token</th><th>Name</th><th>Mobile</th><th>School</th><th>Stream</th><th>Course</th><th>Centre</th><th>Date</th><th>Counsellor</th>
                {timing && <><th>Wait</th><th>Session</th></>}
                <th>Outcome</th>{status && <th>Status</th>}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.id}>
                  <td><b>{r.token}</b></td><td>{r.name}</td><td>{r.mobile}</td><td>{r.school || "—"}</td><td>{streamName(r.stream)}</td>
                  <td>{r.course || "—"}</td><td>{r.centre.city}</td><td>{r.date}</td><td>{r.counsellor}</td>
                  {timing && <><td>{r.wait_min == null ? "—" : `${r.wait_min} min`}</td><td>{r.session_min == null ? "—" : `${r.session_min} min`}</td></>}
                  <td>{r.outcome ?? "Not set"}</td>{status && <td><StatusPill status={r.status} /></td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

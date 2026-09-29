import { useMemo, useState } from "react";
import { fmtMobile, prettyDate } from "../../lib/format";
import { download } from "../../api/client";
import { useCentres, useCounsellors, useOpsStudents } from "../../api/hooks";
import { StatusPill, errText, useToast } from "../../app/ui";
import { StudentDetailsDialog } from "./StudentDetails";
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
  const centresData = useCentres().data;
  const centres = useMemo(() => centresData ?? [], [centresData]);
  const toast = useToast();
  const [openId, setOpenId] = useState<number | null>(null);

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
      <div className="pagehead">
        <div>
          <h1>All students</h1>
          <p className="lede">Every student who has ever walked into a counselling centre — searchable, filterable, exportable.</p>
        </div>
        <div className="right"><button className="btn" type="button" onClick={exportCsv}>Export CSV</button></div>
      </div>
      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          setApplied(draft);
        }}
      >
        <div className="filters" style={{ marginBottom: 0 }}>
          <input className="input" type="search" aria-label="Search students" placeholder="Name, number or token" value={draft.q} onChange={(e) => set("q", e.target.value)} />
          {sel("counsellor", "Counsellor", counsellors.map((c) => ({ v: String(c.id), l: c.name })))}
          {sel("city", "Centre", cities.map((c) => ({ v: c, l: c })))}
          {sel("venue", "Venue", venues.map((v) => ({ v, l: v })), !draft.city)}
          {sel("stream", "Stream", STREAMS.map((s) => ({ v: s.code, l: s.name })))}
          {status && sel("status", "Status", Object.entries(STATUS_LABELS).map(([v, l]) => ({ v, l })))}
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn primary" type="submit" style={{ flex: 1 }}>Apply</button>
            <button className="btn" type="button" style={{ flex: 1 }} onClick={() => { setDraft(EMPTY); setApplied(EMPTY); }}>Clear</button>
          </div>
        </div>
      </form>
      {data && <p role="status" className="muted">{data.count} of {data.total} students</p>}
      {isLoading && <p role="status">Loading…</p>}
      {data && data.rows.length === 0 && <div className="card empty"><p style={{ margin: 0 }}>No students match these filters.</p></div>}
      {data && data.rows.length > 0 && (
        <div className="table-wrap">
          <table className="t">
            <thead>
              <tr>
                <th>Token</th><th>Student</th><th>Stream</th><th>Centre</th><th>Counsellor</th>
                {timing && <><th>Wait</th><th>Session</th></>}
                <th>Outcome</th>{status && <th>Status</th>}<th />
              </tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.id}>
                  <td><span className="tok">{r.token}</span></td>
                  <td><b style={{ fontWeight: 500 }}>{r.name}</b><span className="cell-sub">{fmtMobile(r.mobile)}{r.school ? ` · ${r.school}` : ""}</span></td>
                  <td>{streamName(r.stream)}{r.course && <span className="cell-sub">{r.course}</span>}</td>
                  <td>{r.centre.city}<span className="cell-sub">{prettyDate(r.date)}</span></td>
                  <td>{r.counsellor}</td>
                  {timing && <><td>{r.wait_min == null ? "—" : `${r.wait_min} min`}</td><td>{r.session_min == null ? "—" : `${r.session_min} min`}</td></>}
                  <td>{r.outcome ?? "—"}</td>{status && <td><StatusPill status={r.status} /></td>}
                  <td><button className="btn sm" onClick={() => setOpenId(r.id)}>Open</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {openId != null && <StudentDetailsDialog path={`hall/students/${openId}`} onClose={() => setOpenId(null)} />}
    </>
  );
}

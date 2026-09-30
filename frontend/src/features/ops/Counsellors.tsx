import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { useCentres, useCounsellors } from "../../api/hooks";
import { Dialog, Field, errText, useToast } from "../../app/ui";
import { STREAMS, minutesLabel, prettyDate, streamName } from "../../lib/format";

const DUTY: Record<string, { label: string; tone: string }> = {
  on_desk: { label: "On Desk", tone: "ok" },
  on_break: { label: "On Break", tone: "warn" },
  off_duty: { label: "Off Duty", tone: "grey" },
};

export function Counsellors() {
  const { data, isLoading } = useCounsellors();
  const centres = useCentres().data ?? [];
  const qc = useQueryClient();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [f, setF] = useState({ name: "", mobile: "", streams: [] as string[], centre_id: "", desk_label: "" });

  async function save() {
    setError("");
    try {
      const res = await api.post("ops/counsellors", {
        name: f.name, mobile: f.mobile, streams: f.streams,
        centre_id: f.centre_id ? Number(f.centre_id) : undefined, desk_label: f.desk_label || undefined,
      });
      res.warnings?.forEach((w) => toast(w.message));
      toast("Counsellor added.");
      setOpen(false);
      setF({ name: "", mobile: "", streams: [], centre_id: "", desk_label: "" });
      qc.invalidateQueries({ queryKey: ["counsellors"] });
    } catch (e) {
      setError(errText(e));
    }
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Counsellors</h1>
          <p className="lede">Who covers which streams, where they're posted, and how they're performing.</p>
        </div>
        <div className="right"><button className="btn primary" onClick={() => { setError(""); setOpen(true); }}>Add a counsellor</button></div>
      </div>
      {isLoading && <p role="status">Loading…</p>}
      {data && (
        <div className="table-wrap">
          <table className="t">
            <thead><tr><th>Counsellor</th><th>Streams</th><th>Posted to</th><th>Status</th><th>Done</th><th>Avg session</th><th>Ready to apply</th><th /></tr></thead>
            <tbody>
              {data.map((c) => {
                const p = c.postings.find((x) => x.centre_status === "live") ?? c.postings[0];
                return (
                  <tr key={c.id}>
                    <td><b style={{ fontWeight: 600 }}>{c.name}</b><span className="cell-sub">{c.mobile}</span></td>
                    <td style={{ whiteSpace: "normal" }}>{c.streams.map(streamName).join(", ")}</td>
                    <td>{p ? <>{p.city} · {p.desk_label}<span className="cell-sub">{prettyDate(p.date)}</span></> : "—"}</td>
                    <td>{p ? <span className={`pill ${DUTY[p.duty]?.tone ?? ""}`}>{DUTY[p.duty]?.label ?? p.duty}</span> : "—"}</td>
                    <td>{c.stats.done}</td>
                    <td>{minutesLabel(c.stats.avg_session_min)}</td>
                    <td>{c.stats.ready_to_apply}</td>
                    <td>{p?.centre_status === "live" && <Link className="btn sm" to={`/console/desk/${c.id}/queue`}>Open desk</Link>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {open && (
        <Dialog title="Add a counsellor" onClose={() => setOpen(false)}>
          {error && <div className="notice bad" role="alert" style={{ marginBottom: "0.75rem" }}>{error}</div>}
          <Field label="Name" htmlFor="k-name"><input id="k-name" className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></Field>
          <Field label="Mobile" htmlFor="k-mobile"><input id="k-mobile" className="input" inputMode="numeric" value={f.mobile} onChange={(e) => setF({ ...f, mobile: e.target.value })} /></Field>
          <Field label="Streams">
            <div className="chips">
              {STREAMS.map((s) => (
                <button type="button" key={s.code} className="chip" aria-pressed={f.streams.includes(s.code)}
                  onClick={() => setF({ ...f, streams: f.streams.includes(s.code) ? f.streams.filter((x) => x !== s.code) : [...f.streams, s.code] })}>
                  {s.name}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Centre" htmlFor="k-centre">
            <select id="k-centre" className="select" value={f.centre_id} onChange={(e) => setF({ ...f, centre_id: e.target.value })}>
              <option value="">Not posted yet</option>
              {centres.filter((c) => c.status !== "closed").map((c) => <option key={c.id} value={c.id}>{c.city} · {prettyDate(c.date)}</option>)}
            </select>
          </Field>
          <Field label={f.centre_id ? "Desk (required with a centre)" : "Desk"} htmlFor="k-desk"><input id="k-desk" className="input" placeholder="Desk 1" value={f.desk_label} onChange={(e) => setF({ ...f, desk_label: e.target.value })} /></Field>
          <div className="actions"><button className="btn" onClick={() => setOpen(false)}>Cancel</button><button className="btn primary" onClick={save}>Save</button></div>
        </Dialog>
      )}
    </>
  );
}

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../api/client";
import { useCentres, useCounsellors } from "../../api/hooks";
import { Dialog, Field, errText, useToast } from "../../app/ui";
import { STREAMS, prettyDate } from "../../lib/format";

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
      <h1>Counsellors</h1>
      <div className="toolbar"><button className="btn primary" onClick={() => { setError(""); setOpen(true); }}>Add a counsellor</button></div>
      {isLoading && <p role="status">Loading…</p>}
      {data && (
        <div className="card table-wrap">
          <table className="t">
            <thead><tr><th>Name</th><th>Mobile</th><th>Streams</th><th>Posted to</th></tr></thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td><b>{c.name}</b></td><td>{c.mobile}</td>
                  <td style={{ whiteSpace: "normal" }}>{c.streams.join(", ")}</td>
                  <td style={{ whiteSpace: "normal" }}>
                    {c.postings.length === 0 ? "—" : c.postings.map((p) => `${p.city} · ${prettyDate(p.date)} · ${p.desk_label}`).join(" | ")}
                  </td>
                </tr>
              ))}
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
          <Field label="Desk" htmlFor="k-desk"><input id="k-desk" className="input" placeholder="Desk 1" value={f.desk_label} onChange={(e) => setF({ ...f, desk_label: e.target.value })} /></Field>
          <div className="actions"><button className="btn" onClick={() => setOpen(false)}>Cancel</button><button className="btn primary" onClick={save}>Save</button></div>
        </Dialog>
      )}
    </>
  );
}

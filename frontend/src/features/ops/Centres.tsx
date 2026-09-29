import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import { useCentres } from "../../api/hooks";
import type { CentreFull } from "../../api/types";
import { Dialog, Field, errText, useToast } from "../../app/ui";
import { prettyDate, streamName } from "../../lib/format";

interface Draft { city: string; venue: string; date: string; opens_at: string; closes_at: string; expected_students: string; front_desk_phone: string; email: string; password: string }
const blank = (): Draft => ({ city: "", venue: "", date: "", opens_at: "10:00", closes_at: "18:00", expected_students: "", front_desk_phone: "", email: "", password: "" });

export function Centres() {
  const { data, isLoading } = useCentres();
  const qc = useQueryClient();
  const toast = useToast();
  const [editing, setEditing] = useState<{ id?: number; draft: Draft } | null>(null);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<{ centre: CentreFull; kind: "go-live" | "close"; message: string } | null>(null);
  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["centres"] });
    qc.invalidateQueries({ queryKey: ["live"] });
  };

  async function save() {
    if (!editing) return;
    setError("");
    const d = editing.draft;
    const body = { ...d, expected_students: d.expected_students === "" ? undefined : Number(d.expected_students) };
    try {
      const res = editing.id ? await api.patch<CentreFull>(`ops/centres/${editing.id}`, body) : await api.post<CentreFull>("ops/centres", body);
      res.warnings?.forEach((w) => toast(w.message));
      toast("Centre saved.");
      setEditing(null);
      refresh();
    } catch (e) {
      setError(errText(e));
    }
  }
  async function decide(c: CentreFull, kind: "go-live" | "close", confirmed: boolean) {
    try {
      await api.post(`ops/centres/${c.id}/${kind}`, { confirm: confirmed });
      toast(kind === "go-live" ? `${c.city} is live.` : `${c.city} is closed.`);
      setConfirm(null);
      refresh();
    } catch (e) {
      if (e instanceof ApiError && e.code === "needs_confirmation") setConfirm({ centre: c, kind, message: e.message });
      else toast(errText(e), true);
    }
  }

  return (
    <>
      <h1>Centres &amp; dates</h1>
      <div className="toolbar"><button className="btn primary" onClick={() => { setError(""); setEditing({ draft: blank() }); }}>New centre</button></div>
      {isLoading && <p role="status">Loading…</p>}
      <div className="grid">
        {data?.map((c) => (
          <article key={c.id} className="card">
            <h2 style={{ marginTop: 0 }}>{c.city} <span className={`pill ${c.status === "live" ? "ok" : c.status === "closed" ? "bad" : ""}`}>{c.status}</span></h2>
            <p className="muted">{c.venue} · {prettyDate(c.date)} · {c.opens_at}–{c.closes_at}</p>
            <p>{c.counsellor_count} counsellors · {c.expected_students} expected</p>
            <p className="muted" style={{ margin: "0.25rem 0" }}>Front desk login: {c.front_desk_email || "—"}</p>
            <p style={{ margin: "0.25rem 0" }}>
              Covers: {c.covered_streams.map(streamName).join(", ") || "—"}
            </p>
            {c.uncovered_streams.length > 0 && c.status !== "closed" && (
              <p className="notice" style={{ margin: "0.25rem 0" }}>Uncovered: {c.uncovered_streams.map(streamName).join(", ")}</p>
            )}
            <div className="toolbar" style={{ marginTop: "0.75rem" }}>
              {c.status !== "closed" && (
                <button className="btn sm" onClick={() => { setError(""); setEditing({ id: c.id, draft: { city: c.city, venue: c.venue, date: c.date, opens_at: c.opens_at, closes_at: c.closes_at, expected_students: String(c.expected_students), front_desk_phone: c.front_desk_phone ?? "", email: c.front_desk_email ?? "", password: "" } }); }}>Edit</button>
              )}
              {c.status === "planned" && <button className="btn sm primary" onClick={() => decide(c, "go-live", false)}>Set live</button>}
              {c.status === "live" && <button className="btn sm danger" onClick={() => decide(c, "close", false)}>Close centre</button>}
            </div>
          </article>
        ))}
      </div>

      {editing && (
        <Dialog title={editing.id ? "Edit centre" : "New centre"} onClose={() => setEditing(null)}>
          {error && <div className="notice bad" role="alert" style={{ marginBottom: "0.75rem" }}>{error}</div>}
          {(["city", "venue"] as const).map((k) => (
            <Field key={k} label={k === "city" ? "City" : "Venue"} htmlFor={`c-${k}`}>
              <input id={`c-${k}`} className="input" value={editing.draft[k]} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, [k]: e.target.value } })} />
            </Field>
          ))}
          <Field label="Date" htmlFor="c-date"><input id="c-date" className="input" type="date" value={editing.draft.date} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, date: e.target.value } })} /></Field>
          <div className="form-grid">
            <Field label="Opens" htmlFor="c-open"><input id="c-open" className="input" type="time" value={editing.draft.opens_at} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, opens_at: e.target.value } })} /></Field>
            <Field label="Closes" htmlFor="c-close"><input id="c-close" className="input" type="time" value={editing.draft.closes_at} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, closes_at: e.target.value } })} /></Field>
          </div>
          <Field label="Expected students" htmlFor="c-exp"><input id="c-exp" className="input" inputMode="numeric" value={editing.draft.expected_students} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, expected_students: e.target.value } })} /></Field>
          <Field label="Front desk phone" htmlFor="c-phone"><input id="c-phone" className="input" value={editing.draft.front_desk_phone} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, front_desk_phone: e.target.value } })} /></Field>
          <h3 style={{ marginBottom: "0.25rem" }}>Front desk login</h3>
          <Field label="Email" htmlFor="c-email"><input id="c-email" className="input" type="email" autoComplete="off" value={editing.draft.email} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, email: e.target.value } })} /></Field>
          <Field label="Password" htmlFor="c-password" hint={editing.id ? "Leave blank to keep the current password." : "At least 8 characters."}>
            <input id="c-password" className="input" type="password" autoComplete="new-password" value={editing.draft.password} onChange={(e) => setEditing({ ...editing, draft: { ...editing.draft, password: e.target.value } })} />
          </Field>
          <div className="actions">
            <button className="btn" onClick={() => setEditing(null)}>Cancel</button>
            <button className="btn primary" onClick={save}>Save centre</button>
          </div>
        </Dialog>
      )}

      {confirm && (
        <Dialog title={confirm.kind === "go-live" ? "Set live?" : "Close this centre?"} onClose={() => setConfirm(null)}>
          <div className="notice">{confirm.message}</div>
          <div className="actions">
            <button className="btn" onClick={() => setConfirm(null)}>Cancel</button>
            <button className={`btn ${confirm.kind === "close" ? "danger" : "primary"}`} onClick={() => decide(confirm.centre, confirm.kind, true)}>
              {confirm.kind === "go-live" ? "Go live anyway" : "Close centre"}
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}

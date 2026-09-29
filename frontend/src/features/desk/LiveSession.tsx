import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useDesk, useDeskAction } from "../../api/hooks";
import type { StudentRecord } from "../../api/types";
import { Field, errText, useToast } from "../../app/ui";
import { ApiError } from "../../api/client";
import { CLARITY, CLASSES, OUTCOMES, STREAMS, elapsedLabel, streamName } from "../../lib/format";
import { phase } from "../../lib/phase";
import { useDeskContext } from "./useDeskContext";

const NA = "Not answered";
const show = (v: string | null | undefined) => (v && v.trim() ? v : NA);

function Intake({ s }: { s: StudentRecord }) {
  return (
    <section className="card" aria-label="What the student told us">
      <h2>What {s.name} told us</h2>
      <dl className="stu-meta" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(11rem,1fr))", gap: "0.5rem 1rem" }}>
        <div><dt className="muted">Course or career</dt><dd style={{ margin: 0 }}>{show(s.course)}</dd></div>
        <div><dt className="muted">School</dt><dd style={{ margin: 0 }}>{show(s.school)}</dd></div>
        <div><dt className="muted">Parent's contact</dt><dd style={{ margin: 0 }}>{show(s.parent_mobile)}</dd></div>
        <div><dt className="muted">Clarity</dt><dd style={{ margin: 0 }}>{show(s.clarity)}</dd></div>
        <div><dt className="muted">Entrance exams</dt><dd style={{ margin: 0 }}>{s.exams.length ? s.exams.join(", ") : NA}</dd></div>
        <div><dt className="muted">Help with</dt><dd style={{ margin: 0 }}>{s.help.length ? s.help.join(", ") : NA}</dd></div>
      </dl>
    </section>
  );
}

function Timer({ s }: { s: StudentRecord }) {
  const t = s.timer;
  const [extra, setExtra] = useState(0);
  useEffect(() => {
    setExtra(0);
    if (!t) return;
    const id = setInterval(() => setExtra((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, [t?.elapsed_seconds, t]);
  if (!t) return null; // no timer before the session starts
  const elapsed = t.elapsed_seconds + extra;
  const over = elapsed > t.target_min * 60;
  return (
    <div aria-live="off" style={{ marginBottom: 10 }}>
      <div className={`timer${over ? " over" : ""}`}>{elapsedLabel(elapsed)}</div>
      <div className="muted">
        {over ? `over the ${t.target_min} min target · ${t.waiting} still waiting for you` : `target ${t.target_min} min`}
      </div>
    </div>
  );
}

export function LiveSession() {
  const { asCounsellor, base } = useDeskContext();
  const { data, isLoading } = useDesk(asCounsellor);
  const act = useDeskAction(asCounsellor);
  const toast = useToast();
  const s = data?.current ?? null;
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [note, setNote] = useState("");

  useEffect(() => {
    if (!s) return setEdit({});
    setEdit({
      name: s.name, school: s.school, mobile: s.mobile, parent_mobile: s.parent_mobile, email: s.email, stream: s.stream,
      klass: s.klass, course: s.course, clarity: s.clarity, home_city: s.home_city, target_exam: s.target_exam,
      budget: s.budget, colleges_discussed: s.colleges_discussed, accompanied_by: s.accompanied_by,
      outcome: s.outcome ?? "", follow_up_on: s.follow_up_on ?? "",
    });
    setErrors({});
  }, [s?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function run(path: string, body?: unknown, ok?: string, method?: "POST" | "PATCH") {
    try {
      const res = await act.mutateAsync({ path, body, method });
      if (ok) toast(res.message ?? ok);
      return res;
    } catch (e) {
      if (e instanceof ApiError && e.code === "invalid") setErrors(e.fields);
      toast(errText(e), true);
      return null;
    }
  }

  if (isLoading || !data) return <p role="status">Loading…</p>;
  if (!s)
    return (
      <>
        <h1>Live session</h1>
        <div className="card"><p>No session in progress. <Link to={`${base}/queue`}>Go to my queue</Link></p></div>
      </>
    );

  const pending = s.consent === "pending";
  const base_ = `desk/students/${s.id}`;
  const setF = (k: string, v: string) => setEdit((x) => ({ ...x, [k]: v }));
  const inp = (k: string, label: string, type = "text") => (
    <Field label={label} htmlFor={`e-${k}`} error={errors[k]}>
      <input id={`e-${k}`} className="input" type={type} value={edit[k] ?? ""} onChange={(e) => setF(k, e.target.value)} />
    </Field>
  );
  const save = async () => {
    const payload: Record<string, unknown> = { ...edit, outcome: edit.outcome || null, follow_up_on: edit.follow_up_on || null };
    setErrors({});
    await run(base_, payload, "Saved.", "PATCH");
  };

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>{s.name}</h1>
          <p className="lede">Token {s.token} · {streamName(s.stream)}</p>
        </div>
        <div className="right"><span className={`pill ${s.status === "in_session" ? "ok" : "warn"}`}>{s.status === "in_session" ? "In session" : "Called"}</span></div>
      </div>
      <div className="two-col">
        <div>
          <div className="card">
            <h2>Session</h2>
            <Timer s={s} />
            {pending && (
              <div className="notice" style={{ margin: "10px 0" }} role="status">
                <b>Consent is pending</b>
                Consent is pending — record verbal consent or resend the request.
                <div className="toolbar" style={{ marginTop: "0.5rem", marginBottom: 0 }}>
                  <button className="btn sm primary" onClick={() => run(`${base_}/consent`, undefined, "Consent recorded.")}>Record verbal consent</button>
                  <button className="btn sm" onClick={() => run(`${base_}/consent-request`, undefined, "Request sent.")}>Resend WhatsApp request</button>
                </div>
              </div>
            )}
            <div className="toolbar" style={{ marginBottom: 0 }}>
              {s.status === "called" && (
                <>
                  <button className="btn primary" disabled={pending || act.isPending} onClick={() => run(`${base_}/start`)}>Start session</button>
                  <button className="btn" onClick={() => run(`${base_}/missed`, undefined, "Marked as not turned up.")}>Not turned up</button>
                </>
              )}
              {s.status === "in_session" && (
                <button className="btn primary" disabled={act.isPending} onClick={() => run(`${base_}/complete`, undefined, "Done.")}>Mark done</button>
              )}
            </div>
          </div>

          <section className="card" aria-label="Notes">
            <h2>Counselling notes</h2>
            {s.notes.length === 0 && <p className="muted">Nothing recorded yet.</p>}
            {s.notes.map((n) => (
              <div className="note" key={n.id}>
                {n.text}
                <div className="by">{n.author} · {new Date(n.at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</div>
              </div>
            ))}
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (await run(`${base_}/notes`, { text: note }, "Note added.")) setNote("");
              }}
            >
              <Field label="Add a note" htmlFor="note">
                <textarea id="note" className="textarea" placeholder="What they asked, what you advised, anything the next person needs to know." value={note} onChange={(e) => setNote(e.target.value)} />
              </Field>
              <button className="btn primary" type="submit">Add note</button>
            </form>
          </section>
        </div>

        <div>
          {phase.intakeSummary && <Intake s={s} />}
          <section className="card" aria-label="Edit details">
            <h2>Student details</h2>
            <div className="form-grid">
              {inp("name", "Name")}{inp("school", "School")}{inp("mobile", "Mobile")}{inp("email", "Email")}
              {inp("parent_mobile", "Parent's contact")}{inp("course", "Course or career targeted")}
              <Field label="Stream" htmlFor="e-stream" error={errors.stream}>
                <select id="e-stream" className="select" value={edit.stream ?? ""} onChange={(e) => setF("stream", e.target.value)}>
                  {STREAMS.map((x) => <option key={x.code} value={x.code}>{x.name}</option>)}
                </select>
              </Field>
              <Field label="Class" htmlFor="e-klass">
                <select id="e-klass" className="select" value={edit.klass ?? ""} onChange={(e) => setF("klass", e.target.value)}>
                  <option value="">Select</option>{CLASSES.map((c) => <option key={c}>{c}</option>)}
                </select>
              </Field>
              <Field label="How clear about the choice" htmlFor="e-clarity">
                <select id="e-clarity" className="select" value={edit.clarity ?? ""} onChange={(e) => setF("clarity", e.target.value)}>
                  <option value="">Select</option>{CLARITY.map((c) => <option key={c}>{c}</option>)}
                </select>
              </Field>
              {inp("home_city", "Home city")}{inp("target_exam", "Target exam")}{inp("budget", "Budget")}{inp("accompanied_by", "Who accompanied them")}
            </div>
            <Field label="Colleges discussed" htmlFor="e-colleges">
              <textarea id="e-colleges" className="textarea" value={edit.colleges_discussed ?? ""} onChange={(e) => setF("colleges_discussed", e.target.value)} />
            </Field>
            <div className="form-grid">
              <Field label="Where the conversation landed" htmlFor="e-outcome" error={errors.outcome}>
                <select id="e-outcome" className="select" value={edit.outcome ?? ""} onChange={(e) => setF("outcome", e.target.value)}>
                  <option value="">Not set</option>{OUTCOMES.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
                </select>
              </Field>
              {inp("follow_up_on", "Follow-up date", "date")}
            </div>
            <button className="btn primary" onClick={save}>Save details</button>
          </section>
        </div>
      </div>
    </>
  );
}

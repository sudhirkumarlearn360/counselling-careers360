import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { useHall } from "../../api/hooks";
import { Field, errText, useToast } from "../../app/ui";
import { CLARITY, CLASSES, EXAMS, HELP, STREAMS } from "../../lib/format";
import { toggleExam } from "../student/schema";
import { useHallCentre } from "./useHallCentre";

const EMPTY = {
  name: "", mobile: "", parent_mobile: "", email: "", school: "", stream: "PCM", klass: "Class 11",
  course: "", exams: [] as string[], clarity: "Very clear", help: [] as string[],
};

export function AddStudent() {
  const { centreId, picker } = useHallCentre();
  const load = useHall(centreId, "", null).data;
  const [f, setF] = useState(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [dup, setDup] = useState<{ message: string; id: number } | null>(null);
  const [done, setDone] = useState("");
  const qc = useQueryClient();
  const toast = useToast();
  const set = <K extends keyof typeof EMPTY>(k: K, v: (typeof EMPTY)[K]) => setF((x) => ({ ...x, [k]: v }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErrors({});
    setDup(null);
    try {
      const res = await api.post<{ token: string }>(`hall/centres/${centreId}/check-in`, f);
      setDone(res.message ?? `Token ${res.data.token} issued.`);
      toast(res.message ?? "Token issued.", false, true);
      setF(EMPTY); // the form clears fully, ready for the next student
      qc.invalidateQueries({ queryKey: ["hall"] });
    } catch (err) {
      if (err instanceof ApiError && err.code === "duplicate_token")
        setDup({ message: err.message, id: Number(err.data.student_id) });
      else if (err instanceof ApiError && err.code === "invalid") setErrors(err.fields); // all together; values kept
      else toast(errText(err), true);
    }
  }

  return (
    <>
      <div className="pagehead">
        <div>
          <h1>Add a student</h1>
          <p className="lede">Same questions the student answers on their phone. For anyone without data, without a phone, or who'd rather you did it.</p>
        </div>
      </div>
      {picker}
      {done && <div className="notice ok" role="status" style={{ marginBottom: "1rem" }}>{done} <Link to="/console/hall">Back to the hall queue</Link></div>}
      {dup && (
        <div className="notice bad" role="alert" style={{ marginBottom: "1rem" }}>
          <b>{dup.message}</b>
          <Link to={`/console/hall?student=${dup.id}`}>Open the existing token in the hall queue</Link>
        </div>
      )}
      <div className="two-col">
        <form className="card" onSubmit={submit} noValidate>
          <h2>Who they are</h2>
          <div className="form-grid">
            <Field label="Student name" htmlFor="a-name" error={errors.name}>
              <input id="a-name" className="input" placeholder="Full name" value={f.name} onChange={(e) => set("name", e.target.value)} />
            </Field>
            <Field label="School" htmlFor="a-school">
              <input id="a-school" className="input" placeholder="School name and city" value={f.school} onChange={(e) => set("school", e.target.value)} />
            </Field>
            <Field label="Mobile" htmlFor="a-mobile" error={errors.mobile}>
              <input id="a-mobile" className="input" inputMode="numeric" placeholder="10 digits" value={f.mobile} onChange={(e) => set("mobile", e.target.value)} />
            </Field>
            <Field label="Parent's contact" htmlFor="a-parent" error={errors.parent_mobile}>
              <input id="a-parent" className="input" inputMode="numeric" placeholder="Optional" value={f.parent_mobile} onChange={(e) => set("parent_mobile", e.target.value)} />
            </Field>
            <Field label="Email" htmlFor="a-email" error={errors.email}>
              <input id="a-email" className="input" placeholder="you@example.com" value={f.email} onChange={(e) => set("email", e.target.value)} />
            </Field>
            <Field label="Class" htmlFor="a-klass">
              <select id="a-klass" className="select" value={f.klass} onChange={(e) => set("klass", e.target.value)}>
                {CLASSES.map((c) => <option key={c}>{c}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Stream" htmlFor="a-stream" error={errors.stream} hint="Decides which desk they're sent to.">
            <select id="a-stream" className="select" value={f.stream} onChange={(e) => set("stream", e.target.value)}>
              {STREAMS.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
            </select>
          </Field>
          <hr style={{ border: 0, borderTop: "1px solid var(--line)", margin: "14px 0" }} />
          <h2>What they want from the session</h2>
          <Field label="Course or career they're targeting" htmlFor="a-course" error={errors.course}>
            <input id="a-course" className="input" placeholder="B.Tech CSE, MBBS, still deciding…" value={f.course} onChange={(e) => set("course", e.target.value)} />
          </Field>
          <Field label="Entrance exams they're preparing for or considering">
            <div className="checks">
              {EXAMS.map((x) => (
                <label key={x}>
                  <input type="checkbox" checked={f.exams.includes(x)} onChange={() => set("exams", toggleExam(f.exams, x))} /> {x}
                </label>
              ))}
            </div>
          </Field>
          <Field label="How clear are they about the college or course choice?" htmlFor="a-clarity">
            <select id="a-clarity" className="select" value={f.clarity} onChange={(e) => set("clarity", e.target.value)}>
              {CLARITY.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
          <Field label="What would they like help with?" error={errors.help}>
            <div className="checks">
              {HELP.map((h) => (
                <label key={h}>
                  <input type="checkbox" checked={f.help.includes(h)} onChange={() => set("help", f.help.includes(h) ? f.help.filter((x) => x !== h) : [...f.help, h])} /> {h}
                </label>
              ))}
            </div>
          </Field>
          <button className="btn primary" type="submit" disabled={centreId == null}>Issue token</button>
        </form>

        <aside className="card">
          <h2>Load right now</h2>
          {load?.tabs.filter((t) => t.counsellor_id != null).map((t) => (
            <div className="kvrow" key={t.key}>
              <span>{t.label}</span>
              <b>{t.duty === "on_break" ? "On Break" : t.duty === "off_duty" ? "Off Duty" : `${t.count} waiting`}</b>
            </div>
          ))}
          <p className="muted" style={{ fontSize: 12.5 }}>New tokens go to the matching stream desk with the shortest queue. You can move anyone from the hall queue afterwards.</p>
        </aside>
      </div>
    </>
  );
}

import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../../api/client";
import { Field, errText, useToast } from "../../app/ui";
import { CLARITY, CLASSES, EXAMS, HELP, STREAMS } from "../../lib/format";
import { toggleExam } from "../student/schema";
import { useHallCentre } from "./useHallCentre";

const EMPTY = {
  name: "", mobile: "", parent_mobile: "", email: "", school: "", stream: "PCM", klass: "",
  course: "", exams: [] as string[], clarity: "", help: [] as string[],
};

export function AddStudent() {
  const { centreId, picker } = useHallCentre();
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
      toast(res.message ?? "Token issued.");
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
      <h1>Add a student</h1>
      {picker}
      {done && <div className="notice ok" role="status" style={{ marginBottom: "1rem" }}>{done} <Link to="/console/hall">Back to the hall queue</Link></div>}
      {dup && (
        <div className="notice bad" role="alert" style={{ marginBottom: "1rem" }}>
          <b>{dup.message}</b>
          <Link to={`/console/hall?student=${dup.id}`}>Open the existing token in the hall queue</Link>
        </div>
      )}
      <form className="card" onSubmit={submit} noValidate>
        <h2>Who they are</h2>
        <div className="form-grid">
          <Field label="Student name" htmlFor="a-name" error={errors.name}>
            <input id="a-name" className="input" value={f.name} onChange={(e) => set("name", e.target.value)} />
          </Field>
          <Field label="Mobile" htmlFor="a-mobile" error={errors.mobile}>
            <input id="a-mobile" className="input" inputMode="numeric" value={f.mobile} onChange={(e) => set("mobile", e.target.value)} />
          </Field>
          <Field label="Parent's number" htmlFor="a-parent" error={errors.parent_mobile}>
            <input id="a-parent" className="input" inputMode="numeric" value={f.parent_mobile} onChange={(e) => set("parent_mobile", e.target.value)} />
          </Field>
          <Field label="Email" htmlFor="a-email" error={errors.email}>
            <input id="a-email" className="input" value={f.email} onChange={(e) => set("email", e.target.value)} />
          </Field>
          <Field label="School" htmlFor="a-school">
            <input id="a-school" className="input" value={f.school} onChange={(e) => set("school", e.target.value)} />
          </Field>
          <Field label="Stream" htmlFor="a-stream" error={errors.stream} hint="The stream decides which counsellor they are sent to.">
            <select id="a-stream" className="select" value={f.stream} onChange={(e) => set("stream", e.target.value)}>
              {STREAMS.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
            </select>
          </Field>
          <Field label="Class" htmlFor="a-klass">
            <select id="a-klass" className="select" value={f.klass} onChange={(e) => set("klass", e.target.value)}>
              <option value="">Select</option>
              {CLASSES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Field>
        </div>
        <h2>What they want from the session</h2>
        <Field label="Course or career" htmlFor="a-course" error={errors.course}>
          <input id="a-course" className="input" value={f.course} onChange={(e) => set("course", e.target.value)} />
        </Field>
        <Field label="Entrance exams">
          <div className="chips">
            {EXAMS.map((x) => (
              <button type="button" key={x} className="chip" aria-pressed={f.exams.includes(x)} onClick={() => set("exams", toggleExam(f.exams, x))}>{x}</button>
            ))}
          </div>
        </Field>
        <Field label="Clarity" htmlFor="a-clarity">
          <select id="a-clarity" className="select" value={f.clarity} onChange={(e) => set("clarity", e.target.value)}>
            <option value="">Select</option>
            {CLARITY.map((c) => <option key={c}>{c}</option>)}
          </select>
        </Field>
        <Field label="Help with" error={errors.help}>
          <div className="chips">
            {HELP.map((h) => (
              <button type="button" key={h} className="chip" aria-pressed={f.help.includes(h)} onClick={() => set("help", f.help.includes(h) ? f.help.filter((x) => x !== h) : [...f.help, h])}>{h}</button>
            ))}
          </div>
        </Field>
        <button className="btn primary" type="submit" disabled={centreId == null}>Issue token</button>
      </form>
    </>
  );
}

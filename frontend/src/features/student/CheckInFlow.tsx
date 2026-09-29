import { useEffect, useState } from "react";
import { useForm, type FieldPath } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import type { ZodTypeAny } from "zod";
import { api, ApiError } from "../../api/client";
import { usePublicCentre } from "../../api/hooks";
import { Field } from "../../app/ui";
import { CLARITY, CLASSES, EXAMS, HELP, STREAMS } from "../../lib/format";
import { normaliseMobile } from "../../lib/mobile";
import {
  DETAILS_FIELDS, EMPTY_FORM, GOALS_FIELDS, detailsSchema, goalsSchema, saveToken, toggleExam, type CheckInForm,
} from "./schema";
import { StudentShell } from "./StudentShell";

const STEPS = ["Details", "Goals", "Verify", "Token"] as const;

function Progress({ step }: { step: number }) {
  return (
    <ol className="progress" aria-label="Progress">
      {STEPS.map((label, i) => (
        <li key={label} aria-current={i + 1 === step ? "step" : undefined} className={i + 1 < step ? "done" : ""}>
          {i + 1}. {label}
        </li>
      ))}
    </ol>
  );
}

export function CheckInFlow() {
  const { centreSlug = "" } = useParams();
  const nav = useNavigate();
  const { data: centre } = usePublicCentre(centreSlug);
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const form = useForm<CheckInForm>({ defaultValues: EMPTY_FORM });
  const { register, watch, setValue, formState } = form;
  const errors = formState.errors;
  const values = watch();

  // OTP step state
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [otpError, setOtpError] = useState("");
  const [notice, setNotice] = useState("");
  const [resendIn, setResendIn] = useState(0);
  const [duplicate, setDuplicate] = useState<{ message: string; key: string } | null>(null);

  useEffect(() => {
    if (resendIn <= 0) return;
    const t = setTimeout(() => setResendIn((n) => n - 1), 1000);
    return () => clearTimeout(t);
  }, [resendIn]);

  /** Validate one step with Zod; every failing field is reported together, values are kept. */
  function validate(schema: ZodTypeAny, fields: readonly string[]): boolean {
    form.clearErrors(fields as FieldPath<CheckInForm>[]);
    const res = schema.safeParse(form.getValues());
    if (res.success) return true;
    res.error.issues.forEach((i) => {
      const name = String(i.path[0]) as FieldPath<CheckInForm>;
      if (!form.getFieldState(name).error) form.setError(name, { message: i.message });
    });
    return false;
  }

  async function sendCode() {
    setBusy(true);
    setOtpError("");
    setNotice("");
    try {
      const res = await api.post<{ resend_after_sec: number }>(
        `public/centres/${centreSlug}/otp/send`,
        { mobile: values.mobile },
        { auth: false },
      );
      setResendIn(res.data.resend_after_sec);
      setStep(3);
    } catch (e) {
      if (e instanceof ApiError && e.code === "otp_resend_wait") {
        setResendIn(Number(e.data.retry_after ?? 30));
        setNotice("A code was already sent to your WhatsApp — enter it, or wait to resend.");
        setStep(3);
      } else setOtpError(e instanceof ApiError ? e.message : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function goals(e: React.FormEvent) {
    e.preventDefault();
    if (validate(goalsSchema, GOALS_FIELDS)) await sendCode();
  }

  /** Verify the code, then issue the token. */
  async function finish(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setOtpError("");
    setDuplicate(null);
    try {
      const mobile = normaliseMobile(values.mobile);
      const v = await api.post<{ verification_id: string }>(
        `public/centres/${centreSlug}/otp/verify`,
        { mobile, code },
        { auth: false },
      );
      const res = await api.post<{ access_key: string }>(
        `public/centres/${centreSlug}/check-in`,
        { ...values, mobile, verification_id: v.data.verification_id },
        { auth: false },
      );
      saveToken(centreSlug, res.data.access_key);
      nav(`/t/${res.data.access_key}`, { replace: true });
    } catch (err) {
      if (!(err instanceof ApiError)) return setOtpError("Something went wrong. Try again.");
      if (err.code === "duplicate_token") {
        const key = String(err.data.access_key ?? "");
        if (key) saveToken(centreSlug, key);
        setDuplicate({ message: err.message, key });
      } else if (err.code === "invalid") {
        // Server-side field errors: show them all and go back to the first step that has one.
        const fields = err.fields;
        Object.entries(fields).forEach(([name, message]) => form.setError(name as FieldPath<CheckInForm>, { message }));
        const inDetails = Object.keys(fields).some((f) => (DETAILS_FIELDS as readonly string[]).includes(f));
        setStep(inDetails ? 1 : 2);
      } else setOtpError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (centre && !centre.open)
    return (
      <StudentShell>
        <div className="notice bad"><b>{centre.message}</b></div>
        <p><Link to={`/c/${centreSlug}?new=1`}>Back</Link></p>
      </StudentShell>
    );

  const err = (name: FieldPath<CheckInForm>) => (errors as Record<string, { message?: string }>)[name]?.message;
  return (
    <StudentShell>
      <Progress step={step} />

      {step === 1 && (
        <form
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            if (validate(detailsSchema, DETAILS_FIELDS)) setStep(2);
          }}
        >
          <h1>Your details</h1>
          <p className="muted">One short screen — it takes a minute.</p>
          <Field label="Your name" htmlFor="name" error={err("name")}>
            <input id="name" className="input" autoComplete="name" aria-invalid={!!err("name")} {...register("name")} />
          </Field>
          <Field label="School" htmlFor="school" error={err("school")}>
            <input id="school" className="input" aria-invalid={!!err("school")} {...register("school")} />
          </Field>
          <Field label="Your mobile number" htmlFor="mobile" hint="We'll send your token and turn alert on WhatsApp." error={err("mobile")}>
            <input id="mobile" className="input" type="tel" inputMode="numeric" autoComplete="tel" aria-invalid={!!err("mobile")} {...register("mobile")} />
          </Field>
          <Field label="Parent's number (optional)" htmlFor="parent_mobile" error={err("parent_mobile")}>
            <input id="parent_mobile" className="input" type="tel" inputMode="numeric" aria-invalid={!!err("parent_mobile")} {...register("parent_mobile")} />
          </Field>
          <Field label="Email (optional)" htmlFor="email" error={err("email")}>
            <input id="email" className="input" type="email" inputMode="email" autoComplete="email" aria-invalid={!!err("email")} {...register("email")} />
          </Field>
          <Field label="Your stream" hint="The stream you pick decides which counsellor you're sent to." error={err("stream")}>
            <div className="chips" role="group" aria-label="Stream">
              {STREAMS.map((s) => (
                <button
                  type="button"
                  key={s.code}
                  className="chip"
                  aria-pressed={values.stream === s.code}
                  onClick={() => setValue("stream", s.code as never, { shouldValidate: false })}
                >
                  {s.name}
                </button>
              ))}
            </div>
          </Field>
          <Field label="Class" htmlFor="klass">
            <select id="klass" className="select" {...register("klass")}>
              <option value="">Select</option>
              {CLASSES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
          <div className="row-actions">
            <button className="btn cta" type="submit">Continue</button>
          </div>
        </form>
      )}

      {step === 2 && (
        <form noValidate onSubmit={goals}>
          <h1>What do you need help with?</h1>
          <p className="muted">So your counsellor starts with your question, not your name.</p>
          <Field label="Course or career you're aiming for" htmlFor="course" hint="“Not sure yet” is a perfectly good answer." error={err("course")}>
            <input id="course" className="input" aria-invalid={!!err("course")} {...register("course")} />
          </Field>
          <Field label="Entrance exams (optional)">
            <div className="chips" role="group" aria-label="Entrance exams">
              {EXAMS.map((x) => (
                <button type="button" key={x} className="chip" aria-pressed={values.exams.includes(x)} onClick={() => setValue("exams", toggleExam(values.exams, x))}>
                  {x}
                </button>
              ))}
            </div>
          </Field>
          <Field label="How clear are you about your college or course choice?">
            <div className="radio-row" role="radiogroup">
              {CLARITY.map((c) => (
                <label key={c}>
                  <input type="radio" value={c} {...register("clarity")} /> {c}
                </label>
              ))}
            </div>
          </Field>
          <Field label="What would you like help with?" error={err("help")}>
            <div className="chips" role="group" aria-label="Help with">
              {HELP.map((h) => (
                <button
                  type="button"
                  key={h}
                  className="chip"
                  aria-pressed={values.help.includes(h)}
                  onClick={() => setValue("help", values.help.includes(h) ? values.help.filter((x) => x !== h) : [...values.help, h])}
                >
                  {h}
                </button>
              ))}
            </div>
          </Field>
          <Field label="" error={err("consent")}>
            <label className="check">
              <input type="checkbox" {...register("consent")} />
              <span>
                I agree that Careers360 counsellors may use these details to advise me and contact me about admissions. I can
                withdraw this at any time.
              </span>
            </label>
          </Field>
          {otpError && <div className="notice bad" role="alert">{otpError}</div>}
          <div className="row-actions">
            <button type="button" className="btn" onClick={() => setStep(1)}>← Back</button>
            <button className="btn cta" type="submit" disabled={busy}>{busy ? "Sending code…" : "Send my code"}</button>
          </div>
        </form>
      )}

      {step === 3 && (
        <form noValidate onSubmit={finish}>
          <h1>Check your WhatsApp 📱</h1>
          <p>We sent a 4-digit code to <b>{normaliseMobile(values.mobile)}</b>. This keeps your number secure.</p>
          {notice && <div className="notice" role="status">{notice}</div>}
          <Field label="Your code" htmlFor="code" error={otpError}>
            <input
              id="code" className="input otp-input" inputMode="numeric" autoComplete="one-time-code" maxLength={4}
              value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} aria-invalid={!!otpError}
            />
          </Field>
          {duplicate && (
            <div className="notice" role="alert">
              <b>{duplicate.message}</b>
              {duplicate.key && <Link to={`/t/${duplicate.key}`}>See my token</Link>}
            </div>
          )}
          <div className="row-actions">
            <button type="button" className="btn" onClick={() => { setCode(""); setStep(1); }}>← Change number</button>
            <button className="btn cta" type="submit" disabled={busy || code.length !== 4}>{busy ? "Checking…" : "Get my token"}</button>
          </div>
          <p style={{ textAlign: "center" }}>
            <button type="button" className="btn ghost sm" disabled={resendIn > 0 || busy} onClick={sendCode}>
              {resendIn > 0 ? `Resend code in ${resendIn}s` : "Resend code"}
            </button>
          </p>
        </form>
      )}
    </StudentShell>
  );
}

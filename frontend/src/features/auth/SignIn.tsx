import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth, type SignInFailure } from "../../api/auth";
import { defaultPath } from "../../lib/nav";
import "../../styles/console.css";

const BLANK = "Enter your work email and password";

export function SignIn() {
  const { user, signIn, ready } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [tries, setTries] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (ready && user) return <Navigate to={defaultPath(user.role)} replace />;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password) return setError(BLANK);
    setBusy(true);
    try {
      await signIn(email, password);
    } catch (err) {
      const failure = (err as { failure?: SignInFailure }).failure;
      setError(failure?.message ?? (err as Error).message);
      setTries(failure?.failedAttempts ?? tries + 1);
      setNotice(failure?.showHelpdesk ? failure.helpdeskNotice : null);
      setPassword(""); // the email stays, the password is cleared
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <form className="card" onSubmit={submit} noValidate>
        <h1 style={{ marginBottom: "0.25rem" }}>CounselQueue</h1>
        <p className="muted" style={{ marginTop: 0 }}>Sign in with your work account</p>
        <div className="field">
          <label htmlFor="email">Work email</label>
          <input id="email" className="input" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <input
              id="password" className="input" type={show ? "text" : "password"} autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)}
            />
            <button type="button" className="btn" aria-pressed={show} onClick={() => setShow((s) => !s)}>
              {show ? "Hide" : "Show"}
            </button>
          </div>
        </div>
        {error && <div className="notice bad" role="alert" style={{ marginBottom: "0.75rem" }}>{error}</div>}
        {notice && (
          <div className="notice" role="status" style={{ marginBottom: "0.75rem" }} data-tries={tries}>
            <b>Still stuck?</b>
            {notice}
          </div>
        )}
        <button className="btn primary" type="submit" disabled={busy} style={{ width: "100%" }}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="muted" style={{ fontSize: "0.8125rem" }}>
          Trouble signing in? IT helpdesk 1800 572 9877 · it-support@careers360.com
        </p>
      </form>
    </div>
  );
}

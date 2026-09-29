import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth, type SignInFailure } from "../../api/auth";
import { useToast } from "../../app/ui";
import { defaultPath } from "../../lib/nav";
import "../../styles/console.css";

const BLANK = "Enter your work email and password";

export function SignIn() {
  const { user, signIn, ready } = useAuth();
  const toast = useToast();
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
      toast("Signed in", false, true);
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
      <div className="left">
        <div className="brand">Counsel<em>Queue</em></div>
        <div className="pitch">
          <h2>Every counselling desk, on one screen.</h2>
          <p>Tokens, queues, consent and student records for Careers360 city drives. Sign in to reach the centre you're rostered on today.</p>
        </div>
        <div className="foot">
          Careers360 internal tool. Access is logged.
          <br />
          Trouble signing in? IT helpdesk 1800 572 9877 · it-support@careers360.com
        </div>
      </div>
      <div className="right">
        <form onSubmit={submit} noValidate>
          <h1>Sign in</h1>
          <p className="muted" style={{ marginTop: 0 }}>Use your Careers360 work account.</p>
          <div className="field">
            <label htmlFor="email">Work email</label>
            <input id="email" className="input" type="email" placeholder="name@careers360.com" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <div className="pw">
              <input id="password" className="input" type={show ? "text" : "password"} autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" aria-pressed={show} onClick={() => setShow((s) => !s)}>{show ? "Hide" : "Show"}</button>
            </div>
          </div>
          {error && <div className="notice bad" role="alert" style={{ marginBottom: "0.75rem" }}>{error}</div>}
          {notice && (
            <div className="notice" role="status" style={{ marginBottom: "0.75rem" }} data-tries={tries}>
              <b>Still stuck?</b>
              {notice}
            </div>
          )}
          <button className="btn primary" type="submit" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        </form>
      </div>
    </div>
  );
}

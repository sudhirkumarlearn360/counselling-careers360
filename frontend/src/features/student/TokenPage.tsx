import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";
import { useToken } from "../../api/hooks";
import type { TokenView } from "../../api/types";
import { Dialog, errText, useToast } from "../../app/ui";
import { prettyDate } from "../../lib/format";
import { StudentShell } from "./StudentShell";
import { saveToken } from "./schema";

function StateBlock({ t }: { t: TokenView }) {
  const s = t.state;
  switch (s.kind) {
    case "waiting":
      return (
        <div className="state-block" aria-live="polite">
          <div className="big">{s.ahead} ahead of you at {t.desk}</div>
          <p>About {s.minutes} min · expected around {s.expected_at}</p>
          <p className="muted">This is an estimate — it updates by itself.</p>
        </div>
      );
    case "next":
      return (
        <div className="notice ok state-block" aria-live="polite">
          <b className="big">You're next</b>
          Stay near {t.desk} — you'll be called any moment.
        </div>
      );
    case "called":
      return (
        <div className="notice state-block" aria-live="assertive">
          <b className="big">It's your turn</b>
          Go to {t.desk}, {t.counsellor}. Your place is held for two calls.
        </div>
      );
    case "in_session":
      return <div className="state-block"><div className="big">Session in progress</div><p>With {t.counsellor} at {t.desk}.</p></div>;
    case "done":
      return (
        <div className="state-block">
          <div className="big">Session complete</div>
          <p>Your shortlist and next steps are on their way over WhatsApp.</p>
        </div>
      );
    case "no_show":
      return (
        <div className="notice bad state-block">
          <b>We missed you twice</b>
          Visit the front desk and they'll put you back in the queue.
        </div>
      );
    case "released":
      return <div className="state-block"><div className="big">Token released</div><p>You can check in again before {t.closes_at}.</p></div>;
    default:
      return <div className="state-block"><div className="big">Not counselled</div><p>The centre closed before your turn.</p></div>;
  }
}

export function TokenPage() {
  const { accessKey = "" } = useParams();
  const { data: t, isLoading, error } = useToken(accessKey);
  const qc = useQueryClient();
  const toast = useToast();
  const [confirmRelease, setConfirmRelease] = useState(false);
  const [busy, setBusy] = useState(false);

  async function act(path: string, body?: unknown) {
    setBusy(true);
    try {
      await api.post(`public/tokens/${accessKey}/${path}`, body, { auth: false });
      await qc.invalidateQueries({ queryKey: ["token", accessKey] });
    } catch (e) {
      toast(errText(e), true);
    } finally {
      setBusy(false);
      setConfirmRelease(false);
    }
  }

  if (isLoading) return <StudentShell><p role="status">Loading your token…</p></StudentShell>;
  if (error || !t)
    return (
      <StudentShell>
        <h1>We can't find this token</h1>
        <p className="muted">Ask the front desk — they can find your token from your mobile number.</p>
      </StudentShell>
    );

  return (
    <StudentShell wide>
      <div className="token-grid">
        <div>
          <div className="ticket">
            <div className="top">
              <div className="lbl">Your token</div>
              <div className="big" aria-label={`Token ${t.token}`}>{t.token}</div>
              <div className="sub">{t.stream_name}</div>
            </div>
            <div className="perf" />
            <div className="bot">
              {[
                ["Counsellor", t.counsellor], ["Desk", t.desk], ["Venue", t.venue], ["Date", prettyDate(t.date)],
                ["Checked in", t.checked_in_at], ["Name", t.name], ["Mobile", t.mobile],
              ].map(([k, v]) => (
                <div className="kv" key={k}><span>{k}</span><b>{v}</b></div>
              ))}
            </div>
          </div>
        </div>

        <div>
          {t.consent === "pending" && (
            <div className="notice" style={{ marginBottom: "1rem" }}>
              <b>Consent pending</b>
              <span>The front desk checked you in. Confirm it's you and agree to counselling use of your details.</span>
              <button className="btn primary sm" disabled={busy} onClick={() => act("consent")} style={{ marginTop: "0.5rem" }}>
                Confirm it's me
              </button>
            </div>
          )}
          <div className="stu-card"><StateBlock t={t} /></div>

          {t.can_rate && (
            <div className="stu-card">
              <h2>How was the session?</h2>
              <div className="rating" role="group" aria-label="Rate the session">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} aria-label={`${n} out of 5`} aria-pressed={false} disabled={busy} onClick={() => act("rating", { rating: n })}>
                    {n}
                  </button>
                ))}
              </div>
              <p className="muted" style={{ textAlign: "center" }}>Optional — the page works fine without it.</p>
            </div>
          )}
          {t.status === "done" && t.rating != null && (
            <div className="stu-card">
              <div className="rating" aria-label={`You rated ${t.rating} out of 5`}>
                {[1, 2, 3, 4, 5].map((n) => (
                  <button key={n} aria-pressed={n === t.rating} disabled>{n}</button>
                ))}
              </div>
              <p className="muted" style={{ textAlign: "center" }}>Thanks — your rating is saved.</p>
            </div>
          )}

          {t.can_release && (
            <button className="btn" style={{ width: "100%" }} onClick={() => setConfirmRelease(true)}>Give up my turn</button>
          )}
          {["released", "done", "no_show", "not_counselled"].includes(t.status) && t.centre_status === "live" && (
            <Link className="btn" style={{ width: "100%", marginTop: "0.5rem" }} to={`/c/${t.centre_slug}?new=1`} onClick={() => saveToken(t.centre_slug, null)}>
              Check in again
            </Link>
          )}

          <div className="stu-card" style={{ marginTop: "1rem" }}>
            <h2>Need help?</h2>
            <p style={{ margin: 0 }}>
              Front desk {t.front_desk_phone ? <b>{t.front_desk_phone}</b> : "at the entrance"} · {t.venue} · open until {t.closes_at}
            </p>
            <p className="muted" style={{ marginBottom: 0 }}>
              Lost this page? The front desk can find your token from your mobile number.
            </p>
          </div>
        </div>
      </div>

      {confirmRelease && (
        <Dialog title="Give up your turn?" onClose={() => setConfirmRelease(false)}>
          <p>You'll need a new token to rejoin.</p>
          <div className="actions">
            <button className="btn" onClick={() => setConfirmRelease(false)}>Keep my turn</button>
            <button className="btn danger" disabled={busy} onClick={() => act("release")}>Yes, release</button>
          </div>
        </Dialog>
      )}
    </StudentShell>
  );
}

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { ApiError } from "../api/client";

// --- toasts ---------------------------------------------------------------------------------------
interface ToastItem {
  id: number;
  text: string;
  bad: boolean;
  ok?: boolean;
}
const ToastCtx = createContext<(text: string, bad?: boolean, ok?: boolean) => void>(() => undefined);
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((text: string, bad = false, ok = false) => {
    const id = Date.now() + Math.random();
    setItems((xs) => [...xs, { id, text, bad, ok }]);
    setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== id)), 3500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toast-host" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast${t.bad ? " bad" : t.ok ? " ok" : ""}`} role={t.bad ? "alert" : "status"}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const errText = (e: unknown): string =>
  e instanceof ApiError ? e.message : "Something went wrong. Try again.";

// --- form pieces ----------------------------------------------------------------------------------
export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="field">
      {htmlFor ? <label htmlFor={htmlFor}>{label}</label> : <span className="label">{label}</span>}
      {children}
      {hint && <span className="hint">{hint}</span>}
      {error && (
        <span className="err" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}

export function Dialog({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="dialog-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog" role="dialog" aria-modal="true" aria-label={title}>
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}

export function StatusPill({ status }: { status: string }) {
  const tone =
    status === "done" || status === "in_session"
      ? "ok"
      : status === "no_show" || status === "released" || status === "not_counselled"
        ? "bad"
        : status === "called"
          ? "warn"
          : "grey";
  const label: Record<string, string> = {
    waiting: "Waiting", called: "Called", in_session: "In session", done: "Completed",
    no_show: "No-show", released: "Released", not_counselled: "Not counselled",
  };
  return <span className={`pill ${tone}`}>{label[status] ?? status}</span>;
}

/** Student record dialog: only the required student details for Phase 1. */
export function DetailRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="kvrow">
      <span>{label}</span>
      <b>{value || "—"}</b>
    </div>
  );
}

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, session } from "./client";
import type { LoginResult, Me } from "./types";

export interface SignInFailure {
  message: string;
  failedAttempts: number;
  showHelpdesk: boolean;
  helpdeskNotice: string | null;
}
interface AuthState {
  user: Me | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}
const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [ready, setReady] = useState(false);
  const qc = useQueryClient();

  useEffect(() => {
    let live = true;
    (async () => {
      if (session.access() || session.refresh()) {
        try {
          const me = await api.get<Me>("auth/me");
          if (live) setUser(me.data);
        } catch {
          session.clear();
        }
      }
      if (live) setReady(true);
    })();
    return () => {
      live = false;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    try {
      const res = await api.post<LoginResult>("auth/login", { email, password }, { auth: false });
      session.set(res.data.access, res.data.refresh);
      setUser(res.data.user);
    } catch (e) {
      if (e instanceof ApiError) {
        const failure: SignInFailure = {
          message: e.message,
          failedAttempts: Number(e.data.failed_attempts ?? 0),
          showHelpdesk: Boolean(e.data.show_helpdesk),
          helpdeskNotice: (e.data.helpdesk_notice as string | null) ?? null,
        };
        throw Object.assign(e, { failure });
      }
      throw e;
    }
  }, []);

  const signOut = useCallback(async () => {
    const refresh = session.refresh();
    session.clear(); // local sign-out first: the next person can't act as me even if the call fails
    setUser(null);
    qc.clear();
    if (refresh) {
      try {
        await api.post("auth/logout", { refresh }, { auth: false });
      } catch {
        /* the refresh token is dropped locally either way */
      }
    }
  }, [qc]);

  const value = useMemo(() => ({ user, ready, signIn, signOut }), [user, ready, signIn, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}

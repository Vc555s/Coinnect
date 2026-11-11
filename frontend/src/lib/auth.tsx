import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, type ReactNode } from "react";
import { api, tokenStore, type Me } from "./api";

interface AuthValue {
  me: Me | undefined;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<Me>;
  signUp: (body: { name: string; email: string; password: string; headline?: string }) => Promise<Me>;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<Me>("/api/me"),
    enabled: !!tokenStore.get(),
    retry: false,
  });

  const accept = useCallback(
    (res: { token: string; user: Me }) => {
      tokenStore.set(res.token);
      qc.setQueryData(["me"], res.user);
      qc.invalidateQueries();
      return res.user;
    },
    [qc],
  );

  const value = useMemo<AuthValue>(
    () => ({
      me: tokenStore.get() ? data : undefined,
      loading: !!tokenStore.get() && isLoading,
      signIn: (email, password) =>
        api<{ token: string; user: Me }>("/api/auth/login", { method: "POST", body: { email, password } }).then(accept),
      signUp: (body) => api<{ token: string; user: Me }>("/api/auth/register", { method: "POST", body }).then(accept),
      signOut: () => {
        tokenStore.clear();
        qc.removeQueries({ queryKey: ["me"] });
        qc.invalidateQueries();
      },
    }),
    [data, isLoading, accept, qc],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

"use client";

import { onAuthStateChanged, type User } from "firebase/auth";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { auth } from "./firebase";

type AuthState = { user: User | null; loading: boolean };

const AuthContext = createContext<AuthState>({ user: null, loading: true });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, loading: true });
  const router = useRouter();
  const pathname = usePathname();

  useEffect(
    () => onAuthStateChanged(auth, (user) => setState({ user, loading: false })),
    []
  );

  useEffect(() => {
    if (!state.loading && !state.user && pathname !== "/login") {
      router.replace("/login");
    }
  }, [state, pathname, router]);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}

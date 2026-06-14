"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/apiClient";
import type { UserAccount } from "@/lib/types";

interface AccountState { account: UserAccount | null; loading: boolean; fetchError: boolean; refresh: () => Promise<void>; }
const AccountContext = createContext<AccountState>({ account: null, loading: true, fetchError: false, refresh: async () => {} });

// Fetches the signed-in user's account (role/status/budget) and exposes it. No redirects/gating
// live here — that is layered on separately (mirrors how BusinessProvider gating is its own concern).
export function AccountProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [account, setAccount] = useState<UserAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) { setAccount(null); setLoading(false); return; }
    setLoading(true);
    try { setAccount(await api<UserAccount>("/users/me")); setFetchError(false); }
    catch (e) { console.error(e); setAccount(null); setFetchError(true); }
    finally { setLoading(false); }
  }, [user]);

  useEffect(() => { if (!authLoading) void refresh(); }, [authLoading, refresh]);

  return (
    <AccountContext.Provider value={{ account, loading: authLoading || loading, fetchError, refresh }}>
      {children}
    </AccountContext.Provider>
  );
}
export const useAccount = () => useContext(AccountContext);

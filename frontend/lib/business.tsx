"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useAccount } from "@/lib/account";
import { api, ApiError } from "@/lib/apiClient";
import type { Business } from "@/lib/types";

interface BusinessState { business: Business | null; loading: boolean; fetchError: boolean; refresh: () => Promise<void>; }
const BusinessContext = createContext<BusinessState>({ business: null, loading: true, fetchError: false, refresh: async () => {} });

export function BusinessProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const { account } = useAccount();
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const refresh = useCallback(async () => {
    // Only fetch once the account is KNOWN-active. While the account is still loading
    // (null) we must NOT hit /businesses/me — that would run ensure_user concurrently with
    // /users/me on first sign-in and could race-overwrite an invited user back to pending.
    if (!user || account?.status !== "active") { setBusiness(null); setLoading(false); return; }
    setLoading(true);
    try { setBusiness(await api<Business>("/businesses/me")); setFetchError(false); }
    catch (e) {
      if (e instanceof ApiError && e.code === "business_not_found") { setBusiness(null); setFetchError(false); }
      else { console.error(e); setBusiness(null); setFetchError(true); }
    } finally { setLoading(false); }
  }, [user, account]);

  useEffect(() => { if (!authLoading) void refresh(); }, [authLoading, refresh]);

  // Gating: signed-in without business -> /onboarding; with business, keep off /onboarding.
  useEffect(() => {
    if (authLoading || loading || !user) return;
    // Only run the onboarding redirect once the account is KNOWN-active. While it's still
    // loading (null) or pending/disabled, AppShell owns the screen (splash / pending / disabled)
    // — bouncing to /onboarding here would be premature/wrong.
    if (account?.status !== "active") return;
    // Read edit mode from the URL directly (effects only run client-side); useSearchParams
    // would force a Suspense boundary at the root layout.
    const editMode = new URLSearchParams(window.location.search).get("edit") === "1";
    // A fetch error must not dump existing owners on the create form.
    if (!business && !fetchError && pathname !== "/onboarding" && pathname !== "/login") router.replace("/onboarding");
    // edit=1 keeps owners on the form so they can edit their business details.
    if (business && pathname === "/onboarding" && !editMode) router.replace("/dashboard");
  }, [authLoading, loading, user, account, business, fetchError, pathname, router]);

  return (
    <BusinessContext.Provider value={{ business, loading: authLoading || loading, fetchError, refresh }}>
      {children}
    </BusinessContext.Provider>
  );
}
export const useBusiness = () => useContext(BusinessContext);

"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useAccount } from "@/lib/account";
import { api, ApiError } from "@/lib/apiClient";
import type { Business } from "@/lib/types";

interface BusinessState { business: Business | null; loading: boolean; loaded: boolean; fetchError: boolean; refresh: () => Promise<void>; }
const BusinessContext = createContext<BusinessState>({ business: null, loading: true, loaded: false, fetchError: false, refresh: async () => {} });

export function BusinessProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const { account } = useAccount();
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  // `loaded` is true only AFTER a /businesses/me fetch completes for the active account.
  // The onboarding redirect must wait for it: when the account flips to active there is a
  // render where business is still null and loading is still false (refresh hasn't run yet) —
  // redirecting then would flash /onboarding for a business-owner before the fetch lands.
  const [loaded, setLoaded] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const refresh = useCallback(async () => {
    // Only fetch once the account is KNOWN-active. While the account is still loading
    // (null) we must NOT hit /businesses/me — that would run ensure_user concurrently with
    // /users/me on first sign-in and could race-overwrite an invited user back to pending.
    if (!user || account?.status !== "active") { setBusiness(null); setLoading(false); setLoaded(false); return; }
    setLoading(true);
    try { setBusiness(await api<Business>("/businesses/me")); setFetchError(false); }
    catch (e) {
      if (e instanceof ApiError && e.code === "business_not_found") { setBusiness(null); setFetchError(false); }
      else { console.error(e); setBusiness(null); setFetchError(true); }
    } finally { setLoading(false); setLoaded(true); }
  }, [user, account]);

  useEffect(() => { if (!authLoading) void refresh(); }, [authLoading, refresh]);

  // Gating: signed-in without business -> /onboarding; with business, keep off /onboarding.
  useEffect(() => {
    if (authLoading || loading || !user) return;
    // Only run the onboarding redirect once the account is KNOWN-active. While it's still
    // loading (null) or pending/disabled, AppShell owns the screen (splash / pending / disabled)
    // — bouncing to /onboarding here would be premature/wrong.
    if (account?.status !== "active") return;
    // Wait until a business fetch has actually completed for this active account — otherwise the
    // active-but-not-yet-fetched window flashes /onboarding before bouncing to /dashboard.
    if (!loaded) return;
    // Read edit mode from the URL directly (effects only run client-side); useSearchParams
    // would force a Suspense boundary at the root layout.
    const editMode = new URLSearchParams(window.location.search).get("edit") === "1";
    // A fetch error must not dump existing owners on the create form.
    if (!business && !fetchError && pathname !== "/onboarding" && pathname !== "/login") router.replace("/onboarding");
    // edit=1 keeps owners on the form so they can edit their business details.
    if (business && pathname === "/onboarding" && !editMode) router.replace("/dashboard");
  }, [authLoading, loading, loaded, user, account, business, fetchError, pathname, router]);

  return (
    <BusinessContext.Provider value={{ business, loading: authLoading || loading, loaded, fetchError, refresh }}>
      {children}
    </BusinessContext.Provider>
  );
}
export const useBusiness = () => useContext(BusinessContext);

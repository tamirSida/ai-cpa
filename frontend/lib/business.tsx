"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/apiClient";
import type { Business } from "@/lib/types";

interface BusinessState { business: Business | null; loading: boolean; refresh: () => Promise<void>; }
const BusinessContext = createContext<BusinessState>({ business: null, loading: true, refresh: async () => {} });

export function BusinessProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  const refresh = useCallback(async () => {
    if (!user) { setBusiness(null); setLoading(false); return; }
    setLoading(true);
    try { setBusiness(await api<Business>("/businesses/me")); }
    catch (e) {
      if (e instanceof ApiError && e.code === "business_not_found") setBusiness(null);
      else { console.error(e); setBusiness(null); }
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { if (!authLoading) void refresh(); }, [authLoading, refresh]);

  // Gating: signed-in without business -> /onboarding; with business, keep off /onboarding.
  useEffect(() => {
    if (authLoading || loading || !user) return;
    if (!business && pathname !== "/onboarding" && pathname !== "/login") router.replace("/onboarding");
    if (business && pathname === "/onboarding") router.replace("/dashboard");
  }, [authLoading, loading, user, business, pathname, router]);

  return (
    <BusinessContext.Provider value={{ business, loading: authLoading || loading, refresh }}>
      {children}
    </BusinessContext.Provider>
  );
}
export const useBusiness = () => useContext(BusinessContext);

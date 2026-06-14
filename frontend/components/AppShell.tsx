"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useAccount } from "@/lib/account";
import { useBusiness } from "@/lib/business";
import BottomNav from "./BottomNav";

const BARE_ROUTES = ["/login", "/onboarding", "/pending", "/disabled"];

function Splash() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <Loader2 size={28} className="animate-spin text-foreground/40" />
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { account, loading: accountLoading } = useAccount();
  const { loading: bizLoading } = useBusiness();

  // Status gate: lock pending users to /pending, disabled users to /disabled, and bounce
  // active users off those screens. AuthProvider owns the /login redirect.
  useEffect(() => {
    if (authLoading || !user) return;            // AuthProvider owns the /login redirect
    if (accountLoading || !account) return;      // wait until we know status
    if (account.status === "pending" && pathname !== "/pending") router.replace("/pending");
    else if (account.status === "disabled" && pathname !== "/disabled") router.replace("/disabled");
    else if (account.status === "active" && (pathname === "/pending" || pathname === "/disabled")) router.replace("/chat");
  }, [authLoading, user, accountLoading, account, pathname, router]);

  if (pathname === "/login") return <>{children}</>;               // login renders immediately
  if (authLoading || (user && accountLoading)) return <Splash />;  // resolving auth/account
  // active user whose business is still loading, on a non-bare route -> splash (avoid chrome flash)
  if (user && account?.status === "active" && bizLoading && !BARE_ROUTES.includes(pathname)) return <Splash />;
  // pending/disabled user on a deep route: the status-gate redirect is in flight — don't flash app chrome
  if (user && account && account.status !== "active" && !BARE_ROUTES.includes(pathname)) return <Splash />;

  if (BARE_ROUTES.includes(pathname)) return <>{children}</>;
  return (
    <div className="mx-auto w-full max-w-lg md:max-w-3xl">
      <main className="min-h-dvh pb-[calc(4rem+env(safe-area-inset-bottom,0px))]">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}

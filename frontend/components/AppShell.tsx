"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { signOut } from "firebase/auth";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useAccount } from "@/lib/account";
import { useBusiness } from "@/lib/business";
import { auth } from "@/lib/firebase";
import { useT } from "@/lib/i18n";
import BottomNav from "./BottomNav";

const BARE_ROUTES = ["/login", "/onboarding", "/pending", "/disabled"];

function Splash() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <Loader2 size={28} className="animate-spin text-foreground/40" />
    </div>
  );
}

// Shown when GET /users/me fails (network/server). Without this we'd fall through to app
// chrome with a null account, silently disabling the status gate — so offer retry/sign-out.
function AccountError({ onRetry }: { onRetry: () => void }) {
  const t = useT();
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-6 text-center">
        <h1 className="text-xl font-semibold">{t("misc.accountLoadFailedTitle")}</h1>
        <p className="mt-2 text-sm text-foreground/60">{t("misc.accountLoadFailedBody")}</p>
        <button
          onClick={onRetry}
          className="mt-5 min-h-12 w-full rounded-xl bg-primary font-medium text-on-primary active:scale-[0.98]"
        >
          {t("misc.tryAgain")}
        </button>
        <button
          onClick={() => void signOut(auth)}
          className="mt-3 min-h-12 w-full rounded-xl border border-border font-medium text-foreground/70 active:scale-[0.98]"
        >
          {t("common.signOut")}
        </button>
      </div>
    </div>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const { account, loading: accountLoading, fetchError: accountError, refresh: refreshAccount } = useAccount();
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
  // signed in but /users/me failed (no account, not loading): offer retry, not broken chrome
  if (user && !accountLoading && !account && accountError) return <AccountError onRetry={() => void refreshAccount()} />;
  // active user whose business is still loading, on a non-bare route -> splash (avoid chrome flash)
  if (user && account?.status === "active" && bizLoading && !BARE_ROUTES.includes(pathname)) return <Splash />;
  // pending/disabled user: ONLY their own status screen may render; on any other route
  // (incl. the bare /onboarding form) the status-gate redirect is in flight -> splash.
  if (user && account && account.status !== "active") {
    const allowed = account.status === "pending" ? "/pending" : "/disabled";
    if (pathname !== allowed) return <Splash />;
  }

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

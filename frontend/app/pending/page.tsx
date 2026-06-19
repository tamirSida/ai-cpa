"use client";

import { signOut } from "firebase/auth";
import { Clock, Loader2, LogOut, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAccount } from "@/lib/account";
import { auth } from "@/lib/firebase";
import { useT } from "@/lib/i18n";

export default function PendingPage() {
  const router = useRouter();
  const account = useAccount();
  const t = useT();
  const [busy, setBusy] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Poll status every 15s; the AppShell gate auto-redirects once the account is approved.
  useEffect(() => {
    const id = setInterval(() => void account.refresh(), 15000);
    return () => clearInterval(id);
  }, [account]);

  async function handleRefresh() {
    setBusy(true);
    try {
      await account.refresh();
    } finally {
      setBusy(false);
    }
  }

  async function handleSignOut() {
    setError(null);
    setSigningOut(true);
    try {
      await signOut(auth);
      router.replace("/login");
    } catch {
      setError(t("common.signOutFailed"));
      setSigningOut(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-6 text-center">
        <Clock size={56} className="mx-auto text-foreground/30" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold">{t("pending.title")}</h1>
        <p className="mt-2 text-sm text-foreground/60">{t("pending.body")}</p>
        <button
          onClick={handleRefresh}
          disabled={busy}
          className="mt-6 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {busy ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <RefreshCw size={20} aria-hidden />
          )}
          {t("common.refresh")}
        </button>
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className="mt-3 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {signingOut ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <LogOut size={20} aria-hidden />
          )}
          {t("common.signOut")}
        </button>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </div>
    </main>
  );
}

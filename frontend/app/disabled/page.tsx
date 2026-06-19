"use client";

import { signOut } from "firebase/auth";
import { Ban, Loader2, LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { auth } from "@/lib/firebase";
import { useT } from "@/lib/i18n";

export default function DisabledPage() {
  const router = useRouter();
  const t = useT();
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        <Ban size={56} className="mx-auto text-destructive/60" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold">{t("disabled.title")}</h1>
        <p className="mt-2 text-sm text-foreground/60">{t("disabled.body")}</p>
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className="mt-6 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
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

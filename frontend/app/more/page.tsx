"use client";

import { signOut } from "firebase/auth";
import {
  Building2,
  ChevronLeft,
  FileText,
  Loader2,
  LogOut,
  Shield,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import LangToggle from "@/components/LangToggle";
import { useAccount } from "@/lib/account";
import { auth } from "@/lib/firebase";
import { formatUsd } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

const LINKS = [
  { href: "/clients", labelKey: "more.clients", Icon: Users },
  { href: "/annual-report", labelKey: "more.annualReport", Icon: FileText },
  { href: "/onboarding?edit=1", labelKey: "more.businessDetails", Icon: Building2 },
];

export default function MorePage() {
  const router = useRouter();
  const { t } = useI18n();
  const { account } = useAccount();
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
    <div className="px-4 pt-6">
      <h1 className="text-2xl font-semibold">{t("more.title")}</h1>
      <div className="mt-4 flex flex-col gap-3">
        <div className="flex min-h-12 items-center justify-between gap-3 rounded-2xl border border-border bg-white p-4">
          <span className="font-medium">{t("more.language")}</span>
          <LangToggle />
        </div>
        {account && (
          <div className="rounded-2xl border border-border bg-white p-4">
            <p className="text-sm text-foreground/60">{t("more.aiQuotaThisMonth")}</p>
            <p className="mt-1 font-medium">
              <span dir="ltr">
                {formatUsd(account.usage.aiCostUsd)} /{" "}
                {account.aiBudgetUsd === null ? t("common.unlimited") : formatUsd(account.aiBudgetUsd)}
              </span>
            </p>
          </div>
        )}
        {account?.role === "admin" && (
          <Link
            href="/admin"
            className="flex min-h-12 items-center gap-3 rounded-2xl border border-border bg-white p-4 font-medium transition-transform duration-150 active:scale-[0.98]"
          >
            <Shield size={22} className="text-primary" aria-hidden />
            <span className="flex-1 text-start">{t("more.systemAdmin")}</span>
            <ChevronLeft size={20} className="text-foreground/40 rtl:rotate-0 rotate-180" aria-hidden />
          </Link>
        )}
        {LINKS.map(({ href, labelKey, Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex min-h-12 items-center gap-3 rounded-2xl border border-border bg-white p-4 font-medium transition-transform duration-150 active:scale-[0.98]"
          >
            <Icon size={22} className="text-primary" aria-hidden />
            <span className="flex-1 text-start">{t(labelKey)}</span>
            <ChevronLeft size={20} className="text-foreground/40 rtl:rotate-0 rotate-180" aria-hidden />
          </Link>
        ))}
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className="flex min-h-12 items-center justify-center gap-2 rounded-2xl border border-border bg-white p-4 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {signingOut ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <LogOut size={20} aria-hidden />
          )}
          {t("common.signOut")}
        </button>
        {error && <p className="text-center text-sm text-destructive">{error}</p>}
      </div>
    </div>
  );
}

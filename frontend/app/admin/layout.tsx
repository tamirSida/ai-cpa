"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { useAccount } from "@/lib/account";
import { useI18n } from "@/lib/i18n";

const TABS = [
  { href: "/admin", labelKey: "admin.tabUsers" },
  { href: "/admin/invites", labelKey: "admin.tabInvites" },
];

function Splash() {
  return (
    <div className="flex min-h-dvh items-center justify-center">
      <Loader2 size={28} className="animate-spin text-foreground/40" />
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { account, loading } = useAccount();
  const { t, lang } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const BackArrow = lang === "he" ? ArrowRight : ArrowLeft;

  useEffect(() => {
    if (!loading && account && account.role !== "admin") router.replace("/chat");
  }, [loading, account, router]);

  if (loading) return <Splash />;
  if (!account || account.role !== "admin") return null; // redirect in flight

  return (
    <div>
      <header className="px-4 pt-6">
        <div className="flex items-center gap-2">
          <Link
            href="/more"
            aria-label={t("admin.back")}
            className="flex min-h-12 min-w-12 items-center justify-center -ms-3 rounded-xl text-foreground/55 transition-transform duration-150 active:scale-[0.96]"
          >
            <BackArrow size={22} aria-hidden />
          </Link>
          <h1 className="text-lg font-semibold">{t("admin.title")}</h1>
        </div>
        <div
          role="tablist"
          aria-label={t("admin.title")}
          className="mt-4 flex rounded-xl border border-border bg-muted p-1"
        >
          {TABS.map((tab) => {
            const active = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                role="tab"
                aria-selected={active}
                className={`flex min-h-12 flex-1 items-center justify-center rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-white font-medium text-foreground shadow-sm"
                    : "text-foreground/55"
                }`}
              >
                {t(tab.labelKey)}
              </Link>
            );
          })}
        </div>
      </header>
      {children}
    </div>
  );
}

"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, Loader2 } from "lucide-react";
import { useAccount } from "@/lib/account";

const TABS = [
  { href: "/admin", label: "משתמשים" },
  { href: "/admin/invites", label: "הזמנות" },
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
  const router = useRouter();
  const pathname = usePathname();

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
            aria-label="חזרה"
            className="flex min-h-12 min-w-12 items-center justify-center -ms-3 rounded-xl text-foreground/55 transition-transform duration-150 active:scale-[0.96]"
          >
            <ArrowRight size={22} aria-hidden />
          </Link>
          <h1 className="text-lg font-semibold">ניהול מערכת</h1>
        </div>
        <div
          role="tablist"
          aria-label="ניהול מערכת"
          className="mt-4 flex rounded-xl border border-border bg-muted p-1"
        >
          {TABS.map((t) => {
            const active = pathname === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                role="tab"
                aria-selected={active}
                className={`flex min-h-12 flex-1 items-center justify-center rounded-lg text-sm transition-colors ${
                  active
                    ? "bg-white font-medium text-foreground shadow-sm"
                    : "text-foreground/55"
                }`}
              >
                {t.label}
              </Link>
            );
          })}
        </div>
      </header>
      {children}
    </div>
  );
}

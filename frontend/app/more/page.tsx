"use client";

import { signOut } from "firebase/auth";
import {
  Building2,
  ChevronLeft,
  FileText,
  Loader2,
  LogOut,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { auth } from "@/lib/firebase";

const LINKS = [
  { href: "/clients", label: "לקוחות", Icon: Users },
  { href: "/annual-report", label: "דוח שנתי", Icon: FileText },
  { href: "/onboarding?edit=1", label: "פרטי העסק", Icon: Building2 },
];

export default function MorePage() {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    try {
      await signOut(auth);
      router.replace("/login");
    } catch {
      setSigningOut(false);
    }
  }

  return (
    <div className="px-4 pt-6">
      <h1 className="text-2xl font-semibold">עוד</h1>
      <div className="mt-4 flex flex-col gap-3">
        {LINKS.map(({ href, label, Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex min-h-12 items-center gap-3 rounded-2xl border border-border bg-white p-4 font-medium transition-transform duration-150 active:scale-[0.98]"
          >
            <Icon size={22} className="text-primary" aria-hidden />
            <span className="flex-1 text-start">{label}</span>
            <ChevronLeft size={20} className="text-foreground/40" aria-hidden />
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
          התנתקות
        </button>
      </div>
    </div>
  );
}

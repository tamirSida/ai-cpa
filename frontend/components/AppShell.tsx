"use client";

import { usePathname } from "next/navigation";
import BottomNav from "./BottomNav";

const BARE_ROUTES = ["/login", "/onboarding"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
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

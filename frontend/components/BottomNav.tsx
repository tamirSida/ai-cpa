"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Menu,
  MessageCircle,
  ReceiptText,
  Wallet,
} from "lucide-react";
import { useT } from "@/lib/i18n";
import type { MsgKey } from "@/lib/messages";

const ITEMS: { href: string; labelKey: MsgKey; Icon: typeof MessageCircle }[] = [
  { href: "/chat", labelKey: "nav.chat", Icon: MessageCircle },
  { href: "/dashboard", labelKey: "nav.dashboard", Icon: LayoutDashboard },
  { href: "/receipts", labelKey: "nav.receipts", Icon: ReceiptText },
  { href: "/expenses", labelKey: "nav.expenses", Icon: Wallet },
  { href: "/more", labelKey: "nav.more", Icon: Menu },
];

export default function BottomNav() {
  const pathname = usePathname();
  const t = useT();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-white pb-safe">
      <div className="mx-auto flex h-16 max-w-lg md:max-w-3xl">
        {ITEMS.map(({ href, labelKey, Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 text-xs font-medium transition-colors ${
                active ? "text-primary" : "text-foreground/55"
              }`}
            >
              <Icon size={24} strokeWidth={active ? 2.4 : 2} aria-hidden />
              {t(labelKey)}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

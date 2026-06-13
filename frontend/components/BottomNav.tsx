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

const ITEMS = [
  { href: "/chat", label: "צ'אט", Icon: MessageCircle },
  { href: "/dashboard", label: "סקירה", Icon: LayoutDashboard },
  { href: "/receipts", label: "קבלות", Icon: ReceiptText },
  { href: "/expenses", label: "הוצאות", Icon: Wallet },
  { href: "/more", label: "עוד", Icon: Menu },
];

export default function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-white pb-safe">
      <div className="mx-auto flex h-16 max-w-lg md:max-w-3xl">
        {ITEMS.map(({ href, label, Icon }) => {
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
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

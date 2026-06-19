import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans_Hebrew } from "next/font/google";
import AppShell from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import { AccountProvider } from "@/lib/account";
import { BusinessProvider } from "@/lib/business";
import { I18nProvider } from "@/lib/i18n";
import "./globals.css";

const plexHebrew = IBM_Plex_Sans_Hebrew({
  subsets: ["hebrew", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-hebrew",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Bookkeeper",
  description: "Chat-first bookkeeping for Israeli sole proprietors",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  interactiveWidget: "resizes-content",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // English is the default; I18nProvider flips lang/dir to Hebrew/RTL on the client when chosen.
  return (
    <html lang="en" dir="ltr" className={plexHebrew.variable}>
      <body>
        <I18nProvider>
          <AuthProvider>
            <AccountProvider>
              <BusinessProvider>
                <AppShell>{children}</AppShell>
              </BusinessProvider>
            </AccountProvider>
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}

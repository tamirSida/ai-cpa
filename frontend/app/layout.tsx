import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans_Hebrew } from "next/font/google";
import AppShell from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const plexHebrew = IBM_Plex_Sans_Hebrew({
  subsets: ["hebrew", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-hebrew",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Bookkeeper",
  description: "הנהלת חשבונות בצ'אט לעוסק פטור",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  interactiveWidget: "resizes-content",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={plexHebrew.variable}>
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}

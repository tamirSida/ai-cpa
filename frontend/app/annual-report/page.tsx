// frontend/app/annual-report/page.tsx
"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CircleCheck,
  ClipboardCheck,
  FileDown,
  Loader2,
  RotateCw,
  TriangleAlert,
} from "lucide-react";
import { api, apiBlob, ApiError } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useBusiness } from "@/lib/business";
import { formatILS } from "@/lib/format";
import type { PrecheckResult } from "@/lib/types";

type CheckKey =
  | "expensesNeedingReview"
  | "expensesMissingImages"
  | "uncategorizedExpenses"
  | "receiptsMissingPdf"
  | "cancelledReceipts"
  | "missingBusinessFields";

const CHECKS: { key: CheckKey; label: string; fixHref: string; fixLabel: string }[] = [
  { key: "expensesNeedingReview", label: "הוצאות שדורשות בדיקה", fixHref: "/expenses", fixLabel: "מעבר להוצאות" },
  { key: "expensesMissingImages", label: "הוצאות ללא קבלה מצולמת", fixHref: "/expenses", fixLabel: "מעבר להוצאות" },
  { key: "uncategorizedExpenses", label: "הוצאות ללא קטגוריה", fixHref: "/expenses", fixLabel: "מעבר להוצאות" },
  { key: "receiptsMissingPdf", label: "קבלות ללא PDF", fixHref: "/receipts", fixLabel: "מעבר לקבלות" },
  { key: "cancelledReceipts", label: "קבלות מבוטלות", fixHref: "/receipts", fixLabel: "מעבר לקבלות" },
  { key: "missingBusinessFields", label: "פרטי עסק חסרים", fixHref: "/dashboard", fixLabel: "מעבר לפרטי העסק" },
];

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = [CURRENT_YEAR - 1, CURRENT_YEAR, CURRENT_YEAR + 1];

// Shared focus-ring classes — every interactive control in this app uses them, and
// -webkit-tap-highlight-color is suppressed globally, so omitting them leaves no focus affordance.
const FOCUS_RING = "focus:outline-none focus:ring-2 focus:ring-primary";

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-border bg-white p-4">
      <div className="h-4 w-1/2 rounded bg-muted" />
      <div className="mt-3 h-4 w-1/3 rounded bg-muted" />
    </div>
  );
}

export default function AnnualReportPage() {
  const { user, loading } = useAuth();
  // Consume the always-mounted BusinessProvider instead of re-fetching /businesses/me here:
  // a local fetch that fails would leave `business` null forever and trap the page on the skeleton.
  const { business, loading: bizLoading, fetchError, refresh } = useBusiness();
  const router = useRouter();
  const [year, setYear] = useState(CURRENT_YEAR);
  const [precheck, setPrecheck] = useState<PrecheckResult | null>(null);
  const [prechecking, setPrechecking] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [downloadedYear, setDownloadedYear] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Invalidates an in-flight precheck if the user changes year (or re-runs) before it resolves,
  // so a stale response can never repopulate the wrong year's data.
  const precheckReq = useRef(0);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  function selectYear(y: number) {
    precheckReq.current += 1;
    setYear(y);
    setPrecheck(null);
    setDownloadedYear(null);
    setError(null);
  }

  async function runPrecheck() {
    if (!business) return;
    const reqId = (precheckReq.current += 1);
    const requestedYear = year;
    setPrechecking(true);
    setError(null);
    setDownloadedYear(null);
    try {
      const result = await api<PrecheckResult>(
        `/businesses/${business.id}/reports/annual/${requestedYear}/precheck`,
        { method: "POST" },
      );
      if (precheckReq.current === reqId) setPrecheck(result);
    } catch (e) {
      if (precheckReq.current === reqId) {
        setError(e instanceof ApiError ? e.message : "הבדיקה נכשלה, נסו שוב");
      }
    } finally {
      if (precheckReq.current === reqId) setPrechecking(false);
    }
  }

  async function generateAndDownload() {
    if (!business) return;
    const requestedYear = year;
    setGenerating(true);
    setError(null);
    try {
      const blob = await apiBlob(
        `/businesses/${business.id}/reports/annual/${requestedYear}/generate`,
        { method: "POST" },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `annual_report_${requestedYear}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      // iOS/WebKit starts the download on the next tick; revoking synchronously kills it.
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDownloadedYear(requestedYear);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "הפקת הדוח נכשלה, נסו שוב");
    } finally {
      setGenerating(false);
    }
  }

  if (loading || bizLoading) {
    return (
      <div className="space-y-3 px-4 py-6" aria-busy="true" aria-label="טוען דף דוח שנתי">
        <div className="h-8 w-36 animate-pulse rounded-lg bg-border" />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (!user) return null; // redirect effect handles navigation to /login

  if (fetchError || !business) {
    return (
      <div className="space-y-4 px-4 py-6">
        <div
          className="flex items-start gap-3 rounded-2xl border border-destructive/40 bg-destructive/5 p-4"
          role="alert"
        >
          <TriangleAlert size={20} className="mt-0.5 shrink-0 text-destructive" aria-hidden />
          <div className="min-w-0">
            <p className="font-medium text-destructive">טעינת פרטי העסק נכשלה</p>
            <p className="mt-1 text-sm text-foreground/60">בדקו את החיבור לאינטרנט ונסו שוב.</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          className={`flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] ${FOCUS_RING}`}
        >
          <RotateCw size={20} aria-hidden />
          נסו שוב
        </button>
      </div>
    );
  }

  const issueCards = precheck
    ? CHECKS.map((c) => ({ ...c, count: precheck[c.key].length })).filter((c) => c.count > 0)
    : [];
  const busy = prechecking || generating;

  return (
    <div className="space-y-4 px-4 py-6">
      <header>
        <h1 className="text-2xl font-semibold">דוח שנתי</h1>
        <p className="mt-1 text-sm text-foreground/60">
          חבילה מוכנה לרואה החשבון: קבצי CSV, סיכום PDF וכל הקבלות וההוצאות.
        </p>
      </header>

      <section className="rounded-2xl border border-border bg-white p-4">
        <p className="text-sm font-medium">שנת הדוח</p>
        <div className="mt-2 flex rounded-xl bg-muted p-1" role="group" aria-label="בחירת שנה">
          {YEARS.map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => selectYear(y)}
              disabled={busy}
              aria-pressed={y === year}
              aria-label={`שנת ${y}`}
              className={`min-h-12 flex-1 rounded-lg text-base font-medium transition-transform duration-150 active:scale-[0.98] disabled:opacity-50 ${FOCUS_RING} ${
                y === year ? "bg-white text-foreground shadow-sm" : "text-foreground/60"
              }`}
            >
              <span dir="ltr" className="tnum">{y}</span>
            </button>
          ))}
        </div>
      </section>

      <button
        type="button"
        onClick={runPrecheck}
        disabled={busy}
        className={`flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50 ${FOCUS_RING}`}
      >
        {prechecking ? (
          <Loader2 size={20} className="animate-spin" aria-hidden />
        ) : (
          <ClipboardCheck size={20} aria-hidden />
        )}
        בדיקה מקדימה
      </button>

      {/* Always-mounted live region: AT only announces changes to a region present at mount. */}
      <div aria-live="polite">
        {precheck && (
          <section className="space-y-3">
            <div className="rounded-2xl border border-border bg-white p-4">
              <p className="text-sm text-foreground/60">
                סך הכנסות לשנת <span dir="ltr" className="tnum">{precheck.year}</span>
              </p>
              <p className="mt-1 text-2xl font-semibold tnum" dir="ltr">
                {formatILS(precheck.totalRevenue)}
              </p>
            </div>

            {precheck.thresholdWarning && (
              <div className="flex items-start gap-3 rounded-2xl border border-destructive/40 bg-destructive/5 p-4">
                <TriangleAlert size={20} className="mt-0.5 shrink-0 text-destructive" aria-hidden />
                <p className="text-sm font-medium text-destructive">
                  {/* the limit itself comes from the backend config (ANNUAL_LIMIT_ILS) — don't hardcode it here */}
                  ההכנסות מתקרבות לתקרת עוסק פטור. מומלץ להתייעץ עם רואה חשבון.
                </p>
              </div>
            )}

            {issueCards.length === 0 ? (
              <div className="flex items-start gap-3 rounded-2xl border border-accent/40 bg-accent/5 p-4">
                <CircleCheck size={24} className="shrink-0 text-accent" aria-hidden />
                <div>
                  <p className="font-medium">הכל מוכן להפקה</p>
                  <p className="mt-1 text-sm text-foreground/60">לא נמצאו פריטים חסרים לשנה זו.</p>
                </div>
              </div>
            ) : (
              issueCards.map((c) => (
                <div
                  key={c.key}
                  className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4"
                >
                  <TriangleAlert size={20} className="mt-0.5 shrink-0 text-amber-600" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-amber-900">
                      {c.label} <span dir="ltr" className="tnum">({c.count})</span>
                    </p>
                    <Link
                      href={c.fixHref}
                      className={`mt-1 inline-flex min-h-12 items-center rounded text-sm font-medium text-primary ${FOCUS_RING}`}
                    >
                      {c.fixLabel}
                    </Link>
                  </div>
                </div>
              ))
            )}
          </section>
        )}
      </div>

      <div className="space-y-2">
        <button
          type="button"
          onClick={generateAndDownload}
          disabled={!precheck || busy}
          className={`flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50 ${FOCUS_RING}`}
        >
          {generating ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <FileDown size={20} aria-hidden />
          )}
          {generating ? "מכין את הדוח..." : "צור דוח שנתי"}
        </button>
        <div aria-live="polite">
          {generating && (
            <p className="text-center text-sm text-foreground/60">
              אוספים קבלות, הוצאות וקבצים לחבילה — זה יכול לקחת עד דקה.
            </p>
          )}
        </div>
        {!precheck && (
          <p className="text-center text-xs text-foreground/60">
            יש להריץ בדיקה מקדימה לפני הפקת הדוח.
          </p>
        )}
        <p className="text-center text-xs text-foreground/60">
          באייפון קובץ ה־ZIP נשמר באפליקציית ״קבצים״ (Files) תחת ״הורדות״.
        </p>
        {error && (
          <p className="text-center text-sm text-destructive" role="alert">
            {error}
          </p>
        )}
      </div>

      <div aria-live="polite">
        {downloadedYear !== null && (
          <div className="flex items-start gap-3 rounded-2xl border border-accent/40 bg-accent/5 p-4">
            <CircleCheck size={24} className="shrink-0 text-accent" aria-hidden />
            <div className="min-w-0">
              <p className="font-medium">הדוח הופק והורד</p>
              <p className="mt-1 text-sm text-foreground/60">
                הקובץ <span dir="ltr" className="tnum">annual_report_{downloadedYear}.zip</span> ירד למכשיר —
                אפשר לשלוח אותו לרואה החשבון.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// frontend/app/annual-report/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CircleCheck,
  ClipboardCheck,
  FileDown,
  Loader2,
  TriangleAlert,
} from "lucide-react";
import { api, apiBlob, ApiError } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { formatILS } from "@/lib/format";
import type { Business, PrecheckResult } from "@/lib/types";

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
  const router = useRouter();
  const [business, setBusiness] = useState<Business | null>(null);
  const [year, setYear] = useState(CURRENT_YEAR);
  const [precheck, setPrecheck] = useState<PrecheckResult | null>(null);
  const [prechecking, setPrechecking] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;
    api<Business>("/businesses/me")
      .then(setBusiness)
      .catch((e) => setError(e instanceof ApiError ? e.message : "טעינת העסק נכשלה"));
  }, [user]);

  function selectYear(y: number) {
    setYear(y);
    setPrecheck(null);
    setDownloaded(false);
    setError(null);
  }

  async function runPrecheck() {
    if (!business) return;
    setPrechecking(true);
    setError(null);
    setDownloaded(false);
    try {
      setPrecheck(
        await api<PrecheckResult>(
          `/businesses/${business.id}/reports/annual/${year}/precheck`,
          { method: "POST" },
        ),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "הבדיקה נכשלה, נסו שוב");
    } finally {
      setPrechecking(false);
    }
  }

  async function generateAndDownload() {
    if (!business) return;
    setGenerating(true);
    setError(null);
    try {
      const blob = await apiBlob(
        `/businesses/${business.id}/reports/annual/${year}/generate`,
        { method: "POST" },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `annual_report_${year}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setDownloaded(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "הפקת הדוח נכשלה, נסו שוב");
    } finally {
      setGenerating(false);
    }
  }

  if (loading || !user || !business) {
    return (
      <div className="space-y-3 px-4 py-6">
        <div className="h-8 w-36 animate-pulse rounded-lg bg-border" />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  const issueCards = precheck
    ? CHECKS.map((c) => ({ ...c, count: precheck[c.key].length })).filter((c) => c.count > 0)
    : [];

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
              aria-pressed={y === year}
              className={`min-h-12 flex-1 rounded-lg text-base font-medium transition-transform duration-150 active:scale-[0.98] ${
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
        disabled={prechecking || generating}
        className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
      >
        {prechecking ? (
          <Loader2 size={20} className="animate-spin" aria-hidden />
        ) : (
          <ClipboardCheck size={20} aria-hidden />
        )}
        בדיקה מקדימה
      </button>

      {precheck && (
        <section className="space-y-3" aria-live="polite">
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
                    className="mt-1 inline-flex min-h-12 items-center text-sm font-medium text-primary"
                  >
                    {c.fixLabel}
                  </Link>
                </div>
              </div>
            ))
          )}
        </section>
      )}

      <div className="space-y-2">
        <button
          type="button"
          onClick={generateAndDownload}
          disabled={!precheck || generating || prechecking}
          className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {generating ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <FileDown size={20} aria-hidden />
          )}
          {generating ? "מכין את הדוח..." : "צור דוח שנתי"}
        </button>
        {generating && (
          <p className="text-center text-sm text-foreground/60" aria-live="polite">
            אוספים קבלות, הוצאות וקבצים לחבילה — זה יכול לקחת עד דקה.
          </p>
        )}
        {!precheck && (
          <p className="text-center text-xs text-foreground/60">
            יש להריץ בדיקה מקדימה לפני הפקת הדוח.
          </p>
        )}
        <p className="text-center text-xs text-foreground/60">
          באייפון קובץ ה־ZIP נשמר באפליקציית ״קבצים״ (Files) תחת ״הורדות״.
        </p>
        {error && <p className="text-center text-sm text-destructive">{error}</p>}
      </div>

      {downloaded && (
        <div className="flex items-start gap-3 rounded-2xl border border-accent/40 bg-accent/5 p-4">
          <CircleCheck size={24} className="shrink-0 text-accent" aria-hidden />
          <div className="min-w-0">
            <p className="font-medium">הדוח הופק והורד</p>
            <p className="mt-1 text-sm text-foreground/60">
              הקובץ <span dir="ltr" className="tnum">annual_report_{year}.zip</span> ירד למכשיר —
              אפשר לשלוח אותו לרואה החשבון.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// frontend/app/dashboard/page.tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MessageCircle, ReceiptText, TriangleAlert, Wallet } from "lucide-react";
import DashboardCards from "@/components/DashboardCards";
import EmptyState from "@/components/EmptyState";
import MonthlyIncomeChart from "@/components/MonthlyIncomeChart";
import { ApiError, api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { formatILS } from "@/lib/format";
import { Business, DashboardResponse } from "@/lib/types";

function DashboardSkeleton() {
  return (
    <div className="space-y-3 p-4">
      <div className="h-8 w-28 animate-pulse rounded-lg bg-border/60" />
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-2xl bg-border/60" />
        ))}
      </div>
      <div className="h-28 animate-pulse rounded-2xl bg-border/60" />
      <div className="h-64 animate-pulse rounded-2xl bg-border/60" />
    </div>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (loading || !user) return;
    api<Business>("/businesses/me")
      .then((biz) => api<DashboardResponse>(`/businesses/${biz.id}/dashboard`))
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "שגיאה בטעינת הנתונים"));
  }, [loading, user, reloadKey]);

  if (loading || (!data && !error)) return <DashboardSkeleton />;
  if (error)
    return (
      <div className="p-4">
        <div className="rounded-2xl border border-border bg-white p-6 text-center">
          <p className="text-destructive">{error}</p>
          <button
            type="button"
            onClick={() => {
              setError(null);
              setData(null);
              setReloadKey((k) => k + 1);
            }}
            className="mt-4 inline-flex min-h-12 items-center justify-center rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
          >
            נסה שנית
          </button>
        </div>
      </div>
    );
  const d = data!;
  const isEmpty =
    d.counts.receiptsCount === 0 && d.recentExpenses.length === 0 && d.totals.incomeThisYear === 0;

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-2xl font-semibold">סקירה</h1>

      {d.warnings.length > 0 && (
        <div className="space-y-2">
          {d.warnings.map((w) => (
            <div
              key={w}
              className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"
            >
              <TriangleAlert size={20} className="mt-0.5 shrink-0 text-amber-600" aria-hidden />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      <DashboardCards data={d} />

      {isEmpty ? (
        <EmptyState
          Icon={MessageCircle}
          title="עדיין אין נתונים"
          hint="כתבו בצ'אט מה קרה בעסק כדי להתחיל"
          action={
            <Link
              href="/chat"
              className="mt-2 inline-flex min-h-12 items-center justify-center rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
            >
              מעבר לצ'אט
            </Link>
          }
        />
      ) : (
        <>
          <section className="rounded-2xl border border-border bg-white p-4">
            <h2 className="mb-2 text-lg font-semibold">הכנסות לפי חודש</h2>
            <MonthlyIncomeChart data={d.monthlyIncome} />
          </section>

          <section className="rounded-2xl border border-border bg-white p-4">
            <h2 className="mb-2 text-lg font-semibold">הוצאות לפי קטגוריה</h2>
            {Object.keys(d.expensesByCategory).length === 0 ? (
              <p className="text-sm text-foreground/60">אין הוצאות מאושרות השנה.</p>
            ) : (
              <ul className="divide-y divide-border text-sm">
                {Object.entries(d.expensesByCategory)
                  .sort((a, b) => b[1] - a[1])
                  .map(([cat, total]) => (
                    <li key={cat} className="flex items-center justify-between py-3">
                      <span>{cat}</span>
                      <span className="tnum font-medium" dir="ltr">{formatILS(total)}</span>
                    </li>
                  ))}
              </ul>
            )}
          </section>

          <div className="space-y-4 md:grid md:grid-cols-2 md:gap-4 md:space-y-0">
            <section>
              <div className="mb-1 flex items-center justify-between">
                <h2 className="text-lg font-semibold">קבלות אחרונות</h2>
                <Link href="/receipts" className="flex min-h-12 items-center text-sm font-medium text-primary">
                  הצג הכל
                </Link>
              </div>
              {d.recentReceipts.length === 0 ? (
                <EmptyState Icon={ReceiptText} title="אין עדיין קבלות" hint="קבלות שתפיקו יופיעו כאן" />
              ) : (
                <ul className="divide-y divide-border rounded-2xl border border-border bg-white px-4">
                  {d.recentReceipts.map((r) => (
                    <li key={r.id} className="flex items-center justify-between gap-3 py-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{r.clientName}</p>
                        <p className="text-xs text-foreground/60">
                          <span className="tnum" dir="ltr">{r.receiptNumber}</span>
                          {" · "}
                          <span className="tnum" dir="ltr">{r.issueDate}</span>
                        </p>
                      </div>
                      <span className="tnum shrink-0 font-semibold" dir="ltr">{formatILS(r.amount)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <div className="mb-1 flex items-center justify-between">
                <h2 className="text-lg font-semibold">הוצאות אחרונות</h2>
                <Link href="/expenses" className="flex min-h-12 items-center text-sm font-medium text-primary">
                  הצג הכל
                </Link>
              </div>
              {d.recentExpenses.length === 0 ? (
                <EmptyState Icon={Wallet} title="אין עדיין הוצאות" hint="צלמו קבלה על הוצאה בצ'אט" />
              ) : (
                <ul className="divide-y divide-border rounded-2xl border border-border bg-white px-4">
                  {d.recentExpenses.map((e) => (
                    <li key={e.id} className="flex items-center justify-between gap-3 py-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{e.supplierName ?? "ללא ספק"}</p>
                        {e.status === "needs_review" && (
                          <p className="text-xs text-amber-600">ממתינה לבדיקה</p>
                        )}
                      </div>
                      <span className="tnum shrink-0 font-semibold" dir="ltr">
                        {e.amount != null ? formatILS(e.amount) : "—"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}

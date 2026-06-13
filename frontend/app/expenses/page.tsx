"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import type { Business, Expense, ExpenseStatus } from "@/lib/types";
import ExpenseList from "@/components/ExpenseList";
import ExpenseReviewSheet from "@/components/ExpenseReviewSheet";
import UploadExpenseButton from "@/components/UploadExpenseButton";

type Tab = ExpenseStatus | "all";

const TABS: { value: Tab; label: string }[] = [
  { value: "needs_review", label: "לבדיקה" },
  { value: "approved", label: "מאושרות" },
  { value: "all", label: "הכל" },
];

export default function ExpensesPage() {
  const { user, loading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [tab, setTab] = useState<Tab>("needs_review");
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [reviewing, setReviewing] = useState<Expense | null>(null);

  useEffect(() => { if (user) api<Business>("/businesses/me").then(setBusiness); }, [user]);

  const refresh = useCallback(async () => {
    if (!business) return;
    try {
      setExpenses(await api<Expense[]>(`/businesses/${business.id}/expenses`));
    } finally {
      setListLoading(false);
    }
  }, [business]);
  useEffect(() => { refresh(); }, [refresh]);

  const needsReviewCount = expenses.filter((e) => e.status === "needs_review").length;
  const visible = tab === "all" ? expenses : expenses.filter((e) => e.status === tab);

  return (
    <div className="px-4 pb-6 pt-4">
      <h1 className="mb-4 text-2xl font-semibold">הוצאות</h1>
      {business && (
        <div className="mb-4">
          <UploadExpenseButton businessId={business.id} onUploaded={(e) => { refresh(); setReviewing(e); }} />
        </div>
      )}
      <div role="tablist" aria-label="סינון הוצאות" className="mb-4 flex rounded-xl border border-border bg-muted p-1">
        {TABS.map((t) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => setTab(t.value)}
            className={`flex min-h-12 flex-1 items-center justify-center gap-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === t.value ? "bg-white text-foreground shadow-sm" : "text-foreground/60"
            }`}
          >
            {t.label}
            {t.value === "needs_review" && needsReviewCount > 0 && (
              <span dir="ltr" className="tnum rounded-full bg-destructive px-1.5 text-xs font-semibold text-white">
                {needsReviewCount}
              </span>
            )}
          </button>
        ))}
      </div>
      <ExpenseList expenses={visible} loading={loading || !business || listLoading} onSelect={setReviewing} />
      {business && reviewing && (
        <ExpenseReviewSheet
          businessId={business.id}
          expense={reviewing}
          onClose={() => setReviewing(null)}
          onSaved={() => { setReviewing(null); refresh(); }}
        />
      )}
    </div>
  );
}

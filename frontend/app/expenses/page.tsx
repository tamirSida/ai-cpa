"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useT } from "@/lib/i18n";
import type { Business, Expense, ExpenseStatus } from "@/lib/types";
import ExpenseList from "@/components/ExpenseList";
import ExpenseReviewSheet from "@/components/ExpenseReviewSheet";
import UploadExpenseButton from "@/components/UploadExpenseButton";

type Tab = ExpenseStatus | "all";

const TABS: { value: Tab; labelKey: string }[] = [
  { value: "needs_review", labelKey: "expenses.tabNeedsReview" },
  { value: "approved", labelKey: "expenses.tabApproved" },
  { value: "all", labelKey: "expenses.tabAll" },
];

export default function ExpensesPage() {
  const t = useT();
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
      <h1 className="mb-4 text-2xl font-semibold">{t("expenses.title")}</h1>
      {business && (
        <div className="mb-4">
          <UploadExpenseButton businessId={business.id} onUploaded={(e) => { refresh(); setReviewing(e); }} />
        </div>
      )}
      <div role="tablist" aria-label={t("expenses.filterLabel")} className="mb-4 flex rounded-xl border border-border bg-muted p-1">
        {TABS.map((tab2) => (
          <button
            key={tab2.value}
            role="tab"
            aria-selected={tab === tab2.value}
            onClick={() => setTab(tab2.value)}
            className={`flex min-h-12 flex-1 items-center justify-center gap-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === tab2.value ? "bg-white text-foreground shadow-sm" : "text-foreground/60"
            }`}
          >
            {t(tab2.labelKey)}
            {tab2.value === "needs_review" && needsReviewCount > 0 && (
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

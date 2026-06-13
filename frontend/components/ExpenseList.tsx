"use client";

import { Wallet } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import { formatILS } from "@/lib/format";
import { CATEGORY_LABELS, EXPENSE_STATUS_LABELS } from "@/lib/labels";
import type { Expense, ExpenseStatus } from "@/lib/types";

const STATUS_BADGE: Record<ExpenseStatus, string> = {
  needs_review: "bg-amber-100 text-amber-800",
  approved: "bg-accent/10 text-accent",
  rejected: "bg-destructive/10 text-destructive",
};

function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("he-IL");
}

export default function ExpenseList({ expenses, loading, onSelect }:
  { expenses: Expense[]; loading: boolean; onSelect: (e: Expense) => void }) {
  if (loading) {
    return (
      <div className="flex flex-col gap-3" aria-hidden>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex animate-pulse items-center gap-3 rounded-2xl border border-border bg-white p-4">
            <div className="size-12 rounded-lg bg-muted" />
            <div className="flex-1">
              <div className="h-4 w-2/5 rounded bg-muted" />
              <div className="mt-2 h-3 w-3/5 rounded bg-muted" />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (expenses.length === 0) {
    return (
      <EmptyState
        Icon={Wallet}
        title="אין הוצאות להצגה"
        hint="צלמו קבלה למעלה או כתבו בצ'אט: תוסיף הוצאה של 120 שקל על Canva"
      />
    );
  }
  return (
    <>
      <ul className="flex flex-col gap-3 md:hidden">
        {expenses.map((e) => (
          <li key={e.id}>
            <button
              onClick={() => onSelect(e)}
              className="flex min-h-12 w-full items-center gap-3 rounded-2xl border border-border bg-white p-4 text-start transition-transform duration-150 active:scale-[0.98]"
            >
              {e.imageUrl ? (
                <img src={e.imageUrl} alt="" className="size-12 shrink-0 rounded-lg object-cover" />
              ) : (
                <span className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <Wallet size={20} className="text-foreground/40" aria-hidden />
                </span>
              )}
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{e.supplierName ?? "ספק לא ידוע"}</span>
                  <span className="tnum shrink-0 font-semibold" dir="ltr">
                    {e.amount !== null ? formatILS(e.amount) : "—"}
                  </span>
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-foreground/60">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[e.status]}`}>
                    {EXPENSE_STATUS_LABELS[e.status]}
                  </span>
                  <span>{e.category ? CATEGORY_LABELS[e.category] : "ללא קטגוריה"}</span>
                  {e.expenseDate && <span className="tnum" dir="ltr">{formatDate(e.expenseDate)}</span>}
                </span>
                {e.extractionConfidence !== null && e.extractionConfidence < 0.7 && (
                  <span className="mt-1 block text-xs text-destructive">זיהוי בביטחון נמוך — כדאי לבדוק את הפרטים</span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <div className="hidden overflow-hidden rounded-2xl border border-border bg-white md:block">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/50">
            <tr>
              <th className="p-3 text-start font-medium">תאריך</th>
              <th className="p-3 text-start font-medium">ספק</th>
              <th className="p-3 text-start font-medium">קטגוריה</th>
              <th className="p-3 text-start font-medium">סכום</th>
              <th className="p-3 text-start font-medium">סטטוס</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((e) => (
              <tr
                key={e.id}
                onClick={() => onSelect(e)}
                className="cursor-pointer border-b border-border last:border-b-0 hover:bg-muted/50"
              >
                <td className="p-3">
                  <span className="tnum" dir="ltr">{e.expenseDate ? formatDate(e.expenseDate) : "—"}</span>
                </td>
                <td className="p-3">
                  <span className="flex items-center gap-2">
                    {e.imageUrl && <img src={e.imageUrl} alt="" className="size-8 rounded object-cover" />}
                    {e.supplierName ?? "ספק לא ידוע"}
                  </span>
                </td>
                <td className="p-3">{e.category ? CATEGORY_LABELS[e.category] : "—"}</td>
                <td className="p-3">
                  <span className="tnum" dir="ltr">{e.amount !== null ? formatILS(e.amount) : "—"}</span>
                </td>
                <td className="p-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[e.status]}`}>
                    {EXPENSE_STATUS_LABELS[e.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

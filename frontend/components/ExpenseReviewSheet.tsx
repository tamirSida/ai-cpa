"use client";

import { useState, type ChangeEvent } from "react";
import { Ban, Check, Loader2 } from "lucide-react";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { CATEGORY_LABELS, EXPENSE_STATUS_LABELS } from "@/lib/labels";
import type { Expense, ExpenseCategory } from "@/lib/types";

const inputClass =
  "min-h-12 w-full rounded-xl border border-border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-muted disabled:text-foreground/60";

export default function ExpenseReviewSheet({ businessId, expense, onClose, onSaved }:
  { businessId: string; expense: Expense; onClose: () => void; onSaved: () => void }) {
  const editable = expense.status === "needs_review";
  const [form, setForm] = useState({
    supplierName: expense.supplierName ?? "",
    amount: expense.amount?.toString() ?? "",
    expenseDate: expense.expenseDate ?? "",
    category: expense.category ?? "",
    description: expense.description ?? "",
    businessUsePercent: expense.businessUsePercent.toString(),
  });
  const [amountError, setAmountError] = useState("");
  const [pctError, setPctError] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<"approve" | "reject" | null>(null);

  const set = (k: keyof typeof form) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });

  function validateAmount(): boolean {
    if (!form.amount || Number(form.amount) <= 0) {
      setAmountError("יש להזין סכום גדול מ-0");
      return false;
    }
    setAmountError("");
    return true;
  }

  function validatePct(): boolean {
    const n = Number(form.businessUsePercent);
    if (Number.isNaN(n) || n < 0 || n > 100) {
      setPctError("אחוז שימוש עסקי חייב להיות בין 0 ל-100");
      return false;
    }
    setPctError("");
    return true;
  }

  async function approve() {
    if (!validateAmount() || !validatePct()) return;
    setPending("approve");
    setError("");
    try {
      const base = `/businesses/${businessId}/expenses/${expense.id}`;
      await api<Expense>(base, {
        method: "PATCH",
        body: JSON.stringify({
          supplierName: form.supplierName || undefined,
          amount: Number(form.amount),
          expenseDate: form.expenseDate || undefined,
          category: form.category || undefined,
          description: form.description || undefined,
          businessUsePercent: Number(form.businessUsePercent),
        }),
      });
      await api<Expense>(`${base}/approve`, { method: "POST" });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "שגיאה בשמירה");
      setPending(null);
    }
  }

  async function reject() {
    setPending("reject");
    setError("");
    try {
      await api<Expense>(`/businesses/${businessId}/expenses/${expense.id}/reject`, { method: "POST" });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "שגיאה בדחייה");
      setPending(null);
    }
  }

  return (
    <Sheet open onClose={onClose} title={editable ? "בדיקת הוצאה" : "פרטי הוצאה"}>
      {expense.imageUrl && (
        <img src={expense.imageUrl} alt="צילום ההוצאה" className="mx-auto mb-4 max-h-48 w-full rounded-xl object-contain" />
      )}
      {!editable && (
        <p className="mb-3 text-sm text-foreground/60">סטטוס: {EXPENSE_STATUS_LABELS[expense.status]}</p>
      )}
      <div className="flex flex-col gap-3">
        <label className="block">
          <span className="mb-1 block text-sm font-medium">ספק</span>
          <input value={form.supplierName} onChange={set("supplierName")} disabled={!editable} className={inputClass} />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">סכום (₪)</span>
          <input
            type="number" inputMode="numeric" min="0" step="0.01" dir="ltr"
            value={form.amount} onChange={set("amount")} onBlur={validateAmount}
            disabled={!editable} className={`${inputClass} tnum`}
          />
          {amountError && <p className="mt-1 text-sm text-destructive">{amountError}</p>}
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">תאריך</span>
          <input
            type="date" dir="ltr" value={form.expenseDate} onChange={set("expenseDate")}
            disabled={!editable} className={`${inputClass} tnum`}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">קטגוריה</span>
          <select value={form.category} onChange={set("category")} disabled={!editable} className={inputClass}>
            <option value="">ללא קטגוריה</option>
            {(Object.keys(CATEGORY_LABELS) as ExpenseCategory[]).map((c) => (
              <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">תיאור</span>
          <input value={form.description} onChange={set("description")} disabled={!editable} className={inputClass} />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">אחוז שימוש עסקי</span>
          <input
            type="number" inputMode="numeric" min="0" max="100" dir="ltr"
            value={form.businessUsePercent} onChange={set("businessUsePercent")} onBlur={validatePct}
            disabled={!editable} className={`${inputClass} tnum`}
          />
          {pctError && <p className="mt-1 text-sm text-destructive">{pctError}</p>}
        </label>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {editable && (
          <div className="mt-1 flex gap-2">
            <button
              onClick={approve}
              disabled={pending !== null}
              className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
            >
              {pending === "approve" ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <Check size={20} aria-hidden />}
              אישור
            </button>
            <button
              onClick={reject}
              disabled={pending !== null}
              className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
            >
              {pending === "reject" ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <Ban size={20} aria-hidden />}
              דחייה
            </button>
          </div>
        )}
      </div>
    </Sheet>
  );
}

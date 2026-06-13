"use client";

import { useState } from "react";
import { Check, Loader2, X } from "lucide-react";
import { formatILS } from "@/lib/format";
import type { ActionView } from "@/lib/types";

const TITLES: Record<string, string> = {
  CREATE_RECEIPT: "אישור יצירת קבלה",
  CREATE_CONTACT: "אישור יצירת איש קשר",
  CREATE_EXPENSE: "אישור הוספת הוצאה",
  GENERATE_ANNUAL_REPORT: "אישור הפקת דוח שנתי",
};

const PAYMENT_HE: Record<string, string> = {
  cash: "מזומן",
  bank_transfer: "העברה בנקאית",
  bit: "ביט",
  paybox: "פייבוקס",
  credit_card: "כרטיס אשראי",
  check: "צ'ק",
  other: "אחר",
  unknown: "לא צוין",
};

const CATEGORY_HE: Record<string, string> = {
  software: "תוכנה",
  equipment: "ציוד",
  travel: "נסיעות",
  office: "משרד",
  marketing: "שיווק",
  professional_services: "שירותים מקצועיים",
  meals: "אוכל",
  parking: "חניה",
  other: "אחר",
};

type SummaryRow = { label: string; value: string; ltr?: boolean };

function summaryRows(action: ActionView): SummaryRow[] {
  const p = action.payload;
  const rows: SummaryRow[] = [];
  if (action.type === "CREATE_RECEIPT") {
    if (typeof p.client_name === "string") rows.push({ label: "לקוח", value: p.client_name });
    if (typeof p.amount === "number") rows.push({ label: "סכום", value: formatILS(p.amount), ltr: true });
    if (typeof p.description === "string") rows.push({ label: "תיאור", value: p.description });
    const pm = typeof p.payment_method === "string" ? p.payment_method : "unknown";
    rows.push({ label: "אמצעי תשלום", value: PAYMENT_HE[pm] ?? "לא צוין" });
  } else if (action.type === "CREATE_CONTACT") {
    if (typeof p.name === "string") rows.push({ label: "שם", value: p.name });
    if (typeof p.phone === "string" && p.phone) rows.push({ label: "טלפון", value: p.phone, ltr: true });
    if (typeof p.email === "string" && p.email) rows.push({ label: "אימייל", value: p.email, ltr: true });
  } else if (action.type === "CREATE_EXPENSE") {
    if (typeof p.supplier_name === "string" && p.supplier_name)
      rows.push({ label: "ספק", value: p.supplier_name });
    if (typeof p.amount === "number") rows.push({ label: "סכום", value: formatILS(p.amount), ltr: true });
    if (typeof p.category === "string" && p.category)
      rows.push({ label: "קטגוריה", value: CATEGORY_HE[p.category] ?? p.category });
    if (typeof p.description === "string" && p.description)
      rows.push({ label: "תיאור", value: p.description });
  } else if (action.type === "GENERATE_ANNUAL_REPORT") {
    if (typeof p.year === "number") rows.push({ label: "שנה", value: String(p.year), ltr: true });
  }
  return rows;
}

type ConfirmActionCardProps = {
  action: ActionView;
  onConfirm: () => Promise<void>;
  onCancel: () => Promise<void>;
};

export default function ConfirmActionCard({ action, onConfirm, onCancel }: ConfirmActionCardProps) {
  const [executing, setExecuting] = useState<"confirm" | "cancel" | null>(null);

  const run = async (kind: "confirm" | "cancel", fn: () => Promise<void>) => {
    if (executing) return;
    setExecuting(kind);
    try {
      await fn();
    } finally {
      setExecuting(null);
    }
  };

  return (
    <div className="me-auto w-full max-w-[85%] rounded-2xl border border-border bg-white p-4">
      <p className="mb-3 text-sm font-semibold text-foreground/70">
        {TITLES[action.type] ?? "אישור פעולה"}
      </p>
      <dl className="mb-4 space-y-2">
        {summaryRows(action).map(({ label, value, ltr }) => (
          <div key={label} className="flex items-baseline justify-between gap-3">
            <dt className="text-sm text-foreground/60">{label}</dt>
            <dd className={`font-medium ${ltr ? "tnum" : ""}`} dir={ltr ? "ltr" : undefined}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="flex gap-2">
        <button
          onClick={() => run("confirm", onConfirm)}
          disabled={executing !== null}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {executing === "confirm" ? (
            <Loader2 size={18} className="animate-spin" aria-hidden />
          ) : (
            <Check size={18} aria-hidden />
          )}
          אישור
        </button>
        <button
          onClick={() => run("cancel", onCancel)}
          disabled={executing !== null}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-border font-medium text-foreground transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {executing === "cancel" ? (
            <Loader2 size={18} className="animate-spin" aria-hidden />
          ) : (
            <X size={18} aria-hidden />
          )}
          ביטול
        </button>
      </div>
    </div>
  );
}

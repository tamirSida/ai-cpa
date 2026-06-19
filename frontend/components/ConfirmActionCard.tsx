"use client";

import { useState } from "react";
import { Check, Loader2, X } from "lucide-react";
import { formatILS } from "@/lib/format";
import { useT } from "@/lib/i18n";
import type { ActionView } from "@/lib/types";

type T = ReturnType<typeof useT>;

const TITLE_KEYS: Record<string, string> = {
  CREATE_RECEIPT: "chat.titleCreateReceipt",
  CREATE_CONTACT: "chat.titleCreateContact",
  CREATE_EXPENSE: "chat.titleCreateExpense",
  GENERATE_ANNUAL_REPORT: "chat.titleAnnualReport",
};

const PAYMENT_KEYS: Record<string, string> = {
  cash: "chat.paymentCash",
  bank_transfer: "chat.paymentBankTransfer",
  bit: "chat.paymentBit",
  paybox: "chat.paymentPaybox",
  credit_card: "chat.paymentCreditCard",
  check: "chat.paymentCheck",
  other: "chat.paymentOther",
  unknown: "chat.paymentUnknown",
};

type SummaryRow = { label: string; value: string; ltr?: boolean };

function summaryRows(action: ActionView, t: T): SummaryRow[] {
  const p = action.payload;
  const rows: SummaryRow[] = [];
  if (action.type === "CREATE_RECEIPT") {
    if (typeof p.client_name === "string") rows.push({ label: t("chat.fieldClient"), value: p.client_name });
    if (typeof p.amount === "number") rows.push({ label: t("chat.fieldAmount"), value: formatILS(p.amount), ltr: true });
    if (typeof p.description === "string") rows.push({ label: t("chat.fieldDescription"), value: p.description });
    const pm = typeof p.payment_method === "string" ? p.payment_method : "unknown";
    rows.push({ label: t("chat.fieldPaymentMethod"), value: t(PAYMENT_KEYS[pm] ?? "chat.paymentUnknown") });
  } else if (action.type === "CREATE_CONTACT") {
    if (typeof p.name === "string") rows.push({ label: t("chat.fieldName"), value: p.name });
    if (typeof p.phone === "string" && p.phone) rows.push({ label: t("chat.fieldPhone"), value: p.phone, ltr: true });
    if (typeof p.email === "string" && p.email) rows.push({ label: t("chat.fieldEmail"), value: p.email, ltr: true });
  } else if (action.type === "CREATE_EXPENSE") {
    if (typeof p.supplier_name === "string" && p.supplier_name)
      rows.push({ label: t("chat.fieldSupplier"), value: p.supplier_name });
    if (typeof p.amount === "number") rows.push({ label: t("chat.fieldAmount"), value: formatILS(p.amount), ltr: true });
    if (typeof p.category === "string" && p.category)
      rows.push({ label: t("chat.fieldCategory"), value: t(`category.${p.category}`) });
    if (typeof p.description === "string" && p.description)
      rows.push({ label: t("chat.fieldDescription"), value: p.description });
  } else if (action.type === "GENERATE_ANNUAL_REPORT") {
    if (typeof p.year === "number") rows.push({ label: t("chat.fieldYear"), value: String(p.year), ltr: true });
  }
  return rows;
}

type ConfirmActionCardProps = {
  action: ActionView;
  onConfirm: () => Promise<void>;
  onCancel: () => Promise<void>;
};

export default function ConfirmActionCard({ action, onConfirm, onCancel }: ConfirmActionCardProps) {
  const t = useT();
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
        {t(TITLE_KEYS[action.type] ?? "chat.titleGeneric")}
      </p>
      <dl className="mb-4 space-y-2">
        {summaryRows(action, t).map(({ label, value, ltr }) => (
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
          {t("common.confirm")}
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
          {t("common.cancel")}
        </button>
      </div>
    </div>
  );
}

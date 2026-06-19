"use client";
import { useEffect, useState } from "react";
import { Ban, Check, Download, Loader2, Plus, ReceiptText, Share2 } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import ReceiptList, { ReceiptStatusBadge } from "@/components/ReceiptList";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { formatILS } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { Business, Client, PaymentMethod, Receipt } from "@/lib/types";

const PAYMENT_METHODS: PaymentMethod[] = ["cash", "bank_transfer", "bit", "paybox", "credit_card", "check", "other", "unknown"];

const EMPTY_FORM = { clientId: "", clientName: "", amount: "", description: "", paymentMethod: "unknown" as PaymentMethod };

type FieldErrors = { clientName?: string; amount?: string; description?: string };

function inputClass(invalid: boolean): string {
  return `min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
    invalid ? "border-destructive" : "border-border"
  }`;
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border py-2 last:border-b-0">
      <dt className="shrink-0 text-sm text-foreground/60">{label}</dt>
      <dd className="text-end text-sm font-medium">{children}</dd>
    </div>
  );
}

export default function ReceiptsPage() {
  const { t, tError } = useI18n();
  const { user, loading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [createError, setCreateError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Receipt | null>(null);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    api<Business>("/businesses/me")
      .then(async (b) => {
        setBusiness(b);
        const [cs, rs] = await Promise.all([
          api<Client[]>(`/businesses/${b.id}/clients`),
          api<Receipt[]>(`/businesses/${b.id}/receipts`),
        ]);
        setClients(cs);
        setReceipts(rs);
        setLoaded(true);
      })
      .catch((e) => setError(tError(e)));
  }, [loading, user]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setFieldErrors({});
    setCreateError(null);
    setCreateOpen(true);
  }

  function openDetails(receipt: Receipt) {
    setCancelMode(false);
    setCancelReason("");
    setCancelError(null);
    setShareCopied(false);
    setSelected(receipt);
  }

  function validateField(field: keyof FieldErrors) {
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      if (field === "clientName" && !form.clientId && !form.clientName.trim()) next.clientName = t("receipts.errClientNameRequired");
      if (field === "amount" && !(Number(form.amount) > 0)) next.amount = t("receipts.errAmountPositive");
      if (field === "description" && !form.description.trim()) next.description = t("receipts.errDescriptionRequired");
      return next;
    });
  }

  async function createAndIssue(e: React.FormEvent) {
    e.preventDefault();
    if (!business) return;
    const errors: FieldErrors = {};
    if (!form.clientId && !form.clientName.trim()) errors.clientName = t("receipts.errClientNameRequired");
    if (!(Number(form.amount) > 0)) errors.amount = t("receipts.errAmountPositive");
    if (!form.description.trim()) errors.description = t("receipts.errDescriptionRequired");
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setBusy(true);
    setCreateError(null);
    try {
      const draft = await api<Receipt>(`/businesses/${business.id}/receipts/draft`, {
        method: "POST",
        body: JSON.stringify({
          clientId: form.clientId || undefined,
          clientName: form.clientId ? undefined : form.clientName.trim(),
          amount: Number(form.amount),
          description: form.description.trim(),
          paymentMethod: form.paymentMethod,
        }),
      });
      const issued = await api<Receipt>(`/businesses/${business.id}/receipts/${draft.id}/issue`, { method: "POST" });
      setReceipts((rs) => [issued, ...rs]);
      setCreateOpen(false);
    } catch (err) {
      setCreateError(tError(err));
    } finally {
      setBusy(false);
    }
  }

  async function shareReceipt(receipt: Receipt) {
    if (!receipt.pdfUrl) return;
    if (navigator.share) {
      try {
        await navigator.share({ url: receipt.pdfUrl });
      } catch {
        // user dismissed the OS share sheet — nothing to do
      }
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(receipt.pdfUrl);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    } else {
      window.prompt(t("receipts.copyLinkPrompt"), receipt.pdfUrl);
    }
  }

  async function confirmCancel() {
    if (!business || !selected) return;
    if (!cancelReason.trim()) {
      setCancelError(t("receipts.errCancelReasonRequired"));
      return;
    }
    setCancelBusy(true);
    setCancelError(null);
    try {
      const cancelled = await api<Receipt>(`/businesses/${business.id}/receipts/${selected.id}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason: cancelReason.trim() }),
      });
      setReceipts((rs) => rs.map((r) => (r.id === cancelled.id ? cancelled : r)));
      setSelected(cancelled);
      setCancelMode(false);
    } catch (err) {
      setCancelError(tError(err));
    } finally {
      setCancelBusy(false);
    }
  }

  return (
    <div className="px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("receipts.title")}</h1>
        <button
          onClick={openCreate}
          className="flex min-h-12 items-center gap-1.5 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
        >
          <Plus size={20} aria-hidden />
          {t("receipts.newReceipt")}
        </button>
      </div>
      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      {loading || !loaded ? (
        <div className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-white p-4">
              <div className="h-4 w-20 rounded bg-muted" />
              <div className="mt-3 h-5 w-36 rounded bg-muted" />
              <div className="mt-2 h-4 w-28 rounded bg-muted" />
            </div>
          ))}
        </div>
      ) : receipts.length === 0 ? (
        <EmptyState
          Icon={ReceiptText}
          title={t("receipts.emptyTitle")}
          hint={t("receipts.emptyHint")}
        />
      ) : (
        <ReceiptList receipts={receipts} onSelect={openDetails} />
      )}

      <Sheet open={createOpen} onClose={() => setCreateOpen(false)} title={t("receipts.newReceipt")}>
        <form onSubmit={createAndIssue} noValidate className="flex flex-col gap-4">
          <div>
            <label htmlFor="receipt-client" className="mb-1 block text-sm font-medium">{t("receipts.clientLabel")}</label>
            <select
              id="receipt-client"
              value={form.clientId}
              onChange={(e) => setForm({ ...form, clientId: e.target.value })}
              className={inputClass(false)}
            >
              <option value="">{t("receipts.clientFreeText")}</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          {!form.clientId && (
            <div>
              <label htmlFor="receipt-client-name" className="mb-1 block text-sm font-medium">{t("receipts.clientNameLabel")}</label>
              <input
                id="receipt-client-name"
                value={form.clientName}
                aria-invalid={Boolean(fieldErrors.clientName)}
                onChange={(e) => setForm({ ...form, clientName: e.target.value })}
                onBlur={() => validateField("clientName")}
                className={inputClass(Boolean(fieldErrors.clientName))}
              />
              {fieldErrors.clientName && <p className="mt-1 text-sm text-destructive">{fieldErrors.clientName}</p>}
            </div>
          )}
          <div>
            <label htmlFor="receipt-amount" className="mb-1 block text-sm font-medium">{t("receipts.amountLabel")}</label>
            <input
              id="receipt-amount"
              type="number"
              step="0.01"
              min="0.01"
              inputMode="numeric"
              dir="ltr"
              value={form.amount}
              aria-invalid={Boolean(fieldErrors.amount)}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              onBlur={() => validateField("amount")}
              className={inputClass(Boolean(fieldErrors.amount))}
            />
            {fieldErrors.amount && <p className="mt-1 text-sm text-destructive">{fieldErrors.amount}</p>}
          </div>
          <div>
            <label htmlFor="receipt-description" className="mb-1 block text-sm font-medium">{t("receipts.descriptionLabel")}</label>
            <input
              id="receipt-description"
              value={form.description}
              aria-invalid={Boolean(fieldErrors.description)}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              onBlur={() => validateField("description")}
              className={inputClass(Boolean(fieldErrors.description))}
            />
            {fieldErrors.description && <p className="mt-1 text-sm text-destructive">{fieldErrors.description}</p>}
          </div>
          <div>
            <label htmlFor="receipt-method" className="mb-1 block text-sm font-medium">{t("receipts.paymentMethodLabel")}</label>
            <select
              id="receipt-method"
              value={form.paymentMethod}
              onChange={(e) => setForm({ ...form, paymentMethod: e.target.value as PaymentMethod })}
              className={inputClass(false)}
            >
              {PAYMENT_METHODS.map((value) => (
                <option key={value} value={value}>{t(`receipts.payment.${value}`)}</option>
              ))}
            </select>
          </div>
          {createError && <p className="text-sm text-destructive">{createError}</p>}
          <button
            type="submit"
            disabled={busy}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {busy && <Loader2 size={20} className="animate-spin" aria-hidden />}
            {t("receipts.createAndIssue")}
          </button>
        </form>
      </Sheet>

      <Sheet open={selected !== null} onClose={() => setSelected(null)} title={t("receipts.detailsTitle")}>
        {selected && (
          <div className="flex flex-col gap-4">
            <dl>
              <DetailRow label={t("receipts.detailNumber")}><span className="tnum" dir="ltr">{selected.receiptNumber ?? "—"}</span></DetailRow>
              <DetailRow label={t("receipts.detailStatus")}><ReceiptStatusBadge status={selected.status} /></DetailRow>
              <DetailRow label={t("receipts.detailClient")}>{selected.clientSnapshot.name}</DetailRow>
              <DetailRow label={t("receipts.detailDate")}><span dir="ltr">{selected.issueDate}</span></DetailRow>
              <DetailRow label={t("receipts.detailAmount")}><span className="tnum" dir="ltr">{formatILS(selected.amount)}</span></DetailRow>
              <DetailRow label={t("receipts.detailPaymentMethod")}>{t(`receipts.payment.${selected.paymentMethod}`)}</DetailRow>
              {selected.checkDetails && (
                <DetailRow label={t("receipts.detailCheckDetails")}>
                  {selected.checkDetails.bank} · {t("receipts.checkNumber")} <span dir="ltr" className="tnum">{selected.checkDetails.number}</span> · {t("receipts.checkBranch")} <span dir="ltr" className="tnum">{selected.checkDetails.branch}</span> · {t("receipts.checkDueDate")} <span dir="ltr" className="tnum">{selected.checkDetails.dueDate}</span>
                </DetailRow>
              )}
              <DetailRow label={t("receipts.detailDescription")}>{selected.description}</DetailRow>
              {selected.status === "cancelled" && selected.cancellationReason && (
                <DetailRow label={t("receipts.detailCancellationReason")}>{selected.cancellationReason}</DetailRow>
              )}
            </dl>
            {!cancelMode ? (
              <div className="flex flex-col gap-2">
                {selected.pdfUrl ? (
                  <>
                    <a
                      href={selected.pdfUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
                    >
                      <Download size={20} aria-hidden />
                      {t("receipts.downloadPdf")}
                    </a>
                    <button
                      onClick={() => void shareReceipt(selected)}
                      className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-border px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98]"
                    >
                      {shareCopied ? <Check size={20} aria-hidden /> : <Share2 size={20} aria-hidden />}
                      {shareCopied ? t("receipts.linkCopied") : t("receipts.share")}
                    </button>
                  </>
                ) : (
                  <p className="text-sm text-foreground/60">{t("receipts.noPdf")}</p>
                )}
                {selected.status === "issued" && (
                  <button
                    onClick={() => setCancelMode(true)}
                    className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-destructive px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98]"
                  >
                    <Ban size={20} aria-hidden />
                    {t("receipts.cancelReceipt")}
                  </button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3 rounded-2xl border border-destructive/40 bg-destructive/5 p-4">
                <p className="text-sm font-medium text-destructive">
                  {t("receipts.cancelWarning")}
                </p>
                <div>
                  <label htmlFor="cancel-reason" className="mb-1 block text-sm font-medium">{t("receipts.cancelReasonLabel")}</label>
                  <input
                    id="cancel-reason"
                    value={cancelReason}
                    aria-invalid={Boolean(cancelError)}
                    onChange={(e) => {
                      setCancelReason(e.target.value);
                      if (cancelError) setCancelError(null);
                    }}
                    onBlur={() => setCancelError(cancelReason.trim() ? null : t("receipts.errCancelReasonRequired"))}
                    className={inputClass(Boolean(cancelError))}
                  />
                  {cancelError && <p className="mt-1 text-sm text-destructive">{cancelError}</p>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => void confirmCancel()}
                    disabled={cancelBusy}
                    className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-destructive px-5 font-medium text-white transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                  >
                    {cancelBusy && <Loader2 size={20} className="animate-spin" aria-hidden />}
                    {t("receipts.confirmCancel")}
                  </button>
                  <button
                    onClick={() => setCancelMode(false)}
                    disabled={cancelBusy}
                    className="min-h-12 flex-1 rounded-xl border border-border px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                  >
                    {t("common.back")}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </Sheet>
    </div>
  );
}

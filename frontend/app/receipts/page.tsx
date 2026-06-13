"use client";
import { useEffect, useState } from "react";
import { Ban, Check, Download, Loader2, Plus, ReceiptText, Share2 } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import ReceiptList, { ReceiptStatusBadge } from "@/components/ReceiptList";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { formatILS } from "@/lib/format";
import type { Business, Client, PaymentMethod, Receipt } from "@/lib/types";
import { PAYMENT_LABELS } from "@/lib/types";

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
  const { user, loading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
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
      .catch((e) => setError((e as Error).message));
  }, [loading, user]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setFieldErrors({});
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
      if (field === "clientName" && !form.clientId && !form.clientName.trim()) next.clientName = "נדרש שם לקוח";
      if (field === "amount" && !(Number(form.amount) > 0)) next.amount = "הסכום חייב להיות גדול מ-0";
      if (field === "description" && !form.description.trim()) next.description = "חסר תיאור לקבלה";
      return next;
    });
  }

  async function createAndIssue(e: React.FormEvent) {
    e.preventDefault();
    if (!business) return;
    const errors: FieldErrors = {};
    if (!form.clientId && !form.clientName.trim()) errors.clientName = "נדרש שם לקוח";
    if (!(Number(form.amount) > 0)) errors.amount = "הסכום חייב להיות גדול מ-0";
    if (!form.description.trim()) errors.description = "חסר תיאור לקבלה";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setBusy(true);
    setError(null);
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
      setError((err as Error).message);
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
    } else {
      await navigator.clipboard.writeText(receipt.pdfUrl);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    }
  }

  async function confirmCancel() {
    if (!business || !selected) return;
    if (!cancelReason.trim()) {
      setCancelError("נדרשת סיבת ביטול");
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
      setCancelError((err as Error).message);
    } finally {
      setCancelBusy(false);
    }
  }

  return (
    <div className="px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">קבלות</h1>
        <button
          onClick={openCreate}
          className="flex min-h-12 items-center gap-1.5 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
        >
          <Plus size={20} aria-hidden />
          קבלה חדשה
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
          title="אין עדיין קבלות"
          hint="הנפיקו קבלה ראשונה בכפתור למעלה, או כתבו בצ׳אט: קיבלתי 2,800 מנועה על עיצוב לוגו"
        />
      ) : (
        <ReceiptList receipts={receipts} onSelect={openDetails} />
      )}

      <Sheet open={createOpen} onClose={() => setCreateOpen(false)} title="קבלה חדשה">
        <form onSubmit={createAndIssue} noValidate className="flex flex-col gap-4">
          <div>
            <label htmlFor="receipt-client" className="mb-1 block text-sm font-medium">לקוח</label>
            <select
              id="receipt-client"
              value={form.clientId}
              onChange={(e) => setForm({ ...form, clientId: e.target.value })}
              className={inputClass(false)}
            >
              <option value="">אחר (שם חופשי)</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          {!form.clientId && (
            <div>
              <label htmlFor="receipt-client-name" className="mb-1 block text-sm font-medium">שם הלקוח *</label>
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
            <label htmlFor="receipt-amount" className="mb-1 block text-sm font-medium">סכום בש״ח *</label>
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
            <label htmlFor="receipt-description" className="mb-1 block text-sm font-medium">תיאור *</label>
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
            <label htmlFor="receipt-method" className="mb-1 block text-sm font-medium">אמצעי תשלום</label>
            <select
              id="receipt-method"
              value={form.paymentMethod}
              onChange={(e) => setForm({ ...form, paymentMethod: e.target.value as PaymentMethod })}
              className={inputClass(false)}
            >
              {(Object.entries(PAYMENT_LABELS) as [PaymentMethod, string][]).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {busy && <Loader2 size={20} className="animate-spin" aria-hidden />}
            צור והנפק קבלה
          </button>
        </form>
      </Sheet>

      <Sheet open={selected !== null} onClose={() => setSelected(null)} title="פרטי קבלה">
        {selected && (
          <div className="flex flex-col gap-4">
            <dl>
              <DetailRow label="מספר קבלה"><span className="tnum" dir="ltr">{selected.receiptNumber ?? "—"}</span></DetailRow>
              <DetailRow label="סטטוס"><ReceiptStatusBadge status={selected.status} /></DetailRow>
              <DetailRow label="לקוח">{selected.clientSnapshot.name}</DetailRow>
              <DetailRow label="תאריך"><span dir="ltr">{selected.issueDate}</span></DetailRow>
              <DetailRow label="סכום"><span className="tnum" dir="ltr">{formatILS(selected.amount)}</span></DetailRow>
              <DetailRow label="אמצעי תשלום">{PAYMENT_LABELS[selected.paymentMethod]}</DetailRow>
              <DetailRow label="תיאור">{selected.description}</DetailRow>
              {selected.status === "cancelled" && selected.cancellationReason && (
                <DetailRow label="סיבת ביטול">{selected.cancellationReason}</DetailRow>
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
                      הורדת PDF
                    </a>
                    <button
                      onClick={() => void shareReceipt(selected)}
                      className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-border px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98]"
                    >
                      {shareCopied ? <Check size={20} aria-hidden /> : <Share2 size={20} aria-hidden />}
                      {shareCopied ? "הקישור הועתק" : "שיתוף"}
                    </button>
                  </>
                ) : (
                  <p className="text-sm text-foreground/60">אין עדיין PDF לקבלה זו.</p>
                )}
                {selected.status === "issued" && (
                  <button
                    onClick={() => setCancelMode(true)}
                    className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-destructive px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98]"
                  >
                    <Ban size={20} aria-hidden />
                    ביטול קבלה
                  </button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3 rounded-2xl border border-destructive/40 bg-destructive/5 p-4">
                <p className="text-sm font-medium text-destructive">
                  ביטול קבלה הוא סופי ונרשם ביומן הפעולות. הקבלה תסומן כמבוטלת ולא תימחק.
                </p>
                <div>
                  <label htmlFor="cancel-reason" className="mb-1 block text-sm font-medium">סיבת הביטול *</label>
                  <input
                    id="cancel-reason"
                    value={cancelReason}
                    aria-invalid={Boolean(cancelError)}
                    onChange={(e) => {
                      setCancelReason(e.target.value);
                      if (cancelError) setCancelError(null);
                    }}
                    onBlur={() => setCancelError(cancelReason.trim() ? null : "נדרשת סיבת ביטול")}
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
                    אישור ביטול
                  </button>
                  <button
                    onClick={() => setCancelMode(false)}
                    disabled={cancelBusy}
                    className="min-h-12 flex-1 rounded-xl border border-border px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                  >
                    חזרה
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

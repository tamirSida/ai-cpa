"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/apiClient";
import { useBusiness } from "@/lib/business";
import { useI18n } from "@/lib/i18n";
import type { Business } from "@/lib/types";

type FieldKey =
  | "businessName"
  | "ownerName"
  | "businessIdNumber"
  | "address"
  | "phone"
  | "email"
  | "bankName"
  | "bankBranch"
  | "bankAccount"
  | "receiptPrefix";

type FieldDef = {
  key: FieldKey;
  labelKey: string;
  type: "text" | "tel" | "email";
  inputMode?: "numeric";
  ltr?: boolean;
  autoComplete?: string;
};

const FIELDS: FieldDef[] = [
  { key: "businessName", labelKey: "onboarding.field.businessName", type: "text", autoComplete: "organization" },
  { key: "ownerName", labelKey: "onboarding.field.ownerName", type: "text", autoComplete: "name" },
  { key: "businessIdNumber", labelKey: "onboarding.field.businessIdNumber", type: "text", inputMode: "numeric", ltr: true },
  { key: "address", labelKey: "onboarding.field.address", type: "text", autoComplete: "street-address" },
  { key: "phone", labelKey: "onboarding.field.phone", type: "tel", ltr: true, autoComplete: "tel" },
  { key: "email", labelKey: "onboarding.field.email", type: "email", ltr: true, autoComplete: "email" },
  { key: "bankName", labelKey: "onboarding.field.bankName", type: "text" },
  { key: "bankBranch", labelKey: "onboarding.field.bankBranch", type: "text", inputMode: "numeric", ltr: true },
  { key: "bankAccount", labelKey: "onboarding.field.bankAccount", type: "text", inputMode: "numeric", ltr: true },
  { key: "receiptPrefix", labelKey: "onboarding.field.receiptPrefix", type: "text", inputMode: "numeric", ltr: true },
];

function OnboardingForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { business, refresh } = useBusiness();
  const { t, tError } = useI18n();
  const editMode = searchParams.get("edit") === "1" && business !== null;

  function validateField(key: FieldKey, value: string): string | null {
    switch (key) {
      case "businessName":
        return value.trim() ? null : t("onboarding.error.businessNameRequired");
      case "ownerName":
        return value.trim() ? null : t("onboarding.error.ownerNameRequired");
      case "businessIdNumber":
        return /^\d{5,9}$/.test(value) ? null : t("onboarding.error.businessIdNumberInvalid");
      case "address":
        return value.trim() ? null : t("onboarding.error.addressRequired");
      case "phone":
        return null; // optional — the server accepts any string
      case "email":
        return !value || /^\S+@\S+\.\S+$/.test(value) ? null : t("onboarding.error.emailInvalid");
      case "bankName":
        return null; // optional
      case "bankBranch":
        return null; // optional
      case "bankAccount":
        return null; // optional
      case "receiptPrefix":
        return value.trim() && value.trim().length <= 10 ? null : t("onboarding.error.receiptPrefixInvalid");
    }
  }

  const [form, setForm] = useState<Record<FieldKey, string>>({
    businessName: "", ownerName: "", businessIdNumber: "", address: "",
    phone: "", email: "", bankName: "", bankBranch: "", bankAccount: "",
    receiptPrefix: String(new Date().getFullYear()),
  });
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldKey, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Prefill from the existing business when entering edit mode.
  useEffect(() => {
    if (!editMode || !business) return;
    setForm({
      businessName: business.businessName,
      ownerName: business.ownerName,
      businessIdNumber: business.businessIdNumber,
      address: business.address ?? "",
      phone: business.phone ?? "",
      email: business.email ?? "",
      bankName: business.bankName ?? "",
      bankBranch: business.bankBranch ?? "",
      bankAccount: business.bankAccount ?? "",
      receiptPrefix: business.receiptPrefix,
    });
  }, [editMode, business]);

  function handleBlur(key: FieldKey) {
    const message = validateField(key, form[key]);
    setFieldErrors((prev) => {
      const next = { ...prev };
      if (message) next[key] = message;
      else delete next[key];
      return next;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (saving) return;
    const errors: Partial<Record<FieldKey, string>> = {};
    for (const { key } of FIELDS) {
      const message = validateField(key, form[key]);
      if (message) errors[key] = message;
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setSaving(true);
    setError(null);
    try {
      if (editMode && business) {
        // businessIdNumber is immutable — BusinessUpdate rejects unknown fields, so send mutable ones only.
        await api<Business>(`/businesses/${business.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            businessName: form.businessName,
            ownerName: form.ownerName,
            address: form.address,
            phone: form.phone || null,
            email: form.email || null,
            bankName: form.bankName || null,
            bankBranch: form.bankBranch || null,
            bankAccount: form.bankAccount || null,
            receiptPrefix: form.receiptPrefix,
          }),
        });
        await refresh();
        router.replace("/more");
      } else {
        await api("/businesses", {
          method: "POST",
          body: JSON.stringify({ ...form, phone: form.phone || null, email: form.email || null, bankName: form.bankName || null, bankBranch: form.bankBranch || null, bankAccount: form.bankAccount || null }),
        });
        await refresh();
        router.replace("/dashboard");
      }
    } catch (err) {
      setError(tError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4 pt-6">
      <h1 className="text-2xl font-bold">{editMode ? t("onboarding.editTitle") : t("onboarding.title")}</h1>
      {!editMode && (
        <p className="mt-1 text-sm text-foreground/60">
          {t("onboarding.subtitle")}
        </p>
      )}
      <form onSubmit={submit} noValidate className="mt-6 flex flex-1 flex-col gap-4">
        {FIELDS.map(({ key, labelKey, type, inputMode, ltr, autoComplete }) => {
          const immutable = editMode && key === "businessIdNumber";
          return (
            <div key={key}>
              <label htmlFor={key} className="mb-1 block text-sm font-medium">
                {t(labelKey)}
              </label>
              <input
                id={key}
                type={type}
                inputMode={inputMode}
                dir={ltr ? "ltr" : undefined}
                autoComplete={autoComplete}
                value={form[key]}
                disabled={immutable}
                aria-invalid={Boolean(fieldErrors[key])}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                onBlur={() => handleBlur(key)}
                className={`min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 ${
                  fieldErrors[key] ? "border-destructive" : "border-border"
                }`}
              />
              {immutable && (
                <p className="mt-1 text-xs text-foreground/60">{t("onboarding.immutable")}</p>
              )}
              {fieldErrors[key] && (
                <p className="mt-1 text-sm text-destructive">{fieldErrors[key]}</p>
              )}
            </div>
          );
        })}
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="sticky bottom-0 mt-auto bg-muted pb-safe pt-2">
          <button
            type="submit"
            disabled={saving}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {saving && <Loader2 size={20} className="animate-spin" aria-hidden />}
            {saving ? t("onboarding.saving") : editMode ? t("onboarding.saveChanges") : t("onboarding.create")}
          </button>
        </div>
      </form>
    </main>
  );
}

// useSearchParams on a statically-rendered page requires a Suspense boundary (build fails otherwise).
export default function OnboardingPage() {
  return (
    <Suspense fallback={null}>
      <OnboardingForm />
    </Suspense>
  );
}

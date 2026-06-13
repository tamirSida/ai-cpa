"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/apiClient";
import { useBusiness } from "@/lib/business";
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
  label: string;
  type: "text" | "tel" | "email";
  inputMode?: "numeric";
  ltr?: boolean;
  autoComplete?: string;
};

const FIELDS: FieldDef[] = [
  { key: "businessName", label: "שם העסק", type: "text", autoComplete: "organization" },
  { key: "ownerName", label: "שם בעל/ת העסק", type: "text", autoComplete: "name" },
  { key: "businessIdNumber", label: "ת.ז / ע.מ (ספרות בלבד)", type: "text", inputMode: "numeric", ltr: true },
  { key: "address", label: "כתובת", type: "text", autoComplete: "street-address" },
  { key: "phone", label: "טלפון (רשות)", type: "tel", ltr: true, autoComplete: "tel" },
  { key: "email", label: "אימייל (רשות)", type: "email", ltr: true, autoComplete: "email" },
  { key: "bankName", label: "בנק (רשות)", type: "text" },
  { key: "bankBranch", label: "סניף (רשות)", type: "text", inputMode: "numeric", ltr: true },
  { key: "bankAccount", label: "מספר חשבון (רשות)", type: "text", inputMode: "numeric", ltr: true },
  { key: "receiptPrefix", label: "קידומת מספרי קבלות", type: "text", inputMode: "numeric", ltr: true },
];

function validateField(key: FieldKey, value: string): string | null {
  switch (key) {
    case "businessName":
      return value.trim() ? null : "יש להזין שם עסק";
    case "ownerName":
      return value.trim() ? null : "יש להזין את שם בעל/ת העסק";
    case "businessIdNumber":
      return /^\d{5,9}$/.test(value) ? null : "יש להזין 5–9 ספרות בלבד";
    case "address":
      return value.trim() ? null : "יש להזין כתובת";
    case "phone":
      return null; // אופציונלי — השרת מקבל כל מחרוזת
    case "email":
      return !value || /^\S+@\S+\.\S+$/.test(value) ? null : "כתובת אימייל לא תקינה";
    case "bankName":
      return null; // אופציונלי
    case "bankBranch":
      return null; // אופציונלי
    case "bankAccount":
      return null; // אופציונלי
    case "receiptPrefix":
      return value.trim() && value.trim().length <= 10 ? null : "יש להזין קידומת של עד 10 תווים";
  }
}

function OnboardingForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { business, refresh } = useBusiness();
  const editMode = searchParams.get("edit") === "1" && business !== null;
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
      setError(err instanceof ApiError ? err.message : "שגיאה לא צפויה, נסו שוב");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4 pt-6">
      <h1 className="text-2xl font-bold">{editMode ? "פרטי העסק" : "הקמת פרופיל עסק"}</h1>
      {!editMode && (
        <p className="mt-1 text-sm text-foreground/60">
          כמה פרטים על העסק — ואפשר להתחיל להפיק קבלות.
        </p>
      )}
      <form onSubmit={submit} noValidate className="mt-6 flex flex-1 flex-col gap-4">
        {FIELDS.map(({ key, label, type, inputMode, ltr, autoComplete }) => {
          const immutable = editMode && key === "businessIdNumber";
          return (
            <div key={key}>
              <label htmlFor={key} className="mb-1 block text-sm font-medium">
                {label}
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
                <p className="mt-1 text-xs text-foreground/60">לא ניתן לשינוי</p>
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
            {saving ? "שומר..." : editMode ? "שמירת שינויים" : "צור עסק"}
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

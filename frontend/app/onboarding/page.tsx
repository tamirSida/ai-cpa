"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/apiClient";
import { useBusiness } from "@/lib/business";

type FieldKey =
  | "businessName"
  | "ownerName"
  | "businessIdNumber"
  | "address"
  | "phone"
  | "email"
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
    case "receiptPrefix":
      return value.trim() && value.trim().length <= 10 ? null : "יש להזין קידומת של עד 10 תווים";
  }
}

export default function OnboardingPage() {
  const router = useRouter();
  const { refresh } = useBusiness();
  const [form, setForm] = useState<Record<FieldKey, string>>({
    businessName: "", ownerName: "", businessIdNumber: "", address: "",
    phone: "", email: "", receiptPrefix: String(new Date().getFullYear()),
  });
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldKey, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

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
      await api("/businesses", {
        method: "POST",
        body: JSON.stringify({ ...form, phone: form.phone || null, email: form.email || null }),
      });
      await refresh();
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "שגיאה לא צפויה, נסו שוב");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4 pt-6">
      <h1 className="text-2xl font-bold">הקמת פרופיל עסק</h1>
      <p className="mt-1 text-sm text-foreground/60">
        כמה פרטים על העסק — ואפשר להתחיל להפיק קבלות.
      </p>
      <form onSubmit={submit} noValidate className="mt-6 flex flex-1 flex-col gap-4">
        {FIELDS.map(({ key, label, type, inputMode, ltr, autoComplete }) => (
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
              aria-invalid={Boolean(fieldErrors[key])}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              onBlur={() => handleBlur(key)}
              className={`min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
                fieldErrors[key] ? "border-destructive" : "border-border"
              }`}
            />
            {fieldErrors[key] && (
              <p className="mt-1 text-sm text-destructive">{fieldErrors[key]}</p>
            )}
          </div>
        ))}
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="sticky bottom-0 mt-auto bg-muted pb-safe pt-2">
          <button
            type="submit"
            disabled={saving}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {saving && <Loader2 size={20} className="animate-spin" aria-hidden />}
            {saving ? "שומר..." : "צור עסק"}
          </button>
        </div>
      </form>
    </main>
  );
}

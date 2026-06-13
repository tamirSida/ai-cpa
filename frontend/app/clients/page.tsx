"use client";
import { useEffect, useState } from "react";
import { Loader2, Plus, Users } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import type { Business, Client } from "@/lib/types";

const EMPTY_FORM = { name: "", phone: "", email: "" };

function inputClass(invalid: boolean): string {
  return `min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
    invalid ? "border-destructive" : "border-border"
  }`;
}

export default function ClientsPage() {
  const { user, loading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [nameError, setNameError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    api<Business>("/businesses/me")
      .then(async (b) => {
        setBusiness(b);
        setClients(await api<Client[]>(`/businesses/${b.id}/clients`));
        setLoaded(true);
      })
      .catch((e) => setError((e as Error).message));
  }, [loading, user]);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setNameError(null);
    setSheetOpen(true);
  }

  function openEdit(client: Client) {
    setEditing(client);
    setForm({ name: client.name, phone: client.phone ?? "", email: client.email ?? "" });
    setNameError(null);
    setSheetOpen(true);
  }

  async function saveClient(e: React.FormEvent) {
    e.preventDefault();
    if (!business) return;
    if (!form.name.trim()) {
      setNameError("נדרש שם לקוח");
      return;
    }
    setBusy(true);
    setError(null);
    const body = JSON.stringify({
      name: form.name.trim(),
      phone: form.phone.trim() || undefined,
      email: form.email.trim() || undefined,
    });
    try {
      if (editing) {
        const updated = await api<Client>(`/businesses/${business.id}/clients/${editing.id}`, { method: "PATCH", body });
        setClients((cs) =>
          cs.map((c) => (c.id === updated.id ? updated : c)).sort((a, b) => a.name.localeCompare(b.name, "he"))
        );
      } else {
        const created = await api<Client>(`/businesses/${business.id}/clients`, { method: "POST", body });
        setClients((cs) => [...cs, created].sort((a, b) => a.name.localeCompare(b.name, "he")));
      }
      setSheetOpen(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">לקוחות</h1>
        <button
          onClick={openCreate}
          className="flex min-h-12 items-center gap-1.5 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
        >
          <Plus size={20} aria-hidden />
          לקוח חדש
        </button>
      </div>
      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      {loading || !loaded ? (
        <div className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-white p-4">
              <div className="h-5 w-32 rounded bg-muted" />
              <div className="mt-2 h-4 w-24 rounded bg-muted" />
            </div>
          ))}
        </div>
      ) : clients.length === 0 ? (
        <EmptyState
          Icon={Users}
          title="אין עדיין לקוחות"
          hint="הוסיפו לקוח בכפתור למעלה, או כתבו בצ׳אט: יש לי לקוח חדש בשם נועה"
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {clients.map((c) => (
            <li key={c.id}>
              <button
                onClick={() => openEdit(c)}
                className="min-h-12 w-full rounded-2xl border border-border bg-white p-4 text-start transition-transform duration-150 active:scale-[0.98]"
              >
                <span className="block font-medium">{c.name}</span>
                {c.phone && (
                  <span className="mt-0.5 block text-sm text-foreground/60">
                    <span dir="ltr">{c.phone}</span>
                  </span>
                )}
                {c.email && (
                  <span className="mt-0.5 block text-sm text-foreground/60">
                    <span dir="ltr">{c.email}</span>
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <Sheet open={sheetOpen} onClose={() => setSheetOpen(false)} title={editing ? "עריכת לקוח" : "לקוח חדש"}>
        <form onSubmit={saveClient} noValidate className="flex flex-col gap-4">
          <div>
            <label htmlFor="client-name" className="mb-1 block text-sm font-medium">שם *</label>
            <input
              id="client-name"
              value={form.name}
              aria-invalid={Boolean(nameError)}
              onChange={(e) => {
                setForm({ ...form, name: e.target.value });
                if (nameError) setNameError(null);
              }}
              onBlur={() => setNameError(form.name.trim() ? null : "נדרש שם לקוח")}
              className={inputClass(Boolean(nameError))}
            />
            {nameError && <p className="mt-1 text-sm text-destructive">{nameError}</p>}
          </div>
          <div>
            <label htmlFor="client-phone" className="mb-1 block text-sm font-medium">טלפון (רשות)</label>
            <input
              id="client-phone"
              type="tel"
              dir="ltr"
              autoComplete="tel"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className={inputClass(false)}
            />
          </div>
          <div>
            <label htmlFor="client-email" className="mb-1 block text-sm font-medium">אימייל (רשות)</label>
            <input
              id="client-email"
              type="email"
              dir="ltr"
              autoComplete="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className={inputClass(false)}
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {busy && <Loader2 size={20} className="animate-spin" aria-hidden />}
            {editing ? "שמירת שינויים" : "הוספת לקוח"}
          </button>
        </form>
      </Sheet>
    </div>
  );
}

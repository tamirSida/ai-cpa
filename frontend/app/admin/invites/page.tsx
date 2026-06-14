"use client";

import { useEffect, useState } from "react";
import { Loader2, Mail, Send } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import { api, ApiError } from "@/lib/apiClient";
import { INVITE_STATUS_LABELS } from "@/lib/labels";
import type { Invite, InviteStatus } from "@/lib/types";

const STATUS_BADGE: Record<InviteStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  accepted: "bg-accent/10 text-accent",
  revoked: "bg-destructive/10 text-foreground/50",
};

const EMAIL_RE = /^\S+@\S+\.\S+$/;

function inputClass(invalid: boolean): string {
  return `min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
    invalid ? "border-destructive" : "border-border"
  }`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("he-IL");
}

function byNewest(a: Invite, b: Invite): number {
  return b.createdAt.localeCompare(a.createdAt);
}

function StatusBadge({ status }: { status: InviteStatus }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[status]}`}>
      {INVITE_STATUS_LABELS[status]}
    </span>
  );
}

export default function AdminInvitesPage() {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Per-row revoke state: tracks which invite id is in-flight + any error.
  const [revoking, setRevoking] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);

  useEffect(() => {
    api<Invite[]>("/admin/invites")
      .then((rows) => {
        setInvites([...rows].sort(byNewest));
        setLoaded(true);
      })
      .catch((e) => setError((e as Error).message));
  }, []);

  // Merge a created/re-invited record: replace if the id already exists, else prepend.
  function upsertInvite(invite: Invite) {
    setInvites((list) => {
      const without = list.filter((i) => i.id !== invite.id);
      return [invite, ...without].sort(byNewest);
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) return;
    const value = email.trim().toLowerCase();
    if (!EMAIL_RE.test(value)) {
      setFormError("כתובת אימייל לא תקינה");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    setRowError(null);
    try {
      const created = await api<Invite>("/admin/invites", {
        method: "POST",
        body: JSON.stringify({ email: value }),
      });
      upsertInvite(created);
      setEmail("");
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function revoke(invite: Invite) {
    if (revoking) return;
    setRevoking(invite.id);
    setRowError(null);
    try {
      await api(`/admin/invites/${invite.id}`, { method: "DELETE" });
      setInvites((list) =>
        list.map((i) => (i.id === invite.id ? { ...i, status: "revoked" } : i))
      );
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : (err as Error).message);
    } finally {
      setRevoking(null);
    }
  }

  return (
    <div className="px-4 pb-6 pt-4">
      {/* Invite-by-email form — this page's primary action. */}
      <form onSubmit={submit} noValidate className="mb-6 flex flex-col gap-2">
        <label htmlFor="invite-email" className="text-sm font-medium">
          הזמנת משתמש לפי אימייל
        </label>
        <div className="flex items-start gap-2">
          <div className="flex-1">
            <input
              id="invite-email"
              type="email"
              dir="ltr"
              inputMode="email"
              autoComplete="off"
              placeholder="name@example.com"
              value={email}
              aria-invalid={Boolean(formError)}
              onChange={(e) => {
                setEmail(e.target.value);
                if (formError) setFormError(null);
              }}
              className={inputClass(Boolean(formError))}
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="flex min-h-12 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 size={20} className="animate-spin" aria-hidden />
            ) : (
              <Send size={18} aria-hidden />
            )}
            שלח הזמנה
          </button>
        </div>
        {formError && <p className="text-sm text-destructive">{formError}</p>}
      </form>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      {rowError && <p className="mb-4 text-sm text-destructive">{rowError}</p>}

      {!loaded ? (
        <div className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-white p-4">
              <div className="h-5 w-40 rounded bg-muted" />
              <div className="mt-2 h-4 w-24 rounded bg-muted" />
            </div>
          ))}
        </div>
      ) : invites.length === 0 ? (
        <EmptyState
          Icon={Mail}
          title="אין הזמנות עדיין"
          hint="הזמן משתמש לפי כתובת אימייל בטופס למעלה."
        />
      ) : (
        <>
          {/* Mobile cards */}
          <ul className="flex flex-col gap-3 md:hidden">
            {invites.map((inv) => (
              <li
                key={inv.id}
                className="rounded-2xl border border-border bg-white p-4"
              >
                <div className="flex items-center justify-between gap-2">
                  <span dir="ltr" className="truncate font-medium">{inv.email}</span>
                  <StatusBadge status={inv.status} />
                </div>
                <div className="mt-1 flex items-center justify-between gap-2">
                  <span dir="ltr" className="text-sm text-foreground/60">{formatDate(inv.createdAt)}</span>
                  {inv.status === "pending" && (
                    <button
                      onClick={() => revoke(inv)}
                      disabled={revoking === inv.id}
                      className="flex min-h-12 items-center justify-center gap-1.5 rounded-xl px-3 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                    >
                      {revoking === inv.id && <Loader2 size={16} className="animate-spin" aria-hidden />}
                      ביטול
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {/* Desktop table */}
          <div className="hidden overflow-hidden rounded-2xl border border-border bg-white md:block">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-muted/50">
                <tr>
                  <th className="p-3 text-start font-medium">אימייל</th>
                  <th className="p-3 text-start font-medium">סטטוס</th>
                  <th className="p-3 text-start font-medium">נשלחה</th>
                  <th className="p-3 text-start font-medium" />
                </tr>
              </thead>
              <tbody>
                {invites.map((inv) => (
                  <tr key={inv.id} className="border-b border-border last:border-b-0">
                    <td className="p-3"><span dir="ltr">{inv.email}</span></td>
                    <td className="p-3"><StatusBadge status={inv.status} /></td>
                    <td className="p-3"><span dir="ltr">{formatDate(inv.createdAt)}</span></td>
                    <td className="p-3 text-end">
                      {inv.status === "pending" && (
                        <button
                          onClick={() => revoke(inv)}
                          disabled={revoking === inv.id}
                          className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-lg px-3 font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-50"
                        >
                          {revoking === inv.id && <Loader2 size={16} className="animate-spin" aria-hidden />}
                          ביטול
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

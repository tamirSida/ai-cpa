"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Users } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { useAccount } from "@/lib/account";
import { useI18n } from "@/lib/i18n";
import { formatUsd } from "@/lib/format";
import type { AccountStatus, AdminUser, AdminUserDetail, Role } from "@/lib/types";

const STATUS_BADGE: Record<AccountStatus, string> = {
  pending: "bg-amber-100 text-amber-800",
  active: "bg-accent/10 text-accent",
  disabled: "bg-destructive/10 text-destructive",
};

const ROLE_BADGE: Record<Role, string> = {
  admin: "bg-primary/10 text-primary",
  user: "bg-muted text-foreground/60",
};

const TABS: { value: AccountStatus; labelKey: string }[] = [
  { value: "pending", labelKey: "admin.tabPending" },
  { value: "active", labelKey: "admin.tabActive" },
  { value: "disabled", labelKey: "admin.tabDisabled" },
];

const EMPTY_TITLES: Record<AccountStatus, string> = {
  pending: "admin.emptyPending",
  active: "admin.emptyActive",
  disabled: "admin.emptyDisabled",
};

function inputClass(invalid: boolean): string {
  return `min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
    invalid ? "border-destructive" : "border-border"
  }`;
}

function StatusBadge({ status }: { status: AccountStatus }) {
  const { t } = useI18n();
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[status]}`}>
      {t(`accountStatus.${status}`)}
    </span>
  );
}

function RoleBadge({ role }: { role: Role }) {
  const { t } = useI18n();
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs ${ROLE_BADGE[role]}`}>
      {t(`role.${role}`)}
    </span>
  );
}

function BudgetText({ aiBudgetUsd }: { aiBudgetUsd: number | null }) {
  const { t } = useI18n();
  if (aiBudgetUsd === null) return <>{t("common.unlimited")}</>;
  return (
    <>
      <span dir="ltr">{formatUsd(aiBudgetUsd)}</span> {t("admin.perMonth")}
    </>
  );
}

export default function AdminUsersPage() {
  const { account } = useAccount();
  const { t, tError } = useI18n();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [filter, setFilter] = useState<AccountStatus>("pending");
  const [search, setSearch] = useState("");

  const [selected, setSelected] = useState<AdminUser | null>(null);
  const [detail, setDetail] = useState<AdminUserDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sheetError, setSheetError] = useState<string | null>(null);

  // Approve / budget form state
  const [amount, setAmount] = useState("3");
  const [unlimited, setUnlimited] = useState(false);
  const [confirmUnlimited, setConfirmUnlimited] = useState(false);
  const [amountError, setAmountError] = useState<string | null>(null);

  useEffect(() => {
    api<AdminUser[]>("/admin/users")
      .then((rows) => {
        setUsers(rows);
        setLoaded(true);
      })
      .catch((e) => setError(tError(e)));
  }, [tError]);

  const pendingCount = useMemo(
    () => users.filter((u) => u.status === "pending").length,
    [users]
  );

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users
      .filter((u) => u.status === filter)
      .filter((u) => u.email.toLowerCase().includes(q))
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }, [users, filter, search]);

  function openSheet(u: AdminUser) {
    setSelected(u);
    setDetail(null);
    setSheetError(null);
    setAmount(u.aiBudgetUsd === null ? "3" : String(u.aiBudgetUsd));
    setUnlimited(u.aiBudgetUsd === null && u.status !== "pending");
    setConfirmUnlimited(false);
    setAmountError(null);
    setDetailLoading(true);
    api<AdminUserDetail>(`/admin/users/${u.uid}`)
      .then(setDetail)
      .catch((e) => setSheetError(tError(e)))
      .finally(() => setDetailLoading(false));
  }

  function closeSheet() {
    setSelected(null);
    setDetail(null);
  }

  // Apply an updated AdminUser returned from an action.
  function applyUpdate(updated: AdminUser) {
    setUsers((us) => us.map((x) => (x.uid === updated.uid ? updated : x)));
    closeSheet();
  }

  async function runAction(
    path: string,
    body?: unknown
  ): Promise<void> {
    setBusy(true);
    setSheetError(null);
    try {
      const updated = await api<AdminUser>(path, {
        method: "POST",
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      applyUpdate(updated);
    } catch (e) {
      setSheetError(tError(e));
    } finally {
      setBusy(false);
    }
  }

  function validBudget(): number | null | false {
    if (unlimited) return null;
    const n = Number(amount);
    if (!amount.trim() || !Number.isFinite(n) || n <= 0) {
      setAmountError(t("admin.positiveAmount"));
      return false;
    }
    return n;
  }

  async function submitApprove() {
    if (!selected) return;
    const budget = validBudget();
    if (budget === false) return;
    await runAction(`/admin/users/${selected.uid}/approve`, { aiBudgetUsd: budget });
  }

  async function submitBudget() {
    if (!selected) return;
    const budget = validBudget();
    if (budget === false) return;
    await runAction(`/admin/users/${selected.uid}/budget`, { aiBudgetUsd: budget });
  }

  const isSelf = selected != null && account != null && selected.uid === account.uid;
  // When unlimited is toggled on, require an explicit confirm before enabling submit.
  const budgetSubmitDisabled = busy || (unlimited && !confirmUnlimited);

  return (
    <div className="px-4 pb-6 pt-4">
      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      <div
        role="tablist"
        aria-label={t("admin.filterUsers")}
        className="mb-4 flex rounded-xl border border-border bg-muted p-1"
      >
        {TABS.map((tab) => (
          <button
            key={tab.value}
            role="tab"
            aria-selected={filter === tab.value}
            onClick={() => setFilter(tab.value)}
            className={`flex min-h-12 flex-1 items-center justify-center gap-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === tab.value ? "bg-white text-foreground shadow-sm" : "text-foreground/60"
            }`}
          >
            {t(tab.labelKey)}
            {tab.value === "pending" && pendingCount > 0 && (
              <span dir="ltr" className="tnum rounded-full bg-amber-500 px-1.5 text-xs font-semibold text-white">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="mb-4">
        <input
          type="search"
          dir="ltr"
          inputMode="email"
          placeholder={t("admin.searchByEmail")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className={inputClass(false)}
        />
      </div>

      {!loaded ? (
        <div className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-white p-4">
              <div className="h-5 w-40 rounded bg-muted" />
              <div className="mt-2 h-4 w-24 rounded bg-muted" />
            </div>
          ))}
        </div>
      ) : visible.length === 0 ? (
        <EmptyState Icon={Users} title={t(EMPTY_TITLES[filter])} />
      ) : (
        <>
          <ul className="flex flex-col gap-3 md:hidden">
            {visible.map((u) => (
              <li key={u.uid}>
                <button
                  onClick={() => openSheet(u)}
                  className="min-h-12 w-full rounded-2xl border border-border bg-white p-4 text-start transition-transform duration-150 active:scale-[0.98]"
                >
                  <span className="flex items-center justify-between gap-2">
                    <span dir="ltr" className="truncate font-medium">{u.email}</span>
                    <span className="flex shrink-0 items-center gap-1.5">
                      <RoleBadge role={u.role} />
                      <StatusBadge status={u.status} />
                    </span>
                  </span>
                  <span className="mt-1 block text-sm text-foreground/60">
                    <BudgetText aiBudgetUsd={u.aiBudgetUsd} />
                  </span>
                </button>
              </li>
            ))}
          </ul>

          <div className="hidden overflow-hidden rounded-2xl border border-border bg-white md:block">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-muted/50">
                <tr>
                  <th className="p-3 text-start font-medium">{t("admin.colEmail")}</th>
                  <th className="p-3 text-start font-medium">{t("admin.colRole")}</th>
                  <th className="p-3 text-start font-medium">{t("admin.colStatus")}</th>
                  <th className="p-3 text-start font-medium">{t("admin.colBudget")}</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((u) => (
                  <tr
                    key={u.uid}
                    onClick={() => openSheet(u)}
                    className="cursor-pointer border-b border-border last:border-b-0 hover:bg-muted/50"
                  >
                    <td className="p-3"><span dir="ltr">{u.email}</span></td>
                    <td className="p-3"><RoleBadge role={u.role} /></td>
                    <td className="p-3"><StatusBadge status={u.status} /></td>
                    <td className="p-3"><BudgetText aiBudgetUsd={u.aiBudgetUsd} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <Sheet open={selected != null} onClose={closeSheet} title={selected?.email}>
        {selected && (
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center gap-1.5">
              <RoleBadge role={selected.role} />
              <StatusBadge status={selected.status} />
            </div>

            {/* Usage line (read-only) */}
            {detailLoading ? (
              <div className="flex items-center gap-2 text-sm text-foreground/60">
                <Loader2 size={16} className="animate-spin" aria-hidden />
                {t("admin.loadingDetails")}
              </div>
            ) : detail ? (
              <p className="text-sm text-foreground/70">
                {t("admin.usageThisMonth")}{" "}
                <span dir="ltr">
                  {formatUsd(detail.usage.aiCostUsd)} /{" "}
                  {detail.aiBudgetUsd === null ? t("common.unlimited") : formatUsd(detail.aiBudgetUsd)}
                </span>
              </p>
            ) : null}

            {/* Approve (pending) or Edit budget (active) */}
            {(selected.status === "pending" || selected.status === "active") && (
              <div className="flex flex-col gap-3 rounded-xl border border-border p-3">
                <p className="text-sm font-medium">
                  {selected.status === "pending" ? t("admin.aiBudgetApprove") : t("admin.aiBudget")}
                </p>
                <div>
                  <label htmlFor="budget-amount" className="mb-1 block text-sm text-foreground/60">
                    {t("admin.monthlyAmountUsd")}
                  </label>
                  <input
                    id="budget-amount"
                    inputMode="decimal"
                    dir="ltr"
                    value={amount}
                    disabled={unlimited}
                    aria-invalid={Boolean(amountError)}
                    onChange={(e) => {
                      setAmount(e.target.value);
                      if (amountError) setAmountError(null);
                    }}
                    className={`${inputClass(Boolean(amountError))} disabled:opacity-50`}
                  />
                  {amountError && <p className="mt-1 text-sm text-destructive">{amountError}</p>}
                </div>

                <label className="flex min-h-12 items-center gap-2">
                  <input
                    type="checkbox"
                    checked={unlimited}
                    onChange={(e) => {
                      setUnlimited(e.target.checked);
                      setConfirmUnlimited(false);
                      setAmountError(null);
                    }}
                    className="size-5 accent-primary"
                  />
                  <span className="text-sm">{t("common.unlimited")}</span>
                </label>

                {unlimited && (
                  <div className="flex flex-col gap-2 rounded-xl bg-amber-100 p-3 text-sm text-amber-800">
                    <p>{t("admin.unlimitedWarning")}</p>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={confirmUnlimited}
                        onChange={(e) => setConfirmUnlimited(e.target.checked)}
                        className="size-5 accent-amber-600"
                      />
                      <span>{t("admin.unlimitedConfirm")}</span>
                    </label>
                  </div>
                )}

                <button
                  onClick={selected.status === "pending" ? submitApprove : submitBudget}
                  disabled={budgetSubmitDisabled}
                  className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                >
                  {busy && <Loader2 size={20} className="animate-spin" aria-hidden />}
                  {selected.status === "pending" ? t("admin.approveUser") : t("admin.saveBudget")}
                </button>
              </div>
            )}

            {/* Change role */}
            <div>
              <button
                onClick={() =>
                  runAction(`/admin/users/${selected.uid}/role`, {
                    role: selected.role === "admin" ? "user" : "admin",
                  })
                }
                disabled={busy || isSelf}
                className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
              >
                {selected.role === "admin" ? t("admin.makeUser") : t("admin.makeAdmin")}
              </button>
              {isSelf && (
                <p className="mt-1 text-sm text-foreground/60">{t("admin.cannotChangeOwnRole")}</p>
              )}
            </div>

            {/* Disable / Enable */}
            {selected.status === "disabled" ? (
              <button
                onClick={() => runAction(`/admin/users/${selected.uid}/enable`)}
                disabled={busy}
                className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
              >
                {t("admin.enableAccount")}
              </button>
            ) : (
              <div>
                <button
                  onClick={() => runAction(`/admin/users/${selected.uid}/disable`)}
                  disabled={busy || isSelf}
                  className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-destructive bg-white px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                >
                  {t("admin.disableAccount")}
                </button>
                {isSelf && (
                  <p className="mt-1 text-sm text-foreground/60">{t("admin.cannotDisableSelf")}</p>
                )}
              </div>
            )}

            {sheetError && <p className="text-sm text-destructive">{sheetError}</p>}
          </div>
        )}
      </Sheet>
    </div>
  );
}

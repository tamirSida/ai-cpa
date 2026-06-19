// frontend/components/DashboardCards.tsx
"use client";

import { DashboardResponse } from "@/lib/types";
import { formatILS } from "@/lib/format";
import { useT } from "@/lib/i18n";
import ThresholdProgress from "./ThresholdProgress";

export default function DashboardCards({ data }: { data: DashboardResponse }) {
  const t = useT();
  const { totals, counts, threshold } = data;
  const cards = [
    { id: "incomeThisYear", label: t("dashboard.incomeThisYear"), value: formatILS(totals.incomeThisYear) },
    { id: "incomeThisMonth", label: t("dashboard.incomeThisMonth"), value: formatILS(totals.incomeThisMonth) },
    { id: "expensesThisYear", label: t("dashboard.recognizedExpenses"), value: formatILS(totals.expensesThisYear) },
    {
      id: "estimatedProfit",
      label: t("dashboard.estimatedProfit"),
      value: formatILS(totals.estimatedProfit),
      valueClassName: totals.estimatedProfit < 0 ? "text-destructive" : undefined,
    },
  ];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {cards.map((c) => (
          <div key={c.id} className="rounded-2xl border border-border bg-white p-4">
            <p className="text-sm text-foreground/60">{c.label}</p>
            <p className={`tnum mt-1 text-2xl font-semibold ${c.valueClassName ?? ""}`} dir="ltr">{c.value}</p>
          </div>
        ))}
      </div>
      <ThresholdProgress threshold={threshold} />
      <div className="flex flex-wrap gap-x-4 gap-y-1 rounded-2xl border border-border bg-white p-4 text-sm text-foreground/60">
        <span><span className="tnum" dir="ltr">{counts.receiptsCount}</span> {t("dashboard.receiptsCount")}</span>
        <span><span className="tnum" dir="ltr">{counts.approvedExpensesCount}</span> {t("dashboard.approvedExpensesCount")}</span>
        <span><span className="tnum" dir="ltr">{counts.needsReviewCount}</span> {t("dashboard.needsReviewCount")}</span>
      </div>
    </div>
  );
}

// frontend/components/DashboardCards.tsx
import { DashboardResponse } from "@/lib/types";
import { formatILS } from "@/lib/format";
import ThresholdProgress from "./ThresholdProgress";

export default function DashboardCards({ data }: { data: DashboardResponse }) {
  const { totals, counts, threshold } = data;
  const cards = [
    { label: "הכנסות השנה", value: formatILS(totals.incomeThisYear) },
    { label: "הכנסות החודש", value: formatILS(totals.incomeThisMonth) },
    { label: "הוצאות מוכרות", value: formatILS(totals.expensesThisYear) },
    { label: "רווח משוער", value: formatILS(totals.estimatedProfit) },
  ];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border border-border bg-white p-4">
            <p className="text-sm text-foreground/60">{c.label}</p>
            <p className="tnum mt-1 text-2xl font-semibold" dir="ltr">{c.value}</p>
          </div>
        ))}
      </div>
      <ThresholdProgress threshold={threshold} />
      <div className="flex flex-wrap gap-x-4 gap-y-1 rounded-2xl border border-border bg-white p-4 text-sm text-foreground/60">
        <span><span className="tnum" dir="ltr">{counts.receiptsCount}</span> קבלות</span>
        <span><span className="tnum" dir="ltr">{counts.approvedExpensesCount}</span> הוצאות מאושרות</span>
        <span><span className="tnum" dir="ltr">{counts.needsReviewCount}</span> ממתינות לבדיקה</span>
      </div>
    </div>
  );
}

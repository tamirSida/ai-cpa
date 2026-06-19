// frontend/components/MonthlyIncomeChart.tsx
"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MonthlyIncomeEntry } from "@/lib/types";
import { monthNames, formatILS } from "@/lib/format";
import { useI18n } from "@/lib/i18n";

export default function MonthlyIncomeChart({ data }: { data: MonthlyIncomeEntry[] }) {
  const { lang } = useI18n();
  const months = monthNames(lang);
  const chartData = data.map((m) => ({ name: months[m.month - 1], total: m.total }));
  return (
    <div className="w-full" dir="ltr">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
          <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} tickLine={false} axisLine={false} />
          <YAxis
            width={64}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => formatILS(v)}
          />
          <Tooltip formatter={(v) => formatILS(Number(v))} cursor={{ fill: "rgba(37, 99, 235, 0.08)" }} />
          <Bar dataKey="total" fill="#2563eb" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

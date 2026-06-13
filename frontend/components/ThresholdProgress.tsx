// frontend/components/ThresholdProgress.tsx
import { ThresholdStatus } from "@/lib/types";
import { formatILS } from "@/lib/format";

export default function ThresholdProgress({ threshold }: { threshold: ThresholdStatus }) {
  const width = Math.min(threshold.pct, 100);
  const barColor =
    threshold.pct >= 100 ? "bg-destructive" : threshold.pct >= 90 ? "bg-amber-500" : "bg-accent";
  return (
    <div className="rounded-2xl border border-border bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">תקרת עוסק פטור</span>
        <span className="tnum text-sm text-foreground/60" dir="ltr">
          {threshold.pct.toFixed(1)}%
        </span>
      </div>
      <p className="mt-1 text-sm text-foreground/60">
        <span className="tnum" dir="ltr">{formatILS(threshold.total)}</span>
        {" מתוך "}
        <span className="tnum" dir="ltr">{formatILS(threshold.limit)}</span>
      </p>
      <div
        className="mt-2 h-3 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={Math.round(threshold.pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`h-3 rounded-full ${barColor}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

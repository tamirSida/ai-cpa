import type { LucideIcon } from "lucide-react";

export default function EmptyState({
  Icon,
  title,
  hint,
  action,
}: {
  Icon: LucideIcon;
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-border bg-white px-6 py-12 text-center">
      <Icon size={32} className="text-foreground/30" aria-hidden />
      <p className="font-medium">{title}</p>
      {hint && <p className="text-sm text-foreground/60">{hint}</p>}
      {action}
    </div>
  );
}

"use client";
import type { Receipt } from "@/lib/types";
import { formatILS } from "@/lib/format";
import { useT } from "@/lib/i18n";

const STATUS_CLASS: Record<Receipt["status"], string> = {
  draft: "bg-muted text-foreground/60",
  issued: "bg-accent/10 text-accent",
  cancelled: "bg-destructive/10 text-destructive",
};

export function ReceiptStatusBadge({ status }: { status: Receipt["status"] }) {
  const t = useT();
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASS[status]}`}>
      {t(`receipts.status.${status}`)}
    </span>
  );
}

export default function ReceiptList({
  receipts,
  onSelect,
}: {
  receipts: Receipt[];
  onSelect: (receipt: Receipt) => void;
}) {
  const t = useT();
  return (
    <>
      {/* Primary markup: mobile card list */}
      <ul className="flex flex-col gap-3 md:hidden">
        {receipts.map((r) => (
          <li key={r.id}>
            <button
              onClick={() => onSelect(r)}
              className="min-h-12 w-full rounded-2xl border border-border bg-white p-4 text-start transition-transform duration-150 active:scale-[0.98]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="tnum text-sm text-foreground/60" dir="ltr">{r.receiptNumber ?? "—"}</span>
                <ReceiptStatusBadge status={r.status} />
              </div>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="font-medium">{r.clientSnapshot.name}</span>
                <span className="tnum text-lg font-semibold" dir="ltr">{formatILS(r.amount)}</span>
              </div>
              <div className="mt-1 text-sm text-foreground/60">
                <span dir="ltr">{r.issueDate}</span>
              </div>
              {r.checkDetails && (
                <div className="mt-1 text-sm text-foreground/60">
                  {t("receipts.checkLabel")} {t("receipts.checkNumber")} <span className="tnum" dir="ltr">{r.checkDetails.number}</span> · {r.checkDetails.bank} · {t("receipts.checkBranch")}{" "}
                  <span className="tnum" dir="ltr">{r.checkDetails.branch}</span> · {t("receipts.checkDueDate")}{" "}
                  <span className="tnum" dir="ltr">{r.checkDetails.dueDate}</span>
                </div>
              )}
            </button>
          </li>
        ))}
      </ul>
      {/* Desktop-only enhancement — never rendered at 375px */}
      <div className="hidden overflow-hidden rounded-2xl border border-border bg-white md:block">
        <table className="w-full text-start">
          <thead>
            <tr className="border-b border-border text-sm font-bold">
              <th scope="col" className="p-3">{t("receipts.colNumber")}</th><th scope="col" className="p-3">{t("receipts.colDate")}</th><th scope="col" className="p-3">{t("receipts.colClient")}</th>
              <th scope="col" className="p-3">{t("receipts.colAmount")}</th><th scope="col" className="p-3">{t("receipts.colMethod")}</th><th scope="col" className="p-3">{t("receipts.colStatus")}</th><th scope="col" className="p-3">{t("receipts.colPdf")}</th>
            </tr>
          </thead>
          <tbody>
            {receipts.map((r) => (
              <tr key={r.id} onClick={() => onSelect(r)} className="cursor-pointer border-b border-border last:border-b-0">
                <td className="tnum p-3" dir="ltr">{r.receiptNumber ?? "—"}</td>
                <td className="p-3" dir="ltr">{r.issueDate}</td>
                <td className="p-3">{r.clientSnapshot.name}</td>
                <td className="tnum p-3" dir="ltr">{formatILS(r.amount)}</td>
                <td className="p-3">{t(`receipts.payment.${r.paymentMethod}`)}</td>
                <td className="p-3"><ReceiptStatusBadge status={r.status} /></td>
                <td className="p-3">
                  {r.pdfUrl ? (
                    <a
                      className="text-primary underline"
                      href={r.pdfUrl}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {t("receipts.download")}
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

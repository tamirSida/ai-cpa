import type { ExpenseCategory, ExpenseStatus } from "@/lib/types";
export const CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  software: "תוכנה", equipment: "ציוד", travel: "נסיעות", office: "משרד", marketing: "שיווק",
  professional_services: "שירותים מקצועיים", meals: "אש\"ל", parking: "חניה", other: "אחר",
};
export const EXPENSE_STATUS_LABELS: Record<ExpenseStatus, string> = {
  needs_review: "לבדיקה", approved: "מאושר", rejected: "נדחה",
};

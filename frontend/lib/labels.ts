import type { ExpenseCategory, ExpenseStatus, Role, AccountStatus, InviteStatus } from "@/lib/types";
import { ApiError } from "@/lib/apiClient";
export const CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  software: "תוכנה", equipment: "ציוד", travel: "נסיעות", office: "משרד", marketing: "שיווק",
  professional_services: "שירותים מקצועיים", meals: "אש\"ל", parking: "חניה", other: "אחר",
};
export const EXPENSE_STATUS_LABELS: Record<ExpenseStatus, string> = {
  needs_review: "לבדיקה", approved: "מאושר", rejected: "נדחה",
};
export const ROLE_LABELS: Record<Role, string> = { admin: "מנהל", user: "משתמש" };
export const ACCOUNT_STATUS_LABELS: Record<AccountStatus, string> = { pending: "ממתין לאישור", active: "פעיל", disabled: "מושבת" };
export const INVITE_STATUS_LABELS: Record<InviteStatus, string> = { pending: "ממתינה", accepted: "התקבלה", revoked: "בוטלה" };
export const UNLIMITED_LABEL = "ללא הגבלה";
export const AI_BUDGET_EXCEEDED_HE = "הגעת למכסת ה-AI החודשית. פנה למנהל כדי להגדיל את המכסה.";

// Returns the agreed Hebrew copy for the budget-exceeded ApiError; null for any other error.
export function aiErrorMessage(e: unknown): string | null {
  return e instanceof ApiError && e.code === "ai_budget_exceeded" ? AI_BUDGET_EXCEEDED_HE : null;
}

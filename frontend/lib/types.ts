export interface Business {
  id: string;
  ownerUserId: string;
  businessName: string;
  ownerName: string;
  businessIdNumber: string;
  businessType: "osek_patur";
  address?: string;
  phone?: string;
  email?: string;
  bankName?: string;
  bankBranch?: string;
  bankAccount?: string;
  receiptPrefix: string;
  nextReceiptNumber: number;
  annualLimit?: number;
}

export type ReceiptStatus = "draft" | "issued" | "cancelled";
export type PaymentMethod = "cash" | "bank_transfer" | "bit" | "paybox" | "credit_card" | "check" | "other" | "unknown";
export interface Client { id: string; businessId: string; name: string; phone?: string; email?: string; companyName?: string; taxId?: string; address?: string; notes?: string; }
export interface ClientSnapshot { name: string; phone?: string; email?: string; taxId?: string; address?: string; }
export interface Receipt { id: string; businessId: string; clientId?: string; receiptNumber?: string; sequenceNumber?: number; status: ReceiptStatus; issueDate: string; amount: number; currency: "ILS"; paymentMethod: PaymentMethod; description: string; clientSnapshot: ClientSnapshot; checkDetails?: { number: string; bank: string; branch: string; dueDate: string }; pdfUrl?: string; cloudinaryPublicId?: string; cancellationReason?: string; }
export const PAYMENT_LABELS: Record<PaymentMethod, string> = { cash: "מזומן", bank_transfer: "העברה בנקאית", bit: "ביט", paybox: "פייבוקס", credit_card: "כרטיס אשראי", check: "צ'ק", other: "אחר", unknown: "לא צוין" };

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  actionId?: string | null;
  createdAt: string;
}

export interface ActionView {
  id: string;
  type: string;
  status: string;
  payload: Record<string, unknown>;
  missingFields: string[];
}

export interface ActionResult {
  receiptId?: string;
  receiptNumber?: string;
  pdfUrl?: string | null;
  clientId?: string;
  expenseId?: string;
  year?: number;
  link?: string;
}

export interface ChatTurnResult {
  assistantText: string;
  action: ActionView | null;
  result?: ActionResult | null;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  activeAction: ActionView | null;
}

// client-only message state for optimistic send / inline retry / inline PDF button
export type ChatSendStatus = "pending" | "failed";

export interface UiChatMessage extends ChatMessage {
  sendStatus?: ChatSendStatus;
  pdfUrl?: string | null;
}

export type ExpenseStatus = "needs_review" | "approved" | "rejected";
export type ExpenseCategory = "software" | "equipment" | "travel" | "office" | "marketing"
  | "professional_services" | "meals" | "parking" | "other";
export interface Expense {
  id: string; businessId: string; supplierName: string | null; expenseDate: string | null;
  amount: number | null; currency: "ILS"; category: ExpenseCategory | null; description: string | null;
  businessUsePercent: number; imageUrl: string | null; cloudinaryPublicId: string | null;
  ocrText: string | null; extractionConfidence: number | null; status: ExpenseStatus;
  createdAt: string; updatedAt: string;
}

export interface DashboardTotals { incomeThisYear: number; incomeThisMonth: number; expensesThisYear: number; estimatedProfit: number; }
export interface DashboardCounts { receiptsCount: number; approvedExpensesCount: number; needsReviewCount: number; }
export interface ThresholdStatus { total: number; limit: number; pct: number; warning: boolean; }
export interface MonthlyIncomeEntry { month: number; total: number; }
export interface RecentReceipt { id: string; receiptNumber: string; clientName: string; amount: number; issueDate: string; pdfUrl: string | null; }
export interface RecentExpense { id: string; supplierName: string | null; amount: number | null; category: string | null; expenseDate: string | null; status: "needs_review" | "approved" | "rejected"; }
export interface DashboardResponse {
  totals: DashboardTotals; counts: DashboardCounts; threshold: ThresholdStatus;
  monthlyIncome: MonthlyIncomeEntry[]; expensesByCategory: Record<string, number>;
  recentReceipts: RecentReceipt[]; recentExpenses: RecentExpense[]; warnings: string[];
}

export interface PrecheckResult {
  year: number; expensesNeedingReview: string[]; expensesMissingImages: string[];
  uncategorizedExpenses: string[]; receiptsMissingPdf: string[]; cancelledReceipts: string[];
  missingBusinessFields: string[]; receiptsMissingPayerAddress: string[]; totalRevenue: number; thresholdWarning: boolean; issuesCount: number;
}

export type Role = "admin" | "user";
export type AccountStatus = "pending" | "active" | "disabled";
export type InviteStatus = "pending" | "accepted" | "revoked";

export interface AiUsage {
  month: string;            // "YYYY-MM"
  aiCostUsd: number;
  aiBudgetUsd: number | null;
  overBudget: boolean;
}

export interface UserAccount {        // shape of GET /users/me
  uid: string;
  email: string;
  displayName?: string | null;
  role: Role;
  status: AccountStatus;
  aiBudgetUsd: number | null;         // null == Unlimited
  usage: AiUsage;
  hasBusiness: boolean;
}

export interface AdminUser {          // GET /admin/users[] rows + action responses
  uid: string;
  email: string;
  displayName?: string | null;
  role: Role;
  status: AccountStatus;
  aiBudgetUsd: number | null;
  invitedByUid?: string | null;
  approvedByUid?: string | null;
  approvedAt?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AdminUserDetail extends AdminUser {
  usage: AiUsage;
  business: { id: string; businessName: string; businessIdNumber: string } | null;
}

export interface Invite {
  id: string;               // == email
  email: string;
  status: InviteStatus;
  invitedByUid: string;
  acceptedByUid?: string | null;
  createdAt: string;
  updatedAt: string;
}

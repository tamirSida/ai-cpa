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
  receiptPrefix: string;
  nextReceiptNumber: number;
  annualLimit?: number;
}

export type ReceiptStatus = "draft" | "issued" | "cancelled";
export type PaymentMethod = "cash" | "bank_transfer" | "bit" | "paybox" | "credit_card" | "check" | "other" | "unknown";
export interface Client { id: string; businessId: string; name: string; phone?: string; email?: string; companyName?: string; taxId?: string; address?: string; notes?: string; }
export interface ClientSnapshot { name: string; phone?: string; email?: string; taxId?: string; address?: string; }
export interface Receipt { id: string; businessId: string; clientId?: string; receiptNumber?: string; sequenceNumber?: number; status: ReceiptStatus; issueDate: string; amount: number; currency: "ILS"; paymentMethod: PaymentMethod; description: string; clientSnapshot: ClientSnapshot; pdfUrl?: string; cloudinaryPublicId?: string; cancellationReason?: string; }
export const PAYMENT_LABELS: Record<PaymentMethod, string> = { cash: "מזומן", bank_transfer: "העברה בנקאית", bit: "ביט", paybox: "פייבוקס", credit_card: "כרטיס אשראי", check: "צ'ק", other: "אחר", unknown: "לא צוין" };

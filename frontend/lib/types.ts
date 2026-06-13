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

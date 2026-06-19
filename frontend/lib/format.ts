export function formatILS(n: number): string {
  // minimumFractionDigits 0 keeps whole amounts clean (₪2,800); maximumFractionDigits 2
  // preserves agorot (₪99.5) so the UI never disagrees with the stored/receipt amount.
  return new Intl.NumberFormat("he-IL", {
    style: "currency",
    currency: "ILS",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n);
}

export const MONTH_NAMES_HE = [
  "ינו׳", "פבר׳", "מרץ", "אפר׳", "מאי", "יוני",
  "יולי", "אוג׳", "ספט׳", "אוק׳", "נוב׳", "דצמ׳",
];

export const MONTH_NAMES_EN = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export function monthNames(lang: "en" | "he"): string[] {
  return lang === "he" ? MONTH_NAMES_HE : MONTH_NAMES_EN;
}

// AI budget/usage is denominated in USD; output is LTR ($3.00) — callers wrap in dir="ltr".
export function formatUsd(n: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
}

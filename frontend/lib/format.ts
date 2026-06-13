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

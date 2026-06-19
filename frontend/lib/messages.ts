// Central i18n catalog. `en` is the source of truth; `he` is typed to mirror its keys
// exactly, so a missing/extra Hebrew key is a compile error. Keys are dot-namespaced by
// feature. Interpolate with {name} placeholders (see t() in lib/i18n.tsx).

const en = {
  // language toggle
  "lang.en": "English",
  "lang.he": "עברית",

  // bottom nav
  "nav.chat": "Chat",
  "nav.dashboard": "Overview",
  "nav.receipts": "Receipts",
  "nav.expenses": "Expenses",
  "nav.more": "More",

  // common
  "common.signOut": "Sign out",
  "common.signOutFailed": "Sign-out failed, try again",
  "common.refresh": "Refresh",
  "common.unlimited": "Unlimited",

  // login
  "login.title": "AI Bookkeeper",
  "login.subtitle": "Chat-first bookkeeping for Israeli sole proprietors — receipts, expenses & annual report",
  "login.google": "Sign in with Google",
  "login.or": "or",
  "login.email": "name@example.com",
  "login.emailLabel": "Email",
  "login.password": "Password",
  "login.emailSignin": "Sign in with email",
  "login.demo": "Enter demo account",
  "login.errFailed": "Sign-in failed — check your details and try again",
  "login.errMissing": "Enter an email and password",

  // pending / disabled account screens
  "pending.title": "Awaiting approval",
  "pending.body": "Your account was created and is waiting for an administrator to approve it. Once approved you'll get full access.",
  "disabled.title": "Account disabled",
  "disabled.body": "Your account has been disabled. Contact the administrator for details.",

  // error messages, keyed by the backend ApiError.code (frontend-localized)
  "error.generic": "Something went wrong, try again",
  "error.account_pending": "Your account is awaiting approval",
  "error.account_disabled": "Your account has been disabled",
  "error.forbidden_not_admin": "Admin access required",
  "error.ai_budget_exceeded": "You've reached your monthly AI limit. Contact the administrator to raise it.",
  "error.business_not_found": "No business found",
  "error.invalid_email": "Invalid email address",
  "error.user_already_exists": "A user with this email already exists",
  "error.invite_not_found": "Invite not found",
  "error.invite_not_revocable": "Can't revoke an invite that was already used",
  "error.invalid_user_status": "Only a pending user can be approved",
  "error.cannot_disable_self": "You can't disable your own account",
  "error.cannot_change_own_role": "You can't change your own role",
  "error.user_not_found": "User not found",
  "error.unsupported_file_type": "Unsupported file type. Upload JPG, PNG, HEIC or WebP",
  "error.file_too_large": "File too large (max 10MB)",
} as const;

const he: Record<keyof typeof en, string> = {
  "lang.en": "English",
  "lang.he": "עברית",

  "nav.chat": "צ'אט",
  "nav.dashboard": "סקירה",
  "nav.receipts": "קבלות",
  "nav.expenses": "הוצאות",
  "nav.more": "עוד",

  "common.signOut": "התנתקות",
  "common.signOutFailed": "ההתנתקות נכשלה, נסה שוב",
  "common.refresh": "רענון",
  "common.unlimited": "ללא הגבלה",

  "login.title": "AI Bookkeeper",
  "login.subtitle": "הנהלת חשבונות בצ'אט לעוסק פטור — קבלות, הוצאות ודוח שנתי",
  "login.google": "התחברות עם Google",
  "login.or": "או",
  "login.email": "name@example.com",
  "login.emailLabel": "אימייל",
  "login.password": "סיסמה",
  "login.emailSignin": "התחברות עם אימייל",
  "login.demo": "כניסה לחשבון דמו",
  "login.errFailed": "ההתחברות נכשלה — בדוק את הפרטים ונסה שוב",
  "login.errMissing": "יש להזין אימייל וסיסמה",

  "pending.title": "ממתין לאישור",
  "pending.body": "החשבון שלך נוצר ונמצא בהמתנה לאישור מנהל. ברגע שהחשבון יאושר תקבל גישה מלאה למערכת.",
  "disabled.title": "החשבון הושבת",
  "disabled.body": "החשבון שלך הושבת. לפרטים נוספים פנה למנהל המערכת.",

  "error.generic": "משהו השתבש, נסה שוב",
  "error.account_pending": "החשבון שלך ממתין לאישור",
  "error.account_disabled": "החשבון שלך הושבת",
  "error.forbidden_not_admin": "נדרשת הרשאת מנהל",
  "error.ai_budget_exceeded": "הגעת למכסת ה-AI החודשית. פנה למנהל כדי להגדיל את המכסה.",
  "error.business_not_found": "לא נמצא עסק",
  "error.invalid_email": "כתובת אימייל לא תקינה",
  "error.user_already_exists": "כבר קיים משתמש עם האימייל הזה",
  "error.invite_not_found": "ההזמנה לא נמצאה",
  "error.invite_not_revocable": "לא ניתן לבטל הזמנה שכבר נוצלה",
  "error.invalid_user_status": "אפשר לאשר רק משתמש בהמתנה",
  "error.cannot_disable_self": "אי אפשר להשבית את עצמך",
  "error.cannot_change_own_role": "אי אפשר לשנות את התפקיד של עצמך",
  "error.user_not_found": "המשתמש לא נמצא",
  "error.unsupported_file_type": "סוג הקובץ לא נתמך. אפשר להעלות JPG, PNG, HEIC או WebP",
  "error.file_too_large": "הקובץ גדול מדי (מקסימום 10MB)",
};

export type Lang = "en" | "he";
// Loose on purpose: t() accepts any key so feature work can reference keys freely, and a
// missing key falls back to the key string. en/he parity is still enforced above by typing
// `he` as Record<keyof typeof en, string>, so the catalog can never drift out of sync.
export type MsgKey = string;
export const messages: Record<Lang, Record<string, string>> = { en, he };

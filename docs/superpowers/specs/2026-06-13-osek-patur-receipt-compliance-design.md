# עוסק פטור Receipt Content Compliance — Design

**Goal:** Bring generated קבלה (receipt) PDFs into **content/format** compliance with the Israeli
bookkeeping directives, capturing legally-mandatory payment-instrument details **only where the law
requires them** (checks), without adding friction to the common cash / bank-transfer / Bit flows.
The digital signature is explicitly **deferred** (open question).

**Status:** Approved design, pending spec review → implementation plan.

---

## Legal basis (researched, sourced)

Primary source: **הוראות מס הכנסה (ניהול פנקסי חשבונות), התשל"ג-1973** ([Nevo](https://www.nevo.co.il/law_html/law01/255_179.htm), [Wikisource](https://he.wikisource.org/wiki/%D7%94%D7%95%D7%A8%D7%90%D7%95%D7%AA_%D7%9E%D7%A1_%D7%94%D7%9B%D7%A0%D7%A1%D7%94_(%D7%A0%D7%99%D7%94%D7%95%D7%9C_%D7%A4%D7%A0%D7%A7%D7%A1%D7%99_%D7%97%D7%A9%D7%91%D7%95%D7%A0%D7%95%D7%AA))).

- **§5 — mandatory receipt fields:** serial number, issuer name + ID number, **issuer address**, date,
  **payer name + address** (except retail cash), amount received, nature of payment (מהות התקבול),
  recipient signature.
- **§5(ב) — checks:** must record check number + bank + branch + due date (תאריך פירעון).
  *(Account number is common practice but not in the statutory text — we will not require it.)*
- **§18ב — computerized documents:** must be marked **«מסמך ממוחשב»**; printed copies mark the
  payer's copy **«מקור»**; the handwritten-signature waiver requires a secured/qualified electronic
  signature — **DEFERRED**, see Out of Scope.
- **עוסק פטור specifics:** issues a קבלה on payment; must **not** issue a חשבונית מס; the חשבוניות-
  ישראל allocation number does **not** apply; documents should make clear no VAT is charged
  (already implemented in the current footer).

Confidence note: §5 fields and §5(ב) check fields are verbatim-statute (high confidence). The "must
print «עוסק פטור»/«no VAT»" wording is strong practitioner convention (already satisfied). Final
format to be confirmed by the user's רואה חשבון.

---

## In scope

### 1. Business profile — bank details + required address
`backend/app/schemas/business.py` (+ onboarding form, `frontend/app/onboarding/page.tsx`):
- Add optional `bankName`, `bankBranch`, `bankAccount` (strings) — the business's **receiving**
  account, rendered on bank-transfer receipts (nice-to-have, not gated).
- Make issuer `address` **required** at onboarding (§5). Existing businesses without it are handled
  by the warn path (see §6).

### 2. Receipt schema — check details, gated
`backend/app/schemas/receipt.py`:
- Add optional nested `checkDetails` object: `{ number: str, bank: str, branch: str, dueDate: str }`
  (dueDate is ISO `YYYY-MM-DD`).
- **Invariant:** `checkDetails` is populated **iff** `paymentMethod == "check"`; it is **null** for
  every other method ("state so and nullify"). No other per-method fields are added.
- Payment date = the existing `issueDate` (a קבלה is issued on receipt of payment). No new date field
  except the check `dueDate`.

### 3. Receipt PDF — `backend/app/templates/receipt.html`
- **«מקור»** rendered under the title.
- **«מסמך ממוחשב»** in the footer. Honest wording: we do **not** print «חתום דיגיטלית» until the
  document is actually signed (deferred).
- A **payment-details block** rendered by method:
  - `check` → check number / bank / branch / due date.
  - `bank_transfer` → the business's `bankName` / `bankBranch` / `bankAccount` from the profile, when set.
  - `cash` / `bit` / `paybox` / `credit_card` / `other` → method label + date + amount only.
  - Non-applicable fields are simply not rendered (no blank rows).
- **«סה"כ שולם»** total line.
- Issuer address and payer address rendered when present.
- Existing no-VAT / not-a-tax-invoice footer retained.

### 4. Chat capture — gate only when mandatory
`backend/app/services/chat_service.py`, `backend/app/utils/hebrew.py`, `backend/app/schemas/ai_commands.py`:
- `ReceiptPayload` gains optional check fields (`check_number`, `check_bank`, `check_branch`,
  `check_due_date`) so the parser can extract them inline (e.g. «צ'ק 123 לאומי סניף 800 לפירעון 1.5.26»).
- `compute_missing_fields`: when `payment_method == "check"`, the four check fields are required and
  any missing ones are added to `missing_fields`, triggering one follow-up question before
  confirmation. **No extra prompt for any non-check method.**
- `build_followup_question` gains the check-detail prompt.
- The executor maps the payload's check fields into the receipt's `checkDetails`; nulls it otherwise.
- Business bank details are entered in the profile/onboarding form, **not** via chat.

### 5. Validation
`backend/app/services/receipt_service.py`:
- If `paymentMethod == "check"`, require a complete `checkDetails` (all four fields) — surfaced as a
  chat follow-up, and as a 422 on the direct API path.
- For any non-check method, force `checkDetails = None` (never persist partial check data).

### 6. Payer address — warn, don't block
- Pull the payer address from the **client record** (`clientSnapshot.address`) when available.
- When missing, surface a **compliance warning** through the existing annual-report precheck
  (`report_service.precheck`) and/or the receipt detail view — **not** a hard block, to keep the fast
  chat flow intact. Same pattern as existing precheck warnings.

---

## Out of scope (deferred)

- **Digital signature / certificate** (qualified or secured), and the §18ב admin steps the *business
  owner* performs: notifying פקיד שומה (registered mail) and obtaining recipient consent. Open
  question — the user may add a platform-level signing certificate later; the PDF pipeline will be
  built to accept one then.
- **חשבונית עסקה** (non-tax demand-for-payment invoice).
- **Hard-gating** payer address (we warn instead).
- Account-number capture for checks (not statutory).

---

## Testing

- **PDF golden** (`backend/tests/test_pdf_golden.py` / report PDF tests): assert «מקור», «מסמך ממוחשב»,
  «סה"כ שולם» render; a check receipt shows number/bank/branch/due-date; a transfer receipt shows the
  profile bank details; a cash receipt shows neither.
- **Chat flow** (`backend/tests/integration/test_chat_*`): a check payment adds the check fields to
  `missing_fields` and the follow-up captures them; a non-check payment asks nothing extra and leaves
  `checkDetails` null.
- **Receipt service**: `checkDetails` required iff `paymentMethod == "check"`; forced null otherwise.
- **Business schema / onboarding**: bank fields persist and round-trip; address required.

---

## Open questions

1. Certificate level + provider for the eventual digital signature (deferred; user to decide with
   accountant — מאובטחת self-managed vs מאושרת accredited).
2. Final receipt format sign-off by the user's רואה חשבון.

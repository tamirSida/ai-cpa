# עוסק פטור Receipt Content + Signature Compliance — Design

**Goal:** Bring generated קבלה (receipt) PDFs into compliance with the Israeli bookkeeping directives —
the **§5 content/format** fields and the **§18ב computerized-document** rules — including an automated
**self-signed cryptographic signature** at the **מאובטחת (secured)** tier. Payment-instrument details
are captured **only where the law requires them** (checks). Per the chosen path (**Option B**), the
signature is a free self-signed certificate; cash receipts fall back to a hand-signed paper path.

**Status:** Approved design (decisions logged below), pending spec review → implementation plan.

---

## Decision log (verified, user-chosen)

- **§18ב accepts מאובטחת OR מאושרת** (disjunctive «או») — verified against the regulation text.
- **מאובטחת** = four technical criteria (unique, identifies signer, sole control, tamper-evident);
  **no CA required by definition**. A self-signed PKCS#12 applied as a PAdES signature meets them.
- **מאושרת** additionally needs a certificate from a registered Israeli גורם מאשר (only **Comsign** /
  **PersonalID** exist; cheapest confirmed ≈ **₪450/yr** PersonalID DocSigner, cloud API). **No free
  path to מאושרת.**
- **§18ב(ד) — payment restriction:** a document signed with **מאובטחת** (not מאושרת) may only be used
  when payment is **credit card / crossed non-negotiable check / bank transfer** — **not cash**.
- **User's choice = Option B:** free self-signed מאובטחת auto-signing, accepting (a) the gray area —
  no published רשות המסים approval of self-signed; weaker audit/evidentiary position — and (b) cash
  receipts cannot use this route. Upgrade path to מאושרת (swap to a Comsign/PersonalID cert) is left open.
- **Not legal advice:** sourced research only; the self-signed acceptability is an accepted-risk gray area.

---

## Legal basis (sourced)

Primary: **הוראות מס הכנסה (ניהול פנקסי חשבונות), התשל"ג-1973** ([Nevo](https://www.nevo.co.il/law_html/law01/255_179.htm), [Wikisource](https://he.wikisource.org/wiki/%D7%94%D7%95%D7%A8%D7%90%D7%95%D7%AA_%D7%9E%D7%A1_%D7%94%D7%9B%D7%A0%D7%A1%D7%94_(%D7%A0%D7%99%D7%94%D7%95%D7%9C_%D7%A4%D7%A0%D7%A7%D7%A1%D7%99_%D7%97%D7%A9%D7%91%D7%95%D7%A0%D7%95%D7%AA))); Electronic Signature Law, התשס"א-2001.

- **§5 fields:** serial number, issuer name + ID, **issuer address**, date, **payer name + address**
  (except retail cash), amount, nature of payment, recipient signature.
- **§5(ב) checks:** check number + bank + branch + due date.
- **§18ב:** «מסמך ממוחשב» label; payer copy «מקור»; signature waiver needs מאובטחת **or** מאושרת.
- **§18ב(ד):** מאובטחת-signed documents are limited to non-cash, traceable payment methods (see decision log).
- **עוסק פטור:** issues a קבלה; never a חשבונית מס; allocation number N/A; no VAT (already in footer).

---

## In scope

### 1. Business profile — bank details + required address
`backend/app/schemas/business.py` (+ onboarding):
- Optional `bankName`, `bankBranch`, `bankAccount` — receiving account, shown on transfer receipts.
- Issuer `address` **required** at onboarding (§5); existing businesses without it → warn path (§6).

### 2. Receipt schema — check details, gated
`backend/app/schemas/receipt.py`:
- Optional nested `checkDetails { number, bank, branch, dueDate }`, populated **iff**
  `paymentMethod == "check"`, **null** otherwise.

### 3. Receipt PDF — `backend/app/templates/receipt.html`
- **«מקור»** under the title.
- **«סה"כ שולם»** total; issuer + payer address when present; existing no-VAT footer retained.
- **Payment-details block** by method: check → number/bank/branch/due-date; bank-transfer → profile
  bank/branch/account (if set); cash/Bit/PayBox/card → method + date + amount. No blank rows.
- Footer signature line driven by a `signed: bool` flag:
  - `signed == true` → **«מסמך ממוחשב חתום דיגיטלית»**.
  - `signed == false` → **«מסמך ממוחשב»** + a Hebrew note that the receipt requires a **handwritten
    signature** (the cash/other path).

### 4. Chat capture — gate only when mandatory
`chat_service.py`, `hebrew.py`, `ai_commands.py`:
- `ReceiptPayload` gains optional `check_number/bank/branch/due_date`.
- `compute_missing_fields`: `payment_method == "check"` → the four fields required → one follow-up.
  No extra prompt for any other method. Executor maps them into `checkDetails` (null otherwise).
- Bank details are a profile/onboarding form, not chat.

### 5. Validation — `receipt_service.py`
- `checkDetails` required iff `paymentMethod == "check"`; forced null otherwise.

### 6. Payer address — warn, don't block
- Use `clientSnapshot.address` when present; when missing, surface a compliance warning via
  `report_service.precheck` (and the receipt detail view) — not a hard block.

### 7. Cryptographic signature — self-signed מאובטחת, payment-gated (Option B)
New: `backend/app/services/signing_service.py`, `backend/scripts/gen_signing_cert.py`; modify
`receipt_service.py`, `core/config.py`, `requirements.txt`, `.env.example`, `docker-compose.yml`.
- **Certificate:** ONE platform-level **self-signed** X.509 cert + key as **PKCS#12** (`.p12`, password),
  generated once via `scripts/gen_signing_cert.py` (`cryptography`), stored at
  `backend/secrets/receipt-signing.p12` (gitignored, Docker-mounted `:ro`). CN = platform name; ~5-yr validity.
- **Config:** `RECEIPT_SIGNING_P12_PATH` (default `secrets/receipt-signing.p12`),
  `RECEIPT_SIGNING_P12_PASSWORD` in Settings + `.env(.example)`.
- **Signing:** `signing_service.sign_pdf(pdf) -> bytes` uses **pyHanko** for an **invisible** PAdES
  signature from the PKCS#12. No visible widget; **no TSA**.
- **Eligibility gate (§18ב(ד)):** sign **only** when the cert is configured **and** the payment method
  is traceable — `paymentMethod ∈ {bank_transfer, bit, paybox, credit_card, check}`. For
  `{cash, other, unknown}` the PDF is **not** signed → `signed=false` → hand-sign note (§3).
  *(Assumptions: Bit/PayBox treated as transfer-equivalent per ITA practice; checks assumed crossed/
  non-negotiable — both flagged for the user.)*
- **Pipeline:** `render_pdf → (eligible ? sign_pdf) → upload_pdf`; localized to `_attach_pdf`. The
  `signed` flag is passed to the template before rendering (render decides text; signing happens after).
- **Graceful no-op:** cert unconfigured (dev/CI/tests) → `sign_pdf` is a no-op, `signed=false`.
- **Dependencies:** add `pyHanko` (+ `cryptography`) to `requirements.txt`.
- **Business-owner admin (not software):** §18ב notice to פקיד שומה + recipient consent; signed
  original retained in Cloudinary. Documented in `docs/smoke-test.md`.

---

## Out of scope (deferred / not software)

- **מאושרת upgrade** (Comsign/PersonalID, ~₪450/yr) — would lift the §18ב(ד) cash restriction and the
  gray area; the `.p12`/signing pipeline is built to accept a CA cert later (cloud-API CAs would need
  extra integration; a file-based CA `.p12` drops straight in).
- **TSA/LTV timestamp**, **חשבונית עסקה**, hard-gating payer address, check account-number capture.

---

## Testing

- **Signature** (`backend/tests/test_signing.py`): ephemeral self-signed `.p12` signs a sample PDF →
  pyHanko validation passes; a mutated byte fails validation (tamper-evidence); `sign_pdf` no-ops unconfigured.
- **Eligibility:** transfer/Bit/card/check receipt → signed, footer «חתום דיגיטלית»; **cash/other →
  unsigned, footer shows the hand-sign note**.
- **PDF golden:** «מקור», «מסמך ממוחשב», «סה"כ שולם»; check shows number/bank/branch/due-date; transfer
  shows profile bank; cash shows neither.
- **Chat flow:** check → follow-up captures details; non-check → asks nothing, `checkDetails` null.
- **Receipt service:** `checkDetails` required iff check; issuance signs only eligible methods when cert configured.
- **Business / onboarding:** bank fields round-trip; address required.

---

## Open questions

1. Final receipt format + the accepted self-signed gray area — sign-off by an accountant whenever the
   user has one (design is upgrade-ready to מאושרת).
2. Whether to later add מאושרת (to allow cash + remove the gray area) and/or a TSA timestamp.

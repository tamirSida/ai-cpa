# עוסק פטור Receipt Content + Signature Compliance — Design

**Goal:** Bring generated קבלה (receipt) PDFs into compliance with the Israeli bookkeeping directives —
both the **§5 content/format** fields and the **§18ב computerized-document** requirements, including a
**lightweight cryptographic signature** (the מאובטחת/secured tier). Payment-instrument details are
captured **only where the law requires them** (checks), keeping the common cash / transfer / Bit flows
friction-free.

**Status:** Approved design, pending spec review → implementation plan.

---

## Legal basis (researched, sourced)

Primary source: **הוראות מס הכנסה (ניהול פנקסי חשבונות), התשל"ג-1973** ([Nevo](https://www.nevo.co.il/law_html/law01/255_179.htm), [Wikisource](https://he.wikisource.org/wiki/%D7%94%D7%95%D7%A8%D7%90%D7%95%D7%AA_%D7%9E%D7%A1_%D7%94%D7%9B%D7%A0%D7%A1%D7%94_(%D7%A0%D7%99%D7%94%D7%95%D7%9C_%D7%A4%D7%A0%D7%A7%D7%A1%D7%99_%D7%97%D7%A9%D7%91%D7%95%D7%A0%D7%95%D7%AA))); Electronic Signature Law, התשס"א-2001.

- **§5 — mandatory receipt fields:** serial number, issuer name + ID number, **issuer address**, date,
  **payer name + address** (except retail cash), amount received, nature of payment (מהות התקבול),
  recipient signature.
- **§5(ב) — checks:** check number + bank + branch + due date (תאריך פירעון). *(Account number is
  common practice but not statutory — not required.)*
- **§18ב — computerized documents:** marked **«מסמך ממוחשב»**; payer's printed copy marked **«מקור»**;
  the handwritten-signature waiver requires a **חתימה אלקטרונית מאובטחת או מאושרת** (secured **or**
  qualified). We implement the **מאובטחת** (secured) tier — see §7.
- **מאובטחת criteria** (Electronic Signature Law): unique to the signer, identifies the signer, under
  the signer's sole control, and tamper-evident. A self-signed PKI certificate applied as a PAdES
  signature meets these; an accredited CA is required only for the higher **מאושרת** tier.
- **עוסק פטור:** issues a קבלה on payment; must **not** issue a חשבונית מס; the חשבוניות-ישראל
  allocation number does **not** apply; no VAT is charged (already in the footer).

Confidence: §5 / §5(ב) fields are verbatim statute. Whether רשות המסים accepts a **self-signed** cert
for the מאובטחת tier (vs. requiring an accredited CA / מאושרת) is the one judgment call — flagged for
the user's רואה חשבון; the design is upgrade-ready (swap the `.p12`).

---

## In scope

### 1. Business profile — bank details + required address
`backend/app/schemas/business.py` (+ onboarding `frontend/app/onboarding/page.tsx`):
- Add optional `bankName`, `bankBranch`, `bankAccount` (strings) — the business's **receiving**
  account, rendered on bank-transfer receipts (nice-to-have, not gated).
- Make issuer `address` **required** at onboarding (§5). Existing businesses without it → warn path (§6).

### 2. Receipt schema — check details, gated
`backend/app/schemas/receipt.py`:
- Add optional nested `checkDetails { number: str, bank: str, branch: str, dueDate: str }` (ISO date).
- **Invariant:** populated **iff** `paymentMethod == "check"`; **null** for every other method.
- Payment date = existing `issueDate`. No new date field besides the check `dueDate`.

### 3. Receipt PDF — `backend/app/templates/receipt.html`
- **«מקור»** under the title.
- Footer: **«מסמך ממוחשב חתום דיגיטלית»** when the PDF was actually signed (§7); falls back to
  **«מסמך ממוחשב»** (no «חתום דיגיטלית») when signing isn't configured — controlled by a `signed: bool`
  template flag (honest in both cases).
- **Payment-details block** by method: check → number/bank/branch/due-date; bank-transfer → profile
  bank/branch/account (if set); cash/Bit/PayBox/card → method + date + amount only. No blank rows.
- **«סה"כ שולם»** total line; issuer + payer address when present; existing no-VAT footer retained.

### 4. Chat capture — gate only when mandatory
`backend/app/services/chat_service.py`, `backend/app/utils/hebrew.py`, `backend/app/schemas/ai_commands.py`:
- `ReceiptPayload` gains optional `check_number`, `check_bank`, `check_branch`, `check_due_date` so the
  parser can extract them inline (e.g. «צ'ק 123 לאומי סניף 800 לפירעון 1.5.26»).
- `compute_missing_fields`: when `payment_method == "check"`, the four fields are required → missing
  ones go to `missing_fields` → one follow-up before confirmation. **No extra prompt for non-check.**
- `build_followup_question` gains the check prompt; the executor maps payload check fields into
  `checkDetails` (null otherwise). Bank details are a profile/onboarding form, not chat.

### 5. Validation — `backend/app/services/receipt_service.py`
- If `paymentMethod == "check"`, require complete `checkDetails` (all four) — chat follow-up, and 422 on
  the direct API path. For any non-check method, force `checkDetails = None`.

### 6. Payer address — warn, don't block
- Use the client record's address (`clientSnapshot.address`) when present. When missing, surface a
  **compliance warning** via the existing `report_service.precheck` (and the receipt detail view) — not
  a hard block. Same pattern as existing precheck warnings.

### 7. Cryptographic signature — lightweight מאובטחת (platform-level)
New: `backend/app/services/signing_service.py`, `backend/scripts/gen_signing_cert.py`; modify
`backend/app/services/receipt_service.py`, `backend/app/core/config.py`, `backend/requirements.txt`,
`backend/.env.example`, `docker-compose.yml`.
- **Certificate:** ONE platform-level **self-signed** X.509 cert + private key, packaged as **PKCS#12**
  (`.p12`) with a password. Generated once via `scripts/gen_signing_cert.py` (using `cryptography`);
  stored at `backend/secrets/receipt-signing.p12` (gitignored, mounted `:ro` in Docker like
  `firebase-sa.json`). Subject CN = the platform/app name; ~5-year validity. Like Invoice4U signing
  with its own system cert; the business's identity is in the receipt **content**.
- **Config:** `RECEIPT_SIGNING_P12_PATH` (default `secrets/receipt-signing.p12`) +
  `RECEIPT_SIGNING_P12_PASSWORD` in Settings + `.env(.example)`.
- **Signing:** `signing_service.sign_pdf(pdf: bytes) -> bytes` uses **pyHanko** to apply an **invisible**
  PAdES signature over the whole document, loaded from the PKCS#12. No visible widget; **no TSA**
  (kept offline/lightweight — timestamp/LTV is a future add).
- **Pipeline:** receipt issuance becomes `render_pdf → sign_pdf → upload_pdf`; the stored + delivered
  PDF is signed. Localized to `_attach_pdf`.
- **Graceful degradation:** if the cert isn't configured (dev/CI/tests), `sign_pdf` is a no-op and the
  template renders without «חתום דיגיטלית». When configured (prod), the PDF is signed and the footer
  shows it.
- **Dependencies:** add `pyHanko` (+ `cryptography`, likely already transitive) to `requirements.txt`.
  WeasyPrint output is standard, signable PDF.
- **Business-owner admin (not software):** §18ב also requires the owner to notify their פקיד שומה
  (registered mail) before first issuing computerized docs and to obtain recipient consent; the signed
  original is retained in Cloudinary. Documented as ops notes in `docs/smoke-test.md`.

---

## Out of scope (deferred / not software)

- **מאושרת (qualified) upgrade:** swapping the self-signed `.p12` for an accredited-CA cert (future,
  if the accountant requires it — pipeline already accepts any `.p12`).
- **Trusted timestamp (TSA) / LTV** for long-term signature validation.
- **חשבונית עסקה** (non-tax demand-for-payment invoice).
- **Hard-gating** payer address (we warn instead) and account-number capture for checks (not statutory).

---

## Testing

- **Signature** (`backend/tests/test_signing.py`, new): generate an ephemeral self-signed `.p12`, sign a
  sample WeasyPrint PDF, assert pyHanko validation reports a valid signature; mutating one byte makes
  validation fail (tamper-evidence). `sign_pdf` is a no-op when unconfigured.
- **PDF golden:** assert «מקור», «מסמך ממוחשב», «סה"כ שולם»; check receipt shows number/bank/branch/
  due-date; transfer shows profile bank; cash shows neither; footer shows «חתום דיגיטלית» only when signed.
- **Chat flow:** check payment → follow-up captures check details; non-check → asks nothing, `checkDetails` null.
- **Receipt service:** `checkDetails` required iff check, forced null otherwise; issuance signs the PDF
  when the cert is configured.
- **Business schema / onboarding:** bank fields round-trip; address required.

---

## Open questions

1. Final receipt format + acceptability of a **self-signed** מאובטחת cert — sign-off by the user's
   רואה חשבון (design is upgrade-ready to a CA cert).
2. Whether to add a trusted timestamp (TSA) later for long-term validation.

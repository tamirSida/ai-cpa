# Production Hardening & Smoke Test

End-to-end checklist for taking the AI Bookkeeper to production and proving it works
against **real** services (Firebase Auth + Firestore, OpenAI, Cloudinary) — not the
emulator/stubs the 186 automated tests run against.

Replace every `<placeholder>` with your real value. Secrets live only in the VPS
`/opt/tax/.env` and `firebase-sa.json` (mode `600`) — never commit them.

---

## Part A — Hardening (run once, in order)

### A1. Deploy deny-all Firestore security rules

The backend talks to Firestore through the **Firebase Admin SDK**, which bypasses
security rules. The browser never reads or writes Firestore directly — it only uses
Firebase **Auth** and sends ID tokens to the API. So client access must be fully closed.

`firestore.rules` (already in the repo) contains exactly:

```txt
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

Deploy to **both** projects:

```bash
firebase deploy --only firestore:rules --project <dev-project-id>
firebase deploy --only firestore:rules --project <prod-project-id>
```

- [ ] **Verify:** in the deployed web app, open browser devtools console and run a direct
  client read. It must fail with `permission-denied`:
  ```js
  // paste in devtools on the live site (Firebase SDK is loaded)
  const { getFirestore, doc, getDoc } = await import("firebase/firestore");
  await getDoc(doc(getFirestore(), "businesses/anything")); // → FirebaseError: Missing or insufficient permissions
  ```

### A2. Deploy composite indexes

The Firestore emulator **does not enforce** composite indexes, so index correctness is
unverified until it runs against a real project.

```bash
firebase deploy --only firestore:indexes --project <dev-project-id>
firebase deploy --only firestore:indexes --project <prod-project-id>
```

Then exercise every indexed query against the **real dev project** and confirm there are
no `FAILED_PRECONDITION: The query requires an index` errors:

- [ ] `GET /api/businesses/{id}/receipts?year=2026` (status + issueDate)
- [ ] `GET /api/businesses/{id}/receipts` recent (status + issuedAt DESC)
- [ ] client-revenue query (status + clientSnapshot.name)
- [ ] `GET /api/businesses/{id}/expenses?status=needs_review` (status + expenseDate)
- [ ] dashboard load + annual-report precheck (exercise the above)
- [ ] `docker compose -f /opt/tax/docker-compose.prod.yml logs api | grep -i "requires an index"` → empty

> If an index is missing, the error message contains a console URL that creates it.
> Add the field combo to `firestore.indexes.json` and re-deploy so it stays in version control.

### A3. Cloudinary — allow PDF/ZIP delivery

Free Cloudinary plans **block** raw PDF/ZIP delivery by default, which would 401 the
receipt-PDF and annual-ZIP downloads.

- [ ] Console → Settings → Security → **"PDF and ZIP files delivery"** → **Allow**.
- [ ] **Verify** with a real issued receipt's `pdfUrl`:
  ```bash
  curl -sI "<pdfUrl-of-a-real-issued-receipt>" | head -1   # → HTTP/2 200
  ```

### A4. VPS / deploy review

- [ ] `ssh <vps> 'ls -l /opt/tax/.env /opt/tax/firebase-sa.json'` → both `-rw-------`
  (`chmod 600` if not)
- [ ] `docker-compose.prod.yml` mounts `firebase-sa.json:ro`
- [ ] `ssh <vps> 'ufw status'` → only `22/80/443` allowed
- [ ] `ssh <vps> 'docker compose -f /opt/tax/docker-compose.prod.yml ps'` → `api` + `caddy` healthy
- [ ] `curl https://<api-domain>/healthz` → `{"status":"ok"}`
- [ ] `/opt/tax/.env` has prod `FIREBASE_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`,
  `OPENAI_API_KEY`, `CLOUDINARY_URL`, `CORS_ORIGINS` = exactly the Netlify origin, `ENV=prod`
- [ ] Netlify env has the four `NEXT_PUBLIC_FIREBASE_*` + `NEXT_PUBLIC_API_BASE_URL` (= `https://<api-domain>/api`)
- [ ] Netlify production domain is listed in **Firebase Auth → Settings → Authorized domains**

---

## Part B — Production end-to-end smoke test

Run on the **live** Netlify URL, on a real phone (iPhone Safari preferred — exercises HEIC
upload, the on-screen keyboard, and the Files-app ZIP download). Check off every step; if
any fails, fix → redeploy → restart this section from step 1.

1. [ ] Open the Netlify URL → **Google sign-in** completes, lands on onboarding (or chat).
2. [ ] **Onboarding:** create business «סטודיו בדיקה», a valid ת.ז, address, receipt prefix `2026`.
3. [ ] **/clients:** create client «נועה».
4. [ ] **Chat:** send «קיבלתי 2800 מנועה על עיצוב לוגו בביט» → get a Hebrew confirmation
   question → reply «אישור» → expect «נוצרה קבלה מספר 2026-0001».
   *(This is the first time the real OpenAI parser runs — confirm it extracted amount 2800,
   client נועה, payment ביט.)*
5. [ ] **/receipts:** download the receipt PDF → Hebrew renders RTL, the receipt number
   `2026-0001` is LTR, ₪ amount correct.
6. [ ] **Expense photo:** upload a receipt photo (HEIC from iPhone) → vision extraction shows
   fields → review & **approve**.
7. [ ] **/dashboard:** income shows **₪2,800**, one approved expense, threshold bar renders.
8. [ ] **Chat:** «כמה כסף עשיתי השנה?» → answer contains **₪2,800**.
9. [ ] **/annual-report:** run «בדיקה מקדימה» (expect clean or only the seeded items) →
   «צור דוח שנתי» → ZIP downloads (iPhone: saved to **Files → Downloads**).
10. [ ] **Unzip:** open `income.csv`, `expenses.csv`, `clients.csv` in Excel → Hebrew intact
    (UTF-8 BOM); open `summary.pdf` and `missing_items.pdf` → RTL correct;
    `receipt_pdfs/2026-0001.pdf` opens.
11. [ ] **Firestore console:** `annualReports/2026` document exists and an
    `annual_report_generated` ledger event was written.
12. [ ] **No tax submission** anywhere — the app never files to רשות המסים (design §19.12).

---

## Part C — Wrap up

- [ ] Any failure above: fix, `docker compose ... up -d --build` (or Netlify redeploy), re-run Part B.
- [ ] Tear down test data (delete the «סטודיו בדיקה» business) or keep it as a known-good fixture.
- [ ] Record the run date + commit SHA here:

| Run date | Commit | Result | Notes |
|----------|--------|--------|-------|
|          |        |        |       |

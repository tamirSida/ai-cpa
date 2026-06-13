# Test Plan

How this app is tested, where the gaps are, and exactly what to wire up to close them.

## Layer 0 — Automated suite (exists today, 186 tests green)

Unit + Firestore-emulator integration. **External services are faked:** OpenAI via
`StubCommandParser`, Cloudinary monkeypatched, Firebase ID-token verification overridden
(`dependency_overrides`), Firestore via the emulator.

```bash
cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test .venv/bin/pytest -q
cd frontend && npx tsc --noEmit && npm run build   # frontend has no unit tests yet — see Layer 2
```

This layer is strong on business logic: receipt atomic numbering + concurrency, expense
deductible math, chat state machine, aggregation, precheck, CSV/ZIP assembly, PDF goldens.

## Why more is needed

The emulator + stubs **cannot** exercise, and a regression in any of these is invisible today:

| Blind spot | Why the suite misses it |
|---|---|
| Real OpenAI command parsing | `StubCommandParser` bypasses the prompt + Responses structured-output contract entirely. |
| Real OpenAI vision extraction | Stub returns a canned `ExpenseExtraction`; the `input_image` URL path never runs. |
| Real Cloudinary upload/fetch | `upload_pdf`/`upload_image`/`fetch_asset` are monkeypatched everywhere. |
| **Firestore composite-index enforcement** | The emulator ignores `firestore.indexes.json` and accepts any compound query. |
| Real Firebase token verification | `get_current_uid` is overridden to `"test-uid"`; JWKS/audience/expiry never checked. |
| Whole frontend | Zero component/page tests exist. |
| Full PDF/ZIP chain | `render_pdf` + `fetch_asset` are both faked in the ZIP test. |

## Layer 1 — Env-gated live integration smokes (backend, new `tests/live/`)

Each test **skips unless its env var is set**, so the default suite stays hermetic and CI stays
offline. Add `@pytest.mark.skipif(not os.getenv(VAR), reason=...)`. Cost is a few cents total.

| Smoke | Env gate(s) | Asserts |
|---|---|---|
| OpenAI command parse | `OPENAI_API_KEY` | `parse_user_command(ctx, "קיבלתי 2800 מנועה על עיצוב לוגו בביט")` → `intent == CREATE_RECEIPT`, `receipt.amount == 2800`, client נועה, payment `bit`. |
| OpenAI vision | `OPENAI_API_KEY` + a permanent test image URL | `extract_expense(url)` → `ExpenseExtraction`, `amount` plausible, `currency in (ILS, None)`. |
| Cloudinary round-trip | `CLOUDINARY_URL` | `upload_pdf(b"%PDF…", public_id="smoke_test/…")` → `secure_url` reachable via `fetch_asset()` returns identical bytes → then `destroy()` cleans up. |
| Firestore indexes | real `GOOGLE_CLOUD_PROJECT` (non-`demo-`) + `GOOGLE_APPLICATION_CREDENTIALS`, indexes deployed | seed a receipt, run each compound query in `aggregation_service` (status+issueDate, +clientSnapshot.name, +issuedAt DESC) and the expenses query → **no `FAILED_PRECONDITION`**. |
| `pendingActions` query | same as above | seed a `pendingActions` doc, call `_load_active_action` → no index error. *(Expected to pass without a composite index: it's `threadId == … AND status in […]`, equality+`in`, no `orderBy`. This smoke confirms that assumption against real Firestore.)* |
| Firebase auth | a real `FIREBASE_ID_TOKEN` (mint via the Auth REST API with a test user) | `GET /api/businesses` with `Authorization: Bearer <token>` → `200`/`404`, not `401`/`500` (validates project ID, JWKS, audience). |

Run, e.g.: `OPENAI_API_KEY=… CLOUDINARY_URL=… .venv/bin/pytest tests/live -q`.

## Layer 2 — Frontend tests (new, recommended)

Currently **zero**. Set up Vitest + React Testing Library and add, at minimum:
1. `lib/format.ts` — `formatILS` keeps agorot, `he-IL` formatting.
2. `lib/labels.ts` — enum→Hebrew maps.
3. `apiClient` — `api()`/`apiBlob()` attach `Authorization`, parse `detail.message`, redirect on persistent 401.
4. `ConfirmActionCard` — renders Hebrew confirm/cancel buttons from a mock action.
5. `annual-report/page` logic — the year-switch precheck guard, the generate-disabled gate, the `fetchError` card (the bugs just fixed in this page warrant a regression test).

## Layer 3 — Production end-to-end smoke (manual) → `docs/smoke-test.md`

The 12-step script on the live Netlify URL + the Part A hardening checklist. This is the
only layer that proves the full Auth→OpenAI→Cloudinary→Firestore→PDF/ZIP chain on a real phone.

## Env matrix (what each layer needs)

| Layer | Env / inputs |
|---|---|
| 0 automated | `FIRESTORE_EMULATOR_HOST`, `GOOGLE_CLOUD_PROJECT=demo-tax-test` (emulator running) |
| 1 OpenAI smokes | `OPENAI_API_KEY` |
| 1 Cloudinary smoke | `CLOUDINARY_URL` |
| 1 Firestore/auth smokes | real `GOOGLE_CLOUD_PROJECT` + `GOOGLE_APPLICATION_CREDENTIALS` (indexes deployed) + `FIREBASE_ID_TOKEN` |
| 2 frontend | none (Vitest is offline) |
| 3 production e2e | full prod deploy (see `docs/env-vars.md` → "What you must provide") |

## Recommended sequence

1. **Layer 0** — already green; keep it the CI gate.
2. **OpenAI + Cloudinary live smokes** — cheapest, highest-value: just `OPENAI_API_KEY` + `CLOUDINARY_URL` in `backend/.env`, run `pytest tests/live`. This is the "few smoke tests" worth doing first.
3. **Firestore index + auth smokes** — once a dev Firebase project + service-account JSON exist and `firebase deploy --only firestore:indexes` has run.
4. **Layer 2 frontend tests** — in parallel, no external deps.
5. **Layer 3 production e2e** — after the first deploy, run `docs/smoke-test.md` end to end.

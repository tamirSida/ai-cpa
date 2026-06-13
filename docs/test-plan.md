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

## Layer 1 — Env-gated live integration smokes (backend, `tests/live/`) — IMPLEMENTED

Lives in `backend/tests/live/`. Gating is two-layered so the default suite stays hermetic and CI
stays offline: (1) a **master switch** — every test skips unless `RUN_LIVE_SMOKE=1`; (2) **per-service
fixtures** that skip when their credential is missing (read from the gitignored `backend/.env` and
`backend/secrets/firebase-sa.json` — nothing hardcoded). The suite overrides the root conftest's
emulator-only autouse fixtures, so it needs no emulator. Cost is a few cents total.

Run it (from `backend/`):
```bash
RUN_LIVE_SMOKE=1 .venv/bin/python -m pytest tests/live -v
```

| Smoke | File | Gate | Asserts |
|---|---|---|---|
| OpenAI command parse | `test_openai_live.py` | `OPENAI_API_KEY` | real parse of «קיבלתי 2800 מנועה על עיצוב לוגו בביט» → `CREATE_RECEIPT`, amount 2800, client נועה, payment `bit`. |
| OpenAI vision | `test_openai_live.py` | `OPENAI_API_KEY` + `LIVE_RECEIPT_IMAGE_URL` | `extract_expense(url)` → `ExpenseExtraction`, amount > 0, `currency in (ILS, None)`. *(Opt-in: set `LIVE_RECEIPT_IMAGE_URL` to a real receipt photo; skips otherwise.)* |
| Cloudinary round-trip | `test_cloudinary_live.py` | `CLOUDINARY_URL` | `upload_pdf` → `fetch_asset` returns identical bytes (proves delivery is enabled) → `destroy`. |
| Cloudinary full chain | `test_cloudinary_live.py` | `CLOUDINARY_URL` | `render_pdf` (real WeasyPrint Hebrew PDF) → upload → fetch → `%PDF` + size match → `destroy`. |
| Firestore indexes | `test_firestore_live.py` | real project + `secrets/firebase-sa.json` | seed a receipt+expense, run the four indexed `aggregation_service` queries (status+issueDate, +clientSnapshot.name, +issuedAt DESC, expenses status+expenseDate) → **no `FAILED_PRECONDITION`** → cleanup. |
| Firebase auth | `test_firebase_auth_live.py` | real project + SA + web API key | mint custom token → exchange for a real ID token (Identity Toolkit) → `verify_id_token` → uid/aud/iss match → delete user. Exercises the exact `get_current_uid` path, no browser needed. |

Status: **5 passing live, 1 (vision) opt-in.** Running the default `pytest` (emulator) leaves them
skipped — verified **186 passed + 6 skipped**, no regression.

> Note on `pendingActions`: `_load_active_action` filters `threadId == … AND status in […]` with no
> `orderBy`. Equality + `in` is served by single-field indexes (merge join), so it needs **no**
> composite index — confirmed by reasoning + the live index smoke run; no separate test required.

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

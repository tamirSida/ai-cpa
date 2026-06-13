# Environment Variables

Complete inventory, derived from `backend/app/core/config.py`, every `os.environ` use in
`backend/`, every `process.env` use in `frontend/`, `docker-compose.yml`, `ci.yml`, and
`backend/tests/conftest.py`. Independently re-scanned — no variables are read anywhere else.

Legend: **Req** = required at runtime · **Secret** = must never be committed/exposed.

## Backend — FastAPI runtime (`/opt/tax/.env` on the VPS, `env_file` in compose)

| Variable | Req | Secret | Default | Purpose |
|---|---|---|---|---|
| `FIREBASE_PROJECT_ID` | ✅ | — | — | Project ID for `firebase-admin` + the Firestore client. |
| `GOOGLE_APPLICATION_CREDENTIALS` | ✅ | path→🔑 | `/code/secrets/firebase-sa.json` | Path to the Firebase service-account JSON. The **file** is the secret; mount it `:ro`, mode `600`. Skipped when `FIRESTORE_EMULATOR_HOST` is set. |
| `OPENAI_API_KEY` | ✅ | 🔑 | — | OpenAI key for chat command parsing + vision expense extraction. |
| `OPENAI_COMMAND_MODEL` | — | — | `gpt-4.1-mini` | Model for Hebrew NLU command parsing. |
| `OPENAI_VISION_MODEL` | — | — | `gpt-4.1-mini` | Model for receipt-photo extraction. |
| `CLOUDINARY_URL` | ✅ | 🔑 | — | `cloudinary://key:secret@cloud`. Read by the SDK at import; also forced from settings in `cloudinary_service`. |
| `CORS_ORIGINS` | — | — | `["http://localhost:3000"]` | JSON array. **In prod must be exactly the Netlify origin.** |
| `ANNUAL_LIMIT_ILS` | — | — | `122833` | עוסק פטור 2026 ceiling; updated annually. |
| `ENV` | — | — | `dev` | `dev` \| `prod` \| `test`. |

### Backend — set automatically (not operator-supplied; listed for awareness)
| Variable | Where | Note |
|---|---|---|
| `FIREBASE_AUTH_EMULATOR_HOST` | `core/firebase.py` (`setdefault` when emulator detected) | Only relevant if you run the Auth emulator on a non-default port. |
| `XDG_CACHE_HOME` | `services/pdf_service.py` (`setdefault` `/tmp/cache`) | WeasyPrint/fontconfig cache dir for non-root Docker. A conflicting container value could break PDF font caching. |

## Frontend — Next.js build-time (Netlify env). All baked into the client bundle.

| Variable | Req | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | ✅ | — | Firebase web app key. **Not a secret** — it's a public client identifier; protect it by restricting the key in GCP console + Firebase Auth authorized domains, not by hiding it. |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | ✅ | — | Auth domain for the Google sign-in flow. |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | ✅ | — | Routes SDK Firestore/Auth calls. |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | ✅ | — | Web app registration ID (`1:NNN:web:HASH`). |
| `NEXT_PUBLIC_API_BASE_URL` | ✅ (prod) | `http://localhost:8000/api` | FastAPI base URL, **no trailing slash**, e.g. `https://api.yourdomain.com/api`. |

## Test-only (CI + local pytest)

| Variable | Req | Default | Purpose |
|---|---|---|---|
| `FIRESTORE_EMULATOR_HOST` | ✅ for tests | — | Points firebase-admin/google-cloud-firestore at the local emulator. `localhost:8080`. Conftest exits if unset. |
| `GOOGLE_CLOUD_PROJECT` | ✅ for tests | `demo-tax-test` | Emulator project ID. The `demo-` prefix keeps the emulator fully offline. |

## What **you** must provide, by deploy target

- **VPS `/opt/tax/.env`:** `FIREBASE_PROJECT_ID`, `OPENAI_API_KEY` 🔑, `CLOUDINARY_URL` 🔑, `CORS_ORIGINS`=Netlify origin, `ENV=prod` (models/limit optional).
- **VPS `/opt/tax/firebase-sa.json`** 🔑 (mode `600`) — the service-account JSON; `GOOGLE_APPLICATION_CREDENTIALS` points at it.
- **Netlify env:** the four `NEXT_PUBLIC_FIREBASE_*` + `NEXT_PUBLIC_API_BASE_URL`.
- **Live smoke tests (local, optional):** `OPENAI_API_KEY` 🔑, `CLOUDINARY_URL` 🔑, a real (non-`demo-`) `GOOGLE_CLOUD_PROJECT` + `GOOGLE_APPLICATION_CREDENTIALS` with indexes deployed, and a `FIREBASE_ID_TOKEN` for the auth smoke. See `docs/test-plan.md`.

> 🔑 secrets go only in the gitignored `backend/.env`, the VPS `.env`, `backend/secrets/`,
> or `! export` — never pasted into chat, committed, or logged.

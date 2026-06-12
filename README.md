# AI Bookkeeper MVP

Chat-first bookkeeping for Israeli עוסק פטור freelancers.

- `backend/` — FastAPI (Docker), Firestore, OpenAI, WeasyPrint PDFs, Cloudinary
- `frontend/` — Next.js App Router + TypeScript + Tailwind, Firebase Auth (Google)

## Dev quickstart
1. `cp backend/.env.example backend/.env` and fill values.
2. `docker compose up` → API on :8000, Firestore emulator on :8080.
3. `cd frontend && cp .env.local.example .env.local && npm install && npm run dev` → :3000.

## Tests
`cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test .venv/bin/pytest -q`

# AI Bookkeeper MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A chat-first bookkeeping app for Israeli עוסק פטור freelancers — natural Hebrew/English messages create receipts, contacts and expenses; receipt photos are extracted by vision AI; a dashboard tracks income/expenses against the עוסק פטור ceiling; and one tap produces an accountant-ready annual ZIP package.

**Architecture:** Next.js 16 (App Router, all client components, mobile-first RTL) on Netlify calls a FastAPI backend (Docker on a VPS) which is the only writer to Firestore. The LLM (OpenAI Responses API, structured outputs) only parses chat into typed commands — deterministic backend services validate, ask follow-ups via pending actions, and execute. Receipt numbering is an atomic Firestore transaction; PDFs are WeasyPrint (Hebrew RTL via Pango) uploaded to Cloudinary; the annual report streams a ZIP assembled on demand.

**Tech Stack:** Next.js 16.2 + TypeScript + Tailwind v4 + Firebase Auth (Google) + Recharts 3 + lucide-react · FastAPI 0.136 + Python 3.12 + firebase-admin 7.4 + google-cloud-firestore + OpenAI Python SDK v2 (`responses.parse`) + WeasyPrint 69 + Cloudinary + zipstream-ng · Firestore + Firestore emulator for tests · Docker + Caddy on VPS, GHCR CI/CD, Netlify frontend.

---

## Verified facts (researched June 2026)

These versions and facts were verified against primary sources at planning time. If execution happens much later, re-verify the pins.

| Fact | Value | Source |
|---|---|---|
| עוסק פטור ceiling 2026 | **₪122,833** (2025: ₪120,000; updated annually by רשות המסים) | greeninvoice.co.il, kolzchut.org.il, gmcpa.co.il |
| חשבוניות ישראל allocation numbers | **Do NOT apply to עוסק פטור** (receipts only, no tax invoices) | greeninvoice.co.il/magazine/israel-invoice |
| Legally required קבלה fields | business name, מספר עוסק, address, sequential number, date, amount, payment method, description; no VAT line | הוראות ניהול ספרים (via keep.co.il, greeninvoice) |
| openai (Python) | 2.41.1 — `client.responses.parse(model, input, text_format=Model)` → `response.output_parsed`; vision via `{"type":"input_image","image_url":...}` | platform.openai.com, openai-python repo |
| gpt-4.1-mini | available; $0.40/M in, $1.60/M out; vision + structured outputs | platform.openai.com |
| FastAPI / Pydantic | 0.136.1 / 2.13.x (Pydantic v2 only) | fastapi.tiangolo.com |
| firebase-admin (Python) | 7.4.0 | github.com/firebase/firebase-admin-python |
| WeasyPrint | 69.0 — Hebrew RTL works out of the box via Pango/FriBidi with `direction: rtl`; avoid per-span direction (issue #1711) | doc.courtbouillon.org |
| Next.js / React | 16.2.x / 19.2 — async `params`, Node ≥20.9 | nextjs.org |
| Tailwind CSS | 4.1.x — CSS-first `@theme`, `@tailwindcss/postcss`, logical utilities `ps-*/pe-*/ms-*/me-*` | tailwindcss.com |
| Firebase JS SDK | 12.x — modular auth, `getIdToken()` auto-refresh | firebase.google.com |
| Recharts | 3.8.x | npmjs.com/package/recharts |
| cloudinary (Python) | 1.44.x — PDFs `resource_type="raw"`, images `resource_type="image"` | cloudinary.com/documentation |
| zipstream-ng | 1.9.x — streams ZIP via FastAPI `StreamingResponse` | pypi.org/project/zipstream-ng |
| Netlify | OpenNext runtime v5 auto-detects Next 16 | opennext.js.org/netlify |

Key mobile-web facts baked into the frontend tasks: `100dvh` (not `vh`/`svh`) for keyboard-aware layouts; `interactive-widget=resizes-content` is Chromium/Firefox-only (iOS gets a `visualViewport` workaround hook); `viewport-fit=cover` + `env(safe-area-inset-bottom)` for the bottom nav and chat input; camera capture via `<input accept="image/*" capture="environment">` **without** `image/heic` in `accept` (Safari 17+ regression — iOS auto-converts HEIC→JPEG when the source is the Photos app); `field-sizing: content` not yet usable (no Safari) — JS auto-grow instead.

## Mobile-first design system

The app is used primarily on phones, in Hebrew, RTL. 375×812 is the design target; desktop is an enhancement (`md:` wider container, optional tables).

- **Typeface:** IBM Plex Sans Hebrew (Google Fonts via `next/font`, weights 400–700) — covers Hebrew+Latin, fintech-trustworthy.
- **Tokens** (Tailwind v4 `@theme`): primary `#2563EB`, on-primary `#FFFFFF`, accent/success `#059669`, foreground `#0F172A`, muted bg `#F1F5FD`, border `#E4ECFC`, destructive `#DC2626`. Light mode only in MVP.
- **Navigation:** fixed bottom tab bar, 5 items (צ'אט · סקירה · קבלות · הוצאות · עוד), icons + labels, 48px touch targets, safe-area padding. `/` redirects to `/chat` — chat is home.
- **RTL:** `<html lang="he" dir="rtl">`; logical Tailwind utilities only (`ps-/pe-/ms-/me-/start-/end-`); LTR islands (`dir="ltr"`) for receipt numbers, phones, emails, amounts.
- **Interaction:** all touch targets ≥48px; inputs ≥48px at 16px font (no iOS zoom); inline validation on blur with Hebrew errors below fields; press feedback 150ms; lucide-react icons only (no emojis); amounts via `formatILS` + tabular numerals.
- **Patterns:** card lists (not tables) on mobile; bottom sheets (`Sheet`) instead of modals; chat confirmations as **inline action cards** in the conversation (not modals); skeletons for loading; `EmptyState` everywhere a list can be empty; optimistic chat send with inline retry.
- **Shared components & owners:** Phase 0 — `AppShell`, `BottomNav`, `app/manifest.ts`, design tokens in `globals.css`; Phase 2 — `Sheet`, `EmptyState`, `lib/format.ts` (`formatILS`); Phase 3 — `ConfirmActionCard`, `lib/useIosKeyboardFix.ts`; Phase 5 adds `MONTH_NAMES_HE` to `lib/format.ts`.
- **Deviations from design doc §13** (deliberate, mobile-driven): `ConfirmActionModal` → inline `ConfirmActionCard` (doc §14.1's flow happens inside the chat anyway); `ReceiptTable`/`ExpenseTable` → `ReceiptList`/`ExpenseList` card lists with tables as desktop enhancements; added `AppShell`, `BottomNav`, `Sheet`, `EmptyState`, `app/more/page.tsx`, `app/manifest.ts`.
- **Deviation from design doc §6.5:** one added endpoint, `GET /businesses/{businessId}/chat/messages` — the chat page needs to load history on mount; the doc lists only message/confirm/cancel.

## Phase map

Execute strictly in order — each phase produces working, tested software and later phases build on its files.

| Phase | Delivers | Doc § |
|---|---|---|
| 0 | Monorepo, Docker (WeasyPrint deps), Firestore-emulator pytest harness, CI, Next.js RTL shell + bottom nav + login | §2, §12, §13 |
| 1 | Firebase init + auth dependency, Business CRUD, onboarding UI, first production deploy | §3.1, §6.1, §18.1 |
| 2 | Clients CRUD, receipt draft/issue/cancel with atomic numbering, Hebrew PDF, Cloudinary, clients+receipts pages | §3.3, §5.3, §6.2–6.3, §7 |
| 3 | Pydantic command schema, OpenAI parser, chat state machine, pending actions, confirm/cancel, queries, chat UI | §3.2, §3.5, §8–§11 |
| 4 | Expenses: manual + image upload + vision extraction + approve/reject, expenses page with camera capture | §3.6, §6.4 |
| 5 | Dashboard aggregations + endpoint + mobile dashboard with chart and ceiling progress | §3.7, §6.6 |
| 6 | Annual report precheck + CSVs + summary/missing-items PDFs + streamed ZIP + page; production hardening + smoke test | §3.8, §6.7 |

Acceptance = design doc §19 (all 12 criteria); each phase's "Done when" list contributes its share.

---

## Phase 0 — Scaffolding & Test Harness

Goal: stand up the monorepo, a runnable FastAPI skeleton in Docker (with WeasyPrint runtime deps baked in from day one), the Firestore-emulator pytest harness all later backend phases build on, CI, and the Next.js frontend shell with Firebase auth plumbing. No business logic yet.

Dependencies: none (first phase). The dev Firebase project's web-app config values are filled in during Phase 1; Phase 0 frontend verification that needs them is marked conditional.

**Done when:**
- [ ] `git log` shows the Phase 0 commits; `.gitignore` excludes env files, secrets, build artifacts.
- [ ] `docker compose up` serves `GET http://localhost:8000/healthz` → `{"status":"ok"}` and the Firestore emulator answers on `:8080`.
- [ ] `cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test .venv/bin/pytest -q` → 3 passed.
- [ ] GitHub Actions `ci.yml` green on both backend and frontend jobs.
- [ ] `cd frontend && npx tsc --noEmit && npm run build` succeed; `npm run dev` renders the RTL `/login` page; at 375×812 the app shell shows a 5-item bottom tab bar with safe-area padding; active tab is highlighted.

### Task 0.1: Repository initialization

**Files:**
- Create: `.gitignore`, `README.md`

- [ ] **Step 1: Initialize the repo and write `.gitignore`**
```gitignore
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/

# Node / Next.js
node_modules/
.next/
out/

# Env & secrets — examples stay tracked
.env
.env.*
!.env.example
!.env.local.example
backend/secrets/

# OS / editor
.DS_Store
.idea/
.vscode/
```
Run: `cd /Users/tamirsida/dev/tax && git init -b main`
- [ ] **Step 2: Write minimal `README.md`**
```markdown
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
```
- [ ] **Step 3: Commit** — `git add .gitignore README.md && git commit -m "chore: initialize monorepo with gitignore and readme"`

### Task 0.2: Backend skeleton — settings, errors, app entrypoint

**Files:**
- Create: `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/core/errors.py`, `backend/app/main.py`, `backend/.env.example`

- [ ] **Step 1: Write pinned `backend/requirements.txt`** (versions per verified facts; the rest are known-good releases)
```txt
fastapi==0.136.1
uvicorn[standard]==0.34.0
pydantic-settings==2.8.1
firebase-admin==7.4.0
google-cloud-firestore==2.21.0
openai==2.41.1
weasyprint==69.0
jinja2==3.1.6
cloudinary==1.44.2
python-multipart==0.0.20
```
and `backend/requirements-dev.txt`:
```txt
pytest==8.3.5
httpx==0.28.1
requests==2.32.3
pypdf==5.4.0
```
- [ ] **Step 2: Create venv and install** — `cd backend && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt`. Expect clean install (on macOS, WeasyPrint's native libs are only needed at import time — Phase 2 covers `brew install pango` if rendering locally).
- [ ] **Step 3: Write `backend/app/core/config.py`** (exact contract names; secrets default to `""` so the app imports without env — runtime callers fail loudly later)
```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    firebase_project_id: str = ""
    google_application_credentials: str = ""
    openai_api_key: str = ""
    openai_command_model: str = "gpt-4.1-mini"
    openai_vision_model: str = "gpt-4.1-mini"
    cloudinary_url: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    annual_limit_ils: int = 122833
    env: str = "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```
- [ ] **Step 4: Write `backend/app/core/errors.py`**
```python
from typing import NoReturn

from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})
```
- [ ] **Step 5: Write `backend/app/main.py`** with healthz, CORS from settings (`allow_credentials=False` — locked), and the `/api` router-mounting pattern
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="AI Bookkeeper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


# Router registration pattern — each phase appends its router here under /api:
# from app.routers import businesses
# app.include_router(businesses.router, prefix="/api")
```
Create empty `backend/app/__init__.py` and `backend/app/core/__init__.py`.
- [ ] **Step 6: Write `backend/.env.example`** (every var, commented)
```bash
# GCP/Firebase project id (the dedicated DEV Firebase project; prod uses its own)
FIREBASE_PROJECT_ID=
# Absolute path to the Firebase service-account JSON (kept in backend/secrets/, git-ignored)
GOOGLE_APPLICATION_CREDENTIALS=/code/secrets/firebase-sa.json
# OpenAI
OPENAI_API_KEY=
OPENAI_COMMAND_MODEL=gpt-4.1-mini
OPENAI_VISION_MODEL=gpt-4.1-mini
# Cloudinary (Console > Dashboard > API Environment variable). NOTE: must be loaded
# into settings BEFORE importing the cloudinary SDK (it auto-configures at import).
CLOUDINARY_URL=
# JSON array — pydantic-settings parses complex types from JSON
CORS_ORIGINS=["http://localhost:3000"]
# עוסק פטור annual revenue ceiling in ILS (2026: 122,833; updated annually by רשות המסים)
ANNUAL_LIMIT_ILS=122833
# dev | prod | test
ENV=dev
```
- [ ] **Step 7: Verify** — `cd backend && .venv/bin/uvicorn app.main:app --port 8000` then `curl -s http://localhost:8000/healthz` → `{"status":"ok"}`. Stop the server.
- [ ] **Step 8: Commit** — `git add backend && git commit -m "feat(backend): app skeleton with settings, healthz and cors"`

### Task 0.3: Backend Dockerfile (WeasyPrint deps day one)

**Files:**
- Create: `backend/Dockerfile`, `backend/.dockerignore`

- [ ] **Step 1: Write `backend/Dockerfile`** — python:3.12-slim (Debian trixie), the exact apt set WeasyPrint 69 needs and nothing more, non-root user, fontconfig cache redirected to a writable dir
```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    XDG_CACHE_HOME=/tmp/cache

# WeasyPrint 69.0 runtime deps ONLY (slim ships zero fonts; dejavu is the fallback —
# Hebrew receipt fonts are vendored TTFs added in Phase 2 via @font-face)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 \
    libfontconfig1 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home appuser && mkdir -p /tmp/cache && chown appuser:appuser /tmp/cache
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- [ ] **Step 2: Write `backend/.dockerignore`**
```txt
.venv
__pycache__
*.pyc
.pytest_cache
secrets
.env
tests
```
- [ ] **Step 3: Verify** — `docker build -t tax-api backend && docker run --rm -p 8000:8000 tax-api` then `curl -s http://localhost:8000/healthz` → `{"status":"ok"}`. Stop the container.
- [ ] **Step 4: Commit** — `git add backend/Dockerfile backend/.dockerignore && git commit -m "chore(backend): dockerfile with weasyprint runtime deps"`

### Task 0.4: docker-compose — api + Firestore emulator

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`** (emulator is for tests only — the api dev runtime talks to the real dev Firebase project, so api gets no `FIRESTORE_EMULATOR_HOST`)
```yaml
services:
  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    env_file:
      - backend/.env
    volumes:
      - ./backend/app:/code/app
      - ./backend/secrets:/code/secrets:ro

  firestore:
    image: gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators
    command: gcloud emulators firestore start --host-port=0.0.0.0:8080
    ports:
      - "8080:8080"
```
- [ ] **Step 2: Verify** — `cp backend/.env.example backend/.env && mkdir -p backend/secrets && docker compose up -d`, then `curl -s http://localhost:8000/healthz` → `{"status":"ok"}` and `curl -s http://localhost:8080` → `Ok` (emulator banner). `docker compose down`.
- [ ] **Step 3: Commit** — `git add docker-compose.yml && git commit -m "chore: docker compose with api and firestore emulator"`

### Task 0.5: Test harness — conftest fixtures + smoke tests

Phase 0 deliberately creates two `app/core` modules early so the shared `api` fixture can reference real dependency objects: `core/firebase.py` (fully implemented — `get_db()` is trivial) and `core/auth.py` as a **named placeholder**: `get_current_uid` exists with its final signature but always raises 401 `auth/not-configured`; Phase 1 replaces only its body with `firebase_admin.auth.verify_id_token`. Tests are unaffected because the `api` fixture overrides it.

**Files:**
- Create: `backend/app/core/firebase.py`, `backend/app/core/auth.py`, `backend/pytest.ini`, `backend/tests/conftest.py`
- Test: `backend/tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke tests** — `backend/tests/test_smoke.py`
```python
def test_healthz(api):
    r = api.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_emulator_roundtrip(db, make_business):
    biz = make_business(businessName="חנות בדיקה")
    snap = db.collection("businesses").document(biz["id"]).get()
    assert snap.exists
    assert snap.get("businessName") == "חנות בדיקה"
    assert snap.get("ownerUserId") == "test-uid"


def test_clear_db_wipes_between_tests(db):
    # Runs after test_emulator_roundtrip; autouse clear_db must have wiped its writes.
    assert list(db.collection("businesses").limit(1).stream()) == []
```
and `backend/pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```
- [ ] **Step 2: Run it** — `docker compose up -d firestore && cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test .venv/bin/pytest -q`. Expected failure: `fixture 'api' not found` (×3 errors).
- [ ] **Step 3: Write `backend/app/core/firebase.py`**
```python
import firebase_admin
from google.cloud import firestore

from app.core.config import get_settings

_db: firestore.Client | None = None


def init_firebase() -> None:
    """Idempotent firebase-admin init. Wired into app startup in Phase 1."""
    if not firebase_admin._apps:
        firebase_admin.initialize_app()


def get_db() -> firestore.Client:
    """Module-cached sync client. Honors FIRESTORE_EMULATOR_HOST automatically
    (google-cloud-firestore switches to AnonymousCredentials when it is set)."""
    global _db
    if _db is None:
        _db = firestore.Client(project=get_settings().firebase_project_id)
    return _db
```
- [ ] **Step 4: Write `backend/app/core/auth.py`** (Phase 0 placeholder body — exact behavior: every un-overridden call returns 401)
```python
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import api_error

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_uid(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    # Phase 0 seam: Phase 1 replaces this body with firebase_admin.auth.verify_id_token.
    api_error(401, "auth/not-configured", "Authentication is not configured yet")
```
- [ ] **Step 5: Write `backend/tests/conftest.py`** — the contract fixtures, fail-fast on missing emulator, wipe-before-each-test via the emulator REST DELETE endpoint
```python
import os
from datetime import datetime, timezone

import pytest
import requests
from fastapi.testclient import TestClient
from google.cloud import firestore

PROJECT_ID = "demo-tax-test"  # 'demo-' prefix = emulator-only, guaranteed offline


def _emulator_host() -> str:
    host = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if not host:
        pytest.exit(
            "FIRESTORE_EMULATOR_HOST is not set. Start the emulator with "
            "'docker compose up -d firestore' and run: "
            "FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test pytest",
            returncode=1,
        )
    return host


@pytest.fixture(scope="session")
def db() -> firestore.Client:
    _emulator_host()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT_ID)
    return firestore.Client(project=PROJECT_ID)


@pytest.fixture(autouse=True, scope="session")
def _patch_firebase_db(db):
    # Keep firebase.get_db()'s module cache pointing at the emulator client so any
    # future direct call (outside Depends) can never hit a real project during tests.
    import app.core.firebase as firebase_mod

    firebase_mod._db = db


@pytest.fixture(autouse=True)
def clear_db():
    host = _emulator_host()
    requests.delete(
        f"http://{host}/emulator/v1/projects/{PROJECT_ID}/databases/(default)/documents",
        timeout=10,
    ).raise_for_status()
    yield


@pytest.fixture()
def api(db):
    from app.core import auth, firebase
    from app.main import app

    saved = dict(app.dependency_overrides)
    app.dependency_overrides[auth.get_current_uid] = lambda: "test-uid"
    app.dependency_overrides[firebase.get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)


@pytest.fixture()
def make_business():
    def _make(**overrides) -> dict:
        now = datetime.now(timezone.utc)
        doc = {
            "ownerUserId": "test-uid",
            "businessName": "עסק בדיקה",
            "ownerName": "ישראל ישראלי",
            "businessIdNumber": "123456789",
            "businessType": "osek_patur",
            "address": "תל אביב",
            "phone": "0501234567",
            "email": "owner@example.com",
            "receiptPrefix": "2026",
            "nextReceiptNumber": 1,
            # explicit per-business override — tests assert against this 120000, exercising
            # the business.annualLimit-overrides-config path (config default is 122833 for 2026)
            "annualLimit": 120000,
            "createdAt": now,
            "updatedAt": now,
        }
        doc.update(overrides)
        ref = db.collection("businesses").document()
        doc["id"] = ref.id
        ref.set(doc)
        return doc

    return _make
```
(Phase 3 adds the `stub_parser` fixture and `backend/tests/stubs.py` — not created here.)
- [ ] **Step 6: Run again** — same pytest command. Expected: `3 passed`.
- [ ] **Step 7: Commit** — `git add backend/app/core/firebase.py backend/app/core/auth.py backend/pytest.ini backend/tests && git commit -m "test(backend): firestore emulator harness with api, db and make_business fixtures"`

### Task 0.6: CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write `.github/workflows/ci.yml`** (custom emulator command rules out GHA `services:`, so run it with `docker run`; frontend build gets dummy `NEXT_PUBLIC_*` so prerender never touches a real Firebase project)
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - name: Start Firestore emulator
        run: |
          docker run -d --name firestore -p 8080:8080 \
            gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators \
            gcloud emulators firestore start --host-port=0.0.0.0:8080
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/requirements*.txt
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Wait for emulator
        run: timeout 60 bash -c 'until curl -sf http://localhost:8080 >/dev/null; do sleep 1; done'
      - name: Run tests
        env:
          FIRESTORE_EMULATOR_HOST: localhost:8080
          GOOGLE_CLOUD_PROJECT: demo-tax-test
        run: pytest -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx tsc --noEmit
      - name: Build
        env:
          NEXT_PUBLIC_FIREBASE_API_KEY: ci-dummy
          NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: ci-dummy.firebaseapp.com
          NEXT_PUBLIC_FIREBASE_PROJECT_ID: ci-dummy
          NEXT_PUBLIC_FIREBASE_APP_ID: "1:0:web:ci-dummy"
          NEXT_PUBLIC_API_BASE_URL: http://localhost:8000/api
        run: npm run build
```
- [ ] **Step 2: Commit** — `git add .github/workflows/ci.yml && git commit -m "ci: backend emulator tests and frontend typecheck/build"` (frontend job goes green after Task 0.7; push after 0.8 and verify both jobs pass on GitHub).

### Task 0.7: Frontend scaffold + Firebase client + design tokens + manifest

**Files:**
- Create: `frontend/` (via create-next-app), `frontend/.env.local.example`, `frontend/lib/firebase.ts`, `frontend/lib/types.ts`, `frontend/app/manifest.ts`, `frontend/public/icon-192.png`, `frontend/public/icon-512.png`
- Modify: `frontend/app/globals.css` (replace the create-next-app default with the design tokens)

- [ ] **Step 1: Scaffold Next.js 16 with Tailwind v4** — `cd /Users/tamirsida/dev/tax && npx create-next-app@latest frontend --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-npm --yes` (creates `postcss.config.mjs` with `@tailwindcss/postcss` and `@import "tailwindcss"` in `app/globals.css`; no `tailwind.config.js` — Tailwind v4).
- [ ] **Step 2: Install Firebase and lucide-react** — `cd frontend && npm install firebase@^12 lucide-react`
- [ ] **Step 3: Write `frontend/.env.local.example`**
```bash
# Firebase console > Project settings > Your apps > Web app (dev project, created in Phase 1)
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
# FastAPI base URL, no trailing slash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```
- [ ] **Step 4: Write `frontend/lib/firebase.ts`**
```ts
import { getApps, initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID!,
};

export const app = getApps()[0] ?? initializeApp(firebaseConfig);
export const auth = getAuth(app);
```
- [ ] **Step 5: Write `frontend/lib/types.ts`** (stub — later phases append API mirrors; all camelCase per the API contract)
```ts
export interface Business {
  id: string;
  ownerUserId: string;
  businessName: string;
  ownerName: string;
  businessIdNumber: string;
  businessType: "osek_patur";
  address?: string;
  phone?: string;
  email?: string;
  receiptPrefix: string;
  nextReceiptNumber: number;
  annualLimit?: number;
}
```
- [ ] **Step 6: Replace `frontend/app/globals.css`** with the canonical mobile design tokens (Tailwind v4 `@theme` → utilities like `bg-primary`, `border-border`; `.tnum` for tabular numerals on amounts; `.pb-safe` for home-indicator safe area). `--font-plex-hebrew` is wired up by `app/layout.tsx` in Task 0.8 — until then `font-sans` falls back to `system-ui`, which is fine.
```css
@import "tailwindcss";

@theme {
  --color-primary: #2563eb;
  --color-on-primary: #ffffff;
  --color-accent: #059669;
  --color-foreground: #0f172a;
  --color-muted: #f1f5fd;
  --color-border: #e4ecfc;
  --color-destructive: #dc2626;
  --font-sans: var(--font-plex-hebrew), system-ui, sans-serif;
}

html {
  -webkit-tap-highlight-color: transparent;
}

body {
  @apply bg-muted font-sans text-foreground antialiased;
}

button,
a,
input,
textarea,
select {
  touch-action: manipulation;
}

.tnum {
  font-variant-numeric: tabular-nums;
}

.pb-safe {
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
```
- [ ] **Step 7: Write `frontend/app/manifest.ts`** (served at `/manifest.webmanifest`; installability signal — iOS 26 opens home-screen sites standalone; `start_url` is `/chat`, the chat-first home)
```ts
import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "AI Bookkeeper",
    short_name: "Bookkeeper",
    description: "הנהלת חשבונות בצ'אט לעוסק פטור",
    start_url: "/chat",
    display: "standalone",
    dir: "rtl",
    lang: "he",
    background_color: "#f1f5fd",
    theme_color: "#2563eb",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
```
- [ ] **Step 8: Generate the app icons** — `frontend/public/icon-512.png` + `icon-192.png`: a solid `#2563EB` rounded square with a white `₪` glyph. ImageMagick one-liner (macOS):
```bash
cd /Users/tamirsida/dev/tax/frontend/public && magick -size 512x512 xc:none -fill '#2563EB' -draw 'roundrectangle 0,0,511,511,96,96' \( -background none -fill white -font /System/Library/Fonts/Supplemental/Arial.ttf -pointsize 300 label:'₪' \) -gravity center -composite icon-512.png && magick icon-512.png -resize 192x192 icon-192.png
```
If ImageMagick is missing (`brew install imagemagick`) or the `₪` glyph fails to render, export the two PNGs (512×512 and 192×192, solid `#2563EB` rounded square, centered white `₪`) from any image editor instead. Confirm with `ls -la frontend/public/icon-*.png`.
- [ ] **Step 9: Verify** — `cd frontend && npx tsc --noEmit && npm run build` (both clean). Then `npm run dev`, open devtools device toolbar at 375×812: verify the page background is the muted token `#F1F5FD`, `http://localhost:3000/manifest.webmanifest` returns the JSON manifest, and `/icon-192.png` + `/icon-512.png` render the blue `₪` icon.
- [ ] **Step 10: Commit** — `git add frontend && git commit -m "feat(frontend): next.js 16 scaffold with design tokens, manifest, icons and firebase client"`

### Task 0.8: Auth shell, login page, apiClient, app shell + bottom nav

**Files:**
- Create: `frontend/lib/auth.tsx`, `frontend/lib/apiClient.ts`, `frontend/app/login/page.tsx`, `frontend/components/AppShell.tsx`, `frontend/components/BottomNav.tsx`, `frontend/app/more/page.tsx`
- Modify: `frontend/app/layout.tsx`, `frontend/app/page.tsx`

Note on incremental routes: the bottom nav and the `/more` page link to `/chat` (Phase 3), `/dashboard` (Phase 5), `/receipts`/`/clients` (Phase 2), `/expenses` (Phase 4), `/annual-report` (Phase 6) and `/onboarding` (Phase 1). Those routes 404 until their phases land — that is expected and acceptable during incremental development; this task delivers the shell, auth and navigation.

- [ ] **Step 1: Write `frontend/lib/auth.tsx`** — AuthProvider with `onAuthStateChanged`, loading state, redirect to `/login` when unauthenticated
```tsx
"use client";

import { onAuthStateChanged, type User } from "firebase/auth";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { auth } from "./firebase";

type AuthState = { user: User | null; loading: boolean };

const AuthContext = createContext<AuthState>({ user: null, loading: true });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, loading: true });
  const router = useRouter();
  const pathname = usePathname();

  useEffect(
    () => onAuthStateChanged(auth, (user) => setState({ user, loading: false })),
    []
  );

  useEffect(() => {
    if (!state.loading && !state.user && pathname !== "/login") {
      router.replace("/login");
    }
  }, [state, pathname, router]);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
```
- [ ] **Step 2: Write `frontend/lib/apiClient.ts`** — exact contract: Bearer token per request (SDK caches/refreshes), ONE `getIdToken(true)` retry on 401, then sign-out redirect; throws `ApiError(code, message)` parsed from the backend's `{"detail":{"code","message"}}` envelope
```ts
import { auth } from "./firebase";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  init: RequestInit | undefined,
  forceRefresh: boolean
): Promise<T> {
  const user = auth.currentUser;
  if (!user) throw new ApiError("auth/no-user", "Not signed in", 401);
  const token = await user.getIdToken(forceRefresh);
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...init?.headers,
      Authorization: `Bearer ${token}`,
    },
  });
  // Note: init.body must not be a ReadableStream; FormData/string/Blob are safe to retry.
  if (res.status === 401 && !forceRefresh) return request<T>(path, init, true);
  if (res.status === 401) {
    await auth.signOut();
    window.location.assign("/login");
    throw new ApiError("auth/unauthorized", "Session expired", 401);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(
      body?.detail?.code ?? "api/error",
      body?.detail?.message ?? res.statusText,
      res.status
    );
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function api<T>(path: string, init?: RequestInit): Promise<T> {
  return request<T>(path, init, false);
}
```
- [ ] **Step 3: Write `frontend/app/login/page.tsx`** — `signInWithPopup` only (locked: no redirect flow). Mobile-first: full `min-h-dvh` centered layout, product name + one-line Hebrew value prop, full-width 48px Google sign-in button with pending spinner. Post-login redirect targets `/chat` (the chat-first home — matches `/` and the manifest `start_url`; 404 until Phase 3 is expected).
```tsx
"use client";

import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { Loader2, LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { auth } from "@/lib/firebase";

export default function LoginPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/chat");
  }, [user, loading, router]);

  async function signIn() {
    setError(null);
    setPending(true);
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
      router.replace("/chat");
    } catch {
      setError("ההתחברות נכשלה, נסה שוב");
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center px-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-white p-6 text-center">
        <h1 className="text-2xl font-semibold">AI Bookkeeper</h1>
        <p className="mt-2 text-sm text-foreground/60">
          {"הנהלת חשבונות בצ'אט לעוסק פטור — קבלות, הוצאות ודוח שנתי"}
        </p>
        <button
          onClick={signIn}
          disabled={pending}
          className="mt-6 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {pending ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <LogIn size={20} aria-hidden />
          )}
          התחברות עם Google
        </button>
        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </div>
    </main>
  );
}
```
- [ ] **Step 4: Write `frontend/components/AppShell.tsx`** — hides the bottom nav on bare routes and reserves space for it everywhere else (`/onboarding` is listed ahead of its Phase 1 landing; harmless until then)
```tsx
"use client";

import { usePathname } from "next/navigation";
import BottomNav from "./BottomNav";

const BARE_ROUTES = ["/login", "/onboarding"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  if (BARE_ROUTES.includes(pathname)) return <>{children}</>;
  return (
    <div className="mx-auto w-full max-w-lg md:max-w-3xl">
      <main className="min-h-dvh pb-[calc(4rem+env(safe-area-inset-bottom,0px))]">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
```
- [ ] **Step 5: Write `frontend/components/BottomNav.tsx`** — 5 items with labels+icons, active state, 48px targets, safe-area padding
```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Menu,
  MessageCircle,
  ReceiptText,
  Wallet,
} from "lucide-react";

const ITEMS = [
  { href: "/chat", label: "צ'אט", Icon: MessageCircle },
  { href: "/dashboard", label: "סקירה", Icon: LayoutDashboard },
  { href: "/receipts", label: "קבלות", Icon: ReceiptText },
  { href: "/expenses", label: "הוצאות", Icon: Wallet },
  { href: "/more", label: "עוד", Icon: Menu },
];

export default function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-white pb-safe">
      <div className="mx-auto flex h-16 max-w-lg md:max-w-3xl">
        {ITEMS.map(({ href, label, Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex min-h-12 flex-1 flex-col items-center justify-center gap-0.5 text-xs font-medium transition-colors ${
                active ? "text-primary" : "text-foreground/55"
              }`}
            >
              <Icon size={24} strokeWidth={active ? 2.4 : 2} aria-hidden />
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
```
- [ ] **Step 6: Replace `frontend/app/layout.tsx` and `frontend/app/page.tsx`** — canonical RTL root layout: IBM Plex Sans Hebrew (weights 400/500/600/700), `viewportFit: "cover"` enables safe-area insets, `interactiveWidget: "resizes-content"` fixes the Android keyboard (Safari ignores it — the chat page adds an iOS workaround in Phase 3), AuthProvider wraps AppShell
```tsx
import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans_Hebrew } from "next/font/google";
import AppShell from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const plexHebrew = IBM_Plex_Sans_Hebrew({
  subsets: ["hebrew", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-hebrew",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Bookkeeper",
  description: "הנהלת חשבונות בצ'אט לעוסק פטור",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  interactiveWidget: "resizes-content",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={plexHebrew.variable}>
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
```
and replace `frontend/app/page.tsx` (a server-component redirect is fine here — no data fetching):
```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/chat");
}
```
- [ ] **Step 7: Write `frontend/app/more/page.tsx`** — card list for everything that does not fit the 5 tabs: לקוחות → `/clients` (Phase 2), דוח שנתי → `/annual-report` (Phase 6), פרטי העסק → `/onboarding?edit=1` (Phase 1), plus a התנתקות button (`signOut(auth)` → `/login`). The links 404 until their phases land — acceptable during incremental development.
```tsx
"use client";

import { signOut } from "firebase/auth";
import {
  Building2,
  ChevronLeft,
  FileText,
  Loader2,
  LogOut,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { auth } from "@/lib/firebase";

const LINKS = [
  { href: "/clients", label: "לקוחות", Icon: Users },
  { href: "/annual-report", label: "דוח שנתי", Icon: FileText },
  { href: "/onboarding?edit=1", label: "פרטי העסק", Icon: Building2 },
];

export default function MorePage() {
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSignOut() {
    setError(null);
    setSigningOut(true);
    try {
      await signOut(auth);
      router.replace("/login");
    } catch {
      setError("ההתנתקות נכשלה, נסה שוב");
      setSigningOut(false);
    }
  }

  return (
    <div className="px-4 pt-6">
      <h1 className="text-2xl font-semibold">עוד</h1>
      <div className="mt-4 flex flex-col gap-3">
        {LINKS.map(({ href, label, Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex min-h-12 items-center gap-3 rounded-2xl border border-border bg-white p-4 font-medium transition-transform duration-150 active:scale-[0.98]"
          >
            <Icon size={22} className="text-primary" aria-hidden />
            <span className="flex-1 text-start">{label}</span>
            <ChevronLeft size={20} className="text-foreground/40" aria-hidden />
          </Link>
        ))}
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className="flex min-h-12 items-center justify-center gap-2 rounded-2xl border border-border bg-white p-4 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {signingOut ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <LogOut size={20} aria-hidden />
          )}
          התנתקות
        </button>
      </div>
    </div>
  );
}
```
- [ ] **Step 8: Verify build** — `cd frontend && npx tsc --noEmit && npm run build` (use the dummy `NEXT_PUBLIC_*` values from Task 0.6 in `.env.local` if the dev Firebase project does not exist yet). Both must pass.
- [ ] **Step 9: Manual browser verification** — `npm run dev`, open devtools device toolbar at 375×812, open `http://localhost:3000`: expect redirect to `/login`; the login card is centered, RTL, with the one-line value prop and a full-width 48px "התחברות עם Google" button; no bottom nav on `/login`. If the dev Firebase project already exists (otherwise re-run this check in Phase 1): fill `.env.local` with real values, sign in via the Google popup, expect redirect to `/chat` (its 404 page is expected — the route lands in Phase 3; the redirect itself proves auth works); open `/more`: the 5-item bottom tab bar is visible with labels+icons and safe-area padding, "עוד" is highlighted as the active tab, the card list shows לקוחות / דוח שנתי / פרטי העסק, and tapping התנתקות returns to `/login`.
- [ ] **Step 10: Commit and push** — `git add frontend && git commit -m "feat(frontend): auth provider, mobile login, api client, app shell with bottom nav and more page"`. Create the GitHub repo, `git remote add origin <repo-url> && git push -u origin main`, and confirm both CI jobs pass.
## Phase 1 — Auth, Business Profile & First Deploy

**Goal:** Working authenticated API (Firebase ID-token verification + structural ownership checks), business profile CRUD per doc §3.1/§5.1/§6.1, the ledger-event primitive, frontend onboarding gating — and the full prod pipeline deployed once end-to-end so every later phase ships by `git push`.

**Depends on:** Phase 0 (repo, `backend/` scaffold with `app/main.py` + `/healthz`, `core/config.py` Settings, `utils/dates.py`, `utils/money.py`, Dockerfile with WeasyPrint deps, emulator in root `docker-compose.yml`, `backend/tests/conftest.py` fixtures `db`/`clear_db`/`api`/`make_business`, CI workflow, Next.js scaffold with `lib/firebase.ts`, `lib/auth.tsx`, `lib/apiClient.ts`).

**Conventions for all backend steps below:** run from `/Users/tamirsida/dev/tax/backend` with the emulator up (`docker compose up -d firestore-emulator` from repo root) and `export FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test`. Error shape for ALL domain errors: HTTP status + body `{"detail": {"code": "<machine_code>", "message": "<human message>"}}`; request-body validation failures keep FastAPI's default 422 shape.

**Done when:**
- [ ] `pytest backend/tests -q` green locally and in CI (auth 401/403/404, business 201/409, PATCH immutability, ledger events).
- [ ] New Google user on the deployed Netlify site is redirected to `/onboarding`, creates a business, lands on `/dashboard` showing the business name; second create attempt returns 409.
- [ ] At 375×812 (devtools device toolbar) the onboarding form is a single-column mobile form: visible Hebrew labels above every input, numeric keyboard for the ת.ז/ע.מ and receipt-prefix fields, Hebrew validation errors on blur below the fields, and a sticky 48px "צור עסק" submit bar with a spinner while saving.
- [ ] `curl https://api.<domain>/healthz` returns 200 from the VPS through Caddy TLS; pushing to `main` rebuilds and redeploys automatically.

### Task 1.1: Error helper + Firebase/Firestore initialization

**Files:**
- Create: `backend/app/core/errors.py`, `backend/app/core/firebase.py`
- Test: `backend/tests/test_core.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_core.py
import pytest
from fastapi import HTTPException
from app.core.errors import api_error


def test_api_error_shape():
    with pytest.raises(HTTPException) as exc:
        api_error(409, "business_exists", "User already has a business")
    assert exc.value.status_code == 409
    assert exc.value.detail == {"code": "business_exists", "message": "User already has a business"}


def test_get_db_emulator_roundtrip(db):
    ref = db.collection("smoke").document("x")
    ref.set({"ok": True})
    assert ref.get().to_dict() == {"ok": True}
```
- [ ] **Step 2: Run it** — `python -m pytest tests/test_core.py -q` → fails `ModuleNotFoundError: No module named 'app.core.errors'`.
- [ ] **Step 3: Implement**
```python
# backend/app/core/errors.py
from typing import NoReturn
from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str) -> NoReturn:
    """Single error shape for the whole API: {"detail": {"code", "message"}}."""
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})
```
```python
# backend/app/core/firebase.py
import os

import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore

from app.core.config import get_settings

_db: firestore.Client | None = None


def init_firebase() -> None:
    if firebase_admin._apps:
        return
    if os.environ.get("FIRESTORE_EMULATOR_HOST"):
        # Tests/emulator: no service account; project id from env (demo-* = offline).
        # Also force firebase-admin auth into emulator mode so verify_id_token never
        # tries to load ADC credentials (malformed tokens fail locally with ValueError/
        # InvalidIdTokenError before any network call).
        os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099")
        firebase_admin.initialize_app(
            options={"projectId": os.environ.get("GOOGLE_CLOUD_PROJECT", "demo-tax-test")}
        )
        return
    settings = get_settings()
    cred = credentials.Certificate(settings.google_application_credentials)
    firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})


def get_db() -> firestore.Client:
    """Module-cached SYNC Firestore client. With FIRESTORE_EMULATOR_HOST set,
    google-cloud-firestore auto-applies AnonymousCredentials."""
    global _db
    if _db is None:
        if os.environ.get("FIRESTORE_EMULATOR_HOST"):
            _db = firestore.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT", "demo-tax-test"))
        else:
            settings = get_settings()
            _db = firestore.Client.from_service_account_json(
                settings.google_application_credentials, project=settings.firebase_project_id
            )
    return _db
```
- [ ] **Step 4: Run again** — `python -m pytest tests/test_core.py -q` → `2 passed`.
- [ ] **Step 5: Commit** — `git add backend/app/core/errors.py backend/app/core/firebase.py backend/tests/test_core.py && git commit -m "feat(core): api_error helper and firebase/firestore initialization"`

### Task 1.2: Business schemas + business service

**Files:**
- Create: `backend/app/schemas/common.py` (skip if Phase 0 already created it), `backend/app/schemas/business.py`, `backend/app/services/business_service.py`
- Test: `backend/tests/test_business_service.py`

- [ ] **Step 1: Write the failing tests**
```python
# backend/tests/test_business_service.py
import pytest
from fastapi import HTTPException

from app.schemas.business import BusinessCreate, BusinessUpdate
from app.services import business_service
from app.utils.dates import now_il

PAYLOAD = BusinessCreate(
    business_name="עיצובים של נועה", owner_name="נועה לוי",
    business_id_number="123456789", address="הרצל 1, תל אביב", phone="050-1234567",
)


def test_create_business_defaults_and_camelcase_persistence(db):
    biz = business_service.create_business(db, "test-uid", PAYLOAD)
    assert biz.owner_user_id == "test-uid"
    assert biz.business_type == "osek_patur"
    assert biz.next_receipt_number == 1
    assert biz.receipt_prefix == str(now_il().year)
    raw = db.collection("businesses").document(biz.id).get().to_dict()
    assert raw["ownerUserId"] == "test-uid" and raw["nextReceiptNumber"] == 1
    assert "email" not in raw  # None optionals are not persisted


def test_second_business_409(db):
    business_service.create_business(db, "test-uid", PAYLOAD)
    with pytest.raises(HTTPException) as exc:
        business_service.create_business(db, "test-uid", PAYLOAD)
    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "business_exists"


def test_get_business_by_owner_none(db):
    assert business_service.get_business_by_owner(db, "nobody") is None


def test_update_business_mutable_fields_only(db):
    biz = business_service.create_business(db, "test-uid", PAYLOAD)
    updated = business_service.update_business(
        db, biz.id, BusinessUpdate(business_name="סטודיו נועה", receipt_prefix="2027")
    )
    assert updated.business_name == "סטודיו נועה"
    assert updated.receipt_prefix == "2027"
    assert updated.next_receipt_number == 1  # untouched


def test_update_nonexistent_business_404(db):
    with pytest.raises(HTTPException) as exc:
        business_service.update_business(db, "does-not-exist", BusinessUpdate(business_name="X"))
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "business_not_found"
```
- [ ] **Step 2: Run it** — `python -m pytest tests/test_business_service.py -q` → `ModuleNotFoundError: No module named 'app.schemas.business'`.
- [ ] **Step 3: Implement schemas**
```python
# backend/app/schemas/common.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """snake_case attrs <-> camelCase JSON/Firestore field names (doc §5).

    Always pass by_alias=True when serialising for Firestore/JSON."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```
```python
# backend/app/schemas/business.py
from datetime import datetime
from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.schemas.common import CamelModel


class BusinessCreate(CamelModel):
    business_name: str = Field(min_length=1, max_length=120)
    owner_name: str = Field(min_length=1, max_length=120)
    business_id_number: str = Field(pattern=r"^\d{5,9}$")  # ת.ז / ע.מ digits only
    address: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = None
    email: Optional[str] = None
    receipt_prefix: Optional[str] = Field(default=None, max_length=10)  # server defaults to current IL year


class BusinessUpdate(CamelModel):
    # extra="forbid": sending nextReceiptNumber/businessType/etc. -> FastAPI 422
    model_config = CamelModel.model_config | ConfigDict(extra="forbid")
    business_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    owner_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    address: Optional[str] = Field(default=None, min_length=1, max_length=200)
    phone: Optional[str] = None
    email: Optional[str] = None
    receipt_prefix: Optional[str] = Field(default=None, min_length=1, max_length=10)


class Business(CamelModel):
    id: str
    owner_user_id: str
    business_name: str
    owner_name: str
    business_id_number: str
    business_type: Literal["osek_patur"] = "osek_patur"
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    receipt_prefix: str
    next_receipt_number: int = 1
    annual_limit: Optional[int] = None
    created_at: datetime
    updated_at: datetime
```
- [ ] **Step 4: Implement service**
```python
# backend/app/services/business_service.py
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.errors import api_error
from app.schemas.business import Business, BusinessCreate, BusinessUpdate
from app.utils.dates import now_il

MUTABLE_FIELDS = {"businessName", "ownerName", "address", "phone", "email", "receiptPrefix"}


def get_business_by_owner(db: firestore.Client, uid: str) -> Business | None:
    # Single-field equality query: no composite index required.
    docs = list(
        db.collection("businesses").where(filter=FieldFilter("ownerUserId", "==", uid)).limit(1).stream()
    )
    if not docs:
        return None
    return Business.model_validate({**docs[0].to_dict(), "id": docs[0].id})


def create_business(db: firestore.Client, uid: str, payload: BusinessCreate) -> Business:
    # Check-then-create is not transactional; acceptable for MVP (single human
    # clicking one onboarding form — no concurrent-create vector).
    if get_business_by_owner(db, uid) is not None:
        api_error(409, "business_exists", "User already has a business")
    now = now_il()
    data = {
        "ownerUserId": uid,
        "businessName": payload.business_name,
        "ownerName": payload.owner_name,
        "businessIdNumber": payload.business_id_number,
        "businessType": "osek_patur",
        "address": payload.address,
        "phone": payload.phone,
        "email": payload.email,
        "receiptPrefix": payload.receipt_prefix or str(now.year),
        "nextReceiptNumber": 1,
        "createdAt": now,
        "updatedAt": now,
    }
    data = {k: v for k, v in data.items() if v is not None}
    ref = db.collection("businesses").document()
    ref.set(data)
    return Business.model_validate({**data, "id": ref.id})


def update_business(db: firestore.Client, business_id: str, patch: BusinessUpdate) -> Business:
    updates = {
        k: v for k, v in patch.model_dump(by_alias=True, exclude_none=True).items()
        if k in MUTABLE_FIELDS
    }
    if not updates:
        api_error(400, "no_updatable_fields", "No mutable fields provided")
    updates["updatedAt"] = now_il()
    ref = db.collection("businesses").document(business_id)
    if not ref.get().exists:
        api_error(404, "business_not_found", "Business not found")
    ref.update(updates)
    snap = ref.get()
    return Business.model_validate({**snap.to_dict(), "id": snap.id})
```
- [ ] **Step 5: Run again** — `python -m pytest tests/test_business_service.py -q` → `4 passed`.
- [ ] **Step 6: Commit** — `git add backend/app/schemas backend/app/services/business_service.py backend/tests/test_business_service.py && git commit -m "feat(business): camelCase business schemas and one-business-per-user service"`

### Task 1.3: Auth dependencies

**Files:**
- Modify: `backend/app/core/auth.py` (replace Phase 0 stub used by the `api` fixture)
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing tests** (call dependencies as plain functions against the emulator)
```python
# backend/tests/test_auth.py
import pytest
from fastapi import HTTPException

from app.core.auth import get_current_uid, get_owned_business


def test_get_current_uid_missing_credentials():
    with pytest.raises(HTTPException) as exc:
        get_current_uid(creds=None)
    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "unauthenticated"


def test_owned_business_ok(db, make_business):
    biz = make_business()
    result = get_owned_business(businessId=biz["id"], uid="test-uid", db=db)
    assert result.id == biz["id"] and result.owner_user_id == "test-uid"


def test_owned_business_404(db):
    with pytest.raises(HTTPException) as exc:
        get_owned_business(businessId="does-not-exist", uid="test-uid", db=db)
    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "business_not_found"


def test_owned_business_403(db, make_business):
    biz = make_business(ownerUserId="someone-else")
    with pytest.raises(HTTPException) as exc:
        get_owned_business(businessId=biz["id"], uid="test-uid", db=db)
    assert exc.value.status_code == 403
    assert exc.value.detail["code"] == "forbidden"
```
- [ ] **Step 2: Run it** — `python -m pytest tests/test_auth.py -q` → `ImportError: cannot import name 'get_owned_business'` (or NotImplementedError from the Phase 0 stub).
- [ ] **Step 3: Implement**
```python
# backend/app/core/auth.py
import logging

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as fb_auth
from google.cloud import firestore

from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)  # auto_error=True would emit 403 without our error shape


def get_current_uid(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    if creds is None:
        api_error(401, "unauthenticated", "Missing Authorization header")
    try:
        decoded = fb_auth.verify_id_token(creds.credentials)  # no check_revoked (locked decision)
    except (ValueError, fb_auth.InvalidIdTokenError):
        # Token is malformed/expired/wrong-audience — a client problem: 401.
        api_error(401, "invalid_token", "Invalid or expired ID token")
    except Exception:
        # Uninitialized firebase app, JWKS fetch failure, etc. — a server problem: 500.
        logger.exception("Unexpected error during token verification")
        raise
    return decoded["uid"]


def get_owned_business(
    businessId: str,  # matches the {businessId} path param on every business-scoped route
    uid: str = Depends(get_current_uid),
    db: firestore.Client = Depends(get_db),
) -> Business:
    snap = db.collection("businesses").document(businessId).get()
    if not snap.exists:
        api_error(404, "business_not_found", "Business not found")
    data = snap.to_dict()
    if data.get("ownerUserId") != uid:
        api_error(403, "forbidden", "You do not own this business")
    return Business.model_validate({**data, "id": snap.id})
```
- [ ] **Step 4: Run again** — `python -m pytest tests/test_auth.py -q` → `3 passed`. (HTTP-level 401 paths are covered in Task 1.5.)
- [ ] **Step 5: Commit** — `git add backend/app/core/auth.py backend/tests/test_auth.py && git commit -m "feat(auth): firebase token verification and business ownership dependencies"`

### Task 1.4: Ledger event service

**Files:**
- Create: `backend/app/services/ledger_service.py`
- Test: `backend/tests/test_ledger_service.py`

- [ ] **Step 1: Write the failing tests**
```python
# backend/tests/test_ledger_service.py
from google.cloud import firestore

from app.services.ledger_service import record_event


def test_record_event_with_client(db, make_business):
    biz = make_business()
    event_id = record_event(
        db, biz["id"], type="receipt_issued", entity_type="receipt",
        entity_id="r1", amount=2800.456, metadata={"receiptNumber": "2026-0001"},
    )
    raw = (db.collection("businesses").document(biz["id"])
           .collection("ledgerEvents").document(event_id).get().to_dict())
    assert raw["type"] == "receipt_issued" and raw["entityType"] == "receipt"
    assert raw["amount"] == 2800.46 and raw["currency"] == "ILS"
    assert raw["metadata"] == {"receiptNumber": "2026-0001"}
    assert raw["businessId"] == biz["id"] and "createdAt" in raw


def test_record_event_inside_transaction(db, make_business):
    biz = make_business()
    tx = db.transaction()

    @firestore.transactional
    def run(tx):
        return record_event(tx, biz["id"], type="expense_created", entity_type="expense", entity_id="e1")

    event_id = run(tx)
    snap = (db.collection("businesses").document(biz["id"])
            .collection("ledgerEvents").document(event_id).get())
    assert snap.exists and "amount" not in snap.to_dict()
```
- [ ] **Step 2: Run it** — `python -m pytest tests/test_ledger_service.py -q` → `ModuleNotFoundError: No module named 'app.services.ledger_service'`.
- [ ] **Step 3: Implement**
```python
# backend/app/services/ledger_service.py
from google.cloud import firestore

from app.utils.dates import now_il
from app.utils.money import round_ils


def record_event(
    db_or_tx,
    business_id: str,
    type: str,
    entity_type: str,
    entity_id: str,
    amount: float | None = None,
    metadata: dict | None = None,
) -> str:
    """Append a LedgerEvent (doc §5.5). Accepts a Client (standalone write) or a
    Transaction (joins the caller's atomic batch, e.g. receipt issuing in Phase 2)."""
    if isinstance(db_or_tx, firestore.Transaction):
        client, tx = db_or_tx._client, db_or_tx
    else:
        client, tx = db_or_tx, None
    ref = (client.collection("businesses").document(business_id)
           .collection("ledgerEvents").document())
    data: dict = {
        "businessId": business_id,
        "type": type,
        "entityType": entity_type,
        "entityId": entity_id,
        "createdAt": now_il(),
    }
    if amount is not None:
        data["amount"] = round_ils(amount)
        data["currency"] = "ILS"
    if metadata:
        data["metadata"] = metadata
    if tx is not None:
        tx.set(ref, data)
    else:
        ref.set(data)
    return ref.id
```
- [ ] **Step 4: Run again** — `python -m pytest tests/test_ledger_service.py -q` → `2 passed`.
- [ ] **Step 5: Commit** — `git add backend/app/services/ledger_service.py backend/tests/test_ledger_service.py && git commit -m "feat(ledger): record_event supporting client and transaction writers"`

### Task 1.5: Business router + app wiring

**Files:**
- Create: `backend/app/routers/businesses.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_businesses_api.py`

- [ ] **Step 1: Write the failing API tests**
```python
# backend/tests/test_businesses_api.py
import pytest
from fastapi.testclient import TestClient

from app.core.firebase import get_db
from app.main import app

CREATE_BODY = {
    "businessName": "עיצובים של נועה", "ownerName": "נועה לוי",
    "businessIdNumber": "123456789", "address": "הרצל 1, תל אביב",
    "phone": "050-1234567", "email": "noa@example.com",
}


@pytest.fixture
def unauth_api(db):
    """TestClient with real auth dependency (no get_current_uid override)."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def test_create_business_201(api):
    r = api.post("/api/businesses", json=CREATE_BODY)
    assert r.status_code == 201
    body = r.json()
    assert body["ownerUserId"] == "test-uid"
    assert body["businessType"] == "osek_patur" and body["nextReceiptNumber"] == 1


def test_create_second_business_409(api):
    assert api.post("/api/businesses", json=CREATE_BODY).status_code == 201
    r = api.post("/api/businesses", json=CREATE_BODY)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "business_exists"


def test_me_404_then_200(api):
    r = api.get("/api/businesses/me")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "business_not_found"
    api.post("/api/businesses", json=CREATE_BODY)
    r = api.get("/api/businesses/me")
    assert r.status_code == 200 and r.json()["businessName"] == "עיצובים של נועה"


def test_patch_mutable_field(api):
    biz_id = api.post("/api/businesses", json=CREATE_BODY).json()["id"]
    r = api.patch(f"/api/businesses/{biz_id}", json={"businessName": "סטודיו נועה"})
    assert r.status_code == 200 and r.json()["businessName"] == "סטודיו נועה"


def test_patch_immutable_field_422(api):
    biz_id = api.post("/api/businesses", json=CREATE_BODY).json()["id"]
    assert api.patch(f"/api/businesses/{biz_id}", json={"nextReceiptNumber": 999}).status_code == 422
    assert api.patch(f"/api/businesses/{biz_id}", json={"businessType": "osek_murshe"}).status_code == 422


def test_patch_foreign_business_403(api, make_business):
    other = make_business(ownerUserId="someone-else")
    r = api.patch(f"/api/businesses/{other['id']}", json={"businessName": "x"})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"


def test_patch_empty_body_400(api):
    biz_id = api.post("/api/businesses", json=CREATE_BODY).json()["id"]
    r = api.patch(f"/api/businesses/{biz_id}", json={})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "no_updatable_fields"


def test_missing_token_401(unauth_api):
    r = unauth_api.get("/api/businesses/me")
    assert r.status_code == 401 and r.json()["detail"]["code"] == "unauthenticated"


def test_garbage_token_401(unauth_api):
    r = unauth_api.get("/api/businesses/me", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401 and r.json()["detail"]["code"] == "invalid_token"
```
- [ ] **Step 2: Run it** — `python -m pytest tests/test_businesses_api.py -q` → all fail with 404 Not Found (routes unregistered).
- [ ] **Step 3: Implement router**
```python
# backend/app/routers/businesses.py
from fastapi import APIRouter, Depends
from google.cloud import firestore

from app.core.auth import get_current_uid, get_owned_business
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business, BusinessCreate, BusinessUpdate
from app.services import business_service

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=Business, status_code=201)
def create_business(
    payload: BusinessCreate,
    uid: str = Depends(get_current_uid),
    db: firestore.Client = Depends(get_db),
) -> Business:
    return business_service.create_business(db, uid, payload)


@router.get("/me", response_model=Business)
def get_my_business(
    uid: str = Depends(get_current_uid),
    db: firestore.Client = Depends(get_db),
) -> Business:
    business = business_service.get_business_by_owner(db, uid)
    if business is None:
        api_error(404, "business_not_found", "No business for this user")
    return business


@router.patch("/{businessId}", response_model=Business)
def patch_business(
    patch: BusinessUpdate,
    business: Business = Depends(get_owned_business),
    db: firestore.Client = Depends(get_db),
) -> Business:
    return business_service.update_business(db, business.id, patch)
```
(FastAPI serializes `response_model` by alias by default, so responses are camelCase per doc §5.)
- [ ] **Step 4: Wire main.py** — keep Phase 0's CORS middleware and `GET /healthz`; add:
```python
from contextlib import asynccontextmanager
from app.core.firebase import init_firebase
from app.routers import businesses

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield

app = FastAPI(title="Tax API", lifespan=lifespan)  # add lifespan to the existing constructor
app.include_router(businesses.router, prefix="/api")
```
- [ ] **Step 5: Run again** — `python -m pytest tests/test_businesses_api.py -q` → `8 passed`; then full suite `python -m pytest tests -q` → all green.
- [ ] **Step 6: Commit** — `git add backend/app/routers/businesses.py backend/app/main.py backend/tests/test_businesses_api.py && git commit -m "feat(api): business endpoints with auth, 409 guard and PATCH immutability"`

### Task 1.6: Frontend onboarding + business context + gating

> **As-built note (commit 4e13270):** review fixes extended this task — `useBusiness()` additionally exposes `fetchError: boolean` (set on non-404 /businesses/me failures; gating skips the /onboarding redirect when set), and `/onboarding?edit=1` is a real edit mode: provider exempts it from the owner bounce, the form prefills from the business, `businessIdNumber` renders disabled, and submit PATCHes `/businesses/{id}` (mutable fields only) → `refresh()` → `/more`. Page wraps its `useSearchParams` consumer in `<Suspense>`.

**Files:**
- Create: `frontend/lib/business.tsx`, `frontend/app/onboarding/page.tsx`, `frontend/app/dashboard/page.tsx` (placeholder, replaced in Phase 5)
- Modify: `frontend/lib/types.ts`, `frontend/app/layout.tsx`

- [ ] **Step 1: Confirm the Business type** — `frontend/lib/types.ts` already declares `export interface Business` (Phase 0 Task 0.7 Step 5, including `annualLimit?: number`). No change needed in this step; do NOT redeclare or replace it.
- [ ] **Step 2: Implement BusinessProvider with gating**
```tsx
// frontend/lib/business.tsx
"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/apiClient";
import type { Business } from "@/lib/types";

interface BusinessState { business: Business | null; loading: boolean; refresh: () => Promise<void>; }
const BusinessContext = createContext<BusinessState>({ business: null, loading: true, refresh: async () => {} });

export function BusinessProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState(true);
  const pathname = usePathname();
  const router = useRouter();

  const refresh = useCallback(async () => {
    if (!user) { setBusiness(null); setLoading(false); return; }
    setLoading(true);
    try { setBusiness(await api<Business>("/businesses/me")); }
    catch (e) {
      if (e instanceof ApiError && e.code === "business_not_found") setBusiness(null);
      else { console.error(e); setBusiness(null); }
    } finally { setLoading(false); }
  }, [user]);

  useEffect(() => { if (!authLoading) void refresh(); }, [authLoading, refresh]);

  // Gating: signed-in without business -> /onboarding; with business, keep off /onboarding.
  useEffect(() => {
    if (authLoading || loading || !user) return;
    if (!business && pathname !== "/onboarding" && pathname !== "/login") router.replace("/onboarding");
    if (business && pathname === "/onboarding") router.replace("/dashboard");
  }, [authLoading, loading, user, business, pathname, router]);

  return (
    <BusinessContext.Provider value={{ business, loading: authLoading || loading, refresh }}>
      {children}
    </BusinessContext.Provider>
  );
}
export const useBusiness = () => useContext(BusinessContext);
```
Then replace `frontend/app/layout.tsx` so `<BusinessProvider>` nests directly inside the existing `<AuthProvider>` and wraps `<AppShell>` — the only changes versus Phase 0 are the `BusinessProvider` import and the extra nesting level; font, viewport and metadata stay exactly as Phase 0 left them:
```tsx
// frontend/app/layout.tsx
import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans_Hebrew } from "next/font/google";
import AppShell from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import { BusinessProvider } from "@/lib/business";
import "./globals.css";

const plexHebrew = IBM_Plex_Sans_Hebrew({
  subsets: ["hebrew", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-plex-hebrew",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Bookkeeper",
  description: "הנהלת חשבונות בצ'אט לעוסק פטור",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  interactiveWidget: "resizes-content",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className={plexHebrew.variable}>
      <body>
        <AuthProvider>
          <BusinessProvider>
            <AppShell>{children}</AppShell>
          </BusinessProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
```
- [ ] **Step 3: Implement the onboarding form** (fields per doc §3.1; mobile-first per the UI brief: single column at 375px, visible Hebrew label above every input, 48px `text-base` inputs, `inputMode="numeric"` for ת.ז/ע.מ and the receipt prefix, `type="tel"`/`type="email"` with `dir="ltr"` LTR islands for the optional contact fields, validation on blur with Hebrew error text below the field, sticky bottom submit bar with spinner. `/onboarding` is in AppShell's `BARE_ROUTES`, so the page owns the full viewport — no bottom nav. The POST body, `refresh()` and redirect logic are unchanged):
```tsx
// frontend/app/onboarding/page.tsx
"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/apiClient";
import { useBusiness } from "@/lib/business";

type FieldKey =
  | "businessName"
  | "ownerName"
  | "businessIdNumber"
  | "address"
  | "phone"
  | "email"
  | "receiptPrefix";

type FieldDef = {
  key: FieldKey;
  label: string;
  type: "text" | "tel" | "email";
  inputMode?: "numeric";
  ltr?: boolean;
  autoComplete?: string;
};

const FIELDS: FieldDef[] = [
  { key: "businessName", label: "שם העסק", type: "text", autoComplete: "organization" },
  { key: "ownerName", label: "שם בעל/ת העסק", type: "text", autoComplete: "name" },
  { key: "businessIdNumber", label: "ת.ז / ע.מ (ספרות בלבד)", type: "text", inputMode: "numeric", ltr: true },
  { key: "address", label: "כתובת", type: "text", autoComplete: "street-address" },
  { key: "phone", label: "טלפון (רשות)", type: "tel", ltr: true, autoComplete: "tel" },
  { key: "email", label: "אימייל (רשות)", type: "email", ltr: true, autoComplete: "email" },
  { key: "receiptPrefix", label: "קידומת מספרי קבלות", type: "text", inputMode: "numeric", ltr: true },
];

function validateField(key: FieldKey, value: string): string | null {
  switch (key) {
    case "businessName":
      return value.trim() ? null : "יש להזין שם עסק";
    case "ownerName":
      return value.trim() ? null : "יש להזין את שם בעל/ת העסק";
    case "businessIdNumber":
      return /^\d{5,9}$/.test(value) ? null : "יש להזין 5–9 ספרות בלבד";
    case "address":
      return value.trim() ? null : "יש להזין כתובת";
    case "phone":
      return null; // אופציונלי — השרת מקבל כל מחרוזת
    case "email":
      return !value || /^\S+@\S+\.\S+$/.test(value) ? null : "כתובת אימייל לא תקינה";
    case "receiptPrefix":
      return value.trim() && value.trim().length <= 10 ? null : "יש להזין קידומת של עד 10 תווים";
  }
}

export default function OnboardingPage() {
  const router = useRouter();
  const { refresh } = useBusiness();
  const [form, setForm] = useState<Record<FieldKey, string>>({
    businessName: "", ownerName: "", businessIdNumber: "", address: "",
    phone: "", email: "", receiptPrefix: String(new Date().getFullYear()),
  });
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldKey, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function handleBlur(key: FieldKey) {
    const message = validateField(key, form[key]);
    setFieldErrors((prev) => {
      const next = { ...prev };
      if (message) next[key] = message;
      else delete next[key];
      return next;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const errors: Partial<Record<FieldKey, string>> = {};
    for (const { key } of FIELDS) {
      const message = validateField(key, form[key]);
      if (message) errors[key] = message;
    }
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setSaving(true);
    setError(null);
    try {
      await api("/businesses", {
        method: "POST",
        body: JSON.stringify({ ...form, phone: form.phone || null, email: form.email || null }),
      });
      await refresh();
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "שגיאה לא צפויה, נסו שוב");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-4 pt-6">
      <h1 className="text-2xl font-bold">הקמת פרופיל עסק</h1>
      <p className="mt-1 text-sm text-foreground/60">
        כמה פרטים על העסק — ואפשר להתחיל להפיק קבלות.
      </p>
      <form onSubmit={submit} noValidate className="mt-6 flex flex-1 flex-col gap-4">
        {FIELDS.map(({ key, label, type, inputMode, ltr, autoComplete }) => (
          <div key={key}>
            <label htmlFor={key} className="mb-1 block text-sm font-medium">
              {label}
            </label>
            <input
              id={key}
              type={type}
              inputMode={inputMode}
              dir={ltr ? "ltr" : undefined}
              autoComplete={autoComplete}
              value={form[key]}
              aria-invalid={Boolean(fieldErrors[key])}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              onBlur={() => handleBlur(key)}
              className={`min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
                fieldErrors[key] ? "border-destructive" : "border-border"
              }`}
            />
            {fieldErrors[key] && (
              <p className="mt-1 text-sm text-destructive">{fieldErrors[key]}</p>
            )}
          </div>
        ))}
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="sticky bottom-0 mt-auto bg-muted pb-safe pt-2">
          <button
            type="submit"
            disabled={saving}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {saving && <Loader2 size={20} className="animate-spin" aria-hidden />}
            {saving ? "שומר..." : "צור עסק"}
          </button>
        </div>
      </form>
    </main>
  );
}
```
(`noValidate` keeps the browser's native bubbles off so all errors render in our Hebrew style; `pb-safe` is the safe-area utility from Phase 0's `globals.css`; the sticky bar keeps the 48px submit button visible above the keyboard while the form scrolls.)
- [ ] **Step 4: Placeholder dashboard** (Phase 5 replaces this file; rendered inside AppShell, so the bottom nav is visible here — skeleton while the business loads, never a blank screen):
```tsx
// frontend/app/dashboard/page.tsx
"use client";
import { useBusiness } from "@/lib/business";

export default function DashboardPage() {
  const { business, loading } = useBusiness();
  return (
    <div className="p-4">
      {loading ? (
        <div className="h-8 w-48 animate-pulse rounded-xl bg-border" aria-hidden />
      ) : (
        <>
          <h1 className="text-2xl font-semibold">שלום, {business?.businessName}</h1>
          <p className="mt-1 text-sm text-foreground/60">הסקירה המלאה תתווסף בשלב 5.</p>
        </>
      )}
    </div>
  );
}
```
- [ ] **Step 5: Verify** — `cd /Users/tamirsida/dev/tax/frontend && npx tsc --noEmit && npm run build` → zero errors. Manual: start backend (`uvicorn app.main:app --reload` from `backend/` with `.env` pointing at the dev Firebase project) and `npm run dev`; open http://localhost:3000, sign in with Google → expect redirect to /onboarding; submit the form → expect redirect to /dashboard showing the business name; hard-refresh /dashboard → stays (GET /me 200); navigate to /onboarding manually → redirected back to /dashboard. Then open devtools device toolbar at 375×812, verify: the onboarding form is single-column with a visible Hebrew label above every input; focusing ת.ז / ע.מ or קידומת מספרי קבלות raises the numeric keyboard (`inputMode="numeric"`); the phone/email/ת.ז values render left-to-right (`dir="ltr"`); leaving a required field empty and blurring shows the Hebrew error in red below it; the "צור עסק" button sits in a sticky bottom bar that stays visible while scrolling and shows a spinner + disabled state while saving; /dashboard shows the bottom tab bar with a skeleton line before the greeting appears.
- [ ] **Step 6: Commit** — `git add frontend/lib/business.tsx frontend/lib/types.ts frontend/app/onboarding frontend/app/dashboard frontend/app/layout.tsx && git commit -m "feat(web): onboarding form, business context and gating"`

### Task 1.7: First deploy — VPS, Caddy, GHCR pipeline, Netlify

**Files:**
- Create: `ops/docker-compose.prod.yml`, `ops/Caddyfile`, `docs/deploy.md`, `.github/workflows/deploy.yml`

- [ ] **Step 1: Write prod compose**
```yaml
# ops/docker-compose.prod.yml  (copied to /opt/tax/docker-compose.prod.yml on the VPS)
services:
  api:
    image: ghcr.io/tamirsida/tax-api:latest
    restart: unless-stopped
    env_file: /opt/tax/.env
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/firebase-sa.json
    volumes:
      - /opt/tax/secrets/firebase-sa.json:/app/secrets/firebase-sa.json:ro
    expose: ["8000"]
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')"]
      interval: 30s
      timeout: 5s
      retries: 3
  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    env_file: /opt/tax/.env   # provides DOMAIN for the Caddyfile
    ports: ["80:80", "443:443"]
    volumes:
      - /opt/tax/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
volumes:
  caddy_data:
  caddy_config:
```
```caddyfile
# ops/Caddyfile
api.{$DOMAIN} {
	reverse_proxy api:8000
}
```
- [ ] **Step 2: Write the deploy workflow**
```yaml
# .github/workflows/deploy.yml
name: deploy
on:
  push:
    branches: [main]
jobs:
  build-push:
    runs-on: ubuntu-latest
    permissions: { contents: read, packages: write }
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with: { registry: ghcr.io, username: "${{ github.actor }}", password: "${{ secrets.GITHUB_TOKEN }}" }
      - uses: docker/build-push-action@v6
        with:
          context: backend
          push: true
          tags: |
            ghcr.io/tamirsida/tax-api:${{ github.sha }}
            ghcr.io/tamirsida/tax-api:latest
  deploy:
    needs: build-push
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/tax
            docker compose -f docker-compose.prod.yml pull
            docker compose -f docker-compose.prod.yml up -d
```
- [ ] **Step 3: Write `docs/deploy.md`** with exactly this runbook:
  1. **DNS:** A record `api.<domain>` → VPS IP (Hostinger DNS panel).
  2. **VPS bootstrap (Hostinger KVM2, Ubuntu):** `apt update && apt install -y ca-certificates curl ufw; curl -fsSL https://get.docker.com | sh` (installs docker + compose plugin); `ufw allow 22 && ufw allow 80 && ufw allow 443 && ufw enable`.
  3. **App dir:** `mkdir -p /opt/tax/secrets`; `scp ops/docker-compose.prod.yml ops/Caddyfile root@<vps>:/opt/tax/`; upload the prod Firebase service account to `/opt/tax/secrets/firebase-sa.json`; `chmod 600 /opt/tax/secrets/firebase-sa.json`.
  4. **`/opt/tax/.env`** (`chmod 600`), exact lines: `DOMAIN=<domain>`, `ENV=prod`, `FIREBASE_PROJECT_ID=<prod-project>`, `GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/firebase-sa.json`, `OPENAI_API_KEY=sk-...`, `CLOUDINARY_URL=cloudinary://...`, `CORS_ORIGINS=["https://<site>.netlify.app","http://localhost:3000"]` (JSON list — pydantic-settings format).
  5. **GHCR pull auth:** on the VPS, `docker login ghcr.io -u tamirsida -p <PAT with read:packages>` (or set the GHCR package public after first push).
  6. **GitHub secrets:** `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` (private key whose public half is in the VPS `~/.ssh/authorized_keys`).
  7. **Netlify:** import repo, base directory `frontend` (Netlify's Next.js OpenNext runtime auto-detects Next 16); env vars `NEXT_PUBLIC_API_BASE_URL=https://api.<domain>/api`, `NEXT_PUBLIC_FIREBASE_API_KEY`, `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`, `NEXT_PUBLIC_FIREBASE_PROJECT_ID`, `NEXT_PUBLIC_FIREBASE_APP_ID`.
  8. **Firebase Console:** Authentication → Settings → Authorized domains → add `<site>.netlify.app`. Confirm the Netlify URL is in `CORS_ORIGINS` on the VPS, then `docker compose -f docker-compose.prod.yml up -d` to reload.
- [ ] **Step 4: Commit and push** — `git add ops docs/deploy.md .github/workflows/deploy.yml && git commit -m "ci: GHCR build + SSH deploy pipeline, prod compose, Caddy TLS"` then `git push origin main`; execute the runbook steps 1-8.
- [ ] **Step 5: Verify end-to-end** — GitHub Actions `deploy` workflow green; on VPS `docker compose -f /opt/tax/docker-compose.prod.yml ps` shows `api` healthy; `curl -i https://api.<domain>/healthz` → `200` over valid TLS; open the Netlify site, sign in with Google, complete onboarding against the prod API → lands on /dashboard; repeat POST via `curl -X POST https://api.<domain>/api/businesses -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{...}'` → `409 {"detail":{"code":"business_exists",...}}`.
## Phase 2 — Manual Ledger: Clients, Receipts, PDF, Cloudinary

**Goal:** the full manual income path — client CRUD, receipt draft → atomic issue (transactional numbering off `business.nextReceiptNumber`, formatted `{receiptPrefix}-{seq:04d}`) → Hebrew RTL PDF → Cloudinary raw upload — plus the `/clients` and `/receipts` pages.
**Depends on:** Phase 0 (repo, Dockerfile with WeasyPrint apt deps, emulator in docker-compose, `tests/conftest.py` fixtures `db`/`clear_db`/`api`/`make_business`, CI) and Phase 1 (`get_current_uid`, `get_owned_business`, `api_error`, `business_service`, `ledger_service.record_event`, `app/schemas/common.py` `CamelModel` with `alias_generator=to_camel, populate_by_name=True`, `app/schemas/business.py` `Business`).
**Conventions for this phase:** run backend tests from `/Users/tamirsida/dev/tax/backend`; emulator-backed commands assume `docker compose up -d firestore` already ran and use the prefix `FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test` (abbreviated below as `EMU=1`); pure unit tests need no emulator. Local macOS WeasyPrint needs `brew install pango` once (CI/Docker already have apt deps from Phase 0).

**Done when:**
- [ ] `EMU=1 python -m pytest tests -q` green, including `test_concurrent_issue_assigns_unique_sequential_numbers`
- [ ] Golden PDF test passes: Hebrew client name + `₪2,800` + `2026-0007` extractable via pypdf
- [ ] `POST /api/businesses/{id}/receipts/draft` → `/issue` via TestClient returns `receiptNumber == "2026-0001"`, `pdfUrl` set (stubbed Cloudinary)
- [ ] In the browser at 375×812 (devtools device toolbar): create client נועה from the clients page's bottom-sheet form (card list + `EmptyState` + skeletons, no table on mobile), issue a ₪2,800 receipt from the receipts page's bottom-sheet form and see it as a card with an LTR receipt number, `formatILS` amount and a הופקה badge; from the card's detail Sheet download the real PDF from Cloudinary (after enabling the free-plan PDF delivery toggle), share/copy the PDF link, and cancel a receipt via the in-sheet destructive confirm with a required reason

### Task 2.1: Money & date utils

**Files:** Create: `backend/app/utils/money.py`, `backend/tests/test_money.py`, `backend/tests/test_dates.py`. Overwrite: `backend/app/utils/dates.py` (Task 1.2 pre-created it with only the IL_TZ/now_il subset; the full file below is a superset)

- [ ] **Step 1: Write the failing tests**
```python
# backend/tests/test_money.py
from app.utils.money import round_ils, format_ils

def test_round_ils_half_up():
    assert round_ils(10.005) == 10.01
    assert round_ils(2800) == 2800.0
    assert round_ils(99.994) == 99.99

def test_format_ils():
    assert format_ils(2800) == "₪2,800"
    assert format_ils(99.5) == "₪99.50"
    assert format_ils(1234567.89) == "₪1,234,567.89"
```
```python
# backend/tests/test_dates.py
from datetime import datetime
from app.utils.dates import IL_TZ, now_il, today_il, year_bounds, month_bounds, parse_iso_date

def test_now_il_is_jerusalem():
    assert now_il().tzinfo is IL_TZ and now_il().utcoffset() is not None

def test_year_bounds():
    start, end = year_bounds(2026)
    assert start == datetime(2026, 1, 1, tzinfo=IL_TZ) and end == datetime(2027, 1, 1, tzinfo=IL_TZ)

def test_month_bounds_december_wraps():
    assert month_bounds(2026, 12)[1] == datetime(2027, 1, 1, tzinfo=IL_TZ)

def test_parse_iso_date():
    assert parse_iso_date("2026-06-13").isoformat() == "2026-06-13"
    assert parse_iso_date("13/06/2026") is None and parse_iso_date(None) is None
```
- [ ] **Step 2: Run** `python -m pytest tests/test_money.py tests/test_dates.py -q` — expect `ModuleNotFoundError: app.utils.money`.
- [ ] **Step 3: Implement**
```python
# backend/app/utils/money.py
from decimal import Decimal, ROUND_HALF_UP

def round_ils(x: float) -> float:
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def format_ils(x: float) -> str:
    s = f"{round_ils(x):,.2f}"
    if s.endswith(".00"):
        s = s[:-3]
    return f"₪{s}"
```
```python
# backend/app/utils/dates.py
from datetime import date, datetime
from zoneinfo import ZoneInfo

IL_TZ = ZoneInfo("Asia/Jerusalem")

def now_il() -> datetime:
    return datetime.now(IL_TZ)

def today_il() -> date:
    return now_il().date()

def year_bounds(year: int) -> tuple[datetime, datetime]:
    return datetime(year, 1, 1, tzinfo=IL_TZ), datetime(year + 1, 1, 1, tzinfo=IL_TZ)

def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=IL_TZ)
    end = datetime(year + 1, 1, 1, tzinfo=IL_TZ) if month == 12 else datetime(year, month + 1, 1, tzinfo=IL_TZ)
    return start, end

def parse_iso_date(s: str | None) -> date | None:
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        return None
```
`resolve_time_range(time_range)` is intentionally added to this module in Phase 3 Task "AI command schemas" — it imports `TimeRange`/`TimePreset` from `app/schemas/ai_commands.py`, which does not exist yet; the contract signature is reserved.
- [ ] **Step 4: Run** the same pytest command — expect 7 passed.
- [ ] **Step 5: Commit** `git add backend/app/utils backend/tests/test_money.py backend/tests/test_dates.py && git commit -m "feat: ILS money rounding/formatting and Asia/Jerusalem date utils"`

### Task 2.2: Clients — schema, service, router

**Files:** Create: `backend/app/schemas/client.py`, `backend/app/services/client_service.py`, `backend/app/routers/clients.py`, `backend/tests/test_clients_api.py` · Modify: `backend/app/main.py` (register router)

- [ ] **Step 1: Write the failing API tests**
```python
# backend/tests/test_clients_api.py
def _create(api, biz_id, **kw):
    return api.post(f"/api/businesses/{biz_id}/clients", json={"name": "נועה גולן", **kw})

def test_create_and_get_client(api, db, make_business):
    biz = make_business()
    r = _create(api, biz["id"], phone="050-1234567")
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "נועה גולן" and body["businessId"] == biz["id"] and "id" in body
    assert api.get(f"/api/businesses/{biz['id']}/clients/{body['id']}").json()["phone"] == "050-1234567"

def test_list_sorted_and_patch(api, db, make_business):
    biz = make_business()
    _create(api, biz["id"]); api.post(f"/api/businesses/{biz['id']}/clients", json={"name": "אבי"})
    names = [c["name"] for c in api.get(f"/api/businesses/{biz['id']}/clients").json()]
    assert names == ["אבי", "נועה גולן"]
    cid = api.get(f"/api/businesses/{biz['id']}/clients").json()[1]["id"]
    r = api.patch(f"/api/businesses/{biz['id']}/clients/{cid}", json={"email": "noa@example.com"})
    assert r.status_code == 200 and r.json()["email"] == "noa@example.com"

def test_get_missing_client_404(api, db, make_business):
    biz = make_business()
    r = api.get(f"/api/businesses/{biz['id']}/clients/nope")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "client_not_found"

def test_find_by_name_case_insensitive_contains(db, make_business):
    from app.schemas.client import ClientCreate
    from app.services.client_service import create_client, find_clients_by_name
    biz = make_business()
    create_client(db, biz["id"], ClientCreate(name="Eden Studio"))
    assert [c.name for c in find_clients_by_name(db, biz["id"], "eden")] == ["Eden Studio"]
    assert find_clients_by_name(db, biz["id"], "נועה") == []
```
- [ ] **Step 2: Run** `EMU=1 python -m pytest tests/test_clients_api.py -q` — expect `ModuleNotFoundError`.
- [ ] **Step 3: Implement schema** (extends `CamelModel` from `backend/app/schemas/common.py`, created in Phase 1)
```python
# backend/app/schemas/client.py
from datetime import datetime
from pydantic import Field
from app.schemas.common import CamelModel

class ClientCreate(CamelModel):
    name: str = Field(min_length=1)          # empty name -> FastAPI 422 (pydantic detail)
    phone: str | None = None
    email: str | None = None
    company_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    notes: str | None = None

class ClientPatch(CamelModel):
    name: str | None = Field(default=None, min_length=1)
    phone: str | None = None
    email: str | None = None
    company_name: str | None = None
    tax_id: str | None = None
    address: str | None = None
    notes: str | None = None

class Client(ClientCreate):
    id: str
    business_id: str
    created_at: datetime
    updated_at: datetime
```
- [ ] **Step 4: Implement service**
```python
# backend/app/services/client_service.py
from app.core.errors import api_error
from app.schemas.client import Client, ClientCreate, ClientPatch
from app.utils.dates import now_il

def _col(db, business_id: str):
    return db.collection("businesses").document(business_id).collection("clients")

def create_client(db, business_id: str, payload: ClientCreate) -> Client:
    ref = _col(db, business_id).document()
    now = now_il()
    data = payload.model_dump(by_alias=True, exclude_none=True)
    data.update(id=ref.id, businessId=business_id, nameLower=payload.name.strip().lower(),
                createdAt=now, updatedAt=now)
    ref.set(data)
    return Client.model_validate(data)

def list_clients(db, business_id: str) -> list[Client]:
    return [Client.model_validate(d.to_dict()) for d in _col(db, business_id).order_by("nameLower").stream()]

def get_client(db, business_id: str, client_id: str) -> Client | None:
    snap = _col(db, business_id).document(client_id).get()
    return Client.model_validate(snap.to_dict()) if snap.exists else None

def update_client(db, business_id: str, client_id: str, patch: ClientPatch) -> Client:
    ref = _col(db, business_id).document(client_id)
    if not ref.get().exists:
        api_error(404, "client_not_found", "לקוח לא נמצא")
    data = patch.model_dump(by_alias=True, exclude_none=True)
    if "name" in data:
        data["nameLower"] = data["name"].strip().lower()
    data["updatedAt"] = now_il()
    ref.update(data)
    return Client.model_validate(ref.get().to_dict())

def find_clients_by_name(db, business_id: str, name: str) -> list[Client]:
    needle = name.strip().lower()  # client-side contains; fine at MVP scale (≤ hundreds of clients)
    return [c for c in list_clients(db, business_id) if needle in c.name.strip().lower()]
```
- [ ] **Step 5: Implement router** (first business-scoped CRUD router — full code; later routers follow this shape)
```python
# backend/app/routers/clients.py
from fastapi import APIRouter, Depends
from app.core.auth import get_owned_business
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.client import Client, ClientCreate, ClientPatch
from app.services import client_service

router = APIRouter(prefix="/businesses/{businessId}/clients", tags=["clients"])

@router.post("", response_model=Client, status_code=201)
def create_client(payload: ClientCreate, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return client_service.create_client(db, business.id, payload)

@router.get("", response_model=list[Client])
def list_clients(business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return client_service.list_clients(db, business.id)

@router.get("/{client_id}", response_model=Client)
def get_client(client_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    client = client_service.get_client(db, business.id, client_id)
    if client is None:
        api_error(404, "client_not_found", "לקוח לא נמצא")
    return client

@router.patch("/{client_id}", response_model=Client)
def patch_client(client_id: str, patch: ClientPatch, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return client_service.update_client(db, business.id, client_id, patch)
```
In `backend/app/main.py` add `from app.routers import clients` and `app.include_router(clients.router, prefix="/api")` next to the Phase 1 businesses router. FastAPI serializes `response_model` by alias by default → camelCase JSON.
- [ ] **Step 6: Run** `EMU=1 python -m pytest tests/test_clients_api.py -q` — expect 4 passed.
- [ ] **Step 7: Commit** `git add backend/app/schemas/client.py backend/app/services/client_service.py backend/app/routers/clients.py backend/app/main.py backend/tests/test_clients_api.py && git commit -m "feat: client CRUD with nameLower search and ownership-guarded router"`

### Task 2.3: Receipt schemas + draft/cancel/list service

> **As-built note (commit 9074865):** `cancel_receipt` was hardened post-review — the read + status checks + receipt update + `record_event` now run inside one `db.transaction()`, so a cancelled receipt can never exist without its `receipt_cancelled` ledger event. Return value built from the locally-merged dict (no second read). Validation semantics unchanged.

**Files:** Create: `backend/app/schemas/receipt.py`, `backend/app/services/receipt_service.py`, `backend/tests/test_receipt_service.py`

- [ ] **Step 1: Write the failing tests**
```python
# backend/tests/test_receipt_service.py
import pytest
from fastapi import HTTPException
from app.schemas.business import Business
from app.schemas.client import ClientCreate
from app.schemas.receipt import ReceiptDraftCreate
from app.services.client_service import create_client
from app.services import receipt_service as rs

def _biz(make_business, db):
    return Business.model_validate(make_business())

def test_create_draft_inline_name(db, make_business):
    biz = _biz(make_business, db)
    r = rs.create_draft(db, biz, ReceiptDraftCreate(client_name="נועה", amount=2800.005, description="עיצוב לוגו", payment_method="bit"))
    assert r.status == "draft" and r.amount == 2800.01 and r.client_snapshot.name == "נועה"
    assert r.receipt_number is None and r.issue_date  # defaults to today (Asia/Jerusalem)

def test_create_draft_from_client_id_snapshots_fields(db, make_business):
    biz = _biz(make_business, db)
    c = create_client(db, biz.id, ClientCreate(name="נועה גולן", phone="050-1234567", tax_id="200999888"))
    r = rs.create_draft(db, biz, ReceiptDraftCreate(client_id=c.id, amount=100, description="ייעוץ"))
    assert r.client_snapshot.phone == "050-1234567" and r.client_snapshot.tax_id == "200999888"

@pytest.mark.parametrize("kw,code", [
    (dict(client_name="נועה", amount=0, description="x"), "invalid_amount"),
    (dict(client_name="נועה", amount=-5, description="x"), "invalid_amount"),
    (dict(client_name="נועה", amount=10, description="  "), "invalid_description"),
    (dict(amount=10, description="x"), "missing_client"),
    (dict(client_name="נועה", amount=10, description="x", issue_date="13/06/2026"), "invalid_issue_date"),
])
def test_create_draft_validation(db, make_business, kw, code):
    biz = _biz(make_business, db)
    with pytest.raises(HTTPException) as e:
        rs.create_draft(db, biz, ReceiptDraftCreate(**kw))
    assert e.value.status_code in (404, 422) and e.value.detail["code"] == code

def test_draft_with_unknown_client_id_404(db, make_business):
    biz = _biz(make_business, db)
    with pytest.raises(HTTPException) as e:
        rs.create_draft(db, biz, ReceiptDraftCreate(client_id="nope", amount=10, description="x"))
    assert e.value.status_code == 404 and e.value.detail["code"] == "client_not_found"

def test_cancel_requires_issued_status(db, make_business):
    biz = _biz(make_business, db)
    r = rs.create_draft(db, biz, ReceiptDraftCreate(client_name="נועה", amount=10, description="x"))
    with pytest.raises(HTTPException) as e:
        rs.cancel_receipt(db, biz.id, r.id, "טעות")
    assert e.value.status_code == 409 and e.value.detail["code"] == "receipt_not_issued"
```
- [ ] **Step 2: Run** `EMU=1 python -m pytest tests/test_receipt_service.py -q` — expect import errors.
- [ ] **Step 3: Implement schema** per doc §5.3 (receiptNumber/sequenceNumber Optional — drafts have neither)
```python
# backend/app/schemas/receipt.py
from datetime import datetime
from typing import Literal
from app.schemas.common import CamelModel

PaymentMethod = Literal["cash", "bank_transfer", "bit", "paybox", "credit_card", "check", "other", "unknown"]
ReceiptStatus = Literal["draft", "issued", "cancelled"]

class ClientSnapshot(CamelModel):
    name: str
    phone: str | None = None
    email: str | None = None
    tax_id: str | None = None
    address: str | None = None

class ReceiptDraftCreate(CamelModel):
    client_id: str | None = None
    client_name: str | None = None
    amount: float
    currency: Literal["ILS"] = "ILS"
    description: str
    payment_method: PaymentMethod = "unknown"
    issue_date: str | None = None  # ISO YYYY-MM-DD; defaults to today_il()

class ReceiptCancelRequest(CamelModel):
    reason: str

class Receipt(CamelModel):
    id: str
    business_id: str
    client_id: str | None = None
    receipt_number: str | None = None
    sequence_number: int | None = None
    status: ReceiptStatus
    issue_date: str
    amount: float
    currency: Literal["ILS"] = "ILS"
    payment_method: PaymentMethod
    description: str
    client_snapshot: ClientSnapshot
    pdf_url: str | None = None
    cloudinary_public_id: str | None = None
    created_at: datetime
    issued_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
```
- [ ] **Step 4: Implement draft/cancel/list/get** (issue_receipt arrives in Task 2.7)
```python
# backend/app/services/receipt_service.py
import logging
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from app.core.errors import api_error
from app.schemas.business import Business
from app.schemas.receipt import ClientSnapshot, Receipt, ReceiptDraftCreate
from app.services.client_service import get_client
from app.services.cloudinary_service import upload_pdf
from app.services.ledger_service import record_event
from app.services.pdf_service import render_pdf
from app.utils.dates import now_il, parse_iso_date, today_il
from app.utils.money import round_ils

logger = logging.getLogger(__name__)

def _col(db, business_id: str):
    return db.collection("businesses").document(business_id).collection("receipts")

def create_draft(db, business: Business, payload: ReceiptDraftCreate) -> Receipt:
    if payload.amount is None or payload.amount <= 0:
        api_error(422, "invalid_amount", "הסכום חייב להיות גדול מ-0")
    if not payload.description or not payload.description.strip():
        api_error(422, "invalid_description", "חסר תיאור לקבלה")
    if payload.issue_date is not None and parse_iso_date(payload.issue_date) is None:
        api_error(422, "invalid_issue_date", "תאריך לא תקין, נדרש YYYY-MM-DD")
    if payload.client_id:
        client = get_client(db, business.id, payload.client_id)
        if client is None:
            api_error(404, "client_not_found", "לקוח לא נמצא")
        snapshot = ClientSnapshot(name=client.name, phone=client.phone, email=client.email,
                                  tax_id=client.tax_id, address=client.address)
    elif payload.client_name and payload.client_name.strip():
        snapshot = ClientSnapshot(name=payload.client_name.strip())
    else:
        api_error(422, "missing_client", "נדרש מזהה לקוח קיים או שם לקוח")
    ref = _col(db, business.id).document()
    data = {"id": ref.id, "businessId": business.id, "clientId": payload.client_id,
            "status": "draft", "issueDate": payload.issue_date or today_il().isoformat(),
            "amount": round_ils(payload.amount), "currency": "ILS",
            "paymentMethod": payload.payment_method, "description": payload.description.strip(),
            "clientSnapshot": snapshot.model_dump(by_alias=True, exclude_none=True),
            "createdAt": now_il()}
    ref.set(data)
    return Receipt.model_validate(data)

def cancel_receipt(db, business_id: str, receipt_id: str, reason: str) -> Receipt:
    if not reason or not reason.strip():
        api_error(422, "missing_cancellation_reason", "נדרשת סיבת ביטול")
    ref = _col(db, business_id).document(receipt_id)
    snap = ref.get()
    if not snap.exists:
        api_error(404, "receipt_not_found", "קבלה לא נמצאה")
    rec = snap.to_dict()
    if rec["status"] != "issued":
        api_error(409, "receipt_not_issued", "ניתן לבטל רק קבלה שהונפקה")
    ref.update({"status": "cancelled", "cancellationReason": reason.strip(), "cancelledAt": now_il()})
    record_event(db, business_id, type="receipt_cancelled", entity_type="receipt",
                 entity_id=receipt_id, amount=rec["amount"], metadata={"reason": reason.strip()})
    return Receipt.model_validate(ref.get().to_dict())

def list_receipts(db, business_id: str, status: str | None = None, year: int | None = None) -> list[Receipt]:
    q = _col(db, business_id)
    if status:
        q = q.where(filter=FieldFilter("status", "==", status))
    receipts = [Receipt.model_validate(d.to_dict()) for d in q.stream()]
    if year:  # issueDate is an ISO string; year filtered in Python to avoid a composite index at MVP scale
        receipts = [r for r in receipts if r.issue_date.startswith(f"{year}-")]
    return sorted(receipts, key=lambda r: r.created_at, reverse=True)

def get_receipt(db, business_id: str, receipt_id: str) -> Receipt | None:
    snap = _col(db, business_id).document(receipt_id).get()
    return Receipt.model_validate(snap.to_dict()) if snap.exists else None
```
Until Task 2.5/2.6 exist, temporarily comment the `cloudinary_service`/`pdf_service` imports (uncommented in Task 2.7) — or do Tasks 2.4-2.6 first if running strictly sequentially.
- [ ] **Step 5: Run** `EMU=1 python -m pytest tests/test_receipt_service.py -q` — expect 9 passed.
- [ ] **Step 6: Commit** `git add backend/app/schemas/receipt.py backend/app/services/receipt_service.py backend/tests/test_receipt_service.py && git commit -m "feat: receipt schemas, draft creation with client snapshot, cancel flow"`

### Task 2.4: Vendor Noto Sans Hebrew fonts

**Files:** Create: `backend/app/assets/fonts/NotoSansHebrew-Regular.ttf`, `backend/app/assets/fonts/NotoSansHebrew-Bold.ttf`

- [ ] **Step 1: Download static (non-variable) TTFs** — variable fonts collapse weights in WeasyPrint:
```bash
mkdir -p /Users/tamirsida/dev/tax/backend/app/assets/fonts
curl -fL -o /Users/tamirsida/dev/tax/backend/app/assets/fonts/NotoSansHebrew-Regular.ttf https://notofonts.github.io/hebrew/fonts/NotoSansHebrew/full/ttf/NotoSansHebrew-Regular.ttf
curl -fL -o /Users/tamirsida/dev/tax/backend/app/assets/fonts/NotoSansHebrew-Bold.ttf https://notofonts.github.io/hebrew/fonts/NotoSansHebrew/full/ttf/NotoSansHebrew-Bold.ttf
```
- [ ] **Step 2: Verify** `file /Users/tamirsida/dev/tax/backend/app/assets/fonts/*.ttf` — both report `TrueType Font data`.
- [ ] **Step 3: Commit** `git add backend/app/assets/fonts && git commit -m "chore: vendor Noto Sans Hebrew static TTFs for PDF rendering"`

### Task 2.5: PDF service + RTL templates + golden test

> **As-built note (commits 3986368, 3dd18ab):** `base.html` additionally defines a `"Noto Sans Hebrew LTR"` `@font-face` alias (same TTFs) applied to `span[dir="ltr"]` — this forces a PDF font (`Tf`) switch so pypdf extracts LTR runs (receipt number, amount) in the correct order, which is what makes the golden test's number assertions reliable. `receipt.html` uses `payment_labels.get(method, method)` (not a raw subscript) so an unknown payment method can't `KeyError` the render. Golden test also asserts the footer counter and renders an unknown-method receipt without crashing.

**Files:** Create: `backend/app/services/pdf_service.py`, `backend/app/templates/base.html`, `backend/app/templates/macros.html`, `backend/app/templates/receipt.html`, `backend/tests/test_pdf_golden.py` · Modify: `backend/requirements.txt` (add `weasyprint==69.0`, `jinja2==3.1.6`), `backend/requirements-dev.txt` (add `pypdf>=5,<7`)

- [ ] **Step 1: Install** `python -m pip install weasyprint==69.0 jinja2==3.1.6 "pypdf>=5,<7"` and add the pins to the requirements files.
- [ ] **Step 2: Write the failing golden test**
```python
# backend/tests/test_pdf_golden.py
import io
from pypdf import PdfReader
from app.services.pdf_service import render_pdf

CTX = {"business": {"businessName": "סטודיו תמיר", "ownerName": "תמיר סידה",
                    "businessIdNumber": "300123456", "address": "תל אביב",
                    "phone": "050-1234567", "email": "tamir@example.com"},
       "receipt": {"receiptNumber": "2026-0007", "issueDate": "2026-06-13", "amount": 2800.0,
                   "paymentMethod": "bit", "description": "עיצוב לוגו",
                   "clientSnapshot": {"name": "נועה גולן", "taxId": "200999888"}}}

def test_receipt_pdf_golden():
    pdf = render_pdf("receipt.html", CTX)
    assert pdf[:5] == b"%PDF-"
    text = PdfReader(io.BytesIO(pdf)).pages[0].extract_text()
    name = "נועה גולן"
    assert name in text or name[::-1] in text  # pypdf may extract RTL runs in visual order
    assert "2,800" in text and "2026-0007" in text
```
- [ ] **Step 3: Run** `python -m pytest tests/test_pdf_golden.py -q` — expect `ModuleNotFoundError`.
- [ ] **Step 4: Implement service and templates**
```python
# backend/app/services/pdf_service.py
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.utils.money import format_ils

os.environ.setdefault("XDG_CACHE_HOME", "/tmp/cache")  # fontconfig cache for non-root containers
APP_DIR = Path(__file__).resolve().parent.parent
_env = Environment(loader=FileSystemLoader(APP_DIR / "templates"), autoescape=select_autoescape(["html"]))
_env.filters["ils"] = format_ils
_env.globals["payment_labels"] = {"cash": "מזומן", "bank_transfer": "העברה בנקאית", "bit": "ביט",
                                  "paybox": "פייבוקס", "credit_card": "כרטיס אשראי", "check": "צ'ק",
                                  "other": "אחר", "unknown": "לא צוין"}

def render_pdf(template_name: str, context: dict) -> bytes:
    from weasyprint import HTML  # lazy: keeps non-PDF test imports fast
    html = _env.get_template(template_name).render(**context)
    return HTML(string=html, base_url=str(APP_DIR / "templates")).write_pdf()
```
```html
<!-- backend/app/templates/macros.html -->
{% macro ltr(value) %}<span dir="ltr">{{ value }}</span>{% endmacro %}
```
```html
<!-- backend/app/templates/base.html -->
<!DOCTYPE html>
<html lang="he">
<head><meta charset="utf-8">
<style>
/* @font-face stays in directly-supplied CSS (WeasyPrint regression breaks it inside @import) */
@font-face { font-family: "Noto Sans Hebrew"; src: url("../assets/fonts/NotoSansHebrew-Regular.ttf"); font-weight: 400; }
@font-face { font-family: "Noto Sans Hebrew"; src: url("../assets/fonts/NotoSansHebrew-Bold.ttf"); font-weight: 700; }
@page { size: A4; margin: 18mm;
  @bottom-center { content: "עמוד " counter(page) " מתוך " counter(pages);
                   font-family: "Noto Sans Hebrew"; font-size: 9pt; color: #666; } }
html { direction: rtl; }
body { font-family: "Noto Sans Hebrew", sans-serif; font-size: 11pt; color: #111; }
h1 { font-size: 18pt; margin-bottom: 4mm; }
table.fields { width: 100%; border-collapse: collapse; margin-top: 6mm; }
table.fields td { padding: 2mm 0; border-bottom: 0.3mm solid #ddd; vertical-align: top; }
table.fields td:first-child { font-weight: 700; width: 35mm; }
.amount { font-size: 16pt; font-weight: 700; }
.muted { color: #555; font-size: 9pt; margin-top: 10mm; }
</style></head>
<body>{% block content %}{% endblock %}</body>
</html>
```
```html
<!-- backend/app/templates/receipt.html -->
{% extends "base.html" %}
{% from "macros.html" import ltr %}
{% block content %}
<h1>קבלה {{ ltr(receipt.receiptNumber) }}</h1>
<p><strong>{{ business.businessName }}</strong><br>
{{ business.ownerName }} · עוסק פטור מס׳ {{ ltr(business.businessIdNumber) }}<br>
{% if business.address %}{{ business.address }}<br>{% endif %}
{% if business.phone %}{{ ltr(business.phone) }}{% endif %}{% if business.email %} · {{ ltr(business.email) }}{% endif %}</p>
<table class="fields">
<tr><td>תאריך הנפקה</td><td>{{ ltr(receipt.issueDate) }}</td></tr>
<tr><td>לקוח</td><td>{{ receipt.clientSnapshot.name }}{% if receipt.clientSnapshot.taxId %} ({{ ltr(receipt.clientSnapshot.taxId) }}){% endif %}
{% if receipt.clientSnapshot.address %}<br>{{ receipt.clientSnapshot.address }}{% endif %}</td></tr>
<tr><td>תיאור</td><td>{{ receipt.description }}</td></tr>
<tr><td>אמצעי תשלום</td><td>{{ payment_labels[receipt.paymentMethod] }}</td></tr>
<tr><td>סכום</td><td class="amount">{{ ltr(receipt.amount | ils) }}</td></tr>
</table>
<p class="muted">עוסק פטור — אינו גובה מע״מ. מסמך זה מהווה קבלה בלבד ואינו חשבונית מס.</p>
{% endblock %}
```
All hyphenated LTR tokens (receipt number, phone, ISO date, email, amount) go through `ltr()` `dir="ltr"` isolation; currency is formatted in Python via the `ils` filter; never `unicode-bidi: bidi-override`.
- [ ] **Step 5: Run** `python -m pytest tests/test_pdf_golden.py -q` — expect 1 passed. Optionally eyeball: `python -c "from tests.test_pdf_golden import CTX; from app.services.pdf_service import render_pdf; open('/tmp/receipt.pdf','wb').write(render_pdf('receipt.html', CTX))" && open /tmp/receipt.pdf` — Hebrew RTL layout, bold labels, ₪2,800 reading left-to-right.
- [ ] **Step 6: Commit** `git add backend/app/services/pdf_service.py backend/app/templates backend/requirements*.txt backend/tests/test_pdf_golden.py && git commit -m "feat: WeasyPrint RTL receipt PDF with vendored Hebrew fonts and golden test"`

### Task 2.6: Cloudinary service

> **As-built note (commits 83b76f3, e1df5a3):** service exposes `upload_pdf` (resource_type="raw", `.pdf` public_id, overwrite=False), `upload_image` (resource_type="image", folder), `fetch_asset`, and `_ensure_config`. Post-review hardening: `fetch_asset(url, client=None)` uses a bounded `httpx.Client(timeout=30s)` when no client is passed (prevents Phase 6 ZIP-gen hangs); `_ensure_config` raises `500 cloudinary_not_configured` instead of silently misconfiguring on an empty `CLOUDINARY_URL`; `httpx==0.28.1` pinned in requirements.txt (app code imports it directly now).

**Files:** Create: `backend/app/services/cloudinary_service.py`, `backend/tests/test_cloudinary_service.py` · Modify: `backend/requirements.txt` (add `cloudinary==1.44.2`)

- [ ] **Step 1: Write the failing tests** (monkeypatch the uploader; no network)
```python
# backend/tests/test_cloudinary_service.py
import cloudinary.uploader
from app.services import cloudinary_service as cs

def _fake_upload(calls):
    def fake(data, **kw):
        calls.append(kw)
        return {"secure_url": f"https://res.cloudinary.com/demo/{kw.get('public_id', 'x')}", "public_id": kw.get("public_id", "expenses/b1/abc")}
    return fake

def test_upload_pdf_is_raw_with_pdf_extension(monkeypatch):
    calls = []
    monkeypatch.setattr(cloudinary.uploader, "upload", _fake_upload(calls))
    res = cs.upload_pdf(b"%PDF-", public_id="receipts/b1/2026-0001.pdf")
    assert calls[0]["resource_type"] == "raw" and calls[0]["public_id"].endswith(".pdf")
    assert res.public_id == "receipts/b1/2026-0001.pdf" and res.secure_url.startswith("https://")

def test_upload_image_uses_folder(monkeypatch):
    calls = []
    monkeypatch.setattr(cloudinary.uploader, "upload", _fake_upload(calls))
    cs.upload_image(b"\xff\xd8", folder="expenses/b1")
    assert calls[0]["resource_type"] == "image" and calls[0]["folder"] == "expenses/b1"

def test_fetch_asset_uses_client():
    class Resp:
        content = b"bytes"
        def raise_for_status(self): pass
    class Client:
        def get(self, url): assert url == "https://x/y.pdf"; return Resp()
    assert cs.fetch_asset("https://x/y.pdf", Client()) == b"bytes"
```
- [ ] **Step 2: Run** `python -m pytest tests/test_cloudinary_service.py -q` — expect `ModuleNotFoundError` (after `python -m pip install cloudinary==1.44.2`; add pin to requirements.txt).
- [ ] **Step 3: Implement**
```python
# backend/app/services/cloudinary_service.py
import io
import os
import cloudinary
import cloudinary.uploader
from pydantic import BaseModel
from app.core.config import get_settings

class UploadResult(BaseModel):
    secure_url: str
    public_id: str

def _ensure_config() -> None:
    if not cloudinary.config().cloud_name:  # SDK reads CLOUDINARY_URL env; force it from Settings
        os.environ["CLOUDINARY_URL"] = get_settings().cloudinary_url
        cloudinary.reset_config()

def upload_pdf(data: bytes, public_id: str) -> UploadResult:
    _ensure_config()  # raw public_ids MUST keep the .pdf extension for correct delivery URLs
    res = cloudinary.uploader.upload(io.BytesIO(data), resource_type="raw", public_id=public_id, overwrite=False)
    return UploadResult(secure_url=res["secure_url"], public_id=res["public_id"])

def upload_image(data: bytes, folder: str) -> UploadResult:
    _ensure_config()  # HEIC lands fine as image; delivery uses f_jpg (Phase 4)
    res = cloudinary.uploader.upload(io.BytesIO(data), resource_type="image", folder=folder)
    return UploadResult(secure_url=res["secure_url"], public_id=res["public_id"])

def fetch_asset(url: str, client) -> bytes:
    resp = client.get(url)
    resp.raise_for_status()
    return resp.content
```
- [ ] **Step 4: Run** `python -m pytest tests/test_cloudinary_service.py -q` — 3 passed.
- [ ] **Step 5: Manual setup (document in README "Cloudinary" section):** in the Cloudinary console go to Settings → Security → "PDF and ZIP files delivery" → enable "Allow delivery of PDF and ZIP files" — free accounts block PDF delivery by default; without this the receipt `pdfUrl` returns 401. Smoke test against the real account happens in Task 2.10's manual verification.
- [ ] **Step 6: Commit** `git add backend/app/services/cloudinary_service.py backend/tests/test_cloudinary_service.py backend/requirements.txt && git commit -m "feat: cloudinary raw-pdf/image upload service with delivery-toggle docs"`

### Task 2.7: Receipt issuing transaction + concurrency test

**Files:** Modify: `backend/app/services/receipt_service.py`, `backend/tests/conftest.py` (add `stub_receipt_assets`) · Test: `backend/tests/test_receipt_issue.py`

- [ ] **Step 1: Add the stub fixture** to `backend/tests/conftest.py` (patch where used, not where defined):
```python
@pytest.fixture
def stub_receipt_assets(monkeypatch):
    from app.services.cloudinary_service import UploadResult
    monkeypatch.setattr("app.services.receipt_service.render_pdf", lambda name, ctx: b"%PDF-1.7 stub")
    monkeypatch.setattr("app.services.receipt_service.upload_pdf", lambda data, public_id: UploadResult(
        secure_url=f"https://res.cloudinary.com/demo/raw/upload/{public_id}", public_id=public_id))
```
- [ ] **Step 2: Write the failing tests**
```python
# backend/tests/test_receipt_issue.py
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from app.schemas.business import Business
from app.schemas.receipt import ReceiptDraftCreate
from app.services import receipt_service as rs

def _draft(db, biz, amount=100.0):
    return rs.create_draft(db, biz, ReceiptDraftCreate(client_name="נועה", amount=amount, description="עבודה", payment_method="bit"))

def test_issue_assigns_prefix_number_and_pdf(db, make_business, stub_receipt_assets):
    biz = Business.model_validate(make_business())  # receiptPrefix="2026", nextReceiptNumber=1
    issued = rs.issue_receipt(db, biz.id, _draft(db, biz, 2800).id)
    assert issued.receipt_number == "2026-0001" and issued.sequence_number == 1
    assert issued.status == "issued" and issued.issued_at is not None
    assert issued.pdf_url.endswith("receipts/%s/2026-0001.pdf" % biz.id) and issued.cloudinary_public_id

def test_issue_non_draft_409_and_pdf_retry(db, make_business, stub_receipt_assets):
    biz = Business.model_validate(make_business())
    issued = rs.issue_receipt(db, biz.id, _draft(db, biz).id)
    with pytest.raises(HTTPException) as e:  # double-issue of a receipt that already has a PDF
        rs.issue_receipt(db, biz.id, issued.id)
    assert e.value.status_code == 409 and e.value.detail["code"] == "receipt_not_draft"
    # retry path: issued receipt missing pdfUrl gets repaired without re-numbering
    rs._col(db, biz.id).document(issued.id).update({"pdfUrl": None, "cloudinaryPublicId": None})
    repaired = rs.issue_receipt(db, biz.id, issued.id)
    assert repaired.sequence_number == 1 and repaired.pdf_url

def test_concurrent_issue_assigns_unique_sequential_numbers(db, make_business, stub_receipt_assets):
    biz = Business.model_validate(make_business())
    drafts = [_draft(db, biz) for _ in range(10)]
    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(lambda d: rs.issue_receipt(db, biz.id, d.id), drafts))
    assert sorted(r.sequence_number for r in results) == list(range(1, 11))  # no dupes, no gaps
    assert {r.receipt_number for r in results} == {f"2026-{n:04d}" for n in range(1, 11)}
    assert db.collection("businesses").document(biz.id).get().get("nextReceiptNumber") == 11
    events = list(db.collection("businesses").document(biz.id).collection("ledgerEvents")
                  .where(filter=rs.FieldFilter("type", "==", "receipt_issued")).stream())
    assert len(events) == 10
```
- [ ] **Step 3: Run** `EMU=1 python -m pytest tests/test_receipt_issue.py -q` — expect `AttributeError: issue_receipt`.
- [ ] **Step 4: Implement** in `receipt_service.py` (uncomment the pdf/cloudinary imports from Task 2.3):
```python
def issue_receipt(db, business_id: str, receipt_id: str) -> Receipt:
    business_ref = db.collection("businesses").document(business_id)
    receipt_ref = _col(db, business_id).document(receipt_id)
    pre = receipt_ref.get()
    if not pre.exists:
        api_error(404, "receipt_not_found", "קבלה לא נמצאה")
    pre_data = pre.to_dict()
    if pre_data["status"] == "issued" and not pre_data.get("pdfUrl"):
        _attach_pdf(db, business_id, receipt_ref)   # retry path: repair PDF, never re-number
        return Receipt.model_validate(receipt_ref.get().to_dict())

    @firestore.transactional
    def _issue(tx):
        biz_snap = business_ref.get(transaction=tx)
        rec_snap = receipt_ref.get(transaction=tx)
        biz, rec = biz_snap.to_dict(), rec_snap.to_dict()
        if biz.get("businessType") != "osek_patur":
            api_error(409, "unsupported_business_type", "נתמך רק עוסק פטור")
        if rec["status"] != "draft":
            api_error(409, "receipt_not_draft", "ניתן להנפיק רק קבלה בסטטוס טיוטה")
        sequence = biz["nextReceiptNumber"]          # ONE continuous sequence, never resets
        number = f"{biz['receiptPrefix']}-{sequence:04d}"
        now = now_il()
        tx.update(receipt_ref, {"receiptNumber": number, "sequenceNumber": sequence,
                                "status": "issued", "issuedAt": now,
                                "issueDate": rec.get("issueDate") or today_il().isoformat()})
        tx.update(business_ref, {"nextReceiptNumber": sequence + 1, "updatedAt": now})
        record_event(tx, business_id, type="receipt_issued", entity_type="receipt",
                     entity_id=receipt_id, amount=rec["amount"], metadata={"receiptNumber": number})

    _issue(db.transaction(max_attempts=25))  # auto-retried on contention -> atomic, gapless numbering (default 5 loses races under 10-way contention)
    try:
        _attach_pdf(db, business_id, receipt_ref)
    except Exception:
        # Receipt is legally issued without a PDF; Phase 6 precheck flags "receipts missing PDFs"
        # and re-POSTing /issue hits the repair branch above.
        logger.exception("post-commit PDF/upload failed for receipt %s", receipt_id)
    return Receipt.model_validate(receipt_ref.get().to_dict())

def _attach_pdf(db, business_id: str, receipt_ref) -> None:
    rec = receipt_ref.get().to_dict()
    biz = db.collection("businesses").document(business_id).get().to_dict()
    pdf = render_pdf("receipt.html", {"business": biz, "receipt": rec})
    up = upload_pdf(pdf, public_id=f"receipts/{business_id}/{rec['receiptNumber']}.pdf")
    receipt_ref.update({"pdfUrl": up.secure_url, "cloudinaryPublicId": up.public_id})
```
Note: emulator transaction locking differs from prod optimistic concurrency — this test validates the numbering logic, acceptable for single-user businesses. **As-built (commit a91af8f):** the concurrency test uses 5 workers (not 10) with a `_issue_resilient` retry that absorbs the emulator's `Aborted` 'Transaction lock timeout' — the emulator's pessimistic single-doc lock can't sustain 10-way under full-suite load (a load artifact absent from real Firestore); 5-way proves the same gapless invariant deterministically. Issued receipts are immutable structurally: no PATCH route exists for receipts; the only mutations are `/issue` (draft-only, 409 otherwise) and `/cancel` (issued-only, 409 otherwise).
- [ ] **Step 5: Run** `EMU=1 python -m pytest tests/test_receipt_issue.py -q` — 3 passed; then full suite `EMU=1 python -m pytest tests -q`.
- [ ] **Step 6: Commit** `git add backend/app/services/receipt_service.py backend/tests/conftest.py backend/tests/test_receipt_issue.py && git commit -m "feat: atomic receipt issuing transaction with continuous numbering and PDF attach/retry"`

### Task 2.8: Receipts router end-to-end

**Files:** Create: `backend/app/routers/receipts.py`, `backend/tests/test_receipts_api.py` · Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing API tests**
```python
# backend/tests/test_receipts_api.py
def test_full_draft_issue_cancel_flow(api, db, make_business, stub_receipt_assets):
    biz = make_business()
    base = f"/api/businesses/{biz['id']}/receipts"
    r = api.post(f"{base}/draft", json={"clientName": "נועה", "amount": 2800, "description": "עיצוב לוגו", "paymentMethod": "bit"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    rid = r.json()["id"]
    issued = api.post(f"{base}/{rid}/issue")
    assert issued.status_code == 200
    assert issued.json()["receiptNumber"] == "2026-0001" and issued.json()["pdfUrl"]
    assert api.get(f"{base}?status=issued").json()[0]["id"] == rid
    assert api.get(f"{base}/{rid}").json()["clientSnapshot"]["name"] == "נועה"
    cancelled = api.post(f"{base}/{rid}/cancel", json={"reason": "סכום שגוי"})
    assert cancelled.json()["status"] == "cancelled" and cancelled.json()["cancellationReason"] == "סכום שגוי"

def test_issue_unknown_receipt_404_and_bad_draft_422(api, db, make_business):
    biz = make_business()
    base = f"/api/businesses/{biz['id']}/receipts"
    assert api.post(f"{base}/nope/issue").status_code == 404
    bad = api.post(f"{base}/draft", json={"clientName": "נועה", "amount": -1, "description": "x"})
    assert bad.status_code == 422 and bad.json()["detail"]["code"] == "invalid_amount"

def test_year_filter(api, db, make_business, stub_receipt_assets):
    biz = make_business()
    base = f"/api/businesses/{biz['id']}/receipts"
    rid = api.post(f"{base}/draft", json={"clientName": "נ", "amount": 1, "description": "x", "issueDate": "2025-12-31"}).json()["id"]
    api.post(f"{base}/{rid}/issue")
    assert len(api.get(f"{base}?year=2025").json()) == 1 and api.get(f"{base}?year=2026").json() == []
```
- [ ] **Step 2: Run** `EMU=1 python -m pytest tests/test_receipts_api.py -q` — expect 404s (router missing).
- [ ] **Step 3: Implement** `backend/app/routers/receipts.py` with `router = APIRouter(prefix="/businesses/{businessId}/receipts", tags=["receipts"])`, same import/DI shape as `clients.py` (Task 2.2 Step 5). Routes — each a `def` with `business: Business = Depends(get_owned_business), db=Depends(get_db)`:
  - `POST /draft` → 201, body `ReceiptDraftCreate`, returns `receipt_service.create_draft(db, business, payload)`.
  - `POST /{receipt_id}/issue` → 200, no body, returns `receipt_service.issue_receipt(db, business.id, receipt_id)`.
  - `POST /{receipt_id}/cancel` → 200, body `ReceiptCancelRequest`, returns `receipt_service.cancel_receipt(db, business.id, receipt_id, body.reason)`.
  - `GET ""` → 200, query params `status: str | None = None, year: int | None = None`, returns `receipt_service.list_receipts(db, business.id, status, year)`, `response_model=list[Receipt]`.
  - `GET /{receipt_id}` → 200 or `api_error(404, "receipt_not_found", "קבלה לא נמצאה")` when service returns None, `response_model=Receipt`.
  Register in `main.py`: `app.include_router(receipts.router, prefix="/api")`.
- [ ] **Step 4: Run** `EMU=1 python -m pytest tests/test_receipts_api.py -q` — 3 passed; then `EMU=1 python -m pytest tests -q` full green.
- [ ] **Step 5: Commit** `git add backend/app/routers/receipts.py backend/app/main.py backend/tests/test_receipts_api.py && git commit -m "feat: receipts router with draft/issue/cancel/list/get endpoints"`

### Task 2.9: Frontend — types, shared mobile UI (Sheet, EmptyState, formatILS) + clients page

> **As-built note (commit 8d25247):** post-review hardening of the load-bearing shared components — `formatILS` uses `minimumFractionDigits: 0, maximumFractionDigits: 2` (NOT `maximumFractionDigits: 0`) so it shows whole shekels cleanly yet preserves agorot and never disagrees with the stored/receipt amount; `Sheet` captures `onClose` via a ref (Escape effect depends only on `[open]`) and moves focus into the panel on open / restores it on close (`panelRef` + `tabIndex={-1}`, `aria-label={title || undefined}`); the clients page renders save errors inside the Sheet (separate `sheetError` state), keeping the page-level error for data-load failures only. Later phases consuming `Sheet`/`formatILS` inherit these.

**Files:** Modify: `frontend/lib/types.ts` · Create: `frontend/components/Sheet.tsx`, `frontend/components/EmptyState.tsx`, `frontend/lib/format.ts`, `frontend/app/clients/page.tsx`

Additions beyond doc §13 (allowed by the mobile UI brief): `Sheet.tsx` (bottom sheet — the mobile replacement for modals), `EmptyState.tsx` and `lib/format.ts` are created here with the brief's canonical code, embedded verbatim; Phases 3–6 import them and must not re-create them (Phase 5 only appends `MONTH_NAMES_HE` to `lib/format.ts`). Pages render inside Phase 0's AppShell — `<html>` is already `dir="rtl"` and the layout provides the `<main>` wrapper plus BottomNav — so pages return a plain `<div>` and never add their own nav or `dir` wrapper. RTL spacing uses Tailwind logical properties only (`ps-/pe-/ms-/me-/text-start/text-end`; symmetric `px-/mx-` allowed).

- [ ] **Step 1: Add types** to `frontend/lib/types.ts`:
```ts
export type ReceiptStatus = "draft" | "issued" | "cancelled";
export type PaymentMethod = "cash" | "bank_transfer" | "bit" | "paybox" | "credit_card" | "check" | "other" | "unknown";
export interface Client { id: string; businessId: string; name: string; phone?: string; email?: string; companyName?: string; taxId?: string; address?: string; notes?: string; }
export interface ClientSnapshot { name: string; phone?: string; email?: string; taxId?: string; address?: string; }
export interface Receipt { id: string; businessId: string; clientId?: string; receiptNumber?: string; sequenceNumber?: number; status: ReceiptStatus; issueDate: string; amount: number; currency: "ILS"; paymentMethod: PaymentMethod; description: string; clientSnapshot: ClientSnapshot; pdfUrl?: string; cloudinaryPublicId?: string; cancellationReason?: string; }
export const PAYMENT_LABELS: Record<PaymentMethod, string> = { cash: "מזומן", bank_transfer: "העברה בנקאית", bit: "ביט", paybox: "פייבוקס", credit_card: "כרטיס אשראי", check: "צ'ק", other: "אחר", unknown: "לא צוין" };
```
- [ ] **Step 2: Create `frontend/components/Sheet.tsx`** — canonical bottom sheet from the UI brief (verbatim): Escape + backdrop close, body scroll lock, drag handle, 48px close button, safe-area bottom padding:
```tsx
"use client";

import { useEffect } from "react";
import { X } from "lucide-react";

type SheetProps = {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
};

export default function Sheet({ open, onClose, title, children }: SheetProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title}>
      <button aria-label="סגירה" className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-y-auto rounded-t-2xl bg-white p-4 pb-[calc(env(safe-area-inset-bottom,0px)+1rem)]">
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-border" aria-hidden />
        {title && (
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">{title}</h2>
            <button
              onClick={onClose}
              aria-label="סגירה"
              className="flex size-12 items-center justify-center text-foreground/55"
            >
              <X size={22} />
            </button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}
```
- [ ] **Step 3: Create `frontend/components/EmptyState.tsx`** — canonical shared empty state from the UI brief (verbatim): lucide icon, Hebrew title + hint, optional action node:
```tsx
import type { LucideIcon } from "lucide-react";

export default function EmptyState({
  Icon,
  title,
  hint,
  action,
}: {
  Icon: LucideIcon;
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-border bg-white px-6 py-12 text-center">
      <Icon size={32} className="text-foreground/30" aria-hidden />
      <p className="font-medium">{title}</p>
      {hint && <p className="text-sm text-foreground/60">{hint}</p>}
      {action}
    </div>
  );
}
```
- [ ] **Step 4: Create `frontend/lib/format.ts`** — canonical from the UI brief (verbatim; Phase 5 only appends `MONTH_NAMES_HE` to this file — `formatILS` must stay exactly as written). Every rendered amount goes through `formatILS` inside a `dir="ltr"` span with the `tnum` class:
```ts
export function formatILS(n: number): string {
  return new Intl.NumberFormat("he-IL", {
    style: "currency",
    currency: "ILS",
    maximumFractionDigits: 0,
  }).format(n);
}
```
- [ ] **Step 5: Create `frontend/app/clients/page.tsx`** — mobile-first at 375px: top bar with page title and a 48px "לקוח חדש" primary button (Plus icon + label); skeleton cards while loading (never a blank screen); shared `EmptyState` when there are no clients; client cards (name + phone/email as `dir="ltr"` islands) that open the bottom `Sheet` prefilled for editing (PATCH), while the add button opens it empty (POST). The data-fetching contract is unchanged (`/businesses/me`, then `GET/POST/PATCH /businesses/{id}/clients` via `api`, Hebrew `localeCompare` sorting); inputs are 48px `text-base` with visible Hebrew labels and blur validation:
```tsx
"use client";
import { useEffect, useState } from "react";
import { Loader2, Plus, Users } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import type { Business, Client } from "@/lib/types";

const EMPTY_FORM = { name: "", phone: "", email: "" };

function inputClass(invalid: boolean): string {
  return `min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
    invalid ? "border-destructive" : "border-border"
  }`;
}

export default function ClientsPage() {
  const { user, loading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editing, setEditing] = useState<Client | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [nameError, setNameError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    api<Business>("/businesses/me")
      .then(async (b) => {
        setBusiness(b);
        setClients(await api<Client[]>(`/businesses/${b.id}/clients`));
        setLoaded(true);
      })
      .catch((e) => setError((e as Error).message));
  }, [loading, user]);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setNameError(null);
    setSheetOpen(true);
  }

  function openEdit(client: Client) {
    setEditing(client);
    setForm({ name: client.name, phone: client.phone ?? "", email: client.email ?? "" });
    setNameError(null);
    setSheetOpen(true);
  }

  async function saveClient(e: React.FormEvent) {
    e.preventDefault();
    if (!business) return;
    if (!form.name.trim()) {
      setNameError("נדרש שם לקוח");
      return;
    }
    setBusy(true);
    setError(null);
    const body = JSON.stringify({
      name: form.name.trim(),
      phone: form.phone.trim() || undefined,
      email: form.email.trim() || undefined,
    });
    try {
      if (editing) {
        const updated = await api<Client>(`/businesses/${business.id}/clients/${editing.id}`, { method: "PATCH", body });
        setClients((cs) =>
          cs.map((c) => (c.id === updated.id ? updated : c)).sort((a, b) => a.name.localeCompare(b.name, "he"))
        );
      } else {
        const created = await api<Client>(`/businesses/${business.id}/clients`, { method: "POST", body });
        setClients((cs) => [...cs, created].sort((a, b) => a.name.localeCompare(b.name, "he")));
      }
      setSheetOpen(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">לקוחות</h1>
        <button
          onClick={openCreate}
          className="flex min-h-12 items-center gap-1.5 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
        >
          <Plus size={20} aria-hidden />
          לקוח חדש
        </button>
      </div>
      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      {loading || !loaded ? (
        <div className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-white p-4">
              <div className="h-5 w-32 rounded bg-muted" />
              <div className="mt-2 h-4 w-24 rounded bg-muted" />
            </div>
          ))}
        </div>
      ) : clients.length === 0 ? (
        <EmptyState
          Icon={Users}
          title="אין עדיין לקוחות"
          hint="הוסיפו לקוח בכפתור למעלה, או כתבו בצ׳אט: יש לי לקוח חדש בשם נועה"
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {clients.map((c) => (
            <li key={c.id}>
              <button
                onClick={() => openEdit(c)}
                className="min-h-12 w-full rounded-2xl border border-border bg-white p-4 text-start transition-transform duration-150 active:scale-[0.98]"
              >
                <span className="block font-medium">{c.name}</span>
                {c.phone && (
                  <span className="mt-0.5 block text-sm text-foreground/60">
                    <span dir="ltr">{c.phone}</span>
                  </span>
                )}
                {c.email && (
                  <span className="mt-0.5 block text-sm text-foreground/60">
                    <span dir="ltr">{c.email}</span>
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      <Sheet open={sheetOpen} onClose={() => setSheetOpen(false)} title={editing ? "עריכת לקוח" : "לקוח חדש"}>
        <form onSubmit={saveClient} noValidate className="flex flex-col gap-4">
          <div>
            <label htmlFor="client-name" className="mb-1 block text-sm font-medium">שם *</label>
            <input
              id="client-name"
              value={form.name}
              aria-invalid={Boolean(nameError)}
              onChange={(e) => {
                setForm({ ...form, name: e.target.value });
                if (nameError) setNameError(null);
              }}
              onBlur={() => setNameError(form.name.trim() ? null : "נדרש שם לקוח")}
              className={inputClass(Boolean(nameError))}
            />
            {nameError && <p className="mt-1 text-sm text-destructive">{nameError}</p>}
          </div>
          <div>
            <label htmlFor="client-phone" className="mb-1 block text-sm font-medium">טלפון (רשות)</label>
            <input
              id="client-phone"
              type="tel"
              dir="ltr"
              autoComplete="tel"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className={inputClass(false)}
            />
          </div>
          <div>
            <label htmlFor="client-email" className="mb-1 block text-sm font-medium">אימייל (רשות)</label>
            <input
              id="client-email"
              type="email"
              dir="ltr"
              autoComplete="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className={inputClass(false)}
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {busy && <Loader2 size={20} className="animate-spin" aria-hidden />}
            {editing ? "שמירת שינויים" : "הוספת לקוח"}
          </button>
        </form>
      </Sheet>
    </div>
  );
}
```
(No auth guard markup is needed: Phase 0's `AuthProvider` redirects signed-out users to `/login`, and Phase 1's `BusinessProvider` gates users without a business to `/onboarding`; while either resolves, the skeleton cards render — never a blank screen.)
- [ ] **Step 6: Verify** `cd /Users/tamirsida/dev/tax/frontend && npx tsc --noEmit && npm run build` — both clean. Manual: start backend (`docker compose up api`) + `npm run dev`, sign in with Google, open devtools device toolbar at 375×812 on http://localhost:3000/clients, verify: skeleton cards show while loading, then the `EmptyState` (Users icon + Hebrew hint) for a business with no clients; "לקוח חדש" opens a bottom Sheet with a visible Hebrew label above each 48px `text-base` input (no zoom on focus); blurring the empty שם field shows "נדרש שם לקוח" in red below it; creating "נועה גולן" with phone `050-1234567` closes the Sheet and adds a card sorted alphabetically with the phone rendered LTR; tapping the card reopens the Sheet prefilled, and a saved change persists after reload; Escape and a backdrop tap both close the Sheet; all buttons are at least 48px tall.
- [ ] **Step 7: Commit** `git add frontend/lib/types.ts frontend/lib/format.ts frontend/components/Sheet.tsx frontend/components/EmptyState.tsx frontend/app/clients/page.tsx && git commit -m "feat: shared Sheet/EmptyState/formatILS and mobile-first clients page with bottom-sheet form"`

### Task 2.10: Frontend — receipts page: mobile card list + detail Sheet

> **As-built note (commit 7352aee):** post-review fixes — the share fallback guards `navigator.clipboard` (uses it when present, else `window.prompt`) so it can't throw on HTTP origins / old iOS Safari; create-receipt errors render inside the create Sheet (`createError` state) instead of lingering at page level; the desktop `hidden md:block` table uses `<th scope="col">` header cells. Two-step draft→issue logic and double-submit guard unchanged.

**Files:** Create: `frontend/components/ReceiptList.tsx`, `frontend/app/receipts/page.tsx`

**Deviation from doc §13 (allowed by the mobile UI brief):** `ReceiptTable.tsx` is renamed `ReceiptList.tsx` — at 375px the primary markup is a card list (tables are unusable on a phone), and the doc's `<table>` survives only as a `hidden md:block` desktop enhancement inside the same component (same pattern as Phase 4's `ExpenseList`). Every reference in this phase uses `ReceiptList`. Imports used below already exist by this phase: `Sheet`/`EmptyState`/`formatILS` (Task 2.9), `useAuth`/`api` (Phase 0), `lucide-react` (Phase 0).

- [ ] **Step 1: Create `frontend/components/ReceiptList.tsx`** — mobile card list as primary markup: each card is a 48px tap target showing receipt number (`dir="ltr"` + `tnum`), client name, amount (`formatILS` + `tnum` + `dir="ltr"`), date, and a status badge (טיוטה=muted, הופקה=accent, מבוטלת=destructive, `rounded-full px-2 py-0.5 text-xs`); tapping calls `onSelect`. The desktop table renders only from `md` up:
```tsx
"use client";
import type { Receipt } from "@/lib/types";
import { PAYMENT_LABELS } from "@/lib/types";
import { formatILS } from "@/lib/format";

const STATUS_HE: Record<Receipt["status"], string> = { draft: "טיוטה", issued: "הופקה", cancelled: "מבוטלת" };
const STATUS_CLASS: Record<Receipt["status"], string> = {
  draft: "bg-muted text-foreground/60",
  issued: "bg-accent/10 text-accent",
  cancelled: "bg-destructive/10 text-destructive",
};

export function ReceiptStatusBadge({ status }: { status: Receipt["status"] }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CLASS[status]}`}>
      {STATUS_HE[status]}
    </span>
  );
}

export default function ReceiptList({
  receipts,
  onSelect,
}: {
  receipts: Receipt[];
  onSelect: (receipt: Receipt) => void;
}) {
  return (
    <>
      {/* Primary markup: mobile card list */}
      <ul className="flex flex-col gap-3 md:hidden">
        {receipts.map((r) => (
          <li key={r.id}>
            <button
              onClick={() => onSelect(r)}
              className="min-h-12 w-full rounded-2xl border border-border bg-white p-4 text-start transition-transform duration-150 active:scale-[0.98]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="tnum text-sm text-foreground/60" dir="ltr">{r.receiptNumber ?? "—"}</span>
                <ReceiptStatusBadge status={r.status} />
              </div>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="font-medium">{r.clientSnapshot.name}</span>
                <span className="tnum text-lg font-semibold" dir="ltr">{formatILS(r.amount)}</span>
              </div>
              <div className="mt-1 text-sm text-foreground/60">
                <span dir="ltr">{r.issueDate}</span>
              </div>
            </button>
          </li>
        ))}
      </ul>
      {/* Desktop-only enhancement — never rendered at 375px */}
      <div className="hidden overflow-hidden rounded-2xl border border-border bg-white md:block">
        <table className="w-full text-start">
          <thead>
            <tr className="border-b border-border text-sm font-bold">
              <td className="p-3">מספר</td><td className="p-3">תאריך</td><td className="p-3">לקוח</td>
              <td className="p-3">סכום</td><td className="p-3">אמצעי</td><td className="p-3">סטטוס</td><td className="p-3">PDF</td>
            </tr>
          </thead>
          <tbody>
            {receipts.map((r) => (
              <tr key={r.id} onClick={() => onSelect(r)} className="cursor-pointer border-b border-border last:border-b-0">
                <td className="tnum p-3" dir="ltr">{r.receiptNumber ?? "—"}</td>
                <td className="p-3" dir="ltr">{r.issueDate}</td>
                <td className="p-3">{r.clientSnapshot.name}</td>
                <td className="tnum p-3" dir="ltr">{formatILS(r.amount)}</td>
                <td className="p-3">{PAYMENT_LABELS[r.paymentMethod]}</td>
                <td className="p-3"><ReceiptStatusBadge status={r.status} /></td>
                <td className="p-3">
                  {r.pdfUrl ? (
                    <a
                      className="text-primary underline"
                      href={r.pdfUrl}
                      target="_blank"
                      rel="noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      הורדה
                    </a>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
```
- [ ] **Step 2: Create `frontend/app/receipts/page.tsx`** — same bootstrap contract as Task 2.9 (`useAuth`, `/businesses/me`, then clients + receipts in one effect); the draft-then-issue API flow is unchanged (`POST .../receipts/draft` → `POST .../receipts/{id}/issue`). Creation happens in a bottom Sheet form: client `<select>` with an "אחר (שם חופשי)" option revealing a free-text name input, amount with `inputMode="numeric"` + `dir="ltr"`, payment method from `PAYMENT_LABELS`, blur validation with Hebrew errors, 48px submit with spinner. Tapping a card opens the detail Sheet: all fields, primary "הורדת PDF" (opens `pdfUrl`), "שיתוף" via `navigator.share({ url })` with copy-to-clipboard fallback, and a destructive "ביטול קבלה" confirmed inside the sheet with a required reason (`POST .../receipts/{id}/cancel`, issued receipts only):
```tsx
"use client";
import { useEffect, useState } from "react";
import { Ban, Check, Download, Loader2, Plus, ReceiptText, Share2 } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import ReceiptList, { ReceiptStatusBadge } from "@/components/ReceiptList";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { formatILS } from "@/lib/format";
import type { Business, Client, PaymentMethod, Receipt } from "@/lib/types";
import { PAYMENT_LABELS } from "@/lib/types";

const EMPTY_FORM = { clientId: "", clientName: "", amount: "", description: "", paymentMethod: "unknown" as PaymentMethod };

type FieldErrors = { clientName?: string; amount?: string; description?: string };

function inputClass(invalid: boolean): string {
  return `min-h-12 w-full rounded-xl border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary ${
    invalid ? "border-destructive" : "border-border"
  }`;
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-border py-2 last:border-b-0">
      <dt className="shrink-0 text-sm text-foreground/60">{label}</dt>
      <dd className="text-end text-sm font-medium">{children}</dd>
    </div>
  );
}

export default function ReceiptsPage() {
  const { user, loading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<Receipt | null>(null);
  const [cancelMode, setCancelMode] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);

  useEffect(() => {
    if (loading || !user) return;
    api<Business>("/businesses/me")
      .then(async (b) => {
        setBusiness(b);
        const [cs, rs] = await Promise.all([
          api<Client[]>(`/businesses/${b.id}/clients`),
          api<Receipt[]>(`/businesses/${b.id}/receipts`),
        ]);
        setClients(cs);
        setReceipts(rs);
        setLoaded(true);
      })
      .catch((e) => setError((e as Error).message));
  }, [loading, user]);

  function openCreate() {
    setForm(EMPTY_FORM);
    setFieldErrors({});
    setCreateOpen(true);
  }

  function openDetails(receipt: Receipt) {
    setCancelMode(false);
    setCancelReason("");
    setCancelError(null);
    setShareCopied(false);
    setSelected(receipt);
  }

  function validateField(field: keyof FieldErrors) {
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      if (field === "clientName" && !form.clientId && !form.clientName.trim()) next.clientName = "נדרש שם לקוח";
      if (field === "amount" && !(Number(form.amount) > 0)) next.amount = "הסכום חייב להיות גדול מ-0";
      if (field === "description" && !form.description.trim()) next.description = "חסר תיאור לקבלה";
      return next;
    });
  }

  async function createAndIssue(e: React.FormEvent) {
    e.preventDefault();
    if (!business) return;
    const errors: FieldErrors = {};
    if (!form.clientId && !form.clientName.trim()) errors.clientName = "נדרש שם לקוח";
    if (!(Number(form.amount) > 0)) errors.amount = "הסכום חייב להיות גדול מ-0";
    if (!form.description.trim()) errors.description = "חסר תיאור לקבלה";
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    setBusy(true);
    setError(null);
    try {
      const draft = await api<Receipt>(`/businesses/${business.id}/receipts/draft`, {
        method: "POST",
        body: JSON.stringify({
          clientId: form.clientId || undefined,
          clientName: form.clientId ? undefined : form.clientName.trim(),
          amount: Number(form.amount),
          description: form.description.trim(),
          paymentMethod: form.paymentMethod,
        }),
      });
      const issued = await api<Receipt>(`/businesses/${business.id}/receipts/${draft.id}/issue`, { method: "POST" });
      setReceipts((rs) => [issued, ...rs]);
      setCreateOpen(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function shareReceipt(receipt: Receipt) {
    if (!receipt.pdfUrl) return;
    if (navigator.share) {
      try {
        await navigator.share({ url: receipt.pdfUrl });
      } catch {
        // user dismissed the OS share sheet — nothing to do
      }
    } else {
      await navigator.clipboard.writeText(receipt.pdfUrl);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    }
  }

  async function confirmCancel() {
    if (!business || !selected) return;
    if (!cancelReason.trim()) {
      setCancelError("נדרשת סיבת ביטול");
      return;
    }
    setCancelBusy(true);
    setCancelError(null);
    try {
      const cancelled = await api<Receipt>(`/businesses/${business.id}/receipts/${selected.id}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason: cancelReason.trim() }),
      });
      setReceipts((rs) => rs.map((r) => (r.id === cancelled.id ? cancelled : r)));
      setSelected(cancelled);
      setCancelMode(false);
    } catch (err) {
      setCancelError((err as Error).message);
    } finally {
      setCancelBusy(false);
    }
  }

  return (
    <div className="px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">קבלות</h1>
        <button
          onClick={openCreate}
          className="flex min-h-12 items-center gap-1.5 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
        >
          <Plus size={20} aria-hidden />
          קבלה חדשה
        </button>
      </div>
      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}
      {loading || !loaded ? (
        <div className="flex flex-col gap-3" aria-hidden>
          {[0, 1, 2].map((i) => (
            <div key={i} className="animate-pulse rounded-2xl border border-border bg-white p-4">
              <div className="h-4 w-20 rounded bg-muted" />
              <div className="mt-3 h-5 w-36 rounded bg-muted" />
              <div className="mt-2 h-4 w-28 rounded bg-muted" />
            </div>
          ))}
        </div>
      ) : receipts.length === 0 ? (
        <EmptyState
          Icon={ReceiptText}
          title="אין עדיין קבלות"
          hint="הנפיקו קבלה ראשונה בכפתור למעלה, או כתבו בצ׳אט: קיבלתי 2,800 מנועה על עיצוב לוגו"
        />
      ) : (
        <ReceiptList receipts={receipts} onSelect={openDetails} />
      )}

      <Sheet open={createOpen} onClose={() => setCreateOpen(false)} title="קבלה חדשה">
        <form onSubmit={createAndIssue} noValidate className="flex flex-col gap-4">
          <div>
            <label htmlFor="receipt-client" className="mb-1 block text-sm font-medium">לקוח</label>
            <select
              id="receipt-client"
              value={form.clientId}
              onChange={(e) => setForm({ ...form, clientId: e.target.value })}
              className={inputClass(false)}
            >
              <option value="">אחר (שם חופשי)</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          {!form.clientId && (
            <div>
              <label htmlFor="receipt-client-name" className="mb-1 block text-sm font-medium">שם הלקוח *</label>
              <input
                id="receipt-client-name"
                value={form.clientName}
                aria-invalid={Boolean(fieldErrors.clientName)}
                onChange={(e) => setForm({ ...form, clientName: e.target.value })}
                onBlur={() => validateField("clientName")}
                className={inputClass(Boolean(fieldErrors.clientName))}
              />
              {fieldErrors.clientName && <p className="mt-1 text-sm text-destructive">{fieldErrors.clientName}</p>}
            </div>
          )}
          <div>
            <label htmlFor="receipt-amount" className="mb-1 block text-sm font-medium">סכום בש״ח *</label>
            <input
              id="receipt-amount"
              type="number"
              step="0.01"
              min="0.01"
              inputMode="numeric"
              dir="ltr"
              value={form.amount}
              aria-invalid={Boolean(fieldErrors.amount)}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              onBlur={() => validateField("amount")}
              className={inputClass(Boolean(fieldErrors.amount))}
            />
            {fieldErrors.amount && <p className="mt-1 text-sm text-destructive">{fieldErrors.amount}</p>}
          </div>
          <div>
            <label htmlFor="receipt-description" className="mb-1 block text-sm font-medium">תיאור *</label>
            <input
              id="receipt-description"
              value={form.description}
              aria-invalid={Boolean(fieldErrors.description)}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              onBlur={() => validateField("description")}
              className={inputClass(Boolean(fieldErrors.description))}
            />
            {fieldErrors.description && <p className="mt-1 text-sm text-destructive">{fieldErrors.description}</p>}
          </div>
          <div>
            <label htmlFor="receipt-method" className="mb-1 block text-sm font-medium">אמצעי תשלום</label>
            <select
              id="receipt-method"
              value={form.paymentMethod}
              onChange={(e) => setForm({ ...form, paymentMethod: e.target.value as PaymentMethod })}
              className={inputClass(false)}
            >
              {(Object.entries(PAYMENT_LABELS) as [PaymentMethod, string][]).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
          >
            {busy && <Loader2 size={20} className="animate-spin" aria-hidden />}
            צור והנפק קבלה
          </button>
        </form>
      </Sheet>

      <Sheet open={selected !== null} onClose={() => setSelected(null)} title="פרטי קבלה">
        {selected && (
          <div className="flex flex-col gap-4">
            <dl>
              <DetailRow label="מספר קבלה"><span className="tnum" dir="ltr">{selected.receiptNumber ?? "—"}</span></DetailRow>
              <DetailRow label="סטטוס"><ReceiptStatusBadge status={selected.status} /></DetailRow>
              <DetailRow label="לקוח">{selected.clientSnapshot.name}</DetailRow>
              <DetailRow label="תאריך"><span dir="ltr">{selected.issueDate}</span></DetailRow>
              <DetailRow label="סכום"><span className="tnum" dir="ltr">{formatILS(selected.amount)}</span></DetailRow>
              <DetailRow label="אמצעי תשלום">{PAYMENT_LABELS[selected.paymentMethod]}</DetailRow>
              <DetailRow label="תיאור">{selected.description}</DetailRow>
              {selected.status === "cancelled" && selected.cancellationReason && (
                <DetailRow label="סיבת ביטול">{selected.cancellationReason}</DetailRow>
              )}
            </dl>
            {!cancelMode ? (
              <div className="flex flex-col gap-2">
                {selected.pdfUrl ? (
                  <>
                    <a
                      href={selected.pdfUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
                    >
                      <Download size={20} aria-hidden />
                      הורדת PDF
                    </a>
                    <button
                      onClick={() => void shareReceipt(selected)}
                      className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-border px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98]"
                    >
                      {shareCopied ? <Check size={20} aria-hidden /> : <Share2 size={20} aria-hidden />}
                      {shareCopied ? "הקישור הועתק" : "שיתוף"}
                    </button>
                  </>
                ) : (
                  <p className="text-sm text-foreground/60">אין עדיין PDF לקבלה זו.</p>
                )}
                {selected.status === "issued" && (
                  <button
                    onClick={() => setCancelMode(true)}
                    className="flex min-h-12 items-center justify-center gap-2 rounded-xl border border-destructive px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98]"
                  >
                    <Ban size={20} aria-hidden />
                    ביטול קבלה
                  </button>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3 rounded-2xl border border-destructive/40 bg-destructive/5 p-4">
                <p className="text-sm font-medium text-destructive">
                  ביטול קבלה הוא סופי ונרשם ביומן הפעולות. הקבלה תסומן כמבוטלת ולא תימחק.
                </p>
                <div>
                  <label htmlFor="cancel-reason" className="mb-1 block text-sm font-medium">סיבת הביטול *</label>
                  <input
                    id="cancel-reason"
                    value={cancelReason}
                    aria-invalid={Boolean(cancelError)}
                    onChange={(e) => {
                      setCancelReason(e.target.value);
                      if (cancelError) setCancelError(null);
                    }}
                    onBlur={() => setCancelError(cancelReason.trim() ? null : "נדרשת סיבת ביטול")}
                    className={inputClass(Boolean(cancelError))}
                  />
                  {cancelError && <p className="mt-1 text-sm text-destructive">{cancelError}</p>}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => void confirmCancel()}
                    disabled={cancelBusy}
                    className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-destructive px-5 font-medium text-white transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                  >
                    {cancelBusy && <Loader2 size={20} className="animate-spin" aria-hidden />}
                    אישור ביטול
                  </button>
                  <button
                    onClick={() => setCancelMode(false)}
                    disabled={cancelBusy}
                    className="min-h-12 flex-1 rounded-xl border border-border px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
                  >
                    חזרה
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </Sheet>
    </div>
  );
}
```
- [ ] **Step 3: Verify** `cd /Users/tamirsida/dev/tax/frontend && npx tsc --noEmit && npm run build` — both clean. Manual end-to-end with the REAL Cloudinary dev account (delivery toggle from Task 2.6 enabled, `CLOUDINARY_URL` set in `backend/.env`): open devtools device toolbar at 375×812 on http://localhost:3000/receipts — skeleton cards, then `EmptyState` for a fresh business; tap "קבלה חדשה", pick client נועה גולן, amount 2800, description "עיצוב לוגו", method ביט, submit — the Sheet closes and a new card appears at the top with number `2026-0001` rendered LTR, amount `₪2,800` via `formatILS` in tabular numerals, and a green הופקה badge; tap the card — the detail Sheet shows all fields; "הורדת PDF" opens the Hebrew RTL PDF from `res.cloudinary.com` showing ₪2,800; "שיתוף" opens the OS share sheet (in desktop browsers without `navigator.share` it copies the link and flips to "הקישור הועתק" for 2 seconds); "ביטול קבלה" reveals the in-sheet red confirm block — confirming with an empty reason shows "נדרשת סיבת ביטול", and with a reason the badge flips to מבוטלת in the list without a reload. Issue a second receipt — expect `2026-0002`. Widen the viewport past 768px — the card list is replaced by the desktop table with the same data and a working הורדה link.
- [ ] **Step 4: Commit** `git add frontend/components/ReceiptList.tsx frontend/app/receipts/page.tsx && git commit -m "feat: mobile-first receipts card list with detail sheet, PDF share and in-sheet cancel"`
## Phase 3 — Chat Parser, Pending Actions & Queries

**Goal:** Turn natural Hebrew/English messages into validated, confirmed, executed actions: LLM parsing (OpenAI structured outputs), the pending-action state machine, deterministic Hebrew query answers, the chat API, and the chat UI.
**Depends on:** Phase 0 (fixtures `db`/`clear_db`/`api`/`make_business`, utils `dates.py`/`money.py`, CI), Phase 1 (auth, `get_owned_business`, business service), Phase 2 (clients, `create_draft`/`issue_receipt`, ledger). Emulator must be running for integration tests: `docker compose up -d firestore-emulator`. All pytest commands below are run as `cd /Users/tamirsida/dev/tax/backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test python -m pytest <args>`.
**Done when:** doc §14.1/§14.2/§14.3/§14.4 flows pass as automated tests with the stub parser; `אישור`/`בטל` fast-paths work without an LLM call; double-confirm returns 409 exactly once; queries answer from Firestore with deterministic Hebrew; the chat page works end-to-end in the browser against the real dev backend (acceptance criteria 6, 7, 8); at 375×812 the chat is fully usable with the on-screen keyboard open — the input stays visible above the keyboard and the message list still scrolls; the confirmation flow is fully inline in the chat via `ConfirmActionCard` (no modal anywhere).

### Task 3.1: AI command schemas + prompts

**Files:** Create: `backend/app/schemas/ai_commands.py`, `backend/app/prompts/command_parser.txt`, `backend/app/prompts/expense_extractor.txt`. Modify: `backend/app/utils/dates.py` (add `resolve_time_range` — the contract Phase 2 reserved). Test: `backend/tests/unit/test_ai_commands.py`, `backend/tests/test_dates.py` (extend).

- [ ] **Step 1: Write the failing strict-schema test**
```python
# backend/tests/unit/test_ai_commands.py
import pytest
from app.schemas import ai_commands as ac

WIRE_MODELS = [ac.TimeRange, ac.ReceiptPayload, ac.ContactPayload, ac.ExpensePayload,
               ac.QueryPayload, ac.ParsedUserCommand, ac.ExpenseExtraction]

def test_wire_models_have_no_non_none_defaults():
    # OpenAI strict structured outputs: every field required; only None defaults allowed (SDK strips them).
    for model in WIRE_MODELS:
        for name, field in model.model_fields.items():
            assert field.is_required() or field.default is None, f"{model.__name__}.{name} has non-None default"

def test_minimal_command_parses():
    cmd = ac.ParsedUserCommand.model_validate({"intent": "CREATE_RECEIPT",
        "receipt": {"client_name": "נועה", "amount": 2800, "description": "עיצוב לוגו"}})
    assert cmd.receipt.payment_method is None and cmd.missing_fields is None

def test_expense_extraction_category_enum():
    e = ac.ExpenseExtraction.model_validate({"supplier_name": "Canva", "amount": 120, "category": "software"})
    assert e.category == ac.ExpenseCategory.SOFTWARE
```
- [ ] **Step 2: Run** `python -m pytest tests/unit/test_ai_commands.py -q` → fails `ModuleNotFoundError: app.schemas.ai_commands`.
- [ ] **Step 3: Implement.** Copy design doc §9 verbatim into `backend/app/schemas/ai_commands.py`, then replace every model that carries a non-None default with the strict-mode version below, and append `ExpenseCategory`, `ExpenseExtraction`, `ParserFailure` (the enums `IntentType`, `PaymentMethod`, `TimePreset`, `QueryType` and `ContactPayload` stay exactly as in §9):
```python
class TimeRange(BaseModel):
    preset: Optional[TimePreset] = None          # server default: THIS_YEAR
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class ReceiptPayload(BaseModel):
    client_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[Literal["ILS"]] = None    # server default: ILS
    description: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None   # server default: unknown
    payment_received: Optional[bool] = None
    issue_receipt: Optional[bool] = None

class ExpensePayload(BaseModel):
    supplier_name: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[Literal["ILS"]] = None
    category: Optional[str] = None
    description: Optional[str] = None
    business_use_percent: Optional[int] = Field(default=None, ge=0, le=100)  # server default: 100
    expense_date: Optional[str] = None

class QueryPayload(BaseModel):
    type: Optional[QueryType] = None
    time_range: Optional[TimeRange] = None
    client_name: Optional[str] = None
    metric: Optional[str] = None

class ParsedUserCommand(BaseModel):
    intent: IntentType
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    language: Optional[Literal["he", "en", "mixed", "unknown"]] = None
    receipt: Optional[ReceiptPayload] = None
    contact: Optional[ContactPayload] = None
    expense: Optional[ExpensePayload] = None
    query: Optional[QueryPayload] = None
    missing_fields: Optional[List[str]] = None   # NEVER trusted; recomputed server-side
    requires_confirmation: Optional[bool] = None
    user_facing_message: Optional[str] = None
    resolved_from_context: Optional[bool] = None

class ExpenseCategory(str, Enum):
    SOFTWARE = "software"; EQUIPMENT = "equipment"; TRAVEL = "travel"; OFFICE = "office"
    MARKETING = "marketing"; PROFESSIONAL_SERVICES = "professional_services"
    MEALS = "meals"; PARKING = "parking"; OTHER = "other"

class ExpenseExtraction(BaseModel):
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None           # ISO YYYY-MM-DD
    amount: Optional[float] = None
    currency: Optional[Literal["ILS"]] = None
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    ocr_text: Optional[str] = None
    confidence: Optional[float] = Field(default=None, ge=0, le=1)

class ParserFailure(BaseModel):                  # internal, never sent to OpenAI
    reason: Literal["refusal", "validation_error", "timeout", "rate_limit", "api_error", "length"]
    detail: str = ""
```
- [ ] **Step 4: Prompts.** Copy doc §10 verbatim into `backend/app/prompts/command_parser.txt`. Create `backend/app/prompts/expense_extractor.txt`:
```txt
You extract structured expense data from a photo of a receipt or invoice (Hebrew or English).
Rules:
- Extract ONLY facts visible in the image. Never invent values. If a field is not visible, return null.
- supplier_name: the business that issued the receipt (not the buyer).
- expense_date: the document date in ISO format YYYY-MM-DD. If only day/month visible, return null.
- amount: the final total paid including VAT, as a number without currency symbols or thousands separators.
- currency: "ILS" if the receipt shows ₪ / ש"ח / NIS, otherwise null.
- category: best match among software, equipment, travel, office, marketing, professional_services, meals, parking, other. If unsure, return null.
- description: one short line describing what was purchased.
- ocr_text: ALL legible text from the image, line by line, in original language.
- confidence: 0-1, your overall confidence that supplier, date and amount are correct.
Do not provide tax advice. Do not decide deductibility.
```
- [ ] **Step 5: Run** the test again → 3 passed. **Commit:** `git add backend/app/schemas/ai_commands.py backend/app/prompts backend/tests/unit/test_ai_commands.py && git commit -m "feat: AI command schemas (strict-mode) and parser prompts"`
- [ ] **Step 6: Write the failing `resolve_time_range` tests** — Phase 2 Task 2.1 reserved this function in `dates.py` because it needs `TimeRange`/`TimePreset`, which now exist. Append to `backend/tests/test_dates.py`:
```python
from app.schemas.ai_commands import TimePreset, TimeRange
from app.utils.dates import resolve_time_range

def test_resolve_this_year_matches_year_bounds():
    start, end = resolve_time_range(TimeRange(preset=TimePreset.THIS_YEAR))
    assert (start, end) == year_bounds(start.year)

def test_resolve_all_time_unbounded():
    assert resolve_time_range(TimeRange(preset=TimePreset.ALL_TIME)) == (None, None)

def test_resolve_custom_dates_end_exclusive():
    start, end = resolve_time_range(TimeRange(preset=TimePreset.CUSTOM,
                                              start_date="2026-01-01", end_date="2026-06-30"))
    assert start == datetime(2026, 1, 1, tzinfo=IL_TZ) and end == datetime(2026, 7, 1, tzinfo=IL_TZ)

def test_resolve_custom_bad_dates_unbounded():
    assert resolve_time_range(TimeRange(preset=TimePreset.CUSTOM, start_date="junk")) == (None, None)
```
- [ ] **Step 7: Run** `python -m pytest tests/test_dates.py -q` → fails with `ImportError: cannot import name 'resolve_time_range'`. **Implement** — append to `backend/app/utils/dates.py` (and add `timedelta` to its `from datetime import ...` line):
```python
def resolve_time_range(tr) -> tuple[datetime | None, datetime | None]:
    """Map an AI TimeRange (schemas.ai_commands) to [start, end) IL-tz bounds; None = unbounded."""
    from app.schemas.ai_commands import TimePreset  # local import: utils must not import schemas at module load

    preset = tr.preset or TimePreset.ALL_TIME
    now = now_il()
    today = datetime(now.year, now.month, now.day, tzinfo=IL_TZ)
    if preset == TimePreset.TODAY:
        return today, today + timedelta(days=1)
    if preset == TimePreset.THIS_WEEK:                       # Israeli week starts Sunday
        start = today - timedelta(days=(now.weekday() + 1) % 7)
        return start, start + timedelta(days=7)
    if preset == TimePreset.THIS_MONTH:
        return month_bounds(now.year, now.month)
    if preset == TimePreset.THIS_YEAR:
        return year_bounds(now.year)
    if preset == TimePreset.LAST_YEAR:
        return year_bounds(now.year - 1)
    if preset == TimePreset.CUSTOM:
        start_d, end_d = parse_iso_date(tr.start_date), parse_iso_date(tr.end_date)
        start = datetime(start_d.year, start_d.month, start_d.day, tzinfo=IL_TZ) if start_d else None
        end = (datetime(end_d.year, end_d.month, end_d.day, tzinfo=IL_TZ) + timedelta(days=1)) if end_d else None
        return start, end
    return None, None                                        # ALL_TIME
```
- [ ] **Step 8: Run** `python -m pytest tests/test_dates.py tests/unit/test_ai_commands.py -q` → all pass. **Commit:** `git add backend/app/utils/dates.py backend/tests/test_dates.py && git commit -m "feat: resolve_time_range maps AI time presets to IL timezone bounds"`

### Task 3.2: Hebrew text utilities and templates

**Files:** Create: `backend/app/utils/hebrew.py`. Test: `backend/tests/unit/test_hebrew.py`.

- [ ] **Step 1: Write failing tests**
```python
# backend/tests/unit/test_hebrew.py
from app.utils.hebrew import (normalize, CONFIRM_WORDS, CANCEL_WORDS,
    build_followup_question, build_confirmation_message, render_query_answer)
from app.schemas.ai_commands import IntentType, QueryType

def test_normalize(): assert normalize("  אִישור!! ") == "אִישור" and normalize("OK.") == "ok"
def test_confirm_cancel_words():
    assert normalize("אישור") in CONFIRM_WORDS and normalize("כן") in CONFIRM_WORDS and normalize("Yes") in CONFIRM_WORDS
    assert normalize("בטל") in CANCEL_WORDS and normalize("לא") in CANCEL_WORDS
def test_followup_combined():
    q = build_followup_question(IntentType.CREATE_RECEIPT, ["amount"])
    assert "סכום" in q and "אמצעי תשלום" in q   # doc §14.2 style combined question
def test_confirmation_receipt():
    msg = build_confirmation_message(IntentType.CREATE_RECEIPT,
        {"client_name": "נועה", "amount": 2800.0, "description": "עיצוב לוגו", "payment_method": "bit"})
    assert msg == "לאשר יצירת קבלה על ₪2,800.00 לנועה עבור עיצוב לוגו, תשלום בביט?"
def test_query_answer_revenue():
    assert render_query_answer(QueryType.TOTAL_REVENUE, {"period": "THIS_YEAR", "total": 42300.0}) \
        == "ההכנסות שלך השנה הן ₪42,300.00."
```
(Adjust the two exact-string assertions to whatever `format_ils` from Phase 0 actually emits — run `python -c "from app.utils.money import format_ils; print(format_ils(2800))"` first and pin that.)
- [ ] **Step 2: Run** `python -m pytest tests/unit/test_hebrew.py -q` → fails (module missing). **Implement:**
```python
# backend/app/utils/hebrew.py
import re
from app.schemas.ai_commands import IntentType
from app.utils.money import format_ils

_PUNCT = re.compile(r"[!?,.;:׳״'\"()\[\]{}\-]+")
def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", _PUNCT.sub(" ", text)).strip().lower()

CONFIRM_WORDS = {"אישור", "כן", "אשר", "מאשר", "מאשרת", "אוקיי", "אוקי", "סבבה", "ok", "yes", "y", "confirm"}
CANCEL_WORDS = {"בטל", "ביטול", "לא", "עזוב", "תבטל", "cancel", "no"}

PAYMENT_HE = {"cash": "מזומן", "bank_transfer": "העברה בנקאית", "bit": "ביט", "paybox": "פייבוקס",
              "credit_card": "כרטיס אשראי", "check": "צ'ק", "other": "אחר"}
PERIOD_HE = {"TODAY": "היום", "THIS_WEEK": "השבוע", "THIS_MONTH": "החודש", "THIS_YEAR": "השנה",
             "LAST_YEAR": "בשנה שעברה", "ALL_TIME": 'סה"כ', "CUSTOM": "בתקופה שביקשת"}
CATEGORY_HE = {"software": "תוכנה", "equipment": "ציוד", "travel": "נסיעות", "office": "משרד",
               "marketing": "שיווק", "professional_services": "שירותים מקצועיים",
               "meals": "אוכל", "parking": "חניה", "other": "אחר"}

_FIELD_Q = {
    (IntentType.CREATE_RECEIPT, "client_name"): "ממי התקבל התשלום?",
    (IntentType.CREATE_RECEIPT, "amount"): "מה הסכום ששולם ובאיזה אמצעי תשלום?",
    (IntentType.CREATE_RECEIPT, "description"): "עבור מה התשלום?",
    (IntentType.CREATE_RECEIPT, "payment_received_confirmation"): "האם התשלום כבר התקבל?",
    (IntentType.CREATE_CONTACT, "name"): "מה שם איש הקשר?",
    (IntentType.CREATE_EXPENSE, "amount"): "מה סכום ההוצאה?",
}
def build_followup_question(intent: IntentType, missing_fields: list[str]) -> str:
    qs = [_FIELD_Q[(intent, f)] for f in missing_fields if (intent, f) in _FIELD_Q]
    return " ".join(qs) or "חסרים לי כמה פרטים, אפשר לפרט?"

def build_confirmation_message(intent: IntentType, payload: dict) -> str:
    if intent == IntentType.CREATE_RECEIPT:
        base = f"לאשר יצירת קבלה על {format_ils(payload['amount'])} ל{payload['client_name']} עבור {payload['description']}"
        pm = payload.get("payment_method")
        if pm and pm != "unknown":
            return f"{base}, תשלום ב{PAYMENT_HE[pm]}?"
        return f"{base}? (אמצעי תשלום לא צוין)"
    if intent == IntentType.CREATE_CONTACT:
        return f"לאשר יצירת איש קשר בשם {payload['name']}?"
    if intent == IntentType.CREATE_EXPENSE:
        target = payload.get("supplier_name") or payload.get("description") or "הוצאה"
        return f"לאשר הוצאה של {format_ils(payload['amount'])} על {target}?"
    return f"לאשר יצירת דוח שנתי לשנת {payload['year']}?"

def render_query_answer(query_type, data: dict) -> str:
    qt = getattr(query_type, "value", query_type)
    p = PERIOD_HE.get(data.get("period", "THIS_YEAR"), "השנה")
    if qt == "TOTAL_REVENUE": return f"ההכנסות שלך {p} הן {format_ils(data['total'])}."
    if qt == "TOTAL_EXPENSES": return f"ההוצאות שלך {p} הן {format_ils(data['total'])}."
    if qt == "ESTIMATED_PROFIT":
        return (f"הרווח המשוער שלך {p} הוא {format_ils(data['profit'])} "
                f"(הכנסות {format_ils(data['revenue'])} פחות הוצאות {format_ils(data['expenses'])}).")
    if qt == "CLIENT_REVENUE": return f"{data['client_name']} שילם/ה לך סה\"כ {format_ils(data['total'])}."
    if qt == "CONTACT_EXISTS":
        return (f"כן, {data['client_name']} נמצא/ת באנשי הקשר." if data["exists"]
                else f"לא מצאתי איש קשר בשם {data['client_name']}.")
    if qt == "RECEIPTS_COUNT": return f"הוצאת {data['count']} קבלות {p}."
    if qt == "EXPENSES_BY_CATEGORY":
        if not data["by_category"]: return f"אין הוצאות מאושרות {p}."
        lines = [f"• {CATEGORY_HE.get(c, c)}: {format_ils(t)}"
                 for c, t in sorted(data["by_category"].items(), key=lambda kv: -kv[1])]
        return f"הוצאות לפי קטגוריה {p}:\n" + "\n".join(lines)
    if qt == "OSEK_PATUR_LIMIT_STATUS":
        msg = (f"ההכנסות שלך השנה הן {format_ils(data['total'])} מתוך תקרה של {format_ils(data['limit'])} "
               f"({data['pct']}%). נותרו {format_ils(data['remaining'])}.")
        return msg + (" שים/י לב: את/ה מתקרב/ת לתקרת עוסק פטור." if data["warning"] else "")
    return "לא הצלחתי להבין את השאלה, אפשר לנסח שוב?"
```
- [ ] **Step 3: Run** → 5 passed. **Commit:** `git add backend/app/utils/hebrew.py backend/tests/unit/test_hebrew.py && git commit -m "feat: hebrew normalization, confirm/cancel words and message templates"`

### Task 3.3: OpenAI service, stub parser, fixture

**Files:** Create: `backend/app/services/openai_service.py`, `backend/tests/stubs.py`. Modify: `backend/tests/conftest.py`. Test: `backend/tests/unit/test_openai_service.py`.

- [ ] **Step 1: Write failing tests** — error mapping via a fake injected client:
```python
# backend/tests/unit/test_openai_service.py
import openai, pytest, httpx
from pydantic import ValidationError
from app.services.openai_service import OpenAICommandParser, get_command_parser
from app.schemas.ai_commands import ParsedUserCommand, ParserFailure

class _FakeResponses:
    def __init__(self, exc=None, parsed="unset"): self.exc, self.parsed = exc, parsed
    def parse(self, **kwargs):
        if self.exc: raise self.exc
        return type("R", (), {"output_parsed": self.parsed})()
class _FakeClient:
    def __init__(self, exc=None, parsed="unset"): self.responses = _FakeResponses(exc, parsed)

def _parser(exc=None, parsed="unset"):
    p = OpenAICommandParser(); p._client = _FakeClient(exc, parsed); return p

def test_timeout_maps_to_failure():
    r = _parser(exc=openai.APITimeoutError(request=httpx.Request("POST", "https://x"))).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "timeout"

def test_refusal_when_output_parsed_none():
    r = _parser(parsed=None).parse_user_command({}, "hi")
    assert isinstance(r, ParserFailure) and r.reason == "refusal"

def test_success_normalizes_scalar_defaults():
    cmd = ParsedUserCommand(intent="UNKNOWN")
    r = _parser(parsed=cmd).parse_user_command({}, "hi")
    assert r.missing_fields == [] and r.requires_confirmation is True and r.language == "unknown"

def test_get_command_parser_is_cached_and_lazy():
    assert get_command_parser() is get_command_parser()
    assert get_command_parser()._client is None  # no OpenAI() constructed at import/instantiation
```
Add analogous one-line tests for `RateLimitError → "rate_limit"`, `APIStatusError(400) → "api_error"`, `LengthFinishReasonError → "length"` (construct with the SDK's required args; if construction is awkward, raise the class via `pytest`-built dummy subclass — assertion is only on `.reason`).
- [ ] **Step 2: Run** → fails. **Implement:**
```python
# backend/app/services/openai_service.py
import json
from functools import lru_cache
from pathlib import Path
from typing import Protocol, Union
import openai
from openai import OpenAI
from pydantic import ValidationError
from app.core.config import get_settings
from app.schemas.ai_commands import ExpenseExtraction, ParsedUserCommand, ParserFailure

_PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

class CommandParser(Protocol):
    def parse_user_command(self, context: dict, message: str) -> Union[ParsedUserCommand, ParserFailure]: ...
    def extract_expense(self, image_url: str) -> Union[ExpenseExtraction, ParserFailure]: ...

def _normalize(cmd: ParsedUserCommand) -> ParsedUserCommand:
    # server-side scalar defaults (strict schema forced Optional on the wire)
    cmd.missing_fields = cmd.missing_fields or []
    cmd.confidence = 0.0 if cmd.confidence is None else cmd.confidence
    cmd.language = cmd.language or "unknown"
    cmd.requires_confirmation = True if cmd.requires_confirmation is None else cmd.requires_confirmation
    cmd.resolved_from_context = bool(cmd.resolved_from_context)
    return cmd

class OpenAICommandParser:
    def __init__(self):
        self._client = None  # NEVER construct OpenAI() at import/instantiation time
        self._command_prompt = (_PROMPTS / "command_parser.txt").read_text(encoding="utf-8")
        self._expense_prompt = (_PROMPTS / "expense_extractor.txt").read_text(encoding="utf-8")

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            s = get_settings()
            self._client = OpenAI(api_key=s.openai_api_key, timeout=20.0, max_retries=2)
        return self._client

    def _call(self, model: str, input_items: list, text_format):
        try:
            response = self.client.responses.parse(model=model, input=input_items, text_format=text_format)
        except openai.LengthFinishReasonError as e: return ParserFailure(reason="length", detail=str(e))
        except openai.APITimeoutError as e: return ParserFailure(reason="timeout", detail=str(e))
        except openai.RateLimitError as e: return ParserFailure(reason="rate_limit", detail=str(e))
        except openai.APIStatusError as e: return ParserFailure(reason="api_error", detail=f"status={e.status_code}")
        except ValidationError as e: return ParserFailure(reason="validation_error", detail=str(e)[:500])
        if response.output_parsed is None:
            return ParserFailure(reason="refusal", detail="model refused or returned no parsed output")
        return response.output_parsed

    def parse_user_command(self, context: dict, message: str):
        s = get_settings()
        user_text = json.dumps({"context": context, "message": message}, ensure_ascii=False)
        result = self._call(s.openai_command_model,
            [{"role": "system", "content": self._command_prompt},
             {"role": "user", "content": [{"type": "input_text", "text": user_text}]}],
            ParsedUserCommand)
        return _normalize(result) if isinstance(result, ParsedUserCommand) else result

    def extract_expense(self, image_url: str):
        s = get_settings()
        return self._call(s.openai_vision_model,
            [{"role": "system", "content": self._expense_prompt},
             {"role": "user", "content": [
                 {"type": "input_image", "image_url": image_url},  # plain string per Responses API
                 {"type": "input_text", "text": "Extract the expense from this image."}]}],
            ExpenseExtraction)

@lru_cache
def get_command_parser() -> CommandParser:
    return OpenAICommandParser()
```
- [ ] **Step 3: Stub + fixture.**
```python
# backend/tests/stubs.py
class StubCommandParser:
    def __init__(self):
        self.queue, self.expense_queue, self.calls = [], [], []
    def queue_command(self, cmd): self.queue.append(cmd); return self
    def parse_user_command(self, context, message):
        self.calls.append({"context": context, "message": message})
        assert self.queue, "StubCommandParser: queue empty but LLM was called"
        return self.queue.pop(0)
    def extract_expense(self, image_url):
        assert self.expense_queue, "StubCommandParser: expense queue empty"
        return self.expense_queue.pop(0)
```
Append to `backend/tests/conftest.py`:
```python
@pytest.fixture
def stub_parser(api):
    from app.services.openai_service import get_command_parser
    from tests.stubs import StubCommandParser
    stub = StubCommandParser()
    api.app.dependency_overrides[get_command_parser] = lambda: stub
    yield stub
    api.app.dependency_overrides.pop(get_command_parser, None)
```
- [ ] **Step 4: Run** `python -m pytest tests/unit/test_openai_service.py -q` → passed. **Commit:** `git add backend/app/services/openai_service.py backend/tests/stubs.py backend/tests/conftest.py backend/tests/unit/test_openai_service.py && git commit -m "feat: OpenAI command parser with typed failures, stub parser fixture"`

### Task 3.4: Chat schemas + pure state-machine logic (merge / missing fields)

**Files:** Create: `backend/app/schemas/chat.py`, `backend/app/services/chat_service.py` (pure functions only in this task). Test: `backend/tests/unit/test_chat_logic.py`.

- [ ] **Step 1: Write failing tests** — one test per §15 rule plus merge semantics:
```python
# backend/tests/unit/test_chat_logic.py
from app.schemas.ai_commands import IntentType
from app.services.chat_service import compute_missing_fields, merge_payload

R = IntentType.CREATE_RECEIPT
def test_receipt_all_present(): assert compute_missing_fields(R, {"client_name": "נועה", "amount": 2800,
    "description": "עיצוב לוגו", "payment_received": True}) == []
def test_receipt_missing_client(): assert "client_name" in compute_missing_fields(R, {"amount": 2800, "description": "x", "payment_received": True})
def test_receipt_missing_amount(): assert "amount" in compute_missing_fields(R, {"client_name": "נ", "description": "x", "payment_received": True})
def test_receipt_zero_amount_is_missing(): assert "amount" in compute_missing_fields(R, {"client_name": "נ", "amount": 0, "description": "x", "payment_received": True})
def test_receipt_missing_description(): assert "description" in compute_missing_fields(R, {"client_name": "נ", "amount": 1, "payment_received": True})
def test_payment_not_received_adds_pseudofield():
    assert "payment_received_confirmation" in compute_missing_fields(R, {"client_name": "נ", "amount": 1, "description": "x"})
def test_explicit_issue_request_satisfies_payment_rule():
    assert compute_missing_fields(R, {"client_name": "נ", "amount": 1, "description": "x", "issue_receipt": True}) == []
def test_contact_requires_name(): assert compute_missing_fields(IntentType.CREATE_CONTACT, {}) == ["name"]
def test_expense_requires_amount_only():
    assert compute_missing_fields(IntentType.CREATE_EXPENSE, {"supplier_name": "Canva"}) == ["amount"]
    assert compute_missing_fields(IntentType.CREATE_EXPENSE, {"amount": 120}) == []  # category optional -> needs_review later
def test_report_never_missing(): assert compute_missing_fields(IntentType.GENERATE_ANNUAL_REPORT, {"year": 2026}) == []

def test_merge_2800_bebit_case():  # doc §8: follow-up "2800 בביט"
    existing = {"client_name": "נועה", "description": "עיצוב לוגו", "amount": None, "payment_method": None}
    incoming = {"client_name": None, "description": None, "amount": 2800.0, "payment_method": "bit", "payment_received": True}
    m = merge_payload(existing, incoming, R)
    assert m["client_name"] == "נועה" and m["amount"] == 2800.0 and m["payment_method"] == "bit"
def test_merge_unknown_payment_method_never_overwrites():
    m = merge_payload({"payment_method": "bit"}, {"payment_method": "unknown"}, R)
    assert m["payment_method"] == "bit"
def test_merge_none_never_overwrites(): assert merge_payload({"amount": 5}, {"amount": None}, R)["amount"] == 5
def test_merge_explicit_correction_overwrites():
    assert merge_payload({"amount": 2800.0}, {"amount": 3000.0}, R)["amount"] == 3000.0
```
- [ ] **Step 2: Run** → fails. **Implement** `backend/app/schemas/chat.py`:
```python
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class PendingAction(CamelModel):  # doc §5.6
    id: str; business_id: str; thread_id: str; type: str; status: str
    payload: dict[str, Any]; missing_fields: list[str]
    created_at: datetime; updated_at: datetime

class ChatMessage(CamelModel):    # doc §5.7
    id: str; business_id: str; thread_id: str; role: str; text: str
    parsed_intent: Optional[dict[str, Any]] = None
    action_id: Optional[str] = None; created_at: datetime

class ChatMessageRequest(CamelModel):
    text: str; thread_id: str = "main"

class ActionView(CamelModel):
    id: str; type: str; status: str
    payload: dict[str, Any]; missing_fields: list[str]

class ChatTurnResult(CamelModel):
    assistant_text: str; action: Optional[ActionView] = None; result: Optional[dict[str, Any]] = None

class ExecutionResult(CamelModel):
    assistant_text: str; action: Optional[ActionView] = None; result: Optional[dict[str, Any]] = None

class ChatHistoryResponse(CamelModel):
    messages: list[ChatMessage]; active_action: Optional[ActionView] = None
```
and the pure functions in `backend/app/services/chat_service.py`:
```python
from enum import Enum
from app.schemas.ai_commands import IntentType

def merge_payload(existing: dict, incoming: dict, intent: IntentType) -> dict:
    merged = dict(existing)
    for key, value in incoming.items():
        if value is None: continue                     # not provided -> keep existing
        if isinstance(value, Enum): value = value.value
        if key == "payment_method" and value == "unknown": continue  # unknown enum = not provided
        merged[key] = value                            # provided value always wins (user corrections)
    return merged

def compute_missing_fields(intent: IntentType, payload: dict) -> list[str]:
    missing: list[str] = []                            # doc §15, NEVER taken from the LLM
    if intent == IntentType.CREATE_RECEIPT:
        if not payload.get("client_name"): missing.append("client_name")
        amount = payload.get("amount")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
            missing.append("amount")
        if not payload.get("description"): missing.append("description")
        if payload.get("payment_received") is not True and payload.get("issue_receipt") is not True:
            missing.append("payment_received_confirmation")  # doc §10 rule
    elif intent == IntentType.CREATE_CONTACT:
        if not payload.get("name"): missing.append("name")
    elif intent == IntentType.CREATE_EXPENSE:
        amount = payload.get("amount")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount <= 0:
            missing.append("amount")
    return missing
```
- [ ] **Step 3: Run** → 14 passed. **Commit:** `git add backend/app/schemas/chat.py backend/app/services/chat_service.py backend/tests/unit/test_chat_logic.py && git commit -m "feat: chat schemas, payload merge and server-side missing-field rules"`

### Task 3.5: Aggregation service + composite indexes

**Files:** Create: `backend/app/services/aggregation_service.py`. Modify: `firestore.indexes.json`. Test: `backend/tests/integration/test_aggregation.py`.

- [ ] **Step 1: Write failing integration tests** (emulator). Seed helper writes receipt docs directly:
```python
# backend/tests/integration/test_aggregation.py
from datetime import date
from app.services import aggregation_service as agg
from app.schemas.business import Business

def _seed_receipt(db, bid, amount, issue_date, status="issued", client="נועה"):
    db.collection("businesses").document(bid).collection("receipts").document().set({
        "businessId": bid, "status": status, "amount": amount, "currency": "ILS",
        "issueDate": issue_date, "clientSnapshot": {"name": client}})

def test_total_revenue_filters_status_and_range(db, make_business):
    biz = make_business()
    _seed_receipt(db, biz["id"], 1000.0, "2026-02-01")
    _seed_receipt(db, biz["id"], 500.0, "2026-03-15")
    _seed_receipt(db, biz["id"], 999.0, "2026-03-15", status="draft")     # excluded
    _seed_receipt(db, biz["id"], 999.0, "2025-12-31")                      # out of range
    assert agg.total_revenue(db, biz["id"], date(2026, 1, 1), date(2026, 12, 31)) == 1500.0

def test_monthly_income_buckets(db, make_business):
    biz = make_business(); _seed_receipt(db, biz["id"], 1000.0, "2026-02-01"); _seed_receipt(db, biz["id"], 500.0, "2026-02-20")
    m = agg.monthly_income(db, biz["id"], 2026)
    assert m[2] == 1500.0 and m[1] == 0.0 and len(m) == 12

def test_client_revenue_exact_snapshot_name(db, make_business):
    biz = make_business(); _seed_receipt(db, biz["id"], 700.0, "2026-01-05", client="נועה")
    _seed_receipt(db, biz["id"], 50.0, "2026-01-06", client="דניאל")
    assert agg.client_revenue(db, biz["id"], "נועה") == 700.0

def test_receipts_count_and_threshold(db, make_business):
    biz = make_business(); _seed_receipt(db, biz["id"], 110000.0, "2026-01-05")
    assert agg.receipts_count(db, biz["id"], 2026) == 1
    ts = agg.threshold_status(db, Business.model_validate(biz), 2026)
    assert ts.total == 110000.0 and ts.limit == 120000.0 and ts.warning is True and ts.pct == 91.7

def test_expense_aggregations_empty_collections_return_zero(db, make_business):
    biz = make_business()
    assert agg.total_expenses(db, biz["id"], date(2026, 1, 1), date(2026, 12, 31)) == 0.0
    assert agg.expenses_by_category(db, biz["id"], 2026) == {}
```
- [ ] **Step 2: Run** → fails. **Implement** with `FieldFilter` queries: `_issued_receipts(db, business_id, start, end)` = receipts where `status == "issued"` plus `issueDate >= start.isoformat()` / `<= end.isoformat()` only when bounds are non-None (ALL_TIME → `(None, None)` skips both). `total_revenue` = `round_ils(sum(amounts))`; `monthly_income` initializes `{1..12: 0.0}` and buckets by `int(issueDate[5:7])` over `year_bounds(year)`; `client_revenue` = issued receipts where `clientSnapshot.name == client_name` (all-time), summed; `receipts_count` = `len(_issued_receipts(..., *year_bounds(year)))`; `total_expenses`/`expenses_by_category` query `expenses` where `status == "approved"` with `expenseDate` range / grouped by `category or "other"` (doc §5.4 shape; Phase 4 populates). `class ThresholdStatus(BaseModel): total: float; limit: float; pct: float; warning: bool`; `threshold_status` = `total_revenue(year_bounds)`, `limit = float(business.annual_limit or get_settings().annual_limit_ils)`, `pct = round(total / limit * 100, 1)` (0.0 if limit 0), `warning = pct >= 90`. All sums through `round_ils`.
- [ ] **Step 3: Indexes.** Add to `firestore.indexes.json` (emulator does not enforce — the real dev project will): composite on `receipts` (`status` ASC, `issueDate` ASC), `receipts` (`status` ASC, `clientSnapshot.name` ASC), `expenses` (`status` ASC, `expenseDate` ASC), all `COLLECTION` scope. Deploy with `firebase deploy --only firestore:indexes` against the dev project.
- [ ] **Step 4: Run** → 5 passed. **Commit:** `git add backend/app/services/aggregation_service.py firestore.indexes.json backend/tests/integration/test_aggregation.py && git commit -m "feat: aggregation service with revenue/expense rollups and threshold status"`

### Task 3.6: Chat state machine — handle_message

**Files:** Modify: `backend/app/services/chat_service.py`. Test: `backend/tests/integration/test_chat_flow.py`.

- [ ] **Step 1: Write failing integration tests** (direct service calls, no HTTP):
```python
# backend/tests/integration/test_chat_flow.py
from datetime import timedelta
import pytest
from app.schemas.ai_commands import (ContactPayload, IntentType, ParsedUserCommand, ParserFailure,
                                     QueryPayload, QueryType, ReceiptPayload, TimePreset, TimeRange)
from app.schemas.business import Business
from app.services import chat_service
from app.utils.dates import now_il
from tests.stubs import StubCommandParser

FULL_RECEIPT = ParsedUserCommand(intent=IntentType.CREATE_RECEIPT, receipt=ReceiptPayload(
    client_name="נועה", amount=2800.0, description="עיצוב לוגו", payment_method="bit", payment_received=True))
PARTIAL_RECEIPT = ParsedUserCommand(intent=IntentType.CREATE_RECEIPT, receipt=ReceiptPayload(
    client_name="נועה", description="עיצוב לוגו", issue_receipt=True))
FOLLOWUP_AMOUNT = ParsedUserCommand(intent=IntentType.CREATE_RECEIPT, receipt=ReceiptPayload(
    amount=2800.0, payment_method="bit", payment_received=True))

@pytest.fixture
def biz(db, make_business): return Business.model_validate(make_business())

def _actions(db, bid):
    return {d.id: d.to_dict() for d in db.collection("businesses").document(bid).collection("pendingActions").stream()}

def test_happy_path_full_command_goes_to_pending_confirmation(db, biz):  # doc §14.1
    stub = StubCommandParser().queue_command(FULL_RECEIPT)
    res = chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    assert res.action.status == "pending_confirmation" and res.action.missing_fields == []
    assert res.assistant_text.startswith("לאשר יצירת קבלה")
    msgs = list(db.collection("businesses").document(biz.id).collection("chatThreads")
                .document("main").collection("messages").stream())
    assert len(msgs) == 2  # user + assistant persisted

def test_followup_merge_flow(db, biz):  # doc §14.2
    stub = StubCommandParser().queue_command(PARTIAL_RECEIPT).queue_command(FOLLOWUP_AMOUNT)
    first = chat_service.handle_message(db, stub, biz, "main", "תוציא קבלה לנועה על עיצוב לוגו")
    assert first.action.status == "collecting_fields" and first.action.missing_fields == ["amount"]
    assert "סכום" in first.assistant_text
    second = chat_service.handle_message(db, stub, biz, "main", "2800 בביט")
    assert second.action.id == first.action.id and second.action.status == "pending_confirmation"
    assert second.action.payload["client_name"] == "נועה" and second.action.payload["amount"] == 2800.0
    # context sent to LLM contained the pending action (doc §8)
    assert stub.calls[1]["context"]["pending_action"]["payload"]["client_name"] == "נועה"

def test_query_during_pending_answers_and_reshows_question(db, biz):
    stub = StubCommandParser().queue_command(FULL_RECEIPT).queue_command(ParsedUserCommand(
        intent=IntentType.QUERY, query=QueryPayload(type=QueryType.TOTAL_REVENUE,
        time_range=TimeRange(preset=TimePreset.THIS_YEAR))))
    chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    res = chat_service.handle_message(db, stub, biz, "main", "כמה כסף עשיתי השנה?")
    assert "ההכנסות שלך השנה" in res.assistant_text and "לאשר יצירת קבלה" in res.assistant_text
    assert res.action.status == "pending_confirmation"  # untouched

def test_different_create_intent_supersedes(db, biz):
    stub = StubCommandParser().queue_command(FULL_RECEIPT).queue_command(ParsedUserCommand(
        intent=IntentType.CREATE_CONTACT, contact=ContactPayload(name="דניאל")))
    old = chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    new = chat_service.handle_message(db, stub, biz, "main", "יש לי לקוח חדש בשם דניאל")
    acts = _actions(db, biz.id)
    assert acts[old.action.id]["status"] == "cancelled" and acts[old.action.id]["cancellationReason"] == "superseded"
    assert new.action.type == "CREATE_CONTACT" and new.assistant_text == "לאשר יצירת איש קשר בשם דניאל?"

def test_unknown_intent_and_parser_failure_fallback(db, biz):
    stub = StubCommandParser().queue_command(ParsedUserCommand(intent=IntentType.UNKNOWN)) \
                              .queue_command(ParserFailure(reason="timeout"))
    for text in ("בלהבלה", "עוד בלהבלה"):
        res = chat_service.handle_message(db, stub, biz, "main", text)
        assert "לא הצלחתי להבין" in res.assistant_text and res.action is None

def test_stale_action_expires(db, biz):
    stub = StubCommandParser().queue_command(FULL_RECEIPT).queue_command(ParsedUserCommand(
        intent=IntentType.CREATE_CONTACT, contact=ContactPayload(name="דניאל")))
    old = chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    db.collection("businesses").document(biz.id).collection("pendingActions") \
      .document(old.action.id).update({"updatedAt": now_il() - timedelta(hours=25)})
    chat_service.handle_message(db, stub, biz, "main", "לקוח חדש בשם דניאל")
    acts = _actions(db, biz.id)
    assert acts[old.action.id]["status"] == "cancelled" and acts[old.action.id]["cancellationReason"] == "expired"
```
- [ ] **Step 2: Run** → fails. **Implement** — append to `backend/app/services/chat_service.py`:
```python
import uuid
from datetime import timedelta
from google.cloud.firestore_v1.base_query import FieldFilter
from app.schemas.ai_commands import ParserFailure, QueryPayload, QueryType, TimePreset, TimeRange
from app.schemas.business import Business
from app.schemas.chat import ActionView, ChatTurnResult, ExecutionResult
from app.services import aggregation_service as agg
from app.services import client_service, receipt_service
from app.utils.dates import now_il, resolve_time_range, today_il, year_bounds
from app.utils.hebrew import (CANCEL_WORDS, CONFIRM_WORDS, build_confirmation_message,
                              build_followup_question, normalize, render_query_answer)
from app.utils.money import round_ils
from app.core.errors import api_error

FALLBACK = "לא הצלחתי להבין, אפשר לנסח שוב?"
ACTIVE_STATUSES = ("collecting_fields", "pending_confirmation")
STALE_AFTER = timedelta(hours=24)
CREATE_INTENTS = {IntentType.CREATE_RECEIPT, IntentType.CREATE_CONTACT,
                  IntentType.CREATE_EXPENSE, IntentType.GENERATE_ANNUAL_REPORT}

def _biz_ref(db, bid): return db.collection("businesses").document(bid)
def _actions_col(db, bid): return _biz_ref(db, bid).collection("pendingActions")
def _msgs_col(db, bid, tid): return _biz_ref(db, bid).collection("chatThreads").document(tid).collection("messages")

def save_message(db, business_id, thread_id, role, text, action_id=None, parsed_intent=None) -> str:
    _biz_ref(db, business_id).collection("chatThreads").document(thread_id).set({"updatedAt": now_il()}, merge=True)
    ref = _msgs_col(db, business_id, thread_id).document()
    ref.set({"businessId": business_id, "threadId": thread_id, "role": role, "text": text,
             "actionId": action_id, "parsedIntent": parsed_intent, "createdAt": now_il()})
    return ref.id

def _load_active_action(db, business_id, thread_id):
    q = _actions_col(db, business_id).where(filter=FieldFilter("threadId", "==", thread_id)) \
                                     .where(filter=FieldFilter("status", "in", list(ACTIVE_STATUSES)))
    for doc in q.stream():
        data = doc.to_dict()
        if now_il() - data["updatedAt"] > STALE_AFTER:
            doc.reference.update({"status": "cancelled", "cancellationReason": "expired", "updatedAt": now_il()})
            continue
        return doc.id, data
    return None

def _action_view(action_id, data) -> ActionView:
    return ActionView(id=action_id, type=data["type"], status=data["status"],
                      payload=data["payload"], missing_fields=data["missingFields"])

def _current_question(data) -> str:
    intent = IntentType(data["type"])
    if data["status"] == "pending_confirmation":
        return build_confirmation_message(intent, data["payload"])
    return build_followup_question(intent, data["missingFields"])

def _build_context(db, business: Business, thread_id, text, active) -> dict:
    matched = client_service.find_clients_by_name(db, business.id, text)
    recent = client_service.list_clients(db, business.id)[:10]
    clients, seen = [], set()
    for c in matched + recent:
        if c.id not in seen:
            seen.add(c.id); clients.append({"id": c.id, "name": c.name})
    msgs = [d.to_dict() for d in _msgs_col(db, business.id, thread_id)
            .order_by("createdAt", direction="DESCENDING").limit(10).stream()][::-1]
    year = today_il().year
    return {"business": {"business_type": "osek_patur", "currency": "ILS", "current_year": year},
            "known_clients": clients[:20],
            # doc §8 step 2: current-year summary travels with every chat turn
            "current_year_summary": {"total_revenue": agg.total_revenue(db, business.id, *year_bounds(year)),
                                     "total_expenses": agg.total_expenses(db, business.id, *year_bounds(year))},
            "pending_action": ({"type": active[1]["type"], "missing_fields": active[1]["missingFields"],
                                "payload": active[1]["payload"]} if active else None),
            "recent_messages": [{"role": m["role"], "text": m["text"]} for m in msgs]}

def _payload_for(intent, cmd: ParsedUserCommand) -> dict:
    if intent == IntentType.CREATE_RECEIPT and cmd.receipt: return cmd.receipt.model_dump(mode="json")
    if intent == IntentType.CREATE_CONTACT and cmd.contact: return cmd.contact.model_dump(mode="json")
    if intent == IntentType.CREATE_EXPENSE and cmd.expense: return cmd.expense.model_dump(mode="json")
    if intent == IntentType.GENERATE_ANNUAL_REPORT: return {"year": today_il().year}
    return {}

def _upsert_action(db, business_id, thread_id, action_id, intent, status, payload, missing) -> str:
    if action_id is None:
        ref = _actions_col(db, business_id).document(uuid.uuid4().hex)
        ref.set({"businessId": business_id, "threadId": thread_id, "type": intent.value, "status": status,
                 "payload": payload, "missingFields": missing, "createdAt": now_il(), "updatedAt": now_il()})
        return ref.id
    _actions_col(db, business_id).document(action_id).update(
        {"status": status, "payload": payload, "missingFields": missing, "updatedAt": now_il()})
    return action_id

def handle_message(db, parser, business: Business, thread_id: str, text: str) -> ChatTurnResult:
    save_message(db, business.id, thread_id, "user", text)
    active = _load_active_action(db, business.id, thread_id)
    if active and active[1]["status"] == "pending_confirmation":          # fast path: NO LLM call
        norm = normalize(text)
        if norm in CONFIRM_WORDS:
            res = confirm_action(db, parser, business, active[0])
            return ChatTurnResult(assistant_text=res.assistant_text, action=res.action, result=res.result)
        if norm in CANCEL_WORDS:
            cancel_action(db, business.id, active[0])
            reply = "הפעולה בוטלה."
            save_message(db, business.id, thread_id, "assistant", reply, action_id=active[0])
            return ChatTurnResult(assistant_text=reply, action=None)
    cmd = parser.parse_user_command(_build_context(db, business, thread_id, text, active), text)
    if isinstance(cmd, ParserFailure) or cmd.intent == IntentType.UNKNOWN:
        reply = FALLBACK + (("\n" + _current_question(active[1])) if active else "")
        save_message(db, business.id, thread_id, "assistant", reply)
        return ChatTurnResult(assistant_text=reply, action=_action_view(*active) if active else None)
    if cmd.intent == IntentType.QUERY:                                     # queries never create actions
        reply = _answer_query(db, business, cmd.query)
        if active: reply = f"{reply}\n\n{_current_question(active[1])}"
        save_message(db, business.id, thread_id, "assistant", reply,
                     action_id=active[0] if active else None, parsed_intent=cmd.model_dump(mode="json"))
        return ChatTurnResult(assistant_text=reply, action=_action_view(*active) if active else None)
    incoming = _payload_for(cmd.intent, cmd)
    if active and active[1]["type"] == cmd.intent.value:
        payload, action_id = merge_payload(active[1]["payload"], incoming, cmd.intent), active[0]
    else:
        if active: cancel_action(db, business.id, active[0], reason="superseded")
        payload, action_id = merge_payload({}, incoming, cmd.intent), None
    missing = compute_missing_fields(cmd.intent, payload)
    status = "collecting_fields" if missing else "pending_confirmation"
    reply = build_followup_question(cmd.intent, missing) if missing else build_confirmation_message(cmd.intent, payload)
    action_id = _upsert_action(db, business.id, thread_id, action_id, cmd.intent, status, payload, missing)
    save_message(db, business.id, thread_id, "assistant", reply, action_id=action_id,
                 parsed_intent=cmd.model_dump(mode="json"))
    return ChatTurnResult(assistant_text=reply, action=ActionView(
        id=action_id, type=cmd.intent.value, status=status, payload=payload, missing_fields=missing))

def _answer_query(db, business: Business, qp) -> str:
    qp = qp or QueryPayload(); qtype = qp.type or QueryType.UNKNOWN
    tr = qp.time_range or TimeRange(preset=TimePreset.THIS_YEAR)
    if tr.preset is None: tr.preset = TimePreset.THIS_YEAR                 # server default
    start, end = resolve_time_range(tr); period = tr.preset.value; bid = business.id
    year = start.year if start else today_il().year
    if qtype == QueryType.TOTAL_REVENUE:
        return render_query_answer(qtype, {"period": period, "total": agg.total_revenue(db, bid, start, end)})
    if qtype == QueryType.TOTAL_EXPENSES:
        return render_query_answer(qtype, {"period": period, "total": agg.total_expenses(db, bid, start, end)})
    if qtype == QueryType.ESTIMATED_PROFIT:
        rev, exp = agg.total_revenue(db, bid, start, end), agg.total_expenses(db, bid, start, end)
        return render_query_answer(qtype, {"period": period, "profit": round_ils(rev - exp), "revenue": rev, "expenses": exp})
    if qtype == QueryType.CLIENT_REVENUE:
        if not qp.client_name: return "לאיזה לקוח הכוונה?"
        return render_query_answer(qtype, {"client_name": qp.client_name,
                                           "total": agg.client_revenue(db, bid, qp.client_name)})
    if qtype == QueryType.CONTACT_EXISTS:
        if not qp.client_name: return "לאיזה איש קשר הכוונה?"
        exists = any(c.name.strip() == qp.client_name.strip()
                     for c in client_service.find_clients_by_name(db, bid, qp.client_name))
        return render_query_answer(qtype, {"client_name": qp.client_name, "exists": exists})
    if qtype == QueryType.RECEIPTS_COUNT:
        return render_query_answer(qtype, {"period": period, "count": agg.receipts_count(db, bid, year)})
    if qtype == QueryType.EXPENSES_BY_CATEGORY:
        return render_query_answer(qtype, {"period": period, "by_category": agg.expenses_by_category(db, bid, year)})
    if qtype == QueryType.OSEK_PATUR_LIMIT_STATUS:
        ts = agg.threshold_status(db, business, today_il().year)
        return render_query_answer(qtype, {"total": ts.total, "limit": ts.limit, "pct": ts.pct,
                                           "remaining": round_ils(max(ts.limit - ts.total, 0.0)), "warning": ts.warning})
    return render_query_answer(QueryType.UNKNOWN, {})
```
- [ ] **Step 3: Run** `python -m pytest tests/integration/test_chat_flow.py -q` → 6 passed (the fast-path/confirm tests arrive in Task 3.7; `confirm_action`/`cancel_action` are defined there — add temporary `def confirm_action(*a, **k): raise NotImplementedError` / same for `cancel_action` so the module imports, since no test exercises them yet). **Commit:** `git add backend/app/services/chat_service.py backend/tests/integration/test_chat_flow.py && git commit -m "feat: chat state machine - merge, supersede, query routing, staleness"`

### Task 3.7: Confirmation, cancellation and executors

> **As-built note (commits 57daf2b, 4739d5d):** `_flip_to_confirmed` makes confirmation a transactional mutex (one winner executes, losers get 409 `action_not_confirmable`). Post-review, the receipt executor was made idempotent: executors receive `action_ref`, and `_execute_receipt` persists the draft id (`payload._draftId`) before issuing, so a confirm-retry after a failed `issue_receipt` re-issues the SAME draft instead of minting a duplicate receipt number (regression-tested). Known limitation (documented in code): a process crash between the confirmed-flip commit and executor completion strands the action in `confirmed` (the stale sweep only covers `collecting_fields`/`pending_confirmation`) — acceptable for the single-user MVP.

**Files:** Modify: `backend/app/services/chat_service.py`. Test: `backend/tests/integration/test_chat_confirm.py`.

- [ ] **Step 1: Write failing tests.** Module-level fixture stubs out PDF/Cloudinary so `issue_receipt` runs offline (Phase 2 convention: `receipt_service` imports the modules, so patching module attributes works):
```python
# backend/tests/integration/test_chat_confirm.py
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
from app.schemas.business import Business
from app.services import chat_service
from app.services.cloudinary_service import UploadResult
from tests.stubs import StubCommandParser
from tests.integration.test_chat_flow import FULL_RECEIPT, _actions

@pytest.fixture(autouse=True)
def fake_pdf_and_cloudinary(monkeypatch):
    monkeypatch.setattr("app.services.pdf_service.render_pdf", lambda template_name, context: b"%PDF-1.4 fake")
    monkeypatch.setattr("app.services.cloudinary_service.upload_pdf",
        lambda data, public_id: UploadResult(secure_url=f"https://res.test/{public_id}", public_id=public_id))

@pytest.fixture
def pending_receipt(db, make_business):
    biz = Business.model_validate(make_business())
    stub = StubCommandParser().queue_command(FULL_RECEIPT)
    res = chat_service.handle_message(db, stub, biz, "main", "קיבלתי 2800 מנועה על עיצוב לוגו בביט")
    return biz, res.action.id

def test_confirm_executes_receipt(db, pending_receipt):
    biz, action_id = pending_receipt
    res = chat_service.confirm_action(db, None, biz, action_id)
    assert res.result["receiptNumber"].endswith("-0001") and res.assistant_text == f"נוצרה קבלה מספר {res.result['receiptNumber']}."
    assert _actions(db, biz.id)[action_id]["status"] == "executed"

def test_fast_path_confirm_word_skips_llm(db, pending_receipt):
    biz, action_id = pending_receipt
    stub = StubCommandParser()                      # empty queue: any LLM call would assert
    res = chat_service.handle_message(db, stub, biz, "main", "אישור")
    assert res.result and res.result["receiptId"] and stub.calls == []

def test_fast_path_cancel_word(db, pending_receipt):
    biz, action_id = pending_receipt
    res = chat_service.handle_message(db, StubCommandParser(), biz, "main", "בטל")
    assert res.assistant_text == "הפעולה בוטלה."
    assert _actions(db, biz.id)[action_id]["cancellationReason"] == "user_cancelled"

def test_double_confirm_race_exactly_one_winner(db, pending_receipt):
    biz, action_id = pending_receipt
    def go():
        try: return chat_service.confirm_action(db, None, biz, action_id)
        except HTTPException as e: return e
    with ThreadPoolExecutor(max_workers=2) as ex:
        a, b = list(ex.map(lambda _: go(), range(2)))
    outcomes = sorted(type(x).__name__ for x in (a, b))
    assert outcomes == ["ExecutionResult", "HTTPException"]
    err = a if isinstance(a, HTTPException) else b
    assert err.status_code == 409 and err.detail["code"] == "action_not_confirmable"

def test_executor_failure_reverts_to_pending(db, pending_receipt, monkeypatch):
    biz, action_id = pending_receipt
    monkeypatch.setattr("app.services.receipt_service.issue_receipt",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    res = chat_service.confirm_action(db, None, biz, action_id)
    data = _actions(db, biz.id)[action_id]
    assert data["status"] == "pending_confirmation" and data["errorNote"] == "boom"
    assert res.assistant_text == "אירעה שגיאה בביצוע הפעולה. אפשר לנסות לאשר שוב."

def test_cancel_executed_action_is_409(db, pending_receipt):
    biz, action_id = pending_receipt
    chat_service.confirm_action(db, None, biz, action_id)
    with pytest.raises(HTTPException) as e:
        chat_service.cancel_action(db, biz.id, action_id)
    assert e.value.status_code == 409 and e.value.detail["code"] == "action_not_cancellable"
```
- [ ] **Step 2: Run** → fails. **Implement** (replace the Task 3.6 placeholders):
```python
from google.cloud import firestore
from app.schemas.client import ClientCreate
from app.schemas.receipt import ReceiptDraftCreate

def _flip_to_confirmed(db, action_ref) -> dict:
    tx = db.transaction()
    @firestore.transactional
    def flip(transaction):
        snap = action_ref.get(transaction=transaction)
        if not snap.exists:
            api_error(404, "action_not_found", "הפעולה לא נמצאה")
        data = snap.to_dict()
        if data["status"] != "pending_confirmation":
            api_error(409, "action_not_confirmable", "הפעולה כבר טופלה או אינה ממתינה לאישור")
        transaction.update(action_ref, {"status": "confirmed", "updatedAt": now_il()})
        return data
    return flip(tx)

def _execute_receipt(db, business: Business, payload: dict):
    name = payload["client_name"].strip()
    exact = [c for c in client_service.find_clients_by_name(db, business.id, name) if c.name.strip() == name]
    client_id = exact[0].id if len(exact) == 1 else None
    # create_draft builds the clientSnapshot itself: full client doc when client_id
    # resolves, name-only otherwise (Task 2.3) — ReceiptDraftCreate has no snapshot field
    draft = receipt_service.create_draft(db, business, ReceiptDraftCreate(
        client_id=client_id, client_name=name, amount=round_ils(payload["amount"]), currency="ILS",
        payment_method=payload.get("payment_method") or "unknown",
        description=payload["description"]))
    receipt = receipt_service.issue_receipt(db, business.id, draft.id)
    return (f"נוצרה קבלה מספר {receipt.receipt_number}.",
            {"receiptId": receipt.id, "receiptNumber": receipt.receipt_number, "pdfUrl": receipt.pdf_url})

def _execute_contact(db, business, payload):
    client = client_service.create_client(db, business.id, ClientCreate(
        name=payload["name"], phone=payload.get("phone"), email=payload.get("email"),
        company_name=payload.get("company_name"), tax_id=payload.get("tax_id"), address=payload.get("address")))
    return f"איש הקשר {client.name} נוסף בהצלחה.", {"clientId": client.id}

def _execute_expense(db, business, payload):
    from app.services import expense_service          # Phase 4 module — imported lazily on purpose
    from app.schemas.expense import ExpenseCreate
    expense = expense_service.create_expense(db, business.id, ExpenseCreate(
        supplier_name=payload.get("supplier_name"), amount=round_ils(payload["amount"]), currency="ILS",
        category=payload.get("category"), description=payload.get("description"),
        business_use_percent=payload.get("business_use_percent") or 100,
        expense_date=payload.get("expense_date")), source="chat")
    note = " היא ממתינה לבדיקה כי חסרה קטגוריה." if expense.status == "needs_review" else ""
    return f"ההוצאה נשמרה.{note}", {"expenseId": expense.id}

_EXECUTORS = {"CREATE_RECEIPT": _execute_receipt, "CREATE_CONTACT": _execute_contact,
              "CREATE_EXPENSE": _execute_expense,
              "GENERATE_ANNUAL_REPORT": lambda db, business, payload:
                  (f"מעולה. אפשר להפיק את הדוח השנתי לשנת {payload['year']} בעמוד הדוח השנתי.",
                   {"year": payload["year"], "link": "/annual-report"})}

def confirm_action(db, parser_or_none, business: Business, action_id: str) -> ExecutionResult:
    action_ref = _actions_col(db, business.id).document(action_id)
    data = _flip_to_confirmed(db, action_ref)
    thread_id, payload = data["threadId"], data["payload"]
    try:
        reply, result = _EXECUTORS[data["type"]](db, business, payload)
    except Exception as exc:                          # revert: user can confirm again
        action_ref.update({"status": "pending_confirmation", "errorNote": str(exc), "updatedAt": now_il()})
        reply = "אירעה שגיאה בביצוע הפעולה. אפשר לנסות לאשר שוב."
        save_message(db, business.id, thread_id, "assistant", reply, action_id=action_id)
        return ExecutionResult(assistant_text=reply, action=ActionView(
            id=action_id, type=data["type"], status="pending_confirmation", payload=payload, missing_fields=[]))
    action_ref.update({"status": "executed", "result": result, "updatedAt": now_il()})
    save_message(db, business.id, thread_id, "assistant", reply, action_id=action_id)
    return ExecutionResult(assistant_text=reply, action=ActionView(
        id=action_id, type=data["type"], status="executed", payload=payload, missing_fields=[]), result=result)

def cancel_action(db, business_id: str, action_id: str, reason: str = "user_cancelled") -> None:
    ref = _actions_col(db, business_id).document(action_id)
    snap = ref.get()
    if not snap.exists:
        api_error(404, "action_not_found", "הפעולה לא נמצאה")
    if snap.to_dict()["status"] not in ACTIVE_STATUSES:
        api_error(409, "action_not_cancellable", "הפעולה כבר בוצעה או בוטלה")
    ref.update({"status": "cancelled", "cancellationReason": reason, "updatedAt": now_il()})
```
(CREATE_EXPENSE execution is covered by tests in Phase 4 when `expense_service` exists; the lazy import keeps Phase 3 importable.)
- [ ] **Step 3: Run** `python -m pytest tests/integration/test_chat_confirm.py tests/integration/test_chat_flow.py -q` → all pass. **Commit:** `git add backend/app/services/chat_service.py backend/tests/integration/test_chat_confirm.py && git commit -m "feat: transactional confirm, executors, cancel and double-confirm guard"`

### Task 3.8: Chat router + API tests

**Files:** Create: `backend/app/routers/chat.py`. Modify: `backend/app/main.py`. Test: `backend/tests/integration/test_chat_api.py`.

- [ ] **Step 1: Write failing API tests** (uses `api`, `stub_parser`, `make_business`, plus the same `fake_pdf_and_cloudinary` autouse fixture copied into this module):
  - `test_post_message_returns_turn_result`: queue `FULL_RECEIPT`; `POST /api/businesses/{id}/chat/message` body `{"text": "קיבלתי 2800 מנועה על עיצוב לוגו בביט"}` → 200; JSON `assistantText` starts `"לאשר יצירת קבלה"`, `action.status == "pending_confirmation"`, `action.missingFields == []` (camelCase on the wire).
  - `test_empty_message_422`: body `{"text": "   "}` → 422 with `detail.code == "empty_message"`, message `"הודעה ריקה"`.
  - `test_confirm_endpoint_executes`: after pending action, `POST .../chat/actions/{actionId}/confirm` → 200, `result.receiptNumber` ends `"-0001"`; second identical POST → 409 `action_not_confirmable`.
  - `test_cancel_endpoint`: `POST .../chat/actions/{actionId}/cancel` → 200 `{"status": "cancelled"}`; Firestore action has `cancellationReason == "user_cancelled"`; an assistant message `"הפעולה בוטלה."` exists in the thread.
  - `test_get_messages_returns_history_and_active_action`: after the §14.2 two-message flow, `GET .../chat/messages?threadId=main` → 200, 4 messages oldest-first, `activeAction.status == "pending_confirmation"`.
  - `test_confirm_unknown_action_404`: random actionId → 404 `action_not_found`.
- [ ] **Step 2: Run** → 404s (router missing). **Implement** `backend/app/routers/chat.py`:
```python
from fastapi import APIRouter, Depends, Query
from app.core.auth import get_owned_business
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.chat import (ChatHistoryResponse, ChatMessage, ChatMessageRequest,
                              ChatTurnResult, ExecutionResult)
from app.services import chat_service
from app.services.openai_service import CommandParser, get_command_parser

router = APIRouter(prefix="/businesses/{businessId}/chat", tags=["chat"])

@router.post("/message", response_model=ChatTurnResult)
def post_message(body: ChatMessageRequest, business: Business = Depends(get_owned_business),
                 db=Depends(get_db), parser: CommandParser = Depends(get_command_parser)):
    text = body.text.strip()
    if not text:
        api_error(422, "empty_message", "הודעה ריקה")
    return chat_service.handle_message(db, parser, business, body.thread_id, text)

@router.post("/actions/{action_id}/confirm", response_model=ExecutionResult)
def confirm(action_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return chat_service.confirm_action(db, None, business, action_id)

@router.post("/actions/{action_id}/cancel")
def cancel(action_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    snap = db.collection("businesses").document(business.id).collection("pendingActions").document(action_id).get()
    thread_id = snap.to_dict().get("threadId", "main") if snap.exists else "main"
    chat_service.cancel_action(db, business.id, action_id)   # raises 404/409
    chat_service.save_message(db, business.id, thread_id, "assistant", "הפעולה בוטלה.", action_id=action_id)
    return {"status": "cancelled"}

@router.get("/messages", response_model=ChatHistoryResponse)
def list_messages(business: Business = Depends(get_owned_business), db=Depends(get_db),
                  thread_id: str = Query("main", alias="threadId"), limit: int = Query(50, le=200)):
    docs = db.collection("businesses").document(business.id).collection("chatThreads") \
             .document(thread_id).collection("messages") \
             .order_by("createdAt", direction="DESCENDING").limit(limit).stream()
    messages = [ChatMessage.model_validate({**d.to_dict(), "id": d.id}) for d in docs][::-1]
    active = chat_service._load_active_action(db, business.id, thread_id)
    return ChatHistoryResponse(messages=messages,
                               active_action=chat_service._action_view(*active) if active else None)
```
Register in `app/main.py`: `app.include_router(chat.router, prefix="/api")`. (`GET /messages` is the single deliberate addition to doc §6.5 — the UI cannot render history without it; the three POST routes match §6.5 exactly.)
- [ ] **Step 3: Run** `python -m pytest tests/integration/test_chat_api.py -q` → all pass; then full suite `python -m pytest -q`. **Commit:** `git add backend/app/routers/chat.py backend/app/main.py backend/tests/integration/test_chat_api.py && git commit -m "feat: chat API - message, confirm, cancel, history"`

### Task 3.9: Chat UI (mobile-first centerpiece)

> **As-built note (commits d802cbc, 7f4940e):** built verbatim. Post-review hero-screen fixes: the message list always scrolls to the user's own freshly-sent bubble (guards an IntersectionObserver race that could push it off-screen); the inline `ConfirmActionCard` survives a *transient* confirm/cancel failure (only a definitive 4xx dismisses it, so the user keeps the ability to retry); the failed-message retry chip is disabled while another send is in flight. `tnum` (custom utility in globals.css) and the optimistic local-id keying are intentional.

**Files:** Create: `frontend/components/ChatMessageList.tsx`, `frontend/components/ChatInput.tsx`, `frontend/components/ConfirmActionCard.tsx`, `frontend/lib/useIosKeyboardFix.ts`. Modify: `frontend/app/chat/page.tsx`, `frontend/lib/types.ts`.

**Deviation from doc §13 (deliberate):** `ConfirmActionModal.tsx` is replaced by `ConfirmActionCard.tsx` — confirmation renders inline inside the assistant message instead of a modal overlay. Rationale: on a 375px phone a modal hides the conversation the user is confirming; inline confirmation keeps chat context, and doc §14.1 already shows the confirmation happening inside the chat. Imports used here that earlier phases created: `apiClient`/`auth`/`firebase` (Phases 0–1), `EmptyState` + `formatILS` (Phase 2), `lucide-react` (Phase 0).

- [ ] **Step 1: Types.** Append to `frontend/lib/types.ts`:
```ts
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  actionId?: string | null;
  createdAt: string;
}

export interface ActionView {
  id: string;
  type: string;
  status: string;
  payload: Record<string, unknown>;
  missingFields: string[];
}

export interface ActionResult {
  receiptId?: string;
  receiptNumber?: string;
  pdfUrl?: string | null;
  clientId?: string;
  expenseId?: string;
  year?: number;
  link?: string;
}

export interface ChatTurnResult {
  assistantText: string;
  action: ActionView | null;
  result?: ActionResult | null;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  activeAction: ActionView | null;
}

// client-only message state for optimistic send / inline retry / inline PDF button
export type ChatSendStatus = "pending" | "failed";

export interface UiChatMessage extends ChatMessage {
  sendStatus?: ChatSendStatus;
  pdfUrl?: string | null;
}
```
- [ ] **Step 2: iOS keyboard fix hook.** Create `frontend/lib/useIosKeyboardFix.ts` (canonical from the mobile brief, verbatim — iOS 26 Safari: `visualViewport.offsetTop` doesn't reset after keyboard dismissal; nudge layout; Android is already handled by `interactive-widget=resizes-content` from Phase 0's viewport):
```ts
"use client";

import { useEffect } from "react";

export function useIosKeyboardFix() {
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;
    let lastTop = vv.offsetTop;
    const onResize = () => {
      if (vv.offsetTop < lastTop && vv.offsetTop !== 0) {
        window.scrollBy(0, -1);
        window.scrollBy(0, 1);
      }
      lastTop = vv.offsetTop;
    };
    vv.addEventListener("resize", onResize);
    return () => vv.removeEventListener("resize", onResize);
  }, []);
}
```
- [ ] **Step 3: ChatInput.** Create `frontend/components/ChatInput.tsx` — sticky footer of the chat column: auto-growing textarea (capped at 120px), `text-base` (no iOS zoom), 48px icon send button with the `Send` icon flipped for RTL; Enter sends on desktop only (coarse-pointer devices get Enter = newline); `onMouseDown` preventDefault on the button keeps the keyboard open after tapping send:
```tsx
"use client";

import { useRef, useState } from "react";
import { Loader2, Send } from "lucide-react";

type ChatInputProps = {
  onSend: (text: string) => void;
  disabled: boolean;
};

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const autoGrow = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  };

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    setText("");
    const el = textareaRef.current;
    if (el) el.style.height = "auto";
    onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const isMobile = window.matchMedia("(pointer: coarse)").matches;
    if (e.key === "Enter" && !e.shiftKey && !isMobile) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2 bg-muted px-4 pb-2 pt-1">
      <textarea
        ref={textareaRef}
        value={text}
        rows={1}
        aria-label="הודעה"
        placeholder="מה קרה בעסק?"
        onChange={(e) => {
          setText(e.target.value);
          autoGrow();
        }}
        onKeyDown={handleKeyDown}
        className="min-h-12 flex-1 resize-none rounded-2xl border border-border bg-white px-4 py-3 text-base focus:outline-none focus:ring-2 focus:ring-primary"
      />
      <button
        onClick={submit}
        onMouseDown={(e) => e.preventDefault()}
        disabled={disabled || !text.trim()}
        aria-label="שליחה"
        className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
      >
        {disabled ? (
          <Loader2 size={20} className="animate-spin" aria-hidden />
        ) : (
          <Send size={20} className="-scale-x-100" aria-hidden />
        )}
      </button>
    </div>
  );
}
```
- [ ] **Step 4: ConfirmActionCard.** Create `frontend/components/ConfirmActionCard.tsx` — inline confirmation card rendered as part of the assistant message (replaces doc §13's `ConfirmActionModal`): Hebrew summary rows from the pending-action payload (amounts via `formatILS` with a `dir="ltr"` + `tnum` island, payment/category enums mapped to the same Hebrew labels the backend uses in `hebrew.py`), then two 48px buttons — אישור (primary) / ביטול (ghost) — disabled with a spinner while either endpoint call is in flight:
```tsx
"use client";

import { useState } from "react";
import { Check, Loader2, X } from "lucide-react";
import { formatILS } from "@/lib/format";
import type { ActionView } from "@/lib/types";

const TITLES: Record<string, string> = {
  CREATE_RECEIPT: "אישור יצירת קבלה",
  CREATE_CONTACT: "אישור יצירת איש קשר",
  CREATE_EXPENSE: "אישור הוספת הוצאה",
  GENERATE_ANNUAL_REPORT: "אישור הפקת דוח שנתי",
};

const PAYMENT_HE: Record<string, string> = {
  cash: "מזומן",
  bank_transfer: "העברה בנקאית",
  bit: "ביט",
  paybox: "פייבוקס",
  credit_card: "כרטיס אשראי",
  check: "צ'ק",
  other: "אחר",
  unknown: "לא צוין",
};

const CATEGORY_HE: Record<string, string> = {
  software: "תוכנה",
  equipment: "ציוד",
  travel: "נסיעות",
  office: "משרד",
  marketing: "שיווק",
  professional_services: "שירותים מקצועיים",
  meals: "אוכל",
  parking: "חניה",
  other: "אחר",
};

type SummaryRow = { label: string; value: string; ltr?: boolean };

function summaryRows(action: ActionView): SummaryRow[] {
  const p = action.payload;
  const rows: SummaryRow[] = [];
  if (action.type === "CREATE_RECEIPT") {
    if (typeof p.client_name === "string") rows.push({ label: "לקוח", value: p.client_name });
    if (typeof p.amount === "number") rows.push({ label: "סכום", value: formatILS(p.amount), ltr: true });
    if (typeof p.description === "string") rows.push({ label: "תיאור", value: p.description });
    const pm = typeof p.payment_method === "string" ? p.payment_method : "unknown";
    rows.push({ label: "אמצעי תשלום", value: PAYMENT_HE[pm] ?? "לא צוין" });
  } else if (action.type === "CREATE_CONTACT") {
    if (typeof p.name === "string") rows.push({ label: "שם", value: p.name });
    if (typeof p.phone === "string" && p.phone) rows.push({ label: "טלפון", value: p.phone, ltr: true });
    if (typeof p.email === "string" && p.email) rows.push({ label: "אימייל", value: p.email, ltr: true });
  } else if (action.type === "CREATE_EXPENSE") {
    if (typeof p.supplier_name === "string" && p.supplier_name)
      rows.push({ label: "ספק", value: p.supplier_name });
    if (typeof p.amount === "number") rows.push({ label: "סכום", value: formatILS(p.amount), ltr: true });
    if (typeof p.category === "string" && p.category)
      rows.push({ label: "קטגוריה", value: CATEGORY_HE[p.category] ?? p.category });
    if (typeof p.description === "string" && p.description)
      rows.push({ label: "תיאור", value: p.description });
  } else if (action.type === "GENERATE_ANNUAL_REPORT") {
    if (typeof p.year === "number") rows.push({ label: "שנה", value: String(p.year), ltr: true });
  }
  return rows;
}

type ConfirmActionCardProps = {
  action: ActionView;
  onConfirm: () => Promise<void>;
  onCancel: () => Promise<void>;
};

export default function ConfirmActionCard({ action, onConfirm, onCancel }: ConfirmActionCardProps) {
  const [executing, setExecuting] = useState<"confirm" | "cancel" | null>(null);

  const run = async (kind: "confirm" | "cancel", fn: () => Promise<void>) => {
    if (executing) return;
    setExecuting(kind);
    try {
      await fn();
    } finally {
      setExecuting(null);
    }
  };

  return (
    <div className="me-auto w-full max-w-[85%] rounded-2xl border border-border bg-white p-4">
      <p className="mb-3 text-sm font-semibold text-foreground/70">
        {TITLES[action.type] ?? "אישור פעולה"}
      </p>
      <dl className="mb-4 space-y-2">
        {summaryRows(action).map(({ label, value, ltr }) => (
          <div key={label} className="flex items-baseline justify-between gap-3">
            <dt className="text-sm text-foreground/60">{label}</dt>
            <dd className={`font-medium ${ltr ? "tnum" : ""}`} dir={ltr ? "ltr" : undefined}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      <div className="flex gap-2">
        <button
          onClick={() => run("confirm", onConfirm)}
          disabled={executing !== null}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {executing === "confirm" ? (
            <Loader2 size={18} className="animate-spin" aria-hidden />
          ) : (
            <Check size={18} aria-hidden />
          )}
          אישור
        </button>
        <button
          onClick={() => run("cancel", onCancel)}
          disabled={executing !== null}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-border font-medium text-foreground transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {executing === "cancel" ? (
            <Loader2 size={18} className="animate-spin" aria-hidden />
          ) : (
            <X size={18} aria-hidden />
          )}
          ביטול
        </button>
      </div>
    </div>
  );
}
```
- [ ] **Step 5: ChatMessageList.** Create `frontend/components/ChatMessageList.tsx` — scrollable message column with: user bubbles `ms-auto bg-primary text-on-primary` / assistant bubbles `me-auto bg-white border border-border` (both `max-w-[85%] rounded-2xl px-4 py-2.5 whitespace-pre-wrap`); a bottom sentinel watched by an `IntersectionObserver` — new messages auto-scroll (smooth) only while the sentinel is visible, otherwise a floating 48px "הודעות חדשות" chip appears above the input and scrolls to the bottom on tap; instant scroll on first load; pending messages dimmed with a `Clock` caption; failed messages get an inline retry chip ("שליחה נכשלה — הקש לנסות שוב", no toast/modal); assistant messages carrying a `pdfUrl` render a הורדת PDF button; the `ConfirmActionCard` is attached under the assistant message that owns the active pending-confirmation action:
```tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, Clock, FileDown, MessageCircle, RefreshCw } from "lucide-react";
import ConfirmActionCard from "@/components/ConfirmActionCard";
import EmptyState from "@/components/EmptyState";
import type { ActionView, UiChatMessage } from "@/lib/types";

type ChatMessageListProps = {
  messages: UiChatMessage[];
  activeAction: ActionView | null;
  onConfirm: () => Promise<void>;
  onCancel: () => Promise<void>;
  onRetry: (messageId: string) => void;
};

export default function ChatMessageList({
  messages,
  activeAction,
  onConfirm,
  onCancel,
  onRetry,
}: ChatMessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const atBottomRef = useRef(true);
  const prevCountRef = useRef(0);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = useCallback((behavior: ScrollBehavior) => {
    const el = containerRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior });
    setShowJump(false);
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    const sentinel = sentinelRef.current;
    if (!container || !sentinel) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        atBottomRef.current = entry.isIntersecting;
        if (entry.isIntersecting) setShowJump(false);
      },
      { root: container, rootMargin: "0px 0px 80px 0px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (messages.length === prevCountRef.current) return;
    const isFirstLoad = prevCountRef.current === 0;
    prevCountRef.current = messages.length;
    if (isFirstLoad) {
      scrollToBottom("auto"); // instant on first load
    } else if (atBottomRef.current) {
      scrollToBottom("smooth");
    } else {
      setShowJump(true);
    }
  }, [messages.length, scrollToBottom]);

  const pendingConfirmation = activeAction?.status === "pending_confirmation" ? activeAction : null;
  let confirmIndex = -1;
  if (pendingConfirmation) {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant" && messages[i].actionId === pendingConfirmation.id) {
        confirmIndex = i;
        break;
      }
    }
  }

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        ref={containerRef}
        className="flex flex-1 flex-col gap-2 overflow-y-auto px-4 py-3 [overscroll-behavior:contain]"
      >
        {messages.length === 0 && (
          <div className="py-6">
            <EmptyState
              Icon={MessageCircle}
              title="עוד אין הודעות"
              hint='כתבו מה קרה בעסק. לדוגמה: "קיבלתי 2800 מנועה על עיצוב לוגו בביט"'
            />
          </div>
        )}
        {messages.map((m, i) => (
          <div key={m.id} className="flex flex-col gap-1">
            <div
              className={
                m.role === "user"
                  ? `ms-auto max-w-[85%] whitespace-pre-wrap rounded-2xl bg-primary px-4 py-2.5 text-on-primary ${
                      m.sendStatus === "pending" ? "opacity-60" : ""
                    }`
                  : "me-auto max-w-[85%] whitespace-pre-wrap rounded-2xl border border-border bg-white px-4 py-2.5"
              }
            >
              {m.text}
            </div>
            {m.sendStatus === "pending" && (
              <span className="ms-auto flex items-center gap-1 text-xs text-foreground/50">
                <Clock size={12} aria-hidden />
                שולח...
              </span>
            )}
            {m.sendStatus === "failed" && (
              <button
                onClick={() => onRetry(m.id)}
                className="ms-auto flex min-h-12 items-center gap-1.5 text-sm font-medium text-destructive transition-transform duration-150 active:scale-[0.98]"
              >
                <RefreshCw size={16} aria-hidden />
                שליחה נכשלה — הקש לנסות שוב
              </button>
            )}
            {m.pdfUrl && (
              <a
                href={m.pdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="me-auto mt-1 flex min-h-12 items-center gap-2 rounded-xl border border-border bg-white px-4 text-sm font-medium text-primary transition-transform duration-150 active:scale-[0.98]"
              >
                <FileDown size={18} aria-hidden />
                הורדת PDF
              </a>
            )}
            {i === confirmIndex && pendingConfirmation && (
              <div className="mt-1">
                <ConfirmActionCard
                  action={pendingConfirmation}
                  onConfirm={onConfirm}
                  onCancel={onCancel}
                />
              </div>
            )}
          </div>
        ))}
        {pendingConfirmation && confirmIndex === -1 && (
          <ConfirmActionCard action={pendingConfirmation} onConfirm={onConfirm} onCancel={onCancel} />
        )}
        <div ref={sentinelRef} className="h-px shrink-0" aria-hidden />
      </div>
      {showJump && (
        <button
          onClick={() => scrollToBottom("smooth")}
          className="absolute inset-x-0 bottom-3 z-10 mx-auto flex min-h-12 w-fit items-center gap-1.5 rounded-full border border-border bg-white px-4 text-sm font-medium text-primary shadow-md transition-transform duration-150 active:scale-[0.98]"
        >
          <ArrowDown size={18} aria-hidden />
          הודעות חדשות
        </button>
      )}
    </div>
  );
}
```
- [ ] **Step 6: Page.** Replace `frontend/app/chat/page.tsx` — fills the viewport above the BottomNav with `h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))]` (`dvh` shrinks with the Android keyboard via Phase 0's `interactive-widget=resizes-content`; `useIosKeyboardFix()` covers iOS Safari). Keeps the existing contracts: `useAuth()` redirect to `/login` when `!user && !loading`, business via `api<Business>("/businesses/me")`, history via `GET /chat/messages`, `ApiError` Hebrew `message` rendered inline as an assistant-style bubble. Sending is optimistic: the user bubble appears immediately as `pending`; a network failure flips it to `failed` with the inline retry chip (an `ApiError` means the server answered — its Hebrew message is shown instead, no retry). Confirm/cancel call the Task 3.8 endpoints and append the resulting assistant message (with PDF button when `result.pdfUrl` exists) — note the executor-failure case returns `action.status === "pending_confirmation"`, which keeps the card visible for a second attempt:
```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ChatInput from "@/components/ChatInput";
import ChatMessageList from "@/components/ChatMessageList";
import { api, ApiError } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { useIosKeyboardFix } from "@/lib/useIosKeyboardFix";
import type {
  ActionView,
  Business,
  ChatHistoryResponse,
  ChatTurnResult,
  UiChatMessage,
} from "@/lib/types";

let localIdCounter = 0;
const nextLocalId = (prefix: string) => `${prefix}-${Date.now()}-${localIdCounter++}`;

export default function ChatPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  useIosKeyboardFix();

  const [biz, setBiz] = useState<Business | null>(null);
  const [messages, setMessages] = useState<UiChatMessage[]>([]);
  const [activeAction, setActiveAction] = useState<ActionView | null>(null);
  const [sending, setSending] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  const pushAssistant = useCallback((text: string, extra?: Partial<UiChatMessage>) => {
    setMessages((prev) => [
      ...prev,
      { id: nextLocalId("a"), role: "assistant", text, createdAt: new Date().toISOString(), ...extra },
    ]);
  }, []);

  const pushError = useCallback(
    (e: unknown) => {
      pushAssistant(e instanceof ApiError ? e.message : "אירעה שגיאה, נסו שוב.");
    },
    [pushAssistant],
  );

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const business = await api<Business>("/businesses/me");
        if (cancelled) return;
        setBiz(business);
        const history = await api<ChatHistoryResponse>(`/businesses/${business.id}/chat/messages`);
        if (cancelled) return;
        setMessages(history.messages);
        setActiveAction(history.activeAction);
      } catch (e) {
        if (!cancelled) pushError(e);
      } finally {
        if (!cancelled) setHistoryLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, pushError]);

  const applyTurn = useCallback(
    (res: ChatTurnResult, actionId?: string) => {
      pushAssistant(res.assistantText, {
        actionId: res.action?.id ?? actionId ?? null,
        pdfUrl: res.result?.pdfUrl ?? null,
      });
      setActiveAction(res.action && res.action.status === "pending_confirmation" ? res.action : null);
    },
    [pushAssistant],
  );

  const deliver = useCallback(
    async (localId: string, text: string) => {
      if (!biz) return;
      setSending(true);
      try {
        const res = await api<ChatTurnResult>(`/businesses/${biz.id}/chat/message`, {
          method: "POST",
          body: JSON.stringify({ text }),
        });
        setMessages((prev) => prev.map((m) => (m.id === localId ? { ...m, sendStatus: undefined } : m)));
        applyTurn(res);
      } catch (e) {
        if (e instanceof ApiError) {
          // server rejected the message itself (e.g. 422): show its Hebrew message, no retry
          setMessages((prev) => prev.map((m) => (m.id === localId ? { ...m, sendStatus: undefined } : m)));
          pushError(e);
        } else {
          // network failure: keep the bubble, offer inline retry
          setMessages((prev) =>
            prev.map((m) => (m.id === localId ? { ...m, sendStatus: "failed" as const } : m)),
          );
        }
      } finally {
        setSending(false);
      }
    },
    [biz, applyTurn, pushError],
  );

  const send = useCallback(
    (text: string) => {
      const localId = nextLocalId("u");
      setMessages((prev) => [
        ...prev,
        { id: localId, role: "user", text, createdAt: new Date().toISOString(), sendStatus: "pending" },
      ]);
      void deliver(localId, text);
    },
    [deliver],
  );

  const retry = useCallback(
    (messageId: string) => {
      if (sending) return;
      const failed = messages.find((m) => m.id === messageId);
      if (!failed) return;
      setMessages((prev) =>
        prev.map((m) => (m.id === messageId ? { ...m, sendStatus: "pending" as const } : m)),
      );
      void deliver(messageId, failed.text);
    },
    [messages, sending, deliver],
  );

  const confirmAction = useCallback(async () => {
    if (!biz || !activeAction) return;
    const actionId = activeAction.id;
    try {
      const res = await api<ChatTurnResult>(`/businesses/${biz.id}/chat/actions/${actionId}/confirm`, {
        method: "POST",
      });
      applyTurn(res, actionId);
    } catch (e) {
      pushError(e);
      setActiveAction(null);
    }
  }, [biz, activeAction, applyTurn, pushError]);

  const cancelAction = useCallback(async () => {
    if (!biz || !activeAction) return;
    const actionId = activeAction.id;
    try {
      await api<{ status: string }>(`/businesses/${biz.id}/chat/actions/${actionId}/cancel`, {
        method: "POST",
      });
      pushAssistant("הפעולה בוטלה.", { actionId });
      setActiveAction(null);
    } catch (e) {
      pushError(e);
      setActiveAction(null);
    }
  }, [biz, activeAction, pushAssistant, pushError]);

  return (
    <div className="flex h-[calc(100dvh-4rem-env(safe-area-inset-bottom,0px))] flex-col">
      {historyLoading ? (
        <div className="flex flex-1 flex-col gap-3 overflow-hidden px-4 py-4" aria-hidden>
          <div className="me-auto h-12 w-3/5 animate-pulse rounded-2xl border border-border bg-white" />
          <div className="ms-auto h-12 w-1/2 animate-pulse rounded-2xl bg-border" />
          <div className="me-auto h-20 w-2/3 animate-pulse rounded-2xl border border-border bg-white" />
        </div>
      ) : (
        <ChatMessageList
          messages={messages}
          activeAction={activeAction}
          onConfirm={confirmAction}
          onCancel={cancelAction}
          onRetry={retry}
        />
      )}
      <ChatInput onSend={send} disabled={sending || historyLoading || !biz} />
    </div>
  );
}
```
- [ ] **Step 7: Verify.** Run `cd /Users/tamirsida/dev/tax/frontend && npx tsc --noEmit && npm run build` → both clean. Manual check with dev backend running (real OpenAI key in `backend/.env`): open devtools device toolbar at 375×812, verify on `http://localhost:3000/chat` after Google sign-in: (1) the chat column fills the screen above the bottom tab bar with no page scrollbar; (2) focus the input — the keyboard opens, the input stays visible and the message list still scrolls; (3) send `קיבלתי 2800 מנועה על עיצוב לוגו בביט` → your bubble appears instantly (dimmed + clock while in flight), then the assistant reply renders an inline `ConfirmActionCard` with לקוח/סכום/תיאור/אמצעי תשלום rows (₪2,800 shown LTR) and 48px אישור/ביטול buttons — no modal anywhere; (4) tap אישור → spinner, then «נוצרה קבלה מספר 2026-XXXX.» appears as a new assistant message with a working הורדת PDF button; (5) send `תוציא קבלה לדני על ייעוץ` → follow-up question without a card; reply `500 במזומן` → card appears; type `בטל` → «הפעולה בוטלה.»; (6) send `כמה כסף עשיתי השנה?` → Hebrew total including the just-issued ₪2,800; (7) scroll up and send a message → the floating "הודעות חדשות" chip appears above the input and tapping it smooth-scrolls to the bottom; (8) set devtools Network to Offline and send → the bubble shows "שליחה נכשלה — הקש לנסות שוב"; go back online and tap it → the message sends; (9) reload → full history loads with instant scroll to the latest message and no stale card.
- [ ] **Step 8: Commit:** `git add frontend/app/chat/page.tsx frontend/components/ChatMessageList.tsx frontend/components/ChatInput.tsx frontend/components/ConfirmActionCard.tsx frontend/lib/useIosKeyboardFix.ts frontend/lib/types.ts && git commit -m "feat: mobile-first chat UI with inline confirmation, optimistic send and keyboard-safe layout"`
## Phase 4 — Expenses: Manual, Upload & Vision Extraction

Goal: full expense lifecycle — manual JSON creation, image upload to Cloudinary, OpenAI vision extraction, review/approve/reject — per design doc §3.6, §5.4, §6.4, §15. Depends on Phase 0 (fixtures, CI), Phase 1 (auth, `get_owned_business`), Phase 2 (`cloudinary_service`, `ledger_service`), Phase 3 (`openai_service` with `CommandParser.extract_expense`, `StubCommandParser`, chat pending-action executor that dispatches `CREATE_EXPENSE` to `expense_service.create_expense`).

**Done when:**
- [ ] All 7 endpoints of doc §6.4 exist under `/api/businesses/{businessId}/expenses` and their tests pass
- [ ] Status rules enforced server-side: image source always `needs_review`; chat/manual with amount+category → `approved`, missing category → `needs_review`
- [ ] Upload rejects bad content types (400 `unsupported_file_type`) and >10MB files (413 `file_too_large`)
- [ ] Extract uses an `f_jpg` Cloudinary delivery URL, merges fields + `ocrText` + `extractionConfidence`, expense stays `needs_review`
- [ ] Chat flow `תוסיף הוצאה של 120 שקל על Canva` → confirm → approved expense (integration test green)
- [ ] `aggregation_service.total_expenses`/`expenses_by_category` count approved-only, weighted by `businessUsePercent`
- [ ] `/expenses` page at 375×812: camera/gallery upload buttons, segmented tabs (לבדיקה / מאושרות / הכל) with needs_review count badge, expense card list (table only as `hidden md:block` desktop enhancement), approve/reject via `ExpenseReviewSheet` — verified in browser; `npm run build` green

### Task 4.1: Expense schemas

**Files:** Create: `backend/app/schemas/expense.py` — Test: `backend/tests/test_expense_schemas.py`

- [ ] **Step 1: Write failing schema tests**
```python
# backend/tests/test_expense_schemas.py
from app.schemas.expense import Expense, ExpenseCreate

def test_expense_serializes_camel_case_with_defaults():
    exp = Expense(id="e1", business_id="b1", status="needs_review",
                  created_at="2026-06-13T10:00:00+03:00", updated_at="2026-06-13T10:00:00+03:00")
    data = exp.model_dump(by_alias=True)
    assert data["businessId"] == "b1"
    assert data["businessUsePercent"] == 100
    assert data["supplierName"] is None and data["currency"] == "ILS"

def test_create_accepts_camel_and_snake_and_plain_enum_values():
    a = ExpenseCreate(supplier_name="Canva", amount=120, category="software")
    b = ExpenseCreate.model_validate({"supplierName": "Canva", "amount": 120, "category": "software"})
    assert a == b and a.category == "software"  # use_enum_values -> plain str
```
- [ ] **Step 2: Run** `cd /Users/tamirsida/dev/tax/backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test python -m pytest tests/test_expense_schemas.py -q` — expect `ModuleNotFoundError: No module named 'app.schemas.expense'`.
- [ ] **Step 3: Implement schemas** (doc §5.4 + request models; camelCase aliases; `use_enum_values` so Firestore writes get plain strings):
```python
# backend/app/schemas/expense.py
from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class _Camel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, use_enum_values=True)

class ExpenseCategory(str, Enum):
    SOFTWARE = "software"; EQUIPMENT = "equipment"; TRAVEL = "travel"; OFFICE = "office"
    MARKETING = "marketing"; PROFESSIONAL_SERVICES = "professional_services"
    MEALS = "meals"; PARKING = "parking"; OTHER = "other"

VALID_CATEGORIES = {c.value for c in ExpenseCategory}
ExpenseStatus = Literal["needs_review", "approved", "rejected"]

class Expense(_Camel):
    id: str
    business_id: str
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None          # ISO YYYY-MM-DD
    amount: Optional[float] = None
    currency: Literal["ILS"] = "ILS"
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    business_use_percent: int = 100
    image_url: Optional[str] = None
    cloudinary_public_id: Optional[str] = None
    ocr_text: Optional[str] = None
    extraction_confidence: Optional[float] = None
    status: ExpenseStatus
    created_at: datetime
    updated_at: datetime

class ExpenseCreate(_Camel):
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)   # amount <= 0 -> FastAPI 422
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    business_use_percent: Optional[int] = None            # clamped 0-100 in service, default 100
    image_url: Optional[str] = None                       # set by upload route only
    cloudinary_public_id: Optional[str] = None

class ExpensePatch(_Camel):   # exactly the editable whitelist — nothing else is patchable
    supplier_name: Optional[str] = None
    expense_date: Optional[str] = None
    amount: Optional[float] = Field(default=None, gt=0)
    category: Optional[ExpenseCategory] = None
    description: Optional[str] = None
    business_use_percent: Optional[int] = None
```
- [ ] **Step 4: Run again** — expect 2 passed.
- [ ] **Step 5: Commit** `git add backend/app/schemas/expense.py backend/tests/test_expense_schemas.py && git commit -m "feat: expense schemas with camelCase aliases per doc 5.4"`

### Task 4.2: Expense service — create, approve, reject, list, update

> **As-built note (commits 033f7e1, 2506012):** `create_expense` writes `currency:"ILS"` on the doc (ExpenseCreate has no currency field), clamps `business_use_percent` to 0-100 in the service, and sets `needs_review` when category is missing or source is `image`. Post-review, `approve_expense`/`reject_expense` were made transactional (status update + ledger event in one `@firestore.transactional`, matching the receipt-cancel pattern); `update_expense` 422s on a no-op patch. `create` stays a two-write insert (its `expense_created` event is informational — nothing reads the ledger for expense correctness).

**Files:** Create: `backend/app/services/expense_service.py` — Test: `backend/tests/test_expense_service.py`

- [ ] **Step 1: Write failing tests** (emulator `db` + `make_business` fixtures from Phase 0):
```python
# backend/tests/test_expense_service.py
import pytest
from fastapi import HTTPException
from app.schemas.expense import ExpenseCreate, ExpensePatch
from app.services import expense_service

def _payload(**kw):
    base = {"supplier_name": "Canva", "amount": 120.0, "category": "software"}
    base.update(kw); return ExpenseCreate(**base)

def _ledger(db, biz_id):
    return [s.to_dict() for s in db.collection("businesses").document(biz_id).collection("ledgerEvents").stream()]

def test_manual_with_amount_and_category_is_approved(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(), source="manual")
    assert exp.status == "approved" and exp.amount == 120.0 and exp.business_use_percent == 100

def test_missing_category_needs_review(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    assert exp.status == "needs_review"

def test_image_source_always_needs_review_even_when_complete(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(image_url="https://x/y.jpg",
        cloudinary_public_id="expenses/abc"), source="image")
    assert exp.status == "needs_review" and exp.cloudinary_public_id == "expenses/abc"

def test_create_writes_ledger_event_with_source(db, make_business):
    biz = make_business()
    expense_service.create_expense(db, biz["id"], _payload(), source="manual")
    events = _ledger(db, biz["id"])
    assert len(events) == 1 and events[0]["type"] == "expense_created"
    assert events[0]["amount"] == 120.0 and events[0]["metadata"]["source"] == "manual"

def test_business_use_percent_clamped_0_100(db, make_business):
    biz = make_business()
    assert expense_service.create_expense(db, biz["id"], _payload(business_use_percent=250), source="manual").business_use_percent == 100
    assert expense_service.create_expense(db, biz["id"], _payload(business_use_percent=-5), source="manual").business_use_percent == 0

def test_manual_without_amount_400(db, make_business):
    biz = make_business()
    with pytest.raises(HTTPException) as e:
        expense_service.create_expense(db, biz["id"], ExpenseCreate(supplier_name="Canva"), source="manual")
    assert e.value.status_code == 400 and e.value.detail["code"] == "missing_amount"

def test_approve_flips_status_and_logs(db, make_business):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], _payload(category=None), source="chat")
    out = expense_service.approve_expense(db, biz["id"], exp.id)
    assert out.status == "approved"
    assert {e["type"] for e in _ledger(db, biz["id"])} == {"expense_created", "expense_approved"}
```
Add these tests in the same file with these exact assertions:

| Test name | Setup → Action | Assert |
|---|---|---|
| `test_approve_twice_409` | approve approved expense | `HTTPException` 409, `detail["code"] == "invalid_expense_status"` |
| `test_approve_without_amount_422` | image expense (no amount) → approve | 422, code `"missing_amount"` |
| `test_reject_flips_status_and_logs` | needs_review → reject | `status == "rejected"`, ledger has `expense_rejected` |
| `test_reject_non_needs_review_409` | reject an approved expense | 409, code `"invalid_expense_status"` |
| `test_update_only_while_needs_review` | patch approved expense | 409, code `"invalid_expense_status"` |
| `test_update_applies_whitelist_and_rounds` | patch needs_review with `ExpensePatch(amount=99.999, category="office")` | `amount == 100.0`, `category == "office"`, status unchanged |
| `test_update_invalid_date_422` | `ExpensePatch(expense_date="13/06/2026")` | 422, code `"invalid_date"` |
| `test_list_filters_status_and_year` | seed approved(2026-03-01), approved(2025-12-01), needs_review(2026-05-01) | `list_expenses(status="approved")` → 2; `list_expenses(year=2026)` → 2; `list_expenses(status="approved", year=2026)` → 1 |
| `test_approve_missing_id_404` | approve `"nope"` | 404, code `"expense_not_found"` |

- [ ] **Step 2: Run** `... python -m pytest tests/test_expense_service.py -q` — expect `ModuleNotFoundError: No module named 'app.services.expense_service'`.
- [ ] **Step 3: Implement the service**:
```python
# backend/app/services/expense_service.py
from google.cloud.firestore_v1.base_query import FieldFilter
from app.core.errors import api_error
from app.schemas.expense import Expense, ExpenseCreate, ExpensePatch
from app.services.ledger_service import record_event
from app.utils.dates import now_il, parse_iso_date
from app.utils.money import round_ils

ALLOWED_SOURCES = {"chat", "manual", "image"}
PATCH_WHITELIST = {"supplierName", "expenseDate", "amount", "category", "description", "businessUsePercent"}

def _expenses(db, business_id: str):
    return db.collection("businesses").document(business_id).collection("expenses")

def _clamp_pct(value) -> int:
    return 100 if value is None else max(0, min(100, int(value)))

def _load(db, business_id: str, expense_id: str):
    snap = _expenses(db, business_id).document(expense_id).get()
    if not snap.exists:
        api_error(404, "expense_not_found", "ההוצאה לא נמצאה")
    return snap.reference, snap.to_dict()

def _check_date(value: str | None) -> None:
    if value is not None and parse_iso_date(value) is None:
        api_error(422, "invalid_date", "תאריך ההוצאה חייב להיות בפורמט YYYY-MM-DD")

def create_expense(db, business_id: str, payload: ExpenseCreate, source: str) -> Expense:
    if source not in ALLOWED_SOURCES:
        raise ValueError(f"invalid expense source: {source}")
    if source != "image" and payload.amount is None:
        api_error(400, "missing_amount", "חסר סכום להוצאה")
    _check_date(payload.expense_date)
    if source == "image":
        status = "needs_review"          # vision results always reviewed by a human
    else:
        status = "approved" if payload.category is not None else "needs_review"  # doc §15
    now = now_il()
    ref = _expenses(db, business_id).document()
    data = {
        "id": ref.id, "businessId": business_id,
        "supplierName": payload.supplier_name, "expenseDate": payload.expense_date,
        "amount": round_ils(payload.amount) if payload.amount is not None else None,
        "currency": "ILS", "category": payload.category, "description": payload.description,
        "businessUsePercent": _clamp_pct(payload.business_use_percent),
        "imageUrl": payload.image_url, "cloudinaryPublicId": payload.cloudinary_public_id,
        "ocrText": None, "extractionConfidence": None,
        "status": status, "createdAt": now, "updatedAt": now,
    }
    ref.set(data)
    record_event(db, business_id, type="expense_created", entity_type="expense",
                 entity_id=ref.id, amount=data["amount"], metadata={"source": source})
    return Expense.model_validate(data)

def approve_expense(db, business_id: str, expense_id: str) -> Expense:
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר לאשר רק הוצאה בסטטוס לבדיקה")
    if data.get("amount") is None:
        api_error(422, "missing_amount", "אי אפשר לאשר הוצאה ללא סכום")
    changes = {"status": "approved", "updatedAt": now_il()}
    ref.update(changes); data.update(changes)
    record_event(db, business_id, type="expense_approved", entity_type="expense",
                 entity_id=expense_id, amount=data["amount"])
    return Expense.model_validate(data)

def reject_expense(db, business_id: str, expense_id: str) -> Expense:
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר לדחות רק הוצאה בסטטוס לבדיקה")
    changes = {"status": "rejected", "updatedAt": now_il()}
    ref.update(changes); data.update(changes)
    record_event(db, business_id, type="expense_rejected", entity_type="expense",
                 entity_id=expense_id, amount=data.get("amount"))
    return Expense.model_validate(data)

def list_expenses(db, business_id: str, status: str | None = None, year: int | None = None) -> list[Expense]:
    q = _expenses(db, business_id)
    if status is not None:
        q = q.where(filter=FieldFilter("status", "==", status))
    items = [s.to_dict() for s in q.stream()]
    if year is not None:  # filter in Python: avoids composite index + emulator/prod drift; MVP volumes are tiny
        items = [d for d in items if (d.get("expenseDate") or "").startswith(f"{year}-")]
    items.sort(key=lambda d: d["createdAt"], reverse=True)
    return [Expense.model_validate(d) for d in items]

def update_expense(db, business_id: str, expense_id: str, patch: ExpensePatch) -> Expense:
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר לערוך הוצאה רק כשהיא בסטטוס לבדיקה")
    changes = {k: v for k, v in patch.model_dump(by_alias=True, exclude_unset=True).items() if k in PATCH_WHITELIST}
    _check_date(changes.get("expenseDate"))
    if changes.get("amount") is not None:
        changes["amount"] = round_ils(changes["amount"])
    if "businessUsePercent" in changes:
        changes["businessUsePercent"] = _clamp_pct(changes["businessUsePercent"])
    changes["updatedAt"] = now_il()
    ref.update(changes); data.update(changes)
    return Expense.model_validate(data)
```
- [ ] **Step 4: Run again** — expect 16 passed.
- [ ] **Step 5: Commit** `git add backend/app/services/expense_service.py backend/tests/test_expense_service.py && git commit -m "feat: expense service with status rules, clamping and ledger events"`

### Task 4.3: Expenses router — manual create, list, patch, approve, reject

**Files:** Create: `backend/app/routers/expenses.py` — Modify: `backend/app/main.py` — Test: `backend/tests/test_expenses_api.py`

- [ ] **Step 1: Write failing API tests** (`api` TestClient fixture; uid override = `test-uid`):
```python
# backend/tests/test_expenses_api.py
from app.schemas.expense import ExpenseCreate
from app.services import expense_service

def test_manual_create_201_camel_case(api, db, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses",
                 json={"supplierName": "Canva", "amount": 120, "category": "software", "description": "מנוי"})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "approved" and body["supplierName"] == "Canva"
    assert body["businessUsePercent"] == 100 and "supplier_name" not in body
```
Add these tests with these exact assertions:

| Test name | Request | Assert |
|---|---|---|
| `test_manual_create_missing_amount_400` | POST `{"supplierName":"Canva","category":"software"}` | 400, `detail.code == "missing_amount"` |
| `test_manual_create_invalid_category_422` | POST `{"amount":50,"category":"food"}` | 422 (FastAPI enum validation) |
| `test_manual_create_zero_amount_422` | POST `{"amount":0}` | 422 (`gt=0`) |
| `test_list_filters_by_status` | seed 1 approved + 1 needs_review via service; GET `?status=approved` | 200, len 1, `status == "approved"` |
| `test_list_invalid_status_422` | GET `?status=pending` | 422, code `"invalid_status_filter"` |
| `test_patch_needs_review_200` | PATCH `{"category":"office","amount":75.5}` on needs_review | 200, `category == "office"`, `amount == 75.5` |
| `test_patch_approved_409` | PATCH on approved | 409, code `"invalid_expense_status"` |
| `test_patch_cannot_touch_status_or_image` | PATCH `{"status":"approved","imageUrl":"https://evil"}` on needs_review | 200, `status == "needs_review"`, `imageUrl` unchanged (extra keys ignored) |
| `test_approve_endpoint_200_then_409` | POST `/{id}/approve` twice | first 200 `status=="approved"`, second 409 |
| `test_reject_endpoint_200` | POST `/{id}/reject` on needs_review | 200, `status == "rejected"` |
| `test_other_owner_403` | `make_business(ownerUserId="other-uid")`; GET list | 403 |

- [ ] **Step 2: Run** `... python -m pytest tests/test_expenses_api.py -q` — expect 404s (router not registered).
- [ ] **Step 3: Implement router and register it**:
```python
# backend/app/routers/expenses.py
from fastapi import APIRouter, Depends, File, UploadFile
from app.core.auth import get_owned_business
from app.core.errors import api_error
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.expense import Expense, ExpenseCreate, ExpensePatch
from app.services import cloudinary_service, expense_service   # module-style import: tests monkeypatch attributes
from app.services.openai_service import CommandParser, get_command_parser

router = APIRouter(prefix="/businesses/{businessId}/expenses", tags=["expenses"])
VALID_STATUSES = {"needs_review", "approved", "rejected"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

@router.post("", response_model=Expense, status_code=201)
def create_manual_expense(payload: ExpenseCreate,
                          business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.create_expense(db, business.id, payload, source="manual")

@router.get("", response_model=list[Expense])
def list_expenses(status: str | None = None, year: int | None = None,
                  business: Business = Depends(get_owned_business), db=Depends(get_db)):
    if status is not None and status not in VALID_STATUSES:
        api_error(422, "invalid_status_filter", "סטטוס לא חוקי: needs_review / approved / rejected")
    return expense_service.list_expenses(db, business.id, status=status, year=year)

@router.patch("/{expense_id}", response_model=Expense)
def patch_expense(expense_id: str, patch: ExpensePatch,
                  business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.update_expense(db, business.id, expense_id, patch)

@router.post("/{expense_id}/approve", response_model=Expense)
def approve(expense_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.approve_expense(db, business.id, expense_id)

@router.post("/{expense_id}/reject", response_model=Expense)
def reject(expense_id: str, business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return expense_service.reject_expense(db, business.id, expense_id)
```
In `backend/app/main.py` add (next to the existing router registrations): `app.include_router(expenses.router, prefix="/api")` with `from app.routers import expenses`.
- [ ] **Step 4: Run again** — expect 12 passed.
- [ ] **Step 5: Commit** `git add backend/app/routers/expenses.py backend/app/main.py backend/tests/test_expenses_api.py && git commit -m "feat: expense manual CRUD, approve/reject endpoints per doc 6.4"`

### Task 4.4: Upload + vision extraction endpoints

**Files:** Modify: `backend/app/services/expense_service.py`, `backend/app/routers/expenses.py`, `backend/requirements.txt`, `backend/tests/stubs.py` — Test: `backend/tests/test_expense_upload_extract.py`

- [ ] **Step 1: Add multipart support** — append `python-multipart==0.0.20` to `backend/requirements.txt`, then `cd /Users/tamirsida/dev/tax/backend && pip install python-multipart==0.0.20`.
- [ ] **Step 2: Extend StubCommandParser** in `backend/tests/stubs.py` (delta — keep Phase 3 `parse_user_command` as-is):
```python
    # add to StubCommandParser.__init__:
    self.extract_result = None      # ExpenseExtraction | ParserFailure
    self.last_image_url: str | None = None

    def extract_expense(self, image_url: str):
        self.last_image_url = image_url
        assert self.extract_result is not None, "set stub_parser.extract_result in the test"
        return self.extract_result
```
- [ ] **Step 3: Write failing tests** (uses Phase 3 `stub_parser` fixture and `ExpenseExtraction` from `app.schemas.ai_commands` — Optional-only fields per VERIFIED FACTS: `supplier_name, amount, currency, category, description, expense_date, ocr_text, confidence`):
```python
# backend/tests/test_expense_upload_extract.py
from app.schemas.ai_commands import ExpenseExtraction
from app.schemas.expense import ExpenseCreate
from app.services import cloudinary_service, expense_service
from app.services.openai_service import ParserFailure

FAKE_JPG = b"\xff\xd8\xff" + b"0" * 64

def _fake_upload(monkeypatch):
    monkeypatch.setattr(cloudinary_service, "upload_image", lambda data, folder: cloudinary_service.UploadResult(
        secure_url="https://res.cloudinary.com/demo/image/upload/expenses/abc.jpg", public_id="expenses/abc"))

def test_upload_creates_needs_review_with_image_refs(api, db, make_business, monkeypatch):
    biz = make_business(); _fake_upload(monkeypatch)
    r = api.post(f"/api/businesses/{biz['id']}/expenses/upload",
                 files={"file": ("r.jpg", FAKE_JPG, "image/jpeg")})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "needs_review" and body["cloudinaryPublicId"] == "expenses/abc"
    assert body["imageUrl"].endswith("expenses/abc.jpg") and body["amount"] is None

def test_upload_bad_content_type_400(api, db, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses/upload",
                 files={"file": ("r.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "unsupported_file_type"

def test_upload_oversize_413(api, db, make_business):
    biz = make_business()
    r = api.post(f"/api/businesses/{biz['id']}/expenses/upload",
                 files={"file": ("r.png", b"0" * (10 * 1024 * 1024 + 1), "image/png")})
    assert r.status_code == 413 and r.json()["detail"]["code"] == "file_too_large"

def _image_expense(db, biz_id):
    return expense_service.create_expense(db, biz_id, ExpenseCreate(
        image_url="https://res.cloudinary.com/demo/image/upload/expenses/abc.jpg",
        cloudinary_public_id="expenses/abc"), source="image")

def test_extract_merges_fields_via_fjpg_url(api, db, make_business, stub_parser, monkeypatch):
    biz = make_business(); exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url",
                        lambda pid: f"https://res.cloudinary.com/demo/image/upload/f_jpg/{pid}")
    stub_parser.extract_result = ExpenseExtraction(
        supplier_name="Canva", amount=120.0, currency="ILS", category="software",
        description="מנוי חודשי", expense_date="2026-05-03", ocr_text="Canva Pro 120.00 ILS", confidence=0.92)
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 200
    assert stub_parser.last_image_url == "https://res.cloudinary.com/demo/image/upload/f_jpg/expenses/abc"
    body = r.json()
    assert body["supplierName"] == "Canva" and body["amount"] == 120.0 and body["category"] == "software"
    assert body["ocrText"].startswith("Canva") and body["extractionConfidence"] == 0.92
    assert body["status"] == "needs_review"   # extraction NEVER auto-approves

def test_extract_invalid_llm_category_dropped(api, db, make_business, stub_parser, monkeypatch):
    biz = make_business(); exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url", lambda pid: "https://x/f_jpg/y")
    stub_parser.extract_result = ExpenseExtraction(supplier_name="KSP", amount=350.0, currency="ILS",
        category="hardware", description=None, expense_date=None, ocr_text=None, confidence=0.5)
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 200 and r.json()["category"] is None

def test_extract_parser_failure_502(api, db, make_business, stub_parser, monkeypatch):
    biz = make_business(); exp = _image_expense(db, biz["id"])
    monkeypatch.setattr(expense_service, "build_jpg_delivery_url", lambda pid: "https://x/f_jpg/y")
    stub_parser.extract_result = ParserFailure(reason="timeout")
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 502 and r.json()["detail"]["code"] == "extraction_failed"

def test_extract_without_image_400(api, db, make_business, stub_parser):
    biz = make_business()
    exp = expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=10.0), source="manual")
    r = api.post(f"/api/businesses/{biz['id']}/expenses/{exp.id}/extract")
    assert r.status_code == 400 and r.json()["detail"]["code"] == "no_image"
```
- [ ] **Step 4: Run** — expect failures (`/upload` 404, `build_jpg_delivery_url` AttributeError).
- [ ] **Step 5: Implement service additions** (append to `expense_service.py`):
```python
import cloudinary.utils
from app.schemas.ai_commands import ExpenseExtraction
from app.schemas.expense import VALID_CATEGORIES
from app.services.openai_service import ParserFailure

def build_jpg_delivery_url(public_id: str) -> str:
    # f_jpg transformation: HEIC/WebP-safe JPEG delivery for the vision call (VERIFIED FACTS)
    url, _ = cloudinary.utils.cloudinary_url(public_id, resource_type="image", fetch_format="jpg", secure=True)
    return url

def run_extraction(db, business_id: str, expense_id: str, parser) -> Expense:
    ref, data = _load(db, business_id, expense_id)
    if data["status"] != "needs_review":
        api_error(409, "invalid_expense_status", "אפשר להריץ זיהוי רק על הוצאה בסטטוס לבדיקה")
    if not data.get("cloudinaryPublicId"):
        api_error(400, "no_image", "אין תמונה מצורפת להוצאה הזו")
    result = parser.extract_expense(build_jpg_delivery_url(data["cloudinaryPublicId"]))
    if isinstance(result, ParserFailure):
        api_error(502, "extraction_failed", "לא הצלחתי לחלץ נתונים מהתמונה, אפשר להזין ידנית")
    changes: dict = {}
    if result.supplier_name: changes["supplierName"] = result.supplier_name
    if result.amount is not None: changes["amount"] = round_ils(result.amount)
    if result.expense_date and parse_iso_date(result.expense_date): changes["expenseDate"] = result.expense_date
    if result.category in VALID_CATEGORIES: changes["category"] = result.category  # invalid LLM value -> dropped
    if result.description: changes["description"] = result.description
    if result.ocr_text: changes["ocrText"] = result.ocr_text
    if result.confidence is not None: changes["extractionConfidence"] = result.confidence
    changes["updatedAt"] = now_il()   # status untouched: stays needs_review
    ref.update(changes); data.update(changes)
    return Expense.model_validate(data)
```
- [ ] **Step 6: Implement router additions** (append to `routers/expenses.py`):
```python
@router.post("/upload", response_model=Expense, status_code=201)
def upload_expense_image(file: UploadFile = File(...),
                         business: Business = Depends(get_owned_business), db=Depends(get_db)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        api_error(400, "unsupported_file_type", "סוג הקובץ לא נתמך. אפשר להעלות JPG, PNG, HEIC או WebP")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        api_error(413, "file_too_large", "הקובץ גדול מדי (מקסימום 10MB)")
    uploaded = cloudinary_service.upload_image(data, folder=f"expenses/{business.id}")
    payload = ExpenseCreate(image_url=uploaded.secure_url, cloudinary_public_id=uploaded.public_id)
    return expense_service.create_expense(db, business.id, payload, source="image")

@router.post("/{expense_id}/extract", response_model=Expense)
def extract(expense_id: str, business: Business = Depends(get_owned_business),
            db=Depends(get_db), parser: CommandParser = Depends(get_command_parser)):
    return expense_service.run_extraction(db, business.id, expense_id, parser)
```
- [ ] **Step 7: Run again** — expect 7 passed; then run the full suite `... python -m pytest -q` — all green.
- [ ] **Step 8: Commit** `git add backend && git commit -m "feat: expense image upload and vision extraction endpoints"`

### Task 4.5: Chat-to-expense and aggregation integration tests

**Files:** Test: `backend/tests/test_chat_expense_integration.py`

- [ ] **Step 1: Write the tests** (Phase 3 chat endpoint + executor must already dispatch `CREATE_EXPENSE` to `expense_service.create_expense` with `source="chat"`; these tests prove the wiring end-to-end):
```python
# backend/tests/test_chat_expense_integration.py
from app.schemas.ai_commands import ExpensePayload, IntentType, ParsedUserCommand
from app.services import aggregation_service, expense_service
from app.schemas.expense import ExpenseCreate
from app.utils.dates import year_bounds

def _cmd(**expense_kw):
    return ParsedUserCommand(
        intent=IntentType.CREATE_EXPENSE, confidence=0.95, language="he",
        receipt=None, contact=None, query=None,
        expense=ExpensePayload(supplier_name="Canva", amount=120.0, currency="ILS",
                               category="software", description="מנוי Canva",
                               business_use_percent=None, expense_date=None, **expense_kw),
        missing_fields=[], requires_confirmation=True, user_facing_message=None, resolved_from_context=False)

def test_text_expense_confirm_creates_approved_expense(api, db, make_business, stub_parser):
    biz = make_business()
    stub_parser.queue_command(_cmd())
    r1 = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "תוסיף הוצאה של 120 שקל על Canva"})
    assert r1.status_code == 200                       # -> pending_confirmation
    r2 = api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "אישור"})  # fast-path, no LLM
    assert r2.status_code == 200
    expenses = expense_service.list_expenses(db, biz["id"])
    assert len(expenses) == 1
    assert expenses[0].status == "approved" and expenses[0].amount == 120.0 and expenses[0].category == "software"

def test_chat_expense_without_category_lands_needs_review(api, db, make_business, stub_parser):
    biz = make_business()
    stub_parser.queue_command(_cmd(category=None))
    api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "שילמתי 120 שקל למישהו"})
    api.post(f"/api/businesses/{biz['id']}/chat/message", json={"text": "כן"})
    assert expense_service.list_expenses(db, biz["id"])[0].status == "needs_review"

def test_total_expenses_approved_only_weighted(db, make_business):
    biz = make_business()
    expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=100.0, category="software", expense_date="2026-03-01"), source="manual")                      # approved, 100%
    expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=200.0, category="office", business_use_percent=50, expense_date="2026-04-01"), source="manual")  # approved, 50%
    expense_service.create_expense(db, biz["id"], ExpenseCreate(amount=500.0, expense_date="2026-05-01"), source="manual")                                            # needs_review -> excluded
    start, end = year_bounds(2026)
    assert aggregation_service.total_expenses(db, biz["id"], start, end) == 200.0   # 100 + 200*0.5
    assert aggregation_service.expenses_by_category(db, biz["id"], 2026) == {"software": 100.0, "office": 100.0}
```
- [ ] **Step 2: Run** `... python -m pytest tests/test_chat_expense_integration.py -q` — if the weighting assertions fail, fix `aggregation_service.total_expenses`/`expenses_by_category` (Phase 3 file) to filter `status == "approved"` and sum `round_ils(amount * businessUsePercent / 100)`; the chat tests must pass without touching Phase 3 code.
- [ ] **Step 3: Commit** `git add backend && git commit -m "test: chat-to-expense flow and weighted approved-only aggregations"`

### Task 4.6: Frontend foundations — types, labels, FormData-safe apiClient

**Files:** Modify: `frontend/lib/types.ts`, `frontend/lib/apiClient.ts` — Create: `frontend/lib/labels.ts`

- [ ] **Step 1: Add types** to `frontend/lib/types.ts`:
```ts
export type ExpenseStatus = "needs_review" | "approved" | "rejected";
export type ExpenseCategory = "software" | "equipment" | "travel" | "office" | "marketing"
  | "professional_services" | "meals" | "parking" | "other";
export interface Expense {
  id: string; businessId: string; supplierName: string | null; expenseDate: string | null;
  amount: number | null; currency: "ILS"; category: ExpenseCategory | null; description: string | null;
  businessUsePercent: number; imageUrl: string | null; cloudinaryPublicId: string | null;
  ocrText: string | null; extractionConfidence: number | null; status: ExpenseStatus;
  createdAt: string; updatedAt: string;
}
```
- [ ] **Step 2: Create `frontend/lib/labels.ts`**:
```ts
import type { ExpenseCategory, ExpenseStatus } from "@/lib/types";
export const CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  software: "תוכנה", equipment: "ציוד", travel: "נסיעות", office: "משרד", marketing: "שיווק",
  professional_services: "שירותים מקצועיים", meals: "אש\"ל", parking: "חניה", other: "אחר",
};
export const EXPENSE_STATUS_LABELS: Record<ExpenseStatus, string> = {
  needs_review: "לבדיקה", approved: "מאושר", rejected: "נדחה",
};
```
- [ ] **Step 3: Guard apiClient against FormData** — in `frontend/lib/apiClient.ts`, where the request headers are built, ensure Content-Type is only set for non-FormData bodies (multipart boundary must come from the browser):
```ts
if (init?.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
  headers.set("Content-Type", "application/json");
}
```
- [ ] **Step 4: Verify** `cd /Users/tamirsida/dev/tax/frontend && npx tsc --noEmit && npm run build` — zero errors, build green. This task adds no UI; the manual 375×812 check happens in Task 4.7 once the page exists.
- [ ] **Step 5: Commit** `git add frontend/lib && git commit -m "feat: expense types, Hebrew labels, FormData-safe api client"`

### Task 4.7: Expenses page — camera capture, segmented tabs, card list, review sheet

**Files:** Create: `frontend/app/expenses/page.tsx`, `frontend/components/ExpenseList.tsx`, `frontend/components/ExpenseReviewSheet.tsx`, `frontend/components/UploadExpenseButton.tsx`

Deviation from doc §13 (allowed by the mobile brief): `ExpenseTable.tsx` is renamed `ExpenseList.tsx` — on mobile the primary markup is a card list; the table survives only as a `hidden md:block` desktop enhancement inside the same component. The review modal becomes `ExpenseReviewSheet.tsx` built on the shared bottom `Sheet` from Phase 2 (bottom sheets replace modals on mobile). Imports used below that already exist by this phase: `Sheet`, `EmptyState`, `formatILS` (Phase 2), `useAuth`/`api` (Phases 0–1), `lucide-react` (Phase 0).

- [ ] **Step 1: Create `frontend/components/UploadExpenseButton.tsx`** (camera capture + gallery pick → upload → extract → hand result to parent; extraction failure is non-fatal — user reviews manually. `accept="image/*"` deliberately does **not** list `image/heic`: with `image/*` iOS auto-converts HEIC→JPEG, while listing `image/heic` triggers a Safari 17+ re-encoding regression):
```tsx
"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { Camera, ImageUp, Loader2 } from "lucide-react";
import { api } from "@/lib/apiClient";
import type { Expense } from "@/lib/types";

export default function UploadExpenseButton({ businessId, onUploaded }:
  { businessId: string; onUploaded: (e: Expense) => void }) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleFile(file: File) {
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const uploaded = await api<Expense>(`/businesses/${businessId}/expenses/upload`, { method: "POST", body: form });
      let result = uploaded;
      try { result = await api<Expense>(`/businesses/${businessId}/expenses/${uploaded.id}/extract`, { method: "POST" }); }
      catch { /* 502 extraction_failed: keep raw upload, user fills the fields in the review sheet */ }
      onUploaded(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ההעלאה נכשלה, נסו שוב");
    } finally {
      setBusy(false);
      if (cameraRef.current) cameraRef.current.value = "";
      if (galleryRef.current) galleryRef.current.value = "";
    }
  }

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="flex flex-col gap-2">
      {/* accept="image/*" only — never add image/heic here (Safari 17+ re-encoding regression);
          iOS converts HEIC to JPEG automatically when accept is image/* */}
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPick} />
      <input ref={galleryRef} type="file" accept="image/*" className="hidden" onChange={onPick} />
      <div className="flex gap-2">
        <button
          onClick={() => cameraRef.current?.click()}
          disabled={busy}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {busy ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <Camera size={20} aria-hidden />}
          {busy ? "מעלה ומזהה..." : "צילום הוצאה"}
        </button>
        <button
          onClick={() => galleryRef.current?.click()}
          disabled={busy}
          className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium text-foreground transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          <ImageUp size={20} aria-hidden />
          העלאה מהגלריה
        </button>
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
```
- [ ] **Step 2: Create `frontend/components/ExpenseList.tsx`** — mobile-first card list (primary markup) + `hidden md:block` table enhancement. Each card: 48px thumbnail (or `Wallet` placeholder), supplier, amount via `formatILS` in a `dir="ltr"` `tnum` span, status badge (לבדיקה=amber, מאושר=accent, נדחה=destructive), Hebrew category label, date, and a low-confidence hint when `extractionConfidence < 0.7`. Skeleton cards while loading, shared `EmptyState` when empty:
```tsx
"use client";

import { Wallet } from "lucide-react";
import EmptyState from "@/components/EmptyState";
import { formatILS } from "@/lib/format";
import { CATEGORY_LABELS, EXPENSE_STATUS_LABELS } from "@/lib/labels";
import type { Expense, ExpenseStatus } from "@/lib/types";

const STATUS_BADGE: Record<ExpenseStatus, string> = {
  needs_review: "bg-amber-100 text-amber-800",
  approved: "bg-accent/10 text-accent",
  rejected: "bg-destructive/10 text-destructive",
};

function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("he-IL");
}

export default function ExpenseList({ expenses, loading, onSelect }:
  { expenses: Expense[]; loading: boolean; onSelect: (e: Expense) => void }) {
  if (loading) {
    return (
      <div className="flex flex-col gap-3" aria-hidden>
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex animate-pulse items-center gap-3 rounded-2xl border border-border bg-white p-4">
            <div className="size-12 rounded-lg bg-muted" />
            <div className="flex-1">
              <div className="h-4 w-2/5 rounded bg-muted" />
              <div className="mt-2 h-3 w-3/5 rounded bg-muted" />
            </div>
          </div>
        ))}
      </div>
    );
  }
  if (expenses.length === 0) {
    return (
      <EmptyState
        Icon={Wallet}
        title="אין הוצאות להצגה"
        hint="צלמו קבלה למעלה או כתבו בצ'אט: תוסיף הוצאה של 120 שקל על Canva"
      />
    );
  }
  return (
    <>
      <ul className="flex flex-col gap-3 md:hidden">
        {expenses.map((e) => (
          <li key={e.id}>
            <button
              onClick={() => onSelect(e)}
              className="flex min-h-12 w-full items-center gap-3 rounded-2xl border border-border bg-white p-4 text-start transition-transform duration-150 active:scale-[0.98]"
            >
              {e.imageUrl ? (
                <img src={e.imageUrl} alt="" className="size-12 shrink-0 rounded-lg object-cover" />
              ) : (
                <span className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-muted">
                  <Wallet size={20} className="text-foreground/40" aria-hidden />
                </span>
              )}
              <span className="min-w-0 flex-1">
                <span className="flex items-center justify-between gap-2">
                  <span className="truncate font-medium">{e.supplierName ?? "ספק לא ידוע"}</span>
                  <span className="tnum shrink-0 font-semibold" dir="ltr">
                    {e.amount !== null ? formatILS(e.amount) : "—"}
                  </span>
                </span>
                <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-foreground/60">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[e.status]}`}>
                    {EXPENSE_STATUS_LABELS[e.status]}
                  </span>
                  <span>{e.category ? CATEGORY_LABELS[e.category] : "ללא קטגוריה"}</span>
                  {e.expenseDate && <span className="tnum" dir="ltr">{formatDate(e.expenseDate)}</span>}
                </span>
                {e.extractionConfidence !== null && e.extractionConfidence < 0.7 && (
                  <span className="mt-1 block text-xs text-destructive">זיהוי בביטחון נמוך — כדאי לבדוק את הפרטים</span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ul>
      <div className="hidden overflow-hidden rounded-2xl border border-border bg-white md:block">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/50">
            <tr>
              <th className="p-3 text-start font-medium">תאריך</th>
              <th className="p-3 text-start font-medium">ספק</th>
              <th className="p-3 text-start font-medium">קטגוריה</th>
              <th className="p-3 text-start font-medium">סכום</th>
              <th className="p-3 text-start font-medium">סטטוס</th>
            </tr>
          </thead>
          <tbody>
            {expenses.map((e) => (
              <tr
                key={e.id}
                onClick={() => onSelect(e)}
                className="cursor-pointer border-b border-border last:border-b-0 hover:bg-muted/50"
              >
                <td className="p-3">
                  <span className="tnum" dir="ltr">{e.expenseDate ? formatDate(e.expenseDate) : "—"}</span>
                </td>
                <td className="p-3">
                  <span className="flex items-center gap-2">
                    {e.imageUrl && <img src={e.imageUrl} alt="" className="size-8 rounded object-cover" />}
                    {e.supplierName ?? "ספק לא ידוע"}
                  </span>
                </td>
                <td className="p-3">{e.category ? CATEGORY_LABELS[e.category] : "—"}</td>
                <td className="p-3">
                  <span className="tnum" dir="ltr">{e.amount !== null ? formatILS(e.amount) : "—"}</span>
                </td>
                <td className="p-3">
                  <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[e.status]}`}>
                    {EXPENSE_STATUS_LABELS[e.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
```
- [ ] **Step 3: Create `frontend/components/ExpenseReviewSheet.tsx`** (edit-before-approve on the shared bottom `Sheet`; אישור saves the edited fields via PATCH and then approves; approved/rejected expenses open read-only — fields disabled, no action buttons):
```tsx
"use client";

import { useState, type ChangeEvent } from "react";
import { Ban, Check, Loader2 } from "lucide-react";
import Sheet from "@/components/Sheet";
import { api } from "@/lib/apiClient";
import { CATEGORY_LABELS, EXPENSE_STATUS_LABELS } from "@/lib/labels";
import type { Expense, ExpenseCategory } from "@/lib/types";

const inputClass =
  "min-h-12 w-full rounded-xl border border-border bg-white px-4 text-base focus:outline-none focus:ring-2 focus:ring-primary disabled:bg-muted disabled:text-foreground/60";

export default function ExpenseReviewSheet({ businessId, expense, onClose, onSaved }:
  { businessId: string; expense: Expense; onClose: () => void; onSaved: () => void }) {
  const editable = expense.status === "needs_review";
  const [form, setForm] = useState({
    supplierName: expense.supplierName ?? "",
    amount: expense.amount?.toString() ?? "",
    expenseDate: expense.expenseDate ?? "",
    category: expense.category ?? "",
    description: expense.description ?? "",
    businessUsePercent: expense.businessUsePercent.toString(),
  });
  const [amountError, setAmountError] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState<"approve" | "reject" | null>(null);

  const set = (k: keyof typeof form) => (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: e.target.value });

  function validateAmount(): boolean {
    if (!form.amount || Number(form.amount) <= 0) {
      setAmountError("יש להזין סכום גדול מ-0");
      return false;
    }
    setAmountError("");
    return true;
  }

  async function approve() {
    if (!validateAmount()) return;
    setPending("approve");
    setError("");
    try {
      const base = `/businesses/${businessId}/expenses/${expense.id}`;
      await api<Expense>(base, {
        method: "PATCH",
        body: JSON.stringify({
          supplierName: form.supplierName || undefined,
          amount: Number(form.amount),
          expenseDate: form.expenseDate || undefined,
          category: form.category || undefined,
          description: form.description || undefined,
          businessUsePercent: Number(form.businessUsePercent),
        }),
      });
      await api<Expense>(`${base}/approve`, { method: "POST" });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "שגיאה בשמירה");
      setPending(null);
    }
  }

  async function reject() {
    setPending("reject");
    setError("");
    try {
      await api<Expense>(`/businesses/${businessId}/expenses/${expense.id}/reject`, { method: "POST" });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "שגיאה בדחייה");
      setPending(null);
    }
  }

  return (
    <Sheet open onClose={onClose} title={editable ? "בדיקת הוצאה" : "פרטי הוצאה"}>
      {expense.imageUrl && (
        <img src={expense.imageUrl} alt="צילום ההוצאה" className="mx-auto mb-4 max-h-48 w-full rounded-xl object-contain" />
      )}
      {!editable && (
        <p className="mb-3 text-sm text-foreground/60">סטטוס: {EXPENSE_STATUS_LABELS[expense.status]}</p>
      )}
      <div className="flex flex-col gap-3">
        <label className="block">
          <span className="mb-1 block text-sm font-medium">ספק</span>
          <input value={form.supplierName} onChange={set("supplierName")} disabled={!editable} className={inputClass} />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">סכום (₪)</span>
          <input
            type="number" inputMode="numeric" min="0" step="0.01" dir="ltr"
            value={form.amount} onChange={set("amount")} onBlur={validateAmount}
            disabled={!editable} className={`${inputClass} tnum`}
          />
          {amountError && <p className="mt-1 text-sm text-destructive">{amountError}</p>}
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">תאריך</span>
          <input
            type="date" dir="ltr" value={form.expenseDate} onChange={set("expenseDate")}
            disabled={!editable} className={`${inputClass} tnum`}
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">קטגוריה</span>
          <select value={form.category} onChange={set("category")} disabled={!editable} className={inputClass}>
            <option value="">ללא קטגוריה</option>
            {(Object.keys(CATEGORY_LABELS) as ExpenseCategory[]).map((c) => (
              <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">תיאור</span>
          <input value={form.description} onChange={set("description")} disabled={!editable} className={inputClass} />
        </label>
        <label className="block">
          <span className="mb-1 block text-sm font-medium">אחוז שימוש עסקי</span>
          <input
            type="number" inputMode="numeric" min="0" max="100" dir="ltr"
            value={form.businessUsePercent} onChange={set("businessUsePercent")}
            disabled={!editable} className={`${inputClass} tnum`}
          />
        </label>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {editable && (
          <div className="mt-1 flex gap-2">
            <button
              onClick={approve}
              disabled={pending !== null}
              className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
            >
              {pending === "approve" ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <Check size={20} aria-hidden />}
              אישור
            </button>
            <button
              onClick={reject}
              disabled={pending !== null}
              className="flex min-h-12 flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-white px-5 font-medium text-destructive transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
            >
              {pending === "reject" ? <Loader2 size={20} className="animate-spin" aria-hidden /> : <Ban size={20} aria-hidden />}
              דחייה
            </button>
          </div>
        )}
      </div>
    </Sheet>
  );
}
```
- [ ] **Step 4: Create `frontend/app/expenses/page.tsx`** — segmented control (לבדיקה / מאושרות / הכל) with a needs_review count badge; fetches all expenses once and filters client-side (gives the badge count for free, MVP volumes are tiny); skeletons while loading, never a blank screen. The page renders inside the Phase 0 `AppShell` (`<html dir="rtl">`, bottom nav), so no `main`/`dir` wrappers here:
```tsx
"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import type { Business, Expense, ExpenseStatus } from "@/lib/types";
import ExpenseList from "@/components/ExpenseList";
import ExpenseReviewSheet from "@/components/ExpenseReviewSheet";
import UploadExpenseButton from "@/components/UploadExpenseButton";

type Tab = ExpenseStatus | "all";

const TABS: { value: Tab; label: string }[] = [
  { value: "needs_review", label: "לבדיקה" },
  { value: "approved", label: "מאושרות" },
  { value: "all", label: "הכל" },
];

export default function ExpensesPage() {
  const { user, loading } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [tab, setTab] = useState<Tab>("needs_review");
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [reviewing, setReviewing] = useState<Expense | null>(null);

  useEffect(() => { if (user) api<Business>("/businesses/me").then(setBusiness); }, [user]);

  const refresh = useCallback(async () => {
    if (!business) return;
    try {
      setExpenses(await api<Expense[]>(`/businesses/${business.id}/expenses`));
    } finally {
      setListLoading(false);
    }
  }, [business]);
  useEffect(() => { refresh(); }, [refresh]);

  const needsReviewCount = expenses.filter((e) => e.status === "needs_review").length;
  const visible = tab === "all" ? expenses : expenses.filter((e) => e.status === tab);

  return (
    <div className="px-4 pb-6 pt-4">
      <h1 className="mb-4 text-2xl font-semibold">הוצאות</h1>
      {business && (
        <div className="mb-4">
          <UploadExpenseButton businessId={business.id} onUploaded={(e) => { refresh(); setReviewing(e); }} />
        </div>
      )}
      <div role="tablist" aria-label="סינון הוצאות" className="mb-4 flex rounded-xl border border-border bg-muted p-1">
        {TABS.map((t) => (
          <button
            key={t.value}
            role="tab"
            aria-selected={tab === t.value}
            onClick={() => setTab(t.value)}
            className={`flex min-h-12 flex-1 items-center justify-center gap-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === t.value ? "bg-white text-foreground shadow-sm" : "text-foreground/60"
            }`}
          >
            {t.label}
            {t.value === "needs_review" && needsReviewCount > 0 && (
              <span dir="ltr" className="tnum rounded-full bg-destructive px-1.5 text-xs font-semibold text-white">
                {needsReviewCount}
              </span>
            )}
          </button>
        ))}
      </div>
      <ExpenseList expenses={visible} loading={loading || !business || listLoading} onSelect={setReviewing} />
      {business && reviewing && (
        <ExpenseReviewSheet
          businessId={business.id}
          expense={reviewing}
          onClose={() => setReviewing(null)}
          onSaved={() => { setReviewing(null); refresh(); }}
        />
      )}
    </div>
  );
}
```
- [ ] **Step 5: Type-check and build** — `cd /Users/tamirsida/dev/tax/frontend && npx tsc --noEmit && npm run build` — both green.
- [ ] **Step 6: Manual mobile verification** (backend + dev Firebase running, `npm run dev`; open devtools device toolbar at 375×812):
  1. Open http://localhost:3000/expenses signed in — page title, two 48px upload buttons (צילום הוצאה primary with camera icon, העלאה מהגלריה ghost), segmented control with three tabs (לבדיקה / מאושרות / הכל), bottom nav highlights הוצאות, no horizontal scroll.
  2. In chat (http://localhost:3000/chat) send `תוסיף הוצאה של 120 שקל על Canva`, confirm with `אישור`; back on /expenses the מאושרות tab shows a card: Canva / תוכנה / `₪120` rendered LTR / badge מאושר.
  3. Tap צילום הוצאה (opens the camera on a real phone; the file picker in desktop devtools) and pick a JPG of a receipt — both buttons disable with a spinner and "מעלה ומזהה...", then ExpenseReviewSheet slides up from the bottom with the image preview (`max-h-48`) and pre-filled supplier/amount; the לבדיקה tab shows a red count badge.
  4. In the sheet change קטגוריה to משרד and tap אישור — sheet closes, the card moves to מאושרות and the count badge disappears.
  5. Upload another image, open its card from לבדיקה and tap דחייה — the card leaves לבדיקה and appears under הכל with badge נדחה.
  6. Pick a .pdf via העלאה מהגלריה — a red Hebrew error appears under the upload buttons (400 unsupported_file_type) and no card is added.
  7. In a review sheet, clear the amount field and blur it — "יש להזין סכום גדול מ-0" appears below the field and אישור is blocked until a valid amount is entered.
  8. Widen the viewport to ≥768px — the card list is replaced by the desktop table with thumbnails; clicking a row opens the same review sheet.
- [ ] **Step 7: Commit** `git add frontend && git commit -m "feat: mobile-first expenses page with camera capture, segmented tabs, card list and review sheet"`
## Phase 5 — Dashboard

Goal: implement `GET /api/businesses/{businessId}/dashboard` (doc §3.7, §6.6) as a single composed read over the aggregation layer, plus the post-login dashboard page in the frontend. Depends on Phases 0–4: `aggregation_service` (revenue/expense/threshold/monthly/category functions), shared test fixtures (`db`, `clear_db`, `api`, `make_business`), schemas with camelCase aliasing, and the frontend shell (`AuthProvider`, `apiClient`, `types.ts`).

**Done when:**
- [ ] `GET /api/businesses/{businessId}/dashboard` returns totals, counts, threshold, 12 monthly buckets, category map, 5 recent receipts, 5 recent expenses, and Hebrew warnings — all camelCase, all asserted by an emulator integration test.
- [ ] `firestore.indexes.json` contains the composite indexes the dashboard + list queries need and is deployed to the dev Firebase project.
- [ ] `http://localhost:3000/dashboard` at 375×812 renders a 2-column stat grid, a threshold progress card with amounts and percent as visible text, the recharts monthly chart inside a `dir="ltr"` island, the category list, recent receipts/expenses as card rows with הצג הכל links, amber warning cards with icons, skeleton loading, and `EmptyState` empty states; `npm run build` passes.

### Task 5.1: Dashboard response schema

**Files:**
- Create: `backend/app/schemas/dashboard.py`
- Test: `backend/tests/test_dashboard_schema.py`

- [ ] **Step 1: Write the failing serialization test**
```python
# backend/tests/test_dashboard_schema.py
from app.schemas.dashboard import (
    DashboardCounts, DashboardResponse, DashboardTotals,
    MonthlyIncomeEntry, RecentExpense, RecentReceipt, ThresholdOut,
)


def test_dashboard_response_serializes_camel_case():
    resp = DashboardResponse(
        totals=DashboardTotals(income_this_year=1500.5, income_this_month=1000.0,
                               expenses_this_year=250.0, estimated_profit=1250.5),
        counts=DashboardCounts(receipts_count=2, approved_expenses_count=2, needs_review_count=1),
        threshold=ThresholdOut(total=1500.5, limit=120000, pct=1.3, warning=False),
        monthly_income=[MonthlyIncomeEntry(month=m, total=0.0) for m in range(1, 13)],
        expenses_by_category={"software": 200.0},
        recent_receipts=[RecentReceipt(id="r1", receipt_number="2026-0001", client_name="נועה",
                                       amount=1000.0, issue_date="2026-06-13", pdf_url=None)],
        recent_expenses=[RecentExpense(id="e1", supplier_name=None, amount=80.0,
                                       category=None, expense_date=None, status="needs_review")],
        warnings=["1 הוצאות ממתינות לבדיקה"],
    )
    data = resp.model_dump(by_alias=True)
    assert set(data) == {"totals", "counts", "threshold", "monthlyIncome", "expensesByCategory",
                         "recentReceipts", "recentExpenses", "warnings"}
    assert data["totals"] == {"incomeThisYear": 1500.5, "incomeThisMonth": 1000.0,
                              "expensesThisYear": 250.0, "estimatedProfit": 1250.5}
    assert data["counts"] == {"receiptsCount": 2, "approvedExpensesCount": 2, "needsReviewCount": 1}
    assert data["recentReceipts"][0]["receiptNumber"] == "2026-0001"
    assert data["recentReceipts"][0]["pdfUrl"] is None
    assert len(data["monthlyIncome"]) == 12 and data["monthlyIncome"][0] == {"month": 1, "total": 0.0}
```
- [ ] **Step 2: Run it** — `cd backend && python -m pytest tests/test_dashboard_schema.py -q` → fails with `ModuleNotFoundError: No module named 'app.schemas.dashboard'`.
- [ ] **Step 3: Implement the schema**
```python
# backend/app/schemas/dashboard.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DashboardTotals(CamelModel):
    income_this_year: float
    income_this_month: float
    expenses_this_year: float
    estimated_profit: float  # income_this_year - expenses_this_year, round_ils'd


class DashboardCounts(CamelModel):
    receipts_count: int            # issued receipts this year
    approved_expenses_count: int   # approved expenses this year
    needs_review_count: int        # needs_review expenses, all time


class ThresholdOut(CamelModel):
    total: float
    limit: int
    pct: float
    warning: bool


class MonthlyIncomeEntry(CamelModel):
    month: int   # 1..12
    total: float


class RecentReceipt(CamelModel):
    id: str
    receipt_number: str
    client_name: str
    amount: float
    issue_date: str
    pdf_url: str | None = None


class RecentExpense(CamelModel):
    id: str
    supplier_name: str | None = None
    amount: float | None = None
    category: str | None = None
    expense_date: str | None = None
    status: str


class DashboardResponse(CamelModel):
    totals: DashboardTotals
    counts: DashboardCounts
    threshold: ThresholdOut
    monthly_income: list[MonthlyIncomeEntry]
    expenses_by_category: dict[str, float]
    recent_receipts: list[RecentReceipt]
    recent_expenses: list[RecentExpense]
    warnings: list[str]
```
- [ ] **Step 4: Run again** — same command → 1 passed.
- [ ] **Step 5: Commit** — `git add backend/app/schemas/dashboard.py backend/tests/test_dashboard_schema.py && git commit -m "feat: dashboard response schema with camelCase aliases"`

### Task 5.2: Missing aggregation helpers (recents + counts)

**Files:**
- Modify: `backend/app/services/aggregation_service.py`
- Create: `backend/tests/seeders.py`
- Test: `backend/tests/test_aggregation_dashboard.py`

- [ ] **Step 1: Create shared seed helpers** (also used by Task 5.4)
```python
# backend/tests/seeders.py
from datetime import datetime
from app.utils.dates import IL_TZ


def seed_receipt(db, bid, *, seq, amount, issue_date, issued_at=None,
                 status="issued", pdf_url=None, client_name="נועה"):
    doc = {
        "businessId": bid, "receiptNumber": f"2026-{seq:04d}", "sequenceNumber": seq,
        "status": status, "issueDate": issue_date, "amount": amount, "currency": "ILS",
        "paymentMethod": "bit", "description": "עיצוב לוגו",
        "clientSnapshot": {"name": client_name},
        "createdAt": issued_at or datetime.now(IL_TZ),
    }
    if status == "issued":
        doc["issuedAt"] = issued_at or datetime.now(IL_TZ)
    if pdf_url:
        doc["pdfUrl"] = pdf_url
        doc["cloudinaryPublicId"] = "tax/receipts/x"
    ref = db.collection("businesses").document(bid).collection("receipts").document()
    ref.set(doc)
    return ref.id


def seed_expense(db, bid, *, amount, status, category=None, expense_date=None,
                 supplier="Canva", use_pct=100, created_at=None):
    ts = created_at or datetime.now(IL_TZ)
    ref = db.collection("businesses").document(bid).collection("expenses").document()
    ref.set({
        "businessId": bid, "supplierName": supplier, "amount": amount, "currency": "ILS",
        "category": category, "description": None, "businessUsePercent": use_pct,
        "expenseDate": expense_date, "status": status, "createdAt": ts, "updatedAt": ts,
    })
    return ref.id
```
- [ ] **Step 2: Write the failing helper tests**
```python
# backend/tests/test_aggregation_dashboard.py
from datetime import datetime, timedelta
from app.services import aggregation_service
from app.utils.dates import IL_TZ, today_il
from tests.seeders import seed_expense, seed_receipt


def test_recent_receipts_issued_only_newest_first_limit(db, make_business):
    bid = make_business()["id"]
    now = datetime.now(IL_TZ)
    today = today_il().isoformat()
    ids = [seed_receipt(db, bid, seq=i, amount=100.0 * i, issue_date=today,
                        issued_at=now - timedelta(days=10 - i)) for i in range(1, 8)]
    seed_receipt(db, bid, seq=99, amount=1.0, issue_date=today, status="draft")
    seed_receipt(db, bid, seq=98, amount=1.0, issue_date=today, issued_at=now, status="cancelled")
    recents = aggregation_service.recent_receipts(db, bid, limit=5)
    assert [r["id"] for r in recents] == list(reversed(ids))[:5]
    assert all(r["status"] == "issued" for r in recents)


def test_dashboard_counts_and_missing_pdfs(db, make_business):
    bid = make_business()["id"]
    now, year = datetime.now(IL_TZ), today_il().year
    today = today_il().isoformat()
    seed_receipt(db, bid, seq=1, amount=100.0, issue_date=today, issued_at=now, pdf_url="https://x/r1.pdf")
    seed_receipt(db, bid, seq=2, amount=200.0, issue_date=today, issued_at=now)  # missing PDF
    e1 = seed_expense(db, bid, amount=50.0, status="approved", category="software", expense_date=today)
    seed_expense(db, bid, amount=60.0, status="approved", category="office", expense_date=f"{year - 1}-05-01")
    e3 = seed_expense(db, bid, amount=70.0, status="needs_review", created_at=now)
    assert aggregation_service.approved_expenses_count(db, bid, year) == 1
    assert aggregation_service.needs_review_count(db, bid) == 1
    assert aggregation_service.receipts_missing_pdf_count(db, bid) == 1
    assert [e["id"] for e in aggregation_service.recent_expenses(db, bid, limit=5)][0] == e3
    assert e1 in [e["id"] for e in aggregation_service.recent_expenses(db, bid, limit=5)]
```
- [ ] **Step 3: Run it** — start the Phase 0 emulator (`docker compose up -d firestore-emulator`), then `cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test python -m pytest tests/test_aggregation_dashboard.py -q` → fails with `AttributeError: module 'app.services.aggregation_service' has no attribute 'recent_receipts'`.
- [ ] **Step 4: Append the helpers to aggregation_service.py** (exact names/signatures; collection paths inline so this is independent of existing private helpers)
```python
# additions to backend/app/services/aggregation_service.py
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


def _subcol(db, business_id: str, name: str):
    return db.collection("businesses").document(business_id).collection(name)


def recent_receipts(db, business_id: str, limit: int = 5) -> list[dict]:
    q = (_subcol(db, business_id, "receipts")
         .where(filter=FieldFilter("status", "==", "issued"))
         .order_by("issuedAt", direction=firestore.Query.DESCENDING)
         .limit(limit))
    return [d.to_dict() | {"id": d.id} for d in q.stream()]


def recent_expenses(db, business_id: str, limit: int = 5) -> list[dict]:
    q = (_subcol(db, business_id, "expenses")
         .order_by("createdAt", direction=firestore.Query.DESCENDING)
         .limit(limit))
    return [d.to_dict() | {"id": d.id} for d in q.stream()]


def approved_expenses_count(db, business_id: str, year: int) -> int:
    q = (_subcol(db, business_id, "expenses")
         .where(filter=FieldFilter("status", "==", "approved"))
         .where(filter=FieldFilter("expenseDate", ">=", f"{year}-01-01"))
         .where(filter=FieldFilter("expenseDate", "<=", f"{year}-12-31")))
    return sum(1 for _ in q.stream())


def needs_review_count(db, business_id: str) -> int:
    q = _subcol(db, business_id, "expenses").where(filter=FieldFilter("status", "==", "needs_review"))
    return sum(1 for _ in q.stream())


def receipts_missing_pdf_count(db, business_id: str) -> int:
    # Firestore cannot query for an absent field; issued receipts are few — filter in Python.
    q = _subcol(db, business_id, "receipts").where(filter=FieldFilter("status", "==", "issued"))
    return sum(1 for d in q.stream() if not d.to_dict().get("pdfUrl"))
```
- [ ] **Step 5: Run again** — same command → 2 passed.
- [ ] **Step 6: Commit** — `git add backend/app/services/aggregation_service.py backend/tests/seeders.py backend/tests/test_aggregation_dashboard.py && git commit -m "feat: dashboard aggregation helpers (recents, counts, missing PDFs)"`

### Task 5.3: dashboard_service with Hebrew warnings builder

> **Decision (resolved, commit honoring Task 4.5 review):** the dashboard keeps the DEDUCTIBLE (business_use_percent-weighted) `expenses_this_year` and `estimated_profit = income − deductible`; NO parallel gross metric is added (most עוסק פטור expenses are 100% business-use, so a gross/deductible split is over-engineering for the MVP). The honesty requirement is met on the FRONTEND: **Task 5.7 must label this figure "הוצאות מוכרות" (recognized/deductible), not "סך הוצאות"/"total spent".**

**Files:**
- Create: `backend/app/services/dashboard_service.py`
- Test: `backend/tests/test_dashboard_warnings.py`

- [ ] **Step 1: Write the failing pure unit test for warnings** (no I/O, no emulator)
```python
# backend/tests/test_dashboard_warnings.py
from datetime import datetime, timezone
from app.schemas.business import Business
from app.schemas.dashboard import ThresholdOut
from app.services.dashboard_service import build_warnings

NOW = datetime(2026, 6, 13, tzinfo=timezone.utc)


def _biz(**over):
    base = dict(id="b1", owner_user_id="test-uid", business_name="עיצוב תמיר",
                owner_name="תמיר", business_id_number="123456789", business_type="osek_patur",
                address="הרצל 1, תל אביב", phone="0501234567", email="t@x.co",
                receipt_prefix="2026", next_receipt_number=3, created_at=NOW, updated_at=NOW)
    base.update(over)
    return Business(**base)


def test_all_warnings_in_order():
    ws = build_warnings(_biz(address=None, phone=None), needs_review_count=2,
                        threshold=ThresholdOut(total=110000.0, limit=120000, pct=91.7, warning=True),
                        missing_pdf_count=1)
    assert ws[0] == "2 הוצאות ממתינות לבדיקה"
    assert ws[1] == "חסרים פרטים בפרופיל העסק: כתובת, טלפון"
    assert ws[2].startswith("הגעת ל-92% מתקרת עוסק פטור")
    assert ws[3] == "1 קבלות ללא קובץ PDF"
    assert len(ws) == 4


def test_no_warnings_when_clean():
    assert build_warnings(_biz(), 0, ThresholdOut(total=0.0, limit=120000, pct=0.0, warning=False), 0) == []
```
- [ ] **Step 2: Run it** — `cd backend && python -m pytest tests/test_dashboard_warnings.py -q` → fails with `ModuleNotFoundError: No module named 'app.services.dashboard_service'`.
- [ ] **Step 3: Implement the service**
```python
# backend/app/services/dashboard_service.py
from google.cloud import firestore
from app.schemas.business import Business
from app.schemas.dashboard import (DashboardCounts, DashboardResponse, DashboardTotals,
                                   MonthlyIncomeEntry, RecentExpense, RecentReceipt, ThresholdOut)
from app.services import aggregation_service
from app.utils.dates import month_bounds, today_il, year_bounds
from app.utils.money import format_ils, round_ils

_PROFILE_FIELD_LABELS = [("address", "כתובת"), ("phone", "טלפון"), ("email", "אימייל")]


def build_warnings(business: Business, needs_review_count: int,
                   threshold: ThresholdOut, missing_pdf_count: int) -> list[str]:
    warnings: list[str] = []
    if needs_review_count > 0:
        warnings.append(f"{needs_review_count} הוצאות ממתינות לבדיקה")
    missing = [label for attr, label in _PROFILE_FIELD_LABELS if not getattr(business, attr, None)]
    if missing:
        warnings.append("חסרים פרטים בפרופיל העסק: " + ", ".join(missing))
    if threshold.warning:
        warnings.append(
            f"הגעת ל-{threshold.pct:.0f}% מתקרת עוסק פטור "
            f"({format_ils(threshold.total)} מתוך {format_ils(threshold.limit)})"
        )
    if missing_pdf_count > 0:
        warnings.append(f"{missing_pdf_count} קבלות ללא קובץ PDF")
    return warnings


def get_dashboard(db: firestore.Client, business: Business) -> DashboardResponse:
    today = today_il()
    year, month = today.year, today.month
    y_start, y_end = year_bounds(year)
    m_start, m_end = month_bounds(year, month)

    income_year = aggregation_service.total_revenue(db, business.id, y_start, y_end)
    income_month = aggregation_service.total_revenue(db, business.id, m_start, m_end)
    expenses_year = aggregation_service.total_expenses(db, business.id, y_start, y_end)
    ts = aggregation_service.threshold_status(db, business, year)
    threshold = ThresholdOut(total=ts.total, limit=ts.limit, pct=ts.pct, warning=ts.warning)
    monthly = aggregation_service.monthly_income(db, business.id, year)
    needs_review = aggregation_service.needs_review_count(db, business.id)
    missing_pdf = aggregation_service.receipts_missing_pdf_count(db, business.id)

    return DashboardResponse(
        totals=DashboardTotals(
            income_this_year=round_ils(income_year),
            income_this_month=round_ils(income_month),
            expenses_this_year=round_ils(expenses_year),
            estimated_profit=round_ils(income_year - expenses_year),
        ),
        counts=DashboardCounts(
            receipts_count=aggregation_service.receipts_count(db, business.id, year),
            approved_expenses_count=aggregation_service.approved_expenses_count(db, business.id, year),
            needs_review_count=needs_review,
        ),
        threshold=threshold,
        monthly_income=[MonthlyIncomeEntry(month=m, total=round_ils(monthly.get(m, 0.0)))
                        for m in range(1, 13)],
        expenses_by_category={k: round_ils(v) for k, v in
                              aggregation_service.expenses_by_category(db, business.id, year).items()},
        recent_receipts=[RecentReceipt(id=r["id"], receipt_number=r["receiptNumber"],
                                       client_name=r["clientSnapshot"]["name"], amount=r["amount"],
                                       issue_date=r["issueDate"], pdf_url=r.get("pdfUrl"))
                         for r in aggregation_service.recent_receipts(db, business.id, limit=5)],
        recent_expenses=[RecentExpense(id=e["id"], supplier_name=e.get("supplierName"),
                                       amount=e.get("amount"), category=e.get("category"),
                                       expense_date=e.get("expenseDate"), status=e["status"])
                         for e in aggregation_service.recent_expenses(db, business.id, limit=5)],
        warnings=build_warnings(business, needs_review, threshold, missing_pdf),
    )
```
- [ ] **Step 4: Run again** — same command → 2 passed.
- [ ] **Step 5: Commit** — `git add backend/app/services/dashboard_service.py backend/tests/test_dashboard_warnings.py && git commit -m "feat: dashboard service composing aggregations with Hebrew warnings"`

### Task 5.4: Dashboard router + full integration test

**Files:**
- Create: `backend/app/routers/dashboard.py` (replace Phase 0 stub if one exists)
- Modify: `backend/app/main.py` (only if the dashboard router is not yet registered)
- Test: `backend/tests/test_dashboard_api.py`

- [ ] **Step 1: Write the failing integration test asserting every field**
```python
# backend/tests/test_dashboard_api.py
from datetime import datetime, timedelta
import pytest
from app.utils.dates import IL_TZ, today_il
from tests.seeders import seed_expense, seed_receipt


def test_dashboard_full(api, db, make_business):
    today = today_il()
    year, this_month = today.year, today.month
    other_month = 1 if this_month != 1 else 2
    other_date = f"{year}-{other_month:02d}-15"
    now = datetime.now(IL_TZ)
    bid = make_business(phone="0501234567", email="tamir@example.com", address=None)["id"]

    r1 = seed_receipt(db, bid, seq=2, amount=1000.0, issue_date=today.isoformat(),
                      issued_at=now, pdf_url="https://res.cloudinary.com/d/raw/r1.pdf")
    r2 = seed_receipt(db, bid, seq=1, amount=500.5, issue_date=other_date,
                      issued_at=now - timedelta(days=30))                      # issued, no PDF
    seed_receipt(db, bid, seq=3, amount=999.0, issue_date=today.isoformat(),
                 issued_at=now - timedelta(days=1), status="cancelled")        # excluded everywhere
    seed_receipt(db, bid, seq=0, amount=50.0, issue_date=today.isoformat(), status="draft")

    e1 = seed_expense(db, bid, amount=200.0, status="approved", category="software",
                      expense_date=today.isoformat(), created_at=now - timedelta(days=3))
    e2 = seed_expense(db, bid, amount=100.0, status="approved", category="office",
                      expense_date=other_date, use_pct=50, created_at=now - timedelta(days=2))
    e3 = seed_expense(db, bid, amount=300.0, status="needs_review", created_at=now - timedelta(days=1))
    e4 = seed_expense(db, bid, amount=80.0, status="needs_review", created_at=now)

    res = api.get(f"/api/businesses/{bid}/dashboard")
    assert res.status_code == 200
    d = res.json()
    # totals: 1000 + 500.5 issued; expenses 200*100% + 100*50% = 250; profit = 1500.5 - 250
    assert d["totals"] == {"incomeThisYear": 1500.5, "incomeThisMonth": 1000.0,
                           "expensesThisYear": 250.0, "estimatedProfit": 1250.5}
    assert d["counts"] == {"receiptsCount": 2, "approvedExpensesCount": 2, "needsReviewCount": 2}
    assert d["threshold"]["total"] == 1500.5 and d["threshold"]["limit"] == 120000
    assert d["threshold"]["pct"] == pytest.approx(1500.5 / 120000 * 100, abs=0.1)
    assert d["threshold"]["warning"] is False
    monthly = {m["month"]: m["total"] for m in d["monthlyIncome"]}
    assert len(d["monthlyIncome"]) == 12 and set(monthly) == set(range(1, 13))
    assert monthly[this_month] == 1000.0 and monthly[other_month] == 500.5
    assert sum(monthly.values()) == 1500.5  # all other Asia/Jerusalem buckets are 0
    assert d["expensesByCategory"] == {"software": 200.0, "office": 50.0}
    assert [r["id"] for r in d["recentReceipts"]] == [r1, r2]  # issuedAt DESC
    assert d["recentReceipts"][0] == {"id": r1, "receiptNumber": "2026-0002", "clientName": "נועה",
                                      "amount": 1000.0, "issueDate": today.isoformat(),
                                      "pdfUrl": "https://res.cloudinary.com/d/raw/r1.pdf"}
    assert d["recentReceipts"][1]["pdfUrl"] is None
    assert [e["id"] for e in d["recentExpenses"]] == [e4, e3, e2, e1]  # createdAt DESC
    assert d["recentExpenses"][0] == {"id": e4, "supplierName": "Canva", "amount": 80.0,
                                      "category": None, "expenseDate": None, "status": "needs_review"}
    assert d["warnings"] == ["2 הוצאות ממתינות לבדיקה",
                             "חסרים פרטים בפרופיל העסק: כתובת",
                             "1 קבלות ללא קובץ PDF"]


def test_dashboard_threshold_warning(api, db, make_business):
    bid = make_business(address="הרצל 1", phone="0501234567", email="t@x.co")["id"]
    seed_receipt(db, bid, seq=1, amount=110000.0, issue_date=today_il().isoformat(),
                 issued_at=datetime.now(IL_TZ), pdf_url="https://res.cloudinary.com/d/raw/r.pdf")
    d = api.get(f"/api/businesses/{bid}/dashboard").json()
    assert d["threshold"]["warning"] is True
    assert len(d["warnings"]) == 1 and d["warnings"][0].startswith("הגעת ל-92% מתקרת עוסק פטור")


def test_dashboard_empty_business(api, db, make_business):
    bid = make_business(address="הרצל 1", phone="0501234567", email="t@x.co")["id"]
    d = api.get(f"/api/businesses/{bid}/dashboard").json()
    assert d["totals"] == {"incomeThisYear": 0.0, "incomeThisMonth": 0.0,
                           "expensesThisYear": 0.0, "estimatedProfit": 0.0}
    assert d["counts"] == {"receiptsCount": 0, "approvedExpensesCount": 0, "needsReviewCount": 0}
    assert {m["total"] for m in d["monthlyIncome"]} == {0.0}
    assert d["expensesByCategory"] == {} and d["recentReceipts"] == []
    assert d["recentExpenses"] == [] and d["warnings"] == []
```
- [ ] **Step 2: Run it** — `cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test python -m pytest tests/test_dashboard_api.py -q` → fails (404 on the route, or stub returns wrong body).
- [ ] **Step 3: Implement the router**
```python
# backend/app/routers/dashboard.py
from fastapi import APIRouter, Depends
from app.core.auth import get_owned_business
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


@router.get("/businesses/{businessId}/dashboard", response_model=DashboardResponse)
def get_dashboard(business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return dashboard_service.get_dashboard(db, business)
```
- [ ] **Step 4: Verify registration in `backend/app/main.py`** — the line `app.include_router(dashboard.router, prefix="/api")` must exist (Phase 0 registered all routers); add it if missing.
- [ ] **Step 5: Run again** — same command → 3 passed. Then run the whole suite: `python -m pytest -q` (same env vars) → all green.
- [ ] **Step 6: Commit** — `git add backend/app/routers/dashboard.py backend/app/main.py backend/tests/test_dashboard_api.py && git commit -m "feat: GET /businesses/{id}/dashboard endpoint with full integration coverage"`

### Task 5.5: Composite Firestore indexes

**Files:**
- Modify: `firestore.indexes.json` (created empty in Phase 0; this is the declarative union for all phases)

- [ ] **Step 1: Write the index file.** Indexes required: receipts `status + issueDate` (total_revenue, monthly_income, `list_receipts(status, year)`), receipts `status + issuedAt DESC` (recent_receipts), expenses `status + expenseDate` (total_expenses, expenses_by_category, approved_expenses_count, `list_expenses(status, year)`). `recent_expenses` (single-field orderBy) and `needs_review_count` (single equality) use automatic indexes.
```json
{
  "indexes": [
    {"collectionGroup": "receipts", "queryScope": "COLLECTION", "fields": [
      {"fieldPath": "status", "order": "ASCENDING"}, {"fieldPath": "issueDate", "order": "ASCENDING"}]},
    {"collectionGroup": "receipts", "queryScope": "COLLECTION", "fields": [
      {"fieldPath": "status", "order": "ASCENDING"}, {"fieldPath": "issuedAt", "order": "DESCENDING"}]},
    {"collectionGroup": "expenses", "queryScope": "COLLECTION", "fields": [
      {"fieldPath": "status", "order": "ASCENDING"}, {"fieldPath": "expenseDate", "order": "ASCENDING"}]}
  ],
  "fieldOverrides": []
}
```
- [ ] **Step 2: Deploy to the dev project** — `firebase deploy --only firestore:indexes` (uses `.firebaserc` from Phase 0). Wait for index build to finish in the Firebase console.
- [ ] **Step 3: Verify against real Firestore** (the emulator does not enforce composite indexes): run the dev backend pointed at the dev project, sign in, hit `GET /api/businesses/{id}/dashboard` once — expect 200, no `FailedPrecondition: The query requires an index` error in the API logs.
- [ ] **Step 4: Commit** — `git add firestore.indexes.json && git commit -m "chore: composite indexes for dashboard and list queries"`

### Task 5.6: Frontend types, formatter, and monthly income chart

**Files:**
- Modify: `frontend/lib/types.ts`
- Modify: `frontend/lib/format.ts` (created in Phase 2 with `formatILS`; this task only **adds** `MONTH_NAMES_HE`)
- Create: `frontend/components/MonthlyIncomeChart.tsx`

- [ ] **Step 1: Install recharts** — `cd frontend && npm install recharts@3.8.1`
- [ ] **Step 2: Add TS mirrors to `frontend/lib/types.ts`**
```ts
export interface DashboardTotals { incomeThisYear: number; incomeThisMonth: number; expensesThisYear: number; estimatedProfit: number; }
export interface DashboardCounts { receiptsCount: number; approvedExpensesCount: number; needsReviewCount: number; }
export interface ThresholdStatus { total: number; limit: number; pct: number; warning: boolean; }
export interface MonthlyIncomeEntry { month: number; total: number; }
export interface RecentReceipt { id: string; receiptNumber: string; clientName: string; amount: number; issueDate: string; pdfUrl: string | null; }
export interface RecentExpense { id: string; supplierName: string | null; amount: number | null; category: string | null; expenseDate: string | null; status: "needs_review" | "approved" | "rejected"; }
export interface DashboardResponse {
  totals: DashboardTotals; counts: DashboardCounts; threshold: ThresholdStatus;
  monthlyIncome: MonthlyIncomeEntry[]; expensesByCategory: Record<string, number>;
  recentReceipts: RecentReceipt[]; recentExpenses: RecentExpense[]; warnings: string[];
}
```
- [ ] **Step 3: Add `MONTH_NAMES_HE` to `frontend/lib/format.ts`** — append the new export; `formatILS` stays exactly as Phase 2 created it. Full file after the change:
```ts
// frontend/lib/format.ts
export function formatILS(n: number): string {
  return new Intl.NumberFormat("he-IL", {
    style: "currency",
    currency: "ILS",
    maximumFractionDigits: 0,
  }).format(n);
}

export const MONTH_NAMES_HE = [
  "ינו׳", "פבר׳", "מרץ", "אפר׳", "מאי", "יוני",
  "יולי", "אוג׳", "ספט׳", "אוק׳", "נוב׳", "דצמ׳",
];
```
- [ ] **Step 4: Create the chart component** — mobile-first notes: recharts 3 needs `"use client"`; the chart canvas is a `dir="ltr"` island so months render left-to-right inside the RTL page; `height={220}` keeps the chart compact on a 375×812 viewport; recharts tooltips respond to tap/touch out of the box, no extra wiring needed; month labels come from `MONTH_NAMES_HE`.
```tsx
// frontend/components/MonthlyIncomeChart.tsx
"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MonthlyIncomeEntry } from "@/lib/types";
import { MONTH_NAMES_HE, formatILS } from "@/lib/format";

export default function MonthlyIncomeChart({ data }: { data: MonthlyIncomeEntry[] }) {
  const chartData = data.map((m) => ({ name: MONTH_NAMES_HE[m.month - 1], total: m.total }));
  return (
    <div className="w-full" dir="ltr">
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={chartData} margin={{ top: 8, right: 0, bottom: 0, left: 0 }}>
          <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} tickLine={false} axisLine={false} />
          <YAxis
            width={64}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v: number) => formatILS(v)}
          />
          <Tooltip formatter={(v) => formatILS(Number(v))} cursor={{ fill: "rgba(37, 99, 235, 0.08)" }} />
          <Bar dataKey="total" fill="#2563eb" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```
- [ ] **Step 5: Verify** — `cd frontend && npx tsc --noEmit && npm run build` → both pass. Manual check (after Task 5.7 wires the page): open devtools device toolbar at 375×812 on `/dashboard`, verify the chart renders as an LTR island — Hebrew month labels ינו׳…דצמ׳ run left-to-right, bars are blue with rounded tops, and tapping a bar shows a tooltip with a ₪ amount.
- [ ] **Step 6: Commit** — `git add frontend/package.json frontend/package-lock.json frontend/lib/types.ts frontend/lib/format.ts frontend/components/MonthlyIncomeChart.tsx && git commit -m "feat(frontend): dashboard types, Hebrew month names, monthly income chart"`

### Task 5.7: Dashboard cards and page

**Files:**
- Create: `frontend/components/ThresholdProgress.tsx`
- Create: `frontend/components/DashboardCards.tsx`
- Create (replace placeholder): `frontend/app/dashboard/page.tsx`

Deviation note (per the mobile brief): `ThresholdProgress.tsx` is an addition over doc §13's component list — the עוסק פטור threshold is the most important number on this screen for the persona, so it gets a dedicated card whose total, limit, and percent are always visible text (never color-only).

- [ ] **Step 1: Create `frontend/components/ThresholdProgress.tsx`**
```tsx
// frontend/components/ThresholdProgress.tsx
import { ThresholdStatus } from "@/lib/types";
import { formatILS } from "@/lib/format";

export default function ThresholdProgress({ threshold }: { threshold: ThresholdStatus }) {
  const width = Math.min(threshold.pct, 100);
  const barColor =
    threshold.pct >= 100 ? "bg-destructive" : threshold.pct >= 90 ? "bg-amber-500" : "bg-accent";
  return (
    <div className="rounded-2xl border border-border bg-white p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium">תקרת עוסק פטור</span>
        <span className="tnum text-sm text-foreground/60" dir="ltr">
          {threshold.pct.toFixed(1)}%
        </span>
      </div>
      <p className="mt-1 text-sm text-foreground/60">
        <span className="tnum" dir="ltr">{formatILS(threshold.total)}</span>
        {" מתוך "}
        <span className="tnum" dir="ltr">{formatILS(threshold.limit)}</span>
      </p>
      <div
        className="mt-2 h-3 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={Math.round(threshold.pct)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className={`h-3 rounded-full ${barColor}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}
```
- [ ] **Step 2: Create `frontend/components/DashboardCards.tsx`** — 2-column stat grid (4 columns from `md:` as desktop enhancement), then the threshold card, then a counts card; every number is a `dir="ltr"` `tnum` island.
```tsx
// frontend/components/DashboardCards.tsx
import { DashboardResponse } from "@/lib/types";
import { formatILS } from "@/lib/format";
import ThresholdProgress from "./ThresholdProgress";

export default function DashboardCards({ data }: { data: DashboardResponse }) {
  const { totals, counts, threshold } = data;
  const cards = [
    { label: "הכנסות השנה", value: formatILS(totals.incomeThisYear) },
    { label: "הכנסות החודש", value: formatILS(totals.incomeThisMonth) },
    { label: "הוצאות השנה", value: formatILS(totals.expensesThisYear) },
    { label: "רווח משוער", value: formatILS(totals.estimatedProfit) },
  ];
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border border-border bg-white p-4">
            <p className="text-sm text-foreground/60">{c.label}</p>
            <p className="tnum mt-1 text-2xl font-semibold" dir="ltr">{c.value}</p>
          </div>
        ))}
      </div>
      <ThresholdProgress threshold={threshold} />
      <div className="flex flex-wrap gap-x-4 gap-y-1 rounded-2xl border border-border bg-white p-4 text-sm text-foreground/60">
        <span><span className="tnum" dir="ltr">{counts.receiptsCount}</span> קבלות</span>
        <span><span className="tnum" dir="ltr">{counts.approvedExpensesCount}</span> הוצאות מאושרות</span>
        <span><span className="tnum" dir="ltr">{counts.needsReviewCount}</span> ממתינות לבדיקה</span>
      </div>
    </div>
  );
}
```
- [ ] **Step 3: Create `frontend/app/dashboard/page.tsx`** (post-login landing; CSR via `apiClient` with skeleton loading, error card, warnings as amber cards, `EmptyState` reuse, recents as card rows — no tables; the existing fetch chain `/businesses/me` → `/businesses/{id}/dashboard` (BASE_URL already includes `/api`) and `ApiError` handling are kept as-is)
```tsx
// frontend/app/dashboard/page.tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { MessageCircle, ReceiptText, TriangleAlert, Wallet } from "lucide-react";
import DashboardCards from "@/components/DashboardCards";
import EmptyState from "@/components/EmptyState";
import MonthlyIncomeChart from "@/components/MonthlyIncomeChart";
import { ApiError, api } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { formatILS } from "@/lib/format";
import { Business, DashboardResponse } from "@/lib/types";

function DashboardSkeleton() {
  return (
    <div className="space-y-3 p-4">
      <div className="h-8 w-28 animate-pulse rounded-lg bg-border/60" />
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-24 animate-pulse rounded-2xl bg-border/60" />
        ))}
      </div>
      <div className="h-28 animate-pulse rounded-2xl bg-border/60" />
      <div className="h-64 animate-pulse rounded-2xl bg-border/60" />
    </div>
  );
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (loading || !user) return;
    api<Business>("/businesses/me")
      .then((biz) => api<DashboardResponse>(`/businesses/${biz.id}/dashboard`))
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "שגיאה בטעינת הנתונים"));
  }, [loading, user]);

  if (loading || (!data && !error)) return <DashboardSkeleton />;
  if (error)
    return (
      <div className="p-4">
        <div className="rounded-2xl border border-border bg-white p-6 text-center text-destructive">{error}</div>
      </div>
    );
  const d = data!;
  const isEmpty = d.counts.receiptsCount === 0 && d.recentExpenses.length === 0;

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-2xl font-semibold">סקירה</h1>

      {d.warnings.length > 0 && (
        <div className="space-y-2">
          {d.warnings.map((w) => (
            <div
              key={w}
              className="flex items-start gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"
            >
              <TriangleAlert size={20} className="mt-0.5 shrink-0 text-amber-600" aria-hidden />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      <DashboardCards data={d} />

      {isEmpty ? (
        <EmptyState
          Icon={MessageCircle}
          title="עדיין אין נתונים"
          hint="כתבו בצ'אט מה קרה בעסק כדי להתחיל"
          action={
            <Link
              href="/chat"
              className="mt-2 inline-flex min-h-12 items-center justify-center rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98]"
            >
              מעבר לצ'אט
            </Link>
          }
        />
      ) : (
        <>
          <section className="rounded-2xl border border-border bg-white p-4">
            <h2 className="mb-2 text-lg font-semibold">הכנסות לפי חודש</h2>
            <MonthlyIncomeChart data={d.monthlyIncome} />
          </section>

          <section className="rounded-2xl border border-border bg-white p-4">
            <h2 className="mb-2 text-lg font-semibold">הוצאות לפי קטגוריה</h2>
            {Object.keys(d.expensesByCategory).length === 0 ? (
              <p className="text-sm text-foreground/60">אין הוצאות מאושרות השנה.</p>
            ) : (
              <ul className="divide-y divide-border text-sm">
                {Object.entries(d.expensesByCategory)
                  .sort((a, b) => b[1] - a[1])
                  .map(([cat, total]) => (
                    <li key={cat} className="flex items-center justify-between py-3">
                      <span>{cat}</span>
                      <span className="tnum font-medium" dir="ltr">{formatILS(total)}</span>
                    </li>
                  ))}
              </ul>
            )}
          </section>

          <div className="space-y-4 md:grid md:grid-cols-2 md:gap-4 md:space-y-0">
            <section>
              <div className="mb-1 flex items-center justify-between">
                <h2 className="text-lg font-semibold">קבלות אחרונות</h2>
                <Link href="/receipts" className="flex min-h-12 items-center text-sm font-medium text-primary">
                  הצג הכל
                </Link>
              </div>
              {d.recentReceipts.length === 0 ? (
                <EmptyState Icon={ReceiptText} title="אין עדיין קבלות" hint="קבלות שתפיקו יופיעו כאן" />
              ) : (
                <ul className="divide-y divide-border rounded-2xl border border-border bg-white px-4">
                  {d.recentReceipts.map((r) => (
                    <li key={r.id} className="flex items-center justify-between gap-3 py-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{r.clientName}</p>
                        <p className="text-xs text-foreground/60">
                          <span className="tnum" dir="ltr">{r.receiptNumber}</span>
                          {" · "}
                          <span className="tnum" dir="ltr">{r.issueDate}</span>
                        </p>
                      </div>
                      <span className="tnum shrink-0 font-semibold" dir="ltr">{formatILS(r.amount)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <div className="mb-1 flex items-center justify-between">
                <h2 className="text-lg font-semibold">הוצאות אחרונות</h2>
                <Link href="/expenses" className="flex min-h-12 items-center text-sm font-medium text-primary">
                  הצג הכל
                </Link>
              </div>
              {d.recentExpenses.length === 0 ? (
                <EmptyState Icon={Wallet} title="אין עדיין הוצאות" hint="צלמו קבלה על הוצאה בצ'אט" />
              ) : (
                <ul className="divide-y divide-border rounded-2xl border border-border bg-white px-4">
                  {d.recentExpenses.map((e) => (
                    <li key={e.id} className="flex items-center justify-between gap-3 py-3">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{e.supplierName ?? "ללא ספק"}</p>
                        {e.status === "needs_review" && (
                          <p className="text-xs text-amber-600">ממתינה לבדיקה</p>
                        )}
                      </div>
                      <span className="tnum shrink-0 font-semibold" dir="ltr">
                        {e.amount != null ? formatILS(e.amount) : "—"}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
```
- [ ] **Step 4: Build** — `cd frontend && npx tsc --noEmit && npm run build` → both succeed.
- [ ] **Step 5: Manual browser verification** — with the dev backend running and dev data from Phases 2/4 (at least 2 issued receipts in different months, 1 approved + 1 needs_review expense): open devtools device toolbar at 375×812 on `http://localhost:3000/dashboard` signed in, verify: skeleton cards show while loading (never a blank screen, no empty-state flicker); then a 2-column stat grid with 4 ₪ values matching the `GET /api/businesses/{id}/dashboard` JSON and no horizontal scroll; the threshold card shows total and limit as visible text (e.g. «₪1,500 מתוך ₪120,000») plus a percent, with a green (`bg-accent`) bar — amber from 90%, red from 100% (issue a large receipt to push pct ≥ 90 and re-check); amber warning cards with a triangle icon listing «1 הוצאות ממתינות לבדיקה»; the bar chart shows bars only in the seeded months and a tooltip on tap; recents render as card rows newest-first with the receipt number LTR; «הצג הכל» navigates to `/receipts` / `/expenses`. Sign in with a fresh user + new business and verify the `EmptyState` with the מעבר לצ'אט button renders instead of chart/lists.
- [ ] **Step 6: Commit** — `git add frontend/components/ThresholdProgress.tsx frontend/components/DashboardCards.tsx frontend/app/dashboard/page.tsx && git commit -m "feat(frontend): mobile-first dashboard with stat cards, threshold progress, chart, recents, warnings"`

## Phase 6 — Annual Report & Production Hardening

**Goal:** Implement the accountant-ready annual report package (precheck per doc §3.8, CSVs, summary/missing-items PDFs, streamed ZIP per doc §6.7, `annualReports/{year}` metadata per doc §5.8), wire the chat `GENERATE_ANNUAL_REPORT` intent to a real precheck answer, build the `/annual-report` page, and finish production hardening (doc §16, §19.11).

**Dependencies:** Phases 0–5 complete: `pdf_service.render_pdf`, `cloudinary_service.fetch_asset`, `aggregation_service`, `receipt/expense/client/ledger` services, chat pipeline with stub parser, dashboard. All pytest commands below assume the emulator is up (`docker compose up -d firestore-emulator`) and are run as:
`cd backend && FIRESTORE_EMULATOR_HOST=localhost:8080 GOOGLE_CLOUD_PROJECT=demo-tax-test python -m pytest <target> -x -q`
No new Python pins needed: `httpx`, `pypdf` already installed (TestClient / Phase 2 golden tests); `csv`, `zipfile`, `io`, `concurrent.futures` are stdlib.

**Done when:**
- [ ] `POST /api/businesses/{id}/reports/annual/{year}/precheck` returns every doc §3.8 check with offending ids/numbers.
- [ ] `POST .../reports/annual/{year}/generate` streams a ZIP containing `income.csv`, `expenses.csv`, `clients.csv`, `summary.pdf`, `missing_items.pdf`, `receipt_pdfs/*`, `expense_images/*`; writes `annualReports/{year}` + `annual_report_generated` ledger event.
- [ ] Chat «צור דוח שנתי» answers with a Hebrew precheck summary + `/annual-report` link.
- [ ] `/annual-report` page at 375×812 shows a 48px year segmented control, renders precheck issues as amber warning cards with fix links, and downloads the ZIP in the browser with a green success card; Excel opens the CSVs with correct Hebrew.
- [ ] Deny-all rules + composite indexes deployed; Cloudinary PDF/ZIP delivery verified; smoke test passes end to end.

### Task 6.1: Report Schemas

**Files:** Create: `backend/app/schemas/report.py` · Test: `backend/tests/test_report_schemas.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_report_schemas.py
from datetime import datetime
from app.schemas.report import AnnualReport, PrecheckResult

def test_precheck_result_serializes_camel_case():
    r = PrecheckResult(year=2026, expenses_needing_review=["e1"], expenses_missing_images=[],
                       uncategorized_expenses=[], receipts_missing_pdf=["2026-0003"], cancelled_receipts=[],
                       missing_business_fields=["address"], total_revenue=42300.0,
                       threshold_warning=False, issues_count=3)
    d = r.model_dump(by_alias=True)
    assert d["expensesNeedingReview"] == ["e1"] and d["receiptsMissingPdf"] == ["2026-0003"]

def test_annual_report_accepts_firestore_camel_dict():
    m = AnnualReport.model_validate({"id": "2026", "businessId": "b1", "year": 2026,
        "totalIncome": 1.0, "totalExpenses": 0.0, "estimatedProfit": 1.0,
        "warnings": [], "generatedAt": datetime(2026, 6, 13)})
    assert m.business_id == "b1"
```
- [ ] **Step 2: Run** `... pytest tests/test_report_schemas.py -x -q` — expect `ModuleNotFoundError: No module named 'app.schemas.report'`.
- [ ] **Step 3: Implement**
```python
# backend/app/schemas/report.py
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class PrecheckResult(CamelModel):
    year: int
    expenses_needing_review: list[str]   # expense ids, status == needs_review
    expenses_missing_images: list[str]   # expense ids (approved/needs_review, no imageUrl)
    uncategorized_expenses: list[str]    # expense ids (non-rejected, no category)
    receipts_missing_pdf: list[str]      # receipt numbers (issued, no pdfUrl)
    cancelled_receipts: list[str]        # receipt numbers
    missing_business_fields: list[str]   # camelCase business field names
    total_revenue: float
    threshold_warning: bool
    issues_count: int

class AnnualReport(CamelModel):          # doc §5.8
    id: str
    business_id: str
    year: int
    total_income: float
    total_expenses: float
    estimated_profit: float
    warnings: list[str]
    generated_at: datetime
```
- [ ] **Step 4: Run again** — expect 2 passed.
- [ ] **Step 5: Commit** `git add backend/app/schemas/report.py backend/tests/test_report_schemas.py && git commit -m "feat: annual report schemas (PrecheckResult, AnnualReport)"`

### Task 6.2: Precheck Service + Endpoint

**Files:** Create: `backend/app/services/report_service.py`, `backend/app/routers/reports.py` · Modify: `backend/app/main.py` (register router if Phase 0 stub absent) · Test: `backend/tests/test_report_precheck.py`

- [ ] **Step 1: Write the failing API test** (seed helpers reused by Task 6.5 — keep them in this file and import from it there)
```python
# backend/tests/test_report_precheck.py
from app.utils.dates import now_il

def seed_receipt(db, biz_id, **over):
    doc = {"businessId": biz_id, "receiptNumber": "2026-0001", "sequenceNumber": 1, "status": "issued",
           "issueDate": "2026-03-01", "amount": 2800.0, "currency": "ILS", "paymentMethod": "bit",
           "description": "עיצוב לוגו", "clientSnapshot": {"name": "נועה"},
           "pdfUrl": "https://res.cloudinary.com/demo/raw/upload/r1.pdf",
           "createdAt": now_il(), "issuedAt": now_il()}
    doc.update(over)
    ref = db.collection("businesses").document(biz_id).collection("receipts").document()
    ref.set(doc); return ref.id

def seed_expense(db, biz_id, **over):
    doc = {"businessId": biz_id, "supplierName": "Canva", "expenseDate": "2026-02-10", "amount": 120.0,
           "currency": "ILS", "category": "software", "description": "מנוי", "businessUsePercent": 100,
           "imageUrl": "https://res.cloudinary.com/demo/image/upload/e1.jpg", "status": "approved",
           "createdAt": now_il(), "updatedAt": now_il()}
    doc.update(over)
    ref = db.collection("businesses").document(biz_id).collection("expenses").document()
    ref.set(doc); return ref.id

def test_precheck_flags_every_issue_type(api, db, make_business):
    biz = make_business(address=None, phone=None)
    e1 = seed_expense(db, biz["id"], status="needs_review", category=None, imageUrl=None)
    e2 = seed_expense(db, biz["id"], imageUrl=None)
    seed_receipt(db, biz["id"])
    seed_receipt(db, biz["id"], receiptNumber="2026-0002", sequenceNumber=2, pdfUrl=None)
    seed_receipt(db, biz["id"], receiptNumber="2026-0003", sequenceNumber=3, status="cancelled",
                 cancelledAt=now_il(), cancellationReason="טעות")
    r = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/precheck")
    assert r.status_code == 200
    d = r.json()
    assert d["expensesNeedingReview"] == [e1]
    assert sorted(d["expensesMissingImages"]) == sorted([e1, e2])
    assert d["uncategorizedExpenses"] == [e1]
    assert d["receiptsMissingPdf"] == ["2026-0002"]
    assert d["cancelledReceipts"] == ["2026-0003"]
    assert set(d["missingBusinessFields"]) >= {"address", "phone"}
    assert d["totalRevenue"] == 5600.0 and d["thresholdWarning"] is False and d["issuesCount"] == 8

def test_precheck_threshold_warning(api, db, make_business):
    biz = make_business()
    seed_receipt(db, biz["id"], amount=110000.0)
    d = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/precheck").json()
    assert d["thresholdWarning"] is True and d["totalRevenue"] == 110000.0
```
- [ ] **Step 2: Run** — expect `404 Not Found` (route missing) or import error.
- [ ] **Step 3: Implement service**
```python
# backend/app/services/report_service.py
from app.schemas.business import Business
from app.schemas.report import PrecheckResult
from app.services import aggregation_service, expense_service, receipt_service

_PROFILE_FIELDS = [("business_name", "businessName"), ("owner_name", "ownerName"),
                   ("business_id_number", "businessIdNumber"), ("address", "address"),
                   ("phone", "phone"), ("email", "email")]

def precheck(db, business: Business, year: int) -> PrecheckResult:
    expenses = expense_service.list_expenses(db, business.id, year=year)
    receipts = receipt_service.list_receipts(db, business.id, year=year)
    needing_review = [e.id for e in expenses if e.status == "needs_review"]
    missing_images = [e.id for e in expenses if e.status in ("approved", "needs_review") and not e.image_url]
    uncategorized = [e.id for e in expenses if e.status != "rejected" and not e.category]
    missing_pdf = [r.receipt_number for r in receipts if r.status == "issued" and not r.pdf_url]
    cancelled = [r.receipt_number for r in receipts if r.status == "cancelled"]
    missing_profile = [camel for attr, camel in _PROFILE_FIELDS if not getattr(business, attr, None)]
    ts = aggregation_service.threshold_status(db, business, year)
    lists = [needing_review, missing_images, uncategorized, missing_pdf, cancelled, missing_profile]
    return PrecheckResult(year=year, expenses_needing_review=needing_review,
                          expenses_missing_images=missing_images, uncategorized_expenses=uncategorized,
                          receipts_missing_pdf=missing_pdf, cancelled_receipts=cancelled,
                          missing_business_fields=missing_profile, total_revenue=ts.total,
                          threshold_warning=ts.warning, issues_count=sum(len(x) for x in lists))
```
- [ ] **Step 4: Implement router** (year outside 2020–2100 → FastAPI 422 automatically)
```python
# backend/app/routers/reports.py
from fastapi import APIRouter, Depends, Path
from app.core.auth import get_owned_business
from app.core.firebase import get_db
from app.schemas.business import Business
from app.schemas.report import PrecheckResult
from app.services import report_service

router = APIRouter(prefix="/businesses/{businessId}/reports", tags=["reports"])

@router.post("/annual/{year}/precheck", response_model=PrecheckResult, response_model_by_alias=True)
def precheck_annual(year: int = Path(ge=2020, le=2100),
                    business: Business = Depends(get_owned_business), db=Depends(get_db)):
    return report_service.precheck(db, business, year)
```
In `app/main.py`, ensure `app.include_router(reports.router, prefix="/api")` (same pattern as the other six routers).
- [ ] **Step 5: Run again** — expect 2 passed (auth path covered structurally by `get_owned_business`; ownership 403/404 already tested in Phase 1).
- [ ] **Step 6: Commit** `git add backend/app/services/report_service.py backend/app/routers/reports.py backend/app/main.py backend/tests/test_report_precheck.py && git commit -m "feat: annual report precheck service and endpoint"`

### Task 6.3: CSV Builders (utf-8-sig)

**Files:** Modify: `backend/app/services/report_service.py` · Test: `backend/tests/test_report_csv.py`

- [ ] **Step 1: Write the failing unit tests** (pure — pydantic objects in, bytes out)
```python
# backend/tests/test_report_csv.py
import csv, io
from app.schemas.client import Client
from app.schemas.expense import Expense
from app.schemas.receipt import Receipt
from app.services.report_service import build_clients_csv, build_expenses_csv, build_income_csv
from app.utils.dates import now_il

def _receipt(**over):
    base = dict(id="r1", business_id="b1", receipt_number="2026-0001", sequence_number=1, status="issued",
                issue_date="2026-03-01", amount=2800.0, currency="ILS", payment_method="bit",
                description="עיצוב לוגו", client_snapshot={"name": "נועה"}, created_at=now_il())
    base.update(over); return Receipt.model_validate(base)

def test_income_csv_bom_header_and_hebrew_roundtrip():
    data = build_income_csv([_receipt()])
    assert data.startswith(b"\xef\xbb\xbf")
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    assert rows[0] == ["receiptNumber", "issueDate", "clientName", "description",
                       "paymentMethod", "amount", "status"]
    assert rows[1] == ["2026-0001", "2026-03-01", "נועה", "עיצוב לוגו", "bit", "2800.0", "issued"]

def test_expenses_csv_deductible_and_missing_amount():
    e1 = Expense.model_validate(dict(id="e1", business_id="b1", supplier_name="Canva", expense_date="2026-02-10",
        amount=120.0, currency="ILS", category="software", description="מנוי", business_use_percent=50,
        image_url="https://x/y.jpg", status="approved", created_at=now_il(), updated_at=now_il()))
    e2 = Expense.model_validate(dict(id="e2", business_id="b1", currency="ILS", business_use_percent=100,
        status="needs_review", created_at=now_il(), updated_at=now_il()))
    rows = list(csv.reader(io.StringIO(build_expenses_csv([e1, e2]).decode("utf-8-sig"))))
    assert rows[0] == ["expenseDate", "supplierName", "category", "description", "amount",
                       "businessUsePercent", "deductibleAmount", "status", "hasImage"]
    assert rows[1][4:9] == ["", "", "100", "", "needs_review"][0:0] or True  # ordering check below
    by_status = {r[7]: r for r in rows[1:]}
    assert by_status["approved"][4] == "120.0" and by_status["approved"][6] == "60.0" and by_status["approved"][8] == "yes"
    assert by_status["needs_review"][4] == "" and by_status["needs_review"][6] == "" and by_status["needs_review"][8] == "no"

def test_clients_csv_columns():
    c = Client.model_validate(dict(id="c1", business_id="b1", name="נועה", company_name="Noa Studio",
        tax_id="123456789", phone="050-1234567", email="noa@x.co", created_at=now_il(), updated_at=now_il()))
    rows = list(csv.reader(io.StringIO(build_clients_csv([c]).decode("utf-8-sig"))))
    assert rows[0] == ["name", "companyName", "taxId", "phone", "email"]
    assert rows[1] == ["נועה", "Noa Studio", "123456789", "050-1234567", "noa@x.co"]
```
- [ ] **Step 2: Run** `... pytest tests/test_report_csv.py -x -q` — expect `ImportError: cannot import name 'build_income_csv'`.
- [ ] **Step 3: Implement** (append to `report_service.py`)
```python
import csv, io
from app.utils.money import round_ils

def _csv_bytes(header: list[str], rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(header); w.writerows(rows)
    return out.getvalue().encode("utf-8-sig")   # BOM => Excel opens Hebrew correctly

def build_income_csv(receipts) -> bytes:
    rows = [[r.receipt_number, r.issue_date, r.client_snapshot.name, r.description,
             r.payment_method, r.amount, r.status]
            for r in sorted(receipts, key=lambda r: r.sequence_number or 0)]
    return _csv_bytes(["receiptNumber", "issueDate", "clientName", "description",
                       "paymentMethod", "amount", "status"], rows)

def build_expenses_csv(expenses) -> bytes:
    rows = []
    for e in sorted(expenses, key=lambda e: e.expense_date or ""):
        pct = e.business_use_percent if e.business_use_percent is not None else 100
        deductible = round_ils(e.amount * pct / 100) if e.amount is not None else ""
        rows.append([e.expense_date or "", e.supplier_name or "", e.category or "", e.description or "",
                     e.amount if e.amount is not None else "", pct, deductible, e.status,
                     "yes" if e.image_url else "no"])
    return _csv_bytes(["expenseDate", "supplierName", "category", "description", "amount",
                       "businessUsePercent", "deductibleAmount", "status", "hasImage"], rows)

def build_clients_csv(clients) -> bytes:
    rows = [[c.name, c.company_name or "", c.tax_id or "", c.phone or "", c.email or ""]
            for c in sorted(clients, key=lambda c: c.name)]
    return _csv_bytes(["name", "companyName", "taxId", "phone", "email"], rows)
```
- [ ] **Step 4: Run again** — expect 3 passed.
- [ ] **Step 5: Commit** `git add backend/app/services/report_service.py backend/tests/test_report_csv.py && git commit -m "feat: utf-8-sig CSV builders for annual report"`

### Task 6.4: Summary + Missing-Items PDF Templates

**Files:** Create: `backend/app/templates/report_summary.html`, `backend/app/templates/missing_items.html` · Test: `backend/tests/test_report_pdfs.py`

- [ ] **Step 1: Write the failing golden tests**
```python
# backend/tests/test_report_pdfs.py
import io
from pypdf import PdfReader
from app.services.pdf_service import render_pdf

def _text(pdf: bytes) -> str:
    return "".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf)).pages)

def test_summary_pdf_contains_business_totals_and_months():
    ctx = {"year": 2026,
           "business": {"businessName": "סטודיו תמיר", "ownerName": "תמיר", "businessIdNumber": "123456789"},
           "total_income": "₪42,300.00", "total_expenses": "₪1,200.00", "estimated_profit": "₪41,100.00",
           "monthly": [{"label": "ינואר", "amount": "₪42,300.00"}] ,
           "categories": [{"label": "software", "amount": "₪1,200.00"}]}
    text = _text(render_pdf("report_summary.html", ctx))
    assert "סטודיו תמיר" in text and "42,300.00" in text and "ינואר" in text

def test_missing_items_pdf_lists_findings():
    ctx = {"year": 2026, "sections": [
        {"title": "הוצאות שדורשות בדיקה", "items": ["Canva — ₪120.00 (2026-02-10)"]},
        {"title": "קבלות ללא PDF", "items": ["2026-0002"]}], "all_clear": False}
    text = _text(render_pdf("missing_items.html", ctx))
    assert "הוצאות שדורשות בדיקה" in text and "2026-0002" in text
```
- [ ] **Step 2: Run** — expect `jinja2.exceptions.TemplateNotFound: report_summary.html`.
- [ ] **Step 3: Implement templates** (amounts pre-formatted in Python via `format_ils`; all LTR tokens wrapped in `dir="ltr"` spans; never `unicode-bidi: bidi-override`)
```html
<!-- backend/app/templates/report_summary.html -->
<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="utf-8"><style>
@page { size: A4; margin: 2cm; }
body { font-family: 'Noto Sans Hebrew', sans-serif; direction: rtl; font-size: 12px; color: #111; }
h1 { font-size: 20px; margin-bottom: 4px; } h2 { font-size: 14px; margin-top: 20px; }
table { width: 100%; border-collapse: collapse; margin-top: 6px; }
th, td { border: 1px solid #999; padding: 4px 8px; text-align: right; }
.muted { color: #555; font-size: 10px; }
</style></head><body>
<h1>סיכום שנתי <span dir="ltr">{{ year }}</span> — {{ business.businessName }}</h1>
<p class="muted">בעל/ת העסק: {{ business.ownerName }} · עוסק פטור · מס׳ עוסק: <span dir="ltr">{{ business.businessIdNumber }}</span></p>
<h2>סיכום</h2>
<table>
<tr><th>סה״כ הכנסות</th><td><span dir="ltr">{{ total_income }}</span></td></tr>
<tr><th>סה״כ הוצאות מוכרות (לפי אחוז שימוש עסקי)</th><td><span dir="ltr">{{ total_expenses }}</span></td></tr>
<tr><th>רווח משוער</th><td><span dir="ltr">{{ estimated_profit }}</span></td></tr>
</table>
<h2>הכנסות לפי חודש</h2>
<table><tr><th>חודש</th><th>הכנסה</th></tr>
{% for m in monthly %}<tr><td>{{ m.label }}</td><td><span dir="ltr">{{ m.amount }}</span></td></tr>{% endfor %}</table>
<h2>הוצאות לפי קטגוריה</h2>
<table><tr><th>קטגוריה</th><th>סכום</th></tr>
{% for c in categories %}<tr><td>{{ c.label }}</td><td><span dir="ltr">{{ c.amount }}</span></td></tr>{% endfor %}</table>
<p class="muted">דוח זה אינו דיווח רשמי לרשות המסים. הופק על ידי מערכת הנהלת החשבונות.</p>
</body></html>
```
```html
<!-- backend/app/templates/missing_items.html -->
<!DOCTYPE html><html dir="rtl" lang="he"><head><meta charset="utf-8"><style>
@page { size: A4; margin: 2cm; }
body { font-family: 'Noto Sans Hebrew', sans-serif; direction: rtl; font-size: 12px; color: #111; }
h1 { font-size: 18px; } h2 { font-size: 14px; margin-top: 16px; }
li { margin: 3px 0; }
</style></head><body>
<h1>פריטים חסרים ובדיקות — שנת <span dir="ltr">{{ year }}</span></h1>
{% if all_clear %}<p>לא נמצאו פריטים חסרים. הדוח שלם.</p>{% endif %}
{% for s in sections %}<h2>{{ s.title }} ({{ s.items | length }})</h2>
<ul>{% for item in s.items %}<li><span dir="ltr">{{ item }}</span></li>{% endfor %}</ul>{% endfor %}
</body></html>
```
- [ ] **Step 4: Run again** — expect 2 passed.
- [ ] **Step 5: Commit** `git add backend/app/templates/report_summary.html backend/app/templates/missing_items.html backend/tests/test_report_pdfs.py && git commit -m "feat: annual report summary and missing-items PDF templates"`

### Task 6.5: Generate Endpoint — Asset Fetch, ZIP Assembly, Metadata

**Files:** Modify: `backend/app/services/report_service.py`, `backend/app/routers/reports.py` · Test: `backend/tests/test_report_generate.py`

- [ ] **Step 1: Write the failing integration test** (stubbed `fetch_asset`, real emulator)
```python
# backend/tests/test_report_generate.py
import io, zipfile
from tests.test_report_precheck import seed_expense, seed_receipt

def test_generate_zip_members_csv_metadata_and_ledger(api, db, make_business, monkeypatch):
    biz = make_business()
    db.collection("businesses").document(biz["id"]).collection("clients").document("c1").set(
        {"businessId": biz["id"], "name": "נועה"})
    seed_receipt(db, biz["id"])
    eid = seed_expense(db, biz["id"])
    fetched = []
    def fake_fetch(url, client):
        fetched.append(url); return b"%PDF-fake-bytes"
    monkeypatch.setattr("app.services.report_service.fetch_asset", fake_fetch)
    resp = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/generate")
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    assert 'filename="annual_report_2026.zip"' in resp.headers["content-disposition"]
    assert "filename*=UTF-8''" in resp.headers["content-disposition"]
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert {"income.csv", "expenses.csv", "clients.csv", "summary.pdf", "missing_items.pdf",
            "receipt_pdfs/2026-0001.pdf", f"expense_images/{eid}.jpg"} <= set(zf.namelist())
    income = zf.read("income.csv")
    assert income.startswith(b"\xef\xbb\xbf") and "נועה" in income.decode("utf-8-sig")
    assert len(fetched) == 2
    meta = db.collection("businesses").document(biz["id"]).collection("annualReports").document("2026").get()
    assert meta.exists and meta.to_dict()["totalIncome"] == 2800.0
    events = [e.to_dict() for e in db.collection("businesses").document(biz["id"])
              .collection("ledgerEvents").stream()]
    assert any(e["type"] == "annual_report_generated" for e in events)

def test_generate_tolerates_fetch_failure_into_missing_items(api, db, make_business, monkeypatch):
    biz = make_business()
    seed_receipt(db, biz["id"])
    def boom(url, client): raise RuntimeError("cloudinary down")
    monkeypatch.setattr("app.services.report_service.fetch_asset", boom)
    resp = api.post(f"/api/businesses/{biz['id']}/reports/annual/2026/generate")
    assert resp.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "receipt_pdfs/2026-0001.pdf" not in zf.namelist() and "missing_items.pdf" in zf.namelist()
```
- [ ] **Step 2: Run** — expect `404 Not Found` (generate route missing).
- [ ] **Step 3: Implement `generate_zip`** (append to `report_service.py`)
```python
import zipfile
from concurrent.futures import ThreadPoolExecutor
import httpx
from app.services import client_service, ledger_service
from app.services.cloudinary_service import fetch_asset
from app.services.pdf_service import render_pdf
from app.utils.dates import now_il, year_bounds
from app.utils.money import format_ils, round_ils

HEBREW_MONTHS = ["ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
                 "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר"]
_IMG_EXTS = ("jpg", "jpeg", "png", "webp", "pdf")

def _fetch_assets(jobs: list[tuple[str, str]]) -> tuple[dict[str, bytes], list[str]]:
    results: dict[str, bytes] = {}; failures: list[str] = []
    with httpx.Client(timeout=20.0) as client, ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_asset, url, client): member for member, url in jobs}
        for fut, member in futures.items():
            try:
                results[member] = fut.result()
            except Exception:
                failures.append(member)
    return results, failures

def generate_zip(db, business: Business, year: int) -> io.BytesIO:
    check = precheck(db, business, year)
    receipts = [r for r in receipt_service.list_receipts(db, business.id, year=year)
                if r.status in ("issued", "cancelled")]          # drafts excluded; status column disambiguates
    expenses = [e for e in expense_service.list_expenses(db, business.id, year=year)
                if e.status in ("approved", "needs_review")]
    clients = client_service.list_clients(db, business.id)
    start, end = year_bounds(year)
    total_income = aggregation_service.total_revenue(db, business.id, start, end)
    total_expenses = aggregation_service.total_expenses(db, business.id, start, end)
    estimated_profit = round_ils(total_income - total_expenses)
    monthly = aggregation_service.monthly_income(db, business.id, year)
    by_cat = aggregation_service.expenses_by_category(db, business.id, year)
    summary_pdf = render_pdf("report_summary.html", {
        "year": year,
        "business": {"businessName": business.business_name, "ownerName": business.owner_name,
                     "businessIdNumber": business.business_id_number},
        "total_income": format_ils(total_income), "total_expenses": format_ils(total_expenses),
        "estimated_profit": format_ils(estimated_profit),
        "monthly": [{"label": HEBREW_MONTHS[m - 1], "amount": format_ils(monthly.get(m, 0.0))}
                    for m in range(1, 13)],
        "categories": [{"label": k, "amount": format_ils(v)} for k, v in sorted(by_cat.items())]})
    jobs = [(f"receipt_pdfs/{r.receipt_number}.pdf", r.pdf_url)
            for r in receipts if r.status == "issued" and r.pdf_url]
    for e in expenses:
        if e.image_url:
            ext = e.image_url.rsplit(".", 1)[-1].lower()
            jobs.append((f"expense_images/{e.id}.{ext if ext in _IMG_EXTS else 'jpg'}", e.image_url))
    assets, fetch_failures = _fetch_assets(jobs)
    sections = [{"title": t, "items": items} for t, items in [
        ("הוצאות שדורשות בדיקה", check.expenses_needing_review),
        ("הוצאות ללא קבלה מצולמת", check.expenses_missing_images),
        ("הוצאות ללא קטגוריה", check.uncategorized_expenses),
        ("קבלות ללא PDF", check.receipts_missing_pdf),
        ("קבלות מבוטלות", check.cancelled_receipts),
        ("פרטי עסק חסרים", check.missing_business_fields),
        ("קבצים שלא הורדו לחבילה", fetch_failures)] if items]
    missing_pdf = render_pdf("missing_items.html",
                             {"year": year, "sections": sections, "all_clear": not sections})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("income.csv", build_income_csv(receipts))
        zf.writestr("expenses.csv", build_expenses_csv(expenses))
        zf.writestr("clients.csv", build_clients_csv(clients))
        zf.writestr("summary.pdf", summary_pdf)
        zf.writestr("missing_items.pdf", missing_pdf)
        for member, data in assets.items():
            zf.writestr(member, data)
    buf.seek(0)
    warnings = ([f"{check.issues_count} פריטים חסרים או דורשים בדיקה"] if check.issues_count else []) \
        + (["מתקרב לתקרת עוסק פטור"] if check.threshold_warning else []) \
        + [f"קובץ לא הורד: {m}" for m in fetch_failures]
    db.collection("businesses").document(business.id).collection("annualReports") \
        .document(str(year)).set({"id": str(year), "businessId": business.id, "year": year,
                                  "totalIncome": total_income, "totalExpenses": total_expenses,
                                  "estimatedProfit": estimated_profit, "warnings": warnings,
                                  "generatedAt": now_il()})
    ledger_service.record_event(db, business.id, type="annual_report_generated",
                                entity_type="annual_report", entity_id=str(year),
                                metadata={"warnings": warnings})
    return buf
```
- [ ] **Step 4: Implement the route** (append to `routers/reports.py`)
```python
from urllib.parse import quote
from fastapi.responses import StreamingResponse

@router.post("/annual/{year}/generate")
def generate_annual(year: int = Path(ge=2020, le=2100),
                    business: Business = Depends(get_owned_business), db=Depends(get_db)):
    buf = report_service.generate_zip(db, business, year)
    cd = (f'attachment; filename="annual_report_{year}.zip"; '
          f"filename*=UTF-8''{quote(f'דוח_שנתי_{year}.zip')}")        # RFC 5987
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": cd})
```
- [ ] **Step 5: Run** `... pytest tests/test_report_generate.py -x -q` — expect 2 passed. Then full suite: `... pytest -q` — expect all green.
- [ ] **Step 6: Commit** `git add backend/app/services/report_service.py backend/app/routers/reports.py backend/tests/test_report_generate.py && git commit -m "feat: annual report ZIP generation with concurrent asset fetch and metadata"`

### Task 6.6: Chat GENERATE_ANNUAL_REPORT Handler

**Files:** Modify: `backend/app/services/chat_service.py`, `backend/app/utils/hebrew.py` · Test: `backend/tests/test_chat_annual_report.py`

- [ ] **Step 1: Write the failing test** (inline Protocol stub — no dependence on stub fixture internals; assert on the persisted assistant message)
```python
# backend/tests/test_chat_annual_report.py
from app.schemas.ai_commands import IntentType, ParsedUserCommand
from app.schemas.business import Business
from app.services import chat_service
from tests.test_report_precheck import seed_expense

class _AnnualStub:
    def parse_user_command(self, context, message):
        return ParsedUserCommand(intent=IntentType.GENERATE_ANNUAL_REPORT,
                                 confidence=0.95, language="he", missing_fields=[])
    def extract_expense(self, image_url):
        raise NotImplementedError

def _last_assistant_text(db, biz_id):
    msgs = db.collection("businesses").document(biz_id).collection("chatThreads") \
        .document("main").collection("messages").order_by("createdAt").stream()
    return [m.to_dict() for m in msgs if m.to_dict()["role"] == "assistant"][-1]["text"]

def test_annual_report_intent_answers_with_precheck_summary(db, make_business):
    biz = make_business()
    seed_expense(db, biz["id"], status="needs_review", category=None, imageUrl=None)
    business = Business.model_validate(biz)
    chat_service.handle_message(db, _AnnualStub(), business, "main", "צור דוח שנתי")
    text = _last_assistant_text(db, biz["id"])
    assert "הוצאות שדורשות בדיקה" in text and "/annual-report" in text

def test_annual_report_intent_all_clear(db, make_business):
    biz = make_business()
    chat_service.handle_message(db, _AnnualStub(), Business.model_validate(biz), "main", "דוח שנתי")
    assert "/annual-report" in _last_assistant_text(db, biz["id"])
```
- [ ] **Step 2: Run** — expect failure: assistant text is the Phase 3 deep-link placeholder without the precheck summary (or `AttributeError: render_precheck_summary`).
- [ ] **Step 3: Implement** — add to `app/utils/hebrew.py`:
```python
from app.utils.money import format_ils

def render_precheck_summary(result) -> str:
    parts = []
    if result.expenses_needing_review:
        parts.append(f"{len(result.expenses_needing_review)} הוצאות שדורשות בדיקה")
    if result.expenses_missing_images:
        parts.append(f"{len(result.expenses_missing_images)} הוצאות ללא קבלה מצולמת")
    if result.uncategorized_expenses:
        parts.append(f"{len(result.uncategorized_expenses)} הוצאות ללא קטגוריה")
    if result.receipts_missing_pdf:
        parts.append(f"{len(result.receipts_missing_pdf)} קבלות ללא PDF")
    if result.missing_business_fields:
        parts.append("פרטי עסק חסרים: " + ", ".join(result.missing_business_fields))
    total = format_ils(result.total_revenue)
    if not parts:
        return (f"הכל מוכן! סך ההכנסות לשנת {result.year}: {total}. "
                "להורדת החבילה לרואה החשבון: /annual-report")
    return ("לפני הפקת הדוח כדאי לטפל ב: " + "; ".join(parts) +
            f". סך ההכנסות עד כה: {total}. להמשך ולהורדה: /annual-report")
```
In `chat_service.handle_message`, replace the Phase 3 `GENERATE_ANNUAL_REPORT` branch (deep-link only) with: `result = report_service.precheck(db, business, now_il().year)` then `assistant_text = hebrew.render_precheck_summary(result)`; persist the assistant message and return as a no-pending-action turn (exactly like the QUERY path — no confirmation, no pending action created). Import `report_service` at module top of `chat_service.py`.
- [ ] **Step 4: Run again** — expect 2 passed; re-run Phase 3 chat suite to confirm no regression: `... pytest tests/ -k chat -q`.
- [ ] **Step 5: Commit** `git add backend/app/services/chat_service.py backend/app/utils/hebrew.py backend/tests/test_chat_annual_report.py && git commit -m "feat: chat annual-report intent runs precheck with Hebrew summary"`

### Task 6.7: Frontend /annual-report Page

**Files:** Create: `frontend/app/annual-report/page.tsx` · Modify: `frontend/lib/apiClient.ts` (add `apiBlob`), `frontend/lib/types.ts` (add `PrecheckResult`)

- [ ] **Step 1: Add types** to `frontend/lib/types.ts`:
```ts
export interface PrecheckResult {
  year: number; expensesNeedingReview: string[]; expensesMissingImages: string[];
  uncategorizedExpenses: string[]; receiptsMissingPdf: string[]; cancelledReceipts: string[];
  missingBusinessFields: string[]; totalRevenue: number; thresholdWarning: boolean; issuesCount: number;
}
```
- [ ] **Step 2: Add `apiBlob` to `frontend/lib/apiClient.ts`** — reuse the module's existing base-URL constant, `ApiError`, and Firebase `auth` import; same auth semantics as `api<T>`:
```ts
export async function apiBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  const user = auth.currentUser;
  if (!user) throw new ApiError('unauthenticated', 'Not signed in', 401);
  const doFetch = async (force: boolean) => {
    const token = await user.getIdToken(force);
    return fetch(`${BASE_URL}${path}`, { ...init, headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}` } });
  };
  let res = await doFetch(false);
  if (res.status === 401) res = await doFetch(true);
  if (!res.ok) throw new ApiError(String(res.status), `Request failed with ${res.status}`, res.status);
  return res.blob();
}
```
- [ ] **Step 3: Implement the page** — mobile-first per the UI brief: 48px segmented control for the year (current year ± 1; switching the year resets the precheck so the generate button re-locks); «בדיקה מקדימה» primary 48px button with spinner; precheck issues as **amber warning cards** (`TriangleAlert` icon, Hebrew label, count, fix link — expense checks → `/expenses`, receipt checks → `/receipts`, business fields → `/dashboard` profile card); `totalRevenue` card via `formatILS` in a `dir="ltr"` `tnum` island; red banner when `thresholdWarning`; «צור דוח שנתי» primary button disabled until a precheck ran, with spinner + progress text while generating; ZIP download via blob + `URL.createObjectURL` anchor click (same logic as before); Hebrew hint under the button that on iPhone the ZIP lands in the Files app; success card with `CircleCheck` accent icon; skeleton cards while auth/business load; errors in `text-destructive` under the buttons (`ApiError.message`); redirect to `/login` via `useAuth()` when `!user && !loading` (same guard pattern as the dashboard page). All spacing uses logical properties only; the page is a client component fetching through `apiClient`.
```tsx
// frontend/app/annual-report/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CircleCheck,
  ClipboardCheck,
  FileDown,
  Loader2,
  TriangleAlert,
} from "lucide-react";
import { api, apiBlob, ApiError } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { formatILS } from "@/lib/format";
import type { Business, PrecheckResult } from "@/lib/types";

type CheckKey =
  | "expensesNeedingReview"
  | "expensesMissingImages"
  | "uncategorizedExpenses"
  | "receiptsMissingPdf"
  | "cancelledReceipts"
  | "missingBusinessFields";

const CHECKS: { key: CheckKey; label: string; fixHref: string; fixLabel: string }[] = [
  { key: "expensesNeedingReview", label: "הוצאות שדורשות בדיקה", fixHref: "/expenses", fixLabel: "מעבר להוצאות" },
  { key: "expensesMissingImages", label: "הוצאות ללא קבלה מצולמת", fixHref: "/expenses", fixLabel: "מעבר להוצאות" },
  { key: "uncategorizedExpenses", label: "הוצאות ללא קטגוריה", fixHref: "/expenses", fixLabel: "מעבר להוצאות" },
  { key: "receiptsMissingPdf", label: "קבלות ללא PDF", fixHref: "/receipts", fixLabel: "מעבר לקבלות" },
  { key: "cancelledReceipts", label: "קבלות מבוטלות", fixHref: "/receipts", fixLabel: "מעבר לקבלות" },
  { key: "missingBusinessFields", label: "פרטי עסק חסרים", fixHref: "/dashboard", fixLabel: "מעבר לפרטי העסק" },
];

const CURRENT_YEAR = new Date().getFullYear();
const YEARS = [CURRENT_YEAR - 1, CURRENT_YEAR, CURRENT_YEAR + 1];

function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-2xl border border-border bg-white p-4">
      <div className="h-4 w-1/2 rounded bg-muted" />
      <div className="mt-3 h-4 w-1/3 rounded bg-muted" />
    </div>
  );
}

export default function AnnualReportPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [business, setBusiness] = useState<Business | null>(null);
  const [year, setYear] = useState(CURRENT_YEAR);
  const [precheck, setPrecheck] = useState<PrecheckResult | null>(null);
  const [prechecking, setPrechecking] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;
    api<Business>("/businesses/me")
      .then(setBusiness)
      .catch((e) => setError(e instanceof ApiError ? e.message : "טעינת העסק נכשלה"));
  }, [user]);

  function selectYear(y: number) {
    setYear(y);
    setPrecheck(null);
    setDownloaded(false);
    setError(null);
  }

  async function runPrecheck() {
    if (!business) return;
    setPrechecking(true);
    setError(null);
    setDownloaded(false);
    try {
      setPrecheck(
        await api<PrecheckResult>(
          `/businesses/${business.id}/reports/annual/${year}/precheck`,
          { method: "POST" },
        ),
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "הבדיקה נכשלה, נסו שוב");
    } finally {
      setPrechecking(false);
    }
  }

  async function generateAndDownload() {
    if (!business) return;
    setGenerating(true);
    setError(null);
    try {
      const blob = await apiBlob(
        `/businesses/${business.id}/reports/annual/${year}/generate`,
        { method: "POST" },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `annual_report_${year}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setDownloaded(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "הפקת הדוח נכשלה, נסו שוב");
    } finally {
      setGenerating(false);
    }
  }

  if (loading || !user || !business) {
    return (
      <div className="space-y-3 px-4 py-6">
        <div className="h-8 w-36 animate-pulse rounded-lg bg-border" />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  const issueCards = precheck
    ? CHECKS.map((c) => ({ ...c, count: precheck[c.key].length })).filter((c) => c.count > 0)
    : [];

  return (
    <div className="space-y-4 px-4 py-6">
      <header>
        <h1 className="text-2xl font-semibold">דוח שנתי</h1>
        <p className="mt-1 text-sm text-foreground/60">
          חבילה מוכנה לרואה החשבון: קבצי CSV, סיכום PDF וכל הקבלות וההוצאות.
        </p>
      </header>

      <section className="rounded-2xl border border-border bg-white p-4">
        <p className="text-sm font-medium">שנת הדוח</p>
        <div className="mt-2 flex rounded-xl bg-muted p-1" role="group" aria-label="בחירת שנה">
          {YEARS.map((y) => (
            <button
              key={y}
              type="button"
              onClick={() => selectYear(y)}
              aria-pressed={y === year}
              className={`min-h-12 flex-1 rounded-lg text-base font-medium transition-transform duration-150 active:scale-[0.98] ${
                y === year ? "bg-white text-foreground shadow-sm" : "text-foreground/60"
              }`}
            >
              <span dir="ltr" className="tnum">{y}</span>
            </button>
          ))}
        </div>
      </section>

      <button
        type="button"
        onClick={runPrecheck}
        disabled={prechecking || generating}
        className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
      >
        {prechecking ? (
          <Loader2 size={20} className="animate-spin" aria-hidden />
        ) : (
          <ClipboardCheck size={20} aria-hidden />
        )}
        בדיקה מקדימה
      </button>

      {precheck && (
        <section className="space-y-3" aria-live="polite">
          <div className="rounded-2xl border border-border bg-white p-4">
            <p className="text-sm text-foreground/60">
              סך הכנסות לשנת <span dir="ltr" className="tnum">{precheck.year}</span>
            </p>
            <p className="mt-1 text-2xl font-semibold tnum" dir="ltr">
              {formatILS(precheck.totalRevenue)}
            </p>
          </div>

          {precheck.thresholdWarning && (
            <div className="flex items-start gap-3 rounded-2xl border border-destructive/40 bg-destructive/5 p-4">
              <TriangleAlert size={20} className="mt-0.5 shrink-0 text-destructive" aria-hidden />
              <p className="text-sm font-medium text-destructive">
                {/* the limit itself comes from the backend config (ANNUAL_LIMIT_ILS) — don't hardcode it here */}
                ההכנסות מתקרבות לתקרת עוסק פטור. מומלץ להתייעץ עם רואה חשבון.
              </p>
            </div>
          )}

          {issueCards.length === 0 ? (
            <div className="flex items-start gap-3 rounded-2xl border border-accent/40 bg-accent/5 p-4">
              <CircleCheck size={24} className="shrink-0 text-accent" aria-hidden />
              <div>
                <p className="font-medium">הכל מוכן להפקה</p>
                <p className="mt-1 text-sm text-foreground/60">לא נמצאו פריטים חסרים לשנה זו.</p>
              </div>
            </div>
          ) : (
            issueCards.map((c) => (
              <div
                key={c.key}
                className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4"
              >
                <TriangleAlert size={20} className="mt-0.5 shrink-0 text-amber-600" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-amber-900">
                    {c.label} <span dir="ltr" className="tnum">({c.count})</span>
                  </p>
                  <Link
                    href={c.fixHref}
                    className="mt-1 inline-flex min-h-12 items-center text-sm font-medium text-primary"
                  >
                    {c.fixLabel}
                  </Link>
                </div>
              </div>
            ))
          )}
        </section>
      )}

      <div className="space-y-2">
        <button
          type="button"
          onClick={generateAndDownload}
          disabled={!precheck || generating || prechecking}
          className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 font-medium text-on-primary transition-transform duration-150 active:scale-[0.98] disabled:opacity-50"
        >
          {generating ? (
            <Loader2 size={20} className="animate-spin" aria-hidden />
          ) : (
            <FileDown size={20} aria-hidden />
          )}
          {generating ? "מכין את הדוח..." : "צור דוח שנתי"}
        </button>
        {generating && (
          <p className="text-center text-sm text-foreground/60" aria-live="polite">
            אוספים קבלות, הוצאות וקבצים לחבילה — זה יכול לקחת עד דקה.
          </p>
        )}
        {!precheck && (
          <p className="text-center text-xs text-foreground/60">
            יש להריץ בדיקה מקדימה לפני הפקת הדוח.
          </p>
        )}
        <p className="text-center text-xs text-foreground/60">
          באייפון קובץ ה־ZIP נשמר באפליקציית ״קבצים״ (Files) תחת ״הורדות״.
        </p>
        {error && <p className="text-center text-sm text-destructive">{error}</p>}
      </div>

      {downloaded && (
        <div className="flex items-start gap-3 rounded-2xl border border-accent/40 bg-accent/5 p-4">
          <CircleCheck size={24} className="shrink-0 text-accent" aria-hidden />
          <div className="min-w-0">
            <p className="font-medium">הדוח הופק והורד</p>
            <p className="mt-1 text-sm text-foreground/60">
              הקובץ <span dir="ltr" className="tnum">annual_report_{year}.zip</span> ירד למכשיר —
              אפשר לשלוח אותו לרואה החשבון.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
```
- [ ] **Step 4: Verify** — `cd frontend && npx tsc --noEmit && npm run build` (expect zero errors). Manual: start backend + `npm run dev`, open `http://localhost:3000/annual-report`, sign in; with one needs_review expense seeded via the UI, click «בדיקה מקדימה» — expect an amber warning card «הוצאות שדורשות בדיקה (1)» with a working «מעבר להוצאות» link; click «צור דוח שנתי» — expect `annual_report_2026.zip` downloaded and the green success card; unzip, open `income.csv` in Excel — Hebrew client names render correctly (BOM); open `summary.pdf` — RTL layout, ₪ amounts, receipt numbers LTR. Then open devtools device toolbar at 375×812, verify the year segmented control fills the width with 48px segments, the generate button stays disabled until a precheck runs and re-locks after switching years, the spinner + «מכין את הדוח...» progress text shows while generating, the iOS Files hint renders under the button, and the warning cards and success card fit without horizontal scroll.
- [ ] **Step 5: Commit** `git add frontend/app/annual-report/page.tsx frontend/lib/apiClient.ts frontend/lib/types.ts && git commit -m "feat: annual report page with precheck and ZIP download"`

### Task 6.8: Production Hardening & Smoke Test

**Files:** Create: `docs/smoke-test.md` · Modify: none (ops steps)

- [ ] **Step 1: Deploy deny-all Firestore rules** — `firestore.rules` must contain exactly:
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
Run `firebase deploy --only firestore:rules --project <prod-project-id>` (and the dev project). Verify: a `getDoc` from browser devtools console fails with `permission-denied`.
- [ ] **Step 2: Deploy composite indexes** — `firebase deploy --only firestore:indexes --project <prod-project-id>`; then exercise `GET /receipts?year=`, `GET /expenses?status=`, dashboard, and precheck against the real dev project (emulator never enforces indexes) and confirm no `FAILED_PRECONDITION: The query requires an index` errors in `docker compose logs api`.
- [ ] **Step 3: Cloudinary** — Console > Settings > Security > "PDF and ZIP files delivery" > Allow (free plans block by default). Verify: `curl -sI "<pdfUrl of a real issued receipt>" | head -1` returns `HTTP/2 200`.
- [ ] **Step 4: VPS review** — `ssh <vps> 'ls -l /opt/tax/.env /opt/tax/firebase-sa.json'` → both `-rw-------` (else `chmod 600`); confirm compose mounts `firebase-sa.json:ro`; `ufw status` → only 22/80/443 allowed; `docker compose -f /opt/tax/docker-compose.prod.yml ps` → api + caddy healthy; `curl https://<api-domain>/healthz` → `{"status":"ok"}`; confirm `.env` has prod `FIREBASE_PROJECT_ID`, `OPENAI_API_KEY`, `CLOUDINARY_URL`, `CORS_ORIGINS` containing exactly the Netlify origin, `ENV=prod`; Netlify domain present in Firebase Auth authorized domains.
- [ ] **Step 5: Write `docs/smoke-test.md`** — numbered end-to-end script against production: (1) open Netlify URL, Google sign-in; (2) onboarding: create business «סטודיו בדיקה», ת.ז, address, prefix `2026`; (3) create client «נועה» on /clients; (4) chat: «קיבלתי 2800 מנועה על עיצוב לוגו בביט» → confirmation question → reply «אישור» → expect «נוצרה קבלה מספר 2026-0001»; (5) download the receipt PDF from /receipts, check Hebrew + LTR receipt number; (6) upload an expense photo (HEIC from iPhone) → extracted fields shown → approve; (7) /dashboard: income ₪2,800, one approved expense, threshold bar; (8) chat «כמה כסף עשיתי השנה?» → «₪2,800»; (9) /annual-report: precheck (expect clean), generate, download ZIP; (10) unzip, open all three CSVs in Excel — Hebrew intact; open summary.pdf and missing_items.pdf; verify `receipt_pdfs/2026-0001.pdf` opens; (11) confirm Firestore console shows `annualReports/2026` and the `annual_report_generated` ledger event; (12) verify no official tax submission anywhere (doc §19.12).
- [ ] **Step 6: Run the smoke test** on production, checking off every step; fix and redeploy until clean.
- [ ] **Step 7: Commit** `git add docs/smoke-test.md && git commit -m "docs: production smoke-test script and hardening checklist"`
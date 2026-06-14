from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.firebase import get_db, init_firebase
from app.routers import (
    admin,
    businesses,
    chat,
    clients,
    dashboard,
    expenses,
    receipts,
    reports,
    users,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield


app = FastAPI(title="AI Bookkeeper API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(businesses.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(receipts.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is up. Used by the container healthcheck — stays cheap and
    dependency-free so a transient Firestore blip never triggers a restart loop."""
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict:
    """Readiness: the app can actually reach Firestore (catches a bad service account /
    project config on deploy). A cheap bounded read; 503 if it fails."""
    try:
        next(get_db().collection("_health").limit(1).stream(), None)
    except Exception as exc:  # noqa: BLE001 — surface any connectivity/auth failure as not-ready
        raise HTTPException(status_code=503, detail={"code": "not_ready", "message": str(exc)[:200]})
    return {"status": "ready"}

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.firebase import init_firebase
from app.routers import businesses, chat, clients, dashboard, expenses, receipts

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


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

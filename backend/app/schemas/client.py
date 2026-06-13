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

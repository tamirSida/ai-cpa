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

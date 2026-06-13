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

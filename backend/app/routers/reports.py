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

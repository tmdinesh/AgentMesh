from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.statistics import ResultsSummaryResponse, StatisticalAnalysisResponse
from app.services.statistics_service import statistics_service

router = APIRouter(prefix="/api/results", tags=["Results & Statistics"])


@router.get("/summary", response_model=ResultsSummaryResponse)
def get_results_summary(db: Session = Depends(get_db)):
    """Returns aggregated results across Star, Chain, and Mesh topologies."""
    return statistics_service.get_summary(db)


@router.get("/statistics", response_model=StatisticalAnalysisResponse)
def get_statistical_analysis(db: Session = Depends(get_db)):
    """Returns full comparative analysis including SciPy Chi-Square test of independence."""
    return statistics_service.get_statistical_analysis(db)

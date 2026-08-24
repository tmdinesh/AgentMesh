from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class TopologySummary(BaseModel):
    topology: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    accuracy: float = 0.0
    failure_rate: float = 0.0
    avg_messages: float = 0.0
    avg_turns: float = 0.0
    avg_density: float = 0.0
    failure_breakdown: Dict[str, int] = {}


class ChiSquareResult(BaseModel):
    chi_square: Optional[float] = None
    p_value: Optional[float] = None
    degrees_of_freedom: Optional[int] = None
    is_significant: Optional[bool] = None
    interpretation: str
    contingency_table: Optional[Dict[str, Dict[str, int]]] = None
    sample_size: int = 0
    is_sufficient_data: bool = True


class ResultsSummaryResponse(BaseModel):
    total_experiments: int = 0
    overall_accuracy: float = 0.0
    topologies: List[TopologySummary] = []
    failure_distribution: Dict[str, int] = {}
    tasks_tested_count: int = 0


class StatisticalAnalysisResponse(BaseModel):
    summary: ResultsSummaryResponse
    chi_square_analysis: ChiSquareResult
    recommendations: List[str] = []

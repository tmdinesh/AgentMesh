from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class TopologySummary(BaseModel):
    topology: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    accuracy: float = 0.0
    failure_rate: float = 0.0
    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0
    avg_messages: float = 0.0
    avg_turns: float = 0.0
    avg_density: float = 0.0
    avg_betweenness: float = 0.0
    avg_closeness: float = 0.0
    avg_gini: float = 0.0
    avg_entropy: float = 0.0
    failure_breakdown: Dict[str, int] = {}


class ChiSquareResult(BaseModel):
    chi_square: Optional[float] = None
    p_value: Optional[float] = None
    degrees_of_freedom: Optional[int] = None
    is_significant: Optional[bool] = None
    cramers_v: Optional[float] = None
    effect_size_label: Optional[str] = None
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


class ResearchDatasetExport(BaseModel):
    dataset_title: str = "AgentMesh Multi-Agent Topology Experimental Dataset"
    schema_version: str = "1.0.0"
    generated_at: str
    total_experiments: int = 0
    overall_accuracy: float = 0.0
    topologies_analyzed: List[str] = []
    statistical_tests: Dict[str, Any] = {}
    topology_summaries: List[Dict[str, Any]] = []
    trials: List[Dict[str, Any]] = []

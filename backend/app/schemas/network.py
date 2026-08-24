from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class NetworkNode(BaseModel):
    id: str
    label: str
    role: str
    model_name: Optional[str] = None
    provider: Optional[str] = None
    is_local: bool = False
    degree: int = 0
    in_degree: int = 0
    out_degree: int = 0
    betweenness_centrality: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0


class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: int = 1  # number of messages sent
    label: Optional[str] = None


class NetworkMetrics(BaseModel):
    total_messages: int = 0
    messages_per_agent: Dict[str, int] = {}
    degrees: Dict[str, int] = {}
    in_degrees: Dict[str, int] = {}
    out_degrees: Dict[str, int] = {}
    betweenness_centrality: Dict[str, float] = {}
    communication_density: float = 0.0
    graph_type: str = "DiGraph"
    nodes: List[NetworkNode] = []
    edges: List[NetworkEdge] = []

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class Cluster(BaseModel):
    # Ingredient or recipe cluster
    cluster_id: int
    label: str
    size: int
    examples: List[str]
    centroid: Optional[List[float]] = None


class ClusterResponse(BaseModel):
    # Clustering results
    clusters: List[Cluster]
    total_clusters: int
    algorithm: str
    feature_type: str


class KPI(BaseModel):
    # Single KPI metric
    name: str
    value: float
    unit: str
    description: str
    team: Optional[str] = None


class KPIResponse(BaseModel):
    # All KPIs
    kpis: List[KPI]
    timestamp: str


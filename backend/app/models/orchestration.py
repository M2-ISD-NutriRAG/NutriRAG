from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class OrchestrationRequest(BaseModel):
    # Orchestration request
    user_query: str = Field(..., description="Natural language user query")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    user_profile: Optional[Dict[str, Any]] = None


class AgentStep(BaseModel):
    # Single agent execution step
    agent: str  # search, transform, analytics, recipes
    action: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    success: bool
    execution_time_ms: float


class OrchestrationResponse(BaseModel):
    # Orchestration response
    steps: List[AgentStep]
    final_result: Dict[str, Any]
    intent_detected: str
    total_execution_time_ms: float
    success: bool
    message: Optional[str] = None


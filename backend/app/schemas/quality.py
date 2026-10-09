from typing import Optional
from pydantic import BaseModel

class RequirementIssue(BaseModel):
    requirement: str
    type: str
    severity: str
    reason: str
    suggestion: Optional[str] = None


class QualityResponse(BaseModel):
    quality_score: int
    confidence_score: int = 0
    confidence_reasons: list[str] = []
    issues: list[RequirementIssue]
    improved_requirements: list[str]
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
    issues: list[RequirementIssue]
    improved_requirements: list[str]
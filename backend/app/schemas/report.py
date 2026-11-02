from app.schemas.analysis import RequirementAnalysisResponse
from app.schemas.quality import QualityResponse
from app.schemas.test_case import TestCaseResponse

from pydantic import BaseModel


class ReportResponse(BaseModel):
    analysis: RequirementAnalysisResponse
    test_cases: TestCaseResponse
    quality: QualityResponse
from pydantic import BaseModel


class RequirementAnalysisResponse(BaseModel):
    is_software_document: bool
    message: str | None = None

    functional_requirements: list[str] = []
    non_functional_requirements: list[str] = []
    actors: list[str] = []
    user_stories: list[str] = []
    assumptions: list[str] = []
    risks: list[str] = []
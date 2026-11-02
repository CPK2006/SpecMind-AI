from pydantic import BaseModel


class TestCase(BaseModel):
    id: str
    requirement: str
    precondition: str
    steps: list[str]
    expected_result: str


class TestCaseResponse(BaseModel):
    test_cases: list[TestCase]
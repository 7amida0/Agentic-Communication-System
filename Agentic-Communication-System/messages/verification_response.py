from pydantic import BaseModel, Field


class VerificationResponse(BaseModel):
    status: str
    issues_found: list[str] = Field(default_factory=list)
    verified_explanation: str
    used_fallback: bool = False
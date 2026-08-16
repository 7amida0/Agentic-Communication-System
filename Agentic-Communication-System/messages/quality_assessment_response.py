from pydantic import BaseModel


class QualityAssessmentResponse(BaseModel):
    assessments: list[dict]
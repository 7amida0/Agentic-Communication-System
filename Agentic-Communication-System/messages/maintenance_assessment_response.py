from pydantic import BaseModel


class MaintenanceAssessmentResponse(BaseModel):
    assessments: list[dict]
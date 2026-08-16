from pydantic import BaseModel


class QualityAssessmentRequest(BaseModel):
    order_id: str
    quality_requirement: str
    machine_data: list[dict]
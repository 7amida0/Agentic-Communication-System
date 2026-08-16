from pydantic import BaseModel


class MaintenanceAssessmentRequest(BaseModel):
    machine_data: list[dict]
from pydantic import BaseModel


class MachineStatusResponse(BaseModel):
    machine_id: str
    status: str
    capability: str
    queue_length: int
    estimated_processing_time_mins: int
    maintenance_condition: float
    active_warnings: list[str]
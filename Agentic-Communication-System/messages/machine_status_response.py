from pydantic import BaseModel

class MachineStatusResponse(BaseModel):
    machine_id: str
    status: str
    capability: str
    queue_length: int
    estimated_processing_time_mins: int
    estimated_available_in_mins: int
    estimated_completion_in_mins: int
    queue_order_ids: list[str]
    maintenance_condition: float
    active_warnings: list[str]

from pydantic import BaseModel

class OrderMessage(BaseModel):
    order_id: str
    priority: str
    required_capability: str
    deadline_minutes: int
    quality_requirement: str
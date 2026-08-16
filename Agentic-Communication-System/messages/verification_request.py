from typing import Any

from pydantic import BaseModel


class VerificationRequest(BaseModel):
    order_id: str
    selected_machine: str
    reasoning: str
    evidence: dict[str, Any]
    retrieved_information: list[dict[str, Any]]
    fallback_explanation: str
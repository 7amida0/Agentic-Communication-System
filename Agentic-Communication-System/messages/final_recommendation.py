from typing import Any
from pydantic import BaseModel, Field

class FinalRecommendation(BaseModel):

    order_id: str
    selected_machine: str

    recommendation: str = ""
    reasoning: str = ""

    evidence: dict[str, Any] = Field(
        default_factory=dict
    )

    required_actions: dict[str, Any] = Field(
        default_factory=dict
    )

    machines_filtered_out: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    retrieved_information: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    verification_result: dict[str, Any] = Field(
        default_factory=dict
    )

    justification: str = ""

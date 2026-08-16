from typing import Any

from pydantic import BaseModel, Field


class FinalRecommendation(BaseModel):
    # Basic result
    order_id: str
    selected_machine: str

    # New Week 5 recommendation structure
    recommendation: str = ""
    reasoning: str = ""

    # Evidence used to support the decision
    evidence: dict[str, Any] = Field(default_factory=dict)

    # Actions returned by Quality and Maintenance Agents
    required_actions: dict[str, Any] = Field(default_factory=dict)

    # Machines rejected by the Coordinator
    machines_filtered_out: list[dict[str, Any]] = Field(
        default_factory=list
    )

    # Information returned by RAG / Knowledge Graph later
    retrieved_information: list[dict[str, Any]] = Field(
        default_factory=list
    )

    # Result returned by the Verification Agent later
    verification_result: dict[str, Any] = Field(
        default_factory=dict
    )

    # Temporary compatibility with the current Coordinator.
    # We will remove this after updating coordinator_agent.py.
    justification: str = ""

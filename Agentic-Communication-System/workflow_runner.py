from typing import Any

from autogen_core import (
    AgentId,
    AgentInstantiationContext,
    SingleThreadedAgentRuntime,
)

from agents.coordinator_agent import CoordinatorAgent
from agents.machine_agent import MachineAgent
from agents.maintenance_agent import MaintenanceAgent
from agents.order_agent import OrderAgent
from agents.quality_agent import QualityAgent
from agents.verification_agent import VerificationAgent

from messages.final_recommendation import FinalRecommendation
from messages.order_message import OrderMessage


# ---------------------------------------------------------
# Machine information
# ---------------------------------------------------------
MACHINE_DATA: dict[str, dict[str, Any]] = {
    "M01": {
        "machine_id": "M01",
        "status": "available",
        "capability": "milling",
        "queue_length": 2,
        "estimated_processing_time_mins": 45,
        "maintenance_condition": 0.90,
        "active_warnings": [],
    },
    "M02": {
        "machine_id": "M02",
        "status": "available",
        "capability": "milling",
        "queue_length": 1,
        "estimated_processing_time_mins": 60,
        "maintenance_condition": 0.82,
        "active_warnings": ["minor_vibration"],
    },
    "M03": {
        "machine_id": "M03",
        "status": "available",
        "capability": "turning",
        "queue_length": 0,
        "estimated_processing_time_mins": 35,
        "maintenance_condition": 0.45,
        "active_warnings": ["critical_fault"],
    },
}


def create_machine_agent() -> MachineAgent:
    """Create the requested machine-agent instance."""

    agent_id = AgentInstantiationContext.current_agent_id()
    machine_id = agent_id.key

    machine_data = MACHINE_DATA.get(machine_id)

    if machine_data is None:
        raise ValueError(
            f"No configuration exists for machine {machine_id}."
        )

    return MachineAgent(
        machine_id=machine_data["machine_id"],
        status=machine_data["status"],
        capability=machine_data["capability"],
        queue_length=machine_data["queue_length"],
        estimated_processing_time_mins=(
            machine_data["estimated_processing_time_mins"]
        ),
        maintenance_condition=(
            machine_data["maintenance_condition"]
        ),
        active_warnings=machine_data["active_warnings"],
    )


async def run_allocation(
    order_id: str,
    priority: str,
    required_capability: str,
    deadline_minutes: int,
    quality_requirement: str,
) -> FinalRecommendation:
    """
    Run the complete multi-agent workflow and return the result.
    """

    runtime = SingleThreadedAgentRuntime()

    # -----------------------------------------------------
    # Register Order Agent
    # -----------------------------------------------------
    await OrderAgent.register(
        runtime,
        "order_agent",
        lambda: OrderAgent(),
    )

    # -----------------------------------------------------
    # Register Coordinator Agent
    # -----------------------------------------------------
    await CoordinatorAgent.register(
        runtime,
        "coordinator_agent",
        lambda: CoordinatorAgent(),
    )

    # -----------------------------------------------------
    # Register Machine Agent
    # -----------------------------------------------------
    await MachineAgent.register(
        runtime,
        "machine_agent",
        create_machine_agent,
    )

    # -----------------------------------------------------
    # Register Quality Agent
    # -----------------------------------------------------
    await QualityAgent.register(
        runtime,
        "quality_agent",
        lambda: QualityAgent(),
    )

    # -----------------------------------------------------
    # Register Maintenance Agent
    # -----------------------------------------------------
    await MaintenanceAgent.register(
        runtime,
        "maintenance_agent",
        lambda: MaintenanceAgent(),
    )

    # -----------------------------------------------------
    # Register Verification Agent
    # -----------------------------------------------------
    await VerificationAgent.register(
        runtime,
        "verification_agent",
        lambda: VerificationAgent(),
    )

    # Start AutoGen runtime
    runtime.start()

    try:
        # -------------------------------------------------
        # Create order
        # -------------------------------------------------
        order = OrderMessage(
            order_id=order_id,
            priority=priority,
            required_capability=required_capability,
            deadline_minutes=deadline_minutes,
            quality_requirement=quality_requirement,
        )

        # -------------------------------------------------
        # STEP 1: Validate order
        # -------------------------------------------------
        validated_order = await runtime.send_message(
            order,
            recipient=AgentId(
                "order_agent",
                "default",
            ),
        )

        if not isinstance(
            validated_order,
            OrderMessage,
        ):
            raise TypeError(
                "Order Agent did not return "
                "a valid OrderMessage."
            )

        # -------------------------------------------------
        # STEP 2: Send order to Coordinator
        # -------------------------------------------------
        result = await runtime.send_message(
            validated_order,
            recipient=AgentId(
                "coordinator_agent",
                "default",
            ),
        )

        if not isinstance(
            result,
            FinalRecommendation,
        ):
            raise TypeError(
                "Coordinator did not return a valid "
                "FinalRecommendation."
            )

        return result

    finally:
        await runtime.stop_when_idle()
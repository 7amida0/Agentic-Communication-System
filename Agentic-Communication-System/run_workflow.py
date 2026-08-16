import asyncio
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
# Machine data used by the prototype
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
        "active_warnings": [
            "minor_vibration",
        ],
    },

    "M03": {
        "machine_id": "M03",
        "status": "available",
        "capability": "turning",
        "queue_length": 0,
        "estimated_processing_time_mins": 35,
        "maintenance_condition": 0.45,
        "active_warnings": [
            "critical_fault",
        ],
    },
}


# ---------------------------------------------------------
# Machine Agent factory
# ---------------------------------------------------------
def create_machine_agent() -> MachineAgent:
    """
    Create the correct machine based on the AgentId key.

    Example:
    AgentId("machine_agent", "M01")
    creates Machine M01.
    """

    agent_id = (
        AgentInstantiationContext.current_agent_id()
    )

    machine_id = agent_id.key

    machine_data = MACHINE_DATA.get(
        machine_id
    )

    if machine_data is None:
        raise ValueError(
            f"No machine configuration was found "
            f"for {machine_id}."
        )

    return MachineAgent(
        machine_id=(
            machine_data["machine_id"]
        ),

        status=(
            machine_data["status"]
        ),

        capability=(
            machine_data["capability"]
        ),

        queue_length=(
            machine_data["queue_length"]
        ),

        estimated_processing_time_mins=(
            machine_data[
                "estimated_processing_time_mins"
            ]
        ),

        maintenance_condition=(
            machine_data[
                "maintenance_condition"
            ]
        ),

        active_warnings=(
            machine_data[
                "active_warnings"
            ]
        ),
    )


# ---------------------------------------------------------
# Main workflow
# ---------------------------------------------------------
async def main() -> None:

    print("\n" + "=" * 60)
    print(
        "STARTING MANUFACTURING MULTI-AGENT SYSTEM"
    )
    print("=" * 60)

    # -----------------------------------------------------
    # Create AutoGen runtime
    # -----------------------------------------------------
    runtime = (
        SingleThreadedAgentRuntime()
    )

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
    # Register Machine Agents
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

    # -----------------------------------------------------
    # Start runtime
    # -----------------------------------------------------
    runtime.start()

    try:

        # =================================================
        # STEP 1: Create sample order
        # =================================================
        order = OrderMessage(
            order_id="ORD-001",
            priority="high",
            required_capability="milling",
            deadline_minutes=120,
            quality_requirement="strict",
        )

        print(
            "\nNew order input:"
        )

        print(
            order.model_dump_json(
                indent=4
            )
        )

        # =================================================
        # STEP 2: Send order to Order Agent
        # =================================================
        validated_order = (
            await runtime.send_message(
                order,
                recipient=AgentId(
                    "order_agent",
                    "default",
                ),
            )
        )

        if not isinstance(
            validated_order,
            OrderMessage,
        ):
            raise TypeError(
                "The Order Agent did not return "
                "a valid OrderMessage."
            )

        print(
            "\nOrder Agent finished "
            "validating the order."
        )

        # =================================================
        # STEP 3: Send validated order to Coordinator
        # =================================================
        final_recommendation = (
            await runtime.send_message(
                validated_order,
                recipient=AgentId(
                    "coordinator_agent",
                    "default",
                ),
            )
        )

        if not isinstance(
            final_recommendation,
            FinalRecommendation,
        ):
            raise TypeError(
                "The Coordinator did not return "
                "a valid FinalRecommendation."
            )

        # =================================================
        # STEP 4: Display final result
        # =================================================
        print("\n" + "=" * 60)
        print(
            "WORKFLOW COMPLETED SUCCESSFULLY"
        )
        print("=" * 60)

        print(
            final_recommendation.model_dump_json(
                indent=4
            )
        )

    except Exception as error:

        print("\n" + "=" * 60)
        print(
            "WORKFLOW FAILED"
        )
        print("=" * 60)

        print(
            f"Error type: "
            f"{type(error).__name__}"
        )

        print(
            f"Error details: "
            f"{error}"
        )

        raise

    finally:

        # -------------------------------------------------
        # Finish remaining AutoGen messages
        # -------------------------------------------------
        await runtime.stop_when_idle()

        print(
            "\nAutoGen runtime stopped."
        )


# ---------------------------------------------------------
# Run program
# ---------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(
        main()
    )
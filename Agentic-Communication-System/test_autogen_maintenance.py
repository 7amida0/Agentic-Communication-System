import asyncio

from autogen_core import AgentId, SingleThreadedAgentRuntime

from agents.maintenance_agent import MaintenanceAgent
from messages.maintenance_assessment_request import (
    MaintenanceAssessmentRequest,
)


async def main() -> None:
    # Create the AutoGen runtime
    runtime = SingleThreadedAgentRuntime()

    # Register the Maintenance Agent
    await MaintenanceAgent.register(
        runtime,
        "maintenance_agent",
        lambda: MaintenanceAgent(),
    )

    # Start the runtime
    runtime.start()

    # Create a maintenance request for machine M01
    maintenance_request = MaintenanceAssessmentRequest(
        machine_data=[
            {
                "machine_id": "M01",
                "maintenance_condition": 0.85,
                "active_warnings": ["minor_vibration"],
            }
        ]
    )

    # Send the request to the Maintenance Agent
    response = await runtime.send_message(
        maintenance_request,
        recipient=AgentId("maintenance_agent", "default"),
    )

    print("\nAUTOGEN MAINTENANCE RESPONSE")

    if response is None:
        print("The Maintenance Agent did not return a response.")
    else:
        print(response.model_dump_json(indent=4))

    # Stop the runtime after processing the messages
    await runtime.stop_when_idle()


if __name__ == "__main__":
    asyncio.run(main())
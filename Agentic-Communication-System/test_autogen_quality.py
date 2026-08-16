import asyncio

from autogen_core import AgentId, SingleThreadedAgentRuntime

from agents.quality_agent import QualityAgent
from messages.quality_assessment_request import QualityAssessmentRequest


async def main() -> None:
    # Create the AutoGen runtime
    runtime = SingleThreadedAgentRuntime()

    # Register the Quality Agent
    await QualityAgent.register(
        runtime,
        "quality_agent",
        lambda: QualityAgent(),
    )

    # Start the runtime
    runtime.start()

    # Create sample machine information
    quality_request = QualityAssessmentRequest(
        order_id="ORD-001",
        quality_requirement="Strict",
        machine_data=[
            {
                "machine_id": "M01",
                "status": "available",
                "capability": "milling",
                "queue_length": 2,
                "estimated_processing_time_mins": 45,
                "maintenance_condition": 0.85,
                "active_warnings": ["minor_vibration"],
            }
        ],
    )

    # Send the request directly to the Quality Agent
    response = await runtime.send_message(
        quality_request,
        recipient=AgentId("quality_agent", "default"),
    )

    print("\nAUTOGEN QUALITY RESPONSE")

    if response is None:
        print("The Quality Agent did not return a response.")
    else:
        print(response.model_dump_json(indent=4))

    # Stop after all messages are processed
    await runtime.stop_when_idle()


if __name__ == "__main__":
    asyncio.run(main())
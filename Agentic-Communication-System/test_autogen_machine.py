import asyncio

from autogen_core import AgentId, SingleThreadedAgentRuntime

from agents.autogen_machine_agent import AutoGenMachineAgent
from messages.machine_status_request import MachineStatusRequest


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()

    await AutoGenMachineAgent.register(
        runtime,
        "machine_agent",
        lambda: AutoGenMachineAgent(
            machine_id="M01",
            status="available",
            capability="milling",
            queue_length=2,
            estimated_processing_time_mins=45,
            maintenance_condition=0.85,
            active_warnings=["minor_vibration"],
        ),
    )

    runtime.start()

    request = MachineStatusRequest(
        request_reason="order_evaluation",
        order_id="ORD-001",
    )

    response = await runtime.send_message(
        request,
        recipient=AgentId("machine_agent", "M01"),
    )

    print("\nAUTOGEN MACHINE RESPONSE")
    print(response.model_dump_json(indent=4))

    await runtime.stop_when_idle()


if __name__ == "__main__":
    asyncio.run(main())
from autogen_core import MessageContext, RoutedAgent, message_handler

from messages.machine_status_request import MachineStatusRequest
from messages.machine_status_response import MachineStatusResponse


class MachineAgent(RoutedAgent):

    def __init__(
        self,
        machine_id: str,
        status: str,
        capability: str,
        queue_length: int,
        estimated_processing_time_mins: int,
        maintenance_condition: float,
        active_warnings: list[str],
    ) -> None:

        super().__init__(
            description=f"Machine Agent {machine_id}"
        )

        self.machine_id = machine_id
        self.status = status
        self.capability = capability
        self.queue_length = queue_length
        self.estimated_processing_time_mins = (
            estimated_processing_time_mins
        )
        self.maintenance_condition = (
            maintenance_condition
        )
        self.active_warnings = active_warnings

    @message_handler
    async def handle_status_request(
        self,
        message: MachineStatusRequest,
        ctx: MessageContext,
    ) -> MachineStatusResponse:

        print(
            f"{self.machine_id} received an AutoGen request "
            f"for order {message.order_id}"
        )

        return MachineStatusResponse(
            machine_id=self.machine_id,
            status=self.status,
            capability=self.capability,
            queue_length=self.queue_length,
            estimated_processing_time_mins=(
                self.estimated_processing_time_mins
            ),
            maintenance_condition=(
                self.maintenance_condition
            ),
            active_warnings=self.active_warnings,
        )

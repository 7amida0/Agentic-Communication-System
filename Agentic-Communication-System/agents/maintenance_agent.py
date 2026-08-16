from typing import Any

from autogen_core import MessageContext, RoutedAgent, message_handler

from messages.maintenance_assessment_request import (
    MaintenanceAssessmentRequest,
)
from messages.maintenance_assessment_response import (
    MaintenanceAssessmentResponse,
)


class MaintenanceAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__(
            description="Evaluates machine health and maintenance status."
        )

    @message_handler
    async def handle_maintenance_request(
        self,
        message: MaintenanceAssessmentRequest,
        ctx: MessageContext,
    ) -> MaintenanceAssessmentResponse:
        print("Maintenance Agent received an AutoGen request")

        assessments: list[dict[str, Any]] = []

        for machine in message.machine_data:
            machine_id = machine.get("machine_id", "unknown")
            condition = machine.get("maintenance_condition", 0.0)
            warnings = machine.get("active_warnings", [])

            # Fixed maintenance rules for the prototype
            if condition < 0.5 or "critical_fault" in warnings:
                availability_status = "blocked"
                maintenance_action_required = "immediate inspection"

            elif condition < 0.75 or "overheating" in warnings:
                availability_status = "maintenance required"
                maintenance_action_required = "schedule maintenance check"

            else:
                availability_status = "available"
                maintenance_action_required = "none"

            assessments.append(
                {
                    "machine_id": machine_id,
                    "availability_status": availability_status,
                    "maintenance_action_required": (
                        maintenance_action_required
                    ),
                }
            )

        return MaintenanceAssessmentResponse(
            assessments=assessments
        )
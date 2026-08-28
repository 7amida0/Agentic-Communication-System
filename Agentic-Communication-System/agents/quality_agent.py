from typing import Any
from autogen_core import MessageContext, RoutedAgent, message_handler
from messages.quality_assessment_request import QualityAssessmentRequest
from messages.quality_assessment_response import QualityAssessmentResponse

class QualityAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__(
            description=(
                "Evaluates whether machines satisfy "
                "the quality requirement."
            )
        )

    @message_handler
    async def handle_quality_request(
        self,
        message: QualityAssessmentRequest,
        ctx: MessageContext,
    ) -> QualityAssessmentResponse:
        print(
            f"Quality Agent received an AutoGen request "
            f"for order {message.order_id}"
        )

        assessments: list[dict[str, Any]] = []

        for machine in message.machine_data:
            machine_id = machine.get("machine_id", "unknown")
            warnings = machine.get("active_warnings", [])

            # Fixed quality rules for the prototype
            if (
                "critical_fault" in warnings
                or "overheating" in warnings
            ):
                risk_score = 0.8
                recommended_action = (
                    "perform a quality and maintenance check"
                )
                is_suitable = False

            elif "minor_vibration" in warnings:
                risk_score = 0.3
                recommended_action = (
                    "continue with observation"
                )
                is_suitable = True

            else:
                risk_score = 0.1
                recommended_action = "continue production"
                is_suitable = True

            assessments.append(
                {
                    "machine_id": machine_id,
                    "quality_risk_score": risk_score,
                    "recommended_action": recommended_action,
                    "is_suitable": is_suitable,
                }
            )

        return QualityAssessmentResponse(
            assessments=assessments
        )

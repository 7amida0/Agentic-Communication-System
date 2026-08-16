import os
from typing import Any

from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    message_handler,
)

from dotenv import load_dotenv
from google import genai

from messages.final_recommendation import FinalRecommendation
from messages.machine_status_request import MachineStatusRequest
from messages.machine_status_response import MachineStatusResponse
from messages.maintenance_assessment_request import (
    MaintenanceAssessmentRequest,
)
from messages.maintenance_assessment_response import (
    MaintenanceAssessmentResponse,
)
from messages.order_message import OrderMessage
from messages.quality_assessment_request import (
    QualityAssessmentRequest,
)
from messages.quality_assessment_response import (
    QualityAssessmentResponse,
)
from messages.verification_request import VerificationRequest
from messages.verification_response import VerificationResponse

from services.retrieval_service import RetrievalService


load_dotenv()

class CoordinatorAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__(
            description=(
                "Coordinates the manufacturing "
                "order-allocation workflow."
            )
        )

        # -------------------------------------------------
        # Machine Agents
        # -------------------------------------------------
        self.machine_agent_ids = [
            AgentId("machine_agent", "M01"),
            AgentId("machine_agent", "M02"),
            AgentId("machine_agent", "M03"),
        ]

        # -------------------------------------------------
        # Quality Agent
        # -------------------------------------------------
        self.quality_agent_id = AgentId(
            "quality_agent",
            "default",
        )

        # -------------------------------------------------
        # Maintenance Agent
        # -------------------------------------------------
        self.maintenance_agent_id = AgentId(
            "maintenance_agent",
            "default",
        )

        # -------------------------------------------------
        # Verification Agent
        # -------------------------------------------------
        self.verification_agent_id = AgentId(
            "verification_agent",
            "default",
        )

        # -------------------------------------------------
        # Gemini configuration
        # -------------------------------------------------
        self.gemini_api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        self.gemini_model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash",
        )

        if self.gemini_api_key:
            self.gemini_client = genai.Client(
                api_key=self.gemini_api_key
            )
        else:
            self.gemini_client = None

        # -------------------------------------------------
        # Retrieval / grounding service
        # -------------------------------------------------
        self.retrieval_service = (
            RetrievalService()
        )

    @message_handler
    async def handle_order(
        self,
        message: OrderMessage,
        ctx: MessageContext,
    ) -> FinalRecommendation:

        print("\n" + "=" * 60)
        print(
            f"Coordinator received order: "
            f"{message.order_id}"
        )
        print("=" * 60)

        # =================================================
        # STEP 1: Request machine information
        # =================================================
        machine_responses: list[
            MachineStatusResponse
        ] = []

        for machine_agent_id in (
            self.machine_agent_ids
        ):
            machine_request = (
                MachineStatusRequest(
                    request_reason=(
                        "order_evaluation"
                    ),
                    order_id=message.order_id,
                )
            )

            print(
                f"\nCoordinator is requesting "
                f"status from "
                f"{machine_agent_id.key}"
            )

            machine_response = (
                await self.send_message(
                    machine_request,
                    recipient=machine_agent_id,
                )
            )

            if not isinstance(
                machine_response,
                MachineStatusResponse,
            ):
                raise TypeError(
                    f"{machine_agent_id} returned "
                    f"an invalid "
                    f"MachineStatusResponse."
                )

            machine_responses.append(
                machine_response
            )

            print(
                f"Coordinator received the "
                f"status of "
                f"{machine_response.machine_id}"
            )

        if not machine_responses:
            raise ValueError(
                "The Coordinator did not "
                "receive any machine responses."
            )

        # Convert Pydantic objects into dictionaries.
        machine_data = [
            machine_response.model_dump()
            for machine_response
            in machine_responses
        ]

        # =================================================
        # STEP 2: Request quality assessments
        # =================================================
        print(
            "\nCoordinator is requesting "
            "quality assessments"
        )

        quality_request = (
            QualityAssessmentRequest(
                order_id=message.order_id,
                quality_requirement=(
                    message.quality_requirement
                ),
                machine_data=machine_data,
            )
        )

        quality_response = (
            await self.send_message(
                quality_request,
                recipient=self.quality_agent_id,
            )
        )

        if not isinstance(
            quality_response,
            QualityAssessmentResponse,
        ):
            raise TypeError(
                "The Quality Agent returned "
                "an invalid response."
            )

        if not quality_response.assessments:
            raise ValueError(
                "The Quality Agent returned "
                "no assessments."
            )

        print(
            "Coordinator received the "
            "quality assessments"
        )

        # =================================================
        # STEP 3: Request maintenance assessments
        # =================================================
        print(
            "\nCoordinator is requesting "
            "maintenance assessments"
        )

        maintenance_request = (
            MaintenanceAssessmentRequest(
                machine_data=machine_data,
            )
        )

        maintenance_response = (
            await self.send_message(
                maintenance_request,
                recipient=(
                    self.maintenance_agent_id
                ),
            )
        )

        if not isinstance(
            maintenance_response,
            MaintenanceAssessmentResponse,
        ):
            raise TypeError(
                "The Maintenance Agent "
                "returned an invalid response."
            )

        if not (
            maintenance_response.assessments
        ):
            raise ValueError(
                "The Maintenance Agent "
                "returned no assessments."
            )

        print(
            "Coordinator received the "
            "maintenance assessments"
        )

        # =================================================
        # STEP 4: Organize assessments by machine ID
        # =================================================
        quality_by_machine: dict[
            str,
            dict[str, Any],
        ] = {
            assessment["machine_id"]:
            assessment
            for assessment
            in quality_response.assessments
        }

        maintenance_by_machine: dict[
            str,
            dict[str, Any],
        ] = {
            assessment["machine_id"]:
            assessment
            for assessment
            in maintenance_response.assessments
        }

        suitable_machines: list[
            tuple[
                MachineStatusResponse,
                dict[str, Any],
                dict[str, Any],
            ]
        ] = []

        machines_filtered_out: list[
            dict[str, str]
        ] = []

        # =================================================
        # STEP 5: Apply rejection rules
        # =================================================
        print(
            "\nCoordinator is applying "
            "the decision rules"
        )

        for machine in machine_responses:
            rejection_reasons: list[str] = []

            quality_result = (
                quality_by_machine.get(
                    machine.machine_id
                )
            )

            maintenance_result = (
                maintenance_by_machine.get(
                    machine.machine_id
                )
            )

            # Rule 1: Machine must be available.
            if (
                machine.status.lower()
                != "available"
            ):
                rejection_reasons.append(
                    "machine is not available"
                )

            # Rule 2: Capability must match.
            if (
                machine.capability.lower()
                !=
                message.required_capability.lower()
            ):
                rejection_reasons.append(
                    "wrong capability"
                )

            # Rule 3: Deadline must be met.
            if (
                machine.
                estimated_processing_time_mins
                >
                message.deadline_minutes
            ):
                rejection_reasons.append(
                    "cannot meet the deadline"
                )

            # Rule 4: Quality assessment
            # must exist.
            if quality_result is None:
                rejection_reasons.append(
                    "quality assessment "
                    "is missing"
                )

            # Rule 5: Quality must pass.
            elif not quality_result.get(
                "is_suitable",
                False,
            ):
                rejection_reasons.append(
                    "failed the "
                    "quality assessment"
                )

            # Rule 6: Maintenance assessment
            # must exist.
            if maintenance_result is None:
                rejection_reasons.append(
                    "maintenance assessment "
                    "is missing"
                )

            # Rule 7: Maintenance must pass.
            elif (
                maintenance_result.get(
                    "availability_status",
                    "blocked",
                ).lower()
                != "available"
            ):
                rejection_reasons.append(
                    "failed the "
                    "maintenance assessment"
                )

            if rejection_reasons:
                machines_filtered_out.append(
                    {
                        "machine_id": (
                            machine.machine_id
                        ),
                        "reason": ", ".join(
                            rejection_reasons
                        ),
                    }
                )

                print(
                    f"{machine.machine_id} "
                    f"rejected: "
                    f"{', '.join(rejection_reasons)}"
                )

            else:
                suitable_machines.append(
                    (
                        machine,
                        quality_result,
                        maintenance_result,
                    )
                )

                print(
                    f"{machine.machine_id} "
                    f"passed all checks"
                )

        # =================================================
        # STEP 6: Select the best suitable machine
        # =================================================

        selected_machine: (
            MachineStatusResponse | None
        ) = None

        selected_quality: (
            dict[str, Any] | None
        ) = None

        selected_maintenance: (
            dict[str, Any] | None
        ) = None

        if suitable_machines:

            selected = min(
                suitable_machines,
                key=lambda result: (
                    result[0].queue_length,
                    result[1].get(
                        "quality_risk_score",
                        1.0,
                    ),
                    result[
                        0
                    ].estimated_processing_time_mins,
                ),
            )

            selected_machine = selected[0]
            selected_quality = selected[1]
            selected_maintenance = selected[2]

            selected_machine_id = (
                selected_machine.machine_id
            )

            required_actions = {
                "quality": (
                    selected_quality.get(
                        "recommended_action",
                        "none",
                    )
                ),
                "maintenance": (
                    selected_maintenance.get(
                        "maintenance_action_required",
                        "none",
                    )
                ),
            }

            recommendation = (
                f"Select machine "
                f"{selected_machine_id} "
                f"for order "
                f"{message.order_id}."
            )

            # Deterministic Python fallback.
            fallback_justification = (
                f"Machine "
                f"{selected_machine.machine_id} "
                f"was selected because it "
                f"has the required "
                f"{message.required_capability} "
                f"capability, is available, "
                f"can meet the deadline, and "
                f"passed the quality and "
                f"maintenance checks. "
                f"It was ranked above the "
                f"other suitable machines "
                f"based on queue length, "
                f"quality risk, and "
                f"processing time."
            )

        else:
            selected_machine_id = "none"

            required_actions = {
                "quality": "none",
                "maintenance": "none",
            }

            recommendation = (
                f"No suitable machine was "
                f"found for order "
                f"{message.order_id}."
            )

            fallback_justification = (
                "No machine satisfied all "
                "order, quality, maintenance, "
                "availability, capability, "
                "and deadline requirements."
            )

        # =================================================
        # STEP 7: Build structured evidence package
        # =================================================

        evidence: dict[str, Any] = {
            "order": {
                "order_id": (
                    message.order_id
                ),
                "priority": (
                    message.priority
                ),
                "required_capability": (
                    message.required_capability
                ),
                "deadline_minutes": (
                    message.deadline_minutes
                ),
                "quality_requirement": (
                    message.quality_requirement
                ),
            },

            "machine_statuses": [
                machine.model_dump()
                for machine
                in machine_responses
            ],

            "quality_assessments": (
                quality_response.assessments
            ),

            "maintenance_assessments": (
                maintenance_response.assessments
            ),

            "selected_machine": (
                selected_machine_id
            ),

            "rejected_machines": (
                machines_filtered_out
            ),

            "decision_rules": {
                "availability_required": True,
                "capability_must_match": True,
                "deadline_must_be_met": True,
                "quality_must_pass": True,
                "maintenance_must_pass": True,
            },

            "ranking_method": [
                "shortest_queue",
                "lowest_quality_risk",
                "shortest_processing_time",
            ],
        }

        # =================================================
        # STEP 8: Retrieve grounding information
        # =================================================

        retrieved_information = (
            self.retrieval_service.retrieve(
                evidence
            )
        )

        print(
            "Coordinator retrieved grounding information"
        )

        # =================================================
        # STEP 9: Generate grounded reasoning
        # =================================================

        # Track whether the final explanation came from Gemini
        # or from the deterministic Python fallback.
        gemini_used = True
        fallback_reason = "none"

        if selected_machine is not None:

            reasoning = (
                await self.
                _generate_gemini_explanation(
                    order=message,

                    selected_machine=(
                        selected_machine
                    ),

                    quality_result=(
                        selected_quality
                        if (
                            selected_quality
                            is not None
                        )
                        else {}
                    ),

                    maintenance_result=(
                        selected_maintenance
                        if (
                            selected_maintenance
                            is not None
                        )
                        else {}
                    ),

                    filtered_machines=(
                        machines_filtered_out
                    ),

                    retrieved_information=(
                        retrieved_information
                    ),

                    fallback=(
                        fallback_justification
                    ),
                )
            )

            if reasoning == fallback_justification:
                gemini_used = False
                fallback_reason = "gemini_failure"

        else:

            reasoning = (
                await self.
                _generate_no_selection_explanation(
                    order=message,

                    filtered_machines=(
                        machines_filtered_out
                    ),

                    retrieved_information=(
                        retrieved_information
                    ),

                    fallback=(
                        fallback_justification
                    ),
                )
            )

            if reasoning == fallback_justification:
                gemini_used = False
                fallback_reason = "gemini_failure"

        # =================================================
        # STEP 10: Send reasoning to Verification Agent
        # =================================================

        print(
            "\nCoordinator is requesting "
            "verification"
        )

        verification_request = (
            VerificationRequest(
                order_id=message.order_id,

                selected_machine=(
                    selected_machine_id
                ),

                reasoning=reasoning,

                evidence=evidence,

                retrieved_information=(
                    retrieved_information
                ),

                fallback_explanation=(
                    fallback_justification
                ),
            )
        )

        verification_response = (
            await self.send_message(
                verification_request,
                recipient=(
                    self.verification_agent_id
                ),
            )
        )

        if not isinstance(
            verification_response,
            VerificationResponse,
        ):
            raise TypeError(
                "The Verification Agent "
                "returned an invalid response."
            )

        print(
            f"Verification status: "
            f"{verification_response.status}"
        )

        # =================================================
        # STEP 11: Apply verification result
        # =================================================

        if (
            verification_response.status.lower()
            == "passed"
        ):
            verified_reasoning = (
                verification_response.
                verified_explanation
            )

            print(
                "Gemini explanation "
                "passed verification."
            )

        else:
            verified_reasoning = (
                fallback_justification
            )

            fallback_reason = "verification_failure"

            print(
                "Gemini explanation failed "
                "verification."
            )

            print(
                "Using deterministic "
                "Python explanation."
            )

        verification_result = {
            "status": (
                verification_response.status
            ),

            "issues_found": (
                verification_response.
                issues_found
            ),

            "verified_explanation": (
                verified_reasoning
            ),

            "used_fallback": (
                verification_response.used_fallback
                or not gemini_used
            ),

            "fallback_reason": (
                fallback_reason
            ),

            "gemini_used": (
                gemini_used
            ),
        }

        # =================================================
        # STEP 12: Create final recommendation
        # =================================================

        final_recommendation = (
            FinalRecommendation(
                order_id=(
                    message.order_id
                ),

                selected_machine=(
                    selected_machine_id
                ),

                recommendation=(
                    recommendation
                ),

                # Important:
                # This now contains the
                # VERIFIED explanation.
                reasoning=(
                    verified_reasoning
                ),

                evidence=evidence,

                required_actions=(
                    required_actions
                ),

                machines_filtered_out=(
                    machines_filtered_out
                ),

                retrieved_information=(
                    retrieved_information
                ),

                verification_result=(
                    verification_result
                ),

                # Temporary compatibility
                # with your current UI.
                justification=(
                    verified_reasoning
                ),
            )
        )

        # =================================================
        # Show result in terminal
        # =================================================

        return final_recommendation

    # =====================================================
    # Grounded Gemini explanation
    # =====================================================

    async def _generate_gemini_explanation(
        self,
        order: OrderMessage,
        selected_machine: MachineStatusResponse,
        quality_result: dict[str, Any],
        maintenance_result: dict[str, Any],
        filtered_machines: list[
            dict[str, str]
        ],
        retrieved_information: list[
            dict[str, Any]
        ],
        fallback: str,
    ) -> str:
        """
        Ask Gemini to explain an already
        completed machine-selection decision.

        Gemini does not select the machine.
        """

        if self.gemini_client is None:
            print(
                "\nGemini API key was not "
                "found. Using the Python "
                "explanation."
            )

            return fallback

        prompt = f"""
You are explaining a manufacturing machine-allocation decision.

The machine has already been selected using deterministic Python
decision rules.

You are NOT responsible for selecting the machine.

STRICT GROUNDING RULES:

1. Use only the supplied evidence and retrieved information.
2. Never invent machine values.
3. Never change the selected machine.
4. Never change the decision produced by the Coordinator.
5. Never assume missing information.
6. If a value is not present, do not mention it.
7. Every factual statement must be supported by the supplied data.
8. Do not claim that a rejected machine passed a check that it failed.

ORDER:
- Order ID: {order.order_id}
- Required capability: {order.required_capability}
- Deadline: {order.deadline_minutes} minutes
- Quality requirement: {order.quality_requirement}

SELECTED MACHINE:
- Machine ID: {selected_machine.machine_id}
- Status: {selected_machine.status}
- Capability: {selected_machine.capability}
- Queue length: {selected_machine.queue_length}
- Estimated processing time:
  {selected_machine.estimated_processing_time_mins} minutes
- Maintenance condition:
  {selected_machine.maintenance_condition}
- Active warnings:
  {selected_machine.active_warnings}

QUALITY ASSESSMENT:
{quality_result}

MAINTENANCE ASSESSMENT:
{maintenance_result}

REJECTED MACHINES:
{filtered_machines}

RETRIEVED SUPPORTING INFORMATION:
{retrieved_information}

Explain clearly why the selected machine was chosen.

Mention the strongest evidence supporting the decision.

Mention relevant ranking factors when supported by the data.

If useful, briefly explain why an important rejected machine
was not selected.

Use two or three short sentences.

Do not use headings.

Do not use bullet points.
""".strip()

        try:
            response = (
                await self.gemini_client.
                aio.models.generate_content(
                    model=(
                        self.gemini_model
                    ),
                    contents=prompt,
                )
            )

            if (
                response.text
                and response.text.strip()
            ):
                print("Gemini generated grounded explanation")

                return (
                    response.text.strip()
                )

            print(
                "\nGemini returned an empty "
                "explanation. Using the "
                "Python explanation."
            )

            return fallback

        except Exception as error:

            print(
                f"\nGemini explanation "
                f"failed: {error}"
            )

            print(
                "Using the Python "
                "explanation instead."
            )

            return fallback

    # =====================================================
    # Grounded no-selection explanation
    # =====================================================

    async def _generate_no_selection_explanation(
        self,
        order: OrderMessage,
        filtered_machines: list[
            dict[str, str]
        ],
        retrieved_information: list[
            dict[str, Any]
        ],
        fallback: str,
    ) -> str:
        """
        Ask Gemini to explain why no
        machine was selected.
        """

        if self.gemini_client is None:
            return fallback

        prompt = f"""
You are explaining a manufacturing machine-allocation result.

No machine was selected because every machine failed at least one
deterministic Python decision rule.

STRICT GROUNDING RULES:

1. Use only the information supplied below.
2. Do not invent machine values.
3. Do not recommend a different machine.
4. Do not assume missing information.
5. Every factual statement must match the supplied evidence.
6. Do not claim that a rejected machine passed a failed check.

ORDER:
- Order ID: {order.order_id}
- Required capability: {order.required_capability}
- Deadline: {order.deadline_minutes} minutes
- Quality requirement: {order.quality_requirement}

REJECTED MACHINES:
{filtered_machines}

RETRIEVED SUPPORTING INFORMATION:
{retrieved_information}

Explain clearly why no machine was selected.

Use two short sentences.

Do not use headings.

Do not use bullet points.
""".strip()

        try:
            response = (
                await self.gemini_client.
                aio.models.generate_content(
                    model=(
                        self.gemini_model
                    ),
                    contents=prompt,
                )
            )

            if (
                response.text
                and response.text.strip()
            ):
                return (
                    response.text.strip()
                )

            return fallback

        except Exception as error:

            print(
                f"\nGemini no-selection "
                f"explanation failed: "
                f"{error}"
            )

            return fallback
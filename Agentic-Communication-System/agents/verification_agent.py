from __future__ import annotations
import re
from typing import Any

from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,)

from messages.verification_request import VerificationRequest
from messages.verification_response import VerificationResponse

class VerificationAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__(
            description=(
                "Verifies that Gemini reasoning matches "
                "the structured manufacturing evidence."
            )
        )

    @message_handler
    async def handle_verification_request(
        self,
        message: VerificationRequest,
        ctx: MessageContext,
    ) -> VerificationResponse:

        print("\nVerification Agent received a request")

        issues_found: list[str] = []

        evidence = message.evidence
        reasoning = message.reasoning
        selected_machine_id = message.selected_machine

        order_data = evidence.get(
            "order",
            {},)

        machine_statuses = evidence.get(
            "machine_statuses",
            [],)

        quality_assessments = evidence.get(
            "quality_assessments",
            [],)

        maintenance_assessments = evidence.get(
            "maintenance_assessments",
            [],)

        rejected_machines = evidence.get(
            "rejected_machines",
            [],)

        # NO MACHINE SELECTED

        if selected_machine_id == "none":

            if not rejected_machines:
                issues_found.append(
                    "No machine was selected, but no rejection "
                    "evidence was provided."
                )

            return self._build_response(
                issues_found,
                reasoning,
                message.fallback_explanation,
            )

        # FIND SELECTED MACHINE

        selected_machine = next(
            (
                machine
                for machine in machine_statuses
                if machine.get("machine_id")
                == selected_machine_id
            ),
            None,
        )

        if selected_machine is None:

            issues_found.append(
                "The selected machine does not exist "
                "in the evidence."
            )

            return self._build_response(
                issues_found,
                reasoning,
                message.fallback_explanation,
            )

        # MACHINE VALUES

        status = str(
            selected_machine.get(
                "status",
                "",
            )
        ).lower()

        capability = str(
            selected_machine.get(
                "capability",
                "",
            )
        ).lower()

        queue_length = selected_machine.get(
            "queue_length"
        )

        processing_time = selected_machine.get(
            "estimated_processing_time_mins"
        )

        maintenance_condition = selected_machine.get(
            "maintenance_condition"
        )

        required_capability = str(
            order_data.get(
                "required_capability",
                "",
            )
        ).lower()

        deadline = order_data.get(
            "deadline_minutes"
        )

        # BASIC DECISION CHECKS

        if status != "available":
            issues_found.append(
                "The selected machine is not available."
            )

        if capability != required_capability:
            issues_found.append(
                "The selected machine capability does not "
                "match the order requirement."
            )

        if (
            processing_time is not None
            and deadline is not None
            and float(processing_time) > float(deadline)
        ):
            issues_found.append(
                "The selected machine cannot meet the deadline."
            )

        # =================================================
        # QUALITY CHECK
        # =================================================

        selected_quality = next(
            (
                assessment
                for assessment in quality_assessments
                if assessment.get("machine_id")
                == selected_machine_id
            ),
            None,
        )

        if selected_quality is None:

            issues_found.append(
                "Quality assessment for the selected "
                "machine is missing."
            )

        elif not selected_quality.get(
            "is_suitable",
            False,
        ):

            issues_found.append(
                "The selected machine failed "
                "the quality assessment."
            )

        # =================================================
        # MAINTENANCE CHECK
        # =================================================

        selected_maintenance = next(
            (
                assessment
                for assessment in maintenance_assessments
                if assessment.get("machine_id")
                == selected_machine_id
            ),
            None,
        )

        if selected_maintenance is None:

            issues_found.append(
                "Maintenance assessment for the selected "
                "machine is missing."
            )

        elif (
            str(
                selected_maintenance.get(
                    "availability_status",
                    "",
                )
            ).lower()
            != "available"
        ):

            issues_found.append(
                "The selected machine failed "
                "the maintenance assessment."
            )

        # =================================================
        # WRONG SELECTED MACHINE CLAIM
        # =================================================

        selected_claim = re.search(
            r"(?:machine\s+)?(M\d{2})\s+"
            r"(?:was\s+)?selected",
            reasoning,
            flags=re.IGNORECASE,
        )

        if selected_claim:

            claimed_machine = (
                selected_claim.group(1).upper()
            )

            if (
                claimed_machine
                != selected_machine_id.upper()
            ):

                issues_found.append(
                    "The explanation identifies the wrong "
                    "machine as selected."
                )

        # =================================================
        # WRONG CAPABILITY CLAIM
        # =================================================

        capability_claim = re.search(
            r"(?:required\s+)?"
            r"(milling|turning|drilling)\s+capability",
            reasoning,
            flags=re.IGNORECASE,
        )

        if capability_claim:

            claimed_capability = (
                capability_claim.group(1).lower()
            )

            if claimed_capability != capability:

                issues_found.append(
                    "The explanation states capability "
                    f"{claimed_capability}, but the evidence "
                    f"contains {capability}."
                )

        # =================================================
        # QUEUE LENGTH CLAIM
        # =================================================

        self._check_numeric_patterns(
            reasoning=reasoning,
            label="queue length",
            expected_value=queue_length,
            patterns=[
                r"queue\s+length\s*(?:is|of|:)?\s*(\d+(?:\.\d+)?)",
                r"queue\s*(?:is|of|:)?\s*(\d+(?:\.\d+)?)",
            ],
            issues_found=issues_found,
        )

        # =================================================
        # PROCESSING TIME CLAIM
        # =================================================

        self._check_numeric_patterns(
            reasoning=reasoning,
            label="processing time",
            expected_value=processing_time,
            patterns=[
                (
                    r"(?:processing|completion)\s+time\s*"
                    r"(?:is|of|:)?\s*"
                    r"(\d+(?:\.\d+)?)\s*"
                    r"(?:minutes?|mins?)"
                ),
                (
                    r"in\s+"
                    r"(\d+(?:\.\d+)?)\s*"
                    r"(?:minutes?|mins?)"
                ),
            ],
            issues_found=issues_found,
        )

        # =================================================
        # MAINTENANCE CONDITION CLAIM
        # =================================================

        self._check_maintenance_claim(
            reasoning=reasoning,
            expected_value=maintenance_condition,
            issues_found=issues_found,
        )

        # =================================================
        # QUALITY RISK CLAIM
        # =================================================

        if selected_quality is not None:

            quality_risk = selected_quality.get(
                "quality_risk_score"
            )

            self._check_numeric_patterns(
                reasoning=reasoning,
                label="quality risk score",
                expected_value=quality_risk,
                patterns=[
                    (
                        r"(?:quality\s+)?risk\s+score\s*"
                        r"(?:is|of|:)?\s*"
                        r"(\d+(?:\.\d+)?)"
                    ),
                ],
                issues_found=issues_found,
            )

        # =================================================
        # REJECTED MACHINE CHECKS
        # =================================================

        for rejected in rejected_machines:

            machine_id = rejected.get(
                "machine_id"
            )

            reason = rejected.get(
                "reason"
            )

            if not machine_id:

                issues_found.append(
                    "A rejected machine entry is missing "
                    "its machine ID."
                )

            if not reason:

                issues_found.append(
                    f"Rejected machine {machine_id} has "
                    "no rejection reason."
                )

        # =================================================
        # RETURN RESULT
        # =================================================

        return self._build_response(
            issues_found,
            reasoning,
            message.fallback_explanation,
        )

    # =====================================================
    # NUMERIC CHECK HELPER
    # =====================================================

    def _check_numeric_patterns(
        self,
        reasoning: str,
        label: str,
        expected_value: Any,
        patterns: list[str],
        issues_found: list[str],
    ) -> None:

        if expected_value is None:
            return

        for pattern in patterns:

            match = re.search(
                pattern,
                reasoning,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            claimed_value = float(
                match.group(1)
            )

            expected_number = float(
                expected_value
            )

            if abs(
                claimed_value
                - expected_number
            ) > 0.0001:

                issues_found.append(
                    f"The explanation states {label} "
                    f"{claimed_value}, but the evidence "
                    f"contains {expected_number}."
                )

            return

    # MAINTENANCE CHECK HELPER

    def _check_maintenance_claim(
        self,
        reasoning: str,
        expected_value: Any,
        issues_found: list[str],
    ) -> None:

        if expected_value is None:
            return

        # Example: maintenance condition is 0.82
        decimal_match = re.search(
            (
                r"maintenance\s+(?:condition|score)\s*"
                r"(?:is|of|:)?\s*"
                r"(0(?:\.\d+)?)"
            ),
            reasoning,
            flags=re.IGNORECASE,
        )

        if decimal_match:

            claimed = float(
                decimal_match.group(1)
            )

            expected = float(
                expected_value
            )

            if abs(
                claimed
                - expected
            ) > 0.0001:

                issues_found.append(
                    "The explanation contains an incorrect "
                    "maintenance condition."
                )

            return

        # Example: maintenance condition is 82%
        percentage_match = re.search(
            (
                r"maintenance\s+(?:condition|score)\s*"
                r"(?:is|of|:)?\s*"
                r"(\d+(?:\.\d+)?)\s*%"
            ),
            reasoning,
            flags=re.IGNORECASE,
        )

        if percentage_match:

            claimed_percent = float(
                percentage_match.group(1)
            )

            expected_percent = (
                float(
                    expected_value
                )
                * 100
            )

            if abs(
                claimed_percent
                - expected_percent
            ) > 0.01:

                issues_found.append(
                    "The explanation contains an incorrect "
                    "maintenance condition."
                )

    # RESPONSE BUILDER

    def _build_response(
        self,
        issues_found: list[str],
        reasoning: str,
        fallback: str,
    ) -> VerificationResponse:

        if issues_found:

            print(
                "Verification failed: "
                f"{len(issues_found)} issue(s) found."
            )

            for issue in issues_found:

                print(
                    f"- {issue}"
                )

            return VerificationResponse(
                status="failed",
                issues_found=issues_found,
                verified_explanation=fallback,
                used_fallback=True,
            )

        print(
            "Verification passed"
        )

        return VerificationResponse(
            status="passed",
            issues_found=[],
            verified_explanation=reasoning,
            used_fallback=False,
        )

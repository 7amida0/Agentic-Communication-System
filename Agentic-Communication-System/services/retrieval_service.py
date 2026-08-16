from typing import Any

class RetrievalService:

    def retrieve(
        self,
        evidence: dict[str, Any],
    ) -> list[dict[str, Any]]:
        retrieved_information: list[dict[str, Any]] = []

        selected_machine_id = evidence.get(
            "selected_machine",
            "none",)

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

        # -------------------------------------------------
        # Retrieve selected machine information
        # -------------------------------------------------
        selected_machine = next(
            (
                machine
                for machine in machine_statuses
                if machine.get("machine_id")
                == selected_machine_id
            ),
            None,
        )

        if selected_machine:
            retrieved_information.append(
                {
                    "type": "selected_machine_status",
                    "machine_id": selected_machine_id,
                    "data": selected_machine,
                }
            )

        # -------------------------------------------------
        # Retrieve selected machine quality assessment
        # -------------------------------------------------
        selected_quality = next(
            (
                assessment
                for assessment in quality_assessments
                if assessment.get("machine_id")
                == selected_machine_id
            ),
            None,
        )

        if selected_quality:
            retrieved_information.append(
                {
                    "type": "quality_assessment",
                    "machine_id": selected_machine_id,
                    "data": selected_quality,
                }
            )

        # -------------------------------------------------
        # Retrieve selected machine maintenance assessment
        # -------------------------------------------------
        selected_maintenance = next(
            (
                assessment
                for assessment in maintenance_assessments
                if assessment.get("machine_id")
                == selected_machine_id
            ),
            None,
        )

        if selected_maintenance:
            retrieved_information.append(
                {
                    "type": "maintenance_assessment",
                    "machine_id": selected_machine_id,
                    "data": selected_maintenance,
                }
            )

        # -------------------------------------------------
        # Retrieve rejected machine reasons
        # -------------------------------------------------
        for rejected_machine in rejected_machines:
            retrieved_information.append(
                {
                    "type": "rejected_machine",
                    "machine_id": rejected_machine.get(
                        "machine_id"
                    ),
                    "data": rejected_machine,
                }
            )

        # -------------------------------------------------
        # Retrieve decision rules
        # -------------------------------------------------
        decision_rules = evidence.get(
            "decision_rules",
            {},
        )

        if decision_rules:
            retrieved_information.append(
                {
                    "type": "decision_rules",
                    "data": decision_rules,
                }
            )

        # -------------------------------------------------
        # Retrieve ranking method
        # -------------------------------------------------
        ranking_method = evidence.get(
            "ranking_method",
            [],
        )

        if ranking_method:
            retrieved_information.append(
                {
                    "type": "ranking_method",
                    "data": ranking_method,
                }
            )

        return retrieved_information
import asyncio

from agents.verification_agent import VerificationAgent
from messages.verification_request import VerificationRequest


async def main() -> None:
    agent = VerificationAgent()

    evidence = {
        "order": {
            "order_id": "ORD-TEST-003",
            "priority": "high",
            "required_capability": "milling",
            "deadline_minutes": 120,
            "quality_requirement": "strict",
        },
        "machine_statuses": [
            {
                "machine_id": "M02",
                "status": "available",
                "capability": "milling",
                "queue_length": 1,
                "estimated_processing_time_mins": 60,
                "maintenance_condition": 0.82,
                "active_warnings": ["minor_vibration"],
            }
        ],
        "quality_assessments": [
            {
                "machine_id": "M02",
                "quality_risk_score": 0.3,
                "recommended_action": "continue production with observation",
                "is_suitable": True,
            }
        ],
        "maintenance_assessments": [
            {
                "machine_id": "M02",
                "availability_status": "available",
                "maintenance_action_required": "none",
            }
        ],
        "selected_machine": "M02",
        "rejected_machines": [],
    }

    fake_reasoning = (
        "Machine M02 was selected because its processing time is 40 minutes."
    )

    request = VerificationRequest(
        order_id="ORD-TEST-003",
        selected_machine="M02",
        reasoning=fake_reasoning,
        evidence=evidence,
        retrieved_information=[],
        fallback_explanation=(
            "Machine M02 has a processing time of 60 minutes."
        ),
    )

    response = await agent.handle_verification_request(
        request,
        None,
    )

    print("\nTEST: WRONG PROCESSING TIME")
    print("Expected: FAILED")
    print("Actual:", response.status.upper())
    print("Issues:", response.issues_found)
    print("Fallback Used:", response.used_fallback)

    if response.status.lower() == "failed":
        print("TEST PASSED")
    else:
        print("TEST FAILED")


if __name__ == "__main__":
    asyncio.run(main())
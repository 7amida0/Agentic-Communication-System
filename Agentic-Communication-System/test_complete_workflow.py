import asyncio

from workflow_runner import run_allocation


async def run_test(
    test_name: str,
    order_id: str,
    priority: str,
    capability: str,
    deadline: int,
    quality: str,
    expected_machine: str | None,
) -> None:

    print("\n" + "=" * 70)
    print(test_name)
    print("=" * 70)

    print("\nINPUT")
    print(f"Order ID: {order_id}")
    print(f"Priority: {priority}")
    print(f"Capability: {capability}")
    print(f"Deadline: {deadline}")
    print(f"Quality: {quality}")

    result = await run_allocation(
        order_id=order_id,
        priority=priority,
        required_capability=capability,
        deadline_minutes=deadline,
        quality_requirement=quality,
    )

    print("\nRESULT")
    print(f"Selected Machine: {result.selected_machine}")
    print(f"Recommendation: {result.recommendation}")
    print(f"Reasoning: {result.reasoning}")

    print("\nRETRIEVAL")
    print(
        f"Retrieved items: "
        f"{len(result.retrieved_information)}"
    )

    print("\nVERIFICATION")

    verification = result.verification_result

    print(
        f"Status: "
        f"{verification.get('status')}"
    )

    print(
        f"Issues: "
        f"{verification.get('issues_found')}"
    )

    print(
        f"Fallback Used: "
        f"{verification.get('used_fallback')}"
    )

    print("\nEVIDENCE")

    evidence = result.evidence

    print(
        "Machine statuses:",
        len(
            evidence.get(
                "machine_statuses",
                [],
            )
        ),
    )

    print(
        "Quality assessments:",
        len(
            evidence.get(
                "quality_assessments",
                [],
            )
        ),
    )

    print(
        "Maintenance assessments:",
        len(
            evidence.get(
                "maintenance_assessments",
                [],
            )
        ),
    )

    # -----------------------------------------------------
    # Automatic checks
    # -----------------------------------------------------

    problems = []

    if expected_machine is not None:

        if result.selected_machine != expected_machine:

            problems.append(
                f"Expected selected machine "
                f"{expected_machine}, "
                f"but received "
                f"{result.selected_machine}."
            )

    if not result.recommendation:

        problems.append(
            "Recommendation is missing."
        )

    if not result.reasoning:

        problems.append(
            "Reasoning is missing."
        )

    if not result.evidence:

        problems.append(
            "Evidence package is missing."
        )

    if not result.retrieved_information:

        problems.append(
            "Retrieved information is missing."
        )

    if (
        verification.get(
            "status"
        )
        not in [
            "passed",
            "failed",
        ]
    ):

        problems.append(
            "Verification did not run."
        )

    # -----------------------------------------------------
    # Final test status
    # -----------------------------------------------------

    if problems:

        print("\nWORKFLOW TEST FAILED")

        for problem in problems:

            print(
                "-",
                problem,
            )

    else:

        print(
            "\nWORKFLOW TEST PASSED"
        )


async def main() -> None:

    # =====================================================
    # TEST 1
    # Normal milling order
    # =====================================================

    await run_test(
        test_name=(
            "TEST 1 - NORMAL MILLING ORDER"
        ),
        order_id="ORD-WF-001",
        priority="high",
        capability="milling",
        deadline=120,
        quality="strict",
        expected_machine="M02",
    )

    # =====================================================
    # TEST 2
    # Turning order
    #
    # M03 has turning capability but has critical_fault
    # and poor maintenance condition.
    # Therefore no machine should be selected.
    # =====================================================

    await run_test(
        test_name=(
            "TEST 2 - TURNING ORDER"
        ),
        order_id="ORD-WF-002",
        priority="high",
        capability="turning",
        deadline=120,
        quality="strict",
        expected_machine="none",
    )

    # =====================================================
    # TEST 3
    # Impossible milling deadline
    #
    # M01 = 45 minutes
    # M02 = 60 minutes
    #
    # Deadline = 30 minutes
    #
    # Therefore neither milling machine can meet it.
    # =====================================================

    await run_test(
        test_name=(
            "TEST 3 - IMPOSSIBLE DEADLINE"
        ),
        order_id="ORD-WF-003",
        priority="urgent",
        capability="milling",
        deadline=30,
        quality="strict",
        expected_machine="none",
    )

    # =====================================================
    # TEST 4
    # Standard milling order
    # =====================================================

    await run_test(
        test_name=(
            "TEST 4 - STANDARD QUALITY MILLING"
        ),
        order_id="ORD-WF-004",
        priority="medium",
        capability="milling",
        deadline=120,
        quality="standard",
        expected_machine="M02",
    )


if __name__ == "__main__":

    asyncio.run(
        main()
    )
import asyncio

from autogen_core import AgentId, SingleThreadedAgentRuntime

from agents.machine_agent import MachineAgent
from agents.quality_agent import QualityAgent
from agents.maintenance_agent import MaintenanceAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.verification_agent import VerificationAgent

from messages.order_message import OrderMessage

from colorama import Fore, Style, init


init(autoreset=True)


async def main() -> None:

    # =================================================
    # CREATE AUTOGEN RUNTIME
    # =================================================

    runtime = SingleThreadedAgentRuntime()

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "       SCENARIO 2 - RISK CONFLICT SCENARIO"
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )

    # =================================================
    # REGISTER MACHINE AGENTS
    # =================================================

    machine_m01 = MachineAgent(
        machine_id="M01",
        status="available",
        capability="milling",
        queue_length=2,
        estimated_processing_time_mins=45,
        maintenance_condition=0.85,
        active_warnings=[],
    )

    await machine_m01.register_instance(
        runtime,
        AgentId("machine_agent", "M01"),
    )

    machine_m02 = MachineAgent(
        machine_id="M02",
        status="available",
        capability="turning",
        queue_length=1,
        estimated_processing_time_mins=30,
        maintenance_condition=0.90,
        active_warnings=[],
    )

    await machine_m02.register_instance(
        runtime,
        AgentId("machine_agent", "M02"),
    )

    machine_m03 = MachineAgent(
        machine_id="M03",
        status="available",
        capability="milling",
        queue_length=0,
        estimated_processing_time_mins=25,
        maintenance_condition=0.40,
        active_warnings=["critical_fault"],
    )

    await machine_m03.register_instance(
        runtime,
        AgentId("machine_agent", "M03"),
    )

    # =================================================
    # REGISTER SPECIALIST AGENTS
    # =================================================

    await QualityAgent.register(
        runtime,
        "quality_agent",
        lambda: QualityAgent(),
    )

    await MaintenanceAgent.register(
        runtime,
        "maintenance_agent",
        lambda: MaintenanceAgent(),
    )

    await VerificationAgent.register(
        runtime,
        "verification_agent",
        lambda: VerificationAgent(),
    )

    # =================================================
    # REGISTER COORDINATOR AGENT
    # =================================================

    await CoordinatorAgent.register(
        runtime,
        "coordinator_agent",
        lambda: CoordinatorAgent(),
    )

    # =================================================
    # START RUNTIME
    # =================================================

    runtime.start()

    # =================================================
    # CREATE RISK-CONFLICT ORDER
    # =================================================

    order = OrderMessage(
        order_id="ORD-SC2-001",
        priority="urgent",
        required_capability="milling",
        deadline_minutes=120,
        quality_requirement="strict",
    )

    # =================================================
    # SCENARIO INPUT
    # =================================================

    print()
    print(
        Fore.YELLOW
        + Style.BRIGHT
        + "SCENARIO INPUT"
    )

    print(f"  Order ID: {order.order_id}")
    print(f"  Priority: {order.priority}")
    print(f"  Required Capability: {order.required_capability}")
    print(f"  Deadline: {order.deadline_minutes} minutes")
    print(f"  Quality Requirement: {order.quality_requirement}")

    # =================================================
    # MACHINE CONDITIONS
    # =================================================

    print()
    print(
        Fore.BLUE
        + Style.BRIGHT
        + "MACHINE CONDITIONS"
    )

    print()

    print(
        Fore.GREEN
        + "M01"
        + Style.RESET_ALL
        + " -> Available | Milling | "
        + "Queue: 2 | "
        + "Processing: 45 min | "
        + "Maintenance: 0.85 | "
        + "Warnings: None"
    )

    print(
        Fore.YELLOW
        + "M02"
        + Style.RESET_ALL
        + " -> Available | Turning | "
        + "Queue: 1 | "
        + "Processing: 30 min | "
        + "Maintenance: 0.90 | "
        + "Warnings: None"
    )

    print(
        Fore.RED
        + Style.BRIGHT
        + "M03"
        + Style.RESET_ALL
        + " -> Available | Milling | "
        + "Queue: 0 | "
        + "Processing: 25 min | "
        + "Maintenance: 0.40 | "
        + "Warnings: critical_fault"
    )

    print()
    print(
        Fore.RED
        + Style.BRIGHT
        + "IMPORTANT:"
    )

    print(
        "M03 is the fastest suitable machine "
        "based on processing time and queue."
    )

    print(
        "However, M03 has a critical fault "
        "and poor maintenance condition."
    )

    # =================================================
    # START DECISION PROCESS
    # =================================================

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "STARTING MULTI-AGENT DECISION PROCESS..."
    )

    final_response = await runtime.send_message(
        order,
        recipient=AgentId(
            "coordinator_agent",
            "default",
        ),
    )

    # =================================================
    # FINAL RECOMMENDATION
    # =================================================

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "              FINAL RECOMMENDATION"
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )

    if final_response is None:

        print()
        print(
            Fore.RED
            + "The Coordinator did not return a response."
        )

        await runtime.stop_when_idle()
        return

    # =================================================
    # RECOMMENDATION
    # =================================================

    print()
    print(
        Fore.YELLOW
        + Style.BRIGHT
        + "Recommendation:"
    )

    print(
        f"  {final_response.recommendation}"
    )

    # =================================================
    # SELECTED MACHINE
    # =================================================

    print()
    print(
        Fore.GREEN
        + Style.BRIGHT
        + "Selected Machine:"
    )

    print(
        f"  {final_response.selected_machine}"
    )

    # =================================================
    # REASONING
    # =================================================

    print()
    print(
        Fore.MAGENTA
        + Style.BRIGHT
        + "Reasoning:"
    )

    print(
        f"  {final_response.reasoning}"
    )

    # =================================================
    # REQUIRED ACTIONS
    # =================================================

    print()
    print(
        Fore.YELLOW
        + Style.BRIGHT
        + "Required Actions:"
    )

    for action, value in final_response.required_actions.items():

        print(
            f"  {action}: {value}"
        )

    # =================================================
    # REJECTED MACHINES
    # =================================================

    print()
    print(
        Fore.RED
        + Style.BRIGHT
        + "Rejected Machines:"
    )

    rejected = final_response.machines_filtered_out

    if rejected:

        for machine in rejected:

            print(
                f"  {machine['machine_id']} "
                f"-> {machine['reason']}"
            )

    else:

        print("  None")

    # =================================================
    # EVIDENCE
    # =================================================

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "                    EVIDENCE"
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )

    evidence = final_response.evidence

    # =================================================
    # ORDER EVIDENCE
    # =================================================

    order_evidence = evidence.get(
        "order",
        {},
    )

    print()
    print(
        Fore.BLUE
        + Style.BRIGHT
        + "Order:"
    )

    print(
        f"  Order ID: "
        f"{order_evidence.get('order_id')}"
    )

    print(
        f"  Capability: "
        f"{order_evidence.get('required_capability')}"
    )

    print(
        f"  Deadline: "
        f"{order_evidence.get('deadline_minutes')} minutes"
    )

    print(
        f"  Quality Requirement: "
        f"{order_evidence.get('quality_requirement')}"
    )

    # =================================================
    # MACHINE STATUS EVIDENCE
    # =================================================

    print()
    print(
        Fore.BLUE
        + Style.BRIGHT
        + "Machine Status Evidence:"
    )

    for machine in evidence.get(
        "machine_statuses",
        [],
    ):

        print()
        print(
            f"  {machine.get('machine_id')}:"
        )

        print(
            f"    Status: "
            f"{machine.get('status')}"
        )

        print(
            f"    Capability: "
            f"{machine.get('capability')}"
        )

        print(
            f"    Queue Length: "
            f"{machine.get('queue_length')}"
        )

        print(
            f"    Processing Time: "
            f"{machine.get('estimated_processing_time_mins')} min"
        )

        print(
            f"    Maintenance Condition: "
            f"{machine.get('maintenance_condition')}"
        )

        warnings = machine.get(
            "active_warnings",
            [],
        )

        print(
            f"    Warnings: "
            f"{', '.join(warnings) if warnings else 'None'}"
        )

    # =================================================
    # QUALITY ASSESSMENTS
    # =================================================

    print()
    print(
        Fore.BLUE
        + Style.BRIGHT
        + "Quality Assessments:"
    )

    for assessment in evidence.get(
        "quality_assessments",
        [],
    ):

        print(
            f"  {assessment.get('machine_id')}"
            f" -> Risk: "
            f"{assessment.get('quality_risk_score')}"
            f" | Suitable: "
            f"{assessment.get('is_suitable')}"
            f" | Action: "
            f"{assessment.get('recommended_action')}"
        )

    # =================================================
    # MAINTENANCE ASSESSMENTS
    # =================================================

    print()
    print(
        Fore.BLUE
        + Style.BRIGHT
        + "Maintenance Assessments:"
    )

    for assessment in evidence.get(
        "maintenance_assessments",
        [],
    ):

        print(
            f"  {assessment.get('machine_id')}"
            f" -> Status: "
            f"{assessment.get('availability_status')}"
            f" | Action: "
            f"{assessment.get('maintenance_action_required')}"
        )

    # =================================================
    # VERIFICATION
    # =================================================

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "                 VERIFICATION"
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )

    verification = final_response.verification_result

    status = verification.get(
        "status",
        "unknown",
    )

    print()

    if status == "passed":

        print(
            Fore.GREEN
            + Style.BRIGHT
            + f"Status: {status}"
        )

    else:

        print(
            Fore.RED
            + Style.BRIGHT
            + f"Status: {status}"
        )

    print(
        f"Issues Found: "
        f"{verification.get('issues_found')}"
    )

    print(
        f"Gemini Used: "
        f"{verification.get('gemini_used')}"
    )

    print(
        f"Fallback Used: "
        f"{verification.get('used_fallback')}"
    )

    # =================================================
    # SCENARIO VALIDATION
    # =================================================

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "             SCENARIO VALIDATION"
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )

    print()

    # Check selected machine

    if final_response.selected_machine == "M01":

        print(
            Fore.GREEN
            + "PASS: Safe machine M01 was selected."
        )

    else:

        print(
            Fore.RED
            + "FAIL: M01 was not selected."
        )

    # Check M03 rejection

    m03_rejected = any(
        machine.get("machine_id") == "M03"
        for machine in rejected
    )

    print()

    if m03_rejected:

        print(
            Fore.GREEN
            + "PASS: Risky machine M03 was rejected."
        )

    else:

        print(
            Fore.RED
            + "FAIL: Risky machine M03 was not rejected."
        )

    # Check verification

    print()

    if status == "passed":

        print(
            Fore.GREEN
            + "PASS: Verification completed successfully."
        )

    else:

        print(
            Fore.RED
            + "FAIL: Verification did not pass."
        )

    # =================================================
    # FINAL STATUS
    # =================================================

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )

    if (
        final_response.selected_machine == "M01"
        and m03_rejected
        and status == "passed"
    ):

        print(
            Fore.GREEN
            + Style.BRIGHT
            + "       SCENARIO 2 PASSED SUCCESSFULLY"
        )

    else:

        print(
            Fore.RED
            + Style.BRIGHT
            + "       SCENARIO 2 FAILED"
        )

    print(
        Fore.CYAN
        + Style.BRIGHT
        + "=================================================="
    )

    # =================================================
    # STOP RUNTIME
    # =================================================

    await runtime.stop_when_idle()


if __name__ == "__main__":
    asyncio.run(main())
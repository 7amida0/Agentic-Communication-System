import asyncio
import random

from autogen_core import AgentId, SingleThreadedAgentRuntime

from agents.order_agent import OrderAgent
from agents.machine_agent import MachineAgent
from agents.quality_agent import QualityAgent
from agents.maintenance_agent import MaintenanceAgent
from agents.coordinator_agent import CoordinatorAgent
from agents.verification_agent import VerificationAgent

from colorama import Fore, Style, init

init(autoreset=True)


# =========================================================
# MACHINE AGENT CREATION
# =========================================================

def create_machine(
    machine_id: str,
    capability: str,
) -> MachineAgent:

    maintenance_condition = round(
        random.uniform(0.3, 1.0),
        2,
    )

    if maintenance_condition < 0.5:
        warnings = ["critical_fault"]

    elif maintenance_condition < 0.8:
        warnings = ["minor_vibration"]

    else:
        warnings = []

    return MachineAgent(
        machine_id=machine_id,
        status=random.choice(
            [
                "available",
                "busy",
                "maintenance",
            ]
        ),
        capability=capability,
        queue_length=random.randint(0, 5),
        estimated_processing_time_mins=random.randint(
            20,
            90,
        ),
        maintenance_condition=maintenance_condition,
        active_warnings=warnings,
    )


# =========================================================
# REGISTER MACHINE
# =========================================================

async def register_machine(
    runtime: SingleThreadedAgentRuntime,
    machine: MachineAgent,
) -> None:

    await machine.register_instance(
        runtime,
        AgentId(
            "machine_agent",
            machine.machine_id,
        ),
    )


# =========================================================
# MAIN
# =========================================================

async def main() -> None:

    runtime = SingleThreadedAgentRuntime()

    # =====================================================
    # REGISTER ORDER AGENT
    # =====================================================

    await OrderAgent.register(
        runtime,
        "order_agent",
        lambda: OrderAgent(),
    )

    # =====================================================
    # REGISTER SPECIALIST AGENTS
    # =====================================================

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

    # =====================================================
    # REGISTER VERIFICATION AGENT
    # =====================================================

    await VerificationAgent.register(
        runtime,
        "verification_agent",
        lambda: VerificationAgent(),
    )

    # =====================================================
    # REGISTER COORDINATOR
    # =====================================================

    await CoordinatorAgent.register(
        runtime,
        "coordinator_agent",
        lambda: CoordinatorAgent(),
    )

    # =====================================================
    # START RUNTIME
    # =====================================================

    runtime.start()

    # =====================================================
    # MACHINE DEFINITIONS
    # =====================================================

    machines = [
        create_machine(
            "M01",
            "milling",
        ),
        create_machine(
            "M02",
            "turning",
        ),
        create_machine(
            "M03",
            "milling",
        ),
    ]

    # =====================================================
    # REGISTER INITIAL MACHINES
    # =====================================================

    for machine in machines:

        await register_machine(
            runtime,
            machine,
        )

    # =====================================================
    # GET ORDER AGENT
    # =====================================================

    order_agent = OrderAgent()

    print()
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "============================================================"
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "        CONTINUOUS MULTI-MACHINE AUTOGEN WORKFLOW"
    )
    print(
        Fore.CYAN
        + Style.BRIGHT
        + "============================================================"
    )
    print()

    try:

        while True:

            # =================================================
            # GENERATING NEW ORDER
            # =================================================

            print()
            print(
                Fore.CYAN
                + Style.BRIGHT
                + "============================================================"
            )
            print(
                Fore.CYAN
                + Style.BRIGHT
                + "                     NEW ORDER"
            )
            print(
                Fore.CYAN
                + Style.BRIGHT
                + "============================================================"
            )

            # =================================================
            # RANDOMIZE MACHINE CONDITIONS
            # =================================================

            for machine in machines:

                machine.status = random.choice(
                    [
                        "available",
                        "busy",
                        "maintenance",
                    ]
                )

                machine.queue_length = random.randint(
                    0,
                    5,
                )

                machine.estimated_processing_time_mins = (
                    random.randint(
                        20,
                        90,
                    )
                )

                machine.maintenance_condition = round(
                    random.uniform(
                        0.3,
                        1.0,
                    ),
                    2,
                )

                if (
                    machine.maintenance_condition
                    < 0.5
                ):

                    machine.active_warnings = [
                        "critical_fault"
                    ]

                elif (
                    machine.maintenance_condition
                    < 0.8
                ):

                    machine.active_warnings = [
                        "minor_vibration"
                    ]

                else:

                    machine.active_warnings = []

            # =================================================
            # GENERATE ORDER
            # =================================================

            order = order_agent.generate_order()

            # =================================================
            # PRINT ORDER DETAILS
            # =================================================

            print()
            print(
                Fore.YELLOW
                + Style.BRIGHT
                + "ORDER DETAILS"
            )
            print(
                Fore.YELLOW
                + "------------------------------------------------------------"
            )

            print(
                Fore.BLUE
                + "  Order ID:"
                + Style.RESET_ALL,
                order.order_id,
            )

            print(
                Fore.BLUE
                + "  Priority:"
                + Style.RESET_ALL,
                order.priority,
            )

            print(
                Fore.BLUE
                + "  Required Capability:"
                + Style.RESET_ALL,
                order.required_capability,
            )

            print(
                Fore.BLUE
                + "  Deadline:"
                + Style.RESET_ALL,
                f"{order.deadline_minutes} minutes",
            )

            print(
                Fore.BLUE
                + "  Quality Requirement:"
                + Style.RESET_ALL,
                order.quality_requirement,
            )

            # =================================================
            # PRINT MACHINE CONDITIONS
            # =================================================

            print()
            print(
                Fore.MAGENTA
                + Style.BRIGHT
                + "MACHINE CONDITIONS"
            )
            print(
                Fore.MAGENTA
                + "------------------------------------------------------------"
            )

            for machine in machines:

                warnings = (
                    ", ".join(
                        machine.active_warnings
                    )
                    if machine.active_warnings
                    else "None"
                )

                if machine.status == "available":
                    status_color = Fore.GREEN

                elif machine.status == "busy":
                    status_color = Fore.YELLOW

                else:
                    status_color = Fore.RED

                print(
                    f"  {Fore.CYAN}{machine.machine_id}"
                    f"{Style.RESET_ALL} | "
                    f"{status_color}{machine.status}"
                    f"{Style.RESET_ALL} | "
                    f"{machine.capability} | "
                    f"Queue: {machine.queue_length} | "
                    f"Time: "
                    f"{machine.estimated_processing_time_mins} min | "
                    f"Maintenance: "
                    f"{machine.maintenance_condition} | "
                    f"Warnings: "
                    f"{warnings}"
                )

            # =================================================
            # SEND ORDER TO ORDER AGENT
            # =================================================

            print()
            print(
                Fore.CYAN
                + "Sending order to Order Agent for validation..."
            )

            validated_order = await runtime.send_message(
                order,
                recipient=AgentId(
                    "order_agent",
                    "default",
                ),
            )

            # =================================================
            # SEND VALIDATED ORDER TO COORDINATOR
            # =================================================

            print(
                Fore.CYAN
                + "Sending validated order to Coordinator..."
            )

            try:

                final_response = (
                    await runtime.send_message(
                        validated_order,
                        recipient=AgentId(
                            "coordinator_agent",
                            "default",
                        ),
                    )
                )

            except Exception as error:

                print()
                print(
                    Fore.RED
                    + Style.BRIGHT
                    + "ERROR DURING DECISION PROCESS"
                )
                print(
                    Fore.RED
                    + "------------------------------------------------------------"
                )
                print(
                    Fore.RED
                    + str(error)
                )

                await asyncio.sleep(5)

                continue

            # =================================================
            # FINAL RECOMMENDATION
            # =================================================

            print()
            print(
                Fore.CYAN
                + Style.BRIGHT
                + "============================================================"
            )
            print(
                Fore.CYAN
                + Style.BRIGHT
                + "                  FINAL RECOMMENDATION"
            )
            print(
                Fore.CYAN
                + Style.BRIGHT
                + "============================================================"
            )

            if final_response is None:

                print()
                print(
                    Fore.RED
                    + "No response received from Coordinator."
                )

            else:

                # =================================================
                # RECOMMENDATION
                # =================================================

                print()

                print(
                    Fore.YELLOW
                    + Style.BRIGHT
                    + "Recommendation"
                )

                print(
                    Fore.YELLOW
                    + "------------------------------------------------------------"
                )

                print(
                    Fore.BLUE
                    + "  Recommendation:"
                    + Style.RESET_ALL,
                    final_response.recommendation,
                )

                if final_response.selected_machine == "none":

                    print(
                        Fore.RED
                        + "  Selected Machine:"
                        + Style.RESET_ALL,
                        final_response.selected_machine,
                    )

                else:

                    print(
                        Fore.GREEN
                        + Style.BRIGHT
                        + "  Selected Machine:"
                        + Style.RESET_ALL,
                        final_response.selected_machine,
                    )

                # =================================================
                # REASONING
                # =================================================

                print()
                print(
                    Fore.YELLOW
                    + Style.BRIGHT
                    + "Reasoning"
                )

                print(
                    Fore.YELLOW
                    + "------------------------------------------------------------"
                )

                print(
                    final_response.reasoning
                )

                # =================================================
                # VERIFICATION
                # =================================================

                verification = (
                    final_response.verification_result
                )

                print()
                print(
                    Fore.CYAN
                    + Style.BRIGHT
                    + "Verification"
                )

                print(
                    Fore.CYAN
                    + "------------------------------------------------------------"
                )

                verification_status = verification.get(
                    "status"
                )

                if verification_status == "passed":

                    print(
                        Fore.GREEN
                        + Style.BRIGHT
                        + "  Status:"
                        + Style.RESET_ALL,
                        verification_status,
                    )

                else:

                    print(
                        Fore.RED
                        + Style.BRIGHT
                        + "  Status:"
                        + Style.RESET_ALL,
                        verification_status,
                    )

                print(
                    Fore.BLUE
                    + "  Gemini Used:"
                    + Style.RESET_ALL,
                    verification.get(
                        "gemini_used"
                    ),
                )

                print(
                    Fore.BLUE
                    + "  Fallback Used:"
                    + Style.RESET_ALL,
                    verification.get(
                        "used_fallback"
                    ),
                )

                # =================================================
                # REJECTED MACHINES
                # =================================================

                rejected = (
                    final_response.machines_filtered_out
                )

                print()
                print(
                    Fore.RED
                    + Style.BRIGHT
                    + "Rejected Machines"
                )

                print(
                    Fore.RED
                    + "------------------------------------------------------------"
                )

                if rejected:

                    for machine in rejected:

                        print(
                            "  "
                            + Fore.RED
                            + machine["machine_id"]
                            + Style.RESET_ALL
                            + " -> "
                            + machine["reason"]
                        )

                else:

                    print(
                        "  "
                        + Fore.GREEN
                        + "None"
                        + Style.RESET_ALL
                    )

            # =================================================
            # END OF ORDER
            # =================================================

            print()
            print(
                Fore.CYAN
                + Style.BRIGHT
                + "============================================================"
            )

            print(
                Fore.CYAN
                + "Waiting 5 seconds before the next order..."
            )

            print(
                Fore.CYAN
                + Style.BRIGHT
                + "============================================================"
            )

            await asyncio.sleep(5)

    except KeyboardInterrupt:

        print()
        print(
            Fore.YELLOW
            + Style.BRIGHT
            + "Stopping workflow..."
        )

    finally:

        await runtime.stop_when_idle()

        print(
            Fore.GREEN
            + Style.BRIGHT
            + "Workflow stopped."
        )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    asyncio.run(main())

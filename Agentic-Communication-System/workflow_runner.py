import asyncio
import random
from typing import Any
from autogen_core import AgentId,AgentInstantiationContext,SingleThreadedAgentRuntime
from agents.coordinator_agent import CoordinatorAgent
from agents.machine_agent import MachineAgent
from agents.maintenance_agent import MaintenanceAgent
from agents.order_agent import OrderAgent
from agents.quality_agent import QualityAgent
from agents.verification_agent import VerificationAgent
from messages.final_recommendation import FinalRecommendation
from messages.machine_status_request import MachineStatusRequest
from messages.order_message import OrderMessage

CAPABILITIES=["milling","drilling","cutting","turning","grinding"]

def create_machine_agent():
    agent_id=AgentInstantiationContext.current_agent_id()
    machine_id=agent_id.key
    capability=random.choice(CAPABILITIES)
    processing_time=random.randint(25,65)
    maintenance_condition=round(random.uniform(0.75,1.0),2)
    warnings=[]
    if maintenance_condition<0.82:
        warnings.append("maintenance_due")
    elif maintenance_condition<0.90:
        warnings.append(random.choice(["minor_vibration","tool_wear"]))
    return MachineAgent(
        machine_id=machine_id,
        status="available",
        capability=capability,
        estimated_processing_time_mins=processing_time,
        maintenance_condition=maintenance_condition,
        active_warnings=warnings
    )

async def register_runtime_agents(runtime:SingleThreadedAgentRuntime)->None:
    await OrderAgent.register(runtime,"order_agent",lambda:OrderAgent())
    await CoordinatorAgent.register(runtime,"coordinator_agent",lambda:CoordinatorAgent())
    await MachineAgent.register(runtime,"machine_agent",create_machine_agent)
    await QualityAgent.register(runtime,"quality_agent",lambda:QualityAgent())
    await MaintenanceAgent.register(runtime,"maintenance_agent",lambda:MaintenanceAgent())
    await VerificationAgent.register(runtime,"verification_agent",lambda:VerificationAgent())

async def print_machine_snapshot(runtime:SingleThreadedAgentRuntime)->None:
    print("\n"+"="*110)
    print("CURRENT PRODUCTION FLOOR")
    print("="*110)
    for machine_number in range(1,11):
        machine_id=f"M{machine_number:02d}"
        response=await runtime.send_message(
            MachineStatusRequest(
                order_id="FLOOR-SNAPSHOT",
                request_reason="Production floor status snapshot"
            ),
            AgentId("machine_agent",machine_id)
        )
        current=response.queue_order_ids[0] if response.queue_order_ids else "None"
        queue=", ".join(response.queue_order_ids) if response.queue_order_ids else "None"
        print(
            f"{machine_id:<5} | "
            f"{response.status.upper():<11} | "
            f"Capability: {response.capability:<10} | "
            f"Current: {current:<16} | "
            f"Queue: {queue:<30} | "
            f"Available: {response.estimated_available_in_mins:>3} min | "
            f"Completion: {response.estimated_completion_in_mins:>3} min"
        )
    print("="*110)

async def run_simulation(number_of_orders:int=10,order_interval_seconds:float=5.0)->None:
    runtime=SingleThreadedAgentRuntime()
    await register_runtime_agents(runtime)
    runtime.start()
    try:
        print("\n"+"="*80)
        print("AGENT-BASED MULTI-MACHINE PRODUCTION SIMULATION")
        print("="*80)
        print(f"Machines: 10")
        print(f"Orders: {number_of_orders}")
        print(f"Order interval: {order_interval_seconds} seconds")
        print("="*80)
        await asyncio.sleep(0.2)
        await print_machine_snapshot(runtime)
        order_agent=await runtime.try_get_underlying_agent_instance(AgentId("order_agent","default"))
        if order_agent is None:
            raise RuntimeError("Could not access the Order Agent.")
        for number in range(number_of_orders):
            if number>0:
                print(f"\n[SYSTEM] Waiting {order_interval_seconds} seconds for next order...")
                await asyncio.sleep(order_interval_seconds)
            order=order_agent.generate_order()
            print("\n"+"#"*80)
            print(f"NEW ORDER ARRIVAL: {order.order_id}")
            print("#"*80)
            print(f"Priority: {order.priority}")
            print(f"Capability: {order.required_capability}")
            print(f"Deadline: {order.deadline_minutes} min")
            print(f"Quality: {order.quality_requirement}")
            validated=await runtime.send_message(order,AgentId("order_agent","default"))
            if not isinstance(validated,OrderMessage):
                raise TypeError("Order Agent did not return a valid OrderMessage.")
            result=await runtime.send_message(validated,AgentId("coordinator_agent","default"))
            if not isinstance(result,FinalRecommendation):
                raise TypeError("Coordinator did not return a valid FinalRecommendation.")
            print("\n"+"="*80)
            print("AGENT DECISION EVIDENCE")
            print("="*80)
            print(f"Order: {result.order_id}")
            print(f"Selected Machine: {result.selected_machine}")
            print(f"Recommendation: {result.recommendation}")
            print(f"\nReasoning:\n{result.reasoning}")
            print("\nRequired Actions:")
            print(result.required_actions)
            print("\nRejected Machines:")
            if result.machines_filtered_out:
                for machine in result.machines_filtered_out:
                    print(f"  {machine['machine_id']} -> {machine['reason']}")
            else:
                print("  None")
            print("\nVerification:")
            print(f"  Status: {result.verification_result.get('status')}")
            print(f"  Gemini used: {result.verification_result.get('gemini_used')}")
            print(f"  Fallback used: {result.verification_result.get('used_fallback')}")
            print("="*80)
            await asyncio.sleep(0.2)
            await print_machine_snapshot(runtime)
        print("\n"+"="*80)
        print("SIMULATION COMPLETE")
        print("="*80)
    except asyncio.CancelledError:
        print("\n[SYSTEM] Simulation stopped.")
    finally:
        await runtime.stop_when_idle()

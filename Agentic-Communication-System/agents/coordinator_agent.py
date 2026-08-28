import os
from typing import Any
from autogen_core import AgentId,MessageContext,RoutedAgent,message_handler
from dotenv import load_dotenv
from google import genai
from messages.final_recommendation import FinalRecommendation
from messages.machine_status_request import MachineStatusRequest
from messages.machine_status_response import MachineStatusResponse
from messages.maintenance_assessment_request import MaintenanceAssessmentRequest
from messages.maintenance_assessment_response import MaintenanceAssessmentResponse
from messages.order_message import OrderMessage
from messages.quality_assessment_request import QualityAssessmentRequest
from messages.quality_assessment_response import QualityAssessmentResponse
from messages.verification_request import VerificationRequest
from messages.verification_response import VerificationResponse
from services.retrieval_service import RetrievalService

load_dotenv()

class CoordinatorAgent(RoutedAgent):
    def __init__(self)->None:
        super().__init__(description="Coordinates the manufacturing order-allocation workflow.")
        self.machine_agent_ids=[AgentId("machine_agent",f"M{i:02d}") for i in range(1,11)]
        self.quality_agent_id=AgentId("quality_agent","default")
        self.maintenance_agent_id=AgentId("maintenance_agent","default")
        self.verification_agent_id=AgentId("verification_agent","default")
        self.gemini_api_key=os.getenv("GEMINI_API_KEY")
        self.gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        if self.gemini_api_key:
            self.gemini_client=genai.Client(api_key=self.gemini_api_key)
        else:
            self.gemini_client=None
        self.retrieval_service=RetrievalService()

    @message_handler
    async def handle_order(self,message:OrderMessage,ctx:MessageContext)->FinalRecommendation:
        print()
        print("="*60)
        print(f"Coordinator received order: {message.order_id}")
        print("="*60)
        machine_responses=[]
        for machine_agent_id in self.machine_agent_ids:
            machine_request=MachineStatusRequest(request_reason="order_evaluation",order_id=message.order_id)
            print()
            print(f"Coordinator is requesting status from {machine_agent_id.key}")
            machine_response=await self.send_message(machine_request,recipient=machine_agent_id)
            if not isinstance(machine_response,MachineStatusResponse):
                raise TypeError(f"{machine_agent_id} returned an invalid MachineStatusResponse.")
            machine_responses.append(machine_response)
            print(f"Coordinator received the status of {machine_response.machine_id}")
        if not machine_responses:
            raise ValueError("The Coordinator did not receive any machine responses.")
        machine_data=[response.model_dump() for response in machine_responses]
        print()
        print("Coordinator is requesting quality assessments")
        quality_request=QualityAssessmentRequest(order_id=message.order_id,quality_requirement=message.quality_requirement,machine_data=machine_data)
        quality_response=await self.send_message(quality_request,recipient=self.quality_agent_id)
        if not isinstance(quality_response,QualityAssessmentResponse):
            raise TypeError("The Quality Agent returned an invalid response.")
        if not quality_response.assessments:
            raise ValueError("The Quality Agent returned no assessments.")
        print("Coordinator received the quality assessments")
        print()
        print("Coordinator is requesting maintenance assessments")
        maintenance_request=MaintenanceAssessmentRequest(machine_data=machine_data)
        maintenance_response=await self.send_message(maintenance_request,recipient=self.maintenance_agent_id)
        if not isinstance(maintenance_response,MaintenanceAssessmentResponse):
            raise TypeError("The Maintenance Agent returned an invalid response.")
        if not maintenance_response.assessments:
            raise ValueError("The Maintenance Agent returned no assessments.")
        print("Coordinator received the maintenance assessments")
        quality_by_machine={assessment["machine_id"]:assessment for assessment in quality_response.assessments}
        maintenance_by_machine={assessment["machine_id"]:assessment for assessment in maintenance_response.assessments}
        suitable_machines=[]
        machines_filtered_out=[]
        print()
        print("Coordinator is applying the decision rules")
        for machine in machine_responses:
            rejection_reasons=[]
            quality_result=quality_by_machine.get(machine.machine_id)
            maintenance_result=maintenance_by_machine.get(machine.machine_id)
            if machine.status.lower()=="maintenance":
                rejection_reasons.append("machine is under maintenance")
            if machine.capability.lower()!=message.required_capability.lower():
                rejection_reasons.append("wrong capability")
            if machine.estimated_completion_in_mins>message.deadline_minutes:
                rejection_reasons.append("cannot meet the deadline")
            if quality_result is None:
                rejection_reasons.append("quality assessment is missing")
            elif not quality_result.get("is_suitable",False):
                rejection_reasons.append("failed the quality assessment")
            if maintenance_result is None:
                rejection_reasons.append("maintenance assessment is missing")
            elif maintenance_result.get("availability_status","blocked").lower()!="available":
                rejection_reasons.append("failed the maintenance assessment")
            if rejection_reasons:
                machines_filtered_out.append({"machine_id":machine.machine_id,"reason":", ".join(rejection_reasons)})
                print(f"{machine.machine_id} rejected: {', '.join(rejection_reasons)}")
            else:
                suitable_machines.append((machine,quality_result,maintenance_result))
                print(f"{machine.machine_id} passed all checks")
        selected_machine=None
        selected_quality=None
        selected_maintenance=None
        if suitable_machines:
            selected=min(suitable_machines,key=lambda item:(item[0].queue_length,item[1].get("quality_risk_score",1.0),item[0].estimated_processing_time_mins))
            selected_machine=selected[0]
            selected_quality=selected[1]
            selected_maintenance=selected[2]
            selected_machine_id=selected_machine.machine_id
            required_actions={"quality":selected_quality.get("recommended_action","none"),"maintenance":selected_maintenance.get("maintenance_action_required","none")}
            recommendation=f"Select machine {selected_machine_id} for order {message.order_id}."
            fallback_justification=f"Machine {selected_machine_id} was selected because it has the required {message.required_capability} capability, is available, can meet the deadline, and passed the quality and maintenance checks. It was ranked using queue length, quality risk, and processing time."
        else:
            selected_machine_id="none"
            required_actions={"quality":"none","maintenance":"none"}
            recommendation=f"No suitable machine was found for order {message.order_id}."
            fallback_justification="No machine satisfied all availability, capability, deadline, quality, and maintenance requirements."
        evidence={"order":{"order_id":message.order_id,"priority":message.priority,"required_capability":message.required_capability,"deadline_minutes":message.deadline_minutes,"quality_requirement":message.quality_requirement},"machine_statuses":[machine.model_dump() for machine in machine_responses],"quality_assessments":quality_response.assessments,"maintenance_assessments":maintenance_response.assessments,"selected_machine":selected_machine_id,"rejected_machines":machines_filtered_out,"decision_rules":{"availability_required":True,"capability_must_match":True,"deadline_must_be_met":True,"quality_must_pass":True,"maintenance_must_pass":True},"ranking_method":["shortest_queue","lowest_quality_risk","shortest_processing_time"]}
        retrieved_information=self.retrieval_service.retrieve(evidence)
        print("Coordinator retrieved grounding information")
        gemini_used=True
        fallback_reason="none"
        if selected_machine is not None:
            reasoning=await self._generate_gemini_explanation(message,selected_machine,selected_quality or {},selected_maintenance or {},machines_filtered_out,retrieved_information,fallback_justification)
        else:
            reasoning=await self._generate_no_selection_explanation(message,machines_filtered_out,retrieved_information,fallback_justification)
        if reasoning==fallback_justification:
            gemini_used=False
            fallback_reason="gemini_failure"
        print()
        print("Coordinator is requesting verification")
        verification_request=VerificationRequest(order_id=message.order_id,selected_machine=selected_machine_id,reasoning=reasoning,evidence=evidence,retrieved_information=retrieved_information,fallback_explanation=fallback_justification)
        verification_response=await self.send_message(verification_request,recipient=self.verification_agent_id)
        if not isinstance(verification_response,VerificationResponse):
            raise TypeError("The Verification Agent returned an invalid response.")
        print(f"Verification status: {verification_response.status}")
        if verification_response.status.lower()=="passed":
            verified_reasoning=verification_response.verified_explanation
            print("Gemini explanation passed verification.")
        else:
            verified_reasoning=fallback_justification
            fallback_reason="verification_failure"
            print("Gemini explanation failed verification.")
            print("Using deterministic Python explanation.")
        verification_result={"status":verification_response.status,"issues_found":verification_response.issues_found,"verified_explanation":verified_reasoning,"used_fallback":verification_response.used_fallback or not gemini_used,"fallback_reason":fallback_reason,"gemini_used":gemini_used}
        if selected_machine_id!="none":
            selected_machine_agent_id=AgentId("machine_agent",selected_machine_id)
            print()
            print(f"Coordinator is sending order {message.order_id} to {selected_machine_id}")
            machine_assignment_response=await self.send_message(message,recipient=selected_machine_agent_id)
            if not isinstance(machine_assignment_response,MachineStatusResponse):
                raise TypeError("Selected Machine Agent returned an invalid response after assignment.")
            print(f"Order {message.order_id} assigned to {selected_machine_id}")
        final_recommendation=FinalRecommendation(order_id=message.order_id,selected_machine=selected_machine_id,recommendation=recommendation,reasoning=verified_reasoning,evidence=evidence,required_actions=required_actions,machines_filtered_out=machines_filtered_out,retrieved_information=retrieved_information,verification_result=verification_result,justification=verified_reasoning)
        print()
        print("[Coordinator] FINAL RECOMMENDATION")
        print(f"Order: {final_recommendation.order_id}")
        print(f"Machine: {final_recommendation.selected_machine}")
        return final_recommendation

    async def _generate_gemini_explanation(self, order, selected_machine, quality_result, maintenance_result, filtered_machines, retrieved_information, fallback)->str:
        if self.gemini_client is None:
            print("Gemini API key was not found. Using Python explanation.")
            return fallback
        
        prompt = f"""You are explaining a manufacturing machine-allocation decision..."""
        
        try:
            # NEW: Use AsyncChat instead of direct generate_content
            chat = self.gemini_client.aio.chats.create(model=self.gemini_model)
            response = await chat.send_message(prompt)
            
            if response.text and response.text.strip():
                print("Gemini generated grounded explanation")
                return response.text.strip()
            return fallback
        except Exception as error:
            print(f"Gemini explanation failed: {error}")
            return fallback

    async def _generate_no_selection_explanation(self, order, filtered_machines, retrieved_information, fallback)->str:
        if self.gemini_client is None:
            return fallback
        
        prompt = f"""You are explaining a manufacturing machine-allocation result..."""
        
        try:
            # NEW: Use AsyncChat instead of direct generate_content
            chat = self.gemini_client.aio.chats.create(model=self.gemini_model)
            response = await chat.send_message(prompt)
            
            if response.text and response.text.strip():
                return response.text.strip()
            return fallback
        except Exception as error:
            print(f"Gemini no-selection explanation failed: {error}")
            return fallback

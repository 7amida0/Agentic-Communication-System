from pydantic import BaseModel 
 
class MachineStatusRequest(BaseModel): 
   request_reason: str 
   order_id: str
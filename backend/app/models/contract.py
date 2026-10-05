from typing import Optional
from pydantic import BaseModel


class ContractResponse(BaseModel):
    contract_id: str
    file_name: str
    storage_path: str
    status: str
    message: Optional[str] = None


class ProcessContractResponse(BaseModel):
    contract_id: str
    status: str
    total_pages: Optional[int] = None
    chunks_created: int
    message: str
from pydantic import BaseModel
from typing import Optional


class ContractResponse(BaseModel):
    contract_id: str
    file_name: str
    storage_path: str
    status: str
    message: Optional[str] = None
from typing import Optional
from pydantic import BaseModel, Field

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


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class AskSource(BaseModel):
    chunk_index: Optional[int] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    similarity: Optional[float] = None


class AskResponse(BaseModel):
    answer: str
    sources: list[AskSource]

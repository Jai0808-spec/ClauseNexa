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


class AskContractRequest(BaseModel):
    question: str
    top_k: int = 5


class SourceResponse(BaseModel):
    chunk_index: Optional[int] = None
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    similarity: Optional[float] = None


class AskContractResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
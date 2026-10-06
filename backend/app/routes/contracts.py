import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.database import supabase
from app.services.storage import upload_contract_file
from app.models.contract import (
    ContractResponse,
    ProcessContractResponse,
    AskContractRequest,
    AskContractResponse
)
from clausenexa_rag.rag import ask_contract
from app.services.rag_service import (
    ContractNotFoundError,
    ContractProcessingError,
    process_contract_with_rag
)

router = APIRouter(
    prefix="/contracts",
    tags=["Contracts"]
)


# ---------------------------------------------------------
# Supported contract file types
# ---------------------------------------------------------

ALLOWED_EXTENSIONS = {".pdf", ".docx"}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# ---------------------------------------------------------
# POST /contracts/upload
# ---------------------------------------------------------

@router.post("/upload", response_model=ContractResponse)
async def upload_contract(file: UploadFile = File(...)):

    # -----------------------------------------------------
    # 1. Validate filename
    # -----------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided."
        )

    # Get extension (.pdf or .docx)
    extension = Path(file.filename).suffix.lower()


    # -----------------------------------------------------
    # 2. Validate file extension
    # -----------------------------------------------------

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX contracts are currently supported."
        )


    # -----------------------------------------------------
    # 3. Validate MIME/content type
    # -----------------------------------------------------

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid contract file type. Please upload a PDF or DOCX file."
        )


    # -----------------------------------------------------
    # 4. Generate unique contract ID
    # -----------------------------------------------------

    contract_id = str(uuid.uuid4())

    storage_path = None


    try:

        # -------------------------------------------------
        # 5. Upload original document to Supabase Storage
        # -------------------------------------------------

        storage_path = await upload_contract_file(
            file=file,
            contract_id=contract_id
        )


        # -------------------------------------------------
        # 6. Prepare contract metadata
        # -------------------------------------------------

        contract_data = {
            "id": contract_id,
            "file_name": file.filename,
            "original_file_name": file.filename,
            "file_type": file.content_type,
            "storage_path": storage_path,
            "status": "uploaded"
        }


        # -------------------------------------------------
        # 7. Insert contract into Supabase PostgreSQL
        # -------------------------------------------------

        response = (
            supabase
            .table("contracts")
            .insert(contract_data)
            .execute()
        )


        # -------------------------------------------------
        # 8. Check database insertion
        # -------------------------------------------------

        if not response.data:
            raise Exception(
                "Contract metadata could not be inserted into the database."
            )


        # -------------------------------------------------
        # 9. Return successful response
        # -------------------------------------------------

        return ContractResponse(
            contract_id=contract_id,
            file_name=file.filename,
            storage_path=storage_path,
            status="uploaded",
            message="Contract uploaded successfully."
        )


    except HTTPException:
        raise


    except Exception as exc:

        # -------------------------------------------------
        # 10. Cleanup
        #
        # If Storage upload worked but database insertion
        # failed, remove the orphaned document.
        # -------------------------------------------------

        if storage_path:

            try:
                (
                    supabase
                    .storage
                    .from_("contracts")
                    .remove([storage_path])
                )

            except Exception:
                pass


        # -------------------------------------------------
        # 11. Return server error
        # -------------------------------------------------

        raise HTTPException(
            status_code=500,
            detail=f"Contract upload failed: {str(exc)}"
        )

        # ---------------------------------------------------------
# GET /contracts
# Get all uploaded contracts
# ---------------------------------------------------------

@router.get("")
def get_all_contracts():

    try:
        response = (
            supabase
            .table("contracts")
            .select("*")
            .order("uploaded_at", desc=True)
            .execute()
        )

        return {
            "contracts": response.data
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve contracts: {str(exc)}"
        )
# ---------------------------------------------------------
# POST /contracts/{contract_id}/process
# Process an uploaded contract through the RAG pipeline
# ---------------------------------------------------------

@router.post(
    "/{contract_id}/process",
    response_model=ProcessContractResponse
)
def process_uploaded_contract(
    contract_id: str
):

    try:

        result = process_contract_with_rag(
            contract_id
        )

        return ProcessContractResponse(
            **result
        )


    except ContractNotFoundError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )


    except ContractProcessingError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unexpected contract "
                f"processing error: {exc}"
            )
        )


# ---------------------------------------------------------
# POST /contracts/{contract_id}/ask
# Ask questions about a processed contract
# ---------------------------------------------------------

@router.post(
    "/{contract_id}/ask",
    response_model=AskContractResponse
)
def ask_uploaded_contract(
    contract_id: str,
    request: AskContractRequest
):

    try:

        # -------------------------------------------------
        # 1. Check that the contract exists
        # -------------------------------------------------

        response = (
            supabase
            .table("contracts")
            .select("id, status")
            .eq("id", contract_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Contract not found."
            )

        contract = response.data[0]

        # -------------------------------------------------
        # 2. Contract must be processed first
        # -------------------------------------------------

        if contract.get("status") != "processed":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Contract must be processed "
                    "before asking questions."
                )
            )

        # -------------------------------------------------
        # 3. Validate question
        # -------------------------------------------------

        if not request.question or not request.question.strip():
            raise HTTPException(
                status_code=400,
                detail="Question cannot be empty."
            )

        # -------------------------------------------------
        # 4. Run the full RAG pipeline
        # -------------------------------------------------

        result = ask_contract(
            supabase=supabase,
            contract_id=contract_id,
            question=request.question,
            top_k=request.top_k
        )

        # -------------------------------------------------
        # 5. Return answer + sources
        # -------------------------------------------------

        return AskContractResponse(
            **result
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Contract question answering failed: {str(exc)}"
        )


# ---------------------------------------------------------
# GET /contracts/{contract_id}
# Get one specific contract
# ---------------------------------------------------------

@router.get("/{contract_id}")
def get_contract(contract_id: str):

    try:
        response = (
            supabase
            .table("contracts")
            .select("*")
            .eq("id", contract_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Contract not found."
            )

        return response.data[0]

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve contract: {str(exc)}"
        )

    # ---------------------------------------------------------
# DELETE /contracts/{contract_id}
# Delete a contract from Storage and Database
# ---------------------------------------------------------

@router.delete("/{contract_id}")
def delete_contract(contract_id: str):

    try:
        # -------------------------------------------------
        # 1. Find the contract in the database
        # -------------------------------------------------

        response = (
            supabase
            .table("contracts")
            .select("*")
            .eq("id", contract_id)
            .execute()
        )

        # -------------------------------------------------
        # 2. Check whether contract exists
        # -------------------------------------------------

        if not response.data:
            raise HTTPException(
                status_code=404,
                detail="Contract not found."
            )

        contract = response.data[0]

        storage_path = contract.get("storage_path")


        # -------------------------------------------------
        # 3. Delete document from Supabase Storage
        # -------------------------------------------------

        if storage_path:

            supabase.storage.from_("contracts").remove(
                [storage_path]
            )


        # -------------------------------------------------
        # 4. Delete contract record from database
        # -------------------------------------------------

        supabase.table("contracts").delete().eq(
            "id",
            contract_id
        ).execute()


        # -------------------------------------------------
        # 5. Return success response
        # -------------------------------------------------

        return {
            "message": "Contract deleted successfully.",
            "contract_id": contract_id
        }


    except HTTPException:
        raise


    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete contract: {str(exc)}"
        )
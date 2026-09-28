import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.database import supabase
from app.services.storage import upload_contract_file
from app.models.contract import ContractResponse


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
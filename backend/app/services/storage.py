import uuid
from fastapi import UploadFile

from app.database import supabase


BUCKET_NAME = "contracts"


async def upload_contract_file(file: UploadFile, contract_id: str) -> str:
    """
    Upload a contract PDF to Supabase Storage.

    Returns the path of the uploaded file.
    """

    file_extension = file.filename.split(".")[-1].lower()

    storage_path = f"{contract_id}/{uuid.uuid4()}.{file_extension}"

    file_bytes = await file.read()

    supabase.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=file_bytes,
        file_options={
            "content-type": file.content_type,
            "upsert": "false"
        }
    )

    return storage_path
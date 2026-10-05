import uuid

from fastapi import UploadFile

from app.database import supabase


BUCKET_NAME = "contracts"


async def upload_contract_file(
    file: UploadFile,
    contract_id: str
) -> str:

    file_extension = (
        file.filename
        .split(".")[-1]
        .lower()
    )

    storage_path = (
        f"{contract_id}/"
        f"{uuid.uuid4()}."
        f"{file_extension}"
    )

    file_bytes = await file.read()

    (
        supabase
        .storage
        .from_(BUCKET_NAME)
        .upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                "content-type":
                    file.content_type,

                "upsert":
                    "false"
            }
        )
    )

    return storage_path


def download_contract_file(
    storage_path: str
) -> bytes:

    if not storage_path:
        raise ValueError(
            "storage_path is required."
        )

    file_bytes = (
        supabase
        .storage
        .from_(BUCKET_NAME)
        .download(storage_path)
    )

    if not file_bytes:
        raise RuntimeError(
            "Downloaded contract file is empty."
        )

    return file_bytes
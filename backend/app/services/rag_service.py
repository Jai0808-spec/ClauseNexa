from app.database import supabase
from app.services.storage import download_contract_file

from clausenexa_rag.pipeline import preprocess_contract
from clausenexa_rag.embeddings import (
    embed_texts,
    embeddings_configured
)


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class ContractNotFoundError(Exception):
    """Raised when the requested contract does not exist."""
    pass


class ContractProcessingError(Exception):
    """Raised when contract preprocessing fails."""
    pass


# ============================================================
# STATUS HELPER
# ============================================================

def update_contract_status(
    contract_id: str,
    status: str
) -> None:
    """
    Update the processing status of a contract.

    Valid statuses:
    - uploaded
    - processing
    - processed
    - failed
    """

    (
        supabase
        .table("contracts")
        .update({
            "status": status
        })
        .eq("id", contract_id)
        .execute()
    )


# ============================================================
# MAIN BACKEND <-> RAG SERVICE
# ============================================================

def process_contract_with_rag(
    contract_id: str
) -> dict:
    """
    Process an uploaded contract using the ClauseNexa
    RAG preprocessing pipeline.

    Flow:
        1. Retrieve contract metadata
        2. Validate stored contract
        3. Mark contract as processing
        4. Download PDF/DOCX from Supabase Storage
        5. Extract text
        6. Clean text
        7. Perform clause-aware chunking
        8. Generate embeddings if configured
        9. Remove old chunks if reprocessing
        10. Store chunks and embeddings
        11. Update contract metadata
        12. Mark contract as processed
    """

    # ========================================================
    # 1. RETRIEVE CONTRACT
    # ========================================================

    try:
        response = (
            supabase
            .table("contracts")
            .select("*")
            .eq("id", contract_id)
            .execute()
        )

    except Exception as exc:
        raise ContractProcessingError(
            f"Could not retrieve contract: {exc}"
        ) from exc


    if not response.data:
        raise ContractNotFoundError(
            f"Contract '{contract_id}' was not found."
        )


    contract = response.data[0]


    # ========================================================
    # 2. GET REQUIRED CONTRACT INFORMATION
    # ========================================================

    file_name = (
        contract.get("original_file_name")
        or contract.get("file_name")
    )

    storage_path = contract.get("storage_path")


    if not file_name:
        raise ContractProcessingError(
            "Contract filename is missing."
        )


    if not storage_path:
        raise ContractProcessingError(
            "Contract storage path is missing."
        )


    # ========================================================
    # PROCESSING STARTS
    # ========================================================

    try:

        # ====================================================
        # 3. STATUS -> PROCESSING
        # ====================================================

        update_contract_status(
            contract_id=contract_id,
            status="processing"
        )


        # ====================================================
        # 4. DOWNLOAD ORIGINAL DOCUMENT
        # ====================================================

        file_bytes = download_contract_file(
            storage_path
        )


        if not file_bytes:
            raise ContractProcessingError(
                "Downloaded contract file is empty."
            )


        # ====================================================
        # 5. RUN RAG PREPROCESSING PIPELINE
        # ====================================================

        result = preprocess_contract(
            file_bytes=file_bytes,
            file_name=file_name
        )


        if not isinstance(result, dict):
            raise ContractProcessingError(
                "RAG pipeline returned an invalid result."
            )


        chunks = result.get(
            "chunks",
            []
        )

        total_pages = result.get(
            "total_pages"
        )


        if not chunks:
            raise ContractProcessingError(
                "No chunks were created from the contract."
            )


        # ====================================================
        # 6. REMOVE EMPTY CHUNKS
        # ====================================================

        valid_chunks = []

        for chunk in chunks:

            content = chunk.get(
                "content",
                ""
            ).strip()

            if content:
                valid_chunks.append(chunk)


        if not valid_chunks:
            raise ContractProcessingError(
                "The RAG pipeline produced no valid text chunks."
            )


        # ====================================================
        # 7. OPTIONAL EMBEDDING GENERATION
        # ====================================================

        embeddings = None


        if embeddings_configured():

            chunk_texts = [
                chunk["content"].strip()
                for chunk in valid_chunks
            ]


            embeddings = embed_texts(
                chunk_texts
            )


            if len(embeddings) != len(valid_chunks):
                raise ContractProcessingError(
                    "Number of embeddings does not match "
                    "number of contract chunks."
                )


        # ====================================================
        # 8. CONVERT RAG CHUNKS -> DATABASE ROWS
        # ====================================================

        section_rows = []


        for index, chunk in enumerate(
            valid_chunks
        ):

            content = chunk.get(
                "content",
                ""
            ).strip()


            # ------------------------------------------------
            # PAGE INFORMATION
            # ------------------------------------------------

            pages = chunk.get(
                "page_numbers",
                chunk.get(
                    "pages",
                    []
                )
            )


            if pages is None:
                pages = []


            pages = sorted(
                {
                    int(page)
                    for page in pages
                    if page is not None
                }
            )


            # ------------------------------------------------
            # EMBEDDING
            # ------------------------------------------------

            embedding = None


            if embeddings is not None:
                embedding = embeddings[index]


            # ------------------------------------------------
            # DATABASE ROW
            # ------------------------------------------------

            section_rows.append({

                "contract_id":
                    contract_id,

                "section_title":
                    None,

                "section_text":
                    content,

                # First page of the chunk
                "page_number":
                    pages[0]
                    if pages
                    else None,

                # All pages covered by the chunk
                "page_numbers":
                    pages,

                "chunk_index":
                    chunk.get(
                        "chunk_index",
                        index
                    ),

                "start_char":
                    None,

                "end_char":
                    None,

                # NULL when no embedding API is configured.
                # vector(1536) once embeddings are generated.
                "embedding":
                    embedding
            })


        # ====================================================
        # 9. REMOVE PREVIOUS CHUNKS
        # ====================================================

        (
            supabase
            .table("contract_sections")
            .delete()
            .eq(
                "contract_id",
                contract_id
            )
            .execute()
        )


        # ====================================================
        # 10. INSERT NEW CHUNKS
        # ====================================================

        insert_response = (
            supabase
            .table("contract_sections")
            .insert(
                section_rows
            )
            .execute()
        )


        if not insert_response.data:
            raise ContractProcessingError(
                "Contract chunks could not be stored "
                "in contract_sections."
            )


        # ====================================================
        # 11. UPDATE CONTRACT METADATA
        # ====================================================

        contract_update = {
            "status": "processed"
        }


        if total_pages is not None:
            contract_update[
                "total_pages"
            ] = total_pages


        (
            supabase
            .table("contracts")
            .update(
                contract_update
            )
            .eq(
                "id",
                contract_id
            )
            .execute()
        )


        # ====================================================
        # 12. SUCCESS RESPONSE
        # ====================================================

        return {

            "contract_id":
                contract_id,

            "status":
                "processed",

            "total_pages":
                total_pages,

            "chunks_created":
                len(section_rows),

            "message":
                "Contract preprocessing completed successfully."
        }


    # ========================================================
    # KNOWN PROCESSING ERROR
    # ========================================================

    except ContractProcessingError:

        try:
            update_contract_status(
                contract_id=contract_id,
                status="failed"
            )

        except Exception:
            pass

        raise


    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as exc:

        try:
            update_contract_status(
                contract_id=contract_id,
                status="failed"
            )

        except Exception:
            pass


        raise ContractProcessingError(
            f"Contract processing failed: {exc}"
        ) from exc
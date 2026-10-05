from .extractor import extract_document
from .cleaner import clean_text
from .chunker import chunk_text


def preprocess_contract(
    file_bytes: bytes,
    file_name: str
) -> dict:
    """
    Complete preprocessing pipeline.

    Input:
        Original PDF/DOCX bytes

    Output:
        Cleaned and structured RAG chunks
    """

    # ------------------------------
    # 1. Extract
    # ------------------------------

    extraction = extract_document(
        file_bytes=file_bytes,
        file_name=file_name
    )


    # ------------------------------
    # 2. Clean
    # ------------------------------

    cleaned_text = clean_text(
        extraction.text
    )


    # ------------------------------
    # 3. Chunk
    # ------------------------------

    chunks = chunk_text(
        cleaned_text,
        max_chars=1800,
        overlap_units=1
    )


    return {
        "total_pages":
            extraction.total_pages,

        "chunks":
            chunks
    }
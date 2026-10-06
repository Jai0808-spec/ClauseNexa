from clausenexa_rag.embeddings import embed_text


class RetrievalError(Exception):
    """Raised when contract retrieval fails."""
    pass


def retrieve_contract_sections(
    supabase,
    contract_id: str,
    question: str,
    top_k: int = 5
) -> list[dict]:
    """
    Retrieve the most relevant contract chunks
    for a user's question using cosine similarity.
    """

    if not question or not question.strip():
        raise RetrievalError(
            "Question cannot be empty."
        )

    if top_k <= 0:
        raise RetrievalError(
            "top_k must be greater than 0."
        )

    try:
        query_embedding = embed_text(
            question.strip()
        )

        response = (
            supabase
            .rpc(
                "match_contract_sections",
                {
                    "query_embedding": query_embedding,
                    "match_contract_id": contract_id,
                    "match_count": top_k
                }
            )
            .execute()
        )

    except Exception as exc:
        raise RetrievalError(
            f"Vector retrieval failed: {exc}"
        ) from exc

    return response.data or []
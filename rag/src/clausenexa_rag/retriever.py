import re

from clausenexa_rag.embeddings import embed_text


# Words that carry no signal for matching a question to a clause
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "of", "in",
    "on", "at", "to", "for", "by", "with", "and", "or", "if", "this", "that",
    "these", "those", "it", "its", "what", "which", "who", "whom", "when",
    "where", "how", "why", "do", "does", "did", "there", "any", "can", "may",
    "under", "contract", "agreement", "clause", "much", "many", "long"
}

# Weight of the keyword score relative to cosine similarity (0-1)
KEYWORD_WEIGHT = 0.5

# Candidates fetched from the vector search before re-ranking
MIN_CANDIDATES = 10


class RetrievalError(Exception):
    """Raised when contract retrieval fails."""
    pass


def _stem(word: str) -> str:
    # Crude stem: drop a common suffix, then keep the first 6 letters.
    # "governs" / "governed" / "governing" -> "govern"; "lasts" -> "last"
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[:-len(suffix)]
            break

    return word[:6]


def _keywords(question: str) -> set[str]:
    words = re.findall(r"[a-z]+", question.lower())

    return {
        _stem(word)
        for word in words
        if word not in STOPWORDS and len(word) > 2
    }


def _keyword_score(keywords: set[str], text: str) -> float:
    if not keywords:
        return 0.0

    text_stems = {
        _stem(word)
        for word in re.findall(r"[a-z]+", text.lower())
    }

    return len(keywords & text_stems) / len(keywords)


def retrieve_contract_sections(
    supabase,
    contract_id: str,
    question: str,
    top_k: int = 5
) -> list[dict]:
    """
    Retrieve the most relevant contract chunks for a question.

    Hybrid search: cosine similarity from pgvector, re-ranked with a
    keyword score. Chunks are long, so a short clause (e.g. Governing
    Law) can have low embedding similarity even when the question
    names it directly.
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
                    "match_count": max(top_k * 2, MIN_CANDIDATES)
                }
            )
            .execute()
        )

    except Exception as exc:
        raise RetrievalError(
            f"Vector retrieval failed: {exc}"
        ) from exc

    candidates = response.data or []
    keywords = _keywords(question)

    for section in candidates:
        keyword_score = _keyword_score(
            keywords,
            section.get("section_text", "")
        )

        section["keyword_score"] = round(keyword_score, 4)
        section["hybrid_score"] = (
            (section.get("similarity") or 0.0)
            + KEYWORD_WEIGHT * keyword_score
        )

    candidates.sort(
        key=lambda section: section["hybrid_score"],
        reverse=True
    )

    return candidates[:top_k]

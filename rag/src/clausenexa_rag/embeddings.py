from sentence_transformers import SentenceTransformer


# ============================================================
# EMBEDDING CONFIGURATION
# ============================================================

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384


# ============================================================
# CUSTOM EXCEPTION
# ============================================================

class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass


# ============================================================
# LOAD MODEL
# ============================================================

try:
    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL
    )

except Exception as exc:
    raise EmbeddingError(
        f"Could not load embedding model: {exc}"
    ) from exc


# ============================================================
# EMBEDDING STATUS
# ============================================================

def embeddings_configured() -> bool:
    """
    Hugging Face embeddings run locally.

    No API key is required, so embeddings are always available
    once the model has been successfully loaded.
    """

    return True


# ============================================================
# SINGLE TEXT EMBEDDING
# ============================================================

def embed_text(
    text: str
) -> list[float]:
    """
    Convert a single text string into a
    384-dimensional embedding vector.
    """

    if not text or not text.strip():
        raise EmbeddingError(
            "Cannot create an embedding for empty text."
        )

    try:
        embedding = embedding_model.encode(
            text.strip(),
            convert_to_numpy=True,
            normalize_embeddings=True
        )

    except Exception as exc:
        raise EmbeddingError(
            f"Embedding generation failed: {exc}"
        ) from exc


    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise EmbeddingError(
            f"Expected {EMBEDDING_DIMENSIONS} dimensions, "
            f"received {len(embedding)}."
        )


    return embedding.tolist()


# ============================================================
# BATCH EMBEDDINGS
# ============================================================

def embed_texts(
    texts: list[str]
) -> list[list[float]]:
    """
    Convert multiple text chunks into
    384-dimensional embedding vectors.
    """

    cleaned_texts = [
        text.strip()
        for text in texts
        if text and text.strip()
    ]


    if not cleaned_texts:
        return []


    try:
        embeddings = embedding_model.encode(
            cleaned_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )

    except Exception as exc:
        raise EmbeddingError(
            f"Batch embedding generation failed: {exc}"
        ) from exc


    if len(embeddings) != len(cleaned_texts):
        raise EmbeddingError(
            "Number of returned embeddings does not "
            "match number of input texts."
        )


    result = []


    for embedding in embeddings:

        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingError(
                f"Expected {EMBEDDING_DIMENSIONS}-dimensional "
                "embedding."
            )

        result.append(
            embedding.tolist()
        )


    return result
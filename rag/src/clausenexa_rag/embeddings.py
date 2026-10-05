import os

from openai import OpenAI


EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536

def embeddings_configured() -> bool:
    """
    Return True if the embedding provider
    is configured and ready to use.
    """

    return bool(
        os.getenv("OPENAI_API_KEY")
    )

class EmbeddingError(Exception):
    """Raised when embedding generation fails."""
    pass


def get_embedding_client() -> OpenAI:
    """
    Create the OpenAI client.

    The API key is only required when an
    embedding request is actually made.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise EmbeddingError(
            "OPENAI_API_KEY is not configured."
        )

    return OpenAI(
        api_key=api_key
    )


def embed_text(
    text: str
) -> list[float]:
    """
    Generate one embedding vector.
    """

    if not text or not text.strip():
        raise EmbeddingError(
            "Cannot create an embedding for empty text."
        )

    client = get_embedding_client()

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text.strip()
        )

        embedding = response.data[0].embedding

    except Exception as exc:
        raise EmbeddingError(
            f"Embedding generation failed: {exc}"
        ) from exc

    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise EmbeddingError(
            f"Expected {EMBEDDING_DIMENSIONS} dimensions, "
            f"received {len(embedding)}."
        )

    return embedding


def embed_texts(
    texts: list[str]
) -> list[list[float]]:
    """
    Generate embeddings for multiple text chunks
    in one API request.
    """

    cleaned_texts = [
        text.strip()
        for text in texts
        if text and text.strip()
    ]

    if not cleaned_texts:
        return []

    client = get_embedding_client()

    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=cleaned_texts
        )

    except Exception as exc:
        raise EmbeddingError(
            f"Batch embedding generation failed: {exc}"
        ) from exc

    embeddings = [
        item.embedding
        for item in response.data
    ]

    if len(embeddings) != len(cleaned_texts):
        raise EmbeddingError(
            "Number of returned embeddings does not "
            "match number of input texts."
        )

    for embedding in embeddings:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingError(
                f"Expected {EMBEDDING_DIMENSIONS}-dimensional "
                "embedding."
            )

    return embeddings
import logging
import os
import threading

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.contracts import router as contracts_router


logger = logging.getLogger("clausenexa")


def _preload_models() -> None:
    """
    Load the ML/RAG models once at startup so the first user request
    is not slow. Each model is optional: a missing one is logged and
    the matching endpoint reports 503 when called.
    """

    def load_embeddings():
        import clausenexa_rag.embeddings  # loads the model on import

    def load_classifier():
        from clausenexa_ml.classifier import load_model
        load_model()

    def load_generator():
        import clausenexa_rag.generator  # loads the model on import

    for name, load in (
        ("embeddings", load_embeddings),
        ("clause classifier", load_classifier),
        ("answer generator", load_generator),
    ):
        try:
            load()
            logger.info("Preloaded %s", name)
        except Exception as exc:
            logger.warning("Could not preload %s: %s", name, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background thread: the API accepts requests while models load.
    if os.getenv("PRELOAD_MODELS", "true").lower() != "false":
        threading.Thread(target=_preload_models, daemon=True).start()

    yield


app = FastAPI(
    lifespan=lifespan,
    title="ClauseNexa API",
    description="Backend API for ClauseNexa Legal Contract Analysis and Risk Detection System",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "ClauseNexa API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


app.include_router(contracts_router)
"""FastAPI dependencies for the API layer."""

from fastapi import HTTPException, Request, status

from app.providers import LLMProvider, get_llm_provider
from app.retrieval import Retriever


def get_llm_provider_dep() -> LLMProvider:
    """API-layer seam for the LLM provider; tests swap it via
    ``app.dependency_overrides``."""
    return get_llm_provider()


def get_retriever_dep(request: Request) -> Retriever:
    """API-layer seam for the retriever; reads ``app.state.retriever``
    (built in the lifespan, rebuilt on ingest) and 503s if missing."""
    retriever = getattr(request.app.state, "retriever", None)
    if retriever is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="retriever is not initialized",
        )
    return retriever


__all__ = ["get_llm_provider_dep", "get_retriever_dep"]

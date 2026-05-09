"""Provider adapters — the *single point of LLM interaction* for the project.

Every other layer talks to providers through these protocols (see `base.py`).
"""

from app.providers.base import (
    EmbeddingProvider,
    EmbeddingResponse,
    LLMProvider,
    LLMResponse,
    Message,
    ProviderError,
    StructuredOutputSchema,
    TokenUsage,
    ToolCall,
    ToolDefinition,
)
from app.providers.factory import (
    get_embedding_provider,
    get_llm_provider,
)

__all__ = [
    "EmbeddingProvider",
    "EmbeddingResponse",
    "LLMProvider",
    "LLMResponse",
    "Message",
    "ProviderError",
    "StructuredOutputSchema",
    "TokenUsage",
    "ToolCall",
    "ToolDefinition",
    "get_embedding_provider",
    "get_llm_provider",
]

"""HTTP request/response schemas for B9.

Mirrors ``frontend/src/lib/types.ts`` (the chat contract section). The
shapes here are the canonical wire types — Pydantic does the validation
on the way in and the JSON encoding on the way out; the frontend mirrors
these by hand. Adding a non-nullable field here is a breaking change for
the frontend; nullable additions are non-breaking.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.providers import TokenUsage

# ---- Request ----------------------------------------------------------


class ChatHistoryTurn(BaseModel):
    """One prior turn supplied by the client; consumed only by rewrite."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    conversation_id: str | None = None
    history: list[ChatHistoryTurn] = Field(default_factory=list)


# ---- Response — shared blocks ----------------------------------------


class ChatCitation(BaseModel):
    """One citation in the wire response.

    Maps from :class:`app.agent.verifier.VerifiedCitation`. ``document``
    is the source filename (``<document_id>.md``) — the literal answer to
    "which file did this quote come from?" — and ``heading`` is the leaf
    of ``heading_path`` for one-line rendering on a citation chip.
    """

    model_config = ConfigDict(extra="forbid")

    passage_id: str
    document: str
    document_updated: date | None
    heading: str
    heading_path: list[str]
    quote: str
    passage_text: str | None = None


class DebugStep(BaseModel):
    """One observable step the orchestrator took, in wire form.

    ``result`` carries a step-kind-specific summary of what the step
    *produced* — tool return values, the LLM's tool-call list or parsed
    output, the verifier's verified/failures lists, the final answer
    text. The shape varies by ``kind`` (it's a free-form JSON object on
    the wire); rendering lives in the frontend ``DebugDrawer``.
    """

    model_config = ConfigDict(extra="forbid")

    step_id: str
    kind: Literal["llm_call", "tool_call", "verifier", "response"]
    name: str
    detail: str
    duration_ms: int = 0
    usage: TokenUsage | None = None
    cost_usd: float | None = None
    result: dict[str, Any] | None = None


class UsageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_total_cost_usd: float
    conversation_total_cost_usd: float
    step_count: int
    duration_ms: int = 0


class DebugBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_calls: list[DebugStep]
    verification_passed: bool
    steps: list[DebugStep]


# ---- Response — answer / clarify branches -----------------------------


class ChatAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["answer"] = "answer"
    answer: str
    citations: list[ChatCitation]
    general_knowledge_used: bool
    general_knowledge_section: str | None
    out_of_scope: bool
    disclaimer: str
    usage_summary: UsageSummary
    debug: DebugBlock
    conversation_id: str
    question_id: str


class ChatClarifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["clarifying_question"] = "clarifying_question"
    question: str
    options: list[str]
    disclaimer: str
    usage_summary: UsageSummary
    debug: DebugBlock
    conversation_id: str
    question_id: str


ChatResponse = Annotated[
    ChatAnswerResponse | ChatClarifyResponse,
    Field(discriminator="kind"),
]


# ---- Admin: conversation review --------------------------------------


class ConversationQuestionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    timestamp: datetime
    language: Literal["pt", "en", "es"]
    rewritten_question: str | None
    answer_or_question: dict[str, Any]
    verifier_passed: bool
    step_count: int
    step_kinds: list[str]
    retriever: str
    verifier_strategy: str


class ConversationTraceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    questions: list[ConversationQuestionSummary]
    step_count_total: int


class ConversationCostQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    llm_call_count: int
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    reasoning_tokens: int
    cost_usd: float


class ConversationCostResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    questions: list[ConversationCostQuestion]
    total_cost_usd: float
    total_llm_calls: int


## ---- Chat-side history (frontend sidebar) -----------------------------


class ConversationListItem(BaseModel):
    """One row in the user-facing conversation sidebar."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    title: str  # first user_question, truncated by the server
    first_ts: datetime
    last_ts: datetime
    question_count: int


class ConversationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversations: list[ConversationListItem]


class ConversationMessage(BaseModel):
    """One reconstructed turn — user question + agent response."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    timestamp: datetime
    user_question: str
    language: Literal["pt", "en", "es"]
    kind: Literal["answer", "clarifying_question"]
    answer: str | None = None
    citations: list[ChatCitation] = Field(default_factory=list)
    general_knowledge_used: bool | None = None
    general_knowledge_section: str | None = None
    out_of_scope: bool | None = None
    clarifying_question: str | None = None
    clarifying_options: list[str] = Field(default_factory=list)
    verifier_passed: bool


class ConversationMessagesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    messages: list[ConversationMessage]


class QuestionStepsResponse(BaseModel):
    """Per-question reconstructed debug trace, served from audit_log.

    Drives the per-message debug drawer when the user opens it on a
    historical message (re-loaded from the sidebar) — the live response
    already carries this shape inline as ``ChatAnswerResponse.debug``.
    """

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    question_id: str
    steps: list[DebugStep]
    usage_summary: UsageSummary
    verifier_passed: bool


__all__ = [
    "ChatAnswerResponse",
    "ChatCitation",
    "ChatClarifyResponse",
    "ChatHistoryTurn",
    "ChatRequest",
    "ChatResponse",
    "ConversationCostQuestion",
    "ConversationCostResponse",
    "ConversationListItem",
    "ConversationListResponse",
    "ConversationMessage",
    "ConversationMessagesResponse",
    "ConversationQuestionSummary",
    "ConversationTraceResponse",
    "DebugBlock",
    "DebugStep",
    "QuestionStepsResponse",
    "UsageSummary",
]

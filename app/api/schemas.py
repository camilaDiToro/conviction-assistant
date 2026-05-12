"""HTTP request/response schemas."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.i18n import Language
from app.providers import TokenUsage


class StrictModel(BaseModel):
    """Base for every wire-shape in this module: rejects unknown fields."""

    model_config = ConfigDict(extra="forbid")


# ---- Request ----------------------------------------------------------


class ChatHistoryTurn(StrictModel):
    """One prior turn supplied by the client; consumed only by rewrite."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(StrictModel):
    question: str = Field(min_length=1)
    conversation_id: str | None = None
    history: list[ChatHistoryTurn] = Field(default_factory=list)


# ---- Response — shared blocks ----------------------------------------


class ChatCitation(StrictModel):
    """One citation in the wire response.

    Maps from :class:`app.agent.resolver.CitationResolution`. ``document``
    is the source filename (``<document_id>.md``); ``heading`` is the
    leaf of ``heading_path``. ``start`` and ``end`` are half-open
    character offsets into ``passage_text`` — both ``None`` when the
    model's quote didn't anchor (the popup shows the passage without a
    highlight). Citations whose passage couldn't be loaded at all are
    dropped before they reach this shape.
    """

    passage_id: str
    document: str
    heading: str
    heading_path: list[str]
    passage_text: str
    start: int | None = None
    end: int | None = None


class DebugStep(StrictModel):
    """One observable step the orchestrator took, in wire form.

    ``result`` carries a step-kind-specific summary of what the step
    *produced* — tool return values, the LLM's tool-call list or parsed
    output, the resolver's per-citation outcomes, the final answer text.
    The shape varies by ``kind`` (it's a free-form JSON object on the
    wire); rendering lives in the frontend ``DebugDrawer``.
    """

    step_id: str
    kind: Literal["llm_call", "tool_call", "resolver", "response"]
    name: str
    detail: str
    duration_ms: int = 0
    usage: TokenUsage | None = None
    result: dict[str, Any] | None = None


class UsageSummary(StrictModel):
    llm_call_count: int
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    reasoning_tokens: int
    step_count: int
    duration_ms: int = 0


class DebugBlock(StrictModel):
    tool_calls: list[DebugStep]
    steps: list[DebugStep]


# ---- Response — answer / clarify branches -----------------------------


class ChatAnswerResponse(StrictModel):
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


class ChatClarifyResponse(StrictModel):
    kind: Literal["clarifying_question"] = "clarifying_question"
    question: str
    options: list[str]
    disclaimer: str
    usage_summary: UsageSummary
    debug: DebugBlock
    conversation_id: str
    question_id: str


## ---- Chat-side history (frontend sidebar) -----------------------------


class ConversationListItem(StrictModel):
    """One row in the user-facing conversation sidebar."""

    conversation_id: str
    title: str  # first user_question, truncated by the server
    first_ts: datetime
    last_ts: datetime
    question_count: int


class ConversationListResponse(StrictModel):
    conversations: list[ConversationListItem]


class ConversationMessageBase(StrictModel):
    """Fields shared by every reconstructed turn, regardless of branch."""

    question_id: str
    timestamp: datetime
    user_question: str
    language: Language


class ConversationAnswerMessage(ConversationMessageBase):
    kind: Literal["answer"] = "answer"
    answer: str | None = None
    citations: list[ChatCitation] = Field(default_factory=list)
    general_knowledge_used: bool | None = None
    general_knowledge_section: str | None = None
    out_of_scope: bool | None = None


class ConversationClarifyMessage(ConversationMessageBase):
    kind: Literal["clarifying_question"] = "clarifying_question"
    clarifying_question: str | None = None
    clarifying_options: list[str] = Field(default_factory=list)


ConversationMessage = Annotated[
    ConversationAnswerMessage | ConversationClarifyMessage,
    Field(discriminator="kind"),
]


class ConversationMessagesResponse(StrictModel):
    conversation_id: str
    messages: list[ConversationMessage]


class QuestionStepsResponse(StrictModel):
    """Per-question reconstructed debug trace, served from audit_log.

    Drives the per-message debug drawer when the user opens it on a
    historical message (re-loaded from the sidebar) — the live response
    already carries this shape inline as ``ChatAnswerResponse.debug``.
    """

    conversation_id: str
    question_id: str
    steps: list[DebugStep]
    usage_summary: UsageSummary


__all__ = [
    "ChatAnswerResponse",
    "ChatCitation",
    "ChatClarifyResponse",
    "ChatHistoryTurn",
    "ChatRequest",
    "ConversationAnswerMessage",
    "ConversationClarifyMessage",
    "ConversationListItem",
    "ConversationListResponse",
    "ConversationMessage",
    "ConversationMessageBase",
    "ConversationMessagesResponse",
    "DebugBlock",
    "DebugStep",
    "QuestionStepsResponse",
    "StrictModel",
    "UsageSummary",
]

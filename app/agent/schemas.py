"""Pydantic models + JSON schemas for the agent orchestrator.

Two layers live here:

1. **Pydantic models** (``AnswerOutput`` / ``ClarifyingQuestionOutput``,
   ``Citation``, ``StepRecord``, ``ConversationTurn``, ``AgentResult``)
   — the in-process types the orchestrator and tests use.
2. **A hand-written JSON schema** (``AGENT_OUTPUT_JSON_SCHEMA``) that is
   sent to the LLM via ``StructuredOutputSchema``.

The flat-schema-with-nullable-fields pattern matches the project
convention of hand-written tool schemas (see ``app/agent/tools/registry.py``);
it sidesteps Pydantic's ``oneOf`` emission for discriminated unions.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.agent.resolver import OffsetResolution
from app.i18n import Language
from app.providers import StructuredOutputSchema, TokenUsage


class Citation(BaseModel):
    """One verbatim quote attributed to a passage in the corpus.

    The model emits ``{passage_id, quote}``; the orchestrator runs the
    offset resolver to turn the quote into ``(start, end)`` offsets and
    drops the literal text before the response is built. The literal
    ``quote`` therefore lives only in-process — it never reaches the
    HTTP response or storage.
    """

    model_config = ConfigDict(extra="forbid")

    passage_id: str
    quote: str


class AnswerOutput(BaseModel):
    """The grounded answer shape — the common case.

    ``extra="ignore"`` is intentional: the LLM emits a flat object with
    all 8 schema fields (the unused branch's fields nullable). Pydantic
    drops the irrelevant fields when validating into this concrete
    branch.
    """

    model_config = ConfigDict(extra="ignore")

    kind: Literal["answer"] = "answer"
    answer: str
    citations: list[Citation]
    general_knowledge_used: bool
    general_knowledge_section: str | None
    out_of_scope: bool
    conflict_detected: bool = False
    conflict_statement: str | None = None

    @model_validator(mode="after")
    def _check_invariants(self) -> "AnswerOutput":
        section = (self.general_knowledge_section or "").strip()
        if self.general_knowledge_used and not section:
            raise ValueError(
                "general_knowledge_used=true requires a non-empty general_knowledge_section"
            )
        if section and not self.general_knowledge_used:
            raise ValueError(
                "non-empty general_knowledge_section requires general_knowledge_used=true"
            )
        if self.out_of_scope and self.citations:
            raise ValueError("out_of_scope=true requires empty citations")
        conflict = (self.conflict_statement or "").strip()
        if self.conflict_detected and not conflict:
            raise ValueError("conflict_detected=true requires a non-empty conflict_statement")
        if conflict and not self.conflict_detected:
            raise ValueError("non-empty conflict_statement requires conflict_detected=true")
        return self


class ClarifyingQuestionOutput(BaseModel):
    """Returned only when answering would risk citing the wrong topic."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["clarifying_question"] = "clarifying_question"
    question: str
    options: list[str]


AgentOutput = Annotated[
    AnswerOutput | ClarifyingQuestionOutput,
    Field(discriminator="kind"),
]


class ConversationTurn(BaseModel):
    """One prior turn in the conversation, fed only to the rewrite stage."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class StepRecord(BaseModel):
    """One observable step the orchestrator took.

    The agent emits one record per LLM call and one per tool call; the
    HTTP layer wraps these with ``question_id`` / ``conversation_id`` and
    persists them into ``audit_log``. LLM-call records carry raw token
    usage so debug views can show exactly what the provider reported.
    """

    model_config = ConfigDict(extra="forbid")

    step_id: str
    kind: Literal["llm_call", "tool_call", "resolver"]
    timestamp: datetime
    payload: dict[str, Any]
    usage: TokenUsage | None = None
    tool_name: str | None = None
    duration_ms: int = 0


class TokenTotals(BaseModel):
    """Aggregated token counts across every LLM call in one agent turn.

    Computed from :class:`StepRecord` entries with ``kind='llm_call'``;
    the HTTP layer wraps these totals into a wire ``UsageSummary``.
    """

    model_config = ConfigDict(extra="forbid")

    llm_call_count: int
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int
    reasoning_tokens: int


class AgentResult(BaseModel):
    """One full agent turn: structured output + the trace that produced it.

    ``resolution`` carries one :class:`CitationResolution` per citation
    the model emitted, in original order, with the passage provenance
    and ``(start, end)`` offsets the wire response needs. The HTTP layer
    reads this to build ``ChatCitation`` rows without re-fetching
    passages.
    ``None`` when ``output`` is a ``ClarifyingQuestionOutput`` (no
    citations to resolve).

    ``language`` is the model-detected language from the rewrite stage
    (PT / ES / EN), used to localize the disclaimer. Single source of
    truth for the answer-language choice.
    """

    model_config = ConfigDict(extra="forbid")

    output: AgentOutput
    rewritten_question: str | None
    language: Language
    steps: list[StepRecord]
    tool_call_count: int
    search_count: int
    resolution: OffsetResolution | None = None

    @property
    def token_totals(self) -> TokenTotals:
        """Sum token counts across every ``llm_call`` step in this turn."""
        usages = [s.usage for s in self.steps if s.kind == "llm_call" and s.usage is not None]
        return TokenTotals(
            llm_call_count=len(usages),
            prompt_tokens=sum(u.prompt_tokens for u in usages),
            completion_tokens=sum(u.completion_tokens for u in usages),
            cached_tokens=sum(u.cached_tokens for u in usages),
            reasoning_tokens=sum(u.reasoning_tokens for u in usages),
        )


# --- JSON schemas for the LLM ---------------------------------------------


AGENT_OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {
            "type": "string",
            "enum": ["answer", "clarifying_question"],
            "description": (
                "Discriminator. 'answer' for grounded responses (with citations); "
                "'clarifying_question' only when the user's query is genuinely ambiguous "
                "and answering would risk citing the wrong topic."
            ),
        },
        "answer": {
            "type": ["string", "null"],
            "description": (
                "The grounded answer text. Required when kind='answer'; null otherwise. "
                "Mirror the user's language (PT/EN/ES). Never include the disclaimer "
                "(the orchestrator appends it deterministically)."
            ),
        },
        "citations": {
            "type": ["array", "null"],
            "description": (
                "List of verbatim citations. Required when kind='answer'. Every claim "
                "in 'answer' must be backed by at least one citation. Each quote MUST "
                "be a verbatim substring of the cited passage's text — the backend "
                "uses it to anchor the citation to a (start, end) region of the "
                "passage. Non-verbatim quotes still surface but with no highlight."
            ),
            "items": {
                "type": "object",
                "properties": {
                    "passage_id": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["passage_id", "quote"],
                "additionalProperties": False,
            },
        },
        "general_knowledge_used": {
            "type": ["boolean", "null"],
            "description": (
                "Required when kind='answer'. True only if the response uses general "
                "knowledge alongside conviction citations. Always prefer a real "
                "conviction reference (even tangential) over general knowledge."
            ),
        },
        "general_knowledge_section": {
            "type": ["string", "null"],
            "description": (
                "Required when kind='answer' and general_knowledge_used=true. A "
                "clearly-marked block (e.g. starting 'Not from Decade convictions — "
                "general knowledge:') that contains all and only general-knowledge "
                "claims. Never interleave general-knowledge with cited claims."
            ),
        },
        "out_of_scope": {
            "type": ["boolean", "null"],
            "description": (
                "Required when kind='answer'. True when the user's message is not "
                "a question about Decade's investment convictions — covers greetings, "
                "small talk, and unrelated topics. Emit citations=[] in that case."
            ),
        },
        "conflict_detected": {
            "type": ["boolean", "null"],
            "description": (
                "Required when kind='answer'. Set true when two or more cited "
                "passages contradict each other on the user's topic (Rule B). "
                "When true, conflict_statement must be a non-empty sentence "
                "naming the disagreement explicitly."
            ),
        },
        "conflict_statement": {
            "type": ["string", "null"],
            "description": (
                "Required when conflict_detected=true. One short sentence that "
                "names the disagreement using an explicit marker the analyst can "
                "scan (e.g. 'as convicções divergem', 'convictions disagree', "
                "'las convicciones difieren'). Null when conflict_detected=false."
            ),
        },
        "question": {
            "type": ["string", "null"],
            "description": (
                "Required when kind='clarifying_question'; null otherwise. The "
                "clarifying question to ask the user, in their language."
            ),
        },
        "options": {
            "type": ["array", "null"],
            "items": {"type": "string"},
            "description": (
                "Required when kind='clarifying_question'. 2-4 short options the "
                "user can pick from."
            ),
        },
    },
    "required": [
        "kind",
        "answer",
        "citations",
        "general_knowledge_used",
        "general_knowledge_section",
        "out_of_scope",
        "conflict_detected",
        "conflict_statement",
        "question",
        "options",
    ],
    "additionalProperties": False,
}


REWRITE_OUTPUT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rewritten_question": {
            "type": "string",
            "description": (
                "A self-contained version of the user's new question with all "
                "referents (pronouns, 'and what about X?', etc.) resolved against "
                "the prior turns. If the new question is already self-contained, "
                "return it unchanged. Preserve the user's language verbatim."
            ),
        },
        "detected_language": {
            "type": "string",
            "enum": ["pt", "es", "en"],
            "description": (
                "The language of the user's new question — Portuguese, Spanish, "
                "or English. The downstream agent uses this to pin its answer "
                "language regardless of the cited passages' language. Choose the "
                "language of the new question, not of the prior turns."
            ),
        },
    },
    "required": ["rewritten_question", "detected_language"],
    "additionalProperties": False,
}


AGENT_OUTPUT_SCHEMA = StructuredOutputSchema(
    name="agent_output",
    json_schema=AGENT_OUTPUT_JSON_SCHEMA,
)


REWRITE_OUTPUT_SCHEMA = StructuredOutputSchema(
    name="rewrite_output",
    json_schema=REWRITE_OUTPUT_JSON_SCHEMA,
)

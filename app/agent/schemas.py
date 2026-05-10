"""Pydantic models + JSON schemas for the agent orchestrator.

Two layers live here:

1. **Pydantic models** (``AnswerOutput`` / ``ClarifyingQuestionOutput``,
   ``Citation``, ``StepRecord``, ``ConversationTurn``, ``AgentResult``)
   — the in-process types the orchestrator and tests use.
2. **A hand-written JSON schema** (``AGENT_OUTPUT_JSON_SCHEMA``) that is
   sent to the LLM via ``StructuredOutputSchema``. It is hand-written
   because OpenAI strict mode does not support ``oneOf`` (only
   ``anyOf``); the cleanest strict-compatible shape is a flat object
   with every field nullable, discriminated by ``kind``. The Pydantic
   discriminated union validates the parsed output back into the
   correct concrete type after the model returns.

The flat-schema-with-nullable-fields pattern matches the project
convention of hand-written tool schemas (see ``app/tools/registry.py``);
it sidesteps Pydantic's ``oneOf`` emission for discriminated unions.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agent.verifier import VerifiedCitation
from app.providers import StructuredOutputSchema, TokenUsage


class Citation(BaseModel):
    """One verbatim quote attributed to a passage in the corpus."""

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

    The agent emits one record per LLM call and one per tool call; B9
    wraps these with ``question_id`` / ``conversation_id`` and persists
    them into ``audit_log``. Cost USD is **not** stored — derived in
    ``app/services/cost.py`` from ``usage`` at audit-log read time.
    """

    model_config = ConfigDict(extra="forbid")

    step_id: str
    kind: Literal["llm_call", "tool_call", "verifier"]
    timestamp: datetime
    payload: dict[str, Any]
    usage: TokenUsage | None = None
    tool_name: str | None = None
    duration_ms: int = 0


class AgentResult(BaseModel):
    """One full agent turn: structured output + the trace that produced it.

    ``verified_citations`` carries provenance for each citation that
    survived verification — passage_id, document_id, document_title,
    heading_path, document_updated, quote. B9 reads this to enrich the
    HTTP response without re-fetching passages. ``None`` when ``output``
    is a ``ClarifyingQuestionOutput`` (no citations to verify).
    """

    model_config = ConfigDict(extra="forbid")

    output: AgentOutput
    rewritten_question: str | None
    steps: list[StepRecord]
    tool_call_count: int
    search_count: int
    verified_citations: list[VerifiedCitation] | None = None


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
                "be a verbatim substring of the cited passage's text."
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
                "Required when kind='answer'. True if the question falls outside "
                "Decade's investment-conviction domain entirely."
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
    },
    "required": ["rewritten_question"],
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

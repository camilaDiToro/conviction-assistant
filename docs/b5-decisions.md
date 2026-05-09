# B5 — decisions log

Per-step decisions for ROADMAP B5 (`list_documents`, `read_document_outline`, `read_passage`). Companion to the architectural rules pinned in `docs/ARCHITECTURES.md` § "Tools layer". This file captures the *step-local* choices — return shapes, sort orders, error semantics, tool descriptions — that don't rise to architecture but should be visible to a reviewer.

For the high-level rules (storage-agnosticism, `ToolContext` DI seam, hand-written JSON schemas, single registry, typed errors), read `docs/ARCHITECTURES.md` § "Tools layer" first.

---

## Return shapes

### `list_documents() -> list[DocSummary]`

Reuses the existing `DocSummary` Pydantic schema (`app/schemas/passage.py`). Fields: `id`, `title`, `document_updated` (`date | None`), `passage_count`.

**Sort order:** `document_id` ASC. Matches the existing repository behavior. Deterministic; no recency bias on what the agent sees first.

### `read_document_outline(document_id) -> DocumentOutline`

New schema added in B5: `DocumentOutline { document_id, document_title, document_updated, passage_count, headings: list[Heading] }`.

**Why a new schema instead of reusing `list[Heading]`?** Surfacing `document_updated` and `passage_count` next to the headings supports CLAUDE.md Rule B (conflicting-conviction surfacing by date) without forcing the agent to call `list_documents` first every time it inspects a document. The shape is the smallest extension that carries that signal.

### `read_passage(passage_id) -> Passage`

Returns the full `Passage` schema (`id`, `document_id`, `document_title`, `heading`, `heading_path`, `text`, `document_updated`). Same shape `search_convictions` will return per hit in B6, so the model's mental model of "what a passage looks like" is consistent across tools.

---

## Empty-result semantics

| Tool                    | Bad input                    | Behavior                              |
|-------------------------|------------------------------|---------------------------------------|
| `list_documents`        | empty corpus                 | returns `[]` (pre-ingest is normal)   |
| `read_document_outline` | unknown `document_id`        | raises `DocumentNotFoundError`        |
| `read_passage`          | unknown `passage_id`         | raises `PassageNotFoundError`         |

`read_document_outline` detects "document does not exist" via empty headings — at v1 every ingested document has ≥ 1 passage, so an empty heading list is a reliable proxy for "no such document." Both errors subclass `DomainError` (`app/errors.py`); the agent loop in B8 catches them and feeds the error back to the LLM as a tool-error message.

---

## Tool function signatures

```python
async def list_documents(ctx: ToolContext) -> list[DocSummary]: ...
async def read_document_outline(ctx: ToolContext, *, document_id: str) -> DocumentOutline: ...
async def read_passage(ctx: ToolContext, *, passage_id: str) -> Passage: ...
```

- `ctx` is positional-only by convention.
- All other arguments are **keyword-only** (`*,`). The agent loop dispatches with `await func(ctx, **args)` where `args` is a dict parsed from the LLM's tool call; positional misuse is impossible.
- Tool `name` strings exactly match function names: `list_documents`, `read_document_outline`, `read_passage`.

---

## Tool descriptions

The LLM picks tools based on each tool's `description`. These were drafted in B5 and are subject to tuning during B8 prompt-engineering work.

| Tool                    | Description (drafted) |
|-------------------------|------------------------|
| `list_documents`        | "Return all conviction documents with their titles, last-updated dates (if known), and passage counts. Use this once early in a conversation to discover what documents are available." |
| `read_document_outline` | "Return one document's outline: its title, last-updated date, passage count, and the ordered list of headings (each with its passage_id). Use this to find which passage in a document covers a topic before reading it." |
| `read_passage`          | "Return the full text of one passage by ID, plus its document title, heading path, and last-updated date. This is the only tool that returns full passage text; other tools return identifiers and outlines." |

Test `test_tool_definitions_have_nontrivial_descriptions` floors each at 40 characters so an accidental `"TODO"` cannot ship.

---

## What B5 deliberately did NOT do

- **One new repository function.** Added `get_document_summary(document_id)` so `read_document_outline` is a direct single-doc lookup instead of a corpus-wide `list_documents()` aggregation followed by a linear scan and an `assert`. The existing `read_outline()` and `get()` still cover the other two tools.
- **No `search_convictions`.** B6 adds it; the registry will gain a fourth `ToolEntry` then.
- **No agent loop.** B8.
- **No tool dispatcher** (LLM-args dict → call). B8 adds it; the registry shape is designed for it.
- **No Pydantic-derived JSON schemas.** Hand-written dicts are shorter and trivially satisfy OpenAI strict mode at this complexity. The agent's *output* schema in B8 may use Pydantic; that's a separate decision and does not retroactively change tool inputs.

---

## Files touched in B5

**Created:**
- `app/tools/__init__.py`, `app/tools/context.py`, `app/tools/list_documents.py`, `app/tools/read_document_outline.py`, `app/tools/read_passage.py`, `app/tools/registry.py`
- `tests/tools/__init__.py`, `tests/tools/test_simple_tools.py`
- `docs/b5-decisions.md`

**Edited:**
- `app/repositories/passages.py` — added `get_document_summary` (single-doc lookup used by `read_document_outline`)
- `app/errors.py` — added `PassageNotFoundError`, `DocumentNotFoundError`
- `app/schemas/passage.py` — added `DocumentOutline`
- `app/schemas/__init__.py` — re-export `DocumentOutline`
- `docs/ARCHITECTURES.md` — added § "Tools layer"
- `CLAUDE.md` — pointer to the new tools layer
- `docs/ROADMAP.md` — checked off B5; deviation notes

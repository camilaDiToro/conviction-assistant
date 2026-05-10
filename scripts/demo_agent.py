"""Manual smoke / fixture-driven demo for the agent orchestrator.

  uv run python scripts/demo_agent.py "What is a CDB?"
  uv run python scripts/demo_agent.py --provider stub --fixture basic_search "..."

Stub mode runs against a YAML fixture in
``tests/fixtures/agent_scenarios/`` and a real ToolContext built from
the project's SQLite store + BM25 index — useful as a deterministic
end-to-end check. OpenAI mode uses the real provider; requires
``OPENAI_API_KEY`` and an ingested corpus.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Make `app.*` importable when invoking the script as a file, not as a
# module (`python scripts/demo_agent.py ...`). Tests don't need this —
# pytest adds the project root automatically.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import ConversationTurn, run  # noqa: E402
from app.config import db, settings  # noqa: E402
from app.providers import LLMProvider, get_llm_provider  # noqa: E402
from app.providers.stub import StubLLM, load_stub_responses  # noqa: E402
from app.services.search import BM25Index  # noqa: E402
from app.agent.tools import ToolContext  # noqa: E402

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "agent_scenarios"


def _build_llm(args: argparse.Namespace) -> LLMProvider:
    if args.provider == "stub":
        if not args.fixture:
            raise SystemExit("--provider stub requires --fixture <name>")
        path = FIXTURES_DIR / f"{args.fixture}.yaml"
        if not path.exists():
            raise SystemExit(f"fixture not found: {path}")
        return StubLLM(load_stub_responses(path))
    return get_llm_provider()


async def _amain(args: argparse.Namespace) -> int:
    db.migrate(settings.sqlite_path)
    engine = db.make_engine(settings.async_database_url)
    factory = db.make_session_factory(engine)

    index = BM25Index()
    async with factory() as session:
        await index.build(session)
        ctx = ToolContext(session=session, search_index=index)
        llm = _build_llm(args)

        history = [
            ConversationTurn(role=turn["role"], content=turn["content"])
            for turn in (args.history or [])
        ]
        result = await run(args.message, history, tool_ctx=ctx, llm=llm)

    print(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False, default=str))
    await engine.dispose()
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one agent turn.")
    parser.add_argument("message", help="The user's question.")
    parser.add_argument(
        "--provider",
        choices=["openai", "stub"],
        default=settings.llm_provider,
        help="Which LLM to use (default: from settings).",
    )
    parser.add_argument(
        "--fixture",
        default=None,
        help="Stub fixture name (basename without .yaml); required when --provider stub.",
    )
    parser.add_argument(
        "--history",
        type=_parse_history,
        default=None,
        help='JSON list of {role, content} turns, e.g. \'[{"role":"user","content":"..."}]\'',
    )
    return parser.parse_args()


def _parse_history(raw: str) -> list[dict[str, Any]]:
    return list(json.loads(raw))


def main() -> None:
    args = _parse_args()
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()

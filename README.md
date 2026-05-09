# Decade AI Challenge

Conversational AI assistant grounded on Decade's investment conviction documents.

- Brief: [`AI_CHALLENGE.md`](AI_CHALLENGE.md)
- Build plan: [`docs/ROADMAP.md`](docs/ROADMAP.md)
- Architecture & design: [`docs/ARCHITECTURES.md`](docs/ARCHITECTURES.md), [`CLAUDE.md`](CLAUDE.md)

## Quick start

```sh
uv sync
uv run uvicorn app.main:app --reload
curl http://localhost:8000/health
```

## Test

```sh
uv run pytest
uv run ruff check
```

## Status

Currently at **Step B2** of the roadmap (markdown parser). See `docs/ROADMAP.md` for what's next.

## Running by parts

Each step in `docs/ROADMAP.md` ships a smoke check you can run independently. Add one entry here per step as it lands.

### B1 — health endpoint

```sh
uv run uvicorn app.main:app --reload
# in another shell:
curl http://localhost:8000/health
# expected: {"status":"ok"}
```

### B2 — markdown parser

```sh
# parse the corpus and print stats (doc count, dated/undated, longest passages)
uv run python -m app.parser.cli convictions/

# parser-only tests
uv run pytest tests/parser
```

### All tests + lint

```sh
uv run pytest
uv run ruff check
```

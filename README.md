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

Currently at **Step B1** of the roadmap (skeleton + `/health`). See `docs/ROADMAP.md` for what's next.

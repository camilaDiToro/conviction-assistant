# Scaling cheat-sheet

What changes in the architecture if concurrent users grow beyond v1's "small internal team (<10)".

## v1 — <10 concurrent users (current)

- Single FastAPI instance, in-process BM25, in-memory or SQLite session store.
- No load balancer, no auth beyond a simple API key, no rate limiting.
- Cost tracking already in place (see `ASSUMPTIONS.md` § "Cost tracking — REQUIRED").

## ~10–100 concurrent users

What needs to change:

- **Stateless API instances** behind a load balancer (multiple workers, Gunicorn or similar).
- **External session / conversation store** (Redis or Postgres). In-process state stops working with multiple workers.
- **Provider rate-limit handling** in the adapter — exponential backoff with jitter, configurable retry budget, circuit breaker per provider.
- **Per-user / per-tenant rate limiting** at the API layer (Redis-backed token bucket).
- **Connection pooling** for the DB and any external HTTP client.
- **Background re-index task** when convictions change (still on cold start as the default, but a `/admin/reindex` endpoint becomes useful).
- **Hot-query cache** for repeated questions at the orchestrator level (not the LLM provider's cache — that's a different layer).
- **Real observability**: per-request tracing (OpenTelemetry), structured logs, cost dashboards aggregated from the per-step usage records.
- **Auth & audit**: real JWT / OAuth instead of the v1 API key.

What does **not** change:

- The agent loop, citation contract, verifier, and provider abstraction stay identical.
- BM25 is probably still fine; only the corpus growth (see `RETRIEVAL_SCALE.md`) drives upgrades to hybrid.

## 100+ concurrent users

Everything from the previous tier, plus:

- **External search index** (Elasticsearch / OpenSearch / Tantivy server). In-process BM25 stops scaling once index rebuilds become noticeable per worker.
- **Real vector store** if dense retrieval is in use (pgvector, Qdrant, Weaviate). Aligns with the corpus-scale guidance in `RETRIEVAL_SCALE.md`.
- **Queue-based async processing** for long-running questions or batch evals — Celery / Arq / temporal; the API enqueues, the worker runs the loop.
- **Provider failover** — multi-provider adapter with health checks; degrade gracefully when the primary provider is down or rate-limited.
- **Per-user cost budgets** with enforcement (the cost tracker already exists; now it gates new requests).
- **Sharding by tenant** if Decade ever multi-tenants this internally (separate corpus / separate convictions per business unit).
- **Caching at multiple layers** — provider prompt caching, application response cache (with invalidation tied to corpus rebuilds), edge cache for static UI.

## Rule of thumb

| Concurrency | What changes | Cost |
|---|---|---|
| <10 (v1) | Nothing — single instance is fine | Trivial infra |
| 10–100 | Stateless instances + Redis + rate limits + rich observability | Real ops work, but no architecture change |
| 100+ | External search/vector store + queues + failover + budget enforcement | Real production system |

The agent loop, citation contract, and verifier from `ARCHITECTURES.md` stay identical at every tier. The provider abstraction is what makes this scaling story possible — every component has clean seams.

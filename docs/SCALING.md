# Scaling cheat-sheet

What changes in the architecture if concurrent users grow beyond v1's "small internal team (<10)".

## v1 — <10 concurrent users (current)

- Single FastAPI instance.
- One Postgres (with `pgvector` and `unaccent`) holding passages, FTS index, embeddings, conversations, audit log, cost log.
- No load balancer, no Redis, no auth beyond a simple API key, no rate limiting.
- Cost tracking already in place (see `ASSUMPTIONS.md` § "Cost tracking — REQUIRED").

## ~10–100 concurrent users

What needs to change:

- **Stateless API instances** behind a load balancer (multiple workers, Gunicorn or similar). Already trivial because all state lives in Postgres.
- **Postgres connection pooling** — pgbouncer or the SQLAlchemy pool with sane sizing.
- **Redis** for hot-query cache + rate-limit token buckets (Postgres can do both, but Redis is faster and idiomatic).
- **Provider rate-limit handling** in the adapter — exponential backoff with jitter, configurable retry budget, circuit breaker per provider.
- **Per-user / per-tenant rate limiting** at the API layer (Redis-backed token bucket).
- **Background re-index task** for when convictions change between deploys (a `/admin/reindex` endpoint or a cron job that diffs file hashes against `passages.source_hash` and upserts changed rows).
- **Real observability**: per-request tracing (OpenTelemetry), structured logs, cost dashboards aggregated from the audit log.
- **Auth & audit**: real JWT / OAuth instead of the v1 API key.

What does **not** change:

- The agent loop, citation contract, verifier, and provider abstraction stay identical.
- Same Postgres, same schema. Hybrid Postgres FTS + pgvector is still fine at this tier; corpus size (see `RETRIEVAL_SCALE.md`) is the trigger to add a reranker, not user count.

## 100+ concurrent users

Everything from the previous tier, plus:

- **Dedicated search engine** (Elasticsearch / OpenSearch or ParadeDB `pg_search` for true BM25 inside Postgres). Postgres FTS holds up well, but ranking quality and faceting matter more at this scale.
- **Dedicated vector store** (Qdrant / Weaviate) if pgvector hits index-build or query latency limits. Otherwise stay on pgvector with HNSW indexes.
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

# Scale notes — concurrency-driven level-ups

What changes operationally when concurrent traffic grows past v1's "small internal team (<10)". The architectural story (production-grade vs deliberately simplified per concern; what breaks BM25 first and why) is covered in the frontend design pages (`Tiers`, `Retrieval`). This file only collects the **infra-side** level-ups that don't fit there.

The agent loop, citation contract, resolver, and provider abstraction are unchanged at every tier — only deployment shape and operational seams differ.

## ~10–100 concurrent users

- **Stateless API instances** behind a load balancer (gunicorn + uvicorn workers). Already trivial because all state lives in the DB.
- **DB connection pooling** — pgbouncer (when storage promotes to Postgres) or sized SQLAlchemy pool.
- **Redis** for rate-limit token buckets and a hot-query cache (faster than doing both in the DB).
- **Provider rate-limit handling in the adapter** — exponential backoff with jitter, per-provider circuit breaker, configurable retry budget.
- **Per-user / per-tenant rate limiting** at the API layer (Redis-backed token bucket).
- **Background re-index task** — `/admin/reindex` endpoint or cron job diffs file hashes against `passages.source_hash` and upserts changed rows; replaces the v1 "POST /admin/ingest" full rebuild.
- **Real observability** — OpenTelemetry traces, structured logs, token-usage dashboards rolled up from `audit_log`.
- **Real auth** — OIDC / JWT instead of the v1 shared chat token.

## 100+ concurrent users

Everything from the previous tier, plus:

- **Dedicated lexical search** — Elasticsearch / OpenSearch, or ParadeDB `pg_search` for true BM25 inside Postgres. Postgres FTS holds up but ranking/faceting matter more at this scale.
- **Dedicated vector store** — Qdrant / Weaviate if pgvector hits index-build or query-latency limits; otherwise stay on pgvector with HNSW.
- **Queue-based async processing** — Celery / Arq / Temporal. API enqueues; worker runs the agent loop. Frees the HTTP path from long-tail latency.
- **Provider failover** — multi-provider adapter with health checks; degrade gracefully on primary outage / rate limit.
- **Per-user request quotas enforced** — promotion is "now it gates new requests."
- **Tenant sharding** — if multi-tenant ever happens (separate corpus per business unit).
- **Layered caching** — provider prompt caching, response cache invalidated on corpus rebuilds, edge cache for static UI.

## Rule of thumb

| Concurrency | What changes | Ops footprint |
|---|---|---|
| <10 (v1) | Nothing — single instance is fine | Trivial infra |
| 10–100 | Stateless instances + Redis + rate limits + observability | Real ops work, no architecture change |
| 100+ | External search/vector store + queues + failover + quota enforcement | Real production system |

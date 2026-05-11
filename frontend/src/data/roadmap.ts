export type RoadmapStatus = 'done' | 'in_progress' | 'pending'

export interface RoadmapStep {
  id: string
  title: string
  status: RoadmapStatus
  description: string
  ships: string[]
  levelUp?: string
}

// Update between sessions as steps land.
export const ROADMAP: RoadmapStep[] = [
  {
    id: 'B1',
    title: 'FastAPI skeleton',
    status: 'done',
    description: 'Health endpoint, Pydantic config, pytest setup, ruff + mypy pipelines.',
    ships: ['/health endpoint', 'pyproject.toml stack', 'lint + type-check CI'],
  },
  {
    id: 'B2',
    title: 'Markdown parser → passages',
    status: 'done',
    description: 'Pure markdown → Passage[] transformation. Stable IDs (slug), date extraction (6 variants), NFKD accent strip.',
    ships: ['app/services/parser/', 'date-header parsing', '~400 passages from 30 docs'],
  },
  {
    id: 'B3',
    title: 'SQLAlchemy async store + ingest',
    status: 'done',
    description: 'AsyncSession + select() over aiosqlite. Repository contract is the swap point; level-up to Postgres documented.',
    ships: ['app/repositories/passages.py', 'POST /admin/ingest', 'Alembic migrations'],
    levelUp: 'Postgres + pgvector when concurrency demands; the repo contract stays.',
  },
  {
    id: 'B4',
    title: 'Provider abstraction + OpenAI adapter',
    status: 'done',
    description: 'LLMProvider / EmbeddingProvider protocols. OpenAI gpt-5 adapter with structured output. StubProvider for CI.',
    ships: ['app/providers/{openai,stub}.py', 'TokenUsage', '_model_prices.json (vendored)'],
    levelUp: 'Anthropic adapter ships in B10 as the portability proof.',
  },
  {
    id: 'B5',
    title: 'Read-only tools (3 of 4)',
    status: 'done',
    description: 'list_documents, read_document_outline, read_passage with hand-written JSON schemas. ToolContext DI.',
    ships: ['app/tools/', 'TOOLS registry', 'pure-function tests'],
  },
  {
    id: 'B6',
    title: 'BM25 retrieval + search_convictions',
    status: 'done',
    description: 'In-memory BM25 over normalized passages. ≥80% pass on the 29-case retrieval golden set.',
    ships: ['app/retrieval/bm25.py', 'app/agent/tools/search_convictions.py', 'lifespan-built index'],
    levelUp: 'Hybrid (BM25 + multilingual embeddings + RRF) gated on cross-language eval failure.',
  },
  {
    id: 'B7',
    title: 'Offset resolver',
    status: 'in_progress',
    description: 'Deterministic literal-substring resolver. Citations that do not anchor still surface; popup shows the passage with no highlight.',
    ships: ['app/agent/resolver/substring.py', 'app/agent/resolver/base.py', 'anchor-rate metric'],
  },
  {
    id: 'B8',
    title: 'Bounded agent loop',
    status: 'pending',
    description: 'Max 5 tool calls, ≥1 search before answer, structured-JSON output, multi-turn rewrite of the user question.',
    ships: ['app/agent/loop.py', 'system prompt', 'agent-side language detection'],
  },
  {
    id: 'B9',
    title: '/chat endpoint + audit log + disclaimer',
    status: 'pending',
    description: 'POST /chat. Audit log row per step. Deterministic disclaimer injection (PT/EN/ES). usage_summary + debug.',
    ships: ['app/api/chat.py', 'app/repositories/audit.py', 'response wrapper'],
    levelUp: 'SSE streaming when latency matters more than simplicity.',
  },
  {
    id: 'B10',
    title: 'Eval suite + Anthropic adapter',
    status: 'pending',
    description: '~30 hand-written Q/A. Anchor rate as headline metric. Anthropic adapter as the portability proof.',
    ships: ['tests/eval/', 'pytest -m eval', 'app/providers/anthropic.py'],
  },
  {
    id: 'B11',
    title: 'README + production-readiness audit',
    status: 'pending',
    description: 'Final README, ASSUMPTIONS.md sweep, deployment notes refreshed.',
    ships: ['README.md', 'docs/DEPLOYMENT.md update'],
  },
]

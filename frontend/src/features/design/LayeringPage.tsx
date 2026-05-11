import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'

const RULES = [
  {
    rule: 'No SQL outside app/repositories/',
    why: 'Switching from SQLite to Postgres should touch one directory. Tools, services, and the agent never see a Connection object.',
    grep: `rg -t py "session\\.execute|text\\(|select\\(.*\\)\\.where" app/ \\
   --glob '!app/repositories/**'  # → must be empty`,
  },
  {
    rule: 'No SDK imports outside app/providers/',
    why: 'Single LLM point. Provider portability is grep-checkable.',
    grep: `rg -t py "import openai|from openai|import anthropic|from anthropic" app/ \\
   --glob '!app/providers/**'    # → must be empty`,
  },
  {
    rule: 'No os.getenv outside app/config/',
    why: 'Settings flow through one Pydantic Settings class. Anything else is hidden config.',
    grep: `rg -t py "os\\.getenv|os\\.environ" app/ \\
   --glob '!app/config/**'        # → must be empty`,
  },
  {
    rule: 'No HTTP raises in services/repositories',
    why: 'Services raise domain exceptions; the API layer maps them. Otherwise the service is HTTP-coupled and cannot be reused (CLI, queue worker).',
    grep: `rg -t py "raise HTTPException|status_code" app/services/ app/repositories/
# → must be empty`,
  },
] as const

export default function LayeringPage() {
  return (
    <article>
      <PageHeader
        eyebrow="Plumbing · Layering"
        title="Router → Service → Repository."
        lead={
          <>
            Each layer knows only the one below. Four invariants keep the layering honest;
            each is a single ripgrep. Configuration, errors, and lifecycle live here too —
            the boring scaffolding that makes the rest of the system possible to reason about.
          </>
        }
      />

      <Section eyebrow="Layers">
        <div className="my-2 grid grid-cols-1 md:grid-cols-5 gap-px bg-border border border-border">
          <Layer name="Router" path="app/api/" body="Thin controllers. Parse request, call service, wrap response. Maps domain exceptions to HTTP." />
          <Layer name="Service" path="app/services/" body="Business logic. Raises DomainError subclasses. Does not import HTTP." />
          <Layer name="Tools" path="app/tools/" body="Pure functions of (ToolContext, args). Storage-agnostic; call the repository." />
          <Layer name="Repository" path="app/repositories/" body="All SQL. Module-level async functions taking AsyncSession. Transactions in the caller." />
          <Layer name="DB" path="aiosqlite / Postgres" body="Today SQLite via aiosqlite. The repository contract is the swap point for Postgres." />
        </div>
      </Section>

      <Section eyebrow="The four invariants">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Each rule is one ripgrep. CI runs the four on every push.
        </p>
        <div className="space-y-4">
          {RULES.map((r, i) => (
            <div key={r.rule} className="border border-border bg-surface p-6 rounded-md">
              <div className="flex items-baseline gap-3 mb-3">
                <span className="text-ink-3 font-mono text-[11px]">#{i + 1}</span>
                <h3 className="text-ink-1 font-medium tracking-tight text-base">{r.rule}</h3>
              </div>
              <p className="text-ink-2 leading-relaxed mb-4 text-[15px]">{r.why}</p>
              <pre className="font-mono text-[12px] leading-relaxed text-ink-1 bg-bg border border-border rounded p-3 overflow-x-auto">
                {r.grep}
              </pre>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Domain errors">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Services and repositories never raise <code className="font-mono text-[13px] text-ink-1">HTTPException</code>.
          They raise subclasses of <code className="font-mono text-[13px] text-ink-1">DomainError</code>{' '}
          from <code className="font-mono text-[13px] text-ink-1">app/errors.py</code>; the API layer
          maps them to HTTP via handlers in <code className="font-mono text-[13px] text-ink-1">app/main.py</code>.
        </p>
        <CodeBlock
          lang="python"
          code={`# app/errors.py
class DomainError(Exception): ...
class IngestError(DomainError): ...
class EmptyQueryError(DomainError): ...
class PassageNotFoundError(DomainError): ...
class DocumentNotFoundError(DomainError): ...

# app/main.py
@app.exception_handler(IngestError)
async def _ingest(...): return JSONResponse(400, ...)

@app.exception_handler(EmptyQueryError)
async def _empty(...): return JSONResponse(400, ...)

@app.exception_handler(DomainError)              # fallback
async def _domain(...): return JSONResponse(500, ...)`}
        />
      </Section>

      <Section eyebrow="Configuration">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          A single Pydantic <code className="font-mono text-[13px] text-ink-1">BaseSettings</code> class
          owns every environment-driven knob. Load order is the Pydantic default: process
          environment → <code className="font-mono text-[13px] text-ink-1">.env</code> → field
          defaults.
        </p>
        <SpecList>
          <SpecItem term={<code className="font-mono text-[13px] text-ink-1">SQLITE_PATH</code>}>SQLite database file. Default <code className="font-mono text-[13px] text-ink-1">data/conviction_assistant.sqlite</code>.</SpecItem>
          <SpecItem term={<code className="font-mono text-[13px] text-ink-1">CONVICTIONS_DIR</code>}>Source directory for ingest. Default <code className="font-mono text-[13px] text-ink-1">convictions</code>.</SpecItem>
          <SpecItem term={<code className="font-mono text-[13px] text-ink-1">LLM_PROVIDER</code>}>Adapter to load. <code className="font-mono text-[13px] text-ink-1">openai</code> | <code className="font-mono text-[13px] text-ink-1">anthropic</code>. Default <code className="font-mono text-[13px] text-ink-1">openai</code>.</SpecItem>
          <SpecItem term={<code className="font-mono text-[13px] text-ink-1">OPENAI_API_KEY</code>}>Required when <code className="font-mono text-[13px] text-ink-1">LLM_PROVIDER=openai</code>. Factory raises at startup if missing.</SpecItem>
          <SpecItem term={<code className="font-mono text-[13px] text-ink-1">OPENAI_MODEL</code>}>Default <code className="font-mono text-[13px] text-ink-1">gpt-5</code>.</SpecItem>
          <SpecItem term={<code className="font-mono text-[13px] text-ink-1">OPENAI_EMBEDDING_MODEL</code>}>Default <code className="font-mono text-[13px] text-ink-1">text-embedding-3-large</code>. Used at the hybrid-retrieval level-up only.</SpecItem>
          <SpecItem term={<code className="font-mono text-[13px] text-ink-1">OPENAI_TIMEOUT_SECONDS</code>}>Per-request bound. Default 60.0.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Lifecycle">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          The FastAPI lifespan in <code className="font-mono text-[13px] text-ink-1">app/main.py::lifespan</code>{' '}
          owns DB setup and the search index. The pattern is:
        </p>
        <CodeBlock
          lang="python"
          code={`# app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.migrate(settings.sqlite_path)                     # Alembic upgrade head; idempotent
    engine = db.make_engine(settings.async_database_url)
    factory = db.make_session_factory(engine)            # async_sessionmaker(expire_on_commit=False)
    db.set_session_factory(factory)                      # module-level global for Depends
    index = BM25Index()
    async with factory() as session:
        await index.build(session)
    app.state.search_index = index
    try:
        yield
    finally:
        db.set_session_factory(None)
        await engine.dispose()

# Routers consume an AsyncSession via Depends(get_session).
# get_session yields from the global factory. Per-request session,
# committed or rolled-back by the service layer wrapped in
# 'async with session.begin(): ...'.`}
        />
      </Section>

      <Section eyebrow="Violation example">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          A common drift the rules catch: the agent loop wants to "just check if a passage
          exists" and reaches into the repository directly.
        </p>
        <CodeBlock
          lang="python"
          code={`# ✗ Wrong — the loop now imports the storage layer
async def agent_loop(session, ...):
    if await passages_repo.exists(session, passage_id):
        ...

# ✓ Right — the tool is the seam
async def agent_loop(ctx: ToolContext, ...):
    try:
        passage = await read_passage(ctx, passage_id=passage_id)
    except PassageNotFoundError:
        ...`}
        />
      </Section>
    </article>
  )
}

function Layer({ name, path, body }: { name: string; path: string; body: string }) {
  return (
    <div className="bg-bg p-5">
      <div className="text-ink-1 font-medium tracking-tight text-base mb-1">{name}</div>
      <code className="font-mono text-[11px] text-ink-3 block mb-3">{path}</code>
      <p className="text-ink-2 text-[13px] leading-relaxed">{body}</p>
    </div>
  )
}

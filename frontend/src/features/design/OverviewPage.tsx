import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { PageHeader, Section } from '@/components/Section'

export default function OverviewPage() {
  return (
    <article>
      <PageHeader
        eyebrow="Overview"
        title="Architecture."
        lead={
          <>
            An agentic assistant grounded on Decade's conviction corpus. A bounded agent uses
            four read-only tools to explore 30 markdown documents and produce a structured
            JSON answer, with every citation anchored to a span of its source passage. The
            agent, tools and resolver are provider-agnostic; SQLite and BM25 sit behind the
            repository, and the LLM lives behind a single adapter at{' '}
            <code className="font-mono text-[15px] text-ink-1">app/providers/</code>.
          </>
        }
      />

      <Section eyebrow="Problem">
        <div className="max-w-prose space-y-4 text-ink-2 text-[15px] leading-relaxed">
          <p>
            Investment analysts at Decade have a body of conviction documents written by their
            research team. They need a conversational interface that answers questions strictly
            from those documents and shows its work — exact quotes, exact passage IDs, dated
            sources — without paraphrasing the firm's positions or fabricating new ones.
          </p>
          <p>
            The system is constrained on two axes: it must ground every claim in a cited
            passage, and it must remain portable across LLM providers (OpenAI today, Anthropic
            for the portability proof, others later).
          </p>
        </div>
      </Section>

      <Section eyebrow="Before any question — ingest & indexing">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The corpus is parsed once and the BM25 index is built in memory at app startup, so
          by the time a question arrives the system already has every passage indexed and
          ready to search. Re-running ingest is a single admin POST.
        </p>
        <BootDiagram />
      </Section>

      <Section eyebrow="Architecture diagram">
        <dl className="max-w-prose grid grid-cols-[8.5rem_1fr] gap-x-6 gap-y-3 text-[15px] leading-relaxed mb-8">
          <dt className="text-ink-1 font-medium">Router</dt>
          <dd className="text-ink-2">HTTP entry. Parses the request, hands off to the agent loop, formats the response.</dd>
          <dt className="text-ink-1 font-medium">Agent loop</dt>
          <dd className="text-ink-2">The orchestrator. Decides between calling another tool and producing the final structured answer; enforces the loop bounds.</dd>
          <dt className="text-ink-1 font-medium">Tools</dt>
          <dd className="text-ink-2">Four read-only functions over the corpus. The agent chooses which to call and in what order; the loop never gives it write access.</dd>
          <dt className="text-ink-1 font-medium">LLMProvider</dt>
          <dd className="text-ink-2">The single adapter for any LLM. Everything above it is provider-agnostic; swapping OpenAI for another provider is a config change.</dd>
          <dt className="text-ink-1 font-medium">Offset resolver</dt>
          <dd className="text-ink-2">Turns each cited quote into a <code className="font-mono text-[13px] text-ink-1">(start, end)</code> region of its source passage so the UI can highlight exactly what the model used.</dd>
          <dt className="text-ink-1 font-medium">Repository</dt>
          <dd className="text-ink-2">The only layer that talks to the database. Tools and services go through it; raw SQL lives nowhere else.</dd>
          <dt className="text-ink-1 font-medium">audit_log</dt>
          <dd className="text-ink-2">Every step (LLM call, tool call, resolver) is recorded with step / question / conversation IDs and a per-step cost.</dd>
        </dl>
        <ArchitectureDiagram />
      </Section>

      <Section eyebrow="The four tools">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The agent's entire view of the corpus is these four functions. They are pure,
          read-only, and pass their results back through{' '}
          <code className="font-mono text-[13px] text-ink-1">ToolContext</code> — no global
          state, no side effects.
        </p>
        <div className="max-w-prose border border-border rounded-md divide-y divide-border">
          {TOOLS.map(t => (
            <div key={t.name} className="px-5 py-4 grid grid-cols-1 md:grid-cols-[14rem_1fr] md:items-baseline gap-x-6 gap-y-1">
              <code className="font-mono text-[13px] text-ink-1">{t.name}({t.args})</code>
              <p className="text-ink-2 text-[14px] leading-relaxed">{t.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Request lifecycle">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          A single <code className="font-mono text-[13px] text-ink-1">POST /chat</code>{' '}
          executes one bounded agent loop and returns a structured JSON response. The sequence
          below names the file path that owns each step.
        </p>
        <LifecycleDiagram />
      </Section>

      <Section eyebrow="Reading guide">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The pages are ordered along the data path. Each documents one layer: the problem it
          solves, the constraints it operates under, the approach with file references, the
          contract it exposes, the failure modes, and the alternatives that were rejected.
        </p>
        <ul className="divide-y divide-border border border-border rounded-md">
          {TOUR.map(t => (
            <li key={t.to}>
              <Link to={t.to} className="flex items-baseline justify-between gap-4 px-5 py-4 hover:bg-surface-2 transition-colors group">
                <div className="min-w-0">
                  <code className="font-mono text-[11px] text-ink-3">{t.to}</code>
                  <div className="text-ink-1 font-medium tracking-tight mt-0.5">{t.label}</div>
                  <div className="text-ink-3 text-sm mt-0.5 leading-relaxed">{t.desc}</div>
                </div>
                <ArrowRight size={14} className="text-ink-3 group-hover:text-ink-1 shrink-0 transition-colors" />
              </Link>
            </li>
          ))}
        </ul>
      </Section>
    </article>
  )
}

const TOOLS = [
  {
    name: 'list_documents',
    args: '',
    desc: "Enumerate all documents in the corpus. Returns titles, IDs and the Updated: date for each.",
  },
  {
    name: 'read_document_outline',
    args: 'document_id',
    desc: "One document's heading tree plus its metadata. No body text — used to plan which passages to read.",
  },
  {
    name: 'search_convictions',
    args: 'query, k',
    desc: 'BM25 search across all passages. Returns ranked hits with snippets, scores and source metadata.',
  },
  {
    name: 'read_passage',
    args: 'passage_ids',
    desc: 'Full text of one or more passages by id, returned in the order requested.',
  },
] as const

const TOUR = [
  { to: '/design/pipeline/corpus', label: 'Corpus & chunking', desc: 'Markdown → Passage[]. Slug algorithm, date extraction, stable IDs.' },
  { to: '/design/pipeline/tools', label: 'Tools', desc: 'Four read-only tools, hand-written JSON schemas, ToolContext DI.' },
  { to: '/design/pipeline/retrieval', label: 'Retrieval (BM25)', desc: 'BM25Index over normalized tokens. Cross-language is the level-up trigger.' },
  { to: '/design/pipeline/agent-loop', label: 'Agent loop', desc: 'Bounded gather → act → answer with strict loop invariants.' },
  { to: '/design/plumbing/providers', label: 'Provider abstraction', desc: 'LLMProvider protocol, OpenAI + Stub adapters behind a single interface.' },
  { to: '/design/plumbing/cost', label: 'Cost tracking', desc: 'TokenUsage → vendored prices. Three-granularity audit_log.' },
  { to: '/design/plumbing/layering', label: 'Layering rules', desc: 'Router → Service → Repository. Domain errors. Configuration. Lifecycle.' },
  { to: '/design/framing/tiers', label: 'Production-grade vs simplified', desc: 'What is built right vs deliberately simplified, with documented level-ups.' },
] as const

function BootDiagram() {
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-8 overflow-x-auto">
      <svg viewBox="0 0 1040 120" className="w-full max-w-[1040px] mx-auto" role="img" aria-label="Boot-time ingest and indexing">
        <defs>
          <marker id="arrow-boot" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        {/* Markdown */}
        <g>
          <rect x="20" y="25" width="150" height="70" fill="#0A0A0A" stroke="#262626" />
          <text x="95" y="55" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Markdown corpus</text>
          <text x="95" y="73" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">convictions/*.md</text>
        </g>
        <line x1="170" y1="60" x2="220" y2="60" stroke="#B5B5B5" markerEnd="url(#arrow-boot)" />
        <text x="195" y="50" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">POST /admin/ingest</text>

        {/* Ingest + Parser */}
        <g>
          <rect x="220" y="25" width="180" height="70" fill="#0A0A0A" stroke="#262626" />
          <text x="310" y="50" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Ingest + Parser</text>
          <text x="310" y="68" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">split on ## headings</text>
          <text x="310" y="84" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">services/parser/</text>
        </g>
        <line x1="400" y1="60" x2="450" y2="60" stroke="#B5B5B5" markerEnd="url(#arrow-boot)" />
        <text x="425" y="50" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">write</text>

        {/* SQLite */}
        <g>
          <rect x="450" y="25" width="200" height="70" fill="#0A0A0A" stroke="#262626" />
          <text x="550" y="50" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">SQLite — passages</text>
          <text x="550" y="68" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">id, doc, heading_path, text</text>
          <text x="550" y="84" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">~30 docs · ~hundreds of passages</text>
        </g>
        <line x1="650" y1="60" x2="700" y2="60" stroke="#B5B5B5" markerEnd="url(#arrow-boot)" />
        <text x="675" y="50" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">on startup</text>

        {/* BM25 index */}
        <g>
          <rect x="700" y="25" width="220" height="70" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="810" y="50" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">BM25 index (in-memory)</text>
          <text x="810" y="68" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">accent-fold · lowercase · tokenize</text>
          <text x="810" y="84" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/retrieval/bm25.py</text>
        </g>
      </svg>
    </div>
  )
}

function ArchitectureDiagram() {
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-10 overflow-x-auto">
      <svg viewBox="0 0 1040 420" className="w-full max-w-[1040px] mx-auto" role="img" aria-label="Architecture diagram">
        <defs>
          <marker id="arrow-arch" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        {/* User */}
        <g>
          <rect x="20" y="170" width="100" height="60" fill="#0A0A0A" stroke="#262626" />
          <text x="70" y="200" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontFamily="Inter">User</text>
          <text x="70" y="218" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">PT/EN/ES</text>
        </g>

        <line x1="120" y1="200" x2="160" y2="200" stroke="#B5B5B5" strokeWidth="1" markerEnd="url(#arrow-arch)" />
        <text x="140" y="190" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">POST</text>

        {/* Router */}
        <g>
          <rect x="160" y="170" width="120" height="60" fill="#0A0A0A" stroke="#262626" />
          <text x="220" y="196" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontFamily="Inter">Router</text>
          <text x="220" y="214" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">api/chat.py</text>
        </g>

        <line x1="280" y1="200" x2="320" y2="200" stroke="#B5B5B5" strokeWidth="1" markerEnd="url(#arrow-arch)" />

        {/* Agent loop */}
        <g>
          <rect x="320" y="80" width="180" height="260" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="410" y="104" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontWeight="600" fontFamily="Inter">Agent loop</text>
          <text x="410" y="122" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/agent/loop.py</text>
          <line x1="340" y1="138" x2="480" y2="138" stroke="#262626" />
          <text x="410" y="162" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">Gather → Act → Answer</text>
          <text x="410" y="190" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">≤ 5 tool calls</text>
          <text x="410" y="208" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">≥ 1 search before answer</text>
          <text x="410" y="226" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">strict JSON output</text>
          <text x="410" y="244" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">no prior assistant text</text>
        </g>

        {/* Agent ↔ Tools (parallel arrows) */}
        <line x1="500" y1="105" x2="560" y2="105" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <line x1="560" y1="125" x2="500" y2="125" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        {/* Tools */}
        <g>
          <rect x="560" y="80" width="260" height="90" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="690" y="104" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Tools (read-only)</text>
          <text x="690" y="126" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">list_documents · read_document_outline</text>
          <text x="690" y="142" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">search_convictions · read_passage</text>
          <text x="690" y="160" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/agent/tools/</text>
        </g>

        {/* Agent ↔ LLMProvider */}
        <line x1="500" y1="210" x2="560" y2="210" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <line x1="560" y1="230" x2="500" y2="230" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        {/* LLMProvider */}
        <g>
          <rect x="560" y="190" width="260" height="70" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="690" y="214" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">LLMProvider</text>
          <text x="690" y="234" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">providers/openai.py</text>
          <text x="690" y="250" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">providers/stub.py</text>
        </g>

        {/* Agent → Resolver */}
        <line x1="500" y1="305" x2="560" y2="305" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        {/* Resolver */}
        <g>
          <rect x="560" y="280" width="260" height="60" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="690" y="304" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Offset resolver</text>
          <text x="690" y="324" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/agent/resolver/</text>
        </g>

        {/* Tools → Repository (clean horizontal) */}
        <line x1="820" y1="125" x2="860" y2="125" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        {/* Repository */}
        <g>
          <rect x="860" y="90" width="160" height="70" fill="#0A0A0A" stroke="#262626" />
          <text x="940" y="118" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Repository</text>
          <text x="940" y="138" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">repositories/passages.py</text>
        </g>

        {/* Repository → SQLite */}
        <line x1="940" y1="160" x2="940" y2="190" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        {/* SQLite */}
        <g>
          <rect x="860" y="190" width="160" height="60" fill="#0A0A0A" stroke="#262626" />
          <text x="940" y="218" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">SQLite</text>
          <text x="940" y="236" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">aiosqlite</text>
        </g>

        {/* Agent → audit_log */}
        <line x1="410" y1="340" x2="410" y2="370" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <g>
          <rect x="320" y="370" width="180" height="36" fill="#0A0A0A" stroke="#262626" />
          <text x="410" y="393" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">audit_log + cost</text>
        </g>
      </svg>
    </div>
  )
}

function LifecycleDiagram() {
  // Sequence diagram. Lanes: Router · Agent · Tools · LLMProvider · Verifier · Audit
  const lanes = [
    { x: 90, label: 'Router', file: 'api/chat.py · B9' },
    { x: 240, label: 'Agent', file: 'services/agent.py · B8' },
    { x: 390, label: 'Tools', file: 'tools/' },
    { x: 540, label: 'LLM', file: 'providers/' },
    { x: 690, label: 'Resolver', file: 'app/agent/resolver/' },
    { x: 840, label: 'Audit', file: 'repositories/audit.py' },
  ]
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-8 overflow-x-auto">
      <svg viewBox="0 0 920 500" className="w-full max-w-[920px] mx-auto" role="img" aria-label="Request lifecycle sequence">
        <defs>
          <marker id="arrow-life" markerWidth="8" markerHeight="8" refX="8" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#FFFFFF" />
          </marker>
        </defs>

        {/* Lane headers */}
        {lanes.map(l => (
          <g key={l.label}>
            <rect x={l.x - 60} y="0" width="120" height="48" fill="#0A0A0A" stroke="#262626" />
            <text x={l.x} y="22" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">{l.label}</text>
            <text x={l.x} y="38" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">{l.file}</text>
            <line x1={l.x} y1="48" x2={l.x} y2="480" stroke="#262626" strokeDasharray="2 3" />
          </g>
        ))}

        {/* Steps */}
        {[
          { y: 80, from: 0, to: 1, label: 'invoke loop with question' },
          { y: 120, from: 1, to: 2, label: 'search_convictions(query, k=5)' },
          { y: 145, from: 2, to: 1, label: 'list[PassageHit]', back: true },
          { y: 180, from: 1, to: 2, label: 'read_passage(passage_ids)' },
          { y: 205, from: 2, to: 1, label: 'list[Passage]', back: true },
          { y: 245, from: 1, to: 3, label: 'generate(messages, schema=AnswerSchema)' },
          { y: 270, from: 3, to: 1, label: 'LLMResponse(parsed=Answer, usage)', back: true },
          { y: 310, from: 1, to: 4, label: 'resolve(citations, passages)' },
          { y: 335, from: 4, to: 1, label: 'Resolution(passage_id, start, end)', back: true },
          { y: 375, from: 1, to: 5, label: 'append step rows · llm_call · tool_call · resolver' },
          { y: 415, from: 1, to: 0, label: 'ChatAnswerResponse with citations + disclaimer + usage', back: true },
          { y: 455, from: 0, to: -1, label: 'response body', back: true },
        ].map((s, i) => {
          const fromX = s.from === -1 ? -20 : lanes[s.from].x
          const toX = s.to === -1 ? -20 : lanes[s.to].x
          return (
            <g key={i}>
              <line x1={fromX} y1={s.y} x2={toX} y2={s.y} stroke="#FFFFFF" strokeWidth="1" markerEnd="url(#arrow-life)" />
              <text x={(fromX + toX) / 2} y={s.y - 6} textAnchor="middle" fill="#B5B5B5" fontSize="10" fontFamily="JetBrains Mono">{s.label}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

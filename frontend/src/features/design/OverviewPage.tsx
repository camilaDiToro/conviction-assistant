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
      <svg viewBox="0 0 600 250" className="w-full max-w-[600px] mx-auto" role="img" aria-label="Boot-time ingest and indexing">
        <defs>
          <marker id="arrow-boot" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        {/* Top-left: Markdown corpus */}
        <g>
          <rect x="20" y="20" width="240" height="80" fill="#0A0A0A" stroke="#262626" />
          <text x="140" y="52" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Markdown corpus</text>
          <text x="140" y="72" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">convictions/*.md</text>
          <text x="140" y="88" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">~30 docs · PT/EN</text>
        </g>

        {/* Arrow top-left → top-right */}
        <line x1="260" y1="60" x2="340" y2="60" stroke="#B5B5B5" markerEnd="url(#arrow-boot)" />
        <text x="300" y="50" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">POST /admin/ingest</text>

        {/* Top-right: Ingest + Parser */}
        <g>
          <rect x="340" y="20" width="240" height="80" fill="#0A0A0A" stroke="#262626" />
          <text x="460" y="48" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Ingest + Parser</text>
          <text x="460" y="68" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">split on ## headings</text>
          <text x="460" y="84" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">services/parser/</text>
        </g>

        {/* Vertical arrow top-right → bottom-right */}
        <line x1="460" y1="100" x2="460" y2="150" stroke="#B5B5B5" markerEnd="url(#arrow-boot)" />
        <text x="478" y="129" textAnchor="start" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">write</text>

        {/* Bottom-right: SQLite */}
        <g>
          <rect x="340" y="150" width="240" height="80" fill="#0A0A0A" stroke="#262626" />
          <text x="460" y="178" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">SQLite — passages</text>
          <text x="460" y="198" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">id, doc, heading_path, text</text>
          <text x="460" y="214" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">~hundreds of passages</text>
        </g>

        {/* Arrow bottom-right → bottom-left */}
        <line x1="340" y1="190" x2="260" y2="190" stroke="#B5B5B5" markerEnd="url(#arrow-boot)" />
        <text x="300" y="180" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">on startup</text>

        {/* Bottom-left: BM25 index */}
        <g>
          <rect x="20" y="150" width="240" height="80" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="140" y="178" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">BM25 index (in-memory)</text>
          <text x="140" y="198" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">accent-fold · lowercase · tokenize</text>
          <text x="140" y="214" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/retrieval/bm25.py</text>
        </g>
      </svg>
    </div>
  )
}

function ArchitectureDiagram() {
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-10 overflow-x-auto">
      <svg viewBox="0 0 720 510" className="w-full max-w-[720px] mx-auto" role="img" aria-label="Architecture diagram">
        <defs>
          <marker id="arrow-arch" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        {/* Row 1: User → Router (centered over Agent loop) */}
        <g>
          <rect x="10" y="20" width="70" height="50" fill="#0A0A0A" stroke="#262626" />
          <text x="45" y="42" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontFamily="Inter">User</text>
          <text x="45" y="58" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">PT/EN/ES</text>
        </g>

        <line x1="80" y1="45" x2="120" y2="45" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        <g>
          <rect x="120" y="20" width="120" height="50" fill="#0A0A0A" stroke="#262626" />
          <text x="180" y="42" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontFamily="Inter">Router</text>
          <text x="180" y="58" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">api/chat.py</text>
        </g>

        {/* Router → Agent loop (vertical, centered on x=180) */}
        <line x1="180" y1="70" x2="180" y2="110" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <text x="195" y="92" textAnchor="start" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">POST</text>

        {/* Row 2: Agent loop + middle column */}
        <g>
          <rect x="20" y="110" width="320" height="290" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="180" y="136" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontWeight="600" fontFamily="Inter">Agent loop</text>
          <text x="180" y="154" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/agent/loop.py</text>
          <line x1="40" y1="170" x2="320" y2="170" stroke="#262626" />
          <text x="180" y="200" textAnchor="middle" fill="#B5B5B5" fontSize="12" fontFamily="Inter">Gather → Act → Answer</text>
          <text x="180" y="232" textAnchor="middle" fill="#6B6B6B" fontSize="11" fontFamily="Inter">≤ 5 tool calls</text>
          <text x="180" y="252" textAnchor="middle" fill="#6B6B6B" fontSize="11" fontFamily="Inter">≥ 1 search before answer</text>
          <text x="180" y="272" textAnchor="middle" fill="#6B6B6B" fontSize="11" fontFamily="Inter">strict JSON output</text>
          <text x="180" y="292" textAnchor="middle" fill="#6B6B6B" fontSize="11" fontFamily="Inter">no prior assistant text</text>
        </g>

        {/* Agent ↔ Tools */}
        <line x1="340" y1="138" x2="380" y2="138" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <line x1="380" y1="158" x2="340" y2="158" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        <g>
          <rect x="380" y="110" width="280" height="80" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="520" y="134" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Tools (read-only)</text>
          <text x="520" y="154" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">list_documents · read_document_outline</text>
          <text x="520" y="170" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">search_convictions · read_passage</text>
          <text x="520" y="184" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/agent/tools/</text>
        </g>

        {/* Agent ↔ LLMProvider */}
        <line x1="340" y1="228" x2="380" y2="228" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <line x1="380" y1="248" x2="340" y2="248" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        <g>
          <rect x="380" y="210" width="280" height="70" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="520" y="234" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">LLMProvider</text>
          <text x="520" y="254" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">providers/openai.py</text>
          <text x="520" y="270" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">providers/stub.py</text>
        </g>

        {/* Agent → Resolver */}
        <line x1="340" y1="330" x2="380" y2="330" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        <g>
          <rect x="380" y="300" width="280" height="70" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="520" y="324" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Offset resolver</text>
          <text x="520" y="344" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">anchors each citation to (start, end)</text>
          <text x="520" y="360" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">app/agent/resolver/</text>
        </g>

        {/* Agent → audit_log (vertical) */}
        <line x1="180" y1="400" x2="180" y2="430" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        {/* Row 3: audit_log + Repository → SQLite */}
        <g>
          <rect x="20" y="430" width="320" height="50" fill="#0A0A0A" stroke="#262626" />
          <text x="180" y="452" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">audit_log + cost</text>
          <text x="180" y="470" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">repositories/audit.py</text>
        </g>

        <g>
          <rect x="380" y="430" width="140" height="50" fill="#0A0A0A" stroke="#262626" />
          <text x="450" y="452" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Repository</text>
          <text x="450" y="470" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">repositories/passages.py</text>
        </g>

        <line x1="520" y1="455" x2="560" y2="455" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />

        <g>
          <rect x="560" y="430" width="100" height="50" fill="#0A0A0A" stroke="#262626" />
          <text x="610" y="452" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">SQLite</text>
          <text x="610" y="470" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">aiosqlite</text>
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
          { y: 415, from: 1, to: 0, label: 'ChatAnswerResponse (citations + disclaimer + usage)', back: true },
        ].map((s, i) => {
          const fromX = lanes[s.from].x
          const toX = lanes[s.to].x
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

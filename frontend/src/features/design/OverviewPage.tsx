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
            A FastAPI service over a corpus of 30 markdown investment-conviction documents.
            The agent uses four read-only tools to gather evidence and produces a structured
            JSON answer with citations; a deterministic substring verifier rejects any quote
            that does not round-trip through its claimed source. Provider-portable above{' '}
            <code className="font-mono text-[15px] text-ink-1">app/providers/</code>; SQLite +
            BM25 below it.
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

      <Section eyebrow="Constraints">
        <dl className="max-w-prose grid grid-cols-1 md:grid-cols-[12rem_1fr] gap-x-8 gap-y-2 text-[15px] leading-relaxed">
          <dt className="text-ink-1 font-medium pt-px">Correctness</dt>
          <dd className="text-ink-2">Every cited quote substring-matches its source passage after a pinned normalization pipeline. No model self-judges its own grounding.</dd>

          <dt className="text-ink-1 font-medium pt-px md:pt-3 border-t md:border-t border-border md:pl-0">Portability</dt>
          <dd className="text-ink-2 md:pt-3 md:border-t md:border-border">No provider SDKs are imported outside <code className="font-mono text-[13px] text-ink-1">app/providers/</code>. The orchestrator, tools, and verifier are provider-agnostic. Swapping providers is a config change, not a refactor.</dd>

          <dt className="text-ink-1 font-medium pt-3 border-t border-border">Reproducibility</dt>
          <dd className="text-ink-2 pt-3 border-t border-border">The verifier is deterministic. The stub provider (<code className="font-mono text-[13px] text-ink-1">app/providers/stub.py::StubLLM</code>) replays canned responses from YAML fixtures. Tests run without network or tokens.</dd>

          <dt className="text-ink-1 font-medium pt-3 border-t border-border">Inspectability</dt>
          <dd className="text-ink-2 pt-3 border-t border-border">Every step is recorded in <code className="font-mono text-[13px] text-ink-1">audit_log</code> with three IDs (step, question, conversation). Cost is derived from <code className="font-mono text-[13px] text-ink-1">TokenUsage</code> + a vendored price table; old rows re-price under new prices.</dd>

          <dt className="text-ink-1 font-medium pt-3 border-t border-border">Cost</dt>
          <dd className="text-ink-2 pt-3 border-t border-border">Prompt caching on the system prompt; <code className="font-mono text-[13px] text-ink-1">reasoning_effort=medium</code> on gpt-5 (override to <code className="font-mono text-[13px] text-ink-1">low</code> via <code className="font-mono text-[13px] text-ink-1">AGENT_REASONING_EFFORT</code> for cost-sensitive runs); no LLM calls in unit or integration tests.</dd>
        </dl>
      </Section>

      <Section eyebrow="Architecture">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Five layers, each owning a single responsibility. Heavy outline marks a contract that
          enforces an invariant. Dashed outline marks a node that is designed but not yet
          implemented (B7 verifier, B8 agent, B9 chat endpoint).
        </p>
        <ArchitectureDiagram />
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

const TOUR = [
  { to: '/design/pipeline/corpus', label: 'Corpus & chunking', desc: 'Markdown → Passage[]. Slug algorithm, date extraction, stable IDs.' },
  { to: '/design/pipeline/tools', label: 'Tools', desc: 'Four read-only tools, hand-written JSON schemas, ToolContext DI.' },
  { to: '/design/pipeline/retrieval', label: 'Retrieval (BM25)', desc: 'BM25Index over normalized tokens. Cross-language is the level-up trigger.' },
  { to: '/design/pipeline/verifier', label: 'Verifier', desc: 'Six-step normalization + substring check. Designed; ships in B7.' },
  { to: '/design/pipeline/agent-loop', label: 'Agent loop', desc: 'Gather → Act → Verify with bounded retries. Designed; ships in B8.' },
  { to: '/design/plumbing/providers', label: 'Provider abstraction', desc: 'LLMProvider protocol, OpenAI + Stub adapters, Anthropic at B10.' },
  { to: '/design/plumbing/cost', label: 'Cost tracking', desc: 'TokenUsage → vendored prices. Three-granularity audit_log.' },
  { to: '/design/plumbing/layering', label: 'Layering rules', desc: 'Router → Service → Repository. Domain errors. Configuration. Lifecycle.' },
  { to: '/design/framing/tiers', label: 'Production-grade vs simplified', desc: 'What is built right vs deliberately simplified, with documented level-ups.' },
] as const

function ArchitectureDiagram() {
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-10 overflow-x-auto">
      <svg viewBox="0 0 920 380" className="w-full max-w-[920px] mx-auto" role="img" aria-label="Architecture diagram">
        <defs>
          <marker id="arrow-arch" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        <g>
          <rect x="20" y="160" width="100" height="60" fill="#0A0A0A" stroke="#262626" />
          <text x="70" y="190" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontFamily="Inter">User</text>
          <text x="70" y="208" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">PT/EN/ES</text>
        </g>

        <line x1="120" y1="190" x2="160" y2="190" stroke="#B5B5B5" strokeWidth="1" markerEnd="url(#arrow-arch)" />
        <text x="140" y="180" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">POST</text>

        <g>
          <rect x="160" y="160" width="120" height="60" fill="#0A0A0A" stroke="#262626" />
          <text x="220" y="186" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontFamily="Inter">Router</text>
          <text x="220" y="204" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">api/chat.py</text>
        </g>

        <line x1="280" y1="190" x2="320" y2="190" stroke="#B5B5B5" strokeWidth="1" markerEnd="url(#arrow-arch)" />

        <g>
          <rect x="320" y="100" width="160" height="180" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" strokeDasharray="3 2" />
          <text x="400" y="124" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontWeight="600" fontFamily="Inter">Agent loop</text>
          <text x="400" y="142" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">services/agent.py · B8</text>
          <line x1="340" y1="156" x2="460" y2="156" stroke="#262626" />
          <text x="400" y="178" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">Gather → Act → Verify</text>
          <text x="400" y="200" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">≤ 5 tool calls</text>
          <text x="400" y="216" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">≥ 1 search before answer</text>
          <text x="400" y="232" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">retry budget = 1</text>
          <text x="400" y="252" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">strict JSON output</text>
        </g>

        <line x1="480" y1="135" x2="540" y2="115" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <line x1="540" y1="115" x2="480" y2="135" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <g>
          <rect x="540" y="80" width="180" height="80" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="630" y="104" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Tools (read-only)</text>
          <text x="630" y="122" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">tools/list_documents.py</text>
          <text x="630" y="135" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">tools/read_document_outline.py</text>
          <text x="630" y="148" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">tools/search_convictions.py · read_passage.py</text>
        </g>

        <line x1="480" y1="190" x2="540" y2="190" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <line x1="540" y1="190" x2="480" y2="190" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <g>
          <rect x="540" y="170" width="180" height="80" fill="#0A0A0A" stroke="#FFFFFF" />
          <text x="630" y="194" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">LLMProvider</text>
          <text x="630" y="210" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">providers/openai.py</text>
          <text x="630" y="223" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">providers/stub.py</text>
          <text x="630" y="236" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">providers/anthropic.py · B10</text>
        </g>

        <line x1="480" y1="245" x2="540" y2="265" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <g>
          <rect x="540" y="260" width="180" height="60" fill="#0A0A0A" stroke="#FFFFFF" strokeDasharray="3 2" />
          <text x="630" y="284" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Verifier</text>
          <text x="630" y="302" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">verifier/substring.py · B7</text>
        </g>

        <line x1="630" y1="160" x2="820" y2="60" stroke="#B5B5B5" strokeDasharray="2 3" markerEnd="url(#arrow-arch)" />
        <g>
          <rect x="780" y="40" width="120" height="60" fill="#0A0A0A" stroke="#262626" />
          <text x="840" y="66" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">Repository</text>
          <text x="840" y="84" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">repositories/passages.py</text>
        </g>
        <line x1="840" y1="100" x2="840" y2="140" stroke="#B5B5B5" markerEnd="url(#arrow-arch)" />
        <g>
          <rect x="780" y="140" width="120" height="60" fill="#0A0A0A" stroke="#262626" />
          <text x="840" y="166" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">SQLite</text>
          <text x="840" y="184" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="JetBrains Mono">aiosqlite</text>
        </g>

        <line x1="400" y1="280" x2="400" y2="330" stroke="#B5B5B5" strokeDasharray="2 3" markerEnd="url(#arrow-arch)" />
        <g>
          <rect x="320" y="328" width="160" height="40" fill="#0A0A0A" stroke="#262626" />
          <text x="400" y="354" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">audit_log + cost</text>
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
    { x: 690, label: 'Verifier', file: 'verifier/ · B7' },
    { x: 840, label: 'Audit', file: 'repositories/audit.py · B9' },
  ]
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-8 overflow-x-auto">
      <svg viewBox="0 0 920 540" className="w-full max-w-[920px] mx-auto" role="img" aria-label="Request lifecycle sequence">
        <defs>
          <marker id="arrow-life" markerWidth="8" markerHeight="8" refX="8" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#FFFFFF" />
          </marker>
          <marker id="arrow-life-d" markerWidth="8" markerHeight="8" refX="8" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        {/* Lane headers */}
        {lanes.map(l => (
          <g key={l.label}>
            <rect x={l.x - 60} y="0" width="120" height="48" fill="#0A0A0A" stroke="#262626" />
            <text x={l.x} y="22" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontFamily="Inter">{l.label}</text>
            <text x={l.x} y="38" textAnchor="middle" fill="#6B6B6B" fontSize="9" fontFamily="JetBrains Mono">{l.file}</text>
            <line x1={l.x} y1="48" x2={l.x} y2="510" stroke="#262626" strokeDasharray="2 3" />
          </g>
        ))}

        {/* Steps */}
        {[
          { y: 80, from: 0, to: 1, label: 'invoke loop with question' },
          { y: 120, from: 1, to: 2, label: 'search_convictions(query, k=5)' },
          { y: 145, y2: 145, from: 2, to: 1, label: 'list[PassageHit]', back: true },
          { y: 180, from: 1, to: 2, label: 'read_passage(passage_ids)' },
          { y: 205, from: 2, to: 1, label: 'list[Passage]', back: true },
          { y: 245, from: 1, to: 3, label: 'generate(messages, schema=AnswerSchema)' },
          { y: 270, from: 3, to: 1, label: 'LLMResponse(parsed=Answer, usage)', back: true },
          { y: 310, from: 1, to: 4, label: 'verify(quote, passage_text) for each citation', dashed: true },
          { y: 335, from: 4, to: 1, label: 'VerifyResult(passed=true)', back: true, dashed: true },
          { y: 375, from: 1, to: 5, label: 'append step rows · llm_call · tool_call · verifier', dashed: true },
          { y: 415, from: 1, to: 0, label: 'ChatAnswerResponse with citations + disclaimer + usage', back: true },
          { y: 455, from: 0, to: -1, label: 'response body', back: true },
        ].map((s, i) => {
          const fromX = s.from === -1 ? -20 : lanes[s.from].x
          const toX = s.to === -1 ? -20 : lanes[s.to].x
          const stroke = s.dashed ? '#B5B5B5' : '#FFFFFF'
          const dasharray = s.dashed ? '4 3' : undefined
          const marker = s.dashed ? 'url(#arrow-life-d)' : 'url(#arrow-life)'
          return (
            <g key={i}>
              <line x1={fromX} y1={s.y} x2={toX} y2={s.y} stroke={stroke} strokeWidth="1" strokeDasharray={dasharray} markerEnd={marker} />
              <text x={(fromX + toX) / 2} y={s.y - 6} textAnchor="middle" fill="#B5B5B5" fontSize="10" fontFamily="JetBrains Mono">{s.label}</text>
            </g>
          )
        })}

        <text x="460" y="500" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">
          dashed = designed; not yet built. Solid = wired today.
        </text>
      </svg>
    </div>
  )
}

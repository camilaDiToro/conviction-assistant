import { PageHeader, Section } from '@/components/Section'

const ROWS = [
  {
    label: 'Citation grounding',
    built: 'Deterministic substring verifier with pinned normalization. Retry-once-with-feedback.',
    simplified: '—',
    levelUp: null,
  },
  {
    label: 'Provider abstraction',
    built: 'LLMProvider protocol with OpenAI + Stub adapters. Anthropic adapter documented as future work. Single LLM point.',
    simplified: '—',
    levelUp: null,
  },
  {
    label: 'Agent loop bounds',
    built: 'Max 5 tool calls, ≥ 1 search before answer, retry-once-with-feedback, strip-or-refuse.',
    simplified: '—',
    levelUp: null,
  },
  {
    label: 'Tool surface',
    built: 'Four read-only tools, hand-written JSON schemas, ToolContext DI, pure-function tests.',
    simplified: '—',
    levelUp: null,
  },
  {
    label: 'Token usage',
    built: 'Per-step TokenUsage plus per-question token totals in the response summary.',
    simplified: 'Raw counters only; no enforcement gate.',
    levelUp: null,
  },
  {
    label: 'Layering',
    built: 'Router → Service → Repository, four CI-greppable invariants, domain errors mapped at the boundary.',
    simplified: '—',
    levelUp: null,
  },
  {
    label: 'Storage',
    built: '—',
    simplified: 'SQLite + SQLAlchemy async + aiosqlite. One process, one file.',
    levelUp: { text: 'Postgres + pgvector. The repository contract is the swap point; tools and services are unaffected.' },
  },
  {
    label: 'Retrieval',
    built: '—',
    simplified: 'BM25 only with NFKD-stripped tokens. 30-document corpus, single-language baseline.',
    levelUp: { text: 'Hybrid (BM25 + multilingual embeddings + RRF), gated on cross-language eval failure.' },
  },
  {
    label: 'Auth & rate limiting',
    built: '—',
    simplified: 'No auth, no rate limit, no per-user quotas. Demo gate on the chat surface only.',
    levelUp: { text: 'Real auth (OIDC) and per-user / per-conversation request quotas when productized.' },
  },
  {
    label: 'Streaming',
    built: '—',
    simplified: 'Single sync POST /chat. Whole response or nothing.',
    levelUp: { text: 'SSE streaming for the answer body once UX latency outweighs simplicity.' },
  },
  {
    label: 'Testing',
    built: 'Unit (parser, search, tools — pure functions) + integration (FastAPI test client + tmp SQLite) + provider-adapter tests against StubLLM. No LLM in the request path of CI.',
    simplified: '—',
    levelUp: null,
  },
  {
    label: 'Evaluation',
    built: '—',
    simplified: '~30 hand-written Q/A planned. Verifier-pass-rate is the headline metric; LLM-judge entailment is secondary. Today the methodology is described; not measured.',
    levelUp: { text: 'Auto-generated eval bank, LLM-judge dashboard, weekly regressions. Cross-language eval is the trigger that gates the hybrid-retrieval promotion.' },
  },
  {
    label: 'Deployment',
    built: '—',
    simplified: 'Single FastAPI process, file-based settings, manual deploy.',
    levelUp: { text: 'Container + secrets manager + multi-replica + observability stack when productized.' },
  },
] as const

export default function TiersPage() {
  return (
    <article>
      <PageHeader
        eyebrow="Framing · Tiers"
        title="Production-grade vs deliberately simplified."
        lead={
          <>
            Two tiers ship in this project, on purpose. The reviewer should be able to tell at a
            glance which tier any file belongs to. Each simplified row names where its level-up
            lands, in the same module.
          </>
        }
      />

      <Section eyebrow="Comparison">
        <div className="border border-border rounded-md overflow-hidden bg-surface mt-2">
          <div className="grid grid-cols-[1fr_2fr_2fr] bg-surface-2 border-b border-border text-ink-3 text-[11px] uppercase tracking-tight">
            <div className="px-5 py-3">Concern</div>
            <div className="px-5 py-3 border-l border-border">Production-grade</div>
            <div className="px-5 py-3 border-l border-border">Deliberately simplified</div>
          </div>
          {ROWS.map((r, i) => (
            <div key={r.label} className={`grid grid-cols-[1fr_2fr_2fr] ${i ? 'border-t border-border' : ''}`}>
              <div className="px-5 py-4 text-ink-1 font-medium text-sm tracking-tight">{r.label}</div>
              <div className="px-5 py-4 border-l border-border text-ink-2 text-[14px] leading-relaxed">
                {r.built === '—' ? <span className="text-ink-4">—</span> : r.built}
              </div>
              <div className="px-5 py-4 border-l border-border text-ink-2 text-[14px] leading-relaxed">
                {r.simplified === '—' ? <span className="text-ink-4">—</span> : (
                  <>
                    {r.simplified}
                    {r.levelUp && (
                      <div className="mt-2 flex items-baseline gap-2 text-ink-3 text-xs">
                        <span className="font-mono text-ink-1">Level-up</span>
                        <span>· {r.levelUp.text}</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Promotion criterion">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Promotion from a simplified tier to its production-grade counterpart is a
          conversation, not a unilateral implementation decision. The trigger is one of two:
          a measurable failure in the evaluation suite that the simplified path cannot
          recover, or a stakeholder request grounded in a concrete operational concern (load,
          compliance, observability). Implementer enthusiasm is not a trigger.
        </p>
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mt-4">
          Each simplified entry above lands in the same file as its production-grade
          counterpart would: <code className="font-mono text-[13px] text-ink-1">app/repositories/</code>{' '}
          for storage, <code className="font-mono text-[13px] text-ink-1">app/services/search.py</code>{' '}
          for retrieval, <code className="font-mono text-[13px] text-ink-1">app/api/chat.py</code>{' '}
          for streaming. Promotion is a content change in a known place, not a re-architecture.
        </p>
      </Section>
    </article>
  )
}

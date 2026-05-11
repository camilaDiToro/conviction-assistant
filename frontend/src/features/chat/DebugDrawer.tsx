import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight, Loader2, X } from 'lucide-react'
import type { ChatMessage, DebugStep } from '@/lib/types'

interface DebugDrawerProps {
  message: Extract<ChatMessage, { role: 'assistant' }>
  onClose: () => void
  loading?: boolean
  loadError?: string | null
}

export function DebugDrawer({ message, onClose, loading = false, loadError = null }: DebugDrawerProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const r = message.response

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-bg/80 backdrop-blur-sm" onClick={onClose} />
      <aside className="w-full max-w-xl bg-bg border-l border-border overflow-y-auto animate-fade-in">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between sticky top-0 bg-bg">
          <div>
            <div className="text-ink-3 text-[10px] uppercase tracking-tight">Debug</div>
            <h3 className="text-ink-1 font-medium">Per-step breakdown</h3>
          </div>
          <button onClick={onClose} aria-label="Close debug" className="text-ink-3 hover:text-ink-1 p-1">
            <X size={18} />
          </button>
        </div>

        <div className="p-6 space-y-8">
          <section>
            <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Summary</h4>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border border border-border">
              <div className="bg-bg p-4">
                <dt className="text-ink-3 text-[10px] uppercase tracking-tight">Question</dt>
                <dd className="text-ink-1 font-mono mt-1">${r.usage_summary.question_total_cost_usd.toFixed(5)}</dd>
              </div>
              <div className="bg-bg p-4">
                <dt className="text-ink-3 text-[10px] uppercase tracking-tight">Conversation</dt>
                <dd className="text-ink-1 font-mono mt-1">${r.usage_summary.conversation_total_cost_usd.toFixed(5)}</dd>
              </div>
              <div className="bg-bg p-4">
                <dt className="text-ink-3 text-[10px] uppercase tracking-tight">Steps</dt>
                <dd className="text-ink-1 font-mono mt-1">{r.usage_summary.step_count}</dd>
              </div>
              <div className="bg-bg p-4">
                <dt className="text-ink-3 text-[10px] uppercase tracking-tight">Time</dt>
                <dd className="text-ink-1 font-mono mt-1">{formatDuration(r.usage_summary.duration_ms)}</dd>
              </div>
            </dl>
          </section>

          <section>
            <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Step timeline</h4>
            {loading && r.debug.steps.length === 0 && (
              <div className="flex items-center gap-2 text-ink-3 text-xs px-1 py-2">
                <Loader2 size={12} className="animate-spin" /> Loading steps from audit log…
              </div>
            )}
            {loadError && (
              <div className="text-ink-2 text-xs border border-border bg-surface rounded-md p-3 mb-3">
                <strong className="text-ink-1 font-medium block mb-1">Failed to load steps.</strong>
                {loadError}
              </div>
            )}
            {!loading && !loadError && r.debug.steps.length === 0 && (
              <div className="text-ink-3 text-xs px-1 py-2">No steps recorded for this message.</div>
            )}
            <ol className="space-y-3">
              {r.debug.steps.map((s, i) => (
                <StepItem key={s.step_id} step={s} index={i} />
              ))}
            </ol>
          </section>
        </div>
      </aside>
    </div>
  )
}

function formatDuration(ms: number): string {
  if (!ms || ms < 0) return '0ms'
  if (ms < 1000) return `${ms}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)}s`
  const minutes = Math.floor(seconds / 60)
  const remainder = seconds - minutes * 60
  return `${minutes}m ${remainder.toFixed(0)}s`
}

function StepItem({ step, index }: { step: DebugStep; index: number }) {
  const [open, setOpen] = useState(step.kind === 'response')
  const hasResult = step.result !== null && step.result !== undefined
  return (
    <li className="border border-border bg-surface rounded-md p-4">
      <div className="flex items-baseline justify-between gap-3 mb-1.5">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-ink-3 font-mono text-[10px]">#{index + 1}</span>
          <span className="pill !py-0.5">{step.kind}</span>
          <code className="font-mono text-[12px] text-ink-1 truncate">{step.name}</code>
        </div>
        <span className="text-ink-3 text-[11px] shrink-0 font-mono">
          {step.duration_ms}ms
          {typeof step.cost_usd === 'number' ? ` · $${step.cost_usd.toFixed(5)}` : ''}
        </span>
      </div>
      <div className="text-ink-2 text-sm leading-relaxed">{step.detail}</div>
      {step.usage && (
        <div className="mt-3 pt-3 border-t border-border text-[11px] font-mono text-ink-3 grid grid-cols-2 gap-x-6 gap-y-1">
          <span>model: <span className="text-ink-1">{step.usage.model}</span></span>
          {step.usage.reasoning_effort && (
            <span>effort: <span className="text-ink-1">{step.usage.reasoning_effort}</span></span>
          )}
          <span>prompt: <span className="text-ink-1">{step.usage.prompt_tokens}</span></span>
          <span>cached: <span className="text-ink-1">{step.usage.cached_tokens}</span></span>
          <span>completion: <span className="text-ink-1">{step.usage.completion_tokens}</span></span>
          <span>reasoning: <span className="text-ink-1">{step.usage.reasoning_tokens}</span></span>
        </div>
      )}
      {hasResult && (
        <div className="mt-3 pt-3 border-t border-border">
          <button
            onClick={() => setOpen(o => !o)}
            className="flex items-center gap-1.5 text-ink-3 hover:text-ink-1 text-[11px] uppercase tracking-tight transition-colors"
          >
            {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            {step.kind === 'response' ? 'Model response' : step.kind === 'tool_call' ? 'Tool result' : step.kind === 'resolver' ? 'Resolver detail' : 'LLM detail'}
          </button>
          {open && <ResultBlock step={step} />}
        </div>
      )}
    </li>
  )
}

function ResultBlock({ step }: { step: DebugStep }) {
  const result = step.result as Record<string, unknown> | null
  if (!result) return null

  if (step.kind === 'response') {
    const output = (result.output ?? {}) as Record<string, unknown>
    const kind = String(output.kind ?? 'answer')
    if (kind === 'clarifying_question') {
      const question = String(output.question ?? '')
      const options = (output.options as string[] | undefined) ?? []
      return (
        <div className="mt-3 space-y-2">
          <div className="text-ink-3 text-[10px] uppercase tracking-tight">Clarifying question</div>
          <div className="text-ink-1 text-sm leading-relaxed whitespace-pre-wrap">{question}</div>
          {options.length > 0 && (
            <ul className="flex flex-wrap gap-2 mt-2">
              {options.map(o => (
                <li key={o} className="pill !py-0.5">{o}</li>
              ))}
            </ul>
          )}
        </div>
      )
    }
    const answer = String(output.answer ?? '')
    const outOfScope = Boolean(output.out_of_scope)
    const generalKnowledge = Boolean(output.general_knowledge_used)
    const generalSection = output.general_knowledge_section as string | null | undefined
    const entries = (result.resolution_entries as Array<Record<string, unknown>> | undefined) ?? []
    return (
      <div className="mt-3 space-y-3">
        <div>
          <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">Answer</div>
          <div className="text-ink-1 text-sm leading-relaxed whitespace-pre-wrap">{answer || '(empty)'}</div>
        </div>
        {(outOfScope || generalKnowledge) && (
          <div className="flex gap-2 flex-wrap">
            {outOfScope && <span className="pill !py-0.5">out_of_scope</span>}
            {generalKnowledge && <span className="pill !py-0.5">general_knowledge_used</span>}
          </div>
        )}
        {generalKnowledge && generalSection && (
          <div className="border-l-2 border-dashed border-ink-2 pl-3">
            <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">General knowledge section</div>
            <div className="text-ink-2 text-sm leading-relaxed whitespace-pre-wrap">{generalSection}</div>
          </div>
        )}
        <div>
          <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">
            Resolved citations ({entries.length})
          </div>
          {entries.length === 0 ? (
            <div className="text-ink-3 text-xs italic">No citations in this response.</div>
          ) : (
            <ul className="space-y-2">
              {entries.map((c, i) => (
                <li key={i} className="border border-border bg-bg rounded-md p-2.5 text-[12px]">
                  <code className="font-mono text-ink-1">{String(c.passage_id ?? '')}</code>
                  <div className="text-ink-3 text-[11px] mt-0.5">
                    {((c.heading_path as string[] | undefined) ?? []).join(' › ')}
                  </div>
                  <div className="text-ink-3 text-[11px] mt-1 font-mono">
                    {c.failure_reason
                      ? `unresolved · ${String(c.failure_reason)}`
                      : `anchored · [${String(c.start)}, ${String(c.end)})`}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    )
  }

  if (step.kind === 'tool_call') {
    const value = result.result
    return (
      <div className="mt-3">
        <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">Returned</div>
        <ToolResultRender value={value} />
      </div>
    )
  }

  if (step.kind === 'resolver') {
    const entries = (result.entries as Array<Record<string, unknown>> | undefined) ?? []
    const anchored = entries.filter(e => !e.failure_reason)
    const unresolved = entries.filter(e => e.failure_reason)
    return (
      <div className="mt-3 space-y-2 text-[12px]">
        <div className="text-ink-2">
          entries {entries.length} · anchored{' '}
          <span className="text-ink-1 font-medium">{anchored.length}</span> · unresolved{' '}
          <span className="text-ink-1 font-medium">{unresolved.length}</span>
        </div>
        {anchored.length > 0 && (
          <div>
            <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">
              Anchored ({anchored.length})
            </div>
            <pre className="text-[11px] text-ink-2 bg-bg p-2 rounded-md overflow-x-auto">
              {JSON.stringify(anchored, null, 2)}
            </pre>
          </div>
        )}
        {unresolved.length > 0 && (
          <div>
            <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">
              Unresolved ({unresolved.length})
            </div>
            <pre className="text-[11px] text-ink-2 bg-bg p-2 rounded-md overflow-x-auto">
              {JSON.stringify(unresolved, null, 2)}
            </pre>
          </div>
        )}
      </div>
    )
  }

  // llm_call: show tool_calls or parsed/content
  const toolCalls = result.tool_calls as Array<Record<string, unknown>> | undefined
  return (
    <div className="mt-3 space-y-2 text-[12px]">
      {toolCalls && toolCalls.length > 0 && (
        <div>
          <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">
            Tool calls ({toolCalls.length})
          </div>
          <pre className="text-[11px] text-ink-2 bg-bg p-2 rounded-md overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(toolCalls, null, 2)}
          </pre>
        </div>
      )}
      {result.parsed !== undefined && (
        <div>
          <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">Parsed output</div>
          <pre className="text-[11px] text-ink-2 bg-bg p-2 rounded-md overflow-x-auto whitespace-pre-wrap">
            {JSON.stringify(result.parsed, null, 2)}
          </pre>
        </div>
      )}
      {typeof result.content === 'string' && (
        <div>
          <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">Content</div>
          <div className="text-ink-2 leading-relaxed whitespace-pre-wrap">{result.content}</div>
        </div>
      )}
    </div>
  )
}

function ToolResultRender({ value }: { value: unknown }) {
  // search_convictions returns a list of PassageHits.
  if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object' && value[0] !== null) {
    const first = value[0] as Record<string, unknown>
    if ('passage_id' in first && 'score' in first) {
      return (
        <ul className="space-y-2">
          {(value as Array<Record<string, unknown>>).map((hit, i) => (
            <li key={i} className="border border-border bg-bg rounded-md p-2.5 text-[12px]">
              <div className="flex items-baseline justify-between gap-2">
                <code className="font-mono text-ink-1 truncate">{String(hit.passage_id ?? '')}</code>
                <span className="text-ink-3 font-mono text-[10px] shrink-0">
                  score {Number(hit.score ?? 0).toFixed(3)}
                </span>
              </div>
              <div className="text-ink-3 text-[11px] mt-0.5">
                {((hit.heading_path as string[] | undefined) ?? []).join(' › ')}
              </div>
              {typeof hit.snippet === 'string' && hit.snippet && (
                <div className="text-ink-2 text-[12px] mt-1.5 leading-relaxed">
                  {hit.snippet}
                </div>
              )}
            </li>
          ))}
        </ul>
      )
    }
    // list_documents returns a list of DocSummaries.
    if ('id' in first && 'title' in first) {
      return (
        <ul className="text-[12px] space-y-1">
          {(value as Array<Record<string, unknown>>).map((doc, i) => (
            <li key={i} className="flex items-baseline justify-between gap-2 border-b border-border/50 pb-1">
              <code className="font-mono text-ink-1 truncate">{String(doc.id ?? '')}</code>
              <span className="text-ink-3 truncate">{String(doc.title ?? '')}</span>
            </li>
          ))}
        </ul>
      )
    }
    // read_passage returns a list of Passage objects.
    if ('id' in first && 'text' in first) {
      return (
        <ul className="space-y-2">
          {(value as Array<Record<string, unknown>>).map((p, i) => (
            <li key={i} className="border border-border bg-bg rounded-md p-2.5 text-[12px] space-y-1.5">
              <code className="font-mono text-ink-1 block">{String(p.id ?? '')}</code>
              <div className="text-ink-3 text-[11px]">
                {((p.heading_path as string[] | undefined) ?? []).join(' › ')}
              </div>
              <div className="text-ink-2 leading-relaxed whitespace-pre-wrap mt-1">
                {String(p.text ?? '')}
              </div>
            </li>
          ))}
        </ul>
      )
    }
  }
  // Fallback: pretty-print JSON.
  return (
    <pre className="text-[11px] text-ink-2 bg-bg p-2 rounded-md overflow-x-auto whitespace-pre-wrap">
      {JSON.stringify(value, null, 2)}
    </pre>
  )
}

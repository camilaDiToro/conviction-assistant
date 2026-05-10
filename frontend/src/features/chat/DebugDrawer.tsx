import { useEffect } from 'react'
import { X } from 'lucide-react'
import type { ChatMessage } from '@/lib/types'

interface DebugDrawerProps {
  message: Extract<ChatMessage, { role: 'assistant' }>
  onClose: () => void
}

export function DebugDrawer({ message, onClose }: DebugDrawerProps) {
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
            <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Cost summary</h4>
            <dl className="grid grid-cols-3 gap-px bg-border border border-border">
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
            </dl>
          </section>

          <section>
            <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Step timeline</h4>
            <ol className="space-y-3">
              {r.debug.steps.map((s, i) => (
                <li key={s.step_id} className="border border-border bg-surface rounded-md p-4">
                  <div className="flex items-baseline justify-between gap-3 mb-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-ink-3 font-mono text-[10px]">#{i + 1}</span>
                      <span className="pill !py-0.5">{s.kind}</span>
                      <code className="font-mono text-[12px] text-ink-1 truncate">{s.name}</code>
                    </div>
                    <span className="text-ink-3 text-[11px] shrink-0 font-mono">
                      {s.duration_ms}ms{s.cost_usd !== undefined ? ` · $${s.cost_usd.toFixed(5)}` : ''}
                    </span>
                  </div>
                  <div className="text-ink-2 text-sm leading-relaxed">{s.detail}</div>
                  {s.usage && (
                    <div className="mt-3 pt-3 border-t border-border text-[11px] font-mono text-ink-3 grid grid-cols-2 gap-x-6 gap-y-1">
                      <span>model: <span className="text-ink-1">{s.usage.model}</span></span>
                      <span>prompt: <span className="text-ink-1">{s.usage.prompt_tokens}</span></span>
                      <span>cached: <span className="text-ink-1">{s.usage.cached_tokens}</span></span>
                      <span>completion: <span className="text-ink-1">{s.usage.completion_tokens}</span></span>
                      <span>reasoning: <span className="text-ink-1">{s.usage.reasoning_tokens}</span></span>
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </section>

          <section>
            <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Verifier</h4>
            <div className="border border-border bg-surface rounded-md p-4">
              {r.debug.verification_passed ? (
                <div className="text-ink-1">
                  <span className="font-medium">✓ All citations verified.</span>
                  <p className="text-ink-2 text-sm mt-1.5">Each cited quote substring-matched its passage after normalization.</p>
                </div>
              ) : (
                <div className="text-ink-1">
                  <span className="font-medium">✗ One or more citations failed.</span>
                  <p className="text-ink-2 text-sm mt-1.5">Retried once with feedback; final state stripped the failing claim or returned a safe refusal.</p>
                </div>
              )}
            </div>
          </section>
        </div>
      </aside>
    </div>
  )
}

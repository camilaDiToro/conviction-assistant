import { useMemo, useState } from 'react'
import { AlertTriangle, ArrowRight, Lock } from 'lucide-react'
import { PageHeader } from '@/components/Section'
import { MessageList } from '@/features/chat/MessageList'
import type {
  ChatAnswerResponse,
  ChatClarifyResponse,
  ChatMessage,
  UsageSummary,
} from '@/lib/types'
import { EVAL_MOCK, EVAL_MOCK_META, type EvalRecord, type EvalTurn } from '@/data/eval_mock'
import { EvalModal } from './EvalModal'

const BUCKETS = ['all', 'factual', 'rule_a', 'rule_b', 'cross_lang', 'out_of_scope', 'clarify'] as const
type BucketFilter = (typeof BUCKETS)[number]

const EMPTY_USAGE: UsageSummary = {
  llm_call_count: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  cached_tokens: 0,
  reasoning_tokens: 0,
  step_count: 0,
  duration_ms: 0,
}
const EMPTY_DEBUG = { tool_calls: [], steps: [] }

export default function EvalChatPage() {
  const [activeId, setActiveId] = useState<string>(EVAL_MOCK[0]?.id ?? '')
  const [bucket, setBucket] = useState<BucketFilter>('all')
  const [evalFor, setEvalFor] = useState<EvalRecord | null>(null)

  const active = useMemo(
    () => EVAL_MOCK.find(r => r.id === activeId) ?? null,
    [activeId],
  )

  const filtered = useMemo(
    () => (bucket === 'all' ? EVAL_MOCK : EVAL_MOCK.filter(r => r.bucket === bucket)),
    [bucket],
  )

  const messages = useMemo(() => (active ? toChatMessages(active) : []), [active])

  return (
    <article>
      <PageHeader
        eyebrow="Eval · latest run as chat"
        title="See the eval results in the chat surface."
        lead={
          <>
            Same UI the analyst would touch, fed with every question/answer pair from{' '}
            <code className="font-mono text-[14px] text-ink-1">{EVAL_MOCK_META.run_dir}</code>. Pick
            a question on the left; <strong className="text-ink-1">view eval</strong> on each
            assistant turn opens the deterministic metrics plus what the LLM-as-judge said.
          </>
        }
      />

      <div className="mt-6 mb-8 border border-amber-500/40 bg-amber-500/5 rounded-md px-4 py-3 flex items-start gap-3">
        <AlertTriangle size={16} className="text-amber-400 mt-0.5 shrink-0" />
        <div className="text-ink-2 text-[13px] leading-relaxed">
          <strong className="text-ink-1 font-medium">Vibecoded read of the real eval results</strong>{' '}
          — not real conversations stored in the database. Composer is disabled. Source files live
          in <code className="font-mono text-[12px] text-ink-1">{EVAL_MOCK_META.run_dir}/</code>{' '}
          (deterministic: <code className="font-mono text-[12px] text-ink-1">{EVAL_MOCK_META.combined_basename}</code>,
          judge: <code className="font-mono text-[12px] text-ink-1">{EVAL_MOCK_META.judge_basename}</code>).
        </div>
      </div>

      <div className="border border-border rounded-md bg-bg overflow-hidden flex min-h-[40rem]">
        <aside className="w-72 shrink-0 border-r border-border bg-surface flex flex-col">
          <div className="px-3 py-3 border-b border-border">
            <div className="text-ink-3 text-[10px] uppercase tracking-tight font-medium mb-2">
              Filter
            </div>
            <div className="flex flex-wrap gap-1.5">
              {BUCKETS.map(b => {
                const count = b === 'all' ? EVAL_MOCK.length : EVAL_MOCK.filter(r => r.bucket === b).length
                const isActive = bucket === b
                return (
                  <button
                    key={b}
                    onClick={() => setBucket(b)}
                    className={[
                      'text-[11px] font-mono px-2 py-0.5 rounded-md border transition-colors',
                      isActive
                        ? 'border-ink-1 text-ink-1 bg-bg'
                        : 'border-border text-ink-3 hover:text-ink-1 hover:border-ink-3',
                    ].join(' ')}
                  >
                    {b}
                    <span className="text-ink-4">·{count}</span>
                  </button>
                )
              })}
            </div>
          </div>
          <ul className="flex-1 overflow-y-auto py-2">
            {filtered.map(r => (
              <li key={r.id}>
                <button
                  onClick={() => setActiveId(r.id)}
                  className={[
                    'w-full text-left px-4 py-2.5 hover:bg-bg transition-colors group',
                    r.id === activeId ? 'bg-bg border-l-2 border-ink-1' : 'border-l-2 border-transparent',
                  ].join(' ')}
                >
                  <div className="flex items-baseline gap-2 mb-0.5">
                    <code className="font-mono text-[11px] text-ink-1">{r.id}</code>
                    <span className="font-mono text-[10px] text-ink-3">{r.bucket}</span>
                    <span className="font-mono text-[10px] text-ink-4">{r.language.toUpperCase()}</span>
                  </div>
                  <div className="text-ink-2 text-[12px] leading-snug line-clamp-2 group-hover:text-ink-1">
                    {r.question}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <main className="flex-1 flex flex-col min-w-0">
          {active ? (
            <>
              <div className="flex-1 overflow-y-auto px-6 md:px-10 py-8">
                <div className="max-w-3xl mx-auto">
                  <MessageList
                    messages={messages}
                    onOpenDebug={() => undefined}
                    onOpenEval={() => setEvalFor(active)}
                    busy={false}
                  />
                </div>
              </div>
              <div className="px-6 md:px-10 pb-6 pt-2 border-t border-border bg-gradient-to-t from-surface to-bg">
                <div className="max-w-3xl mx-auto">
                  <div className="flex items-center gap-3 border border-border rounded-md bg-surface px-4 py-3 text-ink-3 text-[13px]">
                    <Lock size={14} className="text-ink-3" />
                    Read-only · eval run {EVAL_MOCK_META.run_dir.split('/').pop()} ·{' '}
                    {EVAL_MOCK_META.agent_model}/{EVAL_MOCK_META.reasoning_effort}
                  </div>
                  <div className="mt-2 text-ink-4 text-[11px]">
                    Click <strong>view eval</strong> below any answer for the deterministic metrics and judge rubrics.
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-ink-3 text-sm">
              No record selected.
            </div>
          )}
        </main>
      </div>

      <p className="text-ink-3 text-[12px] leading-relaxed mt-4 max-w-prose">
        Judge prompt hash <code className="font-mono text-ink-1">{EVAL_MOCK_META.judge_prompt_hash}</code>{' '}
        · judge model <code className="font-mono text-ink-1">{EVAL_MOCK_META.judge_model}</code> ·{' '}
        {EVAL_MOCK_META.question_count} questions covered. <ArrowRight size={11} className="inline-block align-middle" />{' '}
        Two judge runs are comparable only when both signatures (model + prompt hash) match.
      </p>

      <EvalModal record={evalFor} onClose={() => setEvalFor(null)} />
    </article>
  )
}

function toChatMessages(record: EvalRecord): ChatMessage[] {
  // EvalTurn[] mirrors ChatMessage but assistant.response is missing the
  // wire-only fields (disclaimer, usage_summary, debug, …). Inject empty
  // defaults so MessageList renders identically to the live chat.
  return record.turns.flatMap<ChatMessage>((t: EvalTurn, i): ChatMessage[] => {
    if (t.role === 'user') {
      return [{ role: 'user', content: t.content, id: `${record.id}-u-${i}` }]
    }
    const base = t.response
    const response: ChatAnswerResponse | ChatClarifyResponse =
      base.kind === 'answer'
        ? {
            kind: 'answer',
            answer: base.answer,
            citations: base.citations,
            general_knowledge_used: base.general_knowledge_used,
            general_knowledge_section: base.general_knowledge_section,
            out_of_scope: base.out_of_scope,
            conflict_detected: base.conflict_detected,
            conflict_statement: base.conflict_statement,
            disclaimer: '',
            usage_summary: EMPTY_USAGE,
            debug: EMPTY_DEBUG,
            conversation_id: '',
            question_id: record.id,
          }
        : {
            kind: 'clarifying_question',
            question: base.question,
            options: base.options,
            disclaimer: '',
            usage_summary: EMPTY_USAGE,
            debug: EMPTY_DEBUG,
            conversation_id: '',
            question_id: record.id,
          }
    return [{ role: 'assistant', response, id: `${record.id}-a-${i}` }]
  })
}

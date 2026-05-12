import { useEffect } from 'react'
import { X } from 'lucide-react'
import type {
  EvalDeterministicMetric,
  EvalJudgeRubric,
  EvalRecord,
  EvalRecordExpected,
} from '@/data/eval_mock'

interface EvalModalProps {
  record: EvalRecord | null
  onClose: () => void
}

export function EvalModal({ record, onClose }: EvalModalProps) {
  useEffect(() => {
    if (!record) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [record, onClose])

  if (!record) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-8">
      <div
        className="absolute inset-0 bg-bg/80 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />
      <div
        className="relative w-full max-w-3xl max-h-full bg-bg border border-border rounded-md shadow-lg overflow-hidden flex flex-col animate-fade-in"
        role="dialog"
        aria-modal="true"
      >
        <div className="px-5 py-4 border-b border-border flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">
              Eval · {record.id}
            </div>
            <div className="text-ink-1 text-[13px] leading-snug truncate">{record.question}</div>
            <div className="text-ink-3 text-[11px] mt-1 font-mono">
              bucket={record.bucket} · lang={record.language.toUpperCase()} · {record.duration_ms} ms
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close eval"
            className="text-ink-3 hover:text-ink-1 p-1 shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4 overflow-y-auto space-y-7">
          <ExpectedBlock expected={record.expected} />
          <DeterministicBlock metrics={record.deterministic} />
          <JudgeBlock rubrics={record.judge} />
        </div>
      </div>
    </div>
  )
}

function ExpectedBlock({ expected }: { expected: EvalRecordExpected }) {
  return (
    <section>
      <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-3">
        What was expected (from the golden set)
      </div>
      <div className="border border-border rounded-md divide-y divide-border text-[12px]">
        <Row label="expected_passage_ids">
          {expected.passage_ids.length === 0 ? (
            <span className="text-ink-3">— none (not asserted for this bucket)</span>
          ) : (
            <div className="flex flex-col gap-1">
              {expected.passage_ids.map(pid => (
                <code key={pid} className="font-mono text-ink-1">
                  {pid}
                </code>
              ))}
            </div>
          )}
        </Row>
        <Row label="must_cite_at_least">
          <code className="font-mono text-ink-1">{expected.must_cite_at_least}</code>
        </Row>
        <Row label="expected_out_of_scope">
          <code className="font-mono text-ink-1">{String(expected.out_of_scope)}</code>
        </Row>
        <Row label="expected_general_knowledge">
          <code className="font-mono text-ink-1">{String(expected.general_knowledge)}</code>
        </Row>
        <Row label="expected_conflict_mention">
          <code className="font-mono text-ink-1">{String(expected.conflict_mention)}</code>
        </Row>
      </div>
    </section>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-2.5 grid grid-cols-[14rem_1fr] items-baseline gap-x-4">
      <code className="font-mono text-[11px] text-ink-3">{label}</code>
      <div className="text-ink-2 leading-relaxed">{children}</div>
    </div>
  )
}

function DeterministicBlock({ metrics }: { metrics: EvalDeterministicMetric[] }) {
  return (
    <section>
      <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-3">
        Deterministic metrics
      </div>
      <div className="border border-border rounded-md overflow-hidden">
        <table className="w-full text-[12px]">
          <thead className="bg-surface text-ink-3 text-[10px] uppercase tracking-tight">
            <tr>
              <th className="text-left px-4 py-2 font-medium w-[14rem]">metric</th>
              <th className="text-left px-4 py-2 font-medium w-[6rem]">value</th>
              <th className="text-left px-4 py-2 font-medium">reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {metrics.map(m => (
              <tr key={m.name}>
                <td className="px-4 py-2 align-top">
                  <code className="font-mono text-ink-1">{m.name}</code>
                </td>
                <td className={['px-4 py-2 align-top font-mono', labelColor(m.label)].join(' ')}>
                  {m.label || '—'}
                </td>
                <td className="px-4 py-2 align-top text-ink-2 leading-relaxed">{m.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function JudgeBlock({ rubrics }: { rubrics: EvalJudgeRubric[] }) {
  return (
    <section>
      <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-3">
        LLM-as-judge · claude-opus-4-7
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {rubrics.map(r => (
          <div key={r.name} className="border border-border rounded-md p-3">
            <div className="flex items-baseline justify-between gap-3 mb-1.5">
              <code className="font-mono text-[11px] text-ink-1">{r.name}</code>
              <span className={['font-mono text-[11px]', judgeColor(r)].join(' ')}>
                {formatJudgeValue(r)}
              </span>
            </div>
            <p className="text-ink-2 text-[12px] leading-relaxed">{r.reason}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function labelColor(label: string): string {
  const l = label.toLowerCase()
  if (l === 'correct') return 'text-emerald-400'
  if (l === 'incorrect') return 'text-red-400'
  if (l === 'n/a' || l === '') return 'text-ink-3'
  // numeric (e.g. "1.0", "0.75")
  const n = Number(l)
  if (!Number.isNaN(n)) {
    if (n >= 0.99) return 'text-emerald-400'
    if (n >= 0.7) return 'text-ink-1'
    return 'text-red-400'
  }
  return 'text-ink-1'
}

function judgeColor(r: EvalJudgeRubric): string {
  if (!r.applicable || r.score === null) return 'text-ink-3'
  if (r.score >= 0.99) return 'text-emerald-400'
  if (r.score >= 0.7) return 'text-ink-1'
  return 'text-red-400'
}

function formatJudgeValue(r: EvalJudgeRubric): string {
  if (!r.applicable || (r.score === null && (!r.label || r.label === 'n/a'))) return 'n/a'
  const parts: string[] = []
  if (r.label && r.label !== 'n/a') parts.push(r.label)
  if (r.score !== null) parts.push(r.score.toFixed(3))
  return parts.join(' · ') || 'n/a'
}

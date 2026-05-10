import type { ReactNode } from 'react'

// A neutral aside used to label a Trade-off, Failure mode, Future work item,
// or a Designed-not-yet-built notice. Tone variants modify border style only;
// the label is the load-bearing signal.

export type CalloutTone = 'note' | 'pending' | 'trade-off' | 'failure'

interface CalloutProps {
  label: string
  tone?: CalloutTone
  children: ReactNode
}

const STYLE: Record<CalloutTone, { border: string; label: string; glyph: string }> = {
  note: {
    border: 'border-border',
    label: 'text-ink-3',
    glyph: '·',
  },
  pending: {
    border: 'border-ink-2 border-dashed',
    label: 'text-ink-1 font-medium',
    glyph: '◐',
  },
  'trade-off': {
    border: 'border-border-strong',
    label: 'text-ink-2 font-medium',
    glyph: '↹',
  },
  failure: {
    border: 'border-ink-2',
    label: 'text-ink-1 font-medium',
    glyph: '!',
  },
}

export function Callout({ label, tone = 'note', children }: CalloutProps) {
  const s = STYLE[tone]
  return (
    <aside className={`my-6 border-l-2 pl-5 py-1 ${s.border}`}>
      <div className={`text-[10px] uppercase tracking-tight mb-2 ${s.label}`}>
        <span className="inline-block w-3 mr-1.5 font-mono">{s.glyph}</span>
        {label}
      </div>
      <div className="text-ink-2 text-[15px] leading-relaxed">{children}</div>
    </aside>
  )
}

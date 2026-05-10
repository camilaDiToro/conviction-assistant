import type { Passage } from '@/lib/types'

interface PassageCardProps {
  passage: Passage
  highlight?: string
  compact?: boolean
}

export function PassageCard({ passage, highlight, compact }: PassageCardProps) {
  return (
    <div className="border border-border bg-surface p-5 rounded-md hover:border-border-strong transition-colors">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-3">
        <code className="font-mono text-[11px] text-ink-1">{passage.id}</code>
        {passage.document_updated && (
          <span className="text-ink-3 text-[11px]">· updated {passage.document_updated}</span>
        )}
      </div>
      <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-1">
        {passage.heading_path.join(' › ')}
      </div>
      <h4 className="text-ink-1 font-medium mb-3 tracking-tight">{passage.heading}</h4>
      <p
        className={`text-ink-2 leading-relaxed ${compact ? 'text-sm line-clamp-3' : 'text-[15px]'}`}
      >
        {highlight ? (
          <Highlight text={passage.text} term={highlight} />
        ) : (
          passage.text
        )}
      </p>
    </div>
  )
}

function Highlight({ text, term }: { text: string; term: string }) {
  if (!term) return <>{text}</>
  const re = new RegExp(`(${escape(term)})`, 'gi')
  const parts = text.split(re)
  return (
    <>
      {parts.map((p, i) =>
        re.test(p) ? (
          <mark key={i} className="bg-ink-1 text-bg px-0.5">{p}</mark>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </>
  )
}

function escape(s: string) {
  return s.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')
}

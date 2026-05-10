import { useEffect } from 'react'
import { X } from 'lucide-react'
import type { Citation } from '@/lib/types'

interface CitationModalProps {
  citation: Citation | null
  onClose: () => void
}

export function CitationModal({ citation, onClose }: CitationModalProps) {
  useEffect(() => {
    if (!citation) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [citation, onClose])

  if (!citation) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4 py-8">
      <div
        className="absolute inset-0 bg-bg/80 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />
      <div
        className="relative w-full max-w-2xl max-h-full bg-bg border border-border rounded-md shadow-lg overflow-hidden flex flex-col animate-fade-in"
        role="dialog"
        aria-modal="true"
      >
        <div className="px-5 py-4 border-b border-border flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-1">
              Cited passage
            </div>
            <code className="font-mono text-[12px] text-ink-1 block truncate">
              {citation.passage_id}
            </code>
            <div className="text-ink-3 text-[11px] mt-1 truncate">
              {citation.heading_path.join(' › ')}
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close citation"
            className="text-ink-3 hover:text-ink-1 p-1 shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4 overflow-y-auto">
          <pre className="whitespace-pre-wrap font-sans text-ink-1 leading-relaxed text-[15px]">
            {renderPassage(citation)}
          </pre>
        </div>
      </div>
    </div>
  )
}

function renderPassage(c: Citation): React.ReactNode {
  const { passage_text, start, end } = c
  if (start === null || end === null || start < 0 || end > passage_text.length || start >= end) {
    return passage_text
  }
  return (
    <>
      {passage_text.slice(0, start)}
      <mark className="bg-ink-1/15 text-ink-1 rounded-[2px] px-0.5">
        {passage_text.slice(start, end)}
      </mark>
      {passage_text.slice(end)}
    </>
  )
}

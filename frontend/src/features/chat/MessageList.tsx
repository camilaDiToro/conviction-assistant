import { Bug, FileText, Info, Quote } from 'lucide-react'
import { useState } from 'react'
import type { ChatMessage, Citation } from '@/lib/types'

interface MessageListProps {
  messages: ChatMessage[]
  onOpenDebug: (m: ChatMessage) => void
  busy: boolean
}

export function MessageList({ messages, onOpenDebug, busy }: MessageListProps) {
  return (
    <div className="space-y-10">
      {messages.map(m =>
        m.role === 'user' ? (
          <UserBubble key={m.id} text={m.content} />
        ) : (
          <AssistantTurn key={m.id} message={m} onOpenDebug={() => onOpenDebug(m)} />
        ),
      )}
      {busy && <Thinking />}
    </div>
  )
}

function UserBubble({ text }: { text: string }) {
  return (
    <div className="animate-fade-in">
      <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-2">You</div>
      <div className="text-ink-1 text-lg leading-relaxed text-balance">{text}</div>
    </div>
  )
}

function AssistantTurn({ message, onOpenDebug }: { message: Extract<ChatMessage, { role: 'assistant' }>; onOpenDebug: () => void }) {
  const r = message.response

  if (r.kind === 'clarifying_question') {
    return (
      <div className="animate-fade-in">
        <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-2">Decade AI · clarifying</div>
        <div className="text-ink-1 leading-relaxed text-lg mb-4">{r.question}</div>
        <div className="flex flex-wrap gap-2">
          {r.options.map(o => (
            <span key={o} className="pill">{o}</span>
          ))}
        </div>
        <Footer onOpenDebug={onOpenDebug} cost={r.usage_summary.question_total_cost_usd} disclaimer={r.disclaimer} />
      </div>
    )
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-ink-3 text-[11px] uppercase tracking-tight">Decade AI</span>
        {r.out_of_scope && <span className="pill"><Info size={11} /> Out of scope</span>}
        {!r.out_of_scope && r.debug.verification_passed && (
          <span className="pill"><span className="text-ink-1">✓</span> Verified</span>
        )}
        {!r.out_of_scope && !r.debug.verification_passed && (
          <span className="pill"><span className="text-ink-1">✗</span> Verifier failed</span>
        )}
      </div>

      <div className="prose-decade text-ink-1 leading-relaxed text-[17px] mb-6">
        <RenderAnswer text={r.answer} citations={r.citations} />
      </div>

      {r.general_knowledge_used && r.general_knowledge_section && (
        <div className="my-6 border-l-2 border-dashed border-ink-2 pl-5 py-1">
          <div className="text-ink-1 text-[11px] uppercase tracking-tight font-medium mb-2">
            Not from Decade convictions — general knowledge
          </div>
          <p className="text-ink-2 leading-relaxed">{r.general_knowledge_section}</p>
        </div>
      )}

      {r.citations.length > 0 && (
        <div className="mt-6 space-y-2">
          <div className="text-ink-3 text-[11px] uppercase tracking-tight">Citations</div>
          {r.citations.map((c, i) => (
            <CitationRow key={i} citation={c} />
          ))}
        </div>
      )}

      <Footer onOpenDebug={onOpenDebug} cost={r.usage_summary.question_total_cost_usd} disclaimer={r.disclaimer} />
    </div>
  )
}

function RenderAnswer({ text }: { text: string; citations: Citation[] }) {
  return <p>{text}</p>
}

function CitationRow({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-border bg-surface rounded-md">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-surface-2 transition-colors"
      >
        <FileText size={14} className="text-ink-3 mt-0.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <code className="font-mono text-[11px] text-ink-1 truncate block">{citation.passage_id}</code>
          <div className="text-ink-3 text-[11px] mt-0.5 truncate">
            {citation.heading_path.join(' › ')}
            {citation.document_updated && ` · updated ${citation.document_updated}`}
          </div>
        </div>
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-border">
          <div className="flex items-start gap-2">
            <Quote size={14} className="text-ink-3 mt-1 shrink-0" />
            <blockquote className="text-ink-2 italic leading-relaxed text-[15px]">
              "{citation.quote}"
            </blockquote>
          </div>
        </div>
      )}
    </div>
  )
}

function Footer({ onOpenDebug, cost, disclaimer }: { onOpenDebug: () => void; cost: number; disclaimer: string }) {
  return (
    <div className="mt-6 pt-4 border-t border-border flex flex-wrap items-center justify-between gap-3">
      <p className="text-ink-3 text-xs italic leading-relaxed max-w-prose">{disclaimer}</p>
      <button
        onClick={onOpenDebug}
        className="text-ink-3 hover:text-ink-1 text-xs flex items-center gap-1.5 transition-colors"
      >
        <Bug size={12} /> debug · ${cost.toFixed(5)}
      </button>
    </div>
  )
}

function Thinking() {
  return (
    <div className="animate-fade-in">
      <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-2">Decade AI</div>
      <div className="flex items-center gap-2 text-ink-3">
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-ink-3 animate-pulse" />
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-ink-3 animate-pulse [animation-delay:120ms]" />
        <span className="inline-block h-1.5 w-1.5 rounded-full bg-ink-3 animate-pulse [animation-delay:240ms]" />
        <span className="ml-2 text-xs">searching · reading · verifying</span>
      </div>
    </div>
  )
}

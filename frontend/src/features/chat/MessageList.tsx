import { Bug, FileText, Info } from 'lucide-react'
import { useState } from 'react'
import type { ChatMessage, Citation } from '@/lib/types'
import { CitationModal } from './CitationModal'

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
  const [openCitation, setOpenCitation] = useState<Citation | null>(null)

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
        <Footer onOpenDebug={onOpenDebug} disclaimer={r.disclaimer} />
      </div>
    )
  }

  const openByIndex = (n: number) => {
    if (n < 1 || n > r.citations.length) return
    setOpenCitation(r.citations[n - 1])
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-ink-3 text-[11px] uppercase tracking-tight">Decade AI</span>
        {r.out_of_scope && <span className="pill"><Info size={11} /> Out of scope</span>}
      </div>

      <div className="prose-decade text-ink-1 leading-relaxed text-[17px] mb-6">
        <RenderAnswer text={r.answer} citations={r.citations} onOpenCitation={openByIndex} />
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
            <CitationRow
              key={i}
              citation={c}
              index={i + 1}
              onOpen={() => setOpenCitation(c)}
            />
          ))}
        </div>
      )}

      <Footer onOpenDebug={onOpenDebug} disclaimer={r.disclaimer} />

      <CitationModal citation={openCitation} onClose={() => setOpenCitation(null)} />
    </div>
  )
}

const INLINE_RE = /\*\*(.+?)\*\*|⟦cite:(\d+)⟧/g

function injectCitationTokens(answer: string, citations: Citation[]): string {
  // Convert literal [N] markers (1-indexed) typed by the agent into the
  // internal token. Out-of-range numbers are left alone (they may be
  // legitimate bracketed numbers in the prose).
  return answer.replace(/\[(\d+)\]/g, (match, n) => {
    const idx = Number(n)
    if (idx < 1 || idx > citations.length) return match
    return `⟦cite:${idx}⟧`
  })
}

function renderInline(
  text: string,
  key: string,
  onOpenCitation: (n: number) => void,
): React.ReactNode[] {
  const out: React.ReactNode[] = []
  let last = 0
  let match: RegExpExecArray | null
  const re = new RegExp(INLINE_RE.source, 'g')
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) out.push(text.slice(last, match.index))
    if (match[1] !== undefined) {
      out.push(<strong key={`${key}-b${out.length}`}>{match[1]}</strong>)
    } else if (match[2] !== undefined) {
      const n = Number(match[2])
      out.push(
        <sup key={`${key}-c${out.length}`}>
          <button
            type="button"
            onClick={() => onOpenCitation(n)}
            className="ml-0.5 text-ink-1 no-underline hover:underline font-medium bg-transparent border-0 p-0 cursor-pointer"
          >
            [{n}]
          </button>
        </sup>,
      )
    }
    last = re.lastIndex
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

function RenderAnswer({
  text,
  citations,
  onOpenCitation,
}: {
  text: string
  citations: Citation[]
  onOpenCitation: (n: number) => void
}) {
  const tokenized = injectCitationTokens(text, citations)
  const blocks = tokenized.split(/\n{2,}/)
  return (
    <>
      {blocks.map((block, bi) => {
        const lines = block.split('\n')
        const allBullets = lines.length > 0 && lines.every(l => /^\s*-\s+/.test(l))
        if (allBullets) {
          return (
            <ul key={bi} className="list-disc pl-6 my-3 space-y-1.5">
              {lines.map((l, li) => (
                <li key={li}>
                  {renderInline(l.replace(/^\s*-\s+/, ''), `b${bi}-${li}`, onOpenCitation)}
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={bi} className="my-3">
            {lines.flatMap((l, li) => {
              const stripped = l.replace(/^\s*-\s+/, '• ')
              const nodes = renderInline(stripped, `b${bi}-${li}`, onOpenCitation)
              return li === 0 ? nodes : [<br key={`br-${bi}-${li}`} />, ...nodes]
            })}
          </p>
        )
      })}
    </>
  )
}

function CitationRow({
  citation,
  index,
  onOpen,
}: {
  citation: Citation
  index: number
  onOpen: () => void
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="w-full border border-border bg-surface hover:bg-surface-2 hover:border-border-strong rounded-md transition-colors text-left"
    >
      <div className="flex items-start gap-3 px-4 py-3">
        <span className="font-mono text-[11px] text-ink-1 mt-0.5 shrink-0 min-w-[1.5rem]">[{index}]</span>
        <FileText size={14} className="text-ink-3 mt-0.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <code className="font-mono text-[11px] text-ink-1 truncate block">{citation.passage_id}</code>
          <div className="text-ink-3 text-[11px] mt-0.5 truncate">
            {citation.heading_path.join(' › ')}
            {citation.document_updated && ` · updated ${citation.document_updated}`}
          </div>
        </div>
      </div>
    </button>
  )
}

function Footer({ onOpenDebug, disclaimer }: { onOpenDebug: () => void; disclaimer: string }) {
  return (
    <div className="mt-6 pt-4 border-t border-border flex flex-wrap items-center justify-between gap-3">
      <p className="text-ink-3 text-xs italic leading-relaxed max-w-prose">{disclaimer}</p>
      <button
        onClick={onOpenDebug}
        className="text-ink-3 hover:text-ink-1 text-xs flex items-center gap-1.5 transition-colors"
      >
        <Bug size={12} /> view steps
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
        <span className="ml-2 text-xs">searching · reading · grounding</span>
      </div>
    </div>
  )
}

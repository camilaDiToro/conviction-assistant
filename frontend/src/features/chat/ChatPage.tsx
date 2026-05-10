import { Link } from 'react-router-dom'
import { ArrowLeft, ArrowRight, FlaskConical } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { GridMark } from '@/components/GridMark'
import { sendChatMessage } from '@/lib/api'
import type { ChatMessage } from '@/lib/types'
import { MessageList } from './MessageList'
import { DebugDrawer } from './DebugDrawer'

const SUGGESTIONS = [
  'Como funciona a tributação de LCI e LCA?',
  'Qual o limite do FGC para LCIs?',
  'How do I compare an LCA yield to a CDB?',
  '¿Cuál es el plazo mínimo de carencia para una LCA?',
]

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [debugFor, setDebugFor] = useState<ChatMessage | null>(null)
  const conversationId = useRef(`conv-${Math.random().toString(36).slice(2, 10)}`)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const ask = async (q: string) => {
    if (!q.trim() || busy) return
    const user: ChatMessage = { role: 'user', content: q, id: rid() }
    setMessages(m => [...m, user])
    setInput('')
    setBusy(true)
    try {
      const res = await sendChatMessage({
        question: q,
        conversationId: conversationId.current,
        history: messages.map(m =>
          m.role === 'user' ? { role: 'user', content: m.content } : { role: 'assistant', content: '' },
        ),
      })
      const reply: ChatMessage = { role: 'assistant', response: res, id: rid() }
      setMessages(m => [...m, reply])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col bg-bg">
      <header className="px-6 md:px-10 h-16 flex items-center justify-between border-b border-border shrink-0 bg-bg sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <Link to="/" className="flex items-center gap-3 text-ink-1">
            <GridMark size={26} />
            <span className="text-sm tracking-tight font-medium">Decade AI Chat</span>
          </Link>
          <span className="pill">
            <FlaskConical size={11} /> Mock backend · /chat lands in B9
          </span>
        </div>
        <Link to="/design/overview" className="btn-ghost">
          <ArrowLeft size={14} /> Design
        </Link>
      </header>

      <main className="flex-1 flex flex-col">
        <div className="flex-1 px-6 md:px-10 py-10">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <EmptyState onPick={ask} />
            ) : (
              <MessageList messages={messages} onOpenDebug={setDebugFor} busy={busy} />
            )}
            <div ref={endRef} />
          </div>
        </div>

        <div className="px-6 md:px-10 pb-8 sticky bottom-0 bg-gradient-to-t from-bg via-bg to-transparent">
          <form
            onSubmit={(e) => { e.preventDefault(); ask(input) }}
            className="max-w-3xl mx-auto"
          >
            <div className="flex items-end gap-3 border border-border focus-within:border-ink-1 rounded-md bg-surface transition-colors">
              <textarea
                rows={1}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    ask(input)
                  }
                }}
                placeholder="Ask about Decade convictions — PT, EN, or ES."
                className="flex-1 bg-transparent text-ink-1 px-4 py-3 outline-none resize-none placeholder:text-ink-3"
                disabled={busy}
              />
              <button
                type="submit"
                disabled={busy || !input.trim()}
                className="m-2 p-2 text-ink-3 hover:text-ink-1 disabled:opacity-30 transition-colors"
                aria-label="Send"
              >
                <ArrowRight size={16} />
              </button>
            </div>
            <div className="mt-2 text-ink-4 text-[11px]">
              Enter sends · Shift+Enter for newline · Responses are mocked until B9 ships /chat.
            </div>
          </form>
        </div>
      </main>

      {debugFor && debugFor.role === 'assistant' && (
        <DebugDrawer message={debugFor} onClose={() => setDebugFor(null)} />
      )}
    </div>
  )
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="py-20 animate-fade-in">
      <div className="pill mb-6">Conversation is empty</div>
      <h1 className="text-display-2 text-ink-1 mb-4 max-w-[16ch] text-balance">
        Ask the conviction corpus a question.
      </h1>
      <p className="text-ink-2 max-w-prose mb-10 text-balance leading-relaxed">
        Every claim in the answer must round-trip through the deterministic verifier — quotes
        substring-match a cited passage after normalization, or they don't make it to your screen.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            className="text-left border border-border bg-surface hover:border-border-strong hover:bg-surface-2 px-5 py-4 rounded-md transition-colors group"
          >
            <div className="text-ink-2 group-hover:text-ink-1 transition-colors">
              {s}
            </div>
            <div className="text-ink-4 text-[11px] mt-2 flex items-center gap-1">
              Try this <ArrowRight size={11} />
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function rid() { return Math.random().toString(36).slice(2, 10) }

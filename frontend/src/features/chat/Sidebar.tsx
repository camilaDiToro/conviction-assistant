import { Plus, MessageSquare, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { listConversations, UnauthorizedError } from '@/lib/api'
import type { ConversationListItem } from '@/lib/types'

interface SidebarProps {
  activeId: string | null
  refreshKey: number
  onSelect: (id: string) => void
  onNewChat: () => void
  onUnauthorized: () => void
}

export function Sidebar({
  activeId,
  refreshKey,
  onSelect,
  onNewChat,
  onUnauthorized,
}: SidebarProps) {
  const [items, setItems] = useState<ConversationListItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setError(null)
    listConversations()
      .then(res => {
        if (!cancelled) setItems(res.conversations)
      })
      .catch(e => {
        if (cancelled) return
        if (e instanceof UnauthorizedError) onUnauthorized()
        else setError(e instanceof Error ? e.message : String(e))
      })
    return () => {
      cancelled = true
    }
  }, [refreshKey, onUnauthorized])

  return (
    <aside className="w-72 shrink-0 border-r border-border bg-surface flex flex-col">
      <div className="px-4 py-4 border-b border-border">
        <button
          onClick={onNewChat}
          className="w-full inline-flex items-center justify-center gap-2 border border-border hover:border-ink-1 px-3 py-2 rounded-md text-sm text-ink-1 transition-colors"
        >
          <Plus size={14} /> New chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {items === null && !error && (
          <div className="px-4 py-6 text-ink-3 text-xs flex items-center gap-2">
            <Loader2 size={12} className="animate-spin" /> Loading conversations…
          </div>
        )}
        {error && (
          <div className="px-4 py-6 text-ink-2 text-xs">
            <strong className="text-ink-1 font-medium block mb-1">Failed to load list.</strong>
            {error}
          </div>
        )}
        {items !== null && items.length === 0 && (
          <div className="px-4 py-6 text-ink-3 text-xs leading-relaxed">
            No conversations yet. Ask something on the right — it'll show up here.
          </div>
        )}
        {items !== null && items.length > 0 && (
          <ul className="py-2">
            {items.map(item => (
              <li key={item.conversation_id}>
                <button
                  onClick={() => onSelect(item.conversation_id)}
                  className={`w-full text-left px-4 py-3 hover:bg-bg transition-colors group ${
                    item.conversation_id === activeId ? 'bg-bg border-l-2 border-ink-1' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <MessageSquare
                      size={12}
                      className="mt-1 text-ink-3 group-hover:text-ink-1 shrink-0"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="text-ink-1 text-sm leading-snug truncate">{item.title}</div>
                      <div className="text-ink-3 text-[11px] mt-1 flex gap-2">
                        <span>{formatDate(item.last_ts)}</span>
                        <span>·</span>
                        <span>
                          {item.question_count}{' '}
                          {item.question_count === 1 ? 'message' : 'messages'}
                        </span>
                      </div>
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  )
}

function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    const now = new Date()
    const sameDay = d.toDateString() === now.toDateString()
    if (sameDay) {
      return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch {
    return iso.slice(0, 10)
  }
}

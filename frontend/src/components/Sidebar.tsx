import { Link, useLocation } from 'react-router-dom'
import { ChevronDown, Lock, PanelLeftClose, PanelLeftOpen } from 'lucide-react'
import { useEffect, useState } from 'react'
import { GridMark } from './GridMark'
import { NAV_GROUPS } from '@/data/decisions'

interface SidebarProps {
  expanded: boolean
  onToggle: () => void
}

export function Sidebar({ expanded, onToggle }: SidebarProps) {
  return (
    <aside
      className={[
        'h-screen sticky top-0 left-0 flex flex-col bg-bg border-r border-border transition-[width] duration-300 ease-decade overflow-hidden',
        expanded ? 'w-[260px]' : 'w-[60px]',
      ].join(' ')}
    >
      <div
        className={[
          'flex items-center h-16 shrink-0 border-b border-border',
          expanded ? 'justify-between px-3' : 'justify-center px-0',
        ].join(' ')}
      >
        {expanded && (
          <Link to="/" className="flex items-center gap-3 text-ink-1 px-1">
            <GridMark size={26} />
            <span className="text-sm font-medium tracking-tight whitespace-nowrap">
              Decade AI
            </span>
          </Link>
        )}
        <button
          onClick={onToggle}
          aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
          className="text-ink-3 hover:text-ink-1 p-2 transition-colors"
        >
          {expanded ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-4">
        {NAV_GROUPS.map((g, i) => (
          <NavGroupBlock key={g.label || `g${i}`} group={g} expanded={expanded} />
        ))}
        <ChatNavLink expanded={expanded} />
      </nav>

      <div className="px-3 py-3 border-t border-border shrink-0">
        {expanded ? (
          <div className="text-ink-4 text-[11px] leading-relaxed">
            Interview project · v0.6 · May 2026
          </div>
        ) : (
          <div className="text-ink-4 text-[10px] text-center">v0.6</div>
        )}
      </div>
    </aside>
  )
}

function NavGroupBlock({ group, expanded }: { group: typeof NAV_GROUPS[number]; expanded: boolean }) {
  const location = useLocation()
  const groupActive = group.items.some(it => location.pathname.startsWith(it.to))
  const [open, setOpen] = useState(group.caret ? groupActive || group.items.length <= 2 : true)

  useEffect(() => {
    if (groupActive) setOpen(true)
  }, [groupActive])

  if (!group.label) {
    return (
      <ul className="mb-2 space-y-px">
        {group.items.map(it => (
          <NavLeaf key={it.to} item={it} expanded={expanded} />
        ))}
      </ul>
    )
  }

  return (
    <div className="mb-1.5">
      {expanded ? (
        <button
          onClick={() => group.caret && setOpen(o => !o)}
          className="w-full flex items-center justify-between px-3 pt-3 pb-1.5 text-ink-3 text-[11px] uppercase tracking-tight font-medium hover:text-ink-2 transition-colors"
        >
          <span>{group.label}</span>
          {group.caret && (
            <ChevronDown
              size={12}
              className={`transition-transform duration-200 ease-decade ${open ? '' : '-rotate-90'}`}
            />
          )}
        </button>
      ) : (
        <div className="h-px bg-border mx-3 my-3" />
      )}
      {(open || !expanded) && (
        <ul className="space-y-px">
          {group.items.map(it => (
            <NavLeaf key={it.to} item={it} expanded={expanded} />
          ))}
        </ul>
      )}
    </div>
  )
}

function NavLeaf({ item, expanded }: { item: { to: string; label: string }; expanded: boolean }) {
  const location = useLocation()
  const active = location.pathname === item.to
  return (
    <li>
      <Link
        to={item.to}
        title={!expanded ? item.label : undefined}
        className={[
          'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150 ease-decade',
          active
            ? 'bg-surface-2 text-ink-1'
            : 'text-ink-2 hover:text-ink-1 hover:bg-surface',
        ].join(' ')}
      >
        <span
          className={[
            'h-1 w-1 rounded-full shrink-0 transition-colors',
            active ? 'bg-ink-1' : 'bg-ink-4',
          ].join(' ')}
        />
        {expanded && (
          <span className="truncate tracking-tight">{item.label}</span>
        )}
      </Link>
    </li>
  )
}

function ChatNavLink({ expanded }: { expanded: boolean }) {
  const location = useLocation()
  const active = location.pathname === '/chat'
  return (
    <div className="mt-6">
      {expanded && (
        <div className="px-3 pt-3 pb-1.5 text-ink-3 text-[11px] uppercase tracking-tight font-medium">
          Demo
        </div>
      )}
      {!expanded && <div className="h-px bg-border mx-3 my-3" />}
      <Link
        to="/chat"
        title={!expanded ? 'Chat (gated)' : undefined}
        className={[
          'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors duration-150 ease-decade',
          active
            ? 'bg-surface-2 text-ink-1'
            : 'text-ink-2 hover:text-ink-1 hover:bg-surface',
        ].join(' ')}
      >
        <Lock size={12} className="text-ink-3 shrink-0" />
        {expanded && <span className="truncate tracking-tight">Chat</span>}
      </Link>
    </div>
  )
}

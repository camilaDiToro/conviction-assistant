import { Link } from 'react-router-dom'
import { ArrowRight, ShieldAlert } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { GridMark } from '@/components/GridMark'
import { hasToken, saveToken } from '@/lib/access-gate'

interface AccessGateProps {
  children: ReactNode
}

export default function AccessGate({ children }: AccessGateProps) {
  const [unlocked, set] = useState<boolean>(hasToken)
  if (unlocked) return <>{children}</>
  return (
    <Locked
      onUnlock={token => {
        saveToken(token)
        set(true)
      }}
    />
  )
}

function Locked({ onUnlock }: { onUnlock: (token: string) => void }) {
  const [token, setToken] = useState('')
  const [error, setError] = useState<string | null>(null)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = token.trim()
    if (!trimmed) {
      setError('Token cannot be empty.')
      return
    }
    setError(null)
    onUnlock(trimmed)
  }

  return (
    <div className="min-h-screen flex flex-col bg-bg">
      <header className="px-6 md:px-10 py-6 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 text-ink-1">
          <GridMark size={26} />
          <span className="text-sm tracking-tight font-medium">Decade AI Challenge</span>
        </Link>
        <Link to="/design/overview" className="btn-ghost">
          Back to design
        </Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-6">
        <div className="w-full max-w-md border border-border bg-surface p-8 md:p-10 rounded-md animate-fade-in">
          <div className="pill mb-6 inline-flex">
            <ShieldAlert size={11} /> Access required
          </div>
          <h1 className="text-display-3 text-ink-1 mb-3 tracking-tight">Paste your chat token.</h1>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <label
                htmlFor="token"
                className="text-ink-3 text-xs uppercase tracking-tight block mb-2"
              >
                Chat access token
              </label>
              <input
                id="token"
                type="password"
                autoFocus
                autoComplete="off"
                value={token}
                onChange={e => setToken(e.target.value)}
                className="w-full bg-bg border border-border focus:border-ink-1 outline-none rounded-md px-4 py-3 text-ink-1 font-mono text-sm transition-colors"
                placeholder="paste token here"
              />
              {error && <p className="text-ink-2 text-xs mt-2">{error}</p>}
            </div>
            <button type="submit" className="btn-line w-full justify-center">
              Save and enter <ArrowRight size={14} />
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}

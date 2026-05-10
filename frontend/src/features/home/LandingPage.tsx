import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { GridMark } from '@/components/GridMark'

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-bg">
      {/* Header */}
      <header className="px-6 md:px-10 py-6 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 text-ink-1">
          <GridMark size={28} />
          <span className="text-sm tracking-tight font-medium">Decade AI Challenge</span>
        </Link>
        <nav className="flex items-center gap-2 md:gap-4 text-sm">
          <Link to="/design/overview" className="btn-ghost">Design</Link>
          <Link to="/chat" className="btn-line">
            Chat <ArrowRight size={14} />
          </Link>
        </nav>
      </header>

      {/* Hero */}
      <main className="flex-1 px-6 md:px-10 flex items-center">
        <div className="max-w-page mx-auto w-full py-16 md:py-28">
          <div className="pill mb-8">Interview deliverable · v0.6 · May 2026</div>
          <h1 className="text-display-1 text-ink-1 mb-6 max-w-[28ch] text-balance">
            A constrained agentic harness over a conviction corpus.
          </h1>
          <p className="text-ink-2 text-base md:text-lg leading-relaxed max-w-prose mb-10 text-balance">
            Inspired by Claude Code's "tools, not embeddings-as-the-retriever" philosophy.
            A deterministic substring verifier is the grounding guarantee — no provider's
            Citations API matches it.
          </p>

          <div className="flex flex-wrap items-center gap-4">
            <Link to="/design/overview" className="btn-line">
              Read the design <ArrowRight size={14} />
            </Link>
            <Link to="/chat" className="btn-ghost">
              Open chat <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-6 md:px-10 py-10 border-t border-border">
        <div className="max-w-page mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <GridMark size={20} />
            <span className="text-ink-3 text-sm">Decade AI Challenge — interview project</span>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2 text-ink-3 text-sm">
            <Link to="/design/overview" className="hover:text-ink-1 transition-colors">Architecture</Link>
            <Link to="/design/pipeline/verifier" className="hover:text-ink-1 transition-colors">Verifier</Link>
            <Link to="/chat" className="hover:text-ink-1 transition-colors">Chat</Link>
          </div>
        </div>
        <div className="max-w-page mx-auto mt-10 pt-10 border-t border-border text-ink-4 text-xs leading-relaxed max-w-prose">
          This is an interview project, not a product. The corpus is a synthetic set of
          investment-conviction documents. Nothing on this site is investment advice.
          Past performance does not guarantee future results.
        </div>
      </footer>
    </div>
  )
}

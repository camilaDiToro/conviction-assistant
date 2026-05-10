import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { GridMark } from '@/components/GridMark'

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col bg-bg">
      <header className="px-6 md:px-10 py-6 flex items-center">
        <Link to="/" className="flex items-center gap-3 text-ink-1">
          <GridMark size={28} />
          <span className="text-sm tracking-tight font-medium">Decade AI Challenge</span>
        </Link>
      </header>

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
    </div>
  )
}

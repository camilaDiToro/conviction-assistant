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
          <h1 className="text-display-1 text-ink-1 mb-6 max-w-[28ch] text-balance">
            An agentic assistant grounded on Decade's conviction corpus.
          </h1>
          <p className="text-ink-2 text-base md:text-lg leading-relaxed max-w-prose mb-10 text-balance">
            A bounded agent uses four read-only tools to explore the corpus, gather evidence,
            and produce a structured answer with exact citations into the source passages.
          </p>

          <div className="flex flex-wrap items-center gap-4">
            <Link to="/chat" className="btn-line">
              Open chat <ArrowRight size={14} />
            </Link>
            <Link to="/design/overview" className="btn-ghost">
              Read the design <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}

import { useMemo, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { resolve } from '@/lib/resolver'
import { EXAMPLE_PASSAGES } from '@/data/exampleConviction'

const TRIBUTACAO = EXAMPLE_PASSAGES.find(p => p.heading === 'Prazo Mínimo, Carência e Tributação')!

const PRESETS = [
  {
    label: 'Exact substring',
    quote: 'são isentas de Imposto de Renda para pessoas físicas nos rendimentos',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Smart quotes / em-dash',
    quote: '“são isentas de Imposto de Renda para pessoas físicas” – nos rendimentos',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Paraphrase (no match)',
    quote: 'are exempt from income tax for individuals',
    passage: TRIBUTACAO.text,
  },
] as const

export default function ResolverPage() {
  const [quote, setQuote] = useState<string>(PRESETS[0].quote)
  const [passage, setPassage] = useState<string>(PRESETS[0].passage)
  const [showResult, setShowResult] = useState(true)
  const result = useMemo(() => resolve(quote, passage), [quote, passage])

  return (
    <article>
      <PageHeader
        eyebrow="Pipeline · Resolver"
        title="It's just str.find."
        lead={
          <>
            <code className="font-mono text-[15px] text-ink-1">passage.find(quote)</code> →{' '}
            <code className="font-mono text-[15px] text-ink-1">(start, end)</code>. That's the
            algorithm.
          </>
        }
      />

      <Section eyebrow="The algorithm">
        <ol className="max-w-prose text-ink-2 text-[15px] leading-relaxed list-decimal pl-5 space-y-2">
          <li>
            Call <code className="font-mono text-[13px] text-ink-1">passage_text.find(quote)</code>.
            If it returns an index, you're done.
          </li>
          <li>
            Otherwise fold both sides 1-to-1 (curly quotes → straight,{' '}
            <code className="font-mono text-[13px] text-ink-1">–</code>{' '}
            <code className="font-mono text-[13px] text-ink-1">—</code> → ASCII hyphen, NBSP →
            space, then NFKC for the rest — only if it stays length-1). Call{' '}
            <code className="font-mono text-[13px] text-ink-1">find</code> again.
          </li>
          <li>
            Return <code className="font-mono text-[13px] text-ink-1">(start, end)</code> or{' '}
            <code className="font-mono text-[13px] text-ink-1">None</code>. The fold is
            length-preserving so the offsets index the <em>original</em> passage — no offset
            map needed.
          </li>
        </ol>
      </Section>

      <Section eyebrow="Try it">
        <div className="flex flex-wrap gap-2 mb-6">
          {PRESETS.map(p => (
            <button
              key={p.label}
              onClick={() => { setQuote(p.quote); setPassage(p.passage); setShowResult(true) }}
              className="pill hover:bg-surface-2 hover:text-ink-1 transition-colors"
            >
              {p.label}
            </button>
          ))}
          <button
            onClick={() => { setQuote(''); setPassage(''); setShowResult(false) }}
            className="pill hover:bg-surface-2 hover:text-ink-1 transition-colors flex items-center gap-1"
          >
            <RotateCcw size={11} /> Clear
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-border border border-border">
          <Editor label="Quote" value={quote} onChange={setQuote} placeholder="A verbatim substring of the passage." rows={5} />
          <Editor label="Passage" value={passage} onChange={setPassage} placeholder="The source passage." rows={10} />
        </div>

        {showResult && quote && passage && (
          <>
            <ResultBanner result={result} />
            <HighlightPreview passage={passage} result={result} />
          </>
        )}
      </Section>

      <Section eyebrow="The code">
        <CodeBlock
          lang="python"
          code={`def resolve_citation(quote: str, passage_text: str) -> tuple[int, int] | None:
    if not quote:
        return None
    idx = passage_text.find(quote)
    if idx != -1:
        return idx, idx + len(quote)
    norm_quote = _normalize(quote)
    norm_text = _normalize(passage_text)
    idx = norm_text.find(norm_quote)
    if idx == -1:
        return None
    return idx, idx + len(norm_quote)`}
        />
      </Section>

      <Section eyebrow="When it doesn't anchor">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Three outcomes, all non-rejecting — the citation still ships, the popup just shows
          the passage without a highlight:
        </p>
        <ul className="max-w-prose text-ink-2 text-[15px] leading-relaxed list-disc pl-5 space-y-1.5 mt-4">
          <li>
            <code className="font-mono text-[13px] text-ink-1">empty_quote</code> — the model
            returned a whitespace-only quote.
          </li>
          <li>
            <code className="font-mono text-[13px] text-ink-1">passage_not_found</code> — the
            cited passage id doesn't exist in the corpus.
          </li>
          <li>
            <code className="font-mono text-[13px] text-ink-1">offset_not_found</code> — the
            quote isn't a substring of the passage, even after the fold. Usually a paraphrase
            or a translation.
          </li>
        </ul>
      </Section>

    </article>
  )
}

function Editor({ label, value, onChange, placeholder, rows = 6 }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string; rows?: number }) {
  return (
    <div className="bg-bg p-4">
      <label className="text-ink-3 text-[10px] uppercase tracking-tight block mb-2">{label}</label>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="w-full bg-bg border border-border focus:border-ink-1 outline-none rounded p-3 text-ink-1 text-[13px] font-mono leading-relaxed resize-y transition-colors"
      />
    </div>
  )
}

function ResultBanner({ result }: { result: ReturnType<typeof resolve> }) {
  const failureCopy: Record<string, string> = {
    empty_quote: 'Quote is empty. Citation ships with no highlight.',
    offset_not_found:
      'Quote is not a substring of the passage. Citation ships with no highlight.',
  }
  return (
    <div
      className={[
        'mt-6 p-5 border rounded-md flex items-start gap-4 animate-fade-in',
        result.anchored ? 'border-ink-1' : 'border-ink-1 border-dashed',
      ].join(' ')}
    >
      <div className="text-ink-1 text-xl font-medium shrink-0 leading-none mt-0.5">
        {result.anchored ? '✓' : '○'}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-ink-1 font-medium text-base tracking-tight mb-1">
          {result.anchored
            ? `Anchored at (${result.start}, ${result.end})`
            : 'No anchor'}
        </div>
        <p className="text-ink-2 leading-relaxed text-[15px]">
          {result.anchored
            ? 'The popup will highlight this span.'
            : failureCopy[result.failureReason ?? 'offset_not_found']}
        </p>
      </div>
    </div>
  )
}

function HighlightPreview({ passage, result }: { passage: string; result: ReturnType<typeof resolve> }) {
  return (
    <div className="mt-6 bg-surface border border-border rounded p-5">
      <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-3">
        Passage as the popup would render it
      </div>
      <div className="font-mono text-[13px] text-ink-2 leading-relaxed whitespace-pre-wrap">
        {result.anchored && result.start !== null && result.end !== null ? (
          <>
            {passage.slice(0, result.start)}
            <mark className="bg-ink-1 text-bg px-0.5 rounded-sm">
              {passage.slice(result.start, result.end)}
            </mark>
            {passage.slice(result.end)}
          </>
        ) : (
          passage
        )}
      </div>
    </div>
  )
}

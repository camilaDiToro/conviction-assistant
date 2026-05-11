import { useMemo, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'
import { resolve } from '@/lib/resolver'
import { EXAMPLE_PASSAGES } from '@/data/exampleConviction'

const TRIBUTACAO = EXAMPLE_PASSAGES.find(p => p.heading === 'Prazo Mínimo, Carência e Tributação')!

const PRESETS = [
  {
    label: 'Literal substring · ANCHORS',
    quote: 'são isentas de Imposto de Renda para pessoas físicas nos rendimentos',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Smart quotes · NO ANCHOR',
    quote: '“são isentas de Imposto de Renda para pessoas físicas” — nos rendimentos',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Paraphrase · NO ANCHOR',
    quote: 'are exempt from income tax for individuals',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Whitespace mangled · NO ANCHOR',
    quote: '   prazo  mínimo  de\n carência   de  120 dias  ',
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
        title="Deterministic offset grounding."
        lead={
          <>
            Every cited quote is resolved to a literal{' '}
            <code className="font-mono text-[15px] text-ink-1">(start, end)</code> region of the
            cited passage. No normalization, no edit distance, no LLM-as-judge — just{' '}
            <code className="font-mono text-[15px] text-ink-1">passage_text.find(quote)</code>.
            Citations that don't anchor still ship; the popup shows the passage with no
            highlight.
          </>
        }
      />

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          The agent emits an answer with citations (passage_id + verbatim quote). The reader
          needs to see exactly which span of the source passage was cited. The system needs
          this offset deterministically — independent of the model — so the popup can
          highlight it and an analyst can verify each claim by eye.
        </p>
      </Section>

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="Deterministic">
            Pure function: same inputs, same offsets. No model in the loop. Lives in{' '}
            <code className="font-mono text-[13px] text-ink-1">app/agent/resolver/substring.py</code>{' '}
            — no DB, no session, no I/O.
          </SpecItem>
          <SpecItem term="Fidelity-preserving">
            The passage stored in the DB is what the agent reads via{' '}
            <code className="font-mono text-[13px] text-ink-1">read_passage</code> — verbatim,
            diacritics intact. The model copies its quote from that read, so a literal
            substring search anchors in practice.
          </SpecItem>
          <SpecItem term="Non-rejecting">
            A citation that does not anchor is{' '}
            <strong className="text-ink-1">not</strong> removed from the response. It surfaces
            with <code className="font-mono text-[13px] text-ink-1">start</code> /
            <code className="font-mono text-[13px] text-ink-1">end</code> set to{' '}
            <code className="font-mono text-[13px] text-ink-1">null</code> and the popup shows
            the passage without a highlight. The agent loop does <em>not</em> retry.
          </SpecItem>
          <SpecItem term="Drops the literal quote">
            Only <code className="font-mono text-[13px] text-ink-1">(passage_id, start, end)</code>{' '}
            survives into the wire response. The model's verbatim quote is consumed during
            resolution and discarded — the popup renders the highlight from passage offsets,
            not from the quote string.
          </SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Two functions; together they fit on a page.
        </p>
        <CodeBlock
          lang="python"
          code={`# app/agent/resolver/substring.py

def resolve_citation(quote: str, passage_text: str) -> tuple[int, int] | None:
    """Literal substring search. Half-open: passage_text[start:end] == quote."""
    if not quote:
        return None
    idx = passage_text.find(quote)
    if idx == -1:
        return None
    return idx, idx + len(quote)


def resolve_answer(answer: AnswerOutput, passages: dict[str, Passage]) -> OffsetResolution:
    """Resolve every citation against the passage map.

    failure_reason:
      'empty_quote'       — quote is whitespace-only
      'passage_not_found' — passage_id missing from the map
      'offset_not_found'  — quote is not a literal substring of the passage
    """`}
        />
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mt-6">
          The orchestrator's adapter (
          <code className="font-mono text-[13px] text-ink-1">app/agent/audit.py::resolve_output</code>)
          fetches the cited passages and hands them to the pure resolver. The resolver itself
          owns no I/O — the boundary is deliberate so the resolver is trivial to unit-test.
        </p>
      </Section>

      <Section eyebrow="Live example">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Four presets show why "literal" matters: only an exact substring anchors. Smart
          quotes, paraphrase, and mangled whitespace all fail to anchor — those citations
          would still ship, but the popup would render the passage without a highlight.
        </p>

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
          <Editor label="Quote (the cited claim)" value={quote} onChange={setQuote} placeholder="Paste a verbatim substring of the passage." rows={5} />
          <Editor label="Passage (the source)" value={passage} onChange={setPassage} placeholder="Paste a passage body." rows={10} />
        </div>

        {showResult && quote && passage && (
          <>
            <ResultBanner result={result} />
            <HighlightPreview passage={passage} result={result} />
          </>
        )}
      </Section>

      <Section eyebrow="Contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Defined in <code className="font-mono text-[13px] text-ink-1">app/agent/resolver/base.py</code>.
          One <code className="font-mono text-[13px] text-ink-1">CitationResolution</code> per
          model citation, in input order.
        </p>
        <CodeBlock
          lang="python"
          code={`class CitationResolution(BaseModel):
    passage_id: str
    document_id: str | None
    document_title: str | None
    heading_path: list[str]
    passage_text: str | None         # carried so the popup needs no extra round-trip
    start: int | None = None         # set when the quote anchored
    end: int | None = None
    failure_reason: Literal["empty_quote", "passage_not_found", "offset_not_found"] | None = None


class OffsetResolution(BaseModel):
    entries: list[CitationResolution]

    @property
    def all_anchored(self) -> bool:
        return all(e.failure_reason is None for e in self.entries)`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Paraphrase">
            <code className="font-mono text-[13px] text-ink-1">failure_reason = 'offset_not_found'</code>.
            Citation still ships, popup shows the passage without a highlight. The reader can
            still inspect the source.
          </SpecItem>
          <SpecItem term="Translation">
            Same outcome as paraphrase. A quote in EN over a PT passage will not anchor; the
            citation surfaces without highlight rather than disappearing.
          </SpecItem>
          <SpecItem term="Smart quotes / NBSP / dash variants">
            Treated as a non-match — the resolver does no cosmetic normalization. In practice
            the model copies from <code className="font-mono text-[13px] text-ink-1">read_passage</code>,
            which returns DB-stored text verbatim, so these cases are vanishingly rare.
          </SpecItem>
          <SpecItem term="Empty / whitespace quote">
            <code className="font-mono text-[13px] text-ink-1">failure_reason = 'empty_quote'</code>.
            Same non-rejecting treatment.
          </SpecItem>
          <SpecItem term="Unknown passage_id">
            <code className="font-mono text-[13px] text-ink-1">failure_reason = 'passage_not_found'</code>.
            The popup falls back to the passage_id only — no passage text to render.
          </SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Trade-offs and alternatives considered">
        <SpecList>
          <SpecItem term="Normalize cosmetic differences (smart quotes, dashes, NBSP)">
            Rejected. Would require maintaining an index map from normalized offsets back to
            the original passage so the popup highlight stays correct, for a class of failures
            that essentially never appears once the model copies from{' '}
            <code className="font-mono text-[13px] text-ink-1">read_passage</code>. Net cost
            beats net benefit.
          </SpecItem>
          <SpecItem term="LLM-as-judge entailment">
            Rejected for grounding. Introduces a non-deterministic dependency on the very
            layer we are checking. May surface later as an eval-time secondary metric.
          </SpecItem>
          <SpecItem term="Fuzzy / Levenshtein matching">
            Rejected. Almost-matches fail silently and are more dangerous than a clean
            non-anchor.
          </SpecItem>
          <SpecItem term="Reject and retry on non-anchor">
            Rejected. Reading{' '}
            <code className="font-mono text-[13px] text-ink-1">read_passage</code> first and
            then copying makes failures rare; the cost of a retry round-trip outweighs the
            marginal recall gain. Non-anchoring citations surviving without highlight is the
            chosen graceful degradation.
          </SpecItem>
          <SpecItem term="Provider-native Citations APIs (Anthropic / OpenAI)">
            Rejected as the architecture. Semantics differ across providers; output is not
            portable. May live behind adapters as optimizations; the offset contract above
            sits unchanged.
          </SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Evaluation">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          <strong className="text-ink-1">Anchor rate</strong> — the percentage of citations
          whose quote resolved to a passage offset — is the headline metric on the eval suite
          (~30 hand-written Q/A). Other metrics (retrieval recall, answer relevance) are
          complementary; they do not replace anchor rate as the gate.
        </p>
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
    empty_quote: 'Quote is empty or whitespace-only. Citation surfaces with no highlight.',
    offset_not_found:
      'Quote is not a literal substring of the passage. Citation still ships; popup shows the passage with no highlight (offsets are null).',
  }
  return (
    <div
      className={[
        'mt-6 p-6 border rounded-md flex items-start gap-4 animate-fade-in',
        result.anchored ? 'border-ink-1' : 'border-ink-1 border-dashed',
      ].join(' ')}
    >
      <div className="text-ink-1 text-xl font-medium shrink-0 leading-none mt-0.5">
        {result.anchored ? '✓' : '○'}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-ink-1 font-medium text-base tracking-tight mb-1">
          {result.anchored
            ? `ANCHORS · offsets (${result.start}, ${result.end})`
            : 'NO ANCHOR · citation still ships'}
        </div>
        <p className="text-ink-2 leading-relaxed text-[15px]">
          {result.anchored
            ? 'Quote resolved to a literal region of the passage. The popup will highlight this span.'
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

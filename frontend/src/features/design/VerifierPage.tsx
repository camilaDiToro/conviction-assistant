import { useMemo, useState } from 'react'
import { Play, RotateCcw } from 'lucide-react'
import { PageHeader, Section } from '@/components/Section'
import { Callout } from '@/components/Callout'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'
import { verify } from '@/lib/verifier'
import { EXAMPLE_PASSAGES } from '@/data/exampleConviction'

const TRIBUTACAO = EXAMPLE_PASSAGES.find(p => p.heading === 'Prazo Mínimo, Carência e Tributação')!

const PRESETS = [
  {
    label: 'Exact substring · PASS',
    quote: 'são isentas de Imposto de Renda para pessoas físicas nos rendimentos',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Smart quotes + en-dash · PASS',
    quote: '“são isentas de Imposto de Renda para pessoas físicas” — nos rendimentos',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Paraphrase · FAIL',
    quote: 'are exempt from income tax for individuals',
    passage: TRIBUTACAO.text,
  },
  {
    label: 'Whitespace mangled · PASS',
    quote: '   prazo  mínimo  de\n carência   de  120 dias  ',
    passage: TRIBUTACAO.text,
  },
] as const

export default function VerifierPage() {
  const [quote, setQuote] = useState<string>(PRESETS[0].quote)
  const [passage, setPassage] = useState<string>(PRESETS[0].passage)
  const [showResult, setShowResult] = useState(true)
  const result = useMemo(() => verify(quote, passage), [quote, passage])

  return (
    <article>
      <PageHeader
        eyebrow="Pipeline · Verifier"
        title="Substring grounding."
        lead={
          <>
            A deterministic check: every cited quote must be a substring of its claimed source
            passage after a pinned normalization pipeline. No edit-distance, no semantic
            entailment, no LLM-as-judge in the request path.
          </>
        }
      />

      <Callout label="Designed; ships in B7" tone="pending">
        The TS implementation in{' '}
        <code className="font-mono text-[13px] text-ink-1">frontend/src/lib/verifier.ts</code>{' '}
        is the executable specification on this page. The production verifier ships at{' '}
        <code className="font-mono text-[13px] text-ink-1">app/verifier/normalize.py</code> +{' '}
        <code className="font-mono text-[13px] text-ink-1">app/verifier/substring.py</code>.
        The two implementations must move together; B7 includes a CI check that diffs the
        normalization tables.
      </Callout>

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          The agent emits answers with citations — passage_id plus quote. A reader must be
          able to take a citation, retrieve the passage, and find the quoted text inside it.
          Anything that does not satisfy that invariant — a paraphrase, a translation, a
          hallucinated quote — must be detected and either retried or stripped before the
          response leaves the boundary.
        </p>
      </Section>

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="Deterministic">Same inputs, same verdict. No model in the loop. The reasoning behind a failure is also deterministic, which makes the retry path tractable.</SpecItem>
          <SpecItem term="Fidelity-preserving">Diacritics, accents, case, and punctuation in the cited form must round-trip. This is the opposite of the BM25 layer, which strips diacritics for recall.</SpecItem>
          <SpecItem term="Bounded retry">One re-prompt with the verifier's exact failure reason. A second failure causes the offending claim to be stripped or the answer to become a safe refusal.</SpecItem>
          <SpecItem term="Pinned">Any change to the normalization pipeline is a coordinated edit in the Python and TS implementations and requires a bump to the eval baseline.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          A six-step normalization is applied identically to the cited quote and the source
          passage. The check is a substring containment.
        </p>
        <CodeBlock
          lang="ts"
          code={`function normalizeForVerify(text: string): string {
  return text
    .normalize('NFC')                                      // 1. canonical composition
    .replace(/[\\u00AD\\u200B-\\u200D\\uFEFF]/g, '')              // 2. strip zero-width / soft-hyphen
    .replace(/[\\u201C\\u201D\\u201E\\u201F\\u2033\\u2036]/g, '"') // 3. fold smart double quotes
    .replace(/[\\u2018\\u2019\\u201A\\u201B\\u2032\\u2035]/g, "'") // 3. fold smart single quotes
    .replace(/[\\u2010-\\u2015\\u2212]/g, '-')                    // 4. normalize dashes / minus
    .replace(/\\s+/g, ' ')                                  // 5. collapse whitespace
    .trim()                                                // 6. trim
}

function verify(quote: string, passage_text: string): boolean {
  return normalizeForVerify(passage_text)
    .includes(normalizeForVerify(quote))
}`}
        />
      </Section>

      <Section eyebrow="Reproducible reference implementation">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The four presets exercise the surface explicitly: an exact substring, a quote with
          smart quotes and an en-dash, a paraphrase, and a whitespace-mangled quote. The first,
          second, and fourth pass; the third fails.
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
          <Editor label="Quote (the cited claim)" value={quote} onChange={setQuote} placeholder="Paste an exact substring of the passage." rows={5} />
          <Editor label="Passage (the source)" value={passage} onChange={setPassage} placeholder="Paste a passage body." rows={10} />
        </div>

        <div className="mt-6">
          <button
            onClick={() => setShowResult(true)}
            disabled={!quote || !passage}
            className="btn-line disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play size={14} /> Run verify
          </button>
        </div>

        {showResult && quote && passage && (
          <>
            <ResultBanner result={result} />
            <NormalizedView quote={result.normalizedQuote} passage={result.normalizedPassage} />
          </>
        )}
      </Section>

      <Section eyebrow="Contract">
        <CodeBlock
          lang="python"
          code={`# app/verifier/substring.py (B7)
def verify(quote: str, passage_text: str) -> VerifyResult: ...

@dataclass(frozen=True)
class VerifyResult:
    passed: bool
    normalized_quote: str
    normalized_passage: str
    reason: str   # filled on failure with the exact message used in the retry prompt`}
        />
      </Section>

      <Section eyebrow="Retry path">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The orchestrator runs <code className="font-mono text-[13px] text-ink-1">verify</code> on
          every citation in the answer. If any fail, the failure reasons are appended as a
          user-role message and the agent is re-invoked once. A second failure terminates the
          retry budget; the orchestrator strips the failing claim or returns a safe refusal.
        </p>
        <CodeBlock
          lang="text"
          code={`agent.act() → answer with citations c1, c2
    │
verify(c1) → PASS
verify(c2) → FAIL  reason="quote not a substring of passage_id ..."
    │
agent.act_again(feedback=<reason>)   ← retry budget = 1
    │
verify(c2') → PASS  → ship answer
    │
    └─ FAIL → strip(c2) OR safe_refuse()`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Paraphrase">Rejected. The quote is in a different language or rewording. There is no edit-distance fallback.</SpecItem>
          <SpecItem term="Translation">Rejected. Quotes round-trip in the source language; an EN translation of a PT passage does not verify.</SpecItem>
          <SpecItem term="Whitespace-only quote">Empty after trim. Treated as failure with reason "empty quote".</SpecItem>
          <SpecItem term="Too-short quote">Currently no minimum length. A one-word quote may match incidentally. Documented; B7 may add a min-length floor (e.g., 8 characters or 3 tokens).</SpecItem>
          <SpecItem term="Unknown passage_id"><code className="font-mono text-[13px] text-ink-1">read_passage</code> raises <code className="font-mono text-[13px] text-ink-1">PassageNotFoundError</code>; the orchestrator treats this as a verify failure of the same retry-budget category.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Trade-offs and alternatives considered">
        <SpecList>
          <SpecItem term="LLM-as-judge entailment">Rejected for grounding (introduces a non-deterministic dependency on the very layer we are checking). Kept as a <em>secondary</em> eval-time metric in B10, where determinism is less important than coverage.</SpecItem>
          <SpecItem term="Fuzzy / Levenshtein matching">Rejected. Citations are exact or wrong; an "almost there" match is more dangerous than a clear failure because it fails silently.</SpecItem>
          <SpecItem term="Provider-native Citations APIs">Rejected as the architecture. Anthropic's and OpenAI's grounding mechanisms differ in semantics and produce non-portable output. They may live behind adapters as optimizations; the substring contract sits above them.</SpecItem>
          <SpecItem term="Cosine similarity over embeddings">Rejected. Higher recall, lower precision, and not deterministic across embedding-model versions. Not a grounding tool.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Evaluation">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Verifier-pass-rate is the headline metric on the eval suite (~30 hand-written Q/A,
          ships in B10). Today it is described, not measured. LLM-judge entailment runs as a
          secondary metric to detect cases where the verifier passes but the cited quote is
          genuinely off-topic (a contained-but-irrelevant fragment).
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

function ResultBanner({ result }: { result: ReturnType<typeof verify> }) {
  return (
    <div
      className={[
        'mt-6 p-6 border rounded-md flex items-start gap-4 animate-fade-in',
        result.passed ? 'border-ink-1' : 'border-ink-1 border-dashed',
      ].join(' ')}
    >
      <div className="text-ink-1 text-xl font-medium shrink-0 leading-none mt-0.5">
        {result.passed ? '✓' : '✗'}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-ink-1 font-medium text-base tracking-tight mb-1">
          {result.passed ? 'PASS' : 'FAIL'}
        </div>
        <p className="text-ink-2 leading-relaxed text-[15px]">{result.reason}</p>
      </div>
    </div>
  )
}

function NormalizedView({ quote, passage }: { quote: string; passage: string }) {
  return (
    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-px bg-border border border-border">
      <div className="bg-bg p-4">
        <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-2">Normalized quote</div>
        <div className="font-mono text-[13px] text-ink-1 break-words leading-relaxed">{quote || <em className="text-ink-3 not-italic">(empty)</em>}</div>
      </div>
      <div className="bg-bg p-4">
        <div className="text-ink-3 text-[10px] uppercase tracking-tight mb-2">Normalized passage</div>
        <div className="font-mono text-[13px] text-ink-1 break-words leading-relaxed line-clamp-6">{passage || <em className="text-ink-3 not-italic">(empty)</em>}</div>
      </div>
    </div>
  )
}

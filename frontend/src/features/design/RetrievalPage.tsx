import { useMemo, useState } from 'react'
import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'
import { BM25, normalizeForSearch, tokenize } from '@/lib/bm25'
import { EXAMPLE_PASSAGES } from '@/data/exampleConviction'
import type { Passage } from '@/lib/types'

const CORPUS_DOCS: Array<{ doc: Passage; text: string }> = EXAMPLE_PASSAGES.map(p => ({
  doc: p,
  text: `${p.heading} ${p.text}`,
}))

const PRESET_QUERIES = [
  'LCI tributação isenção IR',
  'FGC limite garantia',
  'IPCA prefixada CDI indexador',
  'liquidez mercado secundário',
  'tax exemption LCI',
]

export default function RetrievalPage() {
  const index = useMemo(() => new BM25(CORPUS_DOCS), [])
  const [query, setQuery] = useState(PRESET_QUERIES[0])
  const queryTokens = useMemo(() => tokenize(query), [query])
  const hits = useMemo(() => index.search(query, 5), [index, query])

  return (
    <article>
      <PageHeader
        eyebrow="Pipeline · Retrieval"
        title="BM25 over the corpus."
        lead={
          <>
            In-memory BM25 ranking via the <code className="font-mono text-[15px] text-ink-1">bm25s</code>{' '}
            library. Built at lifespan, rebuilt after ingest.
          </>
        }
      />

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Given a free-text query in the user's language, return the top-{`k`} passages most
          likely to contain the answer. The result is a starting point: the agent reads the
          full text of any hit it intends to cite via <code className="font-mono text-[13px] text-ink-1">read_passage</code>.
        </p>
      </Section>

      <Section eyebrow="Why BM25">
        <div className="max-w-prose space-y-4 text-ink-2 text-[15px] leading-relaxed">
          <p>
            For a corpus of this size (~30 documents, a few hundred passages), BM25 has the
            right cost/benefit: deterministic, no embedding provider, no GPU, no per-query API
            cost. Dense retrieval's complexity scales with corpus size — at small scale, a
            well-normalized lexical retriever is typically competitive while being far simpler
            to operate, debug, and reason about.
          </p>
          <p>
            There's also a domain match. Convictions are financial documents (Brazilian fixed
            income, equities, taxation, funds, ESG) — full of precise terms, codes, and proper
            nouns like <code className="font-mono text-[13px] text-ink-1">FGC</code>,{' '}
            <code className="font-mono text-[13px] text-ink-1">LCI</code>,{' '}
            <code className="font-mono text-[13px] text-ink-1">IPCA</code>,{' '}
            <em>tabela regressiva</em>. Akarsu, Karaman &amp; Mierbach benchmark retrieval
            strategies on financial text-and-table corpora and conclude that{' '}
            <strong className="text-ink-1">
              BM25 outperforms state-of-the-art dense retrieval on financial documents
            </strong>
            . See{' '}
            <a
              href="https://arxiv.org/abs/2604.01733"
              target="_blank"
              rel="noopener noreferrer"
              className="text-ink-1 underline underline-offset-2 hover:text-ink-1/80"
            >
              "From BM25 to Corrective RAG: Benchmarking Retrieval Strategies for Text-and-Table
              Documents"
            </a>{' '}
            (arXiv:2604.01733).
          </p>
          <p>
            This matches the spirit of the challenge: ship a working assistant grounded on the
            corpus we actually have, not the one we imagine in two years.
          </p>
        </div>
      </Section>

      <Section eyebrow="Live example">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Below is BM25 running live over a 9-passage subset of the corpus (the LCI/LCA
          document). Try the Portuguese preset queries to see the right passage returned at
          rank 1, or type your own and watch how the normalized query, tokens, and scores
          update.
        </p>

        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="LCI tributação isenção IR"
          className="w-full bg-surface border border-border focus:border-ink-1 outline-none rounded-md px-5 py-4 text-ink-1 text-base font-mono transition-colors"
        />
        <div className="flex flex-wrap gap-2 mt-3 mb-6">
          {PRESET_QUERIES.map(q => (
            <button
              key={q}
              onClick={() => setQuery(q)}
              className="pill hover:bg-surface-2 hover:text-ink-1 transition-colors font-mono"
            >
              {q}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-px bg-border border border-border">
          <aside className="bg-bg p-5">
            <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Normalized query</div>
            <code className="font-mono text-[13px] text-ink-1 break-words">
              {normalizeForSearch(query) || <em className="text-ink-3 not-italic">(empty)</em>}
            </code>
            <div className="mt-5 text-ink-3 text-[11px] uppercase tracking-tight mb-2">Tokens · {queryTokens.length}</div>
            <div className="flex flex-wrap gap-1.5">
              {queryTokens.length ? queryTokens.map((t, i) => (
                <span key={i} className="font-mono text-[11px] text-ink-1 bg-surface-2 px-2 py-0.5 rounded">{t}</span>
              )) : <span className="text-ink-3 text-xs italic">no tokens</span>}
            </div>
          </aside>

          <div className="bg-bg p-5">
            <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">
              Top {hits.length} of 9 passages
            </div>
            {hits.length === 0 ? (
              <p className="text-ink-3 text-sm italic">No passage contains any of those tokens.</p>
            ) : (
              <ol className="space-y-3">
                {hits.map((h, i) => (
                  <li key={h.doc.id} className="border border-border bg-surface p-4 rounded">
                    <div className="flex items-baseline justify-between gap-3 mb-2">
                      <div className="flex items-baseline gap-3 min-w-0">
                        <span className="text-ink-3 font-mono text-[10px]">#{i + 1}</span>
                        <code className="font-mono text-[11px] text-ink-1 truncate">{h.doc.id}</code>
                      </div>
                      <span className="text-ink-3 font-mono text-[11px] shrink-0">score {h.score.toFixed(2)}</span>
                    </div>
                    <div className="text-ink-1 font-medium text-sm tracking-tight mb-1.5">{h.doc.heading}</div>
                    <p className="text-ink-2 text-sm leading-relaxed line-clamp-2">{h.doc.text}</p>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {[...h.matchedTokens].map(t => (
                        <span key={t} className="font-mono text-[10px] text-bg bg-ink-1 px-1.5 py-0.5 rounded">{t}</span>
                      ))}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      </Section>

      <Section eyebrow="Normalization (recall layer)">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Applied identically to indexed passages and incoming queries.
        </p>
        <CodeBlock
          lang="python"
          code={`def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(
        ch for ch in decomposed
        if not unicodedata.combining(ch)
    )
    return _WHITESPACE_RE.sub(" ", no_accents.lower()).strip()`}
        />
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mt-4">
          Tokenization uses <code className="font-mono text-[13px] text-ink-1">bm25s.tokenize</code>{' '}
          defaults: regex split on <code className="font-mono text-[13px] text-ink-1">\W+</code>,
          no stopwords, no stemmer. Snippets (in{' '}
          <code className="font-mono text-[13px] text-ink-1">app/retrieval/snippet.py::make_snippet</code>)
          cut at the last word boundary and append <code className="font-mono text-[13px] text-ink-1">…</code>{' '}
          — strategy-agnostic so a future hybrid retriever reuses it.
        </p>
      </Section>

      <Section eyebrow="Contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          <code className="font-mono text-[13px] text-ink-1">search_convictions</code> returns
          a list of <code className="font-mono text-[13px] text-ink-1">PassageHit</code> from{' '}
          <code className="font-mono text-[13px] text-ink-1">app/schemas/passage.py</code>.
        </p>
        <CodeBlock
          lang="python"
          code={`class PassageHit(BaseModel):
    passage_id: str
    score: float
    document_id: str
    document_title: str
    heading_path: list[str]
    snippet: str               # ~200 chars, word-boundary cut, "…" suffix`}
        />
      </Section>

      <Section eyebrow="How this scales">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          BM25 doesn't fail because of corpus size — it fails because query vocabulary stops
          matching document vocabulary. Compute and memory are not the bottleneck until very
          large N. The right level-up depends on{' '}
          <em>which failure your eval is reporting</em>, not on a doc count. Symptom → fix,
          ordered by what typically breaks first and what's cheapest to add.
        </p>
        <SpecList>
          <SpecItem term="Right passage ranked too low (top-20 but not top-5)">
            The most common first failure. BM25 found the relevant passage but other passages
            with similar token frequencies outranked it.{' '}
            <strong className="text-ink-1">Fix: cross-encoder reranker</strong> over BM25's
            top-50. Wraps <code className="font-mono text-[13px] text-ink-1">.search()</code>{' '}
            results; the <code className="font-mono text-[13px] text-ink-1">Retriever</code>{' '}
            Protocol and <code className="font-mono text-[13px] text-ink-1">PassageHit</code>{' '}
            schema don't change. ~50–200 ms in CPU. Reversible.
          </SpecItem>
          <SpecItem term="Score-driven false positives in top-5">
            Passages that incidentally repeat the query's terms in irrelevant context. Same
            fix as above — the reranker catches both.
          </SpecItem>
          <SpecItem term="Right passage not in top-50 (recall fail)">
            Query uses different words than the doc. Two paths, cheapest first.{' '}
            <strong className="text-ink-1">Fix A: synonym expansion</strong> — a static map (
            <code className="font-mono text-[13px] text-ink-1">renda variável → ações | equities</code>
            ) or an LLM call before search. Cheap, works well in domains with stable jargon.{' '}
            <strong className="text-ink-1">Fix B: hybrid retrieval</strong> — BM25 + dense
            embeddings + Reciprocal Rank Fusion. A new file under{' '}
            <code className="font-mono text-[13px] text-ink-1">app/retrieval/</code>, registered
            in <code className="font-mono text-[13px] text-ink-1">registry.py</code>. Call
            sites don't change.
          </SpecItem>
          <SpecItem term="Cross-language queries fail">
            EN query, PT corpus (or any cross-lingual pair). Diacritic-folding doesn't bridge
            languages. <strong className="text-ink-1">Fix: hybrid with multilingual dense</strong>{' '}
            (e.g. <code className="font-mono text-[13px] text-ink-1">multilingual-e5</code> or{' '}
            <code className="font-mono text-[13px] text-ink-1">bge-m3</code>). Synonyms don't
            help here.
          </SpecItem>
          <SpecItem term="Latency or memory becomes the bottleneck">
            Only at hundreds of thousands of passages or more. BM25 itself stays fast longer
            than people expect.{' '}
            <strong className="text-ink-1">Fix: persistent search engine</strong> (Tantivy,
            Lucene) for the lexical side;{' '}
            <strong className="text-ink-1">ANN</strong> (HNSW / IVF, in pgvector or Qdrant) for
            the dense side. Two-stage retrieval — cheap recall, expensive rerank — becomes
            mandatory at this point.
          </SpecItem>
        </SpecList>
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mt-6">
          The prerequisite for all of the above is{' '}
          <strong className="text-ink-1">an eval set</strong> (~30–100 hand-curated queries
          with expected passage IDs, scored by{' '}
          <code className="font-mono text-[13px] text-ink-1">recall@K</code> and MRR). Today:{' '}
          <code className="font-mono text-[13px] text-ink-1">tests/eval/</code> with 29 cases.
          Without it every "level-up" is guesswork; with it, the highest-leverage fix is
          obvious from the failure breakdown.
        </p>
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mt-6">
          Size is a weak proxy: a homogeneous 5k-doc corpus with stable jargon often outlasts a
          heterogeneous 50-doc one. Standard "hybrid at 1k docs" rules of thumb are empirical
          averages, not laws — let the eval decide.
        </p>
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mt-6">
          The finance-domain twist: precise vocabulary (codes, indices, tax tables) favors
          lexical matching over semantic embeddings, which flatten exactly the distinctions that
          grounded citations need to preserve. These thresholds are conservative for this
          domain — BM25 likely stays competitive further than for a generic prose corpus.
        </p>
      </Section>
    </article>
  )
}

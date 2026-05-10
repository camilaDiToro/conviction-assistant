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
            library. Built at lifespan, rebuilt after ingest. v1 is BM25-only; the hybrid
            level-up (BM25 + multilingual embeddings + RRF) is documented and gated on a
            cross-language evaluation failure.
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

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="Corpus size">30 documents, ~400 passages today. Index fits in memory by an order of magnitude.</SpecItem>
          <SpecItem term="Languages">PT primary, EN secondary, ES queries possible. Diacritic-folding at the search layer is required for recall.</SpecItem>
          <SpecItem term="Build cadence">Index built at startup from <code className="font-mono text-[13px] text-ink-1">passages_repo.iter_all</code>; rebuilt at the end of <code className="font-mono text-[13px] text-ink-1">POST /admin/ingest</code>. No incremental updates.</SpecItem>
          <SpecItem term="Single process">FastAPI runs in one process today. No cross-replica index synchronization.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <div className="max-w-prose space-y-4 text-ink-2 text-[15px] leading-relaxed">
          <p>
            <code className="font-mono text-[13px] text-ink-1">app/services/search.py::BM25Index</code>{' '}
            wraps the <code className="font-mono text-[13px] text-ink-1">bm25s</code> library.{' '}
            <code className="font-mono text-[13px] text-ink-1">build(session)</code> loads all
            passages, normalizes their text, and builds the retriever.{' '}
            <code className="font-mono text-[13px] text-ink-1">search(query, k)</code> normalizes
            the query the same way and returns the top-<code className="font-mono text-[13px] text-ink-1">k</code> (passage,
            score) pairs.
          </p>
          <p>
            The lifespan in <code className="font-mono text-[13px] text-ink-1">app/main.py::lifespan</code>{' '}
            instantiates the index, calls <code className="font-mono text-[13px] text-ink-1">build</code>,
            and stores it on <code className="font-mono text-[13px] text-ink-1">app.state.search_index</code>.
            The admin route in <code className="font-mono text-[13px] text-ink-1">app/api/admin.py</code>{' '}
            calls <code className="font-mono text-[13px] text-ink-1">rebuild</code> after the
            ingest service finishes upserts.
          </p>
        </div>
      </Section>

      <Section eyebrow="Reproducible reference implementation">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The TS implementation in <code className="font-mono text-[13px] text-ink-1">frontend/src/lib/bm25.ts</code>{' '}
          mirrors <code className="font-mono text-[13px] text-ink-1">app/services/search.py::_normalize</code>{' '}
          and the <code className="font-mono text-[13px] text-ink-1">bm25s</code> tokenization defaults. It runs over a
          9-passage subset of the corpus (the LCI/LCA document) so a reader can verify the
          algorithm in the browser. The Portuguese preset queries return the right passage at
          rank 1; the English query "tax exemption LCI" demonstrates the cross-language failure
          mode that motivates the hybrid level-up.
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
          no stopwords, no stemmer. Snippets returned by{' '}
          <code className="font-mono text-[13px] text-ink-1">_make_snippet(text, max_chars=200)</code>{' '}
          cut at the last word boundary and append <code className="font-mono text-[13px] text-ink-1">…</code>.
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
    snippet: str               # ~200 chars, word-boundary cut, "…" suffix
    document_updated: date | None`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Empty index">
            <code className="font-mono text-[13px] text-ink-1">search</code> returns{' '}
            <code className="font-mono text-[13px] text-ink-1">[]</code>. The retriever is{' '}
            <code className="font-mono text-[13px] text-ink-1">None</code> until <code className="font-mono text-[13px] text-ink-1">build</code> is called.
          </SpecItem>
          <SpecItem term="Empty / whitespace query">The tool wrapper raises <code className="font-mono text-[13px] text-ink-1">EmptyQueryError</code> before it reaches the index.</SpecItem>
          <SpecItem term="No matching passages">Returns an empty list. Score-zero passages are filtered.</SpecItem>
          <SpecItem term="Cross-language query">Diacritic-folded BM25 cannot bridge "tax" → "tributação". Recall degrades. This is the level-up trigger.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Trade-offs and alternatives considered">
        <SpecList>
          <SpecItem term="Hybrid (BM25 + dense + RRF) as v1">Rejected. Two retrieval paths, fusion weights, and an embeddings provider before any eval signal that one path is insufficient.</SpecItem>
          <SpecItem term="Cross-encoder reranker as v1">Rejected. A second model and an additional ~100 ms per query, justified at hundreds of documents.</SpecItem>
          <SpecItem term="Evidence-selector model">Rejected. A small LLM picking the best 4–8 of the fused top-30. Correct technique at thousands+ of documents; premature at 30.</SpecItem>
          <SpecItem term="Persistent on-disk index">Rejected. The cost of rebuilding 400 passages at startup is sub-second; persistence adds invalidation surface for no observable win.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Future work">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Hybrid retrieval lands at ROADMAP B6 inside{' '}
          <code className="font-mono text-[13px] text-ink-1">app/services/search.py</code>. The
          repository contract and the <code className="font-mono text-[13px] text-ink-1">PassageHit</code>{' '}
          schema do not change. The promotion gate is a measurable cross-language eval failure
          plus an explicit decision; not auto-triggered.
        </p>
      </Section>
    </article>
  )
}

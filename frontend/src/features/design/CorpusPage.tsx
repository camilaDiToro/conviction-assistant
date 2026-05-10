import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { PassageCard } from '@/components/PassageCard'
import { SpecItem, SpecList } from '@/components/Spec'
import { EXAMPLE_PASSAGES, HEADINGS_TREE, RAW_MARKDOWN } from '@/data/exampleConviction'

export default function CorpusPage() {
  const [activeId, setActiveId] = useState(EXAMPLE_PASSAGES[3].id)
  const passage = EXAMPLE_PASSAGES.find(p => p.id === activeId) ?? EXAMPLE_PASSAGES[0]

  return (
    <article>
      <PageHeader
        eyebrow="Pipeline · Corpus"
        title="Markdown ingestion."
        lead={
          <>
            A corpus document becomes a list of stable, citable{' '}
            <code className="font-mono text-[15px] text-ink-1">Passage</code> objects, one per
            top-level heading. The parser is pure: same input bytes, same output, no I/O
            beyond the file read.
          </>
        }
      />

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Conversational answers must cite specific positions in specific documents. That
          requires the corpus to be addressable at sub-document granularity, with stable
          identifiers that survive document edits. Documents in the corpus are markdown files
          authored in heading-section style, which gives the parser a natural unit to chunk
          on.
        </p>
      </Section>

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="Stable IDs">A passage identifier must not change when the body of the section is edited. The slug is derived from the heading text only.</SpecItem>
          <SpecItem term="Citation granularity">A passage must be small enough to quote in full and large enough to carry context. Heading sections satisfy both.</SpecItem>
          <SpecItem term="Pure parser">No I/O beyond reading the source file. Same bytes in, same passages out. Tests run without the application stack.</SpecItem>
          <SpecItem term="Date stamping">The document's <code className="font-mono text-[13px] text-ink-1">Updated:</code> header is extracted once and stamped on every passage. Required for Rule B (newer-of-two on conflicting convictions).</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <div className="max-w-prose space-y-4 text-ink-2 text-[15px] leading-relaxed">
          <p>
            <code className="font-mono text-[13px] text-ink-1">app/services/parser/markdown.py::parse_markdown</code>{' '}
            reads a markdown file, takes the title from the first <code className="font-mono text-[13px] text-ink-1">^#</code> line,
            then splits the body on <code className="font-mono text-[13px] text-ink-1">^##</code> headings. Each
            (heading, body) pair becomes one passage.
          </p>
          <p>
            Slugs come from{' '}
            <code className="font-mono text-[13px] text-ink-1">app/services/parser/text.py::slugify</code>:
            NFKD decompose → strip combining marks → lowercase → replace runs of non-alphanumeric
            characters with <code className="font-mono text-[13px] text-ink-1">-</code> →
            trim. Collisions within a document are resolved by suffix:{' '}
            <code className="font-mono text-[13px] text-ink-1">slug</code>,{' '}
            <code className="font-mono text-[13px] text-ink-1">slug-2</code>,{' '}
            <code className="font-mono text-[13px] text-ink-1">slug-3</code> in arrival order.
          </p>
          <p>
            Dates come from{' '}
            <code className="font-mono text-[13px] text-ink-1">app/services/parser/dates.py::extract_updated</code>:
            a regex matches{' '}
            <code className="font-mono text-[13px] text-ink-1">(Last Updated|Updated|Atualizado|Última Atualização|Atualização):\s+&lt;month&gt;\s+(de\s+)?&lt;year&gt;</code>{' '}
            with PT and EN month names. The <em>last</em> match wins (footer dates override
            the header when both are present). Day defaults to the first of the month.
          </p>
          <p>
            <code className="font-mono text-[13px] text-ink-1">app/services/ingest.py::ingest_corpus</code>{' '}
            orchestrates: parse all files, upsert via the repository, delete passages whose IDs
            are no longer in the parsed set (orphan detection on re-ingest).
          </p>
        </div>
      </Section>

      <Section eyebrow="Source document">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The example below is{' '}
          <code className="font-mono text-[13px] text-ink-1">convictions/lci_lca_investimentos.md</code>,
          a 161-line PT document with 9 sections.
        </p>
        <CodeBlock lang="markdown" code={RAW_MARKDOWN.split('\n').slice(0, 32).join('\n') + '\n\n# … rest elided …'} />
      </Section>

      <Section eyebrow="Heading tree">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Selecting a heading on the left shows the resulting passage on the right, with the
          slug derivation expandable.
        </p>
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-px bg-border border border-border">
          <ul className="bg-bg max-h-[480px] overflow-y-auto">
            {HEADINGS_TREE.map((h, i) => (
              <li key={h.passage_id}>
                <button
                  onClick={() => setActiveId(h.passage_id)}
                  className={[
                    'w-full text-left px-5 py-3 flex items-baseline gap-3 border-b border-border transition-colors',
                    activeId === h.passage_id
                      ? 'bg-surface-2 text-ink-1'
                      : 'text-ink-2 hover:bg-surface hover:text-ink-1',
                  ].join(' ')}
                >
                  <span className="text-ink-3 text-xs font-mono w-4 shrink-0">{i + 1}</span>
                  <span className="text-sm leading-snug tracking-tight">{h.heading}</span>
                </button>
              </li>
            ))}
          </ul>
          <div className="bg-bg p-6 lg:p-8">
            <PassageCard passage={passage} />
            <SlugTrace heading={passage.heading} slug={passage.id.split('#')[1]} />
          </div>
        </div>
      </Section>

      <Section eyebrow="Contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Defined in <code className="font-mono text-[13px] text-ink-1">app/schemas/passage.py::Passage</code>.
        </p>
        <CodeBlock
          lang="python"
          code={`class Passage(BaseModel):
    """A citable unit: one ## section of a conviction document."""
    model_config = ConfigDict(from_attributes=True)

    id: str                       # f"{document_id}#{slug}"
    document_id: str              # filename stem
    document_title: str           # text of the first ^# line
    heading: str                  # text of the ^## line
    heading_path: list[str]       # [document_title, heading]
    text: str                     # body up to the next ^## or EOF
    document_updated: date | None # extracted from header; None if absent`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Missing Updated header">
            <code className="font-mono text-[13px] text-ink-1">document_updated = None</code>{' '}
            on every passage from that file. Rule B handles a None side by stating the date is
            unknown.
          </SpecItem>
          <SpecItem term="Slug collision">Suffixed in arrival order: <code className="font-mono text-[13px] text-ink-1">-2</code>, <code className="font-mono text-[13px] text-ink-1">-3</code>, etc. Stable across re-ingests as long as section order is stable.</SpecItem>
          <SpecItem term="Empty section body">Allowed; <code className="font-mono text-[13px] text-ink-1">Passage.text</code> is the empty string. The retrieval layer scores it at zero. Documented behavior.</SpecItem>
          <SpecItem term="Re-ingest with renamed heading">Old passage_id becomes an orphan and is deleted from the store; the new heading creates a new passage_id. Citations to the old ID become unreachable — handled at the agent boundary by <code className="font-mono text-[13px] text-ink-1">PassageNotFoundError</code>.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Date-extraction variants">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Pinned in <code className="font-mono text-[13px] text-ink-1">app/services/parser/dates.py</code>.
          Adding a variant is a one-line change; removing one is a breaking change to existing
          documents.
        </p>
        <CodeBlock
          lang="markdown"
          code={`*Atualizado: Abril 2026*
**Atualizado: Abril 2026**
*Atualização: Abril 2026*
*Updated: April 2026*
**Last Updated: April 2026**
*Última Atualização: 2026*`}
        />
      </Section>

      <Section eyebrow="Future work">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          PDF and Excel ingestion slot behind the existing parser registry pattern (
          <code className="font-mono text-[13px] text-ink-1">app/services/parser/__init__.py::register</code>).
          Not built. Sentence-level subdivision <em>inside</em> a passage may become necessary
          at hundreds of documents; the citation unit would remain the section.
        </p>
      </Section>
    </article>
  )
}

function SlugTrace({ heading, slug }: { heading: string; slug: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-6 border-t border-border pt-5">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 text-ink-2 hover:text-ink-1 text-sm transition-colors"
      >
        <ChevronDown size={14} className={open ? '' : '-rotate-90'} />
        Slug derivation for "{heading}"
      </button>
      {open && (
        <ol className="mt-4 space-y-2 font-mono text-[13px] text-ink-2">
          <li><span className="text-ink-3">1.</span> input: <span className="text-ink-1">"{heading}"</span></li>
          <li><span className="text-ink-3">2.</span> NFKD decompose: <span className="text-ink-1">"{heading.normalize('NFKD')}"</span></li>
          <li><span className="text-ink-3">3.</span> strip combining marks: <span className="text-ink-1">"{heading.normalize('NFKD').replace(/[̀-ͯ]/g, '')}"</span></li>
          <li><span className="text-ink-3">4.</span> lowercase + non-alnum → "-": <span className="text-ink-1">"{slug}"</span></li>
        </ol>
      )}
    </div>
  )
}

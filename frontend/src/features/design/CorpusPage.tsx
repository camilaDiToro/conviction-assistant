import { useState } from 'react'
import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { PassageCard } from '@/components/PassageCard'
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
            Each conviction document is a markdown file. The parser splits it into one{' '}
            <code className="font-mono text-[15px] text-ink-1">Passage</code> per{' '}
            <code className="font-mono text-[15px] text-ink-1">##</code> section — that's the
            unit the agent searches, reads and cites.
          </>
        }
      />

      <Section eyebrow="How a file is split">
        <div className="max-w-prose space-y-4 text-ink-2 text-[15px] leading-relaxed">
          <p>
            The parser lives in{' '}
            <code className="font-mono text-[13px] text-ink-1">app/services/parser/markdown.py</code>.
            It does three things:
          </p>
          <ol className="list-decimal pl-5 space-y-2">
            <li>
              Takes the document title from the first <code className="font-mono text-[13px] text-ink-1">#</code> line.
            </li>
            <li>
              Splits the body on <code className="font-mono text-[13px] text-ink-1">##</code> headings.
              Each (heading, body) becomes one passage. Sub-sections (
              <code className="font-mono text-[13px] text-ink-1">###</code> and deeper) stay
              inline inside the parent passage.
            </li>
            <li>
              Builds a stable id <code className="font-mono text-[13px] text-ink-1">{`<document_id>#<slug>`}</code>{' '}
              from the heading text (see <em>What's a slug</em> below).
            </li>
          </ol>
          <p>
            <code className="font-mono text-[13px] text-ink-1">app/services/ingest.py</code>{' '}
            orchestrates the run: parse every file, upsert via the repository, delete passages
            whose ids no longer appear (orphan detection on re-ingest).
          </p>
        </div>
      </Section>

      <Section eyebrow="What's a slug">
        <div className="max-w-prose space-y-4 text-ink-2 text-[15px] leading-relaxed">
          <p>
            A <strong className="text-ink-1">slug</strong> is a URL-safe, lowercase identifier
            derived from a piece of human text. It strips accents and punctuation and replaces
            spaces with dashes — so <code className="font-mono text-[13px] text-ink-1">"Garantia do FGC"</code>{' '}
            becomes <code className="font-mono text-[13px] text-ink-1">garantia-do-fgc</code>.
          </p>
          <p>
            The function is in{' '}
            <code className="font-mono text-[13px] text-ink-1">app/services/parser/text.py::slugify</code>.
            If two headings within the same document slugify to the same string, the second one
            gets <code className="font-mono text-[13px] text-ink-1">-2</code>, the third{' '}
            <code className="font-mono text-[13px] text-ink-1">-3</code>, etc.
          </p>
        </div>
      </Section>

      <Section eyebrow="Example file">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          One real conviction —{' '}
          <code className="font-mono text-[13px] text-ink-1">convictions/lci_lca_investimentos.md</code>{' '}
          (top of the file shown). Each <code className="font-mono text-[13px] text-ink-1">##</code>{' '}
          below is a future passage; the body that follows it is the passage text.
        </p>
        <CodeBlock lang="markdown" code={RAW_MARKDOWN.split('\n').slice(0, 32).join('\n') + '\n\n# … rest elided …'} />
      </Section>

      <Section eyebrow="Resulting passages">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Click a heading to see the parsed passage. The id on top is what every citation in a
          chat answer eventually resolves to.
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
    text: str                     # body up to the next ^## or EOF`}
        />
      </Section>

      <Section eyebrow="Why so simple — and how to extend">
        <div className="max-w-prose space-y-4 text-ink-2 text-[15px] leading-relaxed">
          <p>
            The corpus for this demo is already markdown with consistent{' '}
            <code className="font-mono text-[13px] text-ink-1">##</code> sectioning, so the
            parser is small and pure: same bytes in, same passages out, no I/O beyond the file
            read. The interesting work is in retrieval and grounding, not in chunking.
          </p>
          <p>
            That said, it can be extended cleanly: anything that can produce a list of{' '}
            <code className="font-mono text-[13px] text-ink-1">Passage</code> objects from a
            file plugs in. The contract above is the only thing the rest of the system
            depends on. Below are sketches of how a few other formats would look.
          </p>
          <div className="border border-border rounded-md divide-y divide-border">
            <FormatRow
              ext=".pdf"
              lib="pdfplumber / PyMuPDF"
              note="Extract text per page, then chunk. PDFs rarely have markdown-clean section breaks, so the hard problem is choosing a unit: heuristics on heading-style fonts and font-size jumps, or a fixed-token window with overlap. Each chunk's heading becomes its first line; the slug strategy still works."
            />
            <FormatRow
              ext=".xlsx / .csv"
              lib="openpyxl / pandas"
              note="One sheet per logical document; the heading is the column header or the table caption, the text is a serialized row or row-group. Slug from the column name plus a row index. Useful when the conviction is a structured table of cases rather than prose."
            />
            <FormatRow
              ext=".docx"
              lib="python-docx"
              note="Walk paragraphs and pick up Word styles (Heading 1 / Heading 2). Behaves almost like markdown once styles are mapped, with the caveat that authors sometimes fake headings with bold text — needs a fallback."
            />
            <FormatRow
              ext=".html / web pages"
              lib="readability + beautifulsoup"
              note="Strip chrome, keep the article body, split on heading tags. Same shape as markdown after extraction; the work is in the pre-parser cleanup."
            />
          </div>
        </div>
      </Section>
    </article>
  )
}

function FormatRow({ ext, lib, note }: { ext: string; lib: string; note: string }) {
  return (
    <div className="px-5 py-4 grid grid-cols-1 md:grid-cols-[7rem_10rem_1fr] md:items-baseline gap-x-6 gap-y-1">
      <code className="font-mono text-[13px] text-ink-1">{ext}</code>
      <code className="font-mono text-[12px] text-ink-3">{lib}</code>
      <p className="text-ink-2 text-[14px] leading-relaxed">{note}</p>
    </div>
  )
}

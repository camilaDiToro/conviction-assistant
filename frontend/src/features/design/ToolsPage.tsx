import { useState } from 'react'
import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { TOOLS, type ToolSpec } from '@/data/toolSchemas'

export default function ToolsPage() {
  const [active, setActive] = useState<ToolSpec>(TOOLS[2])

  return (
    <article>
      <PageHeader
        eyebrow="Pipeline · Tools"
        title="Read-only tool surface."
        lead={<>Four pure-function tools over the repository contract.</>}
      />

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          The agent must reach the corpus through a typed interface, not the database, and not
          the BM25 index directly. The interface must be schema-discoverable by the LLM, pure
          (no global state beyond the injected{' '}
          <code className="font-mono text-[13px] text-ink-1">ToolContext</code>), and
          replaceable in tests.
        </p>
      </Section>

      <Section eyebrow="Approach">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          <code className="font-mono text-[13px] text-ink-1">app/agent/tools/registry.py::TOOLS</code>{' '}
          is a <code className="font-mono text-[13px] text-ink-1">dict[str, ToolEntry]</code> of
          four entries. Each <code className="font-mono text-[13px] text-ink-1">ToolEntry</code>{' '}
          pairs a <code className="font-mono text-[13px] text-ink-1">ToolDefinition</code> (name,
          description, JSON schema) with the implementing async function. The orchestrator
          uses the definitions to advertise tools to the LLM and the functions to dispatch
          incoming tool calls.
        </p>

        <div className="flex flex-wrap gap-2 mb-6">
          {TOOLS.map(t => (
            <button
              key={t.name}
              onClick={() => setActive(t)}
              className={[
                'px-4 py-2 rounded-md border text-sm transition-colors font-mono',
                active.name === t.name
                  ? 'bg-ink-1 text-bg border-ink-1'
                  : 'bg-surface text-ink-2 border-border hover:text-ink-1 hover:border-border-strong',
              ].join(' ')}
            >
              {t.name}
            </button>
          ))}
        </div>

        <div className="border border-border rounded-md bg-surface p-6 md:p-8">
          <code className="font-mono text-ink-1 text-base">{active.name}</code>
          <p className="text-ink-2 text-base leading-relaxed mt-2 mb-6 text-balance">{active.oneLine}</p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-10 gap-y-8">
            <div>
              <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Description (advertised to the LLM)</h4>
              <p className="text-ink-2 text-[15px] leading-relaxed">{active.description}</p>

              <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mt-8 mb-3">Decision rule</h4>
              <p className="text-ink-2 text-[15px] leading-relaxed">{active.whenToCall}</p>
            </div>
            <div>
              <h4 className="text-ink-3 text-[11px] uppercase tracking-tight mb-3">Parameters schema</h4>
              <CodeBlock lang="json" code={JSON.stringify(active.parameters, null, 2)} />
            </div>
          </div>

          <div className="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-px bg-border border border-border">
            <div className="bg-bg p-5">
              <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-2">Sample input</div>
              <pre className="font-mono text-[12px] leading-relaxed text-ink-1 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(active.sampleInput, null, 2)}</pre>
            </div>
            <div className="bg-bg p-5">
              <div className="text-ink-3 text-[11px] uppercase tracking-tight mb-2">Sample output</div>
              <pre className="font-mono text-[12px] leading-relaxed text-ink-1 overflow-x-auto whitespace-pre-wrap">{JSON.stringify(active.sampleOutput, null, 2)}</pre>
            </div>
          </div>
        </div>
      </Section>

      <Section eyebrow="Contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Tool advertisements use the protocol-level{' '}
          <code className="font-mono text-[13px] text-ink-1">ToolDefinition</code> defined in{' '}
          <code className="font-mono text-[13px] text-ink-1">app/providers/base.py</code>.
          Dispatch goes through the per-tool <code className="font-mono text-[13px] text-ink-1">ToolContext</code> in{' '}
          <code className="font-mono text-[13px] text-ink-1">app/agent/tools/context.py</code>.
        </p>
        <CodeBlock
          lang="python"
          code={`@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict

@dataclass(frozen=True)
class ToolContext:
    session: AsyncSession     # for repository calls
    retriever: Retriever      # for search_convictions (Protocol; BM25 today)

@dataclass(frozen=True)
class ToolEntry:
    definition: ToolDefinition
    func: Callable[..., Awaitable[Any]]

# Tool function signatures (verbatim):
async def list_documents(ctx: ToolContext, *, k: int) -> list[DocSummary]: ...
async def read_document_outline(ctx: ToolContext, *, document_id: str) -> DocumentOutline: ...
async def search_convictions(ctx: ToolContext, *, query: str, k: int = 5) -> list[PassageHit]: ...
async def read_passage(ctx: ToolContext, *, passage_ids: list[str]) -> list[Passage]: ...`}
        />
      </Section>
    </article>
  )
}

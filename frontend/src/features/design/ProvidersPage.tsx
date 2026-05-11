import { PageHeader, Section } from '@/components/Section'
import { Callout } from '@/components/Callout'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'

export default function ProvidersPage() {
  return (
    <article>
      <PageHeader
        eyebrow="Plumbing · Providers"
        title="Provider abstraction."
        lead={
          <>
            One protocol, three adapters. Provider SDKs are imported in exactly one directory;
            CI greps for violations. The orchestrator, tools, verifier, and cost calculator
            are provider-agnostic.
          </>
        }
      />

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          The agent must run against any LLM provider that supports tool calling and
          structured output. Locking the orchestrator to a specific SDK forecloses portability,
          inflates the test surface, and entangles unrelated concerns.
        </p>
      </Section>

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="Single LLM point">SDK imports live only under <code className="font-mono text-[13px] text-ink-1">app/providers/</code>. Greppable invariant.</SpecItem>
          <SpecItem term="Identical contract">Every adapter returns the same <code className="font-mono text-[13px] text-ink-1">LLMResponse</code> with the same <code className="font-mono text-[13px] text-ink-1">TokenUsage</code> shape. Cost is derived uniformly.</SpecItem>
          <SpecItem term="Deterministic stub">A canned-response adapter is the default in tests. CI never burns provider tokens.</SpecItem>
          <SpecItem term="Schema enforcement at the adapter">Strict-mode JSON output is configured by the adapter, not by the orchestrator. The orchestrator passes a schema; the adapter chooses how to enforce it (response_format strict on OpenAI; tool-output schema on Anthropic).</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          <code className="font-mono text-[13px] text-ink-1">app/providers/base.py</code> defines
          the protocols and the response data classes. Adapters implement the protocols and
          translate the provider's wire format. <code className="font-mono text-[13px] text-ink-1">app/providers/factory.py</code>{' '}
          dispatches on <code className="font-mono text-[13px] text-ink-1">settings.LLM_PROVIDER</code>{' '}
          and constructs the right adapter at startup.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-border border border-border">
          <Adapter
            name="openai.py"
            status="Shipping"
            model="gpt-5"
            notes={[
              'AsyncOpenAI client, configurable timeout',
              'Forwards reasoning_effort / verbosity only when non-None',
              'Maps max_output_tokens → max_completion_tokens for gpt-5',
              'response_format=json_schema strict when a schema is passed',
              'Translates ToolCall → tool_calls; tool messages with tool_call_id',
            ]}
          />
          <Adapter
            name="stub.py"
            status="What CI uses"
            model="—"
            notes={[
              'Replays a deque of LLMResponse from a YAML fixture',
              'Records every call on self.calls for assertions',
              'Raises ProviderError if the deque is exhausted',
              'Companion StubEmbedder returns unit vectors',
              'load_stub_responses(path) is the loader',
            ]}
          />
          <Adapter
            name="anthropic.py"
            status="Not yet built"
            model="claude-opus-4-7"
            notes={[
              'Tool calls via the Messages API tool_use blocks',
              'Same LLMResponse shape returned',
              'Anthropic Citations API ignored at the contract level',
              'Today factory.py raises ProviderError when llm_provider=anthropic',
              'Lands as the portability proof for the protocol',
            ]}
          />
        </div>
      </Section>

      <Section eyebrow="Contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Defined in <code className="font-mono text-[13px] text-ink-1">app/providers/base.py</code>.
        </p>
        <CodeBlock
          lang="python"
          code={`class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        schema: dict | None = None,                       # JSON schema; strict mode
        temperature: float | None = None,
        reasoning_effort: Literal["low","medium","high"] | None = None,
        verbosity: Literal["low","medium","high"] | None = None,
        max_output_tokens: int | None = None,
    ) -> LLMResponse: ...

@dataclass(frozen=True)
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    parsed: dict | None                                   # filled when schema is passed
    usage: TokenUsage
    finish_reason: FinishReason                           # stop | tool_calls | length | refusal

@dataclass(frozen=True)
class TokenUsage:
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    reasoning_tokens: int = 0`}
        />
      </Section>

      <Section eyebrow="Single-LLM-point invariant">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          The rule is enforceable as a single ripgrep. CI runs it on every push.
        </p>
        <CodeBlock
          lang="bash"
          code={`# Every match must be under app/providers/.
$ rg --files-with-matches -t py "import openai|from openai|import anthropic|from anthropic" app/
app/providers/openai.py
app/providers/factory.py

# Anything else fails the build.`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Missing OPENAI_API_KEY">
            <code className="font-mono text-[13px] text-ink-1">factory.py</code> raises{' '}
            <code className="font-mono text-[13px] text-ink-1">ProviderError</code> at startup.
            Lifespan fails fast.
          </SpecItem>
          <SpecItem term="Upstream timeout">
            Bounded by <code className="font-mono text-[13px] text-ink-1">OPENAI_TIMEOUT_SECONDS</code> (default 60).
            Surfaces as <code className="font-mono text-[13px] text-ink-1">ProviderError</code>.
          </SpecItem>
          <SpecItem term="Rate-limit (429)">Surfaced as <code className="font-mono text-[13px] text-ink-1">ProviderError</code>; mapped at the boundary as 502/503.</SpecItem>
          <SpecItem term="Truncated response"><code className="font-mono text-[13px] text-ink-1">finish_reason == "length"</code>. The orchestrator treats this as failure.</SpecItem>
          <SpecItem term="Unknown model in pricing"><code className="font-mono text-[13px] text-ink-1">compute_call_cost_usd</code> raises <code className="font-mono text-[13px] text-ink-1">ProviderError</code>. Audit row is still written; only the cost roll-up is affected.</SpecItem>
          <SpecItem term="Stub fixture exhausted">Test-only. <code className="font-mono text-[13px] text-ink-1">StubLLM</code> raises <code className="font-mono text-[13px] text-ink-1">ProviderError("stub: no more responses")</code>. Indicates a missing fixture entry.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Trade-offs and alternatives considered">
        <SpecList>
          <SpecItem term="Anthropic Citations API as the architecture">Rejected. Each provider's grounding semantics differ; the deterministic substring verifier is stronger and portable. Native APIs may live behind adapters as optimizations only.</SpecItem>
          <SpecItem term="LiteLLM-the-package as a unifier">Rejected. It carries a much larger surface than this project needs and couples us to its release cadence and quirks. The protocol here is small enough to maintain directly.</SpecItem>
          <SpecItem term="A single SDK imported in the orchestrator">Rejected and CI-greppable. The cost is too low to skip and the upside (testability with stubs, portability) is too high.</SpecItem>
          <SpecItem term="Streaming as a first-class adapter feature">Deferred. A streaming variant would change the LLMResponse type to an async iterator; not needed until UX latency outweighs simplicity.</SpecItem>
        </SpecList>
      </Section>

      <Callout label="Embeddings" tone="note">
        <code className="font-mono text-[13px] text-ink-1">app/providers/openai.py::OpenAIEmbedder</code>{' '}
        ships against an <code className="font-mono text-[13px] text-ink-1">EmbeddingProvider</code>{' '}
        protocol. Today no path uses embeddings — they exist as the seam for the hybrid
        retrieval level-up. <code className="font-mono text-[13px] text-ink-1">StubEmbedder</code>{' '}
        returns unit vectors so tests of an embedding-using path can run without a network.
      </Callout>
    </article>
  )
}

function Adapter({ name, status, model, notes }: { name: string; status: string; model: string; notes: readonly string[] }) {
  return (
    <div className="bg-bg p-6">
      <code className="font-mono text-ink-1 text-base">{name}</code>
      <div className="text-ink-3 text-[11px] uppercase tracking-tight mt-1 mb-3">{status}</div>
      <div className="font-mono text-ink-2 text-xs mb-4">model · {model}</div>
      <ul className="space-y-2 text-ink-2 text-[13.5px] leading-relaxed">
        {notes.map((n, i) => (
          <li key={i} className="flex gap-2"><span className="text-ink-3">·</span><span>{n}</span></li>
        ))}
      </ul>
    </div>
  )
}

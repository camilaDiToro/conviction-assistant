import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'

export default function UsagePage() {
  return (
    <article>
      <PageHeader
        eyebrow="Plumbing · Usage & audit"
        title="Token usage."
        lead={
          <>
            Every LLM call records raw token counts from the provider. The app keeps those counts
            for debugging and review.
          </>
        }
      />

      <Section eyebrow="Contract">
        <SpecList>
          <SpecItem term="Per-step usage">Each LLM step carries its own <code className="font-mono text-[13px] text-ink-1">TokenUsage</code>: model, prompt, completion, cached, reasoning, and effort.</SpecItem>
          <SpecItem term="Question summary">The response aggregates token totals across LLM calls for the current question.</SpecItem>
          <SpecItem term="Audit log">The same raw usage JSON is persisted with each <code className="font-mono text-[13px] text-ink-1">llm_call</code> row.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Response shape">
        <CodeBlock
          lang="json"
          code={`{
  "usage_summary": {
    "llm_call_count": 3,
    "prompt_tokens": 8214,
    "completion_tokens": 614,
    "cached_tokens": 4096,
    "reasoning_tokens": 42,
    "step_count": 7,
    "duration_ms": 18240
  },
  "debug": {
    "steps": [
      {
        "kind": "llm_call",
        "usage": {
          "model": "gpt-5.5",
          "prompt_tokens": 3122,
          "completion_tokens": 47,
          "cached_tokens": 2560,
          "reasoning_tokens": 13,
          "reasoning_effort": "low"
        }
      }
    ]
  }
}`}
        />
      </Section>

      <Section eyebrow="Boundary">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          The chat API stops at provider-reported counters. Anything that interprets those
          counters outside debugging should live as a separate layer over the audit log.
        </p>
      </Section>
    </article>
  )
}

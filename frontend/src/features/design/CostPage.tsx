import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'

export default function CostPage() {
  return (
    <article>
      <PageHeader
        eyebrow="Plumbing · Cost & audit"
        title="Cost tracking."
        lead={
          <>
            Every step is recorded with three IDs. Token counts come from the adapter; USD is
            derived from a vendored price table. Old audit rows re-price under a new pricing
            snapshot — cost is never frozen at write time.
          </>
        }
      />

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Operating cost is a first-order concern for an LLM application. A reviewer should be
          able to look at any past conversation and answer: how much did this cost, where did
          it spend, and would it cost the same today? The accounting must survive provider
          price updates and model changes.
        </p>
      </Section>

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="Per-step granularity">One audit row per LLM call, tool call, verifier check, and final response. Not aggregated at write time.</SpecItem>
          <SpecItem term="Three IDs per row">step_id, question_id, conversation_id. Roll-ups (per question, per conversation) are queries against the same table.</SpecItem>
          <SpecItem term="Cost derived, not stored">Token counts are stored; USD is computed at read time from <code className="font-mono text-[13px] text-ink-1">_model_prices.json</code>. A price update re-prices history.</SpecItem>
          <SpecItem term="Cached-tokens discount handled separately">Cached input is priced at the cache-read rate when the model supports it; fresh input at the regular rate.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Every <code className="font-mono text-[13px] text-ink-1">LLMResponse</code> carries a{' '}
          <code className="font-mono text-[13px] text-ink-1">TokenUsage</code> from the adapter.
          The orchestrator stamps the response and every intermediate step with the three IDs
          and writes them to <code className="font-mono text-[13px] text-ink-1">audit_log</code>.
          The HTTP response (B9) includes a per-step <code className="font-mono text-[13px] text-ink-1">debug.steps[]</code> trace
          and a <code className="font-mono text-[13px] text-ink-1">usage_summary</code> roll-up
          for the question and the conversation so far.
        </p>
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          USD is computed by{' '}
          <code className="font-mono text-[13px] text-ink-1">app/services/cost.py::compute_call_cost_usd(usage)</code>.
          The function loads the vendored pricing table once (<code className="font-mono text-[13px] text-ink-1">@lru_cache</code>),
          splits cached vs fresh input tokens, multiplies by the appropriate rate, and rounds
          to 8 decimal places.
        </p>
      </Section>

      <Section eyebrow="Storage contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Defined in <code className="font-mono text-[13px] text-ink-1">alembic/versions/0001_initial_schema.py</code>.
        </p>
        <CodeBlock
          lang="sql"
          code={`CREATE TABLE audit_log (
  step_id          TEXT PRIMARY KEY,
  question_id      TEXT NOT NULL,
  conversation_id  TEXT NOT NULL,
  timestamp        TEXT NOT NULL,                       -- ISO-8601
  kind             TEXT NOT NULL CHECK (kind IN
                       ('llm_call','tool_call','verifier','response')),
  payload          TEXT NOT NULL,                       -- JSON
  usage            TEXT                                 -- JSON, null for non-LLM
);
CREATE INDEX ix_audit_log_question_id ON audit_log (question_id);
CREATE INDEX ix_audit_log_conversation_id ON audit_log (conversation_id);

-- Convenience view for cost-only queries.
CREATE VIEW cost_log AS
  SELECT step_id, question_id, conversation_id, timestamp, payload, usage
  FROM audit_log
  WHERE kind = 'llm_call';`}
        />
      </Section>

      <Section eyebrow="Response contract (B9)">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          The HTTP response wraps the agent's structured answer with a deterministic disclaimer
          and the cost roll-up.
        </p>
        <CodeBlock
          lang="json"
          code={`{
  "kind": "answer",
  "answer": "...",
  "citations": [...],
  "disclaimer": "Esta resposta é informativa e não constitui recomendação de investimento.",
  "usage_summary": {
    "question_total_cost_usd": 0.014,
    "conversation_total_cost_usd": 0.041,
    "step_count": 4
  },
  "debug": {
    "tool_calls": [...],
    "verification_passed": true,
    "steps": [
      { "step_id": "...", "kind": "tool_call", "name": "search_convictions", "duration_ms": 80 },
      { "step_id": "...", "kind": "tool_call", "name": "read_passage",       "duration_ms": 28 },
      { "step_id": "...", "kind": "llm_call",  "name": "agent.answer",
        "duration_ms": 1240, "usage": { "model": "gpt-5", "prompt_tokens": 1834, ... },
        "cost_usd": 0.0118 },
      { "step_id": "...", "kind": "verifier",  "name": "substring",          "duration_ms": 4 }
    ]
  }
}`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Model not in pricing table">
            <code className="font-mono text-[13px] text-ink-1">compute_call_cost_usd</code> raises{' '}
            <code className="font-mono text-[13px] text-ink-1">ProviderError</code>. The audit row
            is still written; only the cost roll-up is missing.
          </SpecItem>
          <SpecItem term="Pricing tier missing for cached_tokens">If a model has no <code className="font-mono text-[13px] text-ink-1">cache_read_input_token_cost</code>, cached tokens are priced at the regular input rate. Documented as graceful degradation.</SpecItem>
          <SpecItem term="audit_log write failure">Logged; does not abort the response. Operationally a P1 — a missing audit row is a missing record.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Trade-offs and alternatives considered">
        <SpecList>
          <SpecItem term="tokencost runtime library">Rejected. A runtime dependency for one number per model is too much trust to extend; we vendor the table.</SpecItem>
          <SpecItem term="LiteLLM-the-package as a pricing source">Rejected. The package carries far more than pricing data; we lift only the JSON we need into <code className="font-mono text-[13px] text-ink-1">app/providers/_model_prices.json</code> via <code className="font-mono text-[13px] text-ink-1">scripts/refresh_prices.py</code>.</SpecItem>
          <SpecItem term="Store cost on the audit row">Rejected. A frozen cost cannot benefit from a price correction or a model rename. Storing tokens and deriving cost is the audit-friendly pattern.</SpecItem>
          <SpecItem term="One row per request">Rejected. Per-step granularity is the difference between "this question cost a lot" and "the answer call cost a lot, the searches were free".</SpecItem>
        </SpecList>
      </Section>
    </article>
  )
}

import { PageHeader, Section } from '@/components/Section'
import { CodeBlock } from '@/components/CodeBlock'
import { SpecItem, SpecList } from '@/components/Spec'

export default function AgentLoopPage() {
  return (
    <article>
      <PageHeader
        eyebrow="Pipeline · Agent loop"
        title="Bounded orchestration."
        lead={
          <>
            A three-state machine — Gather → Act → Verify — with bounds counted by the
            orchestrator. The system prompt suggests behavior; the JSON schema and the
            orchestrator enforce it.
          </>
        }
      />

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Drive a tool-using LLM toward a grounded, structured answer with a finite tool
          budget and a finite retry budget. Detect cases where the model has not yet seen
          enough evidence (force a search), where the answer cites material it cannot
          substantiate (force a retry), and where the question has no in-corpus answer
          (return a safe refusal).
        </p>
      </Section>

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="≤ 5 tool calls">Counted by the orchestrator. The 6th call is refused. Five is empirically enough for the corpus; cheap to bump if eval shows otherwise.</SpecItem>
          <SpecItem term="≥ 1 search before any answer">Forces the agent to look. The orchestrator rejects an Act response that emits before any <code className="font-mono text-[13px] text-ink-1">search_convictions</code> call has run.</SpecItem>
          <SpecItem term="Retry budget = 1">One re-prompt on verifier failure, with the failure reason inlined. A second failure terminates the budget.</SpecItem>
          <SpecItem term="Strict JSON output"><code className="font-mono text-[13px] text-ink-1">response_format=json_schema</code> with <code className="font-mono text-[13px] text-ink-1">strict: true</code>. The orchestrator never parses freeform text.</SpecItem>
          <SpecItem term="Determinism in tests">Against <code className="font-mono text-[13px] text-ink-1">StubLLM</code> the loop is reproducible; the same fixture YAML always produces the same audit trace.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The state machine is small enough to fit on one diagram. Heavy outline = the orchestrator
          enforces an invariant at this transition; dashed = the verifier check.
        </p>
        <StateMachine />
      </Section>

      <Section eyebrow="The bounds, named">
        <SpecList>
          <SpecItem term="max_tool_calls = 5">A single conversation step may chain at most five tool calls. The 6th raises a synthetic <code className="font-mono text-[13px] text-ink-1">ToolBudgetExceeded</code> the agent sees as a tool-result error.</SpecItem>
          <SpecItem term="min_searches_before_answer = 1">Tracked by counting <code className="font-mono text-[13px] text-ink-1">search_convictions</code> calls. An Act response emitted before this counter is non-zero is rejected and the agent is re-prompted with a directive to search.</SpecItem>
          <SpecItem term="verifier_retries = 1">Per Act response. The retry message contains the per-citation failure reasons returned by the verifier verbatim.</SpecItem>
          <SpecItem term='reasoning_effort = "low"'>Set at the server for the deployed model. The verifier still catches paraphrase / hallucinated passage_id, so higher effort is reserved for controlled eval runs.</SpecItem>
          <SpecItem term="temperature = 0">Where the provider honors it. OpenAI gpt-5 ignores temperature; the verifier and the structured-output schema are the determinism-relevant constraints.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          The agent's structured output is one of two variants. Strict JSON schema enforces shape.
        </p>
        <CodeBlock
          lang="json"
          code={`// AnswerResponse
{
  "kind": "answer",
  "answer": "string",
  "citations": [
    {
      "passage_id": "string",
      "quote": "string"          // exact substring of passage.text after normalization
    }
  ],
  "general_knowledge_used": false,
  "general_knowledge_section": null,
  "out_of_scope": false
}

// ClarifyingResponse
{
  "kind": "clarifying_question",
  "question": "string",
  "options": ["string"]
}`}
        />
      </Section>

      <Section eyebrow="Retry path">
        <CodeBlock
          lang="python"
          code={`for attempt in (1, 2):
    response = await llm.generate(messages, tools=tool_specs, schema=AnswerSchema)
    failures = verify_all(response.parsed["citations"])
    if not failures:
        return response                                    # PASS — ship
    if attempt == 1:
        messages.append({
            "role": "user",
            "content": render_feedback(failures),          # exact verifier reasons
        })
        continue
    return strip_or_refuse(response, failures)             # 2nd FAIL terminal`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Schema-violating output"><code className="font-mono text-[13px] text-ink-1">response_format=strict</code> prevents at the provider; if it leaks through (e.g. provider drift), the orchestrator surfaces a <code className="font-mono text-[13px] text-ink-1">ProviderError</code>.</SpecItem>
          <SpecItem term="Tool call to a missing passage_id">The tool raises <code className="font-mono text-[13px] text-ink-1">PassageNotFoundError</code>. The orchestrator surfaces it to the agent as a tool-result error so the agent can self-correct without consuming the verifier retry budget.</SpecItem>
          <SpecItem term="Upstream rate-limit / 5xx">Bubbled as <code className="font-mono text-[13px] text-ink-1">ProviderError</code>; mapped to 502/503 at the boundary. No internal retry today.</SpecItem>
          <SpecItem term="Response truncation"><code className="font-mono text-[13px] text-ink-1">finish_reason == "length"</code>. The orchestrator treats this as failure (the answer cannot be trusted to be complete) and returns a safe refusal.</SpecItem>
          <SpecItem term="Refusal from the model"><code className="font-mono text-[13px] text-ink-1">finish_reason == "refusal"</code> on OpenAI. Surfaced to the user as a refusal with no retry.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Trade-offs and alternatives considered">
        <SpecList>
          <SpecItem term="Prompt-only enforcement of bounds">Rejected. A model can reinterpret prompt instructions; bounds that matter are counted in code.</SpecItem>
          <SpecItem term="Higher reasoning_effort">Rejected. The verifier catches the failures reasoning would have caught (misquotes, hallucinated IDs); higher effort mainly increases token usage on the current eval set.</SpecItem>
          <SpecItem term="Explicit 'I don't know' state">Rejected. Covered by the <code className="font-mono text-[13px] text-ink-1">out_of_scope</code> flag on AnswerResponse; not a separate transition.</SpecItem>
          <SpecItem term="Multiple verifier retries">Rejected. Two retries doubled worst-case latency and token usage without measurable verifier-pass-rate improvement; the gain came from the first retry.</SpecItem>
          <SpecItem term="Streaming output">Deferred level-up. The verifier needs the complete citation list before it can ship the answer, so streaming the body adds UX latency only.</SpecItem>
        </SpecList>
      </Section>
    </article>
  )
}

function StateMachine() {
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-10 overflow-x-auto">
      <svg viewBox="0 0 800 280" className="w-full max-w-[800px] mx-auto" role="img" aria-label="Agent loop state machine">
        <defs>
          <marker id="arrow-loop" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        <g>
          <rect x="40" y="100" width="180" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="130" y="128" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Gather</text>
          <text x="130" y="148" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">tool calls</text>
          <text x="130" y="166" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">≤ 5 total · ≥ 1 search</text>
        </g>

        <path d="M 220 110 Q 270 60 220 100" fill="none" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="276" y="80" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">more tools</text>

        <line x1="220" y1="140" x2="320" y2="140" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="270" y="130" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">enough evidence</text>

        <g>
          <rect x="320" y="100" width="180" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="410" y="128" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Act</text>
          <text x="410" y="148" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">structured answer</text>
          <text x="410" y="166" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">strict JSON · citations</text>
        </g>

        <line x1="500" y1="140" x2="600" y2="140" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />

        <g>
          <rect x="600" y="100" width="160" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" strokeDasharray="3 2" />
          <text x="680" y="128" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Verify</text>
          <text x="680" y="148" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">substring check</text>
          <text x="680" y="166" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">deterministic</text>
        </g>

        <line x1="680" y1="180" x2="680" y2="240" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="700" y="220" fill="#FFFFFF" fontSize="11" fontFamily="Inter" fontWeight="600">PASS · ship</text>

        <path d="M 600 130 Q 500 30 410 100" fill="none" stroke="#B5B5B5" strokeDasharray="3 3" markerEnd="url(#arrow-loop)" />
        <text x="500" y="40" textAnchor="middle" fill="#B5B5B5" fontSize="10" fontFamily="Inter">FAIL · retry once with verifier feedback</text>

        <line x1="680" y1="180" x2="680" y2="195" stroke="#B5B5B5" />
        <line x1="680" y1="195" x2="780" y2="195" stroke="#B5B5B5" />
        <line x1="780" y1="195" x2="780" y2="240" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="785" y="232" fill="#6B6B6B" fontSize="10" fontFamily="Inter">2nd FAIL · strip or refuse</text>
      </svg>
    </div>
  )
}

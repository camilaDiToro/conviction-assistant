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
            A four-stage pipeline — Rewrite → Gather → Act → Resolve — with bounds counted by the
            orchestrator. The system prompt suggests behavior; the JSON schema, the tool budget,
            and the deterministic resolver enforce it.
          </>
        }
      />

      <Section eyebrow="Step 1 · Rewrite">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Before the agent loop runs, a separate LLM call takes <code className="font-mono text-[13px] text-ink-1">(history, new_user_message)</code> and
          produces <code className="font-mono text-[13px] text-ink-1">(rewritten_self_contained_question, detected_language)</code>. The agent loop
          then sees ONLY <code className="font-mono text-[13px] text-ink-1">[system_prompt, user: rewritten_question]</code> — no prior assistant text,
          no prior user turns. This is the <strong className="text-ink-1">conversation-memory quarantine</strong>:
          grounding stays anchored to the corpus, never to the model's own past answers.
        </p>
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          The rewrite resolves pronouns ("it", "those") and elliptic follow-ups ("and LCAs?") into a
          question that stands alone. If the new question already stands alone (or there is no prior
          conversation), it is returned unchanged — the model is instructed not to paraphrase for
          style. The same call classifies the user's language (<code className="font-mono text-[13px] text-ink-1">pt</code> /
          <code className="font-mono text-[13px] text-ink-1"> es</code> / <code className="font-mono text-[13px] text-ink-1">en</code>),
          which drives the answer-language directive downstream.
        </p>
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          This is the industry-standard pattern for multi-turn RAG. LangChain's
          {' '}<code className="font-mono text-[13px] text-ink-1">create_history_aware_retriever</code> "builds a
          retriever that uses chat history to rephrase user questions, making them standalone for
          better retrieval." LlamaIndex's <code className="font-mono text-[13px] text-ink-1">CondenseQuestionChatEngine</code> "first
          generates a standalone question from conversation context and last message, then queries
          the query engine for a response." The motivation in both libraries — and in the RAG
          literature — is the same: passing full history bloats tokens, biases retrieval toward
          prior topics ("context contamination"), and lets the model self-anchor on its own previous
          answers instead of re-deriving claims from the corpus.
        </p>
        <CodeBlock
          lang="python"
          code={`# app/agent/rewrite.py
async def rewrite_question(
    user_message: str,
    history: list[ConversationTurn],
    *,
    llm: LLMProvider,
) -> tuple[str, Language, StepRecord]:
    ...
    # returns (rewritten_question, detected_language, step)

# app/agent/loop.py — the agent only ever sees the rewritten question
rewritten, language, rewrite_step = await rewrite_question(
    user_message, history, llm=llm,
)
messages = [
    Message(role="system", content=SYSTEM_PROMPT),
    Message(role="system", content=language_directive),
    Message(role="user",   content=rewritten),   # <- no prior turns
]`}
        />
      </Section>

      <Section eyebrow="Problem">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Drive a tool-using LLM toward a grounded, structured answer with a finite tool
          budget. Detect cases where the model has not yet seen enough evidence (force a
          search), where the question is off-topic (return a safe out-of-scope reply), and
          turn each cited quote into a verifiable <code className="font-mono text-[13px] text-ink-1">(start, end)</code> region of the source
          passage before shipping.
        </p>
      </Section>

      <Section eyebrow="Constraints">
        <SpecList>
          <SpecItem term="≤ 5 tool calls">Counted by the orchestrator. A 6th call triggers a "tool budget exhausted" message inlined into the in-flight tool results, and the next iteration must produce a final structured answer.</SpecItem>
          <SpecItem term="≥ 1 search before any answer">Forces the agent to look. An <code className="font-mono text-[13px] text-ink-1">AnswerOutput</code> emitted before any <code className="font-mono text-[13px] text-ink-1">search_convictions</code> call has run is rejected (unless <code className="font-mono text-[13px] text-ink-1">out_of_scope=true</code>); the loop appends a reminder and continues.</SpecItem>
          <SpecItem term="Strict JSON output"><code className="font-mono text-[13px] text-ink-1">response_format=json_schema</code> with <code className="font-mono text-[13px] text-ink-1">strict: true</code>. The orchestrator never parses freeform text.</SpecItem>
          <SpecItem term="Deterministic resolver">Every <code className="font-mono text-[13px] text-ink-1">AnswerOutput</code> runs through a substring resolver that turns each cited quote into a <code className="font-mono text-[13px] text-ink-1">(start, end)</code> region of the cited passage. The literal quote is dropped before the wire response is built; non-anchoring citations survive with offsets <code className="font-mono text-[13px] text-ink-1">null</code>.</SpecItem>
          <SpecItem term="Determinism in tests">Against <code className="font-mono text-[13px] text-ink-1">StubLLM</code> the loop is reproducible; the same fixture YAML always produces the same audit trace.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Approach">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The pipeline is small enough to fit on one diagram. Heavy outline = the orchestrator
          enforces an invariant at this transition; dashed = the deterministic resolver.
        </p>
        <StateMachine />
      </Section>

      <Section eyebrow="The bounds, named">
        <SpecList>
          <SpecItem term="agent_max_tool_calls = 5">A single conversation step may chain at most five tool calls. The 6th refuses all calls in that batch with "tool budget exhausted" and forces a final answer next iteration.</SpecItem>
          <SpecItem term="min_searches_before_answer = 1">Tracked by counting <code className="font-mono text-[13px] text-ink-1">search_convictions</code> calls. An <code className="font-mono text-[13px] text-ink-1">AnswerOutput</code> emitted before this counter is non-zero is rejected and the agent is re-prompted with a directive to search (or to set <code className="font-mono text-[13px] text-ink-1">out_of_scope=true</code>).</SpecItem>
          <SpecItem term='reasoning_effort = "low"'>Set at the server for the deployed model. The deterministic resolver catches misquotes and paraphrase post-hoc, so higher effort is reserved for controlled eval runs.</SpecItem>
          <SpecItem term="temperature = 0">Where the provider honors it. OpenAI gpt-5 ignores temperature; the structured-output schema and the resolver are the determinism-relevant constraints.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Contract">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          The agent's structured output is one of two variants. Strict JSON schema enforces shape.
          Citations enter the resolver with verbatim <code className="font-mono text-[13px] text-ink-1">quote</code> strings; after the resolver runs,
          the wire response carries <code className="font-mono text-[13px] text-ink-1">(start, end)</code> offsets into the passage and the literal quote is dropped.
        </p>
        <CodeBlock
          lang="json"
          code={`// Agent output (internal — consumed by the resolver)
{
  "kind": "answer",
  "answer": "string",
  "citations": [
    {
      "passage_id": "string",
      "quote": "string"          // verbatim substring of the cited passage
    }
  ],
  "general_knowledge_used": false,
  "general_knowledge_section": null,
  "out_of_scope": false
}

// Wire citation (post-resolver — the quote is gone)
{
  "passage_id": "string",
  "document": "string.md",
  "heading": "string",
  "heading_path": ["string"],
  "passage_text": "string",
  "start": 42,                   // null when the quote did not anchor
  "end": 87                      // null when the quote did not anchor
}

// ClarifyingResponse (internal == wire)
{
  "kind": "clarifying_question",
  "question": "string",
  "options": ["string"]
}`}
        />
      </Section>

      <Section eyebrow="Soft-correction paths">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-4">
          Two situations cause the loop to inject a reminder and continue rather than abort. Both
          live inside the same iteration counter — there is no separate retry budget and no
          verifier loop. The resolver runs exactly once, at the end, on whatever <code className="font-mono text-[13px] text-ink-1">AnswerOutput</code> the
          loop produces.
        </p>
        <CodeBlock
          lang="python"
          code={`# 1. AnswerOutput without any search → reminder to search.
if isinstance(output, AnswerOutput) and search_count == 0 and not output.out_of_scope:
    messages.append(Message(role="assistant", content=...))
    messages.append(Message(role="user", content=(
        "You must call search_convictions to gather evidence "
        "before producing an answer. If the message is a greeting "
        "or unrelated to Decade's convictions, set out_of_scope=true instead."
    )))
    continue

# 2. Tool batch would push past the budget → refuse all, force final answer.
if tool_call_count + len(response.tool_calls) > max_tool_calls:
    for tc in response.tool_calls:
        messages.append(Message(role="tool", tool_call_id=tc.id, content=(
            f"Tool budget exhausted ({max_tool_calls} calls max). Produce a "
            "final structured answer using the evidence already gathered."
        )))
    budget_exhausted = True
    continue`}
        />
      </Section>

      <Section eyebrow="Failure modes">
        <SpecList>
          <SpecItem term="Schema-violating output"><code className="font-mono text-[13px] text-ink-1">response_format=strict</code> prevents at the provider; if it leaks through (e.g. provider drift), validation against the agent output Pydantic model raises <code className="font-mono text-[13px] text-ink-1">AgentError</code>.</SpecItem>
          <SpecItem term="Tool call to a missing passage_id">The tool raises <code className="font-mono text-[13px] text-ink-1">PassageNotFoundError</code>. The orchestrator surfaces it to the agent as a tool-result error so the agent can self-correct within the remaining tool budget.</SpecItem>
          <SpecItem term="Non-anchoring citation">The resolver did not find the verbatim quote in the cited passage. The citation survives in the wire response with <code className="font-mono text-[13px] text-ink-1">start = end = null</code>; the frontend popup shows the passage without a highlight.</SpecItem>
          <SpecItem term="Citation to a passage that cannot be loaded">Dropped before reaching the wire — without <code className="font-mono text-[13px] text-ink-1">passage_text</code> there is nothing to show.</SpecItem>
          <SpecItem term="Upstream rate-limit / 5xx">Bubbled as <code className="font-mono text-[13px] text-ink-1">ProviderError</code>; mapped to 503 at the boundary. No internal retry today.</SpecItem>
          <SpecItem term="Iteration cap exceeded">If the loop hits <code className="font-mono text-[13px] text-ink-1">agent_max_iterations</code> without producing parsed output, the orchestrator raises <code className="font-mono text-[13px] text-ink-1">AgentError</code> (500 at the boundary). Should be unreachable in practice — the tool-budget rule forces a final answer well before this.</SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="Trade-offs and alternatives considered">
        <SpecList>
          <SpecItem term="Pass full conversation history to the agent loop">Rejected. Letting the loop see prior assistant text lets the model self-anchor on its own past answers, which compounds grounding errors across turns; it bloats every turn's token usage; and it pollutes retrieval — embeddings and BM25 both pick up on assistant phrasing rather than the user's actual question. The rewrite stage compresses history into one self-contained question and feeds the loop <code className="font-mono text-[13px] text-ink-1">[system, user(rewritten)]</code> only. Trade-off: one extra LLM call per turn, and rewrite quality determines retrieval quality.</SpecItem>
          <SpecItem term="Verifier-with-retry loop instead of a deterministic resolver">Rejected. A verifier-with-retry costs extra LLM calls per turn and can still ship paraphrased quotes after a successful "retry" pass. The resolver runs once, deterministically, and drops the literal quote so what reaches the user is always anchored or explicitly un-anchored. Non-anchoring citations are surfaced — not hidden — so the analyst can audit them.</SpecItem>
          <SpecItem term="Prompt-only enforcement of bounds">Rejected. A model can reinterpret prompt instructions; bounds that matter are counted in code.</SpecItem>
          <SpecItem term="Higher reasoning_effort">Rejected. The deterministic resolver catches the failures higher reasoning would have caught (misquotes, hallucinated passage IDs); higher effort mainly increases token usage on the current eval set.</SpecItem>
          <SpecItem term="Explicit 'I don't know' state">Rejected. Covered by the <code className="font-mono text-[13px] text-ink-1">out_of_scope</code> flag on <code className="font-mono text-[13px] text-ink-1">AnswerOutput</code>; not a separate transition.</SpecItem>
          <SpecItem term="Streaming output">Deferred level-up. The resolver needs the complete citation list before it can ship the answer, so streaming the body adds UX latency only.</SpecItem>
        </SpecList>
      </Section>
    </article>
  )
}

function StateMachine() {
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-10 overflow-x-auto">
      <svg viewBox="0 0 900 240" className="w-full max-w-[900px] mx-auto" role="img" aria-label="Agent loop state machine">
        <defs>
          <marker id="arrow-loop" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        <g>
          <rect x="20" y="100" width="160" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="100" y="128" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Rewrite</text>
          <text x="100" y="148" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">history → standalone Q</text>
          <text x="100" y="166" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">+ language detect</text>
        </g>

        <line x1="180" y1="140" x2="240" y2="140" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="210" y="130" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">[system, user(rewritten)]</text>

        <g>
          <rect x="240" y="100" width="160" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="320" y="128" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Gather</text>
          <text x="320" y="148" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">tool calls</text>
          <text x="320" y="166" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">≤ 5 total · ≥ 1 search</text>
        </g>

        <path d="M 400 110 Q 450 60 400 100" fill="none" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="456" y="80" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">more tools</text>

        <line x1="400" y1="140" x2="460" y2="140" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="430" y="130" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">enough evidence</text>

        <g>
          <rect x="460" y="100" width="160" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="540" y="128" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Act</text>
          <text x="540" y="148" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">structured answer</text>
          <text x="540" y="166" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">strict JSON · citations</text>
        </g>

        <path d="M 540 100 Q 470 30 400 100" fill="none" stroke="#B5B5B5" strokeDasharray="3 3" markerEnd="url(#arrow-loop)" />
        <text x="470" y="40" textAnchor="middle" fill="#B5B5B5" fontSize="10" fontFamily="Inter">no search yet · reminder, retry</text>

        <line x1="620" y1="140" x2="680" y2="140" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />

        <g>
          <rect x="680" y="100" width="160" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" strokeDasharray="3 2" />
          <text x="760" y="128" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Resolve</text>
          <text x="760" y="148" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">quote → (start, end)</text>
          <text x="760" y="166" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">deterministic · no retry</text>
        </g>

        <line x1="760" y1="180" x2="760" y2="215" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="780" y="208" fill="#FFFFFF" fontSize="11" fontFamily="Inter" fontWeight="600">ship</text>
      </svg>
    </div>
  )
}

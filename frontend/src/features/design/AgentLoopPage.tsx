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

    </article>
  )
}

function StateMachine() {
  return (
    <div className="my-2 border border-border rounded-md bg-surface p-6 md:p-10 overflow-x-auto">
      <svg viewBox="0 0 960 220" className="w-full max-w-[960px] mx-auto" role="img" aria-label="Agent loop state machine">
        <defs>
          <marker id="arrow-loop" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#B5B5B5" />
          </marker>
        </defs>

        {/* Rewrite */}
        <g>
          <rect x="20" y="120" width="150" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="95" y="148" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Rewrite</text>
          <text x="95" y="168" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">history → standalone Q</text>
          <text x="95" y="184" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">+ language detect</text>
        </g>

        {/* Rewrite → Gather */}
        <line x1="170" y1="160" x2="220" y2="160" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />

        {/* Gather */}
        <g>
          <rect x="230" y="120" width="150" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="305" y="148" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Gather</text>
          <text x="305" y="168" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">tool calls</text>
          <text x="305" y="184" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">≤ 5 tool calls</text>
        </g>

        {/* self-loop above Gather: more tools */}
        <path d="M 265 120 C 265 70, 345 70, 345 120" fill="none" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />
        <text x="305" y="62" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">more tools</text>

        {/* Gather → Act */}
        <line x1="380" y1="160" x2="430" y2="160" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />

        {/* Act */}
        <g>
          <rect x="440" y="120" width="150" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="515" y="148" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Act</text>
          <text x="515" y="168" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">structured answer</text>
          <text x="515" y="184" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">strict JSON · citations</text>
        </g>

        {/* Act → Resolve */}
        <line x1="590" y1="160" x2="640" y2="160" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />

        {/* Resolve */}
        <g>
          <rect x="650" y="120" width="150" height="80" fill="#0A0A0A" stroke="#FFFFFF" strokeWidth="1.5" strokeDasharray="3 2" />
          <text x="725" y="148" textAnchor="middle" fill="#FFFFFF" fontSize="14" fontWeight="600" fontFamily="Inter">Resolve</text>
          <text x="725" y="168" textAnchor="middle" fill="#B5B5B5" fontSize="11" fontFamily="Inter">quote → (start, end)</text>
          <text x="725" y="184" textAnchor="middle" fill="#6B6B6B" fontSize="10" fontFamily="Inter">deterministic · no retry</text>
        </g>

        {/* Resolve → ship */}
        <line x1="800" y1="160" x2="850" y2="160" stroke="#B5B5B5" markerEnd="url(#arrow-loop)" />

        {/* ship terminal */}
        <g>
          <rect x="860" y="135" width="80" height="50" fill="none" stroke="#FFFFFF" strokeWidth="1.5" />
          <text x="900" y="166" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontWeight="600" fontFamily="Inter">ship</text>
        </g>
      </svg>
    </div>
  )
}

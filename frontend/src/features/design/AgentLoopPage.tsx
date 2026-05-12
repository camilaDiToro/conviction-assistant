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
          <SpecItem term="agent_max_iterations = 12">Hard cap on loop turns (one LLM call per iteration). Hitting it raises <code className="font-mono text-[13px] text-ink-1">AgentError</code> — a safety net against runaway loops, not an expected exit.</SpecItem>
          <SpecItem term="≥ 1 search before answer (hard-coded invariant)">Tracked by counting <code className="font-mono text-[13px] text-ink-1">search_convictions</code> calls. An <code className="font-mono text-[13px] text-ink-1">AnswerOutput</code> emitted while the counter is zero is rejected and the agent is re-prompted with a directive to search (unless <code className="font-mono text-[13px] text-ink-1">out_of_scope=true</code>). Not a setting — the check lives in <code className="font-mono text-[13px] text-ink-1">_needs_search_first()</code>.</SpecItem>
          <SpecItem term='agent_reasoning_effort = "low"'>Default for the deployed model (<code className="font-mono text-[13px] text-ink-1">gpt-5.5</code>). The deterministic resolver catches misquotes and paraphrase post-hoc, so higher effort is reserved for controlled eval runs.</SpecItem>
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
  "conflict_detected": false,
  "conflict_statement": null,
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

      <Section eyebrow="System prompt">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The full agent system prompt — every directive the LLM sees on each call.
          Versioned: each eval report is stamped with{' '}
          <code className="font-mono text-[13px] text-ink-1">prompt_version</code> —
          an 8-char SHA-256 prefix of{' '}
          <code className="font-mono text-[13px] text-ink-1">app/agent/prompts/system.md</code> —
          so a run can be traced back to the exact prompt revision that produced its numbers.
        </p>
        <div className="border border-border rounded-md bg-surface relative">
          <div className="absolute top-2.5 left-3 text-[10px] uppercase tracking-tight text-ink-3 font-mono">
            system prompt · system.md
          </div>
          <pre className="font-mono text-[12px] leading-relaxed text-ink-1 p-4 pt-9 whitespace-pre-wrap">
{SYSTEM_PROMPT}
          </pre>
        </div>
      </Section>

    </article>
  )
}

const SYSTEM_PROMPT = `# Role

You are an **expert financial analyst** for Decade — fluent in Brazilian and global markets, fixed income, equities, real estate, derivatives, and tax mechanics. Every claim is grounded **strictly** in Decade's investment conviction documents and backed by a verbatim citation. Your audience is another professional analyst; speak with the precision and structure of a desk note.

# Domain priors

You bring baseline Brazilian-market knowledge to the desk: Selic / CDI / IPCA dynamics; fixed-income instruments (CDB, LCI / LCA / LCD, Tesouro Direto, debêntures, CRI / CRA); FGC deposit insurance; tax mechanics (IR regressivo, come-cotas, equity swing-trade exemption, isenções for PF); B3 equities and derivatives (DI futures, DOL / WDO, IND / WIN, options); fund structures (FIIs, FIPs, FIDCs, ETFs); and general portfolio-construction concepts (duration, carry, basis risk, hedge ratios). Use these priors to interpret the corpus and craft sharper queries.

**Priors do NOT replace citations.** Every factual claim in \`answer\` — specific numbers, thresholds, named programs, mechanics — still needs a passage citation. If a needed specific is not in the corpus, treat it as general knowledge per Rule A.

# Tools

Four read-only tools over the conviction corpus — \`list_documents\`, \`read_document_outline\`, \`search_convictions\`, \`read_passage\` — are exposed to you with full descriptions via the tools API. You have **at most 5 tool calls per question**.

# Citation contract

Every claim in your answer **MUST** carry a citation with:

- a \`passage_id\` returned by one of the tools, and
- a \`quote\` that is a **verbatim substring** of that passage's \`text\`.

The backend anchors your quote to a \`(start, end)\` region and highlights it in the UI. Non-verbatim quotes (paraphrased, fragmented, character-substituted) still render but lose the highlight. **Always copy verbatim from the \`read_passage\` result.**

Quotes must be one **contiguous run** of one passage — never paraphrase inside a quote, never combine fragments from different passages, never skip over intermediate content (paragraphs, examples, tables). If you need two separate regions of the same passage, pick the most important contiguous span and paraphrase the rest in \`answer\` under the same \`[N]\` marker.

## Comprehensiveness

Be **comprehensive within the cited evidence**. When a passage contains several distinct points relevant to the question, address each in \`answer\` — do not collapse a multi-bullet section into one sentence. Length follows the question: broad questions ("what is the thesis on X?", "compare X and Y") span the full breadth of cited material — mechanisms, history, risk caveats; narrow questions ("when does X apply?") stay tight.

## One citation per passage

Emit **at most one Citation per \`passage_id\`** — reuse the same \`[N]\` marker for every claim that passage backs. Pick a verbatim quote that covers as many sub-claims as possible; multi-line / multi-bullet quotes are encouraged when the passage's structure supports them. If one quote can't anchor everything, paraphrase the rest in \`answer\` under the same \`[N]\`.

## Inline citation markers

Place a literal \`[N]\` after each claim, where \`N\` is the **1-indexed** position in the \`citations\` array. Multiple refs after one claim: \`[1][2]\`. The frontend turns these into clickable links.

# Rule A — General knowledge MUST be marked very, very clearly

You MAY use general knowledge when the convictions don't fully cover a topic, but it MUST be marked clearly.

- **Prefer a real conviction reference**, even when tangential.
- **\`answer\` carries only claims literally supported by the cited passages.** Added framing, mechanisms, recommendations, or comparisons not present in the cited text are **general knowledge** — move to \`general_knowledge_section\` with \`general_knowledge_used: true\`, and prefix the section with "**Not from Decade convictions — general knowledge:**".
- **Never interleave or duplicate** gk and grounded claims. Each thought lives in exactly one field.

**Self-check:** for each sentence in \`answer\`, ask "is this a paraphrase of a cited passage, or the Rule B conflict statement?" If neither, it belongs in \`general_knowledge_section\`.

# Rule B — Conflicting convictions MUST be surfaced

When two or more cited passages contradict each other on the user's topic:

- **Cite all sides.** Never silently pick one; a "balanced trade-off synthesis" without naming the conflict is **not enough**. The analyst makes the judgment call — you do not pretend consensus exists.
- **Set \`conflict_detected: true\`.** This is the structural signal the audit layer reads — do not rely on prose alone.
- **Put the explicit disagreement statement in \`conflict_statement\`** — one short sentence in the user's language containing one of these literal phrases:
  - PT: "as convicções divergem" (or "as convicções discordam")
  - EN: "convictions disagree" (or "the convictions conflict")
  - ES: "las convicciones difieren" (or "las convicciones discrepan")
- When \`conflict_detected: false\`, set \`conflict_statement: null\`. Never set one without the other.

# Language mirroring

Respond in the **user's language** (PT / EN / ES). The entire \`answer\` field must be in that single language — do **not** embed source-language passages verbatim; paraphrase or summarise them. Source-language text belongs **only** in \`citations[].quote\`, which stays in the passage's **source language** (a PT passage's quote stays PT even if you answer in EN). The frontend renders quotes in a separate Citations block, so the user already sees the original wording there.

# Clarifying questions

Return \`kind: "clarifying_question"\` when the question is missing parameters needed for a useful answer — investment objective, horizon, risk tolerance, current allocation, or which of two similar instruments the user means (e.g. "LCI" when both LCI and LCA are in scope).

Personal-recommendation questions — anything of the form "should I…", "is now a good time to…", "what should I do with…" applied to an asset class or instrument — are clarify cases unless the user has already supplied horizon, current allocation, and risk view. A framework-conditional essay ("it depends on cycle / sector / valuation…") is **not** a substitute: the user is asking what *they* should do, and the corpus alone cannot answer that. Ask for the missing parameters first; answer in the follow-up turn.

If the user wrote a complete-enough question that you can reasonably interpret, **answer it** instead.

# Output schema

Your output is a single JSON object that matches the schema you were given. Two shapes:

- **\`kind: "answer"\`** — \`answer\`, \`citations\`, \`general_knowledge_used\`, \`general_knowledge_section\`, \`out_of_scope\`, \`conflict_detected\`, \`conflict_statement\` populated; \`question\`, \`options\` null.
- **\`kind: "clarifying_question"\`** — \`question\`, \`options\` populated; the answer-shape fields null.

## Out of scope

\`out_of_scope\` is about **whether the question is about investing**, not whether the corpus covers the topic.

Set \`out_of_scope: true\` ONLY for non-investing messages — greetings / small talk ("hi", "thanks", "ok") or off-topic asks (cooking, weather, programming, sports, personal advice). Reply briefly in the user's language: greetings get a polite hello + offer to help; off-topic asks get a polite decline. No tool calls; emit \`kind: "answer"\`, \`citations: []\`, \`general_knowledge_used: false\`, \`out_of_scope: true\`, \`conflict_detected: false\`.

**Do NOT** set \`out_of_scope: true\` for investing questions the corpus doesn't cover (foreign products, niche instruments, foreign jurisdictions). Search first; if nothing turns up, fall back to Rule A — cite the most tangentially-related passage and put the actual answer in \`general_knowledge_section\`. Refusing a real investment topic is worse than a marked gk answer.

Do **not** include the regulatory disclaimer in \`answer\` — the orchestrator appends it.

# Workflow

1. **Search.** Call \`search_convictions\` with focused query terms.
2. **Comparison questions** ("X or Y", "A vs B", "is it … or …"): run a **separate** \`search_convictions\` per side. BM25 ranks by term overlap, so a single search returns mainly the side whose terms appear in the question — the Rule B test requires actually retrieving the other side.
3. **Read.** Call \`read_passage\` **once** with every passage ID you intend to cite.
4. **Answer.** Emit the structured output with verbatim citations.

Do not produce an answer until you have called \`search_convictions\` at least once — the orchestrator rejects pre-search answers.

## Cite across multiple documents

A serious answer triangulates the corpus — **prefer citations drawn from two or more distinct documents** whenever the question reasonably allows it, and always for comparison / Rule B questions where each side typically lives in a different document. A single passage rarely captures the full picture: tributação, FGC, prazos and operational mechanics for one instrument are often split across an instrument-specific guide and the umbrella tributação doc. If your top BM25 hits all come from the same document, run a second \`search_convictions\` with terms that target adjacent documents (e.g. the tributação umbrella, sector overview, or the contrasting instrument) before you settle on citations. A one-document answer for a multi-document topic is a weak answer.`

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

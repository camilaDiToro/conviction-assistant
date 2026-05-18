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
          A separate LLM call takes <code className="font-mono text-[13px] text-ink-1">(history, new_user_message)</code>{' '}
          and returns <code className="font-mono text-[13px] text-ink-1">(standalone_question, language)</code>.
          The agent loop then sees <em>only</em> the system prompt and the standalone
          question — no prior turns.
        </p>
        <CodeBlock
          lang="python"
          code={`rewritten, language, _ = await rewrite_question(
    user_message, history, llm=llm,
)
messages = [
    Message(role="system", content=SYSTEM_PROMPT),
    Message(role="system", content=language_directive),
    Message(role="user",   content=rewritten),   # <- no prior turns
]`}
        />
      </Section>

      <Section eyebrow="The loop">
        <StateMachine />
        <ol className="max-w-prose text-ink-2 text-[15px] leading-relaxed list-decimal pl-5 space-y-2 mt-6">
          <li>
            <strong className="text-ink-1">Rewrite.</strong> Multi-turn history collapses into
            a standalone question + detected language.
          </li>
          <li>
            <strong className="text-ink-1">Gather.</strong> The agent calls tools (
            <code className="font-mono text-[13px] text-ink-1">search_convictions</code>,{' '}
            <code className="font-mono text-[13px] text-ink-1">read_passage</code>, …) and loops
            on itself until it has enough evidence — bounded at 5 calls.
          </li>
          <li>
            <strong className="text-ink-1">Act.</strong> The LLM emits a strict-JSON answer or a
            clarifying question. The shape is enforced at the provider boundary.
          </li>
          <li>
            <strong className="text-ink-1">Resolve.</strong> Each cited quote runs through{' '}
            <code className="font-mono text-[13px] text-ink-1">str.find</code> against its
            passage and becomes <code className="font-mono text-[13px] text-ink-1">(start, end)</code>.
            Deterministic — no LLM in this step.
          </li>
        </ol>
      </Section>

      <Section eyebrow="Bounds, enforced by the orchestrator">
        <SpecList>
          <SpecItem term="≤ 5 tool calls per turn">
            The 6th is refused with "tool budget exhausted" and the next iteration must answer.
          </SpecItem>
          <SpecItem term="≥ 1 search before any answer">
            An <code className="font-mono text-[13px] text-ink-1">AnswerOutput</code> with zero{' '}
            <code className="font-mono text-[13px] text-ink-1">search_convictions</code> calls
            behind it is rejected (unless{' '}
            <code className="font-mono text-[13px] text-ink-1">out_of_scope=true</code>). Hard-coded,
            not a setting.
          </SpecItem>
          <SpecItem term="≤ 12 iterations">
            Safety net against runaway loops. Hitting it raises{' '}
            <code className="font-mono text-[13px] text-ink-1">AgentError</code> — not an
            expected exit.
          </SpecItem>
          <SpecItem term="Strict JSON output">
            The provider adapter passes a JSON schema; the orchestrator never parses freeform text.
          </SpecItem>
        </SpecList>
      </Section>

      <Section eyebrow="System prompt">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed">
          Lives in{' '}
          <code className="font-mono text-[13px] text-ink-1">app/agent/prompts/system.md</code>.
          Every eval report is stamped with an 8-char SHA-256 prefix of it, so any run can be
          traced back to the exact prompt revision that produced its numbers.
        </p>
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

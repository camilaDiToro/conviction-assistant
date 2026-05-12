import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { PageHeader, Section } from '@/components/Section'

export default function EvalPage() {
  return (
    <article>
      <PageHeader
        eyebrow="Eval"
        title="Evaluation."
        lead={
          <>
            A hand-authored golden set, deterministic metrics that run on every change, and
            a separate LLM-as-judge layer for the semantic checks a regex cannot do. The
            headline number is anchor rate — what fraction of cited quotes resolved cleanly
            to an offset region of the source passage.
          </>
        }
      />

      <Section eyebrow="Question buckets">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The golden set distributes 34 questions across six buckets, each exercising a
          different behavior. Passing the suite means passing in every bucket — the
          aggregate hides regressions that only show up on Rule A / Rule B / clarify.
        </p>
        <div className="max-w-prose border border-border rounded-md divide-y divide-border">
          {BUCKETS.map(b => (
            <div
              key={b.name}
              className="px-5 py-4 grid grid-cols-1 md:grid-cols-[10rem_3rem_1fr] md:items-baseline gap-x-6 gap-y-1"
            >
              <code className="font-mono text-[13px] text-ink-1">{b.name}</code>
              <span className="text-ink-3 text-[12px] font-mono">n={b.n}</span>
              <p className="text-ink-2 text-[14px] leading-relaxed">{b.desc}</p>
            </div>
          ))}
        </div>
        <p className="max-w-prose text-ink-3 text-[13px] leading-relaxed mt-4">
          Total 34 · PT 15 · EN 15 · ES 4. The dataset lives at{' '}
          <code className="font-mono text-[12px] text-ink-1">evals/golden_set.yaml</code>{' '}
          — open the{' '}
          <Link to="/design/eval/dataset" className="text-ink-1 underline underline-offset-2 hover:text-ink-2">
            dataset &amp; results
          </Link>{' '}
          page to see every question and the latest run.
        </p>
      </Section>

      <Section eyebrow="Deterministic metrics">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          These run on the structured agent response without an LLM call. Cheap, fast,
          deterministic — they catch the failure modes a regex can prove. Source:{' '}
          <code className="font-mono text-[12px] text-ink-1">evals/metrics.py</code>.
        </p>
        <div className="max-w-prose border border-border rounded-md divide-y divide-border">
          {DET_METRICS.map(m => (
            <div
              key={m.name}
              className="px-5 py-4 grid grid-cols-1 md:grid-cols-[14rem_5rem_1fr] md:items-baseline gap-x-6 gap-y-1"
            >
              <code className="font-mono text-[13px] text-ink-1">{m.name}</code>
              <span className="text-ink-3 text-[12px] font-mono">{m.type}</span>
              <p className="text-ink-2 text-[14px] leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="LLM-as-judge — five semantic checks">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The judge layer reads each trace produced by the deterministic run and scores
          five rubrics that need reading comprehension — does the answer paraphrase only
          what was cited, does each <code className="font-mono text-[12px] text-ink-1">[N]</code>{' '}
          marker line up with the claim that precedes it, does the answer cover the
          substantive points present in the cited passages. Same prompt is fed to every
          record, so any two runs carrying the same{' '}
          <code className="font-mono text-[12px] text-ink-1">judge_prompt_hash</code>{' '}
          are comparable. Rule B disclosure is no longer scored here — it moved to the
          deterministic{' '}
          <code className="font-mono text-[12px] text-ink-1">conflict_disclosure_det</code>{' '}
          metric, which reads the agent's structured{' '}
          <code className="font-mono text-[12px] text-ink-1">conflict_detected</code>{' '}
          field directly.
        </p>
        <div className="max-w-prose border border-border rounded-md divide-y divide-border">
          {JUDGE_METRICS.map(m => (
            <div
              key={m.name}
              className="px-5 py-4 grid grid-cols-1 md:grid-cols-[14rem_1fr] md:items-baseline gap-x-6 gap-y-1"
            >
              <code className="font-mono text-[13px] text-ink-1">{m.name}</code>
              <p className="text-ink-2 text-[14px] leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Judge prompt">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          The prompt is versioned and its 8-char SHA-256 prefix lands in every judge
          record. The aggregator refuses to merge JSONL files whose records disagree on{' '}
          <code className="font-mono text-[12px] text-ink-1">(judge_model, judge_prompt_hash)</code>{' '}
          — two judge runs are only comparable when both signatures match. The full text
          lives in <code className="font-mono text-[12px] text-ink-1">evals/judge/prompt.md</code>.
        </p>
        <div className="border border-border rounded-md bg-surface relative">
          <div className="absolute top-2.5 left-3 text-[10px] uppercase tracking-tight text-ink-3 font-mono">
            judge prompt · prompt.md
          </div>
          <pre className="font-mono text-[12px] leading-relaxed text-ink-1 p-4 pt-9 whitespace-pre-wrap">
{JUDGE_PROMPT}
          </pre>
        </div>
      </Section>

      <Section eyebrow="How a run flows">
        <ol className="max-w-prose space-y-3 text-ink-2 text-[14px] leading-relaxed list-decimal pl-6">
          <li>
            <code className="font-mono text-[12px] text-ink-1">evals/run.py</code> loads
            the golden set, drives the agent question by question, and writes per-question
            rows to a CSV plus the full step traces to a sibling{' '}
            <code className="font-mono text-[12px] text-ink-1">_traces.jsonl</code>.
          </li>
          <li>
            Deterministic metrics are computed inline; the aggregate report and a
            per-question table land in{' '}
            <code className="font-mono text-[12px] text-ink-1">evals/results/&lt;timestamp&gt;_….md</code>.
          </li>
          <li>
            (Optional) The judge runs from Claude Code with{' '}
            <code className="font-mono text-[12px] text-ink-1">evals/judge/prompt.md</code>{' '}
            against the traces JSONL, producing a{' '}
            <code className="font-mono text-[12px] text-ink-1">_judge.jsonl</code> next to
            the CSV. <code className="font-mono text-[12px] text-ink-1">evals/judge/aggregate.py</code>{' '}
            merges deterministic + judge into a combined markdown report.
          </li>
          <li>
            <code className="font-mono text-[12px] text-ink-1">evals/compare.py</code>{' '}
            diffs two runs: aggregate deltas, per-bucket comparison, list of questions
            that regressed and list of improvements.
          </li>
        </ol>
        <div className="max-w-prose mt-8 space-y-3">
          <Link
            to="/design/eval/dataset"
            className="flex items-baseline justify-between gap-4 px-5 py-4 border border-border rounded-md hover:bg-surface-2 transition-colors group"
          >
            <div className="min-w-0">
              <code className="font-mono text-[11px] text-ink-3">/design/eval/dataset</code>
              <div className="text-ink-1 font-medium tracking-tight mt-0.5">
                Dataset &amp; results
              </div>
              <div className="text-ink-3 text-sm mt-0.5 leading-relaxed">
                Every question in the golden set and the latest deterministic run report.
              </div>
            </div>
            <ArrowRight size={14} className="text-ink-3 group-hover:text-ink-1 shrink-0 transition-colors" />
          </Link>
          <Link
            to="/design/eval/chat"
            className="flex items-baseline justify-between gap-4 px-5 py-4 border border-border rounded-md hover:bg-surface-2 transition-colors group"
          >
            <div className="min-w-0">
              <code className="font-mono text-[11px] text-ink-3">/design/eval/chat</code>
              <div className="text-ink-1 font-medium tracking-tight mt-0.5">
                Latest run as chat
              </div>
              <div className="text-ink-3 text-sm mt-0.5 leading-relaxed">
                The 35 question/answer pairs from the latest run, rendered in the real chat UI.
                Click <em>view eval</em> on any turn for deterministic + judge metrics.
              </div>
            </div>
            <ArrowRight size={14} className="text-ink-3 group-hover:text-ink-1 shrink-0 transition-colors" />
          </Link>
        </div>
      </Section>
    </article>
  )
}

const BUCKETS = [
  {
    name: 'factual',
    n: 17,
    desc: "A direct question whose answer is in the corpus. Two are multiturn — the standalone follow-up is meaningless without the prior turn, so the rewrite stage is what's being tested.",
  },
  {
    name: 'rule_a',
    n: 6,
    desc: 'The corpus mentions the topic only tangentially. The agent must cite the tangential passage and put general-knowledge content in a clearly marked section — never silently mix the two.',
  },
  {
    name: 'rule_b',
    n: 4,
    desc: 'Two convictions take opposite positions. The agent must cite both sides and explicitly state that the convictions disagree, not silently pick one.',
  },
  {
    name: 'cross_lang',
    n: 3,
    desc: 'Spanish queries against the PT/EN corpus. Tests retrieval generalization on a language the corpus does not contain.',
  },
  {
    name: 'out_of_scope',
    n: 2,
    desc: 'Off-topic question with zero tangential corpus touch. Right behavior is refuse — and gen-knowledge fallback is explicitly forbidden.',
  },
  {
    name: 'clarify',
    n: 3,
    desc: 'Ambiguous question (objective? horizon? risk tolerance?). Right behavior is ask, not guess.',
  },
] as const

const DET_METRICS = [
  {
    name: 'anchor_rate',
    type: 'numeric',
    desc: 'Headline. Fraction of cited quotes that resolved to an offset region in their cited passage. A failed anchor means the model emitted a quote that did not literally appear in the passage it pointed to.',
  },
  {
    name: 'citation_precision',
    type: 'numeric',
    desc: 'For questions with an expected passage set: fraction of cited passages that are in the expected set.',
  },
  {
    name: 'citation_recall',
    type: 'numeric',
    desc: 'For questions with an expected passage set: fraction of expected passages that were cited.',
  },
  {
    name: 'refusal_correctness',
    type: 'discrete',
    desc: 'Agent refused iff bucket is out_of_scope. Two-direction — false refusals on in-scope questions also penalised.',
  },
  {
    name: 'general_knowledge_correctness',
    type: 'discrete',
    desc: 'Rule A: was the general_knowledge_used flag set correctly given whether the corpus actually covers the topic?',
  },
  {
    name: 'clarify_correctness',
    type: 'discrete',
    desc: 'Agent asked a clarifying question iff bucket is clarify.',
  },
  {
    name: 'meets_min_citations',
    type: 'discrete',
    desc: 'Distinct citations ≥ must_cite_at_least (per-question floor from the golden set).',
  },
  {
    name: 'conflict_min_citations',
    type: 'discrete',
    desc: 'Rule B precondition: ≥ 2 distinct citations when expected_conflict_mention=true. Pairs with conflict_disclosure_det to fully replace the previous LLM-judge rubric.',
  },
  {
    name: 'conflict_disclosure_det',
    type: 'discrete',
    desc: "Rule B semantic: did the agent emit conflict_detected=true with a conflict_statement carrying a canonical marker phrase (divergem / disagree / difieren / conflitam)? Replaces the LLM-judge rubric — the structured field is the source of truth.",
  },
  {
    name: 'language_match',
    type: 'discrete',
    desc: "Answer (or clarifying question) is in the user's language.",
  },
  {
    name: 'tokens / tool_calls / duration_ms',
    type: 'numeric',
    desc: 'Provider token counters summed across LLM steps, executed tool calls, wall-clock per question.',
  },
] as const

const JUDGE_METRICS = [
  {
    name: 'faithfulness',
    desc: 'n_supported / n_sentences. For each sentence in answer, decide whether the cited passages entail it. Loose paraphrase is fine; added framing or recommendations are not.',
  },
  {
    name: 'answer_relevancy',
    desc: 'relevant | partial | off_topic. Does the answer address what the user actually asked (regardless of grounding quality)?',
  },
  {
    name: 'rule_a_purity',
    desc: 'clean | leaked. Is the main answer free of general-knowledge content that should have been in general_knowledge_section?',
  },
  {
    name: 'citation_attribution',
    desc: 'n_correct / n_markers. For each [N] marker, does citation N actually support the claim immediately preceding it?',
  },
  {
    name: 'completeness',
    desc: 'complete | partial | shallow. Given the cited passages, how thoroughly did the answer cover the substantive points the user asked about?',
  },
] as const

const JUDGE_PROMPT = `You are an evaluator scoring a grounded-QA agent against six rubric criteria.
The agent answers user questions strictly grounded on a set of investment-conviction
documents and emits structured output with verbatim citations.

Your output is a single JSON object validating against the JudgeResult schema. No
prose, no markdown, no commentary outside the JSON.

Inputs you are given (per question):
  id, bucket (factual | rule_a | rule_b | cross_lang | out_of_scope | clarify),
  language (pt | es | en), question, expected_passage_ids, expected_out_of_scope,
  expected_general_knowledge, expected_conflict_mention, must_cite_at_least,
  output_kind (answer | clarifying_question), answer (with [N] markers intact)
  or clarifying_question, general_knowledge_used, general_knowledge_section,
  out_of_scope, citations[] (marker, passage_id, document_title, heading_path,
  passage_text, anchored — full passage_text given for every cited passage).

Six rubrics:

1. faithfulness (numeric, n_supported / n_sentences)
   For each sentence in answer, decide whether the cited passages entail it
   (information present, possibly paraphrased) or do not.
   - n_sentences = number of distinct factual sentences in answer. Skip
     section headers and any sentence in general_knowledge_section.
   - Supported when the union of citations[].passage_text literally states or
     directly implies it. Loose paraphrase ok; added framing, recommendations
     or extra facts are not supported.
   - score = n_supported / n_sentences (3 decimals). List up to 5 unsupported
     sentences verbatim.
   - Edge cases: clarifying-question and out-of-scope refusal turns → score 1.0,
     n_sentences=0.

2. answer_relevancy (discrete: relevant | partial | off_topic)
   Does the answer address what the user actually asked?
   relevant=1.0, partial=0.5, off_topic=0.0.

3. conflict_disclosure (discrete: yes | no | n/a)
   Applicable only when bucket == "rule_b". Did the answer explicitly state
   that the convictions disagree on this topic?
   - yes (1.0): explicit disagreement marker — "the convictions disagree on
     this", "discordam", "divergem", "trade-off entre", "conflicting views",
     a section that opposes one conviction to another. Citing both sides is
     necessary but not sufficient — the answer must call out the conflict in
     words.
   - no (0.0): silent presentation of one or both sides without naming the
     disagreement.

4. rule_a_purity (discrete: clean | leaked | n/a)
   Applicable when output_kind == "answer" and out_of_scope == false.
   Does answer carry general-knowledge content that should have been in
   general_knowledge_section?
   - clean (1.0): every sentence in answer is a paraphrase of cited content
     or the explicit Rule-B conflict-disclosure sentence.
   - leaked (0.0): answer contains framing, recommendations, mechanisms,
     comparisons or context not supported by the cited passages. List up to
     5 leaked sentences. A leaked Rule A is also a faithfulness failure.

5. citation_attribution (numeric, n_correct / n_markers)
   For each [N] marker, decide whether citation N actually supports the claim
   immediately preceding the marker. Deduplicate adjacent markers like [1][2]
   into 2 markers (not 1). Edge: n_markers == 0 → score 1.0.

6. completeness (discrete: complete | partial | shallow | n/a)
   Applicable when output_kind == "answer" with at least one citation.
   complete=1.0 (covers the main points present in the cited material that
   map to the question), partial=0.5, shallow=0.0. Use missing to list
   (≤ 240 chars) the substantive points the answer skipped.

Hard rules (the validator enforces):
  1. label and score must agree per the tables above.
  2. conflict_disclosure.applicable is true iff bucket == "rule_b".
  3. rule_a_purity.label == "leaked" requires ≥ 1 leaked_sentences entry.
  4. n_supported ≤ n_sentences, n_correct ≤ n_markers.
  5. unsupported and leaked_sentences capped at 5 entries.
  6. All reason and missing fields capped at 240 characters.
  7. Skip records where output_kind is empty (error rows from the runner).`

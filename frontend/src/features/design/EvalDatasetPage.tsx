import { useState } from 'react'
import { PageHeader, Section } from '@/components/Section'
import {
  EVAL_AGGREGATE,
  EVAL_BUCKET_RESULTS,
  EVAL_JUDGE_AGGREGATE,
  EVAL_JUDGE_BUCKET_RESULTS,
  EVAL_MOCK,
  EVAL_MOCK_META,
  EVAL_PER_QUESTION,
  EVAL_RUN_META_ROWS,
} from '@/data/eval_mock'

type Bucket = 'factual' | 'rule_a' | 'rule_b' | 'cross_lang' | 'out_of_scope' | 'clarify'
type Lang = 'pt' | 'en' | 'es'

interface DatasetEntry {
  id: string
  bucket: Bucket
  lang: Lang
  question: string
  expected: number
}

const DATASET: DatasetEntry[] = EVAL_MOCK.map(record => ({
  id: record.id,
  bucket: record.bucket as Bucket,
  lang: record.language,
  question: record.question,
  expected: record.expected.passage_ids.length,
}))

export default function EvalDatasetPage() {
  const [tab, setTab] = useState<'dataset' | 'results'>('dataset')
  const [bucketFilter, setBucketFilter] = useState<Bucket | 'all'>('all')

  const filtered = bucketFilter === 'all'
    ? DATASET
    : DATASET.filter(e => e.bucket === bucketFilter)

  return (
    <article>
      <PageHeader
        eyebrow="Eval · dataset & results"
        title="The set, and the latest run."
        lead={
          <>
            The 34 hand-authored questions on the left, and the most recent deterministic
            run report on the right. Source files:{' '}
            <code className="font-mono text-[14px] text-ink-1">evals/golden_set.yaml</code>{' '}
            and{' '}
            <code className="font-mono text-[14px] text-ink-1">evals/results/&lt;timestamp&gt;_…</code>.
          </>
        }
      />

      <div className="mt-8 mb-6 flex items-center gap-1 border-b border-border">
        <TabButton active={tab === 'dataset'} onClick={() => setTab('dataset')}>
          Dataset ({DATASET.length})
        </TabButton>
        <TabButton active={tab === 'results'} onClick={() => setTab('results')}>
          Latest run
        </TabButton>
      </div>

      {tab === 'dataset' ? (
        <Section eyebrow="Golden set">
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <span className="text-ink-3 text-[11px] uppercase tracking-tight font-medium mr-2">
              Filter
            </span>
            {(['all', 'factual', 'rule_a', 'rule_b', 'cross_lang', 'out_of_scope', 'clarify'] as const).map(b => {
              const count = b === 'all' ? DATASET.length : DATASET.filter(e => e.bucket === b).length
              const active = bucketFilter === b
              return (
                <button
                  key={b}
                  onClick={() => setBucketFilter(b)}
                  className={[
                    'text-[12px] font-mono px-2.5 py-1 rounded-md border transition-colors',
                    active
                      ? 'border-ink-1 text-ink-1 bg-surface-2'
                      : 'border-border text-ink-3 hover:text-ink-1 hover:border-ink-3',
                  ].join(' ')}
                >
                  {b} <span className="text-ink-4">·{count}</span>
                </button>
              )
            })}
          </div>

          <div className="border border-border rounded-md overflow-x-auto">
            <table className="w-full text-[13px] leading-relaxed">
              <thead className="bg-surface text-ink-3 text-[11px] uppercase tracking-tight">
                <tr>
                  <th className="text-left px-3 py-2 font-medium w-[3rem]">id</th>
                  <th className="text-left px-3 py-2 font-medium w-[6rem]">bucket</th>
                  <th className="text-left px-3 py-2 font-medium w-[3rem]">lang</th>
                  <th className="text-left px-3 py-2 font-medium">question</th>
                  <th className="text-left px-3 py-2 font-medium w-[6rem]">expected</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filtered.map(e => (
                  <tr key={e.id} className="hover:bg-surface-2 transition-colors">
                    <td className="px-3 py-2 font-mono text-ink-1 align-top">{e.id}</td>
                    <td className="px-3 py-2 font-mono text-ink-2 align-top">{e.bucket}</td>
                    <td className="px-3 py-2 font-mono text-ink-2 align-top uppercase">{e.lang}</td>
                    <td className="px-3 py-2 text-ink-1 align-top">{e.question}</td>
                    <td className="px-3 py-2 font-mono text-ink-3 align-top">
                      {e.expected > 0 ? `${e.expected} passage${e.expected > 1 ? 's' : ''}` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      ) : (
        <ResultsPanel />
      )}
    </article>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={[
        'px-4 py-2.5 text-[13px] tracking-tight border-b-2 -mb-px transition-colors',
        active
          ? 'border-ink-1 text-ink-1'
          : 'border-transparent text-ink-3 hover:text-ink-1',
      ].join(' ')}
    >
      {children}
    </button>
  )
}

function ResultsPanel() {
  return (
    <>
      <Section eyebrow="Run metadata">
        <p className="max-w-prose text-ink-2 text-[15px] leading-relaxed mb-6">
          Most recent full run on the 34-question set. The deterministic CSV and
          LLM-as-judge layer cover{' '}
          <code className="font-mono text-[12px] text-ink-1">
            {EVAL_MOCK_META.judge_question_count}/{EVAL_MOCK_META.question_count}
          </code>{' '}
          questions.
        </p>
        <div className="max-w-prose border border-border rounded-md divide-y divide-border text-[13px]">
          {EVAL_RUN_META_ROWS.map(([k, v]) => (
            <div key={k} className="px-4 py-2 grid grid-cols-[12rem_1fr] gap-x-4">
              <code className="font-mono text-ink-3">{k}</code>
              <code className="font-mono text-ink-1">{v}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section eyebrow="Aggregate metrics">
        <div className="max-w-prose border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[13px] leading-relaxed">
            <thead className="bg-surface text-ink-3 text-[11px] uppercase tracking-tight">
              <tr>
                <th className="text-left px-4 py-2 font-medium">metric</th>
                <th className="text-left px-4 py-2 font-medium">value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {EVAL_AGGREGATE.map(([k, v]) => (
                <tr key={k}>
                  <td className="px-4 py-2 text-ink-1">{k}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="LLM-as-judge aggregate">
        <div className="max-w-prose border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[13px] leading-relaxed">
            <thead className="bg-surface text-ink-3 text-[11px] uppercase tracking-tight">
              <tr>
                <th className="text-left px-4 py-2 font-medium">metric</th>
                <th className="text-left px-4 py-2 font-medium">score</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {EVAL_JUDGE_AGGREGATE.map(([k, v]) => (
                <tr key={k}>
                  <td className="px-4 py-2 text-ink-1">{k}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="Judge per-bucket">
        <div className="max-w-prose border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[13px] leading-relaxed">
            <thead className="bg-surface text-ink-3 text-[11px] uppercase tracking-tight">
              <tr>
                <th className="text-left px-4 py-2 font-medium">bucket</th>
                <th className="text-left px-4 py-2 font-medium">N</th>
                <th className="text-left px-4 py-2 font-medium">faith</th>
                <th className="text-left px-4 py-2 font-medium">relevancy</th>
                <th className="text-left px-4 py-2 font-medium">purity</th>
                <th className="text-left px-4 py-2 font-medium">attrib</th>
                <th className="text-left px-4 py-2 font-medium">complete</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {EVAL_JUDGE_BUCKET_RESULTS.map(b => (
                <tr key={b.bucket}>
                  <td className="px-4 py-2 font-mono text-ink-1">{b.bucket}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.n}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.faithfulness}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.answer_relevancy}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.rule_a_purity}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.citation_attribution}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.completeness}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="Per-bucket anchor rate">
        <div className="max-w-prose border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[13px] leading-relaxed">
            <thead className="bg-surface text-ink-3 text-[11px] uppercase tracking-tight">
              <tr>
                <th className="text-left px-4 py-2 font-medium">bucket</th>
                <th className="text-left px-4 py-2 font-medium">N</th>
                <th className="text-left px-4 py-2 font-medium">anchor</th>
                <th className="text-left px-4 py-2 font-medium">tokens (mean)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {EVAL_BUCKET_RESULTS.map(b => (
                <tr key={b.bucket}>
                  <td className="px-4 py-2 font-mono text-ink-1">{b.bucket}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.n}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{b.anchor}</td>
                  <td className="px-4 py-2 font-mono text-ink-3">{b.tokens}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section eyebrow="Per-question results">
        <div className="border border-border rounded-md overflow-x-auto">
          <table className="w-full text-[12px] leading-relaxed">
            <thead className="bg-surface text-ink-3 text-[11px] uppercase tracking-tight">
              <tr>
                <th className="text-left px-3 py-2 font-medium">id</th>
                <th className="text-left px-3 py-2 font-medium">bucket</th>
                <th className="text-left px-3 py-2 font-medium">lang</th>
                <th className="text-left px-3 py-2 font-medium">cites</th>
                <th className="text-left px-3 py-2 font-medium">anchor</th>
                <th className="text-left px-3 py-2 font-medium">prec</th>
                <th className="text-left px-3 py-2 font-medium">recall</th>
                <th className="text-left px-3 py-2 font-medium">refusal</th>
                <th className="text-left px-3 py-2 font-medium">gen-know</th>
                <th className="text-left px-3 py-2 font-medium">conflict</th>
                <th className="text-left px-3 py-2 font-medium">lang-m</th>
                <th className="text-left px-3 py-2 font-medium">faith</th>
                <th className="text-left px-3 py-2 font-medium">attrib</th>
                <th className="text-left px-3 py-2 font-medium">comp</th>
                <th className="text-left px-3 py-2 font-medium">tools</th>
                <th className="text-left px-3 py-2 font-medium">ms</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border font-mono">
              {EVAL_PER_QUESTION.map(r => (
                <tr key={r.id} className="hover:bg-surface-2 transition-colors">
                  <td className="px-3 py-2 text-ink-1">{r.id}</td>
                  <td className="px-3 py-2 text-ink-2">{r.bucket}</td>
                  <td className="px-3 py-2 text-ink-2 uppercase">{r.lang}</td>
                  <td className="px-3 py-2 text-ink-3">{r.citations}</td>
                  <td className={['px-3 py-2', r.anchor === '1.000' ? 'text-ink-1' : 'text-ink-3'].join(' ')}>{r.anchor}</td>
                  <td className="px-3 py-2 text-ink-2">{r.prec}</td>
                  <td className="px-3 py-2 text-ink-2">{r.recall}</td>
                  <td className={['px-3 py-2', r.refusal === 'incorrect' ? 'text-red-400' : 'text-ink-3'].join(' ')}>{r.refusal}</td>
                  <td className={['px-3 py-2', r.genKnow === 'incorrect' ? 'text-red-400' : 'text-ink-3'].join(' ')}>{r.genKnow}</td>
                  <td className={['px-3 py-2', r.conflict === 'incorrect' ? 'text-red-400' : 'text-ink-3'].join(' ')}>{r.conflict}</td>
                  <td className="px-3 py-2 text-ink-3">{r.langMatch}</td>
                  <td className="px-3 py-2 text-ink-2">{r.faithfulness}</td>
                  <td className="px-3 py-2 text-ink-2">{r.attribution}</td>
                  <td className="px-3 py-2 text-ink-2">{r.completeness}</td>
                  <td className="px-3 py-2 text-ink-3">{r.tools}</td>
                  <td className="px-3 py-2 text-ink-3">{r.ms}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </>
  )
}

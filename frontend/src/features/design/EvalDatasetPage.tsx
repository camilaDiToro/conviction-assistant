import { useState } from 'react'
import { PageHeader, Section } from '@/components/Section'

type Bucket = 'factual' | 'rule_a' | 'rule_b' | 'cross_lang' | 'out_of_scope' | 'clarify'
type Lang = 'pt' | 'en' | 'es'

interface DatasetEntry {
  id: string
  bucket: Bucket
  lang: Lang
  question: string
  expected: number
  flags?: string
  multiturn?: boolean
}

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
            The 35 hand-authored questions on the left, and the most recent deterministic
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
          Most recent full run on the 35-question set. The same run produces three artifacts
          alongside a raw <code className="font-mono text-[12px] text-ink-1">_traces.jsonl</code>{' '}
          that feeds the LLM-as-judge layer.
        </p>
        <div className="max-w-prose border border-border rounded-md divide-y divide-border text-[13px]">
          {RUN_META.map(([k, v]) => (
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
              {AGGREGATE.map(([k, v]) => (
                <tr key={k}>
                  <td className="px-4 py-2 text-ink-1">{k}</td>
                  <td className="px-4 py-2 font-mono text-ink-2">{v}</td>
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
              {BUCKET_RESULTS.map(b => (
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
                <th className="text-left px-3 py-2 font-medium">lang-m</th>
                <th className="text-left px-3 py-2 font-medium">tools</th>
                <th className="text-left px-3 py-2 font-medium">ms</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border font-mono">
              {PER_QUESTION.map(r => (
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
                  <td className="px-3 py-2 text-ink-3">{r.langMatch}</td>
                  <td className="px-3 py-2 text-ink-3">{r.tools}</td>
                  <td className="px-3 py-2 text-ink-3">{r.ms}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="max-w-prose text-ink-3 text-[13px] leading-relaxed mt-4">
          Two rows mark <code className="font-mono text-[12px] text-ink-1">gen-know: incorrect</code>{' '}
          — q15 and q16 were re-bucketed in 0003-v2 from rule_a to factual once the corpus
          coverage was verified end-to-end. The agent still fires the general-knowledge flag
          for those, which the metric now flags. Anchor rate stays 1.000 across all 31
          citing questions.
        </p>
      </Section>
    </>
  )
}

const DATASET: DatasetEntry[] = [
  { id: 'q01', bucket: 'factual', lang: 'pt', question: 'Como funciona a tributação dos CDBs e a tabela regressiva de IR?', expected: 2 },
  { id: 'q02', bucket: 'factual', lang: 'pt', question: 'Qual o limite de cobertura do FGC para CDBs por CPF?', expected: 2 },
  { id: 'q03', bucket: 'factual', lang: 'pt', question: 'LCI e LCA são isentas de Imposto de Renda para pessoa física?', expected: 1 },
  { id: 'q04', bucket: 'factual', lang: 'pt', question: 'O que é o come-cotas em fundos de renda fixa e quando incide?', expected: 2 },
  { id: 'q05', bucket: 'factual', lang: 'pt', question: 'Qual a diferença entre PGBL e VGBL na mecânica fiscal?', expected: 1 },
  { id: 'q06', bucket: 'factual', lang: 'en', question: 'How does BDR pricing work and what is the BDR fair value formula?', expected: 1 },
  { id: 'q07', bucket: 'factual', lang: 'en', question: 'What are the requirements for listing on Novo Mercado on B3?', expected: 1 },
  { id: 'q08', bucket: 'factual', lang: 'en', question: 'What is the blackout period before earnings disclosure under CVM rules?', expected: 1 },
  { id: 'q09', bucket: 'factual', lang: 'en', question: 'How are incentivized debentures (Law 12.431) taxed for individuals?', expected: 2 },
  { id: 'q10', bucket: 'factual', lang: 'en', question: 'What is the minimum investment for a Qualified Foreign Investor under CMN Resolution 4,373?', expected: 2 },
  { id: 'q11', bucket: 'factual', lang: 'en', question: 'How to spot an unsustainable dividend that may be cut?', expected: 1 },
  { id: 'q12', bucket: 'factual', lang: 'pt', question: 'ETFs têm a isenção de R$20.000 por mês como ações?', expected: 2 },
  { id: 'q31', bucket: 'factual', lang: 'pt', question: 'O que é a estratégia de Escada (Laddering) em Tesouro Direto e em que cenário ela faz sentido?', expected: 1, flags: 'coverage-gap' },
  { id: 'q32', bucket: 'factual', lang: 'en', question: 'What is the monthly exemption threshold for crypto sales in Brazil and the applicable tax-rate structure?', expected: 1, flags: 'coverage-gap' },
  { id: 'q33', bucket: 'factual', lang: 'pt', question: 'Como funcionam a taxa de administração e a taxa de performance em fundos multimercado brasileiros?', expected: 1, flags: 'coverage-gap' },
  { id: 'q13', bucket: 'rule_a', lang: 'pt', question: 'Quais são as principais características e vantagens fiscais de uma Roth IRA como veículo de aposentadoria nos Estados Unidos?', expected: 0, flags: 'gen-knowledge expected' },
  { id: 'q14', bucket: 'rule_a', lang: 'en', question: 'What are the typical pros and cons of dynamic versus static hedging for portfolio currency risk?', expected: 0, flags: 'gen-knowledge expected' },
  { id: 'q15', bucket: 'factual', lang: 'en', question: 'How do Brazilian exporters typically hedge USD revenues when their costs are in BRL?', expected: 0, flags: 're-bucketed v2' },
  { id: 'q16', bucket: 'factual', lang: 'en', question: 'What protections does B3 provide if a broker defaults during a trade settlement?', expected: 0, flags: 're-bucketed v2' },
  { id: 'q17', bucket: 'rule_b', lang: 'pt', question: 'Vale mais a pena montar o núcleo de ações em ETFs passivos como BOVA11 e SMAL11, ou um gestor ativo de small caps consegue entregar retorno superior consistente após taxas?', expected: 0, flags: 'conflict expected' },
  { id: 'q18', bucket: 'rule_b', lang: 'pt', question: 'Os FIIs operam como classe de renda recorrente sob a regra de distribuição compulsória de 95% dos resultados, ou os FIIs de desenvolvimento são incompatíveis com um mandato de renda?', expected: 0, flags: 'conflict expected' },
  { id: 'q19', bucket: 'rule_b', lang: 'en', question: 'For a 30-year-old Brazilian investor with only BRL liabilities, is dollar exposure via IVVB11 a portfolio necessity or an optional diversification?', expected: 0, flags: 'conflict expected' },
  { id: 'q20', bucket: 'rule_b', lang: 'pt', question: 'Para um colchão de longo prazo, é melhor concentrar em Tesouro IPCA+ direto ou priorizar debêntures incentivadas que oferecem IPCA+ sem IR e taxas reais superiores?', expected: 0, flags: 'conflict expected' },
  { id: 'q21', bucket: 'cross_lang', lang: 'es', question: '¿Cómo se calculan los impuestos sobre los CDB en Brasil?', expected: 1 },
  { id: 'q22', bucket: 'cross_lang', lang: 'es', question: '¿Qué son los fondos inmobiliarios brasileños (FII) y cómo se gravan?', expected: 2 },
  { id: 'q23', bucket: 'cross_lang', lang: 'es', question: 'Estrategias de dolarización para inversores brasileños', expected: 1 },
  { id: 'q24', bucket: 'rule_a', lang: 'pt', question: 'Como o tratado tributário Brasil-EUA afeta a tributação de dividendos de REITs americanos para residentes brasileiros?', expected: 0, flags: 're-bucketed v2 · gen-knowledge expected' },
  { id: 'q25', bucket: 'out_of_scope', lang: 'en', question: "What's the best way to learn Python programming as a beginner?", expected: 0, flags: 'refuse expected' },
  { id: 'q26', bucket: 'rule_a', lang: 'en', question: 'Should I speculate on iron ore futures on B3, or invest directly in mining companies — what position size, what stop-loss?', expected: 0, flags: 're-bucketed v2 · gen-knowledge expected' },
  { id: 'q27', bucket: 'out_of_scope', lang: 'pt', question: 'Qual o melhor restaurante para almoço de negócios em Faria Lima?', expected: 0, flags: 'refuse expected' },
  { id: 'q28', bucket: 'clarify', lang: 'pt', question: 'Qual o melhor fundo para mim?', expected: 0, flags: 'clarify expected' },
  { id: 'q29', bucket: 'clarify', lang: 'en', question: 'Is now a good time to invest in equities?', expected: 0, flags: 'clarify expected' },
  { id: 'q30', bucket: 'clarify', lang: 'es', question: '¿Cuánto debo destinar a derivados?', expected: 0, flags: 'clarify expected' },
  { id: 'q34', bucket: 'factual', lang: 'pt', question: 'Para CDB de 25 meses.', expected: 1, multiturn: true },
  { id: 'q35', bucket: 'factual', lang: 'en', question: 'Does it cover LCAs as well?', expected: 1, multiturn: true },
]

const RUN_META: ReadonlyArray<[string, string]> = [
  ['timestamp', '2026-05-12_13-28-45'],
  ['provider', 'openai'],
  ['model', 'gpt-5.5'],
  ['reasoning_effort', 'low'],
  ['agent_max_tool_calls', '5'],
  ['agent_max_output_tokens', '8192'],
  ['git_sha', '7281e22'],
  ['subset', 'full'],
  ['with_judge', 'False'],
  ['prompt_version', '54fd65ee'],
]

const AGGREGATE: ReadonlyArray<[string, string]> = [
  ['Questions evaluated', '35'],
  ['Anchor rate (headline)', '1.000 (across 31 citing questions)'],
  ['Citation precision', '0.875 (across 20 questions with expected ids)'],
  ['Citation recall', '0.875 (across 20 questions with expected ids)'],
  ['Refusal correctness', '1.000 (33/33)'],
  ['General-knowledge correctness', '0.935 (29/31)'],
  ['Clarify correctness', '0.667 (2/3)'],
  ['Meets min citations', '1.000 (29/29)'],
  ['Conflict min citations (Rule B precondition)', '1.000 (4/4)'],
  ['Language match', '1.000 (35/35)'],
  ['Tokens total', '629,606'],
  ['Tokens mean / p95', '17,989 / 26,282'],
  ['Prompt / completion tokens', '579,622 / 49,984'],
  ['Cached / reasoning tokens', '308,224 / 1,133'],
  ['Tool calls (mean)', '2.37'],
  ['Duration mean / p95', '26,354ms / 52,769ms'],
]

const BUCKET_RESULTS = [
  { bucket: 'clarify', n: 3, anchor: '1.000', tokens: '11,289' },
  { bucket: 'cross_lang', n: 3, anchor: '1.000', tokens: '24,023' },
  { bucket: 'factual', n: 17, anchor: '1.000', tokens: '17,883' },
  { bucket: 'out_of_scope', n: 2, anchor: '—', tokens: '3,830' },
  { bucket: 'rule_a', n: 6, anchor: '1.000', tokens: '20,913' },
  { bucket: 'rule_b', n: 4, anchor: '1.000', tokens: '21,629' },
] as const

interface PerQ {
  id: string
  bucket: string
  lang: string
  citations: string
  anchor: string
  prec: string
  recall: string
  refusal: string
  genKnow: string
  langMatch: string
  tools: number
  ms: number
}

const PER_QUESTION: ReadonlyArray<PerQ> = [
  { id: 'q01', bucket: 'factual', lang: 'pt', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 26333 },
  { id: 'q02', bucket: 'factual', lang: 'pt', citations: '1 (1 anch)', anchor: '1.000', prec: '0.500', recall: '0.500', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 10614 },
  { id: 'q03', bucket: 'factual', lang: 'pt', citations: '2 (2 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 22756 },
  { id: 'q04', bucket: 'factual', lang: 'pt', citations: '2 (2 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 20958 },
  { id: 'q05', bucket: 'factual', lang: 'pt', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 4, ms: 31014 },
  { id: 'q06', bucket: 'factual', lang: 'en', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 19896 },
  { id: 'q07', bucket: 'factual', lang: 'en', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 29986 },
  { id: 'q08', bucket: 'factual', lang: 'en', citations: '1 (1 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 10947 },
  { id: 'q09', bucket: 'factual', lang: 'en', citations: '3 (3 anch)', anchor: '1.000', prec: '0.500', recall: '0.500', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 22824 },
  { id: 'q10', bucket: 'factual', lang: 'en', citations: '1 (1 anch)', anchor: '1.000', prec: '0.500', recall: '0.500', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 9520 },
  { id: 'q11', bucket: 'factual', lang: 'en', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 29206 },
  { id: 'q12', bucket: 'factual', lang: 'pt', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 17956 },
  { id: 'q31', bucket: 'factual', lang: 'pt', citations: '4 (4 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 32554 },
  { id: 'q32', bucket: 'factual', lang: 'en', citations: '1 (1 anch)', anchor: '1.000', prec: '0.000', recall: '0.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 15520 },
  { id: 'q33', bucket: 'factual', lang: 'pt', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 44078 },
  { id: 'q13', bucket: 'rule_a', lang: 'pt', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 27146 },
  { id: 'q14', bucket: 'rule_a', lang: 'en', citations: '4 (4 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 30299 },
  { id: 'q15', bucket: 'rule_a', lang: 'en', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'incorrect', langMatch: 'correct', tools: 3, ms: 27751 },
  { id: 'q16', bucket: 'rule_a', lang: 'en', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'incorrect', langMatch: 'correct', tools: 2, ms: 23455 },
  { id: 'q17', bucket: 'rule_b', lang: 'pt', citations: '5 (5 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 34258 },
  { id: 'q18', bucket: 'rule_b', lang: 'pt', citations: '4 (4 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 40796 },
  { id: 'q19', bucket: 'rule_b', lang: 'en', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 31012 },
  { id: 'q20', bucket: 'rule_b', lang: 'pt', citations: '4 (4 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 30500 },
  { id: 'q21', bucket: 'cross_lang', lang: 'es', citations: '3 (3 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 23801 },
  { id: 'q22', bucket: 'cross_lang', lang: 'es', citations: '4 (4 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 64311 },
  { id: 'q23', bucket: 'cross_lang', lang: 'es', citations: '7 (7 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 5, ms: 59641 },
  { id: 'q24', bucket: 'rule_a', lang: 'pt', citations: '2 (2 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 31850 },
  { id: 'q25', bucket: 'out_of_scope', lang: 'en', citations: '0 (0 anch)', anchor: '—', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'n/a', langMatch: 'correct', tools: 0, ms: 6487 },
  { id: 'q26', bucket: 'rule_a', lang: 'en', citations: '4 (4 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 38300 },
  { id: 'q27', bucket: 'out_of_scope', lang: 'pt', citations: '0 (0 anch)', anchor: '—', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'n/a', langMatch: 'correct', tools: 0, ms: 5213 },
  { id: 'q28', bucket: 'clarify', lang: 'pt', citations: '0 (0 anch)', anchor: '—', prec: '1.000', recall: '1.000', refusal: 'n/a', genKnow: 'n/a', langMatch: 'correct', tools: 0, ms: 9864 },
  { id: 'q29', bucket: 'clarify', lang: 'en', citations: '4 (4 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 3, ms: 49825 },
  { id: 'q30', bucket: 'clarify', lang: 'es', citations: '0 (0 anch)', anchor: '—', prec: '1.000', recall: '1.000', refusal: 'n/a', genKnow: 'n/a', langMatch: 'correct', tools: 0, ms: 7315 },
  { id: 'q34', bucket: 'factual', lang: 'pt', citations: '2 (2 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 16159 },
  { id: 'q35', bucket: 'factual', lang: 'en', citations: '2 (2 anch)', anchor: '1.000', prec: '1.000', recall: '1.000', refusal: 'correct', genKnow: 'correct', langMatch: 'correct', tools: 2, ms: 20274 },
]

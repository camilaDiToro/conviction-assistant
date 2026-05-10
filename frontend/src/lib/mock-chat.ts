// Mock backend for the chat surface. Returns the real response contract
// (citations, disclaimer, usage_summary, debug.steps) so the UI can be
// built and reviewed before B9 lands.

import type { ChatResponse, DebugStep, ChatAnswerResponse } from './types'

const DISCLAIMERS = {
  pt: 'Esta resposta é informativa e não constitui recomendação de investimento.',
  en: 'This response is informational and does not constitute investment advice.',
  es: 'Esta respuesta es informativa y no constituye una recomendación de inversión.',
}

function detectLang(q: string): 'pt' | 'en' | 'es' {
  // Heuristic — same family as app/agent/language.py will use.
  const t = q.toLowerCase()
  if (/[ãõáéíóúâêô]|ção|que|como|para|tributação|isenção/.test(t)) return 'pt'
  if (/¿|qué|cómo|inversión|recomendación|fiscal/.test(t)) return 'es'
  return 'en'
}

interface Args {
  question: string
  conversationId: string
}

export async function mockChat(args: Args): Promise<ChatResponse> {
  // Simulate a realistic latency for retrieval + generation
  await sleep(700 + Math.random() * 600)

  const lang = detectLang(args.question)
  const q = args.question.toLowerCase()

  // Out-of-scope detector
  if (/weather|football|recipe|piada|chiste|joke/.test(q)) {
    return wrapAnswer({
      lang,
      answer:
        lang === 'pt'
          ? 'Esta pergunta está fora do escopo do corpus de convicções da Decade. Posso ajudar com renda fixa, ações brasileiras, fundos, derivativos, tributação de investimentos, e estruturas patrimoniais.'
          : lang === 'es'
            ? 'Esta pregunta está fuera del alcance del corpus de convicciones de Decade. Puedo ayudar con renta fija, acciones brasileñas, fondos, derivados, tributación de inversiones y estructuras patrimoniales.'
            : 'This question is outside the scope of the Decade conviction corpus. I can help with fixed income, Brazilian equities, funds, derivatives, investment taxation, and wealth structures.',
      citations: [],
      out_of_scope: true,
      general_knowledge_used: false,
      general_knowledge_section: null,
      steps: [
        step('llm_call', 'agent.plan', 'Out-of-scope detection — refuse early.', 320, {
          model: 'gpt-5',
          prompt_tokens: 412,
          completion_tokens: 28,
          cached_tokens: 380,
          reasoning_tokens: 64,
        }),
      ],
    })
  }

  // LCI / LCA / tributação canned answer
  if (/lci|lca|isenção|isencao|imposto.*renda|tributação|tributacao/.test(q)) {
    return wrapAnswer({
      lang,
      answer:
        lang === 'pt'
          ? 'LCIs e LCAs são isentas de Imposto de Renda para pessoas físicas sobre os rendimentos. Para preservar essa isenção, o título precisa ser mantido por um prazo mínimo de carência de 120 dias corridos a partir da data de emissão; resgates antes desse prazo perdem o benefício e ficam sujeitos à tabela regressiva do IR. Para comparação justa com um CDB tributado, divida a taxa da LCI/LCA por (1 - alíquota do IR aplicável).'
          : lang === 'es'
            ? 'Las LCI y LCA están exentas de Impuesto sobre la Renta para personas físicas. Para preservar esa exención, el título debe mantenerse durante un plazo mínimo de carencia de 120 días corridos desde la fecha de emisión; los rescates antes de ese plazo pierden el beneficio fiscal.'
            : 'LCIs and LCAs are exempt from income tax for individuals on the yields. To preserve that exemption the bond must be held for a minimum 120 calendar-day grace period from the issue date; redemptions before that lose the benefit and are taxed on the regressive IR table. For a fair comparison to a taxed CDB, divide the LCI/LCA rate by (1 - applicable IR rate).',
      citations: [
        {
          passage_id: 'lci_lca_investimentos#prazo-minimo-carencia-tributacao',
          document: 'lci_lca_investimentos.md',
          document_updated: '2026-04-01',
          heading: 'Prazo Mínimo, Carência e Tributação',
          heading_path: ['LCI e LCA: Guia Completo de Letras de Crédito', 'Prazo Mínimo, Carência e Tributação'],
          quote:
            lang === 'en'
              ? 'devem ser mantidas pelo prazo mínimo de carência de 120 dias corridos a partir da data de emissão'
              : 'devem ser mantidas pelo prazo mínimo de carência de 120 dias corridos a partir da data de emissão',
        },
        {
          passage_id: 'lci_lca_investimentos#prazo-minimo-carencia-tributacao',
          document: 'lci_lca_investimentos.md',
          document_updated: '2026-04-01',
          heading: 'Prazo Mínimo, Carência e Tributação',
          heading_path: ['LCI e LCA: Guia Completo de Letras de Crédito', 'Prazo Mínimo, Carência e Tributação'],
          quote: 'são isentas de Imposto de Renda para pessoas físicas nos rendimentos',
        },
      ],
      out_of_scope: false,
      general_knowledge_used: false,
      general_knowledge_section: null,
      steps: [
        step('tool_call', 'search_convictions', "query='LCI tributação isenção IR' k=5", 80),
        step('tool_call', 'read_passage', 'passage_id=lci_lca_investimentos#prazo-minimo-carencia-tributacao', 28),
        step('llm_call', 'agent.answer', 'Compose grounded answer with citations.', 1240, {
          model: 'gpt-5',
          prompt_tokens: 1834,
          completion_tokens: 142,
          cached_tokens: 1620,
          reasoning_tokens: 220,
        }),
        step('verifier', 'substring', '2 citations checked → both PASS.', 4),
      ],
    })
  }

  // FGC question — answer with general-knowledge sidecar example
  if (/fgc|garantia|garantidor/.test(q)) {
    return wrapAnswer({
      lang,
      answer:
        lang === 'pt'
          ? 'O FGC protege LCIs e LCAs até R$ 250.000 por CPF por conglomerado financeiro, com limite global de R$ 1 milhão considerando todos os bancos, renovável a cada 4 anos após acionamento.'
          : 'The FGC covers LCIs and LCAs up to R$ 250,000 per CPF per financial conglomerate, with a global cap of R$ 1 million across all banks, renewable every 4 years after a payout event.',
      citations: [
        {
          passage_id: 'lci_lca_investimentos#garantia-do-fgc',
          document: 'lci_lca_investimentos.md',
          document_updated: '2026-04-01',
          heading: 'Garantia do FGC',
          heading_path: ['LCI e LCA: Guia Completo de Letras de Crédito', 'Garantia do FGC'],
          quote: 'R$ 250.000 por CPF/CNPJ por conglomerado financeiro',
        },
      ],
      out_of_scope: false,
      general_knowledge_used: false,
      general_knowledge_section: null,
      steps: [
        step('tool_call', 'search_convictions', "query='FGC garantia limite' k=5", 75),
        step('tool_call', 'read_passage', 'passage_id=lci_lca_investimentos#garantia-do-fgc', 22),
        step('llm_call', 'agent.answer', 'Compose grounded answer.', 980, {
          model: 'gpt-5',
          prompt_tokens: 1502,
          completion_tokens: 96,
          cached_tokens: 1380,
          reasoning_tokens: 160,
        }),
        step('verifier', 'substring', '1 citation checked → PASS.', 2),
      ],
    })
  }

  // Default: generic grounded answer + Rule A demo (general knowledge marked clearly)
  return wrapAnswer({
    lang,
    answer:
      lang === 'pt'
        ? 'O corpus contém convicções sobre renda fixa, ações brasileiras, fundos, tributação e estruturas patrimoniais. Para essa pergunta, não encontrei uma passagem diretamente relevante.'
        : 'The corpus covers fixed income, Brazilian equities, funds, taxation and wealth structures. I could not find a passage directly relevant to your question.',
    citations: [],
    out_of_scope: false,
    general_knowledge_used: true,
    general_knowledge_section:
      lang === 'pt'
        ? 'Não há convicção da Decade que cubra esse tópico. Em geral, a literatura aponta que diversificação setorial e temporal reduz volatilidade de carteira — mas isso não é uma posição da Decade.'
        : 'No Decade conviction covers this topic. Broadly, the literature suggests sectoral and time diversification reduces portfolio volatility — but this is not a Decade position.',
    steps: [
      step('tool_call', 'search_convictions', `query='${args.question.slice(0, 40)}' k=5`, 75),
      step('llm_call', 'agent.answer', 'No strong hits → fall back per Rule A.', 720, {
        model: 'gpt-5',
        prompt_tokens: 1240,
        completion_tokens: 88,
        cached_tokens: 1100,
        reasoning_tokens: 140,
      }),
      step('verifier', 'substring', 'No citations to verify (general-knowledge fallback).', 1),
    ],
  })
}

function step(
  kind: DebugStep['kind'],
  name: string,
  detail: string,
  duration_ms: number,
  usage?: DebugStep['usage'],
): DebugStep {
  const cost_usd = usage ? approxCost(usage) : undefined
  return { step_id: rand(), kind, name, detail, duration_ms, usage, cost_usd }
}

// Approximate gpt-5 pricing per 1M tokens — illustrative for the debug drawer.
function approxCost(u: NonNullable<DebugStep['usage']>): number {
  const inputCost = (u.prompt_tokens - u.cached_tokens) * (1.25 / 1_000_000)
  const cachedCost = u.cached_tokens * (0.125 / 1_000_000)
  const outputCost = u.completion_tokens * (10 / 1_000_000)
  return Number((inputCost + cachedCost + outputCost).toFixed(6))
}

function wrapAnswer(o: {
  lang: 'pt' | 'en' | 'es'
  answer: string
  citations: ChatAnswerResponse['citations']
  out_of_scope: boolean
  general_knowledge_used: boolean
  general_knowledge_section: string | null
  steps: DebugStep[]
}): ChatAnswerResponse {
  const totalCost = o.steps.reduce((s, st) => s + (st.cost_usd ?? 0), 0)
  return {
    kind: 'answer',
    answer: o.answer,
    citations: o.citations,
    general_knowledge_used: o.general_knowledge_used,
    general_knowledge_section: o.general_knowledge_section,
    out_of_scope: o.out_of_scope,
    disclaimer: DISCLAIMERS[o.lang],
    usage_summary: {
      question_total_cost_usd: Number(totalCost.toFixed(6)),
      conversation_total_cost_usd: Number(totalCost.toFixed(6)),
      step_count: o.steps.length,
    },
    debug: {
      tool_calls: o.steps.filter(s => s.kind === 'tool_call'),
      verification_passed: !o.steps.some(s => s.kind === 'verifier' && s.detail.includes('FAIL')),
      steps: o.steps,
    },
  }
}

function rand() {
  return Math.random().toString(36).slice(2, 10)
}

function sleep(ms: number) {
  return new Promise(r => setTimeout(r, ms))
}

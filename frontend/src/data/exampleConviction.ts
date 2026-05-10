// The full LCI/LCA conviction inlined so the chunking explainer page can
// show the raw markdown alongside the parsed passages. Source of truth:
// convictions/lci_lca_investimentos.md.

import type { Passage } from '@/lib/types'

export const RAW_MARKDOWN = `# LCI e LCA: Guia Completo de Letras de Crédito

**Decade Investment Research | Renda Fixa**
*Atualizado: Abril 2026*

---

## O Que São LCI e LCA

As Letras de Crédito Imobiliário (LCI) e as Letras de Crédito do Agronegócio (LCA) são instrumentos de dívida emitidos por instituições financeiras com o propósito de captar recursos para financiar, respectivamente, o setor imobiliário e o agronegócio. São títulos de renda fixa privada, lastreados em carteiras de crédito dos bancos emissores, e carregam dois atributos especialmente relevantes para o investidor pessoa física: a garantia do Fundo Garantidor de Créditos (FGC) e a isenção de Imposto de Renda sobre os rendimentos.

A LCI surgiu como mecanismo de fomento ao crédito habitacional — os recursos captados financiam operações de crédito imobiliário no balanço do banco emissor. A LCA cumpre papel análogo no agronegócio, viabilizando financiamento a produtores rurais, cooperativas e empresas do setor.

Do ponto de vista do investidor, LCI e LCA são funcionalmente similares e a distinção prática mais relevante é a origem setorial do lastro — o que raramente afeta a decisão de investimento, exceto em casos de análise aprofundada do balanço do emissor.

---

## Quem Pode Emitir

A emissão de LCI e LCA é restrita a instituições financeiras autorizadas pelo Banco Central do Brasil...

---

## Indexadores Disponíveis

LCIs e LCAs são emitidas com três tipos principais de remuneração:

### Pós-fixadas (CDI)
A modalidade mais comum no mercado brasileiro...

### Inflação (IPCA+)
O rendimento é composto por uma taxa real fixa mais a variação do IPCA acumulado no período...

### Prefixadas
Taxa de juros fixa definida no momento da aplicação...
`

const DOC_ID = 'lci_lca_investimentos'
const DOC_TITLE = 'LCI e LCA: Guia Completo de Letras de Crédito'

const make = (heading: string, text: string): Passage => ({
  id: `${DOC_ID}#${slugify(heading)}`,
  document_id: DOC_ID,
  document_title: DOC_TITLE,
  heading,
  heading_path: [DOC_TITLE, heading],
  text,
})

export const EXAMPLE_PASSAGES: Passage[] = [
  make(
    'O Que São LCI e LCA',
    'As Letras de Crédito Imobiliário (LCI) e as Letras de Crédito do Agronegócio (LCA) são instrumentos de dívida emitidos por instituições financeiras com o propósito de captar recursos para financiar, respectivamente, o setor imobiliário e o agronegócio. São títulos de renda fixa privada, lastreados em carteiras de crédito dos bancos emissores, e carregam dois atributos especialmente relevantes para o investidor pessoa física: a garantia do Fundo Garantidor de Créditos (FGC) e a isenção de Imposto de Renda sobre os rendimentos.\n\nA LCI surgiu como mecanismo de fomento ao crédito habitacional — os recursos captados financiam operações de crédito imobiliário no balanço do banco emissor. A LCA cumpre papel análogo no agronegócio, viabilizando financiamento a produtores rurais, cooperativas e empresas do setor.\n\nDo ponto de vista do investidor, LCI e LCA são funcionalmente similares e a distinção prática mais relevante é a origem setorial do lastro — o que raramente afeta a decisão de investimento, exceto em casos de análise aprofundada do balanço do emissor.',
  ),
  make(
    'Quem Pode Emitir',
    'A emissão de LCI e LCA é restrita a instituições financeiras autorizadas pelo Banco Central do Brasil. Os emissores elegíveis incluem bancos múltiplos e comerciais, sociedades de crédito imobiliário, associações de poupança e empréstimo, bancos de desenvolvimento e cooperativas de crédito (em condições específicas), e companhias hipotecárias. Bancos de médio porte são frequentemente os emissores mais agressivos em termos de taxas, pois concorrem pelo passivo com instituições maiores.',
  ),
  make(
    'Indexadores Disponíveis',
    'LCIs e LCAs são emitidas com três tipos principais de remuneração: pós-fixadas (CDI) — a modalidade mais comum, expressa como percentual do CDI; inflação (IPCA+) — taxa real fixa mais a variação do IPCA acumulado; e prefixadas — taxa de juros fixa definida no momento da aplicação. Bancos menores frequentemente oferecem LCIs/LCAs a 100-115% do CDI para captações de maior prazo.',
  ),
  make(
    'Prazo Mínimo, Carência e Tributação',
    'LCIs e LCAs são isentas de Imposto de Renda para pessoas físicas nos rendimentos. Para manter a isenção, devem ser mantidas pelo prazo mínimo de carência de 120 dias corridos a partir da data de emissão, conforme regulamentação do CMN. Resgates antes desse prazo perdem o benefício fiscal e ficam sujeitos à tabela regressiva do IR. Para comparar uma LCA isenta com um CDB tributado: Taxa bruta equivalente = Taxa LCI/LCA ÷ (1 - Alíquota IR). Exemplo: LCA a 92% do CDI com IR 15% equivale a 108,2% do CDI bruto.',
  ),
  make(
    'Garantia do FGC',
    'O Fundo Garantidor de Créditos protege LCIs e LCAs com limite de R$ 250.000 por CPF por conglomerado financeiro, e limite global de R$ 1.000.000 considerando todos os bancos, renovável a cada 4 anos após acionamento. A cobertura inclui principal mais rendimentos acumulados até a data do evento de crédito. O FGC tem até 3 meses para iniciar pagamentos. Para patrimônios acima do limite, a diversificação entre emissores é fundamental.',
  ),
  make(
    'Liquidez e Mercado Secundário',
    'A esmagadora maioria das LCIs e LCAs é emitida sem liquidez antes do vencimento. Existe um mercado secundário em algumas plataformas (XP, BTG Digital, Inter, Rico), mas com liquidez muito limitada — o comprador paga deságio, nem sempre há comprador disponível, e o deságio pode ser significativo em ambientes de juros elevados. Para investidores que precisam de liquidez frequente, LCIs e LCAs não são o instrumento correto.',
  ),
  make(
    'Risco de Crédito do Emissor',
    "A garantia do FGC resolve o risco de crédito dentro dos limites cobertos. Acima desses limites, o investidor está exposto ao risco de insolvência do banco emissor. Considere: rating de crédito (Moody's, Fitch, S&P, Austin Rating, SR Rating), índice de Basileia (atenção abaixo de 12%), qualidade da carteira de crédito (inadimplência acima de 5% é alerta), concentração de passivo, e liquidez corrente.",
  ),
  make(
    'Onde Acessar LCIs e LCAs',
    'A democratização do acesso ocorreu principalmente através de plataformas digitais que agregam emissões de dezenas de bancos: XP Investimentos, BTG Digital, Rico, Órama, Nuinvest e Inter Invest. Grandes bancos emitem para sua base de clientes com taxas geralmente inferiores às disponíveis em plataformas abertas. Para volumes acima de R$ 500.000, mesas de renda fixa frequentemente acessam emissões mais recentes via negociação direta.',
  ),
  make(
    'Estratégias de Alocação',
    'Escalonamento de Vencimentos (Ladder): construção de uma escada de vencimentos com LCIs e LCAs distribuídas ao longo do tempo. Mistura de Indexadores: diversificar entre LCIs pós-fixadas (CDI) e IPCA+ reduz o risco de oportunidade. Reserva de Emergência vs. Acumulação: para reserva de emergência LCIs e LCAs NÃO são adequadas (prefira Tesouro Selic ou fundos DI); para acumulação de médio e longo prazo, são uma das alternativas mais competitivas, especialmente em cenários de Selic elevada.',
  ),
]

function slugify(s: string): string {
  return s
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export const HEADINGS_TREE = EXAMPLE_PASSAGES.map(p => ({
  passage_id: p.id,
  heading: p.heading,
  slug: p.id.split('#')[1],
}))

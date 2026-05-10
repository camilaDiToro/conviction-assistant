// Hand-written JSON schemas — pulled verbatim from app/tools/registry.py.
// Each schema satisfies OpenAI strict mode: every property is in `required`,
// `additionalProperties: false`, no `default` values.

export interface ToolSpec {
  name: string
  oneLine: string
  description: string
  parameters: object
  whenToCall: string
  sampleInput: object
  sampleOutput: unknown
}

export const TOOLS: ToolSpec[] = [
  {
    name: 'list_documents',
    oneLine: 'The corpus-level table of contents.',
    description:
      'Return all conviction documents with their titles, last-updated dates (if known), and passage counts. Use this once early in a conversation to discover what documents are available.',
    parameters: {
      type: 'object',
      properties: {},
      required: [],
      additionalProperties: false,
    },
    whenToCall:
      'Once at the start when the agent has no idea which documents are even in scope. After that, prefer search_convictions.',
    sampleInput: {},
    sampleOutput: [
      { id: 'lci_lca_investimentos', title: 'LCI e LCA: Guia Completo de Letras de Crédito', document_updated: '2026-04-01', passage_count: 9 },
      { id: 'cdbs_quick_guide', title: 'CDBs: A Quick Guide', document_updated: '2026-03-15', passage_count: 6 },
      { id: 'guia_completo_tributacao_investimentos', title: 'Guia Completo de Tributação de Investimentos', document_updated: '2026-04-15', passage_count: 12 },
      '... 27 more',
    ],
  },
  {
    name: 'read_document_outline',
    oneLine: 'One document’s table of contents — to pick the right passage to read.',
    description:
      "Return one document's outline: its title, last-updated date, passage count, and the ordered list of headings (each with its passage_id). Use this to find which passage in a document covers a topic before reading it.",
    parameters: {
      type: 'object',
      properties: {
        document_id: {
          type: 'string',
          description: 'The document ID, as returned by list_documents (DocSummary.id).',
        },
      },
      required: ['document_id'],
      additionalProperties: false,
    },
    whenToCall:
      'When search_convictions surfaces a document that may have a more directly relevant passage than the one returned. Cheaper than calling search again with a refined query.',
    sampleInput: { document_id: 'lci_lca_investimentos' },
    sampleOutput: {
      document_id: 'lci_lca_investimentos',
      document_title: 'LCI e LCA: Guia Completo de Letras de Crédito',
      document_updated: '2026-04-01',
      passage_count: 9,
      headings: [
        { passage_id: 'lci_lca_investimentos#o-que-sao-lci-e-lca', heading: 'O Que São LCI e LCA', ordinal: 1 },
        { passage_id: 'lci_lca_investimentos#quem-pode-emitir', heading: 'Quem Pode Emitir', ordinal: 2 },
        { passage_id: 'lci_lca_investimentos#prazo-minimo-carencia-tributacao', heading: 'Prazo Mínimo, Carência e Tributação', ordinal: 4 },
        '...',
      ],
    },
  },
  {
    name: 'search_convictions',
    oneLine: 'BM25 retrieval — call this first.',
    description:
      'Search the conviction corpus by free-text query and return the top-k matching passages, each with a short snippet, document title, heading path, last-updated date, and BM25 score. Call this first to find relevant evidence; then call read_passage for the full text of any hit you want to cite.',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description:
            "Free-text query in the user's language (PT, EN, or ES). BM25 ranking with accent-stripped, lowercase tokenization. Use specific terms (asset names, regulations, headings) rather than long paraphrases.",
        },
        k: {
          type: 'integer',
          description:
            'Number of top hits to return. Pass 5 unless you have a reason to change it; larger k dilutes precision.',
        },
      },
      required: ['query', 'k'],
      additionalProperties: false,
    },
    whenToCall:
      'First call after the user question. The orchestrator enforces ≥ 1 search before any answer can be emitted.',
    sampleInput: { query: 'LCI tributação isenção de IR', k: 5 },
    sampleOutput: [
      {
        passage_id: 'lci_lca_investimentos#prazo-minimo-carencia-tributacao',
        score: 8.42,
        document_title: 'LCI e LCA: Guia Completo de Letras de Crédito',
        heading_path: ['LCI e LCA: Guia Completo de Letras de Crédito', 'Prazo Mínimo, Carência e Tributação'],
        snippet:
          'LCIs e LCAs são isentas de Imposto de Renda para pessoas físicas nos rendimentos. Para manter a isenção, devem ser mantidas pelo prazo mínimo de carência de 120…',
        document_updated: '2026-04-01',
      },
      '... 4 more',
    ],
  },
  {
    name: 'read_passage',
    oneLine: 'Full passage text — the only tool that returns the full body.',
    description:
      "Return the full text of one passage by ID, plus its document title, heading path, and last-updated date. This is the only tool that returns full passage text; other tools return identifiers and outlines.",
    parameters: {
      type: 'object',
      properties: {
        passage_id: {
          type: 'string',
          description:
            'The passage ID, as returned by search_convictions or read_document_outline (Heading.passage_id).',
        },
      },
      required: ['passage_id'],
      additionalProperties: false,
    },
    whenToCall:
      'After search_convictions surfaces a relevant snippet — the snippet is truncated to ~200 chars. The agent must read the full passage before quoting it, otherwise the verifier will fail.',
    sampleInput: { passage_id: 'lci_lca_investimentos#prazo-minimo-carencia-tributacao' },
    sampleOutput: {
      id: 'lci_lca_investimentos#prazo-minimo-carencia-tributacao',
      document_title: 'LCI e LCA: Guia Completo de Letras de Crédito',
      heading: 'Prazo Mínimo, Carência e Tributação',
      heading_path: ['LCI e LCA: Guia Completo de Letras de Crédito', 'Prazo Mínimo, Carência e Tributação'],
      text: 'LCIs e LCAs são isentas de Imposto de Renda para pessoas físicas nos rendimentos. Para manter a isenção, devem ser mantidas pelo prazo mínimo de carência de 120 dias corridos a partir da data de emissão, conforme regulamentação do CMN…',
      document_updated: '2026-04-01',
    },
  },
]

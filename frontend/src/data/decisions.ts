// Source of truth for sidebar nav. Each item maps to a route under /design/*.

export interface NavItem {
  to: string
  label: string
}

export interface NavGroup {
  label: string
  caret: boolean // collapsible
  items: NavItem[]
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: '',
    caret: false,
    items: [{ to: '/design/overview', label: 'Overview' }],
  },
  {
    label: 'Pipeline',
    caret: true,
    items: [
      { to: '/design/pipeline/corpus', label: 'Corpus & chunking' },
      { to: '/design/pipeline/retrieval', label: 'Retrieval (BM25)' },
      { to: '/design/pipeline/tools', label: 'Tools' },
      { to: '/design/pipeline/resolver', label: 'Resolver' },
      { to: '/design/pipeline/agent-loop', label: 'Agent loop' },
    ],
  },
  {
    label: 'Eval',
    caret: true,
    items: [
      { to: '/design/eval', label: 'Metrics & judge' },
      { to: '/design/eval/dataset', label: 'Dataset & results' },
      { to: '/design/eval/chat', label: 'Latest run as chat' },
    ],
  },
  // {
  //   label: 'Framing',
  //   caret: true,
  //   items: [
  //     { to: '/design/framing/tiers', label: 'Production vs simplified' },
  //   ],
  // },
]

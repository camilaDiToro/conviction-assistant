// Mirror of the backend offset resolver in app/agent/resolver/substring.py.
//
// Literal substring search — no normalization, no edit distance, no LLM. If
// the quote doesn't anchor, the citation still surfaces in the response; the
// popup shows the passage with no highlight (offsets are null). The agent
// loop does NOT retry on resolver failure.

export type ResolutionFailure = 'empty_quote' | 'offset_not_found'

export interface Resolution {
  anchored: boolean
  start: number | null
  end: number | null
  failureReason: ResolutionFailure | null
}

export function resolve(quote: string, passageText: string): Resolution {
  if (!quote || !quote.trim()) {
    return { anchored: false, start: null, end: null, failureReason: 'empty_quote' }
  }
  const idx = passageText.indexOf(quote)
  if (idx === -1) {
    return { anchored: false, start: null, end: null, failureReason: 'offset_not_found' }
  }
  return { anchored: true, start: idx, end: idx + quote.length, failureReason: null }
}

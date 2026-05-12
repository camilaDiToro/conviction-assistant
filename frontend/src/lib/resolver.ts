// Mirror of the backend offset resolver in app/agent/resolver/substring.py.
//
// Substring search with a length-preserving fold for cosmetic diffs (smart
// quotes, NBSP, en/em dash). Every fold is 1:1 so offsets returned still
// index the ORIGINAL passage text. No edit distance, no LLM. If the quote
// still doesn't anchor after the fold, the citation surfaces with no
// highlight (offsets null). The agent loop does NOT retry on resolver
// failure.

export type ResolutionFailure = 'empty_quote' | 'offset_not_found'

export interface Resolution {
  anchored: boolean
  start: number | null
  end: number | null
  failureReason: ResolutionFailure | null
}

// Keep this table in sync with _FOLD_TABLE in app/agent/resolver/substring.py.
const FOLD: Record<string, string> = {
  '“': '"', '”': '"', '„': '"', '‟': '"',
  '«': '"', '»': '"',
  '‘': "'", '’': "'", '‚': "'", '‛': "'",
  '–': '-', '—': '-', '−': '-',
  ' ': ' ', ' ': ' ', ' ': ' ',
}

function normalize(text: string): string {
  let out = ''
  for (const ch of text) {
    const folded = FOLD[ch]
    if (folded !== undefined) { out += folded; continue }
    const nfkc = ch.normalize('NFKC')
    out += nfkc.length === 1 ? nfkc : ch
  }
  return out
}

export function resolve(quote: string, passageText: string): Resolution {
  if (!quote || !quote.trim()) {
    return { anchored: false, start: null, end: null, failureReason: 'empty_quote' }
  }
  let idx = passageText.indexOf(quote)
  if (idx !== -1) {
    return { anchored: true, start: idx, end: idx + quote.length, failureReason: null }
  }
  const normQuote = normalize(quote)
  const normText = normalize(passageText)
  idx = normText.indexOf(normQuote)
  if (idx === -1) {
    return { anchored: false, start: null, end: null, failureReason: 'offset_not_found' }
  }
  return { anchored: true, start: idx, end: idx + normQuote.length, failureReason: null }
}

// Tiny BM25 implementation for the retrieval playground page. Matches the
// backend's normalization pipeline (NFKD → strip combining marks →
// lowercase → collapse whitespace → tokenize on \W+) so the visualization
// is faithful to what the production index does.
//
// Default BM25 parameters: k1=1.5, b=0.75. Production uses bm25s defaults
// but the difference is negligible for this demo and the rankings are the
// observable thing, not the absolute scores.

const COMBINING = /[̀-ͯ]/g
const NON_WORD = /\W+/u

export function normalizeForSearch(text: string): string {
  return text
    .normalize('NFKD')
    .replace(COMBINING, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim()
}

export function tokenize(text: string): string[] {
  return normalizeForSearch(text).split(NON_WORD).filter(Boolean)
}

export interface IndexedDoc<T> {
  doc: T
  text: string
  tokens: string[]
}

export interface ScoredHit<T> {
  doc: T
  score: number
  matchedTokens: Set<string>
}

export class BM25<T> {
  private k1 = 1.5
  private b = 0.75
  private docs: IndexedDoc<T>[] = []
  private avgDocLen = 0
  private docFreq: Map<string, number> = new Map()
  private idf: Map<string, number> = new Map()

  constructor(docs: Array<{ doc: T; text: string }>) {
    this.docs = docs.map(({ doc, text }) => ({ doc, text, tokens: tokenize(text) }))
    const totalLen = this.docs.reduce((sum, d) => sum + d.tokens.length, 0)
    this.avgDocLen = totalLen / Math.max(this.docs.length, 1)
    for (const d of this.docs) {
      const seen = new Set<string>()
      for (const t of d.tokens) {
        if (seen.has(t)) continue
        seen.add(t)
        this.docFreq.set(t, (this.docFreq.get(t) ?? 0) + 1)
      }
    }
    const N = this.docs.length
    for (const [t, df] of this.docFreq) {
      this.idf.set(t, Math.log(1 + (N - df + 0.5) / (df + 0.5)))
    }
  }

  search(query: string, k = 5): ScoredHit<T>[] {
    const queryTokens = tokenize(query)
    if (queryTokens.length === 0) return []

    const hits: ScoredHit<T>[] = this.docs.map(d => {
      let score = 0
      const matched = new Set<string>()
      const tf = new Map<string, number>()
      for (const t of d.tokens) tf.set(t, (tf.get(t) ?? 0) + 1)
      for (const qt of queryTokens) {
        const f = tf.get(qt)
        if (!f) continue
        const idf = this.idf.get(qt) ?? 0
        const numerator = f * (this.k1 + 1)
        const denominator =
          f + this.k1 * (1 - this.b + (this.b * d.tokens.length) / (this.avgDocLen || 1))
        score += idf * (numerator / denominator)
        matched.add(qt)
      }
      return { doc: d.doc, score, matchedTokens: matched }
    })

    return hits
      .filter(h => h.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, k)
  }
}

// Mirror of the backend citation-verifier normalization policy. Kept in
// sync deliberately — any change here MUST land in app/verifier (when it
// ships) at the same time. Pinned so the explainer page demonstrates
// the exact pipeline that the production verifier uses.
//
// Pipeline (verifier-layer — preserves diacritics, unlike the BM25 layer):
//   1. NFC unicode normalization
//   2. strip soft-hyphens (U+00AD) and zero-width chars (U+200B/C/D, U+FEFF)
//   3. fold smart quotes / apostrophes to ASCII
//   4. normalize en/em dashes and non-breaking hyphens to ASCII '-'
//   5. collapse internal whitespace runs to a single space
//   6. trim

const ZERO_WIDTH = /[­​‌‍﻿]/g
const SMART_QUOTES_DOUBLE = /[“”„‟″‶]/g
const SMART_QUOTES_SINGLE = /[‘’‚‛′‵]/g
const DASHES = /[‐‑‒–—−]/g
const WHITESPACE = /\s+/g

export function normalizeForVerify(text: string): string {
  return text
    .normalize('NFC')
    .replace(ZERO_WIDTH, '')
    .replace(SMART_QUOTES_DOUBLE, '"')
    .replace(SMART_QUOTES_SINGLE, "'")
    .replace(DASHES, '-')
    .replace(WHITESPACE, ' ')
    .trim()
}

export interface VerifyResult {
  passed: boolean
  normalizedQuote: string
  normalizedPassage: string
  reason: string
}

export function verify(quote: string, passage: string): VerifyResult {
  const nq = normalizeForVerify(quote)
  const np = normalizeForVerify(passage)
  if (!nq) {
    return { passed: false, normalizedQuote: nq, normalizedPassage: np, reason: 'Empty quote.' }
  }
  if (!np) {
    return { passed: false, normalizedQuote: nq, normalizedPassage: np, reason: 'Empty passage.' }
  }
  const passed = np.includes(nq)
  return {
    passed,
    normalizedQuote: nq,
    normalizedPassage: np,
    reason: passed
      ? 'Quote is a substring of the normalized passage.'
      : 'Quote is NOT a substring of the normalized passage. The agent retries once with this exact feedback; if it fails again the claim is stripped or the answer becomes a safe refusal.',
  }
}

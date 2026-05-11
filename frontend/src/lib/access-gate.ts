// Chat access token, paste-and-store flow.
//
// The token is no longer bundled into the SPA via VITE_CHAT_ACCESS_CODE
// — that's trivially extractable from the deployed JS. The user pastes
// the token at runtime; we keep it in localStorage and send it as
// `X-Chat-Token` on every /chat request.
//
// The token is validated server-side. Real auth (JWT/OAuth/sessions) is
// still out of scope for v1; this gives us a server-enforced bearer
// without a real auth flow.

const STORAGE_KEY = 'decade-chat-token'

export function readToken(): string | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v && v.trim() ? v : null
  } catch {
    return null
  }
}

export function saveToken(token: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, token.trim())
  } catch {
    /* localStorage disabled — gate becomes session-only */
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}

export function hasToken(): boolean {
  return readToken() !== null
}
